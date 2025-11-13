"""
釘釘 Webhook 服務器
"""

import logging
import json
import hashlib
import base64
from typing import Dict, Any
from aiohttp import web
from Crypto.Cipher import AES


class WebhookServer:
    """釘釘 Webhook 服務器"""
    
    def __init__(self, sync_service, config: Dict[str, Any]):
        """
        初始化 Webhook 服務器
        
        Args:
            sync_service: 同步服務實例
            config: Webhook 配置
        """
        self.sync_service = sync_service
        self.port = config['port']
        self.aes_key = config['aes_key']
        self.token = config['token']
        self.logger = logging.getLogger('dingtalk_notion_sync.webhook')
        
        # 初始化 AES 解密器
        self.aes_key_bytes = base64.b64decode(self.aes_key + "=")
        
        # 創建 web 應用
        self.app = web.Application()
        self.app.router.add_post('/webhook/dingtalk', self.handle_webhook)
    
    async def start(self):
        """啟動 Webhook 服務器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        self.logger.info(f"Webhook 服務器已啟動,監聽端口 {self.port}")
    
    async def handle_webhook(self, request: web.Request) -> web.Response:
        """
        處理 Webhook 請求
        
        Args:
            request: HTTP 請求
            
        Returns:
            HTTP 響應
        """
        try:
            # 讀取請求體
            body = await request.json()
            self.logger.debug(f"收到 Webhook 請求: {body}")
            
            # 驗證簽名
            query_params = request.query
            if not self._verify_signature(body):
                self.logger.warning("Webhook 簽名驗證失敗")
            if not self._verify_signature(query_params, body):
            
            # 解密事件內容
            encrypt_data = body.get('encrypt')
            if encrypt_data:
                event_data = self._decrypt(encrypt_data)
                event = json.loads(event_data)
                
                # 處理事件
                await self.sync_service.handle_dingtalk_event(event)
                
                # 返回成功響應
                return web.json_response({
                    "msg_signature": self._generate_signature(encrypt_data),
                    "timeStamp": body.get('timeStamp'),
                    "nonce": body.get('nonce'),
                    "encrypt": encrypt_data
                })
            else:
                # 處理驗證 URL 請求
                return web.Response(text="ok")
                
        except Exception as e:
            self.logger.error(f"處理 Webhook 請求時發生錯誤: {e}", exc_info=True)
            return web.Response(status=500, text="Internal server error")
    
    def _verify_signature(self, query_params, body: Dict[str, Any]) -> bool:
        """
        驗證請求簽名
        
        Args:
            body: 請求體
            
        Returns:
            驗證是否通過
        """
        # 從 URL 查詢參數獲取簽名相關參數
        msg_signature = query_params.get('signature')
        timestamp = query_params.get('timestamp')
        nonce = query_params.get('nonce')

        # 從請求體獲取加密數據
        encrypt = body.get('encrypt')           
            # 計算簽名
            computed_signature = self._generate_signature(
                timestamp, nonce, encrypt
            )
            
            return msg_signature == computed_signature
        except Exception as e:
            self.logger.error(f"驗證簽名時發生錯誤: {e}", exc_info=True)
            return False
    
    def _generate_signature(self, *args) -> str:
        """
        生成簽名
        
        Args:
            *args: 要簽名的參數
            
        Returns:
            簽名字符串
        """
        # 將參數與 token 組合並排序
        params = [self.token] + [str(arg) for arg in args]
        params.sort()
        
        # 計算 SHA1
        sha1 = hashlib.sha1()
        sha1.update(''.join(params).encode('utf-8'))
        return sha1.hexdigest()
    
    def _decrypt(self, encrypt_text: str) -> str:
        """
        解密事件內容
        
        Args:
            encrypt_text: 加密的文本
            
        Returns:
            解密後的文本
        """
        try:
            # Base64 解碼
            cipher_text = base64.b64decode(encrypt_text)
            
            # AES 解密
            cipher = AES.new(self.aes_key_bytes, AES.MODE_CBC, self.aes_key_bytes[:16])
            decrypted = cipher.decrypt(cipher_text)
            
            # 去除填充
            pad = decrypted[-1]
            if isinstance(pad, str):
                pad = ord(pad)
            decrypted = decrypted[:-pad]
            
            # 提取消息內容 (去除前 16 字節的隨機數和後 4 字節的長度)
            content = decrypted[16:-4].decode('utf-8')
            
            return content
        except Exception as e:
            self.logger.error(f"解密事件內容時發生錯誤: {e}", exc_info=True)
            raise


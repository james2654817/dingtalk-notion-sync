#!/usr/bin/env python3
"""
釘釘-Notion 雙向同步系統主程式
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import load_config
from src.dingtalk_client import DingTalkClient
from src.notion_client import NotionClient
from src.sync_service import SyncService
from src.webhook_server import WebhookServer
from src.logger import setup_logger


async def main():
    """主函數"""
    # 載入配置
    config = load_config()
    
    # 設置日誌
    logger = setup_logger(config)
    logger.info("=" * 60)
    logger.info("釘釘-Notion 雙向同步系統啟動")
    logger.info("=" * 60)
    
    try:
        # 初始化客戶端
        dingtalk_client = DingTalkClient(config['dingtalk'])
        notion_client = NotionClient(config['notion'])
        
        # 初始化同步服務
        sync_service = SyncService(
            dingtalk_client=dingtalk_client,
            notion_client=notion_client,
            config=config
        )
        
        # 初始化 Webhook 服務器
        webhook_server = WebhookServer(
            sync_service=sync_service,
            config=config['dingtalk']['webhook']
        )
        
        # 啟動服務
        logger.info("正在啟動 Webhook 服務器...")
        webhook_task = asyncio.create_task(webhook_server.start())
        
        logger.info("正在啟動 Notion 輪詢服務...")
        polling_task = asyncio.create_task(sync_service.start_notion_polling())
        
        logger.info("系統已成功啟動,正在運行中...")
        logger.info(f"Webhook 服務器監聽端口: {config['dingtalk']['webhook']['port']}")
        logger.info(f"Notion 輪詢間隔: {config['notion']['polling_interval']} 秒")
        
        # 等待任務完成 (通常不會完成,除非出錯或手動停止)
        await asyncio.gather(webhook_task, polling_task)
        
    except KeyboardInterrupt:
        logger.info("收到停止信號,正在關閉服務...")
    except Exception as e:
        logger.error(f"系統運行時發生錯誤: {e}", exc_info=True)
        raise
    finally:
        logger.info("系統已停止")


if __name__ == "__main__":
    asyncio.run(main())


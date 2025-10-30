"""
釘釘 API 客戶端
"""

import logging
import time
from typing import Dict, Any, Optional, List
import requests


class DingTalkClient:
    """釘釘 API 客戶端"""
    
    BASE_URL = "https://api.dingtalk.com"
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化釘釘客戶端
        
        Args:
            config: 釘釘配置字典
        """
        self.app_key = config['app_key']
        self.app_secret = config['app_secret']
        self.user_union_id = config['union_id']
        self.logger = logging.getLogger('dingtalk_notion_sync.dingtalk')
        
        # Access Token 緩存
        self._access_token = None
        self._token_expires_at = 0
    
    def get_access_token(self) -> str:
        """
        獲取企業內部應用的 Access Token
        
        Returns:
            Access Token 字符串
        """
        # 檢查緩存是否有效
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        # 請求新的 Access Token
        url = f"{self.BASE_URL}/v1.0/oauth2/accessToken"
        response = requests.post(
            url,
            json={
                "appKey": self.app_key,
                "appSecret": self.app_secret
            }
        )
        response.raise_for_status()
        data = response.json()
        
        self._access_token = data['accessToken']
        # 提前 5 分鐘過期以確保安全
        self._token_expires_at = time.time() + data['expireIn'] - 300
        
        self.logger.info("成功獲取釘釘 Access Token")
        return self._access_token
    
    def create_todo_task(
        self,
        subject: str,
        executor_ids: List[str],
        due_time: Optional[int] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        創建釘釘待辦任務
        
        Args:
            subject: 待辦標題
            executor_ids: 執行者的 unionId 列表
            due_time: 截止時間 (Unix 時間戳,毫秒)
            description: 待辦描述
            priority: 優先級 (10/20/30/40)
            source_id: 業務系統側的唯一標識 ID
            
        Returns:
            創建結果,包含 taskId
        """
        url = f"{self.BASE_URL}/v1.0/todo/users/{self.user_union_id}/tasks"
        headers = {
            "x-acs-dingtalk-access-token": self.get_access_token(),
            "Content-Type": "application/json"
        }
        
        body = {
            "subject": subject,
            "executorIds": executor_ids
        }
        
        if source_id:
            body["sourceId"] = source_id
        if due_time:
            body["dueTime"] = due_time
        if description:
            body["description"] = description
        if priority:
            body["priority"] = priority
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        result = response.json()
        
        self.logger.info(f"成功創建釘釘待辦任務: {subject}")
        return result
    
    def update_todo_task(
        self,
        task_id: str,
        subject: Optional[str] = None,
        due_time: Optional[int] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        done: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        更新釘釘待辦任務
        
        Args:
            task_id: 釘釘任務 ID
            subject: 待辦標題
            due_time: 截止時間
            description: 待辦描述
            priority: 優先級
            done: 是否完成
            
        Returns:
            更新結果
        """
        url = f"{self.BASE_URL}/v1.0/todo/users/{self.user_union_id}/tasks/{task_id}"
        headers = {
            "x-acs-dingtalk-access-token": self.get_access_token(),
            "Content-Type": "application/json"
        }
        
        body = {}
        if subject is not None:
            body["subject"] = subject
        if due_time is not None:
            body["dueTime"] = due_time
        if description is not None:
            body["description"] = description
        if priority is not None:
            body["priority"] = priority
        if done is not None:
            body["done"] = done
        
        response = requests.put(url, headers=headers, json=body)
        response.raise_for_status()
        result = response.json()
        
        self.logger.info(f"成功更新釘釘待辦任務: {task_id}")
        return result
    
    def delete_todo_task(self, task_id: str) -> Dict[str, Any]:
        """
        刪除釘釘待辦任務
        
        Args:
            task_id: 釘釘任務 ID
            
        Returns:
            刪除結果
        """
        url = f"{self.BASE_URL}/v1.0/todo/users/{self.user_union_id}/tasks/{task_id}"
        headers = {
            "x-acs-dingtalk-access-token": self.get_access_token()
        }
        
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        self.logger.info(f"成功刪除釘釘待辦任務: {task_id}")
        return result
    
    def get_todo_task(self, task_id: str) -> Dict[str, Any]:
        """
        獲取釘釘待辦任務詳情
        
        Args:
            task_id: 釘釘任務 ID
            
        Returns:
            任務詳情
        """
        url = f"{self.BASE_URL}/v1.0/todo/users/{self.user_union_id}/tasks/{task_id}"
        headers = {
            "x-acs-dingtalk-access-token": self.get_access_token()
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


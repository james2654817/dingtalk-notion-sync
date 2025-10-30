"""
Notion API 客戶端
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests


class NotionClient:
    """Notion API 客戶端"""
    
    BASE_URL = "https://api.notion.com/v1"
    API_VERSION = "2022-06-28"
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Notion 客戶端
        
        Args:
            config: Notion 配置字典
        """
        self.integration_token = config['token']
        self.personal_todo_db_id = config['personal_todo_database_id']
        self.team_task_db_id = config['team_task_database_id']
        self.logger = logging.getLogger('dingtalk_notion_sync.notion')
        
        self.headers = {
            "Authorization": f"Bearer {self.integration_token}",
            "Notion-Version": self.API_VERSION,
            "Content-Type": "application/json"
        }
    
    def query_database(
        self,
        database_id: str,
        filter_obj: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        查詢資料庫
        
        Args:
            database_id: 資料庫 ID
            filter_obj: 篩選條件
            sorts: 排序條件
            
        Returns:
            頁面列表
        """
        url = f"{self.BASE_URL}/databases/{database_id}/query"
        body = {}
        if filter_obj:
            body["filter"] = filter_obj
        if sorts:
            body["sorts"] = sorts
        
        response = requests.post(url, headers=self.headers, json=body)
        response.raise_for_status()
        data = response.json()
        
        return data.get('results', [])
    
    def create_page(
        self,
        database_id: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        在資料庫中創建新頁面
        
        Args:
            database_id: 資料庫 ID
            properties: 頁面屬性
            
        Returns:
            創建的頁面對象
        """
        url = f"{self.BASE_URL}/pages"
        body = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        response = requests.post(url, headers=self.headers, json=body)
        response.raise_for_status()
        page = response.json()
        
        self.logger.info(f"成功在 Notion 創建頁面: {page['id']}")
        return page
    
    def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新頁面屬性
        
        Args:
            page_id: 頁面 ID
            properties: 要更新的屬性
            
        Returns:
            更新後的頁面對象
        """
        url = f"{self.BASE_URL}/pages/{page_id}"
        body = {"properties": properties}
        
        response = requests.patch(url, headers=self.headers, json=body)
        response.raise_for_status()
        page = response.json()
        
        self.logger.info(f"成功更新 Notion 頁面: {page_id}")
        return page
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        獲取頁面詳情
        
        Args:
            page_id: 頁面 ID
            
        Returns:
            頁面對象
        """
        url = f"{self.BASE_URL}/pages/{page_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def find_page_by_dingtalk_id(
        self,
        database_id: str,
        dingtalk_task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        根據釘釘任務 ID 查找 Notion 頁面
        
        Args:
            database_id: 資料庫 ID
            dingtalk_task_id: 釘釘任務 ID
            
        Returns:
            頁面對象,若不存在則返回 None
        """
        filter_obj = {
            "property": "DingTalk Task ID",
            "rich_text": {
                "equals": dingtalk_task_id
            }
        }
        
        pages = self.query_database(database_id, filter_obj)
        return pages[0] if pages else None
    
    def get_recently_edited_pages(
        self,
        database_id: str,
        since_timestamp: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        獲取最近編輯的頁面
        
        Args:
            database_id: 資料庫 ID
            since_timestamp: 起始時間戳 (ISO 8601 格式)
            
        Returns:
            頁面列表
        """
        filter_obj = None
        if since_timestamp:
            filter_obj = {
                "timestamp": "last_edited_time",
                "last_edited_time": {
                    "after": since_timestamp
                }
            }
        
        sorts = [
            {
                "timestamp": "last_edited_time",
                "direction": "descending"
            }
        ]
        
        return self.query_database(database_id, filter_obj, sorts)
    
    @staticmethod
    def build_title_property(text: str) -> Dict[str, Any]:
        """構建標題屬性"""
        return {
            "title": [
                {
                    "text": {"content": text}
                }
            ]
        }
    
    @staticmethod
    def build_rich_text_property(text: str) -> Dict[str, Any]:
        """構建富文本屬性"""
        return {
            "rich_text": [
                {
                    "text": {"content": text}
                }
            ]
        }
    
    @staticmethod
    def build_date_property(date_str: Optional[str]) -> Dict[str, Any]:
        """構建日期屬性"""
        if not date_str:
            return {"date": None}
        return {
            "date": {
                "start": date_str
            }
        }
    
    @staticmethod
    def build_select_property(option: str) -> Dict[str, Any]:
        """構建單選屬性"""
        return {
            "select": {
                "name": option
            }
        }
    
    @staticmethod
    def build_status_property(status: str) -> Dict[str, Any]:
        """構建狀態屬性"""
        return {
            "status": {
                "name": status
            }
        }
    
    @staticmethod
    def build_url_property(url: str) -> Dict[str, Any]:
        """構建 URL 屬性"""
        return {
            "url": url
        }
    
    @staticmethod
    def extract_plain_text(rich_text_array: List[Dict]) -> str:
        """從富文本數組中提取純文本"""
        if not rich_text_array:
            return ""
        return "".join([item.get('plain_text', '') for item in rich_text_array])
    
    @staticmethod
    def extract_date(date_obj: Optional[Dict]) -> Optional[str]:
        """從日期對象中提取日期字符串"""
        if not date_obj or not date_obj.get('date'):
            return None
        return date_obj['date'].get('start')
    
    @staticmethod
    def extract_select(select_obj: Optional[Dict]) -> Optional[str]:
        """從單選對象中提取選項名稱"""
        if not select_obj or not select_obj.get('select'):
            return None
        return select_obj['select'].get('name')
    
    @staticmethod
    def extract_status(status_obj: Optional[Dict]) -> Optional[str]:
        """從狀態對象中提取狀態名稱"""
        if not status_obj or not status_obj.get('status'):
            return None
        return status_obj['status'].get('name')


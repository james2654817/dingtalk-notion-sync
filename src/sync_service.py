"""
同步服務核心邏輯
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from src.dingtalk_client import DingTalkClient
from src.notion_client import NotionClient


class SyncService:
    """雙向同步服務"""
    
    def __init__(
        self,
        dingtalk_client: DingTalkClient,
        notion_client: NotionClient,
        config: Dict[str, Any]
    ):
        """
        初始化同步服務
        
        Args:
            dingtalk_client: 釘釘客戶端
            notion_client: Notion 客戶端
            config: 配置字典
        """
        self.dingtalk = dingtalk_client
        self.notion = notion_client
        self.config = config
        self.logger = logging.getLogger('dingtalk_notion_sync.sync')
        
        # 記錄上次輪詢時間 (初始化為 7 天前,以便首次同步所有最近的項面)
        from datetime import timedelta
        initial_time = datetime.now(timezone.utc) - timedelta(days=7)
        self.last_poll_time = initial_time.isoformat()
    
    async def start_notion_polling(self):
        """啟動 Notion 輪詢服務"""
        interval = self.config['polling']['interval']
        self.logger.info(f"Notion 輪詢服務已啟動,間隔 {interval} 秒")
        
        while True:
            try:
                await self._poll_notion_changes()
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"Notion 輪詢時發生錯誤: {e}", exc_info=True)
                await asyncio.sleep(interval)
    
    async def _poll_notion_changes(self):
        """輪詢 Notion 的變更"""
        self.logger.debug("開始輪詢 Notion 變更...")
        
        # 輪詢私人待辦看板
        await self._poll_database_changes(
            database_id=self.notion.personal_todo_db_id,
            is_personal_todo=True
        )
        
        # 輪詢團隊任務追蹤表
        await self._poll_database_changes(
            database_id=self.notion.team_task_db_id,
            is_personal_todo=False
        )
        
        # 更新輪詢時間
        self.last_poll_time = datetime.now(timezone.utc).isoformat()
    
    async def _poll_database_changes(self, database_id: str, is_personal_todo: bool):
        """
        輪詢單個資料庫的變更
        
        Args:
            database_id: 資料庫 ID
            is_personal_todo: 是否為私人待辦看板
        """
        try:
            # 查詢最近編輯的頁面
            pages = self.notion.get_recently_edited_pages(
                database_id=database_id,
                since_timestamp=self.last_poll_time
            )
            
            for page in pages:
                await self._sync_notion_to_dingtalk(page, is_personal_todo)
                
        except Exception as e:
            db_name = "私人待辦看板" if is_personal_todo else "團隊任務追蹤表"
            self.logger.error(f"輪詢 {db_name} 時發生錯誤: {e}", exc_info=True)
    
    async def _sync_notion_to_dingtalk(self, page: Dict[str, Any], is_personal_todo: bool):
        """
        將 Notion 頁面同步到釘釘
        
        Args:
            page: Notion 頁面對象
            is_personal_todo: 是否為私人待辦
        """
        try:
            properties = page['properties']
            
            # 提取釘釘任務ID
            dingtalk_id_prop = properties.get('釘釘任務ID', {})
            dingtalk_task_id = self.notion.extract_plain_text(
                dingtalk_id_prop.get('rich_text', [])
            )
            
            # 提取上次同步時間
            last_synced_prop = properties.get('上次同步', {})
            last_synced = self.notion.extract_date(last_synced_prop)
            
            # 檢查是否為本次同步產生的變更 (避免循環)
            page_last_edited = page['last_edited_time']
            if last_synced and last_synced >= page_last_edited:
                self.logger.debug(f"頁面 {page['id']} 已同步,跳過")
                return
            
            # 提取任務數據
            task_data = self._extract_task_data_from_notion(properties)
            
            if not dingtalk_task_id:
                # 新增任務到釘釘
                await self._create_dingtalk_task_from_notion(
                    page['id'],
                    task_data,
                    is_personal_todo
                )
            else:
                # 更新釘釘任務
                await self._update_dingtalk_task_from_notion(
                    page['id'],
                    dingtalk_task_id,
                    task_data
                )
                
        except Exception as e:
            self.logger.error(
                f"同步 Notion 頁面 {page['id']} 到釘釘時發生錯誤: {e}",
                exc_info=True
            )
    
    def _extract_task_data_from_notion(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """從 Notion 頁面屬性中提取任務數據"""
        # 提取標題
        title_prop = properties.get('任務名稱', {})
        title = self.notion.extract_plain_text(title_prop.get('title', []))
        
        # 提取截止日期
        due_date_prop = properties.get('到期日', {})
        due_date_str = self.notion.extract_date(due_date_prop)
        due_time = None
        if due_date_str:
            # 轉換為 Unix 時間戳 (毫秒)
            dt = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            due_time = int(dt.timestamp() * 1000)
        
        # 提取優先級
        priority_prop = properties.get('優先級', {})
        priority_name = self.notion.extract_select(priority_prop)
        priority_map = {
            '高': 40,
            '中': 30,
            '低': 20
        }
        priority = priority_map.get(priority_name, 20)
        
        # 提取備註
        notes_prop = properties.get('備註', {})
        notes = self.notion.extract_plain_text(notes_prop.get('rich_text', []))
        
        # 提取狀態
        status_prop = properties.get('狀態', {})
        status = self.notion.extract_status(status_prop)
        done = status in ['已完成', '完成', 'Done']
        
        return {
            'subject': title,
            'due_time': due_time,
            'priority': priority,
            'description': notes,
            'done': done
        }
    
    async def _create_dingtalk_task_from_notion(
        self,
        notion_page_id: str,
        task_data: Dict[str, Any],
        is_personal_todo: bool
    ):
        """從 Notion 創建釘釘任務"""
        try:
            # 創建釘釘任務
            # 注意: 這裡需要根據實際情況設置 executor_ids
            # 對於私人待辦,執行者是自己
            # 對於團隊任務,需要從 Notion 的 Assignee 欄位中提取
            executor_ids = [self.dingtalk.user_union_id]
            
            result = self.dingtalk.create_todo_task(
                subject=task_data['subject'],
                executor_ids=executor_ids,
                due_time=task_data.get('due_time'),
                description=task_data.get('description'),
                priority=task_data.get('priority'),
                source_id=f"notion_{notion_page_id}"
            )
            
            dingtalk_task_id = result.get('id')
            
            # 更新 Notion 頁面,記錄釘釘任務 ID
            self.notion.update_page(
                page_id=notion_page_id,
                properties={
                    "釘釘任務ID": self.notion.build_rich_text_property(dingtalk_task_id),
                    "上次同步": self.notion.build_date_property(
                        datetime.now(timezone.utc).isoformat()
                    )
                }
            )
            
            self.logger.info(
                f"成功從 Notion 創建釘釘任務: {dingtalk_task_id}"
            )
            
        except Exception as e:
            self.logger.error(
                f"從 Notion 頁面 {notion_page_id} 創建釘釘任務時發生錯誤: {e}",
                exc_info=True
            )
    
    async def _update_dingtalk_task_from_notion(
        self,
        notion_page_id: str,
        dingtalk_task_id: str,
        task_data: Dict[str, Any]
    ):
        """從 Notion 更新釘釘任務"""
        try:
            # 更新釘釘任務
            self.dingtalk.update_todo_task(
                task_id=dingtalk_task_id,
                subject=task_data['subject'],
                due_time=task_data.get('due_time'),
                description=task_data.get('description'),
                priority=task_data.get('priority'),
                done=task_data.get('done')
            )
            
            # 更新 Notion 的上次同步時間
            self.notion.update_page(
                page_id=notion_page_id,
                properties={
                    "上次同步": self.notion.build_date_property(
                        datetime.now(timezone.utc).isoformat()
                    )
                }
            )
            
            self.logger.info(
                f"成功從 Notion 更新釘釘任務: {dingtalk_task_id}"
            )
            
        except Exception as e:
            self.logger.error(
                f"從 Notion 頁面 {notion_page_id} 更新釘釘任務 {dingtalk_task_id} 時發生錯誤: {e}",
                exc_info=True
            )



    async def handle_dingtalk_event(self, event: Dict[str, Any]):
        """
        處理釘釘事件
        
        Args:
            event: 釘釘事件對象
        """
        event_type = event.get('EventType')
        
        if event_type == 'todo_task_create':
            await self._handle_task_create_event(event)
        elif event_type == 'todo_task_update':
            await self._handle_task_update_event(event)
        elif event_type == 'todo_task_delete':
            await self._handle_task_delete_event(event)
        else:
            self.logger.warning(f"未知的事件類型: {event_type}")
    
    async def _handle_task_create_event(self, event: Dict[str, Any]):
        """處理待辦任務創建事件"""
        try:
            task_data = event.get('taskData', {})
            task_id = task_data.get('taskId')
            creator_id = task_data.get('creatorId')
            executor_ids = task_data.get('executorIds', [])
            
            # 判斷是「指派給我」還是「我指派的」
            is_assigned_to_me = self.dingtalk.user_union_id in executor_ids
            is_created_by_me = creator_id == self.dingtalk.user_union_id
            
            if is_assigned_to_me and not is_created_by_me:
                # 別人指派給我 -> 私人待辦看板
                await self._sync_dingtalk_to_notion(
                    task_id,
                    task_data,
                    self.notion.personal_todo_db_id
                )
            elif is_created_by_me and not is_assigned_to_me:
                # 我指派給別人 -> 團隊任務追蹤表
                await self._sync_dingtalk_to_notion(
                    task_id,
                    task_data,
                    self.notion.team_task_db_id
                )
            
        except Exception as e:
            self.logger.error(f"處理任務創建事件時發生錯誤: {e}", exc_info=True)
    
    async def _handle_task_update_event(self, event: Dict[str, Any]):
        """處理待辦任務更新事件"""
        try:
            task_data = event.get('taskData', {})
            task_id = task_data.get('taskId')
            
            # 在兩個資料庫中查找對應的頁面
            notion_page = self.notion.find_page_by_dingtalk_id(
                self.notion.personal_todo_db_id,
                task_id
            )
            
            if not notion_page:
                notion_page = self.notion.find_page_by_dingtalk_id(
                    self.notion.team_task_db_id,
                    task_id
                )
            
            if notion_page:
                await self._update_notion_from_dingtalk(
                    notion_page['id'],
                    task_data
                )
            else:
                self.logger.warning(f"找不到對應的 Notion 頁面: 釘釘任務 ID {task_id}")
                
        except Exception as e:
            self.logger.error(f"處理任務更新事件時發生錯誤: {e}", exc_info=True)
    
    async def _handle_task_delete_event(self, event: Dict[str, Any]):
        """處理待辦任務刪除事件"""
        try:
            task_data = event.get('taskData', {})
            task_id = task_data.get('taskId')
            
            # 在兩個資料庫中查找對應的頁面
            notion_page = self.notion.find_page_by_dingtalk_id(
                self.notion.personal_todo_db_id,
                task_id
            )
            
            if not notion_page:
                notion_page = self.notion.find_page_by_dingtalk_id(
                    self.notion.team_task_db_id,
                    task_id
                )
            
            if notion_page:
                # 將 Notion 頁面標記為已刪除 (或直接刪除)
                # 這裡選擇更新狀態而不是刪除,以保留歷史記錄
                self.notion.update_page(
                    page_id=notion_page['id'],
                    properties={
                        "狀態": self.notion.build_status_property("已刪除")
                    }
                )
                self.logger.info(f"已將 Notion 頁面標記為已刪除: {notion_page['id']}")
            
        except Exception as e:
            self.logger.error(f"處理任務刪除事件時發生錯誤: {e}", exc_info=True)
    
    async def _sync_dingtalk_to_notion(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        database_id: str
    ):
        """
        將釘釘任務同步到 Notion
        
        Args:
            task_id: 釘釘任務 ID
            task_data: 釘釘任務數據
            database_id: 目標 Notion 資料庫 ID
        """
        try:
            # 檢查是否已存在
            existing_page = self.notion.find_page_by_dingtalk_id(database_id, task_id)
            
            if existing_page:
                # 更新現有頁面
                await self._update_notion_from_dingtalk(
                    existing_page['id'],
                    task_data
                )
            else:
                # 創建新頁面
                properties = self._build_notion_properties_from_dingtalk(task_data, task_id)
                self.notion.create_page(database_id, properties)
                self.logger.info(f"成功從釘釘創建 Notion 頁面: 任務 ID {task_id}")
                
        except Exception as e:
            self.logger.error(
                f"同步釘釘任務 {task_id} 到 Notion 時發生錯誤: {e}",
                exc_info=True
            )
    
    async def _update_notion_from_dingtalk(
        self,
        notion_page_id: str,
        task_data: Dict[str, Any]
    ):
        """從釘釘更新 Notion 頁面"""
        try:
            properties = self._build_notion_properties_from_dingtalk(
                task_data,
                task_data.get('taskId')
            )
            
            self.notion.update_page(notion_page_id, properties)
            self.logger.info(f"成功從釘釘更新 Notion 頁面: {notion_page_id}")
            
        except Exception as e:
            self.logger.error(
                f"從釘釘更新 Notion 頁面 {notion_page_id} 時發生錯誤: {e}",
                exc_info=True
            )
    
    def _build_notion_properties_from_dingtalk(
        self,
        task_data: Dict[str, Any],
        task_id: str
    ) -> Dict[str, Any]:
        """從釘釘任務數據構建 Notion 屬性"""
        properties = {}
        
        # 標題
        subject = task_data.get('subject', '未命名任務')
        properties['任務名稱'] = self.notion.build_title_property(subject)
        
        # 釘釘任務 ID
        properties['釘釘任務ID'] = self.notion.build_rich_text_property(task_id)
        
        # 截止日期
        due_time = task_data.get('dueTime')
        if due_time:
            # 轉換毫秒時間戳為 ISO 8601 格式
            dt = datetime.fromtimestamp(due_time / 1000, tz=timezone.utc)
            properties['到期日'] = self.notion.build_date_property(dt.isoformat())
        
        # 優先級
        priority = task_data.get('priority')
        priority_map = {
            40: '緊急',
            30: '較高',
            20: '普通',
            10: '較低'
        }
        if priority:
            properties['優先級'] = self.notion.build_select_property(
                priority_map.get(priority, '普通')
            )
        
        # 備註
        description = task_data.get('description')
        if description:
            properties['備註'] = self.notion.build_rich_text_property(description)
        
        # 狀態
        done = task_data.get('done', False)
        status = 'Done' if done else 'To Do'
        properties['狀態'] = self.notion.build_status_property(status)
        
        # 最後同步時間
        properties['上次同步'] = self.notion.build_date_property(
            datetime.now(timezone.utc).isoformat()
        )
        
        return properties


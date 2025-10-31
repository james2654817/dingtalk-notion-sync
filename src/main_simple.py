#!/usr/bin/env python3
"""
釘釘-Notion 雙向同步系統主程式 (簡化版 - 僅輪詢模式)
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
from src.logger import setup_logger


async def main():
    """主函數"""
    # 載入配置
    config = load_config()
    
    # 設置日誌
    logger = setup_logger(config)
    logger.info("=" * 60)
    logger.info("釘釘-Notion 雙向同步系統啟動 (輪詢模式)")
    logger.info("=" * 60)
    
    try:
        # 初始化客戶端
        logger.info("正在初始化釘釘客戶端...")
        dingtalk_client = DingTalkClient(config['dingtalk'])
        
        logger.info("正在初始化 Notion 客戶端...")
        notion_client = NotionClient(config['notion'])
        
        # 初始化同步服務
        logger.info("正在初始化同步服務...")
        sync_service = SyncService(
            dingtalk_client=dingtalk_client,
            notion_client=notion_client,
            config=config
        )
        
        # 啟動雙向輪詢服務
        logger.info("正在啟動雙向輪詢服務...")
        logger.info(f"輪詢間隔: {config['polling']['interval']} 秒")
        logger.info("系統已成功啟動,正在運行中...")
        logger.info("提示: 按 Ctrl+C 停止服務")
        
        # 同時執行 Notion 和釘釘輪詢
        await asyncio.gather(
            sync_service.start_notion_polling(),
            sync_service.start_dingtalk_polling()
        )
        
    except KeyboardInterrupt:
        logger.info("收到停止信號,正在關閉服務...")
    except Exception as e:
        logger.error(f"系統運行時發生錯誤: {e}", exc_info=True)
        raise
    finally:
        logger.info("系統已停止")


if __name__ == "__main__":
    asyncio.run(main())


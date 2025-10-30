"""
日誌配置模組
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Dict, Any


def setup_logger(config: Dict[str, Any]) -> logging.Logger:
    """
    設置日誌系統
    
    Args:
        config: 配置字典
        
    Returns:
        配置好的 logger 實例
    """
    log_config = config['logging']
    
    # 創建 logger
    logger = logging.getLogger('dingtalk_notion_sync')
    logger.setLevel(getattr(logging, log_config['level'].upper()))
    
    # 清除現有的 handlers
    logger.handlers.clear()
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台處理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件處理器 (帶輪轉)
    log_file = Path(config['logging']['file'])
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_config.get('max_bytes', 10485760),  # 預設 10MB
        backupCount=log_config.get('backup_count', 5),
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_config['level'].upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


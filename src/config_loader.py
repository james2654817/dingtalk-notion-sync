"""
配置文件載入模組
支持從環境變數或 YAML 文件加載配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    載入配置
    優先從環境變數讀取,若不存在則從 YAML 文件讀取
    
    Args:
        config_path: 配置文件路徑,若為 None 則使用預設路徑
        
    Returns:
        配置字典
    """
    # 嘗試從環境變數加載
    config = _load_from_env()
    
    if config:
        print("✅ 從環境變數加載配置")
        return config
    
    # 否則從文件加載
    print("📁 從配置文件加載配置")
    return _load_from_file(config_path)


def _load_from_env() -> Dict[str, Any]:
    """從環境變數加載配置"""
    # 檢查必要的環境變數是否存在
    required_env_vars = [
        'DINGTALK_APP_KEY',
        'DINGTALK_APP_SECRET',
        'DINGTALK_UNION_ID',
        'NOTION_TOKEN',
        'NOTION_PERSONAL_TODO_DATABASE_ID'
    ]
    
    # 如果任何必要變數不存在,返回 None
    if not all(os.getenv(var) for var in required_env_vars):
        return None
    
    config = {
        'dingtalk': {
            'app_key': os.getenv('DINGTALK_APP_KEY'),
            'app_secret': os.getenv('DINGTALK_APP_SECRET'),
            'union_id': os.getenv('DINGTALK_UNION_ID')
        },
        'notion': {
            'token': os.getenv('NOTION_TOKEN'),
            'personal_todo_database_id': os.getenv('NOTION_PERSONAL_TODO_DATABASE_ID'),
            'team_task_database_id': os.getenv('NOTION_TEAM_TASK_DATABASE_ID', '')
        },
        'webhook': {
            'enabled': os.getenv('WEBHOOK_ENABLED', 'false').lower() == 'true',
            'port': int(os.getenv('WEBHOOK_PORT', '8000')),
            'aes_key': os.getenv('WEBHOOK_AES_KEY', ''),
            'token': os.getenv('WEBHOOK_TOKEN', '')
        },
        'polling': {
            'enabled': os.getenv('POLLING_ENABLED', 'true').lower() == 'true',
            'interval': int(os.getenv('POLLING_INTERVAL', '30'))
        },
        'logging': {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'file': os.getenv('LOG_FILE', 'logs/sync.log')
        }
    }
    
    return config


def _load_from_file(config_path: str = None) -> Dict[str, Any]:
    """從 YAML 文件加載配置"""
    if config_path is None:
        # 預設配置文件路徑
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "config.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}\n"
            f"請複製 config.yaml.example 為 config.yaml 並填入您的配置\n"
            f"或設置環境變數"
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 驗證必要配置
    _validate_config(config)
    
    return config


def _validate_config(config: Dict[str, Any]):
    """驗證配置的完整性"""
    required_keys = {
        'dingtalk': ['app_key', 'app_secret', 'union_id'],
        'notion': ['token', 'personal_todo_database_id'],
        'logging': ['level', 'file']
    }
    
    for section, keys in required_keys.items():
        if section not in config:
            raise ValueError(f"配置缺少 '{section}' 區塊")
        
        for key in keys:
            if key not in config[section]:
                raise ValueError(f"配置 '{section}' 區塊缺少 '{key}' 欄位")
    
    # 檢查是否有未填寫的佔位符
    def check_placeholder(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_placeholder(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, str):
            if obj.startswith("your_") or obj.startswith("${"):
                raise ValueError(
                    f"配置項 '{path}' 尚未填寫,請替換預設值 '{obj}'"
                )
    
    check_placeholder(config)

"""
配置文件載入模組
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    載入配置文件
    
    Args:
        config_path: 配置文件路徑,若為 None 則使用預設路徑
        
    Returns:
        配置字典
    """
    if config_path is None:
        # 預設配置文件路徑
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "config.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}\n"
            f"請複製 config.yaml.example 為 config.yaml 並填入您的配置"
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
        'notion': ['token', 'personal_todo_database_id', 'team_task_database_id'],
        'logging': ['level', 'file']
    }
    
    for section, keys in required_keys.items():
        if section not in config:
            raise ValueError(f"配置文件缺少 '{section}' 區塊")
        
        for key in keys:
            if key not in config[section]:
                raise ValueError(f"配置文件 '{section}' 區塊缺少 '{key}' 欄位")
    
    # 檢查是否有未填寫的佔位符
    def check_placeholder(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_placeholder(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, str):
            if obj.startswith("your_"):
                raise ValueError(
                    f"配置項 '{path}' 尚未填寫,請替換預設值 '{obj}'"
                )
    
    check_placeholder(config)


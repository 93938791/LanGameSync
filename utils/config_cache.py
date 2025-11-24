"""
配置缓存管理
保存和加载用户配置
"""
import json
from pathlib import Path
from config import Config
from utils.logger import Logger

logger = Logger().get_logger("ConfigCache")

class ConfigCache:
    """配置缓存管理器"""
    
    CACHE_FILE = Config.CONFIG_DIR / "user_config.json"
    
    @classmethod
    def save(cls, config_data):
        """
        保存配置
        
        Args:
            config_data: 配置字典
        """
        try:
            Config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(cls.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logger.info("配置已保存")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    @classmethod
    def load(cls):
        """
        加载配置
        
        Returns:
            dict: 配置字典，如果不存在返回默认值
        """
        try:
            if cls.CACHE_FILE.exists():
                with open(cls.CACHE_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info("配置已加载")
                return config
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
        
        # 返回默认配置
        return {
            "room_name": "langamesync-network",
            "password": "langamesync-2025",
            "nickname": "",
            "last_folders": []
        }

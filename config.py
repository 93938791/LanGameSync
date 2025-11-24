"""
配置管理模块
"""
import os
import json
from pathlib import Path

class Config:
    """全局配置类"""
    
    # 应用信息
    APP_NAME = "LanGameSync"
    APP_VERSION = "1.0.0"
    
    # 路径配置
    BASE_DIR = Path(__file__).parent
    RESOURCES_DIR = BASE_DIR / "resources"
    CONFIG_DIR = Path.home() / ".langamesync"
    DATA_DIR = CONFIG_DIR / "data"
    LOG_DIR = CONFIG_DIR / "logs"
    LOG_FILE = LOG_DIR / "langamesync.log"
    
    # Syncthing配置
    SYNCTHING_BIN = RESOURCES_DIR / "syncthing.exe"
    
    # 使用主机名作为唯一标识，确保不同设备有不同的配置目录
    import socket
    HOSTNAME = socket.gethostname()
    SYNCTHING_HOME = CONFIG_DIR / "syncthing" / HOSTNAME
    SYNCTHING_API_PORT = 8384
    SYNCTHING_API_KEY = "langamesync-secret-key-12345"
    
    # Easytier配置
    EASYTIER_BIN = RESOURCES_DIR / "easytier-core.exe"
    EASYTIER_CLI = RESOURCES_DIR / "easytier-cli.exe"
    EASYTIER_CONFIG = CONFIG_DIR / "easytier.conf"
    EASYTIER_NETWORK_NAME = "langamesync-network"
    EASYTIER_NETWORK_SECRET = "langamesync-2025"
    # 公共节点（用于NAT穿透，实现跨网络连接）
    EASYTIER_PUBLIC_PEERS = [
        "tcp://public.easytier.cn:11010",
        "udp://public.easytier.cn:11010"
    ]
    
    # 同步配置
    SYNC_FOLDER_ID = "game-sync"
    SYNC_FOLDER_LABEL = "游戏同步目录"
    
    # 用户配置文件
    USER_CONFIG_FILE = CONFIG_DIR / "user_config.json"
    
    @classmethod
    def init_dirs(cls):
        """初始化所有必要目录"""
        for dir_path in [cls.CONFIG_DIR, cls.DATA_DIR, cls.LOG_DIR, cls.SYNCTHING_HOME]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_user_config(cls):
        """加载用户配置"""
        if cls.USER_CONFIG_FILE.exists():
            with open(cls.USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"sync_folders": []}
    
    @classmethod
    def save_user_config(cls, config_data):
        """保存用户配置"""
        with open(cls.USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

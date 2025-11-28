"""
同步控制器
负责协调Syncthing和Easytier，实现自动设备发现和配对
"""
import time
import requests
from config import Config
from utils.logger import Logger
from managers.syncthing_manager import SyncthingManager
from managers.easytier_manager import EasytierManager

logger = Logger().get_logger("SyncController")

class SyncController:
    """同步流程控制器"""
    
    def __init__(self):
        self.syncthing = SyncthingManager()
        self.easytier = EasytierManager()
        self.sync_folders = []
        self.discovered_devices = []
    

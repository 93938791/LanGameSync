"""
Syncthing管理模块
负责Syncthing的启动、配置和API交互
"""
import os
import time
import json
import requests
from pathlib import Path
from config import Config
from utils.logger import Logger
from utils.process_helper import ProcessHelper

logger = Logger().get_logger("SyncthingManager")

class SyncthingManager:
    """Syncthing管理器"""
    
    def __init__(self):
        self.process = None
        self.api_url = f"http://localhost:{Config.SYNCTHING_API_PORT}"
        self.headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
        self.device_id = None
    
    def start(self):
        """启动Syncthing服务"""
        if not Config.SYNCTHING_BIN.exists():
            raise FileNotFoundError(f"Syncthing程序不存在: {Config.SYNCTHING_BIN}")
        
        # 先杀死占用端口的进程
        ProcessHelper.kill_by_port(Config.SYNCTHING_API_PORT)
        
        # 准备环境变量
        env = os.environ.copy()
        env["STHOMEDIR"] = str(Config.SYNCTHING_HOME)
        
        # 启动参数：禁用浏览器、禁用升级检查
        # gui-address=0.0.0.0 表示监听所有网络接口（包括虚拟网卡）
        args = [
            "--no-browser",
            "--no-upgrade",
            f"--gui-address=0.0.0.0:{Config.SYNCTHING_API_PORT}",
            f"--gui-apikey={Config.SYNCTHING_API_KEY}",
            "--home", str(Config.SYNCTHING_HOME)
        ]
        
        # 启动进程
        self.process = ProcessHelper.start_process(
            Config.SYNCTHING_BIN,
            args=args,
            env=env,
            hide_window=True
        )
        
        # 等待API就绪（增加超时时间）
        if not ProcessHelper.wait_for_port(Config.SYNCTHING_API_PORT, timeout=60):
            raise RuntimeError("Syncthing启动超时")
        
        # 等待API完全可用
        time.sleep(3)
        
        # 获取本机设备ID
        self.device_id = self.get_device_id()
        logger.info(f"Syncthing启动成功，设备ID: {self.device_id}")
        
        return True
    
    def stop(self):
        """停止Syncthing服务"""
        if self.process:
            ProcessHelper.kill_process(self.process)
            self.process = None
            logger.info("Syncthing已停止")
    
    def get_device_id(self):
        """获取本机设备ID"""
        try:
            resp = requests.get(f"{self.api_url}/rest/system/status", headers=self.headers, timeout=5)
            resp.raise_for_status()
            return resp.json()["myID"]
        except Exception as e:
            logger.error(f"获取设备ID失败: {e}")
            return None
    
    def get_config(self):
        """获取完整配置"""
        try:
            resp = requests.get(f"{self.api_url}/rest/config", headers=self.headers, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return None
    
    def set_config(self, config):
        """设置完整配置"""
        try:
            resp = requests.put(
                f"{self.api_url}/rest/config",
                headers=self.headers,
                json=config,
                timeout=10
            )
            resp.raise_for_status()
            logger.info("配置已更新")
            return True
        except Exception as e:
            logger.error(f"设置配置失败: {e}")
            return False
    
    def add_device(self, device_id, device_name=None):
        """添加远程设备"""
        config = self.get_config()
        if not config:
            return False
        
        # 检查设备是否已存在
        for device in config.get("devices", []):
            if device["deviceID"] == device_id:
                logger.info(f"设备已存在: {device_id}")
                return True
        
        # 添加新设备
        new_device = {
            "deviceID": device_id,
            "name": device_name or device_id[:7],
            "addresses": ["dynamic"],
            "compression": "metadata",
            "introducer": False,
            "skipIntroductionRemovals": False,
            "paused": False
        }
        
        config["devices"].append(new_device)
        
        return self.set_config(config)
    
    def set_device_name(self, device_id, name):
        """
        设置设备名称/昵称
        
        Args:
            device_id: 设备ID
            name: 设备名称/昵称
        """
        try:
            config = self.get_config()
            if not config:
                return False
            
            # 查找并更新设备名称
            for device in config.get('devices', []):
                if device['deviceID'] == device_id:
                    device['name'] = name
                    logger.info(f"已设置设备 {device_id[:7]}... 的名称为: {name}")
                    return self.set_config(config)
            
            logger.warning(f"未找到设备: {device_id}")
            return False
        except Exception as e:
            logger.error(f"设置设备名称失败: {e}")
            return False
    
    def get_device_name(self, device_id):
        """
        获取设备名称/昵称
        
        Args:
            device_id: 设备ID
            
        Returns:
            str: 设备名称，如果未设置则返回空字符串
        """
        try:
            config = self.get_config()
            if not config:
                return ''
            
            for device in config.get('devices', []):
                if device['deviceID'] == device_id:
                    return device.get('name', '')
            
            return ''
        except Exception as e:
            logger.error(f"获取设备名称失败: {e}")
            return ''
    
    def add_folder(self, folder_path, folder_id=None, folder_label=None, devices=None):
        """
        添加同步文件夹
        
        Args:
            folder_path: 本地文件夹路径
            folder_id: 文件夹ID（默认使用配置的ID）
            folder_label: 文件夹标签
            devices: 共享设备ID列表
        """
        folder_path = Path(folder_path)
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建同步目录: {folder_path}")
        
        config = self.get_config()
        if not config:
            return False
        
        folder_id = folder_id or Config.SYNC_FOLDER_ID
        folder_label = folder_label or Config.SYNC_FOLDER_LABEL
        
        # 检查文件夹是否已存在
        for folder in config.get("folders", []):
            if folder["id"] == folder_id:
                logger.info(f"文件夹已存在: {folder_id}")
                # 更新路径和设备
                folder["path"] = str(folder_path)
                if devices:
                    folder["devices"] = [{"deviceID": dev_id} for dev_id in devices]
                return self.set_config(config)
        
        # 创建新文件夹
        new_folder = {
            "id": folder_id,
            "label": folder_label,
            "path": str(folder_path),
            "type": "sendreceive",
            "devices": [{"deviceID": dev_id} for dev_id in (devices or [])],
            "rescanIntervalS": 60,
            "fsWatcherEnabled": True,
            "fsWatcherDelayS": 10,
            "ignorePerms": False,
            "autoNormalize": True,
            "minDiskFree": {"value": 1, "unit": "%"},
            "versioning": {"type": "", "params": {}},
            "copiers": 0,
            "pullerMaxPendingKiB": 0,
            "hashers": 0,
            "order": "random",
            "ignoreDelete": False,
            "scanProgressIntervalS": 0,
            "pullerPauseS": 0,
            "maxConflicts": 10,
            "disableSparseFiles": False,
            "disableTempIndexes": False,
            "paused": False,
            "weakHashThresholdPct": 25,
            "markerName": ".stfolder"
        }
        
        config["folders"].append(new_folder)
        
        return self.set_config(config)
    
    def get_connections(self):
        """获取连接状态"""
        try:
            resp = requests.get(f"{self.api_url}/rest/system/connections", headers=self.headers, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"获取连接状态失败: {e}")
            return None
    
    def get_folder_status(self, folder_id=None):
        """获取文件夹同步状态"""
        folder_id = folder_id or Config.SYNC_FOLDER_ID
        try:
            resp = requests.get(
                f"{self.api_url}/rest/db/status",
                params={"folder": folder_id},
                headers=self.headers,
                timeout=5
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"获取文件夹状态失败: {e}")
            return None
    
    def get_completion(self, device_id, folder_id=None):
        """获取同步完成度"""
        folder_id = folder_id or Config.SYNC_FOLDER_ID
        try:
            resp = requests.get(
                f"{self.api_url}/rest/db/completion",
                params={"device": device_id, "folder": folder_id},
                headers=self.headers,
                timeout=5
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"获取同步完成度失败: {e}")
            return None
    
    def is_syncing(self):
        """检查是否正在同步"""
        status = self.get_folder_status()
        if status:
            return status.get("state") in ["syncing", "scanning"]
        return False
    
    def get_sync_progress(self):
        """获取同步进度信息"""
        status = self.get_folder_status()
        if not status:
            return None
        
        state = status.get("state", "unknown")
        global_bytes = status.get("globalBytes", 0)
        in_sync_bytes = status.get("inSyncBytes", 0)
        
        if global_bytes > 0:
            progress = (in_sync_bytes / global_bytes) * 100
        else:
            progress = 100
        
        return {
            "state": state,
            "progress": progress,
            "globalBytes": global_bytes,
            "inSyncBytes": in_sync_bytes
        }

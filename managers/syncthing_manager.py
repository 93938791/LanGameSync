"""Syncthing管理模块
负责Syncthing的启动、配置和API交互
"""
import os
import time
import json
import requests
import threading
from pathlib import Path
from config import Config
from utils.logger import Logger
from utils.process_helper import ProcessHelper

logger = Logger().get_logger("SyncthingManager")

class SyncthingManager:
    """定义Syncthing事件的回调类型"""
    
    def __init__(self):
        self.process = None
        self.api_url = f"http://localhost:{Config.SYNCTHING_API_PORT}"
        self.headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
        self.device_id = None
        self.event_thread = None
        self.event_running = False
        self.event_callbacks = []  # 事件回调列表
    
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
        
        # 启动事件监听
        self.start_event_listener()
        
        return True
    
    def stop(self):
        """停止Syncthing服务"""
        # 停止事件监听
        self.stop_event_listener()
        
        # 先尝试通过API优雅地关闭Syncthing
        try:
            logger.info("尝试通过API关闭Syncthing...")
            resp = requests.post(
                f"{self.api_url}/rest/system/shutdown",
                headers=self.headers,
                timeout=5
            )
            if resp.status_code == 200:
                logger.info("Syncthing API关闭请求已发送")
                # 等待进程结束
                import time
                time.sleep(2)
        except Exception as e:
            logger.warning(f"API关闭失败，将强制结束进程: {e}")
        
        # 强制结束进程
        if self.process:
            ProcessHelper.kill_process(self.process)
            self.process = None
        
        # 杀死所有占用端口的进程（确保彻底清理）
        ProcessHelper.kill_by_port(Config.SYNCTHING_API_PORT)
        
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
    
    def api_request(self, endpoint, method="GET", data=None):
        """通用API请求方法"""
        try:
            url = f"{self.api_url}{endpoint}"
            if method == "GET":
                resp = requests.get(url, headers=self.headers, timeout=5)
            elif method == "POST":
                resp = requests.post(url, headers=self.headers, json=data, timeout=5)
            elif method == "PUT":
                resp = requests.put(url, headers=self.headers, json=data, timeout=5)
            else:
                return None
            
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.debug(f"API请求失败 {endpoint}: {e}")
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
    
    def set_config(self, config, async_mode=False):
        """设置完整配置
        
        Args:
            config: 配置对象
            async_mode: 是否异步执行（避免阻塞主程序）
        """
        def _do_set_config():
            try:
                resp = requests.put(
                    f"{self.api_url}/rest/config",
                    headers=self.headers,
                    json=config,
                    timeout=30  # 增加超时时间
                )
                resp.raise_for_status()
                logger.info("配置已更新")
                return True
            except Exception as e:
                logger.error(f"设置配置失败: {e}")
                return False
        
        if async_mode:
            # 异步执行，避免阻塞主程序
            thread = threading.Thread(target=_do_set_config, daemon=True)
            thread.start()
            logger.info("配置更新已提交到后台线程")
            return True
        else:
            return _do_set_config()
    
    def add_device(self, device_id, device_name=None, async_mode=True):
        """添加远程设备
        
        Args:
            device_id: 设备ID
            device_name: 设备名称
            async_mode: 是否异步执行（默认True，避免阻塞主程序）
            
        Returns:
            bool: True-新增成功, False-失败, None-设备已存在
        """
        config = self.get_config()
        if not config:
            return False
        
        # 检查设备是否已存在
        for device in config.get("devices", []):
            if device["deviceID"] == device_id:
                logger.debug(f"设备已存在: {device_id}")
                return None  # 返回None表示设备已存在，无需重复添加
        
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
        logger.info(f"添加新设备: {device_name or device_id[:7]} ({device_id[:7]}...)")
        
        return self.set_config(config, async_mode=async_mode)
    
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
                    return self.set_config(config, async_mode=True)
            
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
    
    def add_folder(self, folder_path, folder_id=None, folder_label=None, devices=None, watcher_delay=30, paused=True, async_mode=True):
        """
        添加同步文件夹
        
        Args:
            folder_path: 本地文件夹路径
            folder_id: 文件夹ID（默认使用配置的ID）
            folder_label: 文件夹标签
            devices: 共享设备ID列表
            watcher_delay: 文件监控延迟(秒),文件静默这么久后才同步
            paused: 是否暂停同步（默认为True，需要手动启动）
            async_mode: 是否异步执行（默认True，避免阻塞主程序）
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
                # 更新路径、设备、延迟和暂停状态
                folder["path"] = str(folder_path)
                folder["fsWatcherDelayS"] = watcher_delay
                folder["paused"] = paused  # 更新暂停状态
                if devices:
                    folder["devices"] = [{"deviceID": dev_id} for dev_id in devices]
                logger.info(f"更新文件夹: 延迟={watcher_delay}秒, 暂停={paused}")
                return self.set_config(config, async_mode=async_mode)
        
        # 创建新文件夹
        new_folder = {
            "id": folder_id,
            "label": folder_label,
            "path": str(folder_path),
            "type": "sendreceive",
            "devices": [{"deviceID": dev_id} for dev_id in (devices or [])],
            "rescanIntervalS": 60,
            "fsWatcherEnabled": True,
            "fsWatcherDelayS": watcher_delay,  # 懒同步延迟
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
            "paused": paused,  # 使用参数控制是否暂停
            "weakHashThresholdPct": 25,
            "markerName": ".stfolder"
        }
        
        logger.info(f"创建同步文件夹: {folder_id}, 监控延迟: {watcher_delay}秒, 暂停状态: {paused}")
        config["folders"].append(new_folder)
        
        return self.set_config(config, async_mode=async_mode)
    
    def setup_sync_folder(self, folder_id, folder_path, folder_label, watcher_delay=30):
        """
        配置同步文件夹(包含所有已连接设备)
        
        Args:
            folder_id: 文件夹ID
            folder_path: 本地文件夹路径
            folder_label: 文件夹标签
            watcher_delay: 文件监控延迟(秒)
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取所有已知设备(从配置中)
            config = self.get_config()
            if not config:
                logger.error("无法获取Syncthing配置")
                return False
            
            # 获取所有设备ID(除了本机)
            device_ids = []
            for device in config.get('devices', []):
                dev_id = device.get('deviceID')
                if dev_id and dev_id != self.device_id:
                    device_ids.append(dev_id)
            
            logger.info(f"找到 {len(device_ids)} 个远程设备,准备添加到同步文件夹")
            
            # 添加文件夹(带延迟参数，默认暂停)
            result = self.add_folder(
                folder_path=folder_path,
                folder_id=folder_id,
                folder_label=folder_label,
                devices=device_ids,
                watcher_delay=watcher_delay,
                paused=True  # 默认暂停，需要手动启动
            )
            
            if result:
                logger.info(f"同步文件夹配置成功: {folder_id}, 设备数: {len(device_ids)}, 延迟: {watcher_delay}秒")
            else:
                logger.error("同步文件夹配置失败")
            
            return result
        except Exception as e:
            logger.error(f"配置同步文件夹失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def add_device_to_folder(self, folder_id, device_id):
        """
        添加设备到文件夹
        
        Args:
            folder_id: 文件夹ID
            device_id: 设备ID
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.get_config()
            if not config:
                return False
            
            # 查找文件夹
            for folder in config.get('folders', []):
                if folder['id'] == folder_id:
                    # 检查设备是否已存在
                    existing_devices = folder.get('devices', [])
                    for dev in existing_devices:
                        if dev['deviceID'] == device_id:
                            logger.info(f"设备已在文件夹中: {device_id[:7]}")
                            return True
                    
                    # 添加设备
                    existing_devices.append({'deviceID': device_id})
                    folder['devices'] = existing_devices
                    logger.info(f"已添加设备 {device_id[:7]}... 到文件夹 {folder_id}")
                    return self.set_config(config, async_mode=True)
            
            logger.warning(f"未找到文件夹: {folder_id}")
            return False
        except Exception as e:
            logger.error(f"添加设备到文件夹失败: {e}")
            return False
    
    def resume_folder(self, folder_id):
        """
        恢复文件夹同步
        
        Args:
            folder_id: 文件夹ID
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.get_config()
            if not config:
                return False
            
            # 查找文件夹
            for folder in config.get('folders', []):
                if folder['id'] == folder_id:
                    folder['paused'] = False
                    logger.info(f"已恢复文件夹同步: {folder_id}")
                    return self.set_config(config, async_mode=True)
            
            logger.warning(f"未找到文件夹: {folder_id}")
            return False
        except Exception as e:
            logger.error(f"恢复文件夹同步失败: {e}")
            return False
    
    def pause_folder(self, folder_id):
        """
        暂停文件夹同步
        
        Args:
            folder_id: 文件夹ID
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.get_config()
            if not config:
                return False
            
            # 查找文件夹
            for folder in config.get('folders', []):
                if folder['id'] == folder_id:
                    folder['paused'] = True
                    logger.info(f"已暂停文件夹同步: {folder_id}")
                    return self.set_config(config, async_mode=True)
            
            logger.warning(f"未找到文件夹: {folder_id}")
            return False
        except Exception as e:
            logger.error(f"暂停文件夹同步失败: {e}")
            return False
    
    def remove_folder(self, folder_id):
        """
        移除同步文件夹
        
        Args:
            folder_id: 文件夹ID
            
        Returns:
            bool: 是否成功
        """
        try:
            config = self.get_config()
            if not config:
                return False
            
            # 查找并移除文件夹
            folders = config.get('folders', [])
            for i, folder in enumerate(folders):
                if folder['id'] == folder_id:
                    folders.pop(i)
                    logger.info(f"已移除文件夹: {folder_id}")
                    return self.set_config(config, async_mode=True)
            
            logger.warning(f"未找到文件夹: {folder_id}")
            return False
        except Exception as e:
            logger.error(f"移除文件夹失败: {e}")
            return False
    
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
    
    def register_event_callback(self, callback):
        """注册事件回调函数"""
        if callback not in self.event_callbacks:
            self.event_callbacks.append(callback)
            logger.info(f"注册事件回调: {callback.__name__}")
    
    def unregister_event_callback(self, callback):
        """取消注册事件回调函数"""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
            logger.info(f"取消注册事件回调: {callback.__name__}")
    
    def start_event_listener(self):
        """启动事件监听线程"""
        if self.event_running:
            logger.warning("事件监听已在运行")
            return
        
        self.event_running = True
        self.event_thread = threading.Thread(target=self._event_listener_loop, daemon=True)
        self.event_thread.start()
        logger.info("事件监听已启动")
    
    def stop_event_listener(self):
        """停止事件监听线程"""
        if not self.event_running:
            return
        
        self.event_running = False
        if self.event_thread:
            self.event_thread.join(timeout=2)
            self.event_thread = None
        logger.info("事件监听已停止")
    
    def _event_listener_loop(self):
        """事件监听循环"""
        last_event_id = 0
        
        while self.event_running:
            try:
                # 调用Syncthing的事件API (long polling)
                resp = requests.get(
                    f"{self.api_url}/rest/events",
                    params={"since": last_event_id},
                    headers=self.headers,
                    timeout=60  # 60秒超时
                )
                resp.raise_for_status()
                
                events = resp.json()
                for event in events:
                    event_id = event.get('id', 0)
                    event_type = event.get('type', '')
                    event_data = event.get('data', {})
                    
                    # 更新last_event_id
                    if event_id > last_event_id:
                        last_event_id = event_id
                    
                    # 关注文件下载完成事件
                    if event_type in ['ItemFinished', 'FolderSummary', 'DownloadProgress']:
                        logger.debug(f"Syncthing事件: {event_type}")
                        # 调用所有注册的回调
                        for callback in self.event_callbacks:
                            try:
                                callback(event_type, event_data)
                            except Exception as e:
                                logger.error(f"事件回调执行失败: {e}")
                
            except requests.exceptions.Timeout:
                # 超时是正常的，long polling会在没有事件时超时
                continue
            except Exception as e:
                if self.event_running:
                    logger.debug(f"事件监听错误: {e}")
                    time.sleep(1)  # 错误后等待一秒再重试
        
        logger.info("事件监听循环退出")

"""Syncthing管理模块
负责Syncthing的启动、配置和API交互
"""
import os
import time
import json
import requests
import threading
import xml.etree.ElementTree as ET
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
        # Syncthing v2.0+ 不再支持 --listen-address，监听地址通过配置文件管理
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
        
        # 禁用本地发现和全局发现，强制只使用EasyTier虚拟IP
        self._disable_discovery()
        
        # 配置监听地址（确保监听所有接口）
        self._configure_listen_address()
        
        # 启用所有设备的自动接受共享文件夹（多客户端同步必需）
        self._enable_auto_accept_folders()
        
        # 启动事件监听
        self.start_event_listener()
        
        return True
    
    def stop(self):
        """停止Syncthing服务（彻底清理所有进程）"""
        # 停止事件监听
        self.stop_event_listener()
        
        # 先尝试通过API优雅地关闭Syncthing
        try:
            logger.info("尝试通过API关闭Syncthing...")
            resp = requests.post(
                f"{self.api_url}/rest/system/shutdown",
                headers=self.headers,
                timeout=2
            )
            if resp.status_code == 200:
                logger.info("✅ Syncthing API关闭请求已发送")
                time.sleep(1)  # 等待优雅关闭
        except Exception as e:
            logger.warning(f"API关闭失败，将强制结束进程: {e}")
        
        # 强制结束当前进程
        if self.process:
            try:
                ProcessHelper.kill_process(self.process, timeout=3)
            except Exception as e:
                logger.warning(f"结束进程失败: {e}")
            self.process = None
        
        # 杀死所有占用端口的进程
        ProcessHelper.kill_by_port(Config.SYNCTHING_API_PORT)
        
        # 彻底清理所有Syncthing相关进程
        self._kill_all_syncthing_processes()
        
        logger.info("✅ Syncthing已彻底停止")
    
    def _kill_all_syncthing_processes(self):
        """彻底清理所有Syncthing相关进程"""
        try:
            import psutil
            syncthing_names = ['syncthing.exe', 'syncthing']
            killed_count = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info.get('name', '').lower()
                    proc_exe = proc.info.get('exe', '')
                    
                    # 检查进程名
                    is_syncthing = False
                    for name in syncthing_names:
                        if name.lower() in proc_name:
                            is_syncthing = True
                            break
                    
                    # 检查可执行文件路径
                    if not is_syncthing and proc_exe:
                        exe_name = os.path.basename(proc_exe).lower()
                        for name in syncthing_names:
                            if name.lower() in exe_name:
                                is_syncthing = True
                                break
                    
                    if is_syncthing:
                        logger.info(f"发现Syncthing进程: {proc_name} (PID: {proc.info['pid']})，正在清理...")
                        try:
                            proc.terminate()
                            proc.wait(timeout=2)
                            killed_count += 1
                            logger.info(f"✅ 已清理进程 PID: {proc.info['pid']}")
                        except psutil.TimeoutExpired:
                            logger.warning(f"进程 {proc.info['pid']} 未响应，强制杀死...")
                            proc.kill()
                            proc.wait(timeout=1)
                            killed_count += 1
                        except psutil.NoSuchProcess:
                            pass
                        except Exception as e:
                            logger.warning(f"清理进程 {proc.info['pid']} 失败: {e}")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    logger.debug(f"检查进程失败: {e}")
            
            if killed_count > 0:
                logger.info(f"✅ 共清理了 {killed_count} 个Syncthing进程")
            else:
                logger.debug("未发现残留的Syncthing进程")
                
        except Exception as e:
            logger.error(f"清理Syncthing进程失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_device_id(self):
        """获取本机设备ID"""
        try:
            resp = requests.get(f"{self.api_url}/rest/system/status", headers=self.headers, timeout=5)
            resp.raise_for_status()
            return resp.json()["myID"]
        except Exception as e:
            logger.error(f"获取设备ID失败: {e}")
            return None
    
    def _disable_discovery(self):
        """禁用Syncthing的全局发现和中继，保留本地发现"""
        try:
            config = self.get_config()
            if not config:
                logger.warning("无法获取配置，跳过禁用发现")
                return False
            
            # 修改前记录原始状态
            options = config.get('options', {})
            original_local = options.get('localAnnounceEnabled', True)
            original_global = options.get('globalAnnounceEnabled', True)
            original_relay = options.get('relaysEnabled', True)
            
            # 禁用所有自动发现，强制使用配置的虚拟IP地址
            options['localAnnounceEnabled'] = False  # 禁用本地发现（避免绕过SOCKS5）
            options['globalAnnounceEnabled'] = False  # 禁用全局发现（互联网）
            options['relaysEnabled'] = False  # 禁用中继服务器
            options['natEnabled'] = False  # 禁用NAT穿透
            options['urAccepted'] = -1  # 禁用匿名使用统计
            
            config['options'] = options
            
            # 同步保存配置（等待完成）
            result = self.set_config(config, async_mode=False)
            
            if result:
                logger.info(f"✅ 已配置Syncthing发现：本地发现={original_local}→False, 全局发现={original_global}→False, 中继={original_relay}→False")
                logger.info("🚫 已禁用所有自动发现，强制使用配置的虚拟IP地址")
            else:
                logger.warning("配置发现失败")
            
            return result
        except Exception as e:
            logger.error(f"配置发现失败: {e}")
            return False
    
    def _enable_auto_accept_folders(self):
        """启用所有设备的自动接受共享文件夹（多客户端同步必需）"""
        try:
            config = self.get_config()
            if not config:
                logger.warning("无法获取配置，跳过启用自动接受")
                return False
            
            # 检查所有设备
            devices = config.get('devices', [])
            updated_count = 0
            
            for device in devices:
                if not device.get('autoAcceptFolders', False):
                    device['autoAcceptFolders'] = True
                    updated_count += 1
            
            if updated_count > 0:
                # 同步保存配置
                result = self.set_config(config, async_mode=False)
                if result:
                    logger.info(f"✅ 已启用 {updated_count} 个设备的自动接受共享文件夹")
                    logger.info("🔄 多客户端同步将自动工作")
                    return True
                else:
                    logger.warning("启用自动接受失败")
                    return False
            else:
                logger.info("✅ 所有设备已启用自动接受共享文件夹")
                return True
        except Exception as e:
            logger.error(f"启用自动接受失败: {e}")
            return False
    
    def _configure_listen_address(self):
        """配置监听地址，确保监听所有网络接口（Syncthing v2.0+）"""
        try:
            config = self.get_config()
            if not config:
                logger.warning("无法获取配置，跳过配置监听地址")
                return False
            
            # 检查options.listenAddresses配置
            options = config.get('options', {})
            listen_addresses = options.get('listenAddresses', [])
            
            # 默认监听地址：所有接口的 22000 端口
            default_address = "tcp://0.0.0.0:22000"
            
            # 检查是否已配置
            if default_address not in listen_addresses:
                # 添加默认监听地址
                if not listen_addresses:
                    listen_addresses = [default_address]
                elif listen_addresses[0] != default_address:
                    listen_addresses.insert(0, default_address)
                
                options['listenAddresses'] = listen_addresses
                config['options'] = options
                
                # 保存配置
                result = self.set_config(config, async_mode=False)
                if result:
                    logger.info(f"✅ 已配置监听地址: {default_address}")
                    return True
                else:
                    logger.warning("配置监听地址失败")
                    return False
            else:
                logger.info(f"✅ 监听地址已配置: {listen_addresses}")
                return True
        except Exception as e:
            logger.error(f"配置监听地址失败: {e}")
            return False
    
    def _restart_device_connection(self, device_id):
        """触发Syncthing重新连接指定设备"""
        try:
            # 通过设置设备为暂停再恢复来触发重连
            logger.info(f"触发设备重连: {device_id[:7]}...")
            
            # 获取配置
            config = self.get_config()
            if not config:
                return False
            
            # 找到设备
            for device in config.get('devices', []):
                if device['deviceID'] == device_id:
                    # 先暂停
                    device['paused'] = True
                    self.set_config(config, async_mode=False)
                    
                    # 等待一下
                    import time
                    time.sleep(1)
                    
                    # 再恢复
                    device['paused'] = False
                    self.set_config(config, async_mode=False)
                    
                    logger.info(f"✅ 已触发设备 {device_id[:7]}... 重连")
                    return True
            
            logger.warning(f"未找到设备: {device_id}")
            return False
        except Exception as e:
            logger.error(f"触发设备重连失败: {e}")
            return False
    
    def get_config(self, filter_self=True):
        """获取完整配置
        
        Args:
            filter_self: 是否过滤本机ID（默认True）
        """
        try:
            resp = requests.get(f"{self.api_url}/rest/config", headers=self.headers, timeout=5)
            resp.raise_for_status()
            config = resp.json()
            
            # 关键修复：每次读取配置时自动过滤本机ID
            # 防止 Syncthing 自动添加本机到设备列表
            if config and self.device_id and filter_self:
                # 1. 过滤设备列表中的本机ID
                if 'devices' in config:
                    original_count = len(config['devices'])
                    config['devices'] = [dev for dev in config['devices'] if dev.get('deviceID') != self.device_id]
                    removed = original_count - len(config['devices'])
                    if removed > 0:
                        logger.debug(f"⚠️ get_config中过滤了设备列表中的 {removed} 个本机ID")
                
                # 2. 过滤文件夹设备列表中的本机ID（关键！）
                if 'folders' in config:
                    for folder in config['folders']:
                        if 'devices' in folder:
                            original_count = len(folder['devices'])
                            folder['devices'] = [dev for dev in folder['devices'] if dev.get('deviceID') != self.device_id]
                            removed = original_count - len(folder['devices'])
                            if removed > 0:
                                logger.debug(f"⚠️ 从文件夹 {folder.get('id')} 中过滤了 {removed} 个本机ID")
            
            return config
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
                # 关键修复：每次保存配置前都清理本机ID（防止被重新添加）
                if config and self.device_id:
                    # 1. 清理设备列表
                    if 'devices' in config:
                        original_count = len(config['devices'])
                        config['devices'] = [dev for dev in config['devices'] if dev.get('deviceID') != self.device_id]
                        removed = original_count - len(config['devices'])
                        if removed > 0:
                            logger.warning(f"⚠️ set_config检测到设备列表中有 {removed} 个本机ID（已清理）")
                    
                    # 2. 清理文件夹设备列表
                    if 'folders' in config:
                        for folder in config['folders']:
                            if 'devices' in folder:
                                original_count = len(folder['devices'])
                                folder['devices'] = [dev for dev in folder['devices'] if dev.get('deviceID') != self.device_id]
                                removed = original_count - len(folder['devices'])
                                if removed > 0:
                                    logger.warning(f"⚠️ set_config检测到文件夹 {folder.get('id')} 中有 {removed} 个本机ID（已清理）")
                
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
    
    def add_device(self, device_id, device_name=None, device_address=None, async_mode=True):
        """添加远程设备
        
        Args:
            device_id: 设备ID
            device_name: 设备名称
            device_address: 设备地址（虚拟IP），例如 "10.126.126.2"
            async_mode: 是否异步执行（默认True，避免阻塞主程序）
            
        Returns:
            bool: True-新增成功或更新成功, False-失败, None-设备已存在且无需更新
        """
        # 检查是否是自己的设备ID，不应该添加自己
        if device_id == self.device_id:
            logger.debug(f"跳过添加自己的设备: {device_id[:7]}...")
            return None
        
        config = self.get_config()
        if not config:
            return False
        
        # 检查设备是否已存在
        device_exists = False
        for device in config.get("devices", []):
            if device["deviceID"] == device_id:
                device_exists = True
                logger.debug(f"设备已存在: {device_id}")
                
                # 确保使用虚拟IP地址
                if device_address:
                    tcp_address = f"tcp://{device_address}:22000"
                    current_addresses = device.get("addresses", [])
                    
                    # 检查是否需要更新地址
                    if tcp_address not in current_addresses:
                        device["addresses"] = [tcp_address, "dynamic"]
                        logger.info(f"更新已存在设备地址: {tcp_address}")
                        
                        # 保存配置
                        result = self.set_config(config, async_mode=False)
                        if result:
                            # 触发Syncthing重新连接该设备
                            self._restart_device_connection(device_id)
                        return result
                
                # 设备已存在且配置正确，无需操作
                return None
        
        # 设备不存在，需要添加
        if not device_exists:
            # 使用虚拟IP地址
            addresses = ["dynamic"]  # 默认使用dynamic作为备用
            
            if device_address:
                # 配置虚拟IP地址
                tcp_address = f"tcp://{device_address}:22000"
                addresses = [tcp_address, "dynamic"]  # 虚拟IP优先，dynamic备用
                logger.info(f"使用虚拟IP地址: {tcp_address}")
            else:
                logger.warning("未提供虚拟IP地址，使用dynamic发现")
            
            # 添加新设备
            new_device = {
                "deviceID": device_id,
                "name": device_name or device_id[:7],
                "addresses": addresses,
                "compression": "metadata",
                "introducer": False,
                "skipIntroductionRemovals": False,
                "paused": False,
                # 自动接受共享文件夹（多客户端同步必需）
                "autoAcceptFolders": True
            }
            
            config["devices"].append(new_device)
            logger.info(f"添加新设备: {device_name or device_id[:7]} ({device_id[:7]}...) 地址: {addresses}")
            
            # 输出详细诊断信息
            logger.info(f"✅ 设备配置详情:")
            logger.info(f"   设备ID: {device_id}")
            logger.info(f"   设备名称: {device_name or device_id[:7]}")
            logger.info(f"   虚拟IP: {device_address or 'N/A'}")
            logger.info(f"   连接地址: {addresses}")
            
            return self.set_config(config, async_mode=async_mode)
    
    def add_folder(self, folder_path, folder_id=None, folder_label=None, devices=None, watcher_delay=10, paused=True, async_mode=True):
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
        
        # 创建 .stfolder 标记文件夹（Syncthing 必需）
        stfolder_marker = folder_path / ".stfolder"
        if not stfolder_marker.exists():
            stfolder_marker.mkdir(exist_ok=True)
            logger.info(f"创建 .stfolder 标记文件夹: {stfolder_marker}")
        
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
                    logger.info(f"✅ 更新文件夹设备列表: 共享给 {len(devices)} 个设备: {[dev_id[:7] + '...' for dev_id in devices]}")
                else:
                    logger.warning(f"⚠️ 文件夹 {folder_id} 未共享给任何设备")
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
            "minDiskFree": {"value": 0.5, "unit": "%"},
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
        
        # 输出详细的设备共享信息
        if devices:
            logger.info(f"✅ 创建同步文件夹: {folder_id}, 共享给 {len(devices)} 个设备: {[dev_id[:7] + '...' for dev_id in devices]}")
        else:
            logger.warning(f"⚠️ 创建同步文件夹: {folder_id}, 但未共享给任何设备")
        logger.info(f"文件夹配置: 延迟={watcher_delay}秒, 暂停={paused}")
        config["folders"].append(new_folder)
        
        return self.set_config(config, async_mode=async_mode)
    
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
                    # 确保 .stfolder 标记文件夹存在
                    folder_path = Path(folder.get('path', ''))
                    if folder_path.exists():
                        stfolder_marker = folder_path / ".stfolder"
                        if not stfolder_marker.exists():
                            stfolder_marker.mkdir(exist_ok=True)
                            logger.info(f"创建 .stfolder 标记文件夹: {stfolder_marker}")
                    
                    # 检查是否有共享设备（get_config已自动过滤本机ID）
                    folder_devices = folder.get('devices', [])
                    if not folder_devices:
                        logger.warning(f"⚠️ 文件夹 {folder_id} 未共享给任何设备，无法同步")
                        return False
                    
                    device_ids = [d['deviceID'] for d in folder_devices]
                    logger.info(f"✅ 恢复文件夹同步: {folder_id}, 共享给 {len(device_ids)} 个设备: {[dev_id[:7] + '...' for dev_id in device_ids]}")
                    
                    folder['paused'] = False
                    logger.info(f"已恢复文件夹同步: {folder_id}")
                    # 使用异步模式，避免阻塞主窗口
                    result = self.set_config(config, async_mode=True)
                    
                    return result
            
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
                    # 使用异步模式，避免阻塞主窗口
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
            connections = resp.json()
            return connections
        except Exception as e:
            logger.error(f"获取连接状态失败: {e}")
            return None
    
    def get_traffic_stats(self):
        """
        获取Syncthing流量统计信息
        
        Returns:
            dict: 流量统计信息
                {
                    'tx_speed': 上传速度(bytes/s),
                    'rx_speed': 下载速度(bytes/s)
                }
        """
        try:
            # 获取连接信息，其中包含流量统计
            resp = requests.get(f"{self.api_url}/rest/system/connections", headers=self.headers, timeout=5)
            resp.raise_for_status()
            connections = resp.json()
            
            if not connections or 'connections' not in connections:
                return None
            
            # 计算总的上传和下载速度
            total_tx_speed = 0
            total_rx_speed = 0
            
            for device_id, conn_info in connections.get('connections', {}).items():
                if conn_info.get('connected', False):
                    # 从连接信息中获取流量速度
                    # Syncthing API 的 connections 端点可能不直接提供速度信息
                    # 我们需要从其他端点获取，或者使用连接信息中的其他字段
                    pass
            
            # 尝试从 /rest/stats/device 获取设备统计信息
            try:
                stats_resp = requests.get(f"{self.api_url}/rest/stats/device", headers=self.headers, timeout=5)
                if stats_resp.status_code == 200:
                    stats_data = stats_resp.json()
                    # 解析统计信息（需要根据实际API响应格式调整）
                    # 这里先返回None，等待实际测试后完善
                    pass
            except:
                pass
            
            # 由于Syncthing API可能不直接提供实时速度，我们返回None
            # 让调用方使用EasyTier的统计
            return None
            
        except Exception as e:
            logger.debug(f"获取Syncthing流量统计失败: {e}")
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
    
    def get_remote_device_folders(self, device_ip, device_id=None):
        """
        获取远程设备的文件夹列表
        
        Args:
            device_ip: 远程设备的虚拟IP地址
            device_id: 远程设备的ID（可选，用于验证）
            
        Returns:
            list: 远程设备的文件夹列表，失败返回None
        """
        try:
            headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
            
            # 首先从 system/status 获取设备ID和设备名（这是最可靠的方式）
            remote_device_id = None
            remote_device_name = 'Unknown'
            
            try:
                status_url = f"http://{device_ip}:{Config.SYNCTHING_API_PORT}/rest/system/status"
                logger.debug(f"正在访问远程设备状态API: {status_url}")
                status_resp = requests.get(status_url, headers=headers, timeout=5)
                status_resp.raise_for_status()
                
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    remote_device_id = status_data.get('myID')
                    if remote_device_id:
                        logger.info(f"✅ 从 {device_ip} 的 system/status 获取到设备ID: {remote_device_id[:7]}...")
                    else:
                        logger.error(f"❌ 从 {device_ip} 的 system/status 未找到 myID，响应键: {list(status_data.keys())}")
                else:
                    logger.error(f"❌ 访问 {device_ip} 的 system/status 失败，状态码: {status_resp.status_code}")
            except Exception as e:
                logger.error(f"❌ 从 {device_ip} 的 system/status 获取设备ID失败: {e}")
                import traceback
                logger.error(f"详细错误: {traceback.format_exc()}")
            
            if not remote_device_id:
                logger.error(f"❌ 无法从 {device_ip} 获取设备ID")
                return None
            
            # 验证设备ID（如果提供了）
            if device_id:
                if remote_device_id != device_id:
                    logger.warning(f"设备ID不匹配: 期望 {device_id[:7]}..., 实际 {remote_device_id[:7]}...")
                    return None
            
            # 然后从 config 获取文件夹列表
            config_url = f"http://{device_ip}:{Config.SYNCTHING_API_PORT}/rest/config"
            logger.debug(f"正在访问远程设备配置API: {config_url}")
            resp = requests.get(config_url, headers=headers, timeout=5)
            resp.raise_for_status()
            
            # 检查响应状态
            if resp.status_code != 200:
                logger.error(f"从 {device_ip} 获取配置失败，HTTP状态码: {resp.status_code}")
                return None
            
            remote_config = resp.json()
            
            # 检查配置是否有效
            if not remote_config:
                logger.error(f"从 {device_ip} 获取的配置为空")
                return None
            
            # 尝试从 config 获取设备名（如果存在）
            remote_device_name = remote_config.get('myName', 'Unknown')
            # 如果 config 中没有设备名，使用设备ID的前7位作为显示名
            if remote_device_name == 'Unknown':
                remote_device_name = f"设备 {remote_device_id[:7]}..."
            
            # 获取文件夹列表（只返回未暂停的文件夹，即正在分享的）
            folders = []
            
            # 确保 folders 是列表
            folders_list = remote_config.get('folders', [])
            if not isinstance(folders_list, list):
                logger.error(f"从 {device_ip} 获取的 folders 不是列表类型: {type(folders_list)}")
                return None
            
            for folder in folders_list:
                # 确保 folder 是字典
                if not isinstance(folder, dict):
                    logger.warning(f"跳过无效的文件夹项（不是字典）: {type(folder)}")
                    continue
                
                # 只返回未暂停的文件夹（正在分享的）
                if not folder.get('paused', False):
                    # 检查文件夹是否共享给本机
                    # 注意：远程设备的配置中，文件夹的设备列表包含的是共享给哪些设备
                    # 如果本机在列表中，说明这个文件夹是共享给本机的
                    devices_list = folder.get('devices', [])
                    if not isinstance(devices_list, list):
                        devices_list = []
                    
                    folder_devices = []
                    for d in devices_list:
                        if isinstance(d, dict):
                            device_id = d.get('deviceID')
                            if device_id:
                                folder_devices.append(device_id)
                    
                    # 检查本机是否在设备列表中
                    shared_to_me = False
                    if self.device_id:
                        shared_to_me = self.device_id in folder_devices
                    
                    # 重要：返回所有未暂停的文件夹，不管是否已共享给本机
                    # 因为用户可能想要同步，即使还没有被添加到设备列表
                    # 当用户点击同步时，会自动将本机添加到远程设备的文件夹设备列表中
                    folders.append({
                        'id': folder.get('id'),
                        'label': folder.get('label', folder.get('id')),
                        'path': folder.get('path'),  # 远程设备的路径
                        'device_id': remote_device_id,
                        'device_ip': device_ip,
                        'device_name': remote_device_name,
                        'shared_to_me': shared_to_me  # 是否已共享给本机
                    })
                    logger.debug(f"发现远程设备 {remote_device_name} 的文件夹: {folder.get('id')}, 共享给本机: {shared_to_me}")
            
            if len(folders) > 0:
                logger.info(f"从 {remote_device_name} ({device_ip}) 获取到 {len(folders)} 个文件夹: {[f.get('id') for f in folders]}")
            return folders
        except requests.exceptions.Timeout:
            logger.warning(f"获取远程设备 {device_ip} 的文件夹列表超时")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"获取远程设备 {device_ip} 的文件夹列表HTTP错误: {e}, 状态码: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"无法连接到远程设备 {device_ip} 的Syncthing API: {e}")
            return None
        except Exception as e:
            logger.error(f"获取远程设备文件夹列表失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None
    
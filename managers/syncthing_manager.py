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
from managers.socks5_forwarder import SOCKS5Forwarder

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
        self.socks5_forwarder = SOCKS5Forwarder()  # SOCKS5 端口转发器
        self.device_forward_ports = {}  # {device_id: local_port} 设备ID到本地转发端口的映射
        self.next_forward_port = 23001  # 下一个可用的转发端口
    
    def start(self):
        """启动Syncthing服务"""
        if not Config.SYNCTHING_BIN.exists():
            raise FileNotFoundError(f"Syncthing程序不存在: {Config.SYNCTHING_BIN}")
        
        # 先杀死占用端口的进程
        ProcessHelper.kill_by_port(Config.SYNCTHING_API_PORT)
        
        # 准备环境变量
        env = os.environ.copy()
        env["STHOMEDIR"] = str(Config.SYNCTHING_HOME)
        
        # 无TUN模式下，配置Syncthing使用SOCKS5代理进行出站连接
        # 这样Syncthing主动连接其他设备时也可以通过SOCKS5访问虚拟IP
        # 注意：Syncthing使用Go语言，优先识别小写环境变量
        proxy_url = f"socks5://127.0.0.1:{Config.EASYTIER_SOCKS5_PORT}"
        env["all_proxy"] = proxy_url
        env["ALL_PROXY"] = proxy_url  # 也设置大写版本，确保兼容
        # 禁止回退到直接连接，确保所有连接都通过SOCKS5代理
        env["ALL_PROXY_NO_FALLBACK"] = "1"
        logger.info(f"✅ 配置Syncthing环境变量:")
        logger.info(f"   all_proxy / ALL_PROXY = {proxy_url}")
        logger.info(f"   ALL_PROXY_NO_FALLBACK = 1")
        
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
        """停止Syncthing服务"""
        # 停止所有端口转发
        try:
            self.socks5_forwarder.stop_all()
        except Exception as e:
            logger.warning(f"停止端口转发失败: {e}")
        
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
                logger.info("🚫 已禁用所有自动发现，强制使用配置的虚拟IP地址（通过SOCKS5）")
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
            # 注意：在无TUN模式下，监听0.0.0.0可以被EasyTier接收
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
                
                # 无TUN模式下，确保使用虚拟IP地址(通过SOCKS5代理)
                if device_address:
                    tcp_address = f"tcp://{device_address}:22000"
                    current_addresses = device.get("addresses", [])
                    
                    # 检查是否需要更新地址
                    if tcp_address not in current_addresses:
                        device["addresses"] = [tcp_address, "dynamic"]
                        logger.info(f"更新已存在设备地址(通过SOCKS5): {tcp_address}")
                        
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
            # 无TUN模式下，使用虚拟IP地址 + Syncthing的SOCKS5代理
            # Syncthing会通过环境变量 all_proxy 使用SOCKS5访问虚拟IP
            addresses = ["dynamic"]  # 默认使用dynamic作为备用
            
            if device_address:
                # 配置虚拟IP地址，Syncthing会通过SOCKS5代理主动连接
                tcp_address = f"tcp://{device_address}:22000"
                addresses = [tcp_address, "dynamic"]  # 虚拟IP优先，dynamic备用
                logger.info(f"使用虚拟IP地址(通过SOCKS5代理): {tcp_address}")
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
            logger.info(f"🔍 设备配置详情:")
            logger.info(f"   设备ID: {device_id}")
            logger.info(f"   设备名称: {device_name or device_id[:7]}")
            logger.info(f"   虚拟IP: {device_address or 'N/A'}")
            logger.info(f"   连接地址: {addresses}")
            if device_address:
                logger.info(f"   ⚠️ 将通过SOCKS5代理({Config.EASYTIER_SOCKS5_PORT})连接到 {device_address}:22000")
            
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
                    # 检查是否有共享设备（get_config已自动过滤本机ID）
                    folder_devices = folder.get('devices', [])
                    if not folder_devices:
                        logger.warning(f"⚠️ 文件夹 {folder_id} 未共享给任何设备，无法同步")
                        return False
                    
                    device_ids = [d['deviceID'] for d in folder_devices]
                    logger.info(f"✅ 恢复文件夹同步: {folder_id}, 共享给 {len(device_ids)} 个设备: {[dev_id[:7] + '...' for dev_id in device_ids]}")
                    
                    folder['paused'] = False
                    logger.info(f"已恢复文件夹同步: {folder_id}")
                    # 使用同步模式，确保配置立即生效
                    result = self.set_config(config, async_mode=False)
                    
                    # 等待一下然后检查连接状态
                    if result:
                        import time
                        time.sleep(2)  # 等待2秒，让Syncthing尝试连接
                        logger.info("⚠️ 检查设备连接状态...")
                        self.get_connections()  # 输出连接状态
                    
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
                    # 使用同步模式，确保配置立即生效
                    return self.set_config(config, async_mode=False)
            
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
            # 先检查配置中的设备列表
            config = self.get_config()
            if config:
                configured_devices = config.get('devices', [])
                logger.info(f"📋 配置中的设备数: {len(configured_devices)}")
                for dev in configured_devices:
                    dev_id = dev.get('deviceID', '')[:7]
                    dev_name = dev.get('name', 'Unknown')
                    dev_addrs = dev.get('addresses', [])
                    logger.info(f"   配置设备: [{dev_id}...] {dev_name}, 地址: {dev_addrs}")
            
            # 再检查实际连接状态
            resp = requests.get(f"{self.api_url}/rest/system/connections", headers=self.headers, timeout=5)
            resp.raise_for_status()
            connections = resp.json()
            
            # 输出详细连接状态
            logger.info("🔍 Syncthing连接状态:")
            total_devices = connections.get('total', {})
            logger.info(f"   总计: {len(connections.get('connections', {}))} 个设备")
            
            for device_id, conn in connections.get('connections', {}).items():
                # 跳过本机ID
                if device_id == self.device_id:
                    logger.debug(f"   跳过本机设备: [{device_id[:7]}...]")
                    continue
                    
                connected = conn.get('connected', False)
                address = conn.get('address', 'N/A')
                client_version = conn.get('clientVersion', 'N/A')
                logger.info(f"   [{device_id[:7]}...] 连接={connected}, 地址={address}, 版本={client_version}")
            
            return connections
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

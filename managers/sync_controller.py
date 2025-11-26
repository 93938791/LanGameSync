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
    
    def initialize(self):
        """初始化所有服务"""
        try:
            logger.info("=== 初始化同步服务 ===")
            
            # 1. 启动Easytier虚拟网络
            logger.info("步骤 1/2: 启动虚拟网络...")
            self.easytier.start()
            
            # 2. 启动Syncthing
            logger.info("步骤 2/2: 启动Syncthing...")
            self.syncthing.start()
            
            logger.info("=== 初始化完成 ===")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            self.cleanup()
            return False
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理资源...")
        self.syncthing.stop()
        self.easytier.stop()
    
    def discover_and_pair(self, timeout=30):
        """
        自动发现局域网设备并配对
        
        Returns:
            int: 发现的设备数量
        """
        logger.info("=== 开始设备发现与配对 ===")
        
        # 1. 首先添加本机设备
        self.discovered_devices = [{
            "ip": "127.0.0.1",
            "device_id": self.syncthing.device_id,
            "name": "本机",
            "hostname": "localhost"
        }]
        logger.info(f"本机设备: {self.syncthing.device_id}")
        
        # 2. 通过 easytier-cli peer 获取对等设备
        logger.info("通过 Easytier 发现对等设备...")
        import time
        time.sleep(3)  # 等待组网稳定
        
        peers = self.easytier.discover_peers(timeout=5)
        
        # 3. 从 peer 中获取 Syncthing 设备ID
        for peer in peers:
            peer_ip = peer.get('ipv4', '')
            hostname = peer.get('hostname', '')
            
            if not peer_ip:
                continue
            
            # 尝试通过虚拟IP访问 Syncthing
            device_id = self._get_remote_device_id(peer_ip, timeout=2)
            
            if device_id and device_id != self.syncthing.device_id:
                self.discovered_devices.append({
                    "ip": peer_ip,
                    "device_id": device_id,
                    "name": hostname or f"Device-{peer_ip.split('.')[-1]}",
                    "hostname": hostname,
                    "latency": peer.get('latency', '0')
                })
                logger.info(f"发现设备: {hostname} ({peer_ip}) -> {device_id[:7]}...")
        
        # 4. 如果 Easytier 未发现设备，尝试扫描局域网IP（备用方案）
        if len(self.discovered_devices) == 1:  # 只有本机
            logger.info("未通过 Easytier 发现设备，尝试扫描局域网...")
            local_ips = self._scan_local_network()
            
            for ip in local_ips:
                if ip == "127.0.0.1":
                    continue
                
                device_id = self._get_remote_device_id(ip, timeout=2)
                if device_id and device_id != self.syncthing.device_id:
                    # 检查是否已存在
                    if not any(d['device_id'] == device_id for d in self.discovered_devices):
                        self.discovered_devices.append({
                            "ip": ip,
                            "device_id": device_id,
                            "name": f"Device-{ip.split('.')[-1]}",
                            "hostname": ip
                        })
                        logger.info(f"通过IP扫描发现设备 {ip} -> {device_id[:7]}...")
        
        # 5. 将所有设备（除了本机）添加到 Syncthing
        for device in self.discovered_devices:
            if device["device_id"] != self.syncthing.device_id:
                # 传递虚拟IP地址，使Syncthing可以通过虚拟网络连接
                self.syncthing.add_device(
                    device_id=device["device_id"],
                    device_name=device["name"],
                    device_address=device.get("ip")  # 传递虚拟IP
                )
        
        remote_count = len(self.discovered_devices) - 1  # 除去本机
        logger.info(f"=== 配对完成，本机 + {remote_count} 台远程设备 ===")
        return len(self.discovered_devices)
    
    def _scan_local_network(self):
        """
        扫描局域网，查找运行 Syncthing 的设备
        
        Returns:
            list: IP 地址列表
        """
        import socket
        
        # 获取本机 IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "192.168.1.1"
        
        # 提取 IP 段前缀
        ip_prefix = '.'.join(local_ip.split('.')[:-1])
        logger.info(f"扫描 IP 段: {ip_prefix}.0/24")
        
        # 扫描常用 IP（优化扫描范围）
        target_ips = []
        
        # 优先扫描常见的路由器分配的 IP
        common_ranges = [1, 2, 100, 101, 102, 103, 104, 105, 150, 200, 254]
        for i in common_ranges:
            target_ips.append(f"{ip_prefix}.{i}")
        
        return target_ips
    
    def _get_remote_device_id(self, peer_ip, timeout=5):
        """
        从远程设备获取Syncthing设备ID（通过SOCKS5代理，无TUN模式）
        
        Args:
            peer_ip: 对等设备的虚拟IP
            timeout: 超时时间
        
        Returns:
            str: 设备ID，失败返回None
        """
        try:
            # 无TUN模式下，直接通过SOCKS5代理访问（不使用ping）
            # 设置代理（用于无TUN模式下主动访问）
            proxies = {
                'http': 'socks5://127.0.0.1:1080',
                'https': 'socks5://127.0.0.1:1080'
            }
            
            url = f"http://{peer_ip}:{Config.SYNCTHING_API_PORT}/rest/system/status"
            headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
            
            logger.info(f"通过SOCKS5代理访问: {url}")
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            resp.raise_for_status()
            
            device_id = resp.json()["myID"]
            logger.info(f"从 {peer_ip} 获取到设备ID: {device_id[:7]}...")
            return device_id
            
        except requests.exceptions.ProxyError as e:
            logger.warning(f"SOCKS5代理连接失败（{peer_ip}）: {e}")
            return None
        except requests.exceptions.Timeout:
            logger.warning(f"连接到 {peer_ip} 超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"无法从 {peer_ip} 获取设备ID: {e}")
            return None
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            logger.error(f"获取远程设备ID失败: {e}")
            return None
    
    def setup_sync_folder(self, folder_path):
        """
        配置同步文件夹
        
        Args:
            folder_path: 本地文件夹路径
        """
        logger.info(f"配置同步文件夹: {folder_path}")
        
        # 获取所有已发现设备的ID
        device_ids = [dev["device_id"] for dev in self.discovered_devices]
        
        # 添加文件夹到Syncthing，并共享给所有设备
        success = self.syncthing.add_folder(
            folder_path=folder_path,
            devices=device_ids
        )
        
        if success:
            self.sync_folders.append(folder_path)
            logger.info(f"同步文件夹配置成功，共享给 {len(device_ids)} 台设备")
        else:
            logger.error("同步文件夹配置失败")
        
        return success
    
    def start_sync(self, folder_paths):
        """
        开始同步流程
        
        Args:
            folder_paths: 要同步的文件夹路径列表
        
        Returns:
            dict: 同步状态信息
        """
        logger.info("=== 开始同步流程 ===")
        
        # 1. 发现并配对设备
        device_count = self.discover_and_pair()
        
        # 即使没有发现其他设备，也继续（至少有本机）
        logger.info(f"总计 {device_count} 台设备（包含本机）")
        
        # 2. 配置同步文件夹
        for folder_path in folder_paths:
            self.setup_sync_folder(folder_path)
        
        # 3. 等待同步开始
        time.sleep(2)
        
        return {
            "success": True,
            "device_count": device_count,
            "folders": self.sync_folders
        }
    
    def get_sync_status(self):
        """
        获取当前同步状态
        
        Returns:
            dict: 状态信息
        """
        # 获取连接状态
        connections = self.syncthing.get_connections()
        connected_count = 0
        
        if connections and "connections" in connections:
            for dev_id, conn_info in connections["connections"].items():
                if conn_info.get("connected"):
                    connected_count += 1
        
        # 获取同步进度
        progress_info = self.syncthing.get_sync_progress()
        
        state = "idle"
        progress = 100
        
        if progress_info:
            state = progress_info["state"]
            progress = progress_info["progress"]
        
        return {
            "total_devices": len(self.discovered_devices),
            "connected_devices": connected_count,
            "sync_state": state,
            "sync_progress": progress,
            "is_syncing": self.syncthing.is_syncing()
        }
    
    def get_device_list(self):
        """获取已发现的设备列表"""
        return self.discovered_devices

"""
Easytier管理模块
负责Easytier的启动和设备发现
"""
import json
import time
import subprocess
import sys
from pathlib import Path
from config import Config
from utils.logger import Logger
from utils.process_helper import ProcessHelper

logger = Logger().get_logger("EasytierManager")

class EasytierManager:
    """Easytier管理器"""
    
    def __init__(self):
        self.process = None
        self.virtual_ip = None
        self.peer_ips = []
    
    def start(self, custom_peers=None, network_name=None, network_secret=None):
        """启动Easytier虚拟网络
        
        Args:
            custom_peers: 自定义节点列表，如果为None则使用默认公共节点，如果为[]则不使用任何节点
            network_name: 网络名称，如果为None则使用配置文件中的名称
            network_secret: 网络密码，如果为None则使用配置文件中的密码
        """
        if not Config.EASYTIER_BIN.exists():
            raise FileNotFoundError(f"Easytier程序不存在: {Config.EASYTIER_BIN}")
        
        # 使用传入的参数或默认配置
        net_name = network_name if network_name else Config.EASYTIER_NETWORK_NAME
        net_secret = network_secret if network_secret else Config.EASYTIER_NETWORK_SECRET
        
        # 处理节点列表
        if custom_peers is None:
            # None 表示使用默认公共节点
            peers_to_use = Config.EASYTIER_PUBLIC_PEERS
        elif custom_peers == []:
            # 空列表表示不使用任何节点
            peers_to_use = []
        else:
            peers_to_use = custom_peers
        
        args = [
            "--no-tun",
            "--socks5", "1080",
            "--rpc-portal", "127.0.0.1:15888",  # 显式指定 RPC 端口，供 easytier-cli 连接
            "-d",
            "--network-name", net_name,
            "--network-secret", net_secret
        ]
        
        # 添加节点
        if isinstance(peers_to_use, str):
            # 如果是单个字符串，按逗号分割
            peers_list = [p.strip() for p in peers_to_use.split(',') if p.strip()]
        else:
            peers_list = list(peers_to_use) if peers_to_use else []
        
        for peer in peers_list:
            args.extend(["-p", peer])
        
        if peers_list:
            logger.info(f"启动Easytier虚拟网络（使用节点：{len(peers_list)}个）...")
        else:
            logger.info("启动Easytier虚拟网络（不使用节点，局域网模式）...")
        
        # 启动进程
        self.process = ProcessHelper.start_process(
            Config.EASYTIER_BIN,
            args=args,
            hide_window=True
        )
        
        # 等待虚拟网络初始化并分配IP
        logger.info("等待虚拟IP分配...")
        max_retries = 10
        for i in range(max_retries):
            time.sleep(2)
            self.virtual_ip = self._get_virtual_ip()
            if self.virtual_ip and self.virtual_ip not in ["waiting...", "unknown"]:
                logger.info(f"虚拟IP分配成功: {self.virtual_ip}")
                break
            logger.info(f"第{i+1}/{max_retries}次尝试，当前状态: {self.virtual_ip}")
        
        # 检查虚拟IP是否分配成功
        if self.virtual_ip in ["waiting...", "unknown", None]:
            logger.error(f"虚拟IP分配失败，当前状态: {self.virtual_ip}")
            # 停止进程
            self.stop()
            return False
        
        logger.info(f"Easytier启动成功，虚拟IP: {self.virtual_ip}")
        
        return True
    
    def start_with_peer(self, peer, network_name, network_secret):
        """使用自定义节点启动
        
        Args:
            peer: 节点地址
            network_name: 网络名称
            network_secret: 网络密码
        """
        return self.start(
            custom_peers=[peer] if peer else None,
            network_name=network_name,
            network_secret=network_secret
        )
    
    def stop(self):
        """停止Easytier服务"""
        if self.process:
            ProcessHelper.kill_process(self.process)
            self.process = None
            logger.info("Easytier已停止")
    
    def _get_virtual_ip(self):
        """获取本机虚拟IP（通过easytier-cli查询）"""
        try:
            # 通过 easytier-cli peer 命令查看本机信息
            if not Config.EASYTIER_CLI.exists():
                logger.warning(f"easytier-cli 不存在: {Config.EASYTIER_CLI}")
                return "unknown"
            
            # 需要隐藏窗口的startupinfo
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = 0x08000000  # CREATE_NO_WINDOW
            
            result = subprocess.run(
                [str(Config.EASYTIER_CLI), "peer"],
                capture_output=True,
                text=True,
                timeout=5,
                encoding='utf-8',
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            if result.returncode != 0:
                logger.warning(f"easytier-cli peer 执行失败: {result.stderr}")
                logger.debug(f"stderr 内容: {result.stderr}")
                logger.debug(f"stdout 内容: {result.stdout}")
                return "unknown"
            
            # 输出原始数据用于调试
            logger.debug(f"peer 命令输出:\n{result.stdout}")
            
            # 解析输出，找到标记为 Local 的行，其中有本机IP
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                logger.debug(f"第{i+1}行: {line}")
                if 'Local' in line and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    logger.info(f"Local行分割结果 ({len(parts)}列): {parts}")
                    
                    # 尝试从所有列中查找IPv4地址（排除IPv6）
                    for idx, part in enumerate(parts):
                        # IPv4特征：包含点、包含斜杠、不包含冒号、有3个点
                        if (part and 
                            '.' in part and 
                            '/' in part and 
                            ':' not in part and  # 排除IPv6
                            part.count('.') == 3):  # IPv4必须有3个点
                            # 找到了IPv4地址
                            clean_ip = part.split('/')[0]
                            logger.info(f"在第{idx+1}列找到虚拟IP: {clean_ip}")
                            return clean_ip
            
            # 如果没有找到，说明还没分配IP
            logger.info("尚未分配虚拟IP，等待DHCP...")
            return "waiting..."
            
        except Exception as e:
            logger.warning(f"获取虚拟IP失败: {e}")
            return "unknown"
    
    def discover_peers(self, timeout=10):
        """
        发现局域网内的对等设备（通过 easytier-cli peer 命令）
        
        Returns:
            list: 对等设备信息列表
        """
        try:
            # 调用 easytier-cli peer 获取peer列表
            if not Config.EASYTIER_CLI.exists():
                logger.warning(f"easytier-cli 不存在: {Config.EASYTIER_CLI}")
                return []
            
            # 需要隐藏窗口的startupinfo
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = 0x08000000  # CREATE_NO_WINDOW
            
            result = subprocess.run(
                [str(Config.EASYTIER_CLI), "peer"],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            if result.returncode != 0:
                logger.warning(f"easytier-cli peer 执行失败: {result.stderr}")
                return []
            
            # 解析输出
            peers = self._parse_peer_output(result.stdout)
            
            self.peer_ips = [peer['ipv4'] for peer in peers if 'ipv4' in peer]
            
            return peers
            
        except subprocess.TimeoutExpired:
            logger.warning("获取peer信息超时")
            return []
        except Exception as e:
            logger.error(f"发现设备失败: {e}")
            return []
    
    def _parse_peer_output(self, output):
        """
        解析 easytier-cli peer 的输出
        
        Args:
            output: 命令输出文本
        
        Returns:
            list: peer信息列表
        """
        peers = []
        lines = output.strip().split('\n')
        
        # 查找表格数据行（跳过表头和分隔符）
        in_data = False
        for i, line in enumerate(lines):
            original_line = line
            line = line.strip()
            
            # 跳过空行
            if not line:
                continue
            
            # 识别表头
            if 'ipv4' in line.lower() and 'hostname' in line.lower():
                in_data = True
                continue
            
            # 跳过分隔符行
            if line.startswith('---') or line.startswith('===') or set(line.replace('|', '').strip()) == {'-'}:
                continue
            
            # 解析数据行（必须包含 | 分隔符）
            if in_data and '|' in line:
                parts = [p.strip() for p in original_line.split('|')]
                
                # 至少要有足够的列，且第一列（ipv4）包含IP地址
                if len(parts) >= 3:
                    ipv4 = parts[1].strip() if len(parts) > 1 else ''  # 第2列是ipv4
                    hostname = parts[2].strip() if len(parts) > 2 else ''  # 第3列是hostname
                    cost = parts[3].strip() if len(parts) > 3 else ''  # 第4列是cost(Local/p2p)
                    latency = parts[4].strip() if len(parts) > 4 else '0'  # 第5列是latency
                    
                    # 只处理有效的IPv4地址（格式：xxx.xxx.xxx.xxx/xx），且排除本机（cost=Local）
                    # IPv4地址特征：包含3个点、包含斜杠、不包含冒号（排除IPv6）
                    if (ipv4 and 
                        '.' in ipv4 and 
                        '/' in ipv4 and 
                        ':' not in ipv4 and  # 排除IPv6地址（IPv6包含冒号）
                        ipv4.count('.') == 3 and  # IPv4地址必须有3个点
                        cost != 'Local'):
                        # 去掉子网掩码
                        ipv4_clean = ipv4.split('/')[0]
                        
                        peer_info = {
                            'ipv4': ipv4_clean,
                            'hostname': hostname,
                            'latency': latency,
                            'connected': True
                        }
                        peers.append(peer_info)
        
        return peers
    
    def get_peer_count(self):
        """获取已连接的对等设备数量"""
        return len(self.peer_ips)
    
    def wait_for_peers(self, min_count=1, timeout=30):
        """
        等待至少N台对等设备上线
        
        Args:
            min_count: 最少设备数量
            timeout: 超时时间（秒）
        
        Returns:
            bool: 是否满足条件
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            peers = self.discover_peers(timeout=3)
            if len(peers) >= min_count:
                logger.info(f"已发现足够的设备: {len(peers)}/{min_count}")
                return True
            time.sleep(2)
        
        logger.warning(f"等待设备超时，当前仅 {len(self.peer_ips)} 台")
        return False

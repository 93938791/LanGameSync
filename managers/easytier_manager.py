"""
Easytier管理模块
负责Easytier的启动和设备发现
"""
import json
import time
import subprocess
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
    
    def start(self):
        """启动Easytier虚拟网络"""
        if not Config.EASYTIER_BIN.exists():
            raise FileNotFoundError(f"Easytier程序不存在: {Config.EASYTIER_BIN}")
        
        # Easytier启动参数（按照官方文档）
        # --no-tun: 无TUN模式，不需要管理员权限
        # --socks5: 启用SOCKS5代理服务器，格式为 --socks5 端口号
        # -d: DHCP模式，自动分配虚拟IP
        # --network-name: 网络名称（所有设备必须相同）
        # --network-secret: 网络密钥（所有设备必须相同）
        # -p: 公共节点，用于NAT穿透和中继
        args = [
            "--no-tun",  # 无TUN模式，免ROOT权限
            "--socks5", "1080",  # 启用SOCKS5代理，监听1080端口
            "-d",  # DHCP自动分配IP
            "--network-name", Config.EASYTIER_NETWORK_NAME,
            "--network-secret", Config.EASYTIER_NETWORK_SECRET
        ]
        
        # 添加公共节点（实现跨网络连接）
        for peer in Config.EASYTIER_PUBLIC_PEERS:
            args.extend(["-p", peer])
        
        logger.info(f"启动Easytier虚拟网络（使用公共节点：{len(Config.EASYTIER_PUBLIC_PEERS)}个）...")
        
        # 启动进程
        self.process = ProcessHelper.start_process(
            Config.EASYTIER_BIN,
            args=args,
            hide_window=True
        )
        
        # 等待虚拟网络初始化并分配IP（增加等待时间和重试）
        logger.info("等待虚拟IP分配...")
        max_retries = 10
        for i in range(max_retries):
            time.sleep(2)  # 每次等待2秒
            self.virtual_ip = self._get_virtual_ip()
            if self.virtual_ip and self.virtual_ip not in ["waiting...", "unknown"]:
                logger.info(f"虚拟IP分配成功: {self.virtual_ip}")
                break
            logger.info(f"第{i+1}/{max_retries}次尝试，当前状态: {self.virtual_ip}")
        
        if self.virtual_ip in ["waiting...", "unknown"]:
            logger.warning("虚拟IP分配超时，但继续运行")
        
        logger.info(f"Easytier启动成功，虚拟IP: {self.virtual_ip}")
        
        return True
    
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
            
            result = subprocess.run(
                [str(Config.EASYTIER_CLI), "peer"],
                capture_output=True,
                text=True,
                timeout=5,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                logger.warning(f"easytier-cli peer 执行失败")
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
                    
                    if len(parts) > 1:
                        ip = parts[1].strip()  # 第2列是ipv4
                        logger.info(f"提取到的IP字段: '{ip}'")
                        
                        if ip and '.' in ip and '/' in ip:
                            # 去掉子网掩码
                            clean_ip = ip.split('/')[0]
                            logger.info(f"获取到本机虚拟IP: {clean_ip}")
                            return clean_ip
                        else:
                            logger.info(f"IP字段为空或格式不对: '{ip}'")
            
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
            
            result = subprocess.run(
                [str(Config.EASYTIER_CLI), "peer"],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
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
                    latency = parts[4].strip() if len(parts) > 4 else '0'  # 第5列是latency
                    
                    # 只处理有IP地址的行（过滤本机Local和公共服务器）
                    if ipv4 and '.' in ipv4 and '/' in ipv4:
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

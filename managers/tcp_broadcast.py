"""
TCP广播通信管理器
用于客户端间消息广播
"""
import json
import socket
import threading
from utils.logger import Logger

logger = Logger().get_logger("TCPBroadcast")


class TCPBroadcast:
    """TCP广播消息管理器"""
    
    def __init__(self, easytier_manager=None):
        self.server_sock = None  # TCP服务器socket
        self.connected = False
        self.broadcast_port = 9999
        self.callbacks = []  # 消息回调列表
        self.listen_thread = None
        self.running = False
        self.easytier_manager = easytier_manager  # EasyTier管理器引用
        
    def connect(self, broker_host="127.0.0.1", broker_port=1883, room_name="default"):
        """
        启动TCP广播监听
        
        Args:
            broker_host: 忽略(兼容参数)
            broker_port: 广播端口(默认9999)
            room_name: 忽略(兼容参数)
        """
        try:
            self.broadcast_port = broker_port if broker_port != 1883 else 9999
            
            # 创建TCP服务器socket
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind(('0.0.0.0', self.broadcast_port))
            self.server_sock.listen(5)
            self.server_sock.settimeout(1.0)  # 1秒超时
            logger.info(f"TCP监听端口: {self.broadcast_port}")
            
            # 启动监听线程
            self.running = True
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            
            self.connected = True
            logger.info(f"TCP广播已启动,端口: {self.broadcast_port}")
            return True
            
        except Exception as e:
            logger.error(f"TCP广播启动失败: {e}")
            return False
    
    def disconnect(self):
        """断开TCP连接"""
        self.running = False
        
        if self.server_sock:
            self.server_sock.close()
            self.server_sock = None
        
        self.connected = False
        logger.info("TCP广播已关闭")
    
    def publish(self, message_type, data):
        """
        广播消息（使用TCP直连）
        
        Args:
            message_type: 消息类型 (game_starting, server_ready, etc.)
            data: 消息数据(dict)
        """
        if not self.connected:
            logger.warning("TCP未连接,无法发送消息")
            return False
        
        try:
            message = {
                "type": message_type,
                "data": data
            }
            
            payload = json.dumps(message, ensure_ascii=False).encode('utf-8')
            # 添加消息长度头（4字节）
            msg_len = len(payload)
            full_message = msg_len.to_bytes(4, 'big') + payload
            
            # 获取EasyTier对等节点列表
            peer_ips = self._get_easytier_peers()
            
            if not peer_ips:
                logger.warning("未找到EasyTier对等节点")
                # 触发UI更新
                for callback in self.callbacks:
                    try:
                        callback(message_type, data, "no_peers", is_send=True)
                    except:
                        pass
                return False
            
            # 向每个对等节点发送TCP消息（直接连接）
            success_count = 0
            for peer_ip in peer_ips:
                try:
                    # 创建普通的TCP socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)  # 3秒超时
                    
                    # 直接连接到对等节点
                    sock.connect((peer_ip, self.broadcast_port))
                    
                    # 发送消息
                    sock.sendall(full_message)
                    sock.close()
                    
                    success_count += 1
                    logger.debug(f"发送TCP消息到 {peer_ip}: {message_type}")
                    
                except Exception as e:
                    logger.warning(f"发送到 {peer_ip} 失败: {e}")
            
            if success_count > 0:
                logger.info(f"TCP广播: {message_type} -> {success_count}/{len(peer_ips)}个节点")
            
            # 触发UI更新（发送消息）
            for callback in self.callbacks:
                try:
                    target_ip = peer_ips[0] if peer_ips else "unknown"
                    callback(message_type, data, target_ip, is_send=True)
                except:
                    pass
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"TCP广播失败: {e}")
            return False
    
    def _get_easytier_peers(self):
        """
        获取EasyTier对等节点的虚拟IP列表
        
        Returns:
            list: 对等节点IP列表
        """
        if not self.easytier_manager:
            return []
        
        try:
            # 获取对等节点列表（使用discover_peers方法）
            peers = self.easytier_manager.discover_peers(timeout=1)
            if not peers:
                return []
            
            peer_ips = []
            for peer in peers:
                # 使用ipv4字段（discover_peers返回的格式）
                virtual_ip = peer.get('ipv4', '')
                if virtual_ip and virtual_ip != '0.0.0.0':
                    peer_ips.append(virtual_ip)
            
            logger.debug(f"获取到 {len(peer_ips)} 个EasyTier对等节点: {peer_ips}")
            return peer_ips
            
        except Exception as e:
            logger.error(f"获取EasyTier对等节点失败: {e}")
            return []
    
    def register_callback(self, callback):
        """注册消息回调函数"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            logger.info(f"注册UDP回调: {callback.__name__}")
    
    def unregister_callback(self, callback):
        """取消注册回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            logger.info(f"取消UDP回调: {callback.__name__}")
    
    def _listen_loop(self):
        """监听循环"""
        logger.info("启动TCP监听线程")
        
        while self.running:
            try:
                # 接受TCP连接
                try:
                    client_sock, addr = self.server_sock.accept()
                except socket.timeout:
                    # 超时是正常的，继续
                    continue
                
                # 在新线程中处理客户端连接
                threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True
                ).start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"TCP监听失败: {e}")
        
        logger.info("TCP监听线程已退出")
    
    def _handle_client(self, client_sock, addr):
        """处理客户端连接"""
        try:
            # 读取消息长度（4字节）
            length_data = client_sock.recv(4)
            if len(length_data) < 4:
                return
            
            msg_len = int.from_bytes(length_data, 'big')
            
            # 读取完整消息
            data = b''
            while len(data) < msg_len:
                chunk = client_sock.recv(min(msg_len - len(data), 4096))
                if not chunk:
                    break
                data += chunk
            
            if len(data) < msg_len:
                logger.warning(f"消息不完整: 期望{msg_len}字节，实际{len(data)}字节")
                return
            
            # 解析JSON
            payload = data.decode('utf-8')
            message = json.loads(payload)
            
            message_type = message.get('type', 'unknown')
            message_data = message.get('data', {})
            
            logger.info(f"TCP收到: {message_type} from {addr[0]}")
            
            # 调用所有注册的回调
            for callback in self.callbacks:
                try:
                    callback(message_type, message_data, addr[0], is_send=False)
                except Exception as e:
                    logger.error(f"TCP回调执行失败: {e}")
            
        except Exception as e:
            logger.error(f"处理客户端消息失败: {e}")
        finally:
            try:
                client_sock.close()
            except:
                pass

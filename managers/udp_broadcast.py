"""
UDP广播通信管理器
用于客户端间消息广播(无需安装任何服务)
"""
import json
import socket
import threading
from utils.logger import Logger

logger = Logger().get_logger("UDPBroadcast")


class UDPBroadcast:
    """UDP广播消息管理器"""
    
    def __init__(self):
        self.sock = None
        self.listen_sock = None
        self.connected = False
        self.broadcast_port = 9999
        self.callbacks = []  # 消息回调列表
        self.listen_thread = None
        self.running = False
        
    def connect(self, broker_host="127.0.0.1", broker_port=1883, room_name="default"):
        """
        启动UDP广播监听
        
        Args:
            broker_host: 忽略(兼容参数)
            broker_port: 广播端口(默认9999)
            room_name: 忽略(兼容参数)
        """
        try:
            self.broadcast_port = broker_port if broker_port != 1883 else 9999
            
            # 创建广播 socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            logger.info(f"UDP广播 socket已创建")
            
            # 创建监听socket
            self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_sock.bind(('', self.broadcast_port))
            self.listen_sock.settimeout(1.0)  # 1秒超时
            logger.info(f"UDP监听端口: {self.broadcast_port}")
            
            # 启动监听线程
            self.running = True
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            
            self.connected = True
            logger.info(f"UDP广播已启动,端口: {self.broadcast_port}")
            return True
            
        except Exception as e:
            logger.error(f"UDP广播启动失败: {e}")
            return False
    
    def disconnect(self):
        """断开UDP连接"""
        self.running = False
        
        if self.sock:
            self.sock.close()
            self.sock = None
        
        if self.listen_sock:
            self.listen_sock.close()
            self.listen_sock = None
        
        self.connected = False
        logger.info("UDP广播已关闭")
    
    def publish(self, message_type, data):
        """
        广播消息
        
        Args:
            message_type: 消息类型 (game_starting, server_ready, etc.)
            data: 消息数据(dict)
        """
        if not self.connected or not self.sock:
            logger.warning("UDP未连接,无法发送消息")
            return False
        
        try:
            message = {
                "type": message_type,
                "data": data
            }
            
            payload = json.dumps(message, ensure_ascii=False).encode('utf-8')
            
            # 广播到全网
            self.sock.sendto(payload, ('255.255.255.255', self.broadcast_port))
            logger.info(f"UDP广播: {message_type}")
            
            # 触发UI更新（发送消息）
            for callback in self.callbacks:
                try:
                    callback(message_type, data, "255.255.255.255", is_send=True)
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"UDP广播失败: {e}")
            return False
    
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
        logger.info("启动UDP监听线程")
        
        while self.running:
            try:
                # 接收数据
                data, addr = self.listen_sock.recvfrom(4096)
                
                # 解析JSON
                payload = data.decode('utf-8')
                message = json.loads(payload)
                
                message_type = message.get('type', 'unknown')
                message_data = message.get('data', {})
                
                logger.info(f"UDP收到: {message_type} from {addr[0]}")
                
                # 调用所有注册的回调
                for callback in self.callbacks:
                    try:
                        callback(message_type, message_data, addr[0], is_send=False)
                    except Exception as e:
                        logger.error(f"UDP回调执行失败: {e}")
                        
            except socket.timeout:
                # 超时是正常的,继续
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"UDP监听失败: {e}")
        
        logger.info("UDP监听线程已退出")

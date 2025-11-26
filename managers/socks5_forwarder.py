"""
SOCKS5 端口转发服务
用于将本地 TCP 端口通过 SOCKS5 代理转发到远程地址
解决 Syncthing 在无 TUN 模式下无法直接访问虚拟 IP 的问题
"""
import socket
import threading
import socks
from utils.logger import Logger
from config import Config

logger = Logger().get_logger("SOCKS5Forwarder")


class SOCKS5Forwarder:
    """SOCKS5 端口转发器"""
    
    def __init__(self, socks5_host="127.0.0.1", socks5_port=1080):
        """
        初始化 SOCKS5 转发器
        
        Args:
            socks5_host: SOCKS5 代理地址
            socks5_port: SOCKS5 代理端口
        """
        self.socks5_host = socks5_host
        self.socks5_port = socks5_port
        self.forwarders = {}  # {local_port: thread}
        self.running = {}  # {local_port: bool}
    
    def start_forward(self, local_port, remote_ip, remote_port=22000):
        """
        启动端口转发
        
        Args:
            local_port: 本地监听端口
            remote_ip: 远程虚拟 IP
            remote_port: 远程端口（默认 22000）
        
        Returns:
            bool: 是否成功启动
        """
        if local_port in self.forwarders:
            logger.warning(f"端口 {local_port} 已经在转发中")
            return True
        
        try:
            # 创建监听 socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('127.0.0.1', local_port))
            server_socket.listen(5)
            
            # 标记为运行中
            self.running[local_port] = True
            
            # 创建转发线程
            thread = threading.Thread(
                target=self._forward_loop,
                args=(server_socket, local_port, remote_ip, remote_port),
                daemon=True
            )
            thread.start()
            
            self.forwarders[local_port] = {
                'thread': thread,
                'socket': server_socket,
                'remote_ip': remote_ip,
                'remote_port': remote_port
            }
            
            logger.info(f"✅ 启动端口转发: 127.0.0.1:{local_port} → {remote_ip}:{remote_port} (via SOCKS5)")
            return True
            
        except Exception as e:
            logger.error(f"启动端口转发失败 (端口 {local_port}): {e}")
            self.running[local_port] = False
            return False
    
    def _forward_loop(self, server_socket, local_port, remote_ip, remote_port):
        """转发循环（在独立线程中运行）"""
        try:
            while self.running.get(local_port, False):
                try:
                    # 接受客户端连接（超时避免阻塞）
                    server_socket.settimeout(1.0)
                    try:
                        client_socket, client_addr = server_socket.accept()
                    except socket.timeout:
                        continue
                    
                    # 为每个连接创建独立的转发线程
                    thread = threading.Thread(
                        target=self._handle_connection,
                        args=(client_socket, remote_ip, remote_port),
                        daemon=True
                    )
                    thread.start()
                    
                except Exception as e:
                    if self.running.get(local_port, False):
                        logger.error(f"转发循环错误 (端口 {local_port}): {e}")
        finally:
            try:
                server_socket.close()
            except:
                pass
            logger.info(f"端口转发已停止: {local_port}")
    
    def _handle_connection(self, client_socket, remote_ip, remote_port):
        """处理单个连接的转发"""
        remote_socket = None
        try:
            # 创建 SOCKS5 socket
            remote_socket = socks.socksocket()
            remote_socket.set_proxy(
                socks.SOCKS5,
                self.socks5_host,
                self.socks5_port
            )
            
            # 通过 SOCKS5 连接到远程地址
            remote_socket.connect((remote_ip, remote_port))
            
            # 双向转发数据
            self._pipe_sockets(client_socket, remote_socket)
            
        except Exception as e:
            logger.debug(f"连接处理失败 ({remote_ip}:{remote_port}): {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            try:
                if remote_socket:
                    remote_socket.close()
            except:
                pass
    
    def _pipe_sockets(self, sock1, sock2):
        """双向转发两个 socket 的数据"""
        def forward(source, destination):
            try:
                while True:
                    data = source.recv(4096)
                    if not data:
                        break
                    destination.sendall(data)
            except:
                pass
        
        # 创建两个转发线程
        t1 = threading.Thread(target=forward, args=(sock1, sock2), daemon=True)
        t2 = threading.Thread(target=forward, args=(sock2, sock1), daemon=True)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
    
    def stop_forward(self, local_port):
        """停止端口转发"""
        if local_port not in self.forwarders:
            return
        
        # 标记为停止
        self.running[local_port] = False
        
        # 关闭 socket
        try:
            self.forwarders[local_port]['socket'].close()
        except:
            pass
        
        # 等待线程结束（最多 2 秒）
        try:
            self.forwarders[local_port]['thread'].join(timeout=2.0)
        except:
            pass
        
        # 删除记录
        del self.forwarders[local_port]
        del self.running[local_port]
        
        logger.info(f"已停止端口转发: {local_port}")
    
    def stop_all(self):
        """停止所有端口转发"""
        ports = list(self.forwarders.keys())
        for port in ports:
            self.stop_forward(port)
        
        logger.info("已停止所有端口转发")
    
    def get_local_port_for_ip(self, remote_ip):
        """获取某个远程 IP 对应的本地转发端口"""
        for port, info in self.forwarders.items():
            if info['remote_ip'] == remote_ip:
                return port
        return None

"""
网络连接线程
避免阻塞主线程
"""
from PyQt5.QtCore import QThread, pyqtSignal
from utils.logger import Logger

logger = Logger().get_logger("ConnectThread")


class ConnectThread(QThread):
    """网络连接线程（避免阻塞主线程）"""
    connected = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

    def __init__(self, controller, room_name, password, peer=None, use_peer=True):
        super().__init__()
        self.controller = controller
        self.room_name = room_name
        self.password = password
        self.peer = peer
        self.use_peer = use_peer

    def run(self):
        try:
            # 步骤 1: 先启动 EasyTier 分配虚拟 IP
            # 根据是否使用节点来决定连接方式
            if not self.use_peer:
                # 不使用节点，局域网模式
                self.progress.emit(f"正在连接到房间 {self.room_name} (局域网模式)...")
                if not self.controller.easytier.start(custom_peers=[], network_name=self.room_name, network_secret=self.password):
                    self.connected.emit(False, "网络连接失败")
                    return
            elif self.peer:
                # 使用自定义节点
                self.progress.emit(f"正在连接到房间 {self.room_name} (使用自定义节点)...")
                if not self.controller.easytier.start_with_peer(self.peer, self.room_name, self.password):
                    self.connected.emit(False, "网络连接失败")
                    return
            else:
                # 使用默认公共节点
                self.progress.emit(f"正在连接到房间 {self.room_name}...")
                if not self.controller.easytier.start(network_name=self.room_name, network_secret=self.password):
                    self.connected.emit(False, "网络连接失败")
                    return
            
            # 获取虚拟 IP
            virtual_ip = self.controller.easytier.virtual_ip
            logger.info(f"✅ EasyTier 启动成功，虚拟 IP: {virtual_ip}")
            
            # 步骤 2: 在有了虚拟 IP 后再启动 Syncthing
            self.progress.emit("正在启动 Syncthing...")
            if not self.controller.syncthing.start():
                self.connected.emit(False, "Syncthing 启动失败")
                return
            
            logger.info("✅ Syncthing 启动成功")
            
            # 连接成功
            self.connected.emit(True, virtual_ip)
            
        except Exception as e:
            logger.error(f"连接线程异常: {e}")
            self.connected.emit(False, str(e))

"""
设备扫描线程
避免阻塞主线程
"""
from PyQt5.QtCore import QThread, pyqtSignal
from utils.logger import Logger

logger = Logger().get_logger("ScanThread")


class ScanThread(QThread):
    """设备扫描线程（避免阻塞主线程）"""
    peers_found = pyqtSignal(list)  # 发送peer列表
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.running = True
    
    def run(self):
        try:
            if self.running:
                peers = self.controller.easytier.discover_peers(timeout=2)
                if peers:
                    self.peers_found.emit(peers)
        except Exception as e:
            logger.error(f"扫描线程异常: {e}")
    
    def stop(self):
        self.running = False

"""
GUI主窗口 - 美化版
毛玻璃简洁风格
"""
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QListWidget, QMessageBox,
    QProgressBar, QTextEdit, QLineEdit, QMenuBar, QMenu, QAction
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont
from config import Config
from managers.sync_controller import SyncController
from utils.logger import Logger
from utils.config_cache import ConfigCache
from ui.styles import MODERN_STYLE

logger = Logger().get_logger("MainWindow")

class ConnectThread(QThread):
    """网络连接线程（避免阻塞主线程）"""
    connected = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, controller, room_name, password):
        super().__init__()
        self.controller = controller
        self.room_name = room_name
        self.password = password
    
    def run(self):
        try:
            self.progress.emit("正在连接到网络...")
            success = self.controller.easytier.start()
            if success:
                self.connected.emit(True, self.controller.easytier.virtual_ip)
            else:
                self.connected.emit(False, "连接失败")
        except Exception as e:
            self.connected.emit(False, str(e))

class WorkerThread(QThread):
    """后台工作线程"""
    status_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    sync_started = pyqtSignal(dict)
    
    def __init__(self, controller, folders):
        super().__init__()
        self.controller = controller
        self.folders = folders
    
    def run(self):
        """执行同步任务"""
        try:
            self.status_update.emit("正在初始化服务...")
            result = self.controller.start_sync(self.folders)
            
            if result["success"]:
                self.sync_started.emit(result)
            else:
                self.error_occurred.emit(result.get("error", "同步启动失败"))
                
        except Exception as e:
            logger.error(f"同步线程异常: {e}")
            self.error_occurred.emit(f"同步失败: {str(e)}")

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.controller = SyncController()
        self.worker = None
        self.connect_thread = None
        self.sync_folders = []
        
        # 状态跟踪（用于检测变化）
        self.last_sync_state = None
        self.last_progress = -1
        
        # 加载配置
        self.config_data = ConfigCache.load()
        
        self.init_ui()
        self.init_services()
        
        # 应用样式
        self.setStyleSheet(MODERN_STYLE)
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"{Config.APP_NAME} - 局域网游戏文件同步")
        self.setGeometry(100, 100, 700, 600)
        
        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title = QLabel("🎮 局域网游戏文件同步")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 网络配置区域
        network_group = QWidget()
        network_layout = QHBoxLayout()
        network_layout.setSpacing(10)
        
        network_label = QLabel("🔑 房间号:")
        network_label_font = QFont()
        network_label_font.setPointSize(11)
        network_label.setFont(network_label_font)
        network_layout.addWidget(network_label)
        
        from PyQt5.QtWidgets import QLineEdit
        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("输入房间号（默认: langamesync-network）")
        self.room_input.setText("langamesync-network")
        self.room_input.setMinimumHeight(35)
        network_layout.addWidget(self.room_input)
        
        password_label = QLabel("🔒 密码:")
        password_label.setFont(network_label_font)
        network_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("输入密码（默认: langamesync-2025）")
        self.password_input.setText("langamesync-2025")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(35)
        network_layout.addWidget(self.password_input)
        
        self.connect_btn = QPushButton("✅ 连接网络")
        self.connect_btn.setMinimumHeight(35)
        self.connect_btn.setMinimumWidth(120)
        connect_btn_font = QFont()
        connect_btn_font.setPointSize(11)
        connect_btn_font.setBold(True)
        self.connect_btn.setFont(connect_btn_font)
        self.connect_btn.clicked.connect(self.connect_network)
        network_layout.addWidget(self.connect_btn)
        
        network_group.setLayout(network_layout)
        main_layout.addWidget(network_group)
        
        # 同步目录区域
        folder_label = QLabel("同步目录:")
        folder_label_font = QFont()
        folder_label_font.setPointSize(12)
        folder_label.setFont(folder_label_font)
        main_layout.addWidget(folder_label)
        
        # 目录列表
        self.folder_list = QListWidget()
        self.folder_list.setMinimumHeight(120)
        main_layout.addWidget(self.folder_list)
        
        # 目录操作按钮
        folder_btn_layout = QHBoxLayout()
        self.add_folder_btn = QPushButton("➕ 添加目录")
        self.add_folder_btn.setMinimumHeight(40)
        self.add_folder_btn.clicked.connect(self.add_folder)
        
        self.remove_folder_btn = QPushButton("➖ 移除目录")
        self.remove_folder_btn.setMinimumHeight(40)
        self.remove_folder_btn.clicked.connect(self.remove_folder)
        
        folder_btn_layout.addWidget(self.add_folder_btn)
        folder_btn_layout.addWidget(self.remove_folder_btn)
        main_layout.addLayout(folder_btn_layout)
        
        # 同步控制按钮
        self.sync_btn = QPushButton("🚀 开始同步")
        self.sync_btn.setMinimumHeight(50)
        self.sync_btn.setEnabled(False)
        sync_btn_font = QFont()
        sync_btn_font.setPointSize(14)
        sync_btn_font.setBold(True)
        self.sync_btn.setFont(sync_btn_font)
        self.sync_btn.clicked.connect(self.start_sync)
        main_layout.addWidget(self.sync_btn)
        
        # 设备列表区域
        device_label = QLabel("已发现设备:")
        device_label_font = QFont()
        device_label_font.setPointSize(11)
        device_label.setFont(device_label_font)
        main_layout.addWidget(device_label)
        
        self.device_list = QListWidget()
        self.device_list.setMaximumHeight(80)
        self.device_list.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd; padding: 5px;")
        main_layout.addWidget(self.device_list)
        
        # 状态显示区域
        self.status_label = QLabel("状态: 正在初始化...")
        status_font = QFont()
        status_font.setPointSize(11)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #0066cc; padding: 10px;")
        main_layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 日志输出
        log_label = QLabel("运行日志:")
        main_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("background-color: #f5f5f5; font-family: Consolas;")
        main_layout.addWidget(self.log_text)
        
        central_widget.setLayout(main_layout)
        
        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
    
    def init_services(self):
        """初始化后台服务（仅Syncthing）"""
        try:
            self.log("正在初始化Syncthing...")
            
            # 只启动 Syncthing，不启动 Easytier
            Config.init_dirs()
            if self.controller.syncthing.start():
                self.log("Syncthing启动成功")
                self.status_label.setText(f"状态: 就绪，请输入房间号和密码连接网络")
                self.status_label.setStyleSheet("color: #0066cc; padding: 10px;")
                self.connect_btn.setEnabled(True)
            else:
                self.log("Syncthing启动失败")
                self.show_error("初始化失败", "无法启动Syncthing，请重启软件")
        except Exception as e:
            logger.error(f"初始化异常: {e}")
            self.show_error("初始化异常", str(e))
    
    def connect_network(self):
        """连接到网络（启动Easytier）"""
        room_name = self.room_input.text().strip()
        password = self.password_input.text().strip()
        
        if not room_name or not password:
            self.show_info("提示", "请输入房间号和密码")
            return
        
        # 更新配置
        Config.EASYTIER_NETWORK_NAME = room_name
        Config.EASYTIER_NETWORK_SECRET = password
        
        self.connect_btn.setEnabled(False)
        self.room_input.setEnabled(False)
        self.password_input.setEnabled(False)
        
        self.log(f"正在连接到房间: {room_name}...")
        
        try:
            # 启动 Easytier
            if self.controller.easytier.start():
                self.log("网络连接成功！")
                
                # 获取并显示虚拟IP
                virtual_ip = self.controller.easytier.virtual_ip
                self.log(f"🌐 本机虚拟IP: {virtual_ip}")
                
                self.status_label.setText(f"状态: 已连接到房间 '{room_name}' | 虚拟IP: {virtual_ip} | 设备ID: {self.controller.syncthing.device_id[:7]}...")
                self.status_label.setStyleSheet("color: #00aa00; padding: 10px;")
                
                # 添加本机设备
                self.controller.discovered_devices = [{
                    "ip": "127.0.0.1",
                    "device_id": self.controller.syncthing.device_id,
                    "name": "本机",
                    "hostname": "localhost"
                }]
                self.update_device_list()
                
                # 启用功能按钮
                self.add_folder_btn.setEnabled(True)
                
                # 启动后台扫描（基于事件监听的智能扫描）
                self.scan_timer = QTimer()
                self.scan_timer.timeout.connect(self.background_scan_devices)
                
                # 记录上一次的 peer 列表（用于检测变化）
                self.last_peer_ips = set()
                
                # 初始阶段：快速扫描30秒（每5秒一次）
                self.scan_count = 0
                self.scan_timer.start(5000)  # 5秒
                self.log("已启动后台设备监听（初始快速模式：每5秒）")
            else:
                self.log("网络连接失败")
                self.show_error("连接失败", "无法连接到网络，请检查房间号和密码")
                self.connect_btn.setEnabled(True)
                self.room_input.setEnabled(True)
                self.password_input.setEnabled(True)
        except Exception as e:
            logger.error(f"连接网络异常: {e}")
            self.show_error("连接异常", str(e))
            self.connect_btn.setEnabled(True)
            self.room_input.setEnabled(True)
            self.password_input.setEnabled(True)
    
    def add_folder(self):
        """添加同步目录"""
        folder = QFileDialog.getExistingDirectory(self, "选择同步目录")
        if folder:
            folder_path = Path(folder)
            if folder_path not in self.sync_folders:
                self.sync_folders.append(folder_path)
                self.folder_list.addItem(str(folder_path))
                self.log(f"已添加目录: {folder_path}")
                self.sync_btn.setEnabled(True)
            else:
                self.show_info("提示", "该目录已存在")
    
    def remove_folder(self):
        """移除同步目录"""
        current_item = self.folder_list.currentItem()
        if current_item:
            folder_path = Path(current_item.text())
            self.sync_folders.remove(folder_path)
            self.folder_list.takeItem(self.folder_list.row(current_item))
            self.log(f"已移除目录: {folder_path}")
            
            if not self.sync_folders:
                self.sync_btn.setEnabled(False)
    
    def start_sync(self):
        """开始同步"""
        if not self.sync_folders:
            self.show_info("提示", "请先添加同步目录")
            return
        
        self.log("开始同步流程...")
        self.sync_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.remove_folder_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        # 在后台线程执行同步
        self.worker = WorkerThread(self.controller, [str(f) for f in self.sync_folders])
        self.worker.status_update.connect(self.on_status_update)
        self.worker.error_occurred.connect(self.on_sync_error)
        self.worker.sync_started.connect(self.on_sync_started)
        self.worker.start()
    
    def on_status_update(self, message):
        """状态更新回调"""
        self.log(message)
        self.status_label.setText(f"状态: {message}")
    
    def on_sync_error(self, error_msg):
        """同步错误回调"""
        self.log(f"错误: {error_msg}")
        self.progress_bar.setVisible(False)
        self.sync_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.remove_folder_btn.setEnabled(True)
        self.show_error("同步失败", error_msg)
    
    def on_sync_started(self, result):
        """同步开始回调"""
        device_count = result["device_count"]
        self.log(f"同步已启动，发现 {device_count} 台设备")
        
        # 立即更新设备列表
        self.update_device_list()
        
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.status_label.setText(f"状态: 同步中 | 已连接 {device_count} 台设备")
        self.status_label.setStyleSheet("color: #ff6600; padding: 10px;")
        
        # 启动状态更新定时器
        self.status_timer.start(2000)  # 每2秒更新
    
    def update_status(self):
        """更新同步状态（只在状态变化时输出日志）"""
        try:
            status = self.controller.get_sync_status()
            
            connected = status["connected_devices"]
            total = status["total_devices"]
            progress = status["sync_progress"]
            state = status["sync_state"]
            
            # 更新设备列表
            self.update_device_list()
            
            self.progress_bar.setValue(int(progress))
            
            state_text = {
                "idle": "空闲",
                "syncing": "同步中",
                "scanning": "扫描中",
                "sync-preparing": "准备中"
            }.get(state, state)
            
            self.status_label.setText(
                f"状态: {state_text} | 已连接 {connected}/{total} 台设备 | 进度 {progress:.1f}%"
            )
            
            # 检测同步完成（只在状态变化时输出日志）
            if progress >= 100 and state == "idle":
                self.status_label.setText(f"状态: 同步完成 ✓ | 已连接 {connected}/{total} 台设备")
                self.status_label.setStyleSheet("color: #00aa00; padding: 10px;")
                
                # 只在状态从非完成变为完成时输出日志
                if self.last_sync_state != "completed":
                    self.log("同步完成")
                    self.last_sync_state = "completed"
            else:
                # 重置状态
                if self.last_sync_state == "completed":
                    self.last_sync_state = None
                    
        except Exception as e:
            logger.error(f"更新状态失败: {e}")
    
    def update_device_list(self):
        """更新设备列表显示"""
        try:
            devices = self.controller.get_device_list()
            connections = self.controller.syncthing.get_connections()
            
            self.device_list.clear()
            
            if not devices:
                self.device_list.addItem("暂无设备（等待发现中...）")
                return
            
            for device in devices:
                device_id = device["device_id"]
                device_name = device["name"]
                device_ip = device.get("ip", "")
                hostname = device.get("hostname", "")
                latency = device.get("latency", "")
                
                # 检查连接状态
                is_connected = False
                if connections and "connections" in connections:
                    conn_info = connections["connections"].get(device_id, {})
                    is_connected = conn_info.get("connected", False)
                
                # 本机特殊显示
                if device_name == "本机":
                    item_text = f"💻 {device_name} - {device_id[:7]}..."
                else:
                    status_icon = "🟢" if is_connected else "🔴"
                    # 显示: 状态 名称 (IP) 延迟 ms - 设备ID
                    display_name = hostname or device_name
                    latency_text = f" {latency}ms" if latency and latency != '0' else ""
                    item_text = f"{status_icon} {display_name} ({device_ip}){latency_text} - {device_id[:7]}..."
                
                self.device_list.addItem(item_text)
                
        except Exception as e:
            logger.error(f"更新设备列表失败: {e}")
    
    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
        logger.info(message)
    
    def show_info(self, title, message):
        """显示信息对话框"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()
    
    def show_error(self, title, message):
        """显示错误对话框"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()
    
    def background_scan_devices(self):
        """后台监听设备变化（基于事件检测）"""
        try:
            self.scan_count += 1
            
            # 快速监听阶段：前6次（30秒），每5秒一次
            if self.scan_count == 6:
                # 发现设备的数量（排除本机）
                remote_device_count = len([d for d in self.controller.discovered_devices if d.get('name') != '本机'])
                
                if remote_device_count > 0:
                    # 已发现设备，降低检测频率到15秒
                    self.scan_timer.setInterval(15000)
                    self.log(f"💡 已发现 {remote_device_count} 台设备，切换到正常监听（每15秒）")
                else:
                    # 未发现设备，降低检测频率到30秒
                    self.scan_timer.setInterval(30000)
                    self.log("💡 暂无其他设备，切换到低频监听（每30秒）")
            
            # 获取当前 peer 列表
            peers = self.controller.easytier.discover_peers(timeout=2)
            
            if not peers:
                return
            
            # 提取当前所有 peer 的 IP（用于检测变化）
            current_peer_ips = {peer.get('ipv4', '') for peer in peers if peer.get('ipv4')}
            
            # 检测是否有变化（新增或移除）
            new_ips = current_peer_ips - self.last_peer_ips
            removed_ips = self.last_peer_ips - current_peer_ips
            
            # 如果没有变化，直接返回（不做任何处理）
            if not new_ips and not removed_ips:
                return
            
            # 更新记录
            self.last_peer_ips = current_peer_ips
            
            # 处理移除的设备（可选）
            if removed_ips:
                self.log(f"📤 检测到 {len(removed_ips)} 台设备离线")
            
            # 处理新增的设备
            if new_ips:
                self.log(f"📥 检测到 {len(new_ips)} 台新设备上线")
                
                # 排除已添加的设备
                existing_ips = {d.get('ip') for d in self.controller.discovered_devices}
                
                for peer in peers:
                    peer_ip = peer.get('ipv4', '')
                    hostname = peer.get('hostname', '')
                    
                    # 只处理新增且未添加的设备
                    if peer_ip not in new_ips or peer_ip in existing_ips:
                        continue
                    
                    self.log(f"⚡ 正在连接新设备: {hostname} ({peer_ip})")
                    
                    # 获取 Syncthing 设备ID
                    device_id = self.controller._get_remote_device_id(peer_ip, timeout=5)
                    
                    if device_id and device_id != self.controller.syncthing.device_id:
                        # 添加设备
                        self.controller.discovered_devices.append({
                            "ip": peer_ip,
                            "device_id": device_id,
                            "name": hostname or f"Device-{peer_ip.split('.')[-1]}",
                            "hostname": hostname,
                            "latency": peer.get('latency', '0')
                        })
                        
                        self.controller.syncthing.add_device(device_id, hostname or f"Device-{peer_ip.split('.')[-1]}")
                        
                        self.log(f"✅ 成功添加设备: {hostname} ({device_id[:7]}...)")
                        self.update_device_list()
                        
                        # 发现新设备后，如果当前是低频模式，临时提升频率
                        if self.scan_count >= 6 and self.scan_timer.interval() >= 30000:
                            self.scan_timer.setInterval(15000)
                            self.log("💡 发现新设备，临时提升监听频率到每15秒")
                    else:
                        if device_id == self.controller.syncthing.device_id:
                            self.log(f"⚠️ {hostname} 是本机，跳过")
                        else:
                            self.log(f"❌ 无法连接到 {hostname} ({peer_ip}) 的Syncthing")
                        
        except Exception as e:
            logger.error(f"后台监听设备失败: {e}")
    
    def closeEvent(self, event):
        """关闭事件"""
        self.status_timer.stop()
        if hasattr(self, 'scan_timer'):
            self.scan_timer.stop()
        self.controller.cleanup()
        logger.info("应用关闭")
        event.accept()

def run_app():
    """运行应用"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_app()

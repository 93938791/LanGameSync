"""
联机设置页面 - Fluent Design 风格
"""
import os
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidgetItem, QHeaderView, QGraphicsOpacityEffect
from PyQt5.QtGui import QFont, QColor, QPixmap
from qfluentwidgets import (
    ScrollArea, CardWidget, BodyLabel, SubtitleLabel, CaptionLabel,
    PrimaryPushButton, PushButton, LineEdit, PasswordLineEdit,
    ComboBox, TableWidget, TransparentToolButton, FluentIcon,
    InfoBar, InfoBarPosition, MessageBox as FluentMessageBox,
    FlowLayout, InfoBadge, InfoBadgePosition, IconWidget, ElevatedCardWidget
)
from PyQt5.QtGui import QPixmap

from utils.config_cache import ConfigCache
from utils.logger import Logger
from ui.threads import ConnectThread
from ui.components.dialogs import PeerManagerDialog, DeviceListDialog
from config import Config

logger = Logger().get_logger("NetworkInterface")


class NetworkInterface(QWidget):  # 改为 QWidget，不使用 ScrollArea
    """联机设置界面 - 流式布局"""
    
    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
        self.device_widgets = []  # 存储设备卡片的列表
        self.discovery_thread = None  # 设备发现线程
        self.discovery_running = False  # 设备发现线程运行标志
        
        # 日志去重：记录最近重连的设备ID，避免重复输出
        self.last_reconnect_log_time = {}  # 记录每个设备最近一次重连日志的时间戳
        
        # 流量统计定时器
        self.traffic_timer = QTimer()
        self.traffic_timer.timeout.connect(self.update_traffic_stats)
        
        # 设备列表刷新定时器（增加间隔到10秒，减少CPU占用）
        self.device_refresh_timer = QTimer()
        self.device_refresh_timer.timeout.connect(self.update_clients_list)
        
        # 设置全局唯一的对象名称（必须）
        self.setObjectName("networkInterface")
        
        # 设置纯白背景
        self.setStyleSheet("QWidget#networkInterface { background-color: white; }")
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 无边距
        main_layout.setSpacing(0)  # 无间距
        
        # 创建内容
        self.create_content(main_layout)
    
    def showEvent(self, event):
        """页面显示事件：切回页面时刷新设备列表"""
        super().showEvent(event)
        # 如果已连接，刷新设备列表
        if hasattr(self.parent_window, 'is_connected') and self.parent_window.is_connected:
            logger.info("切回联机设置页面，刷新设备列表...")
            self.update_clients_list()
    
    def create_content(self, main_layout):
        """创建内容 - 流式布局"""
        
        # 最上方：显示当前IP
        ip_bar = self.create_ip_bar()
        main_layout.addWidget(ip_bar)
        
        # 主内容区域（流式布局）
        content_widget = QWidget()
        content_layout = FlowLayout(content_widget, needAni=False)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setHorizontalSpacing(25)
        content_layout.setVerticalSpacing(25)
        
        # 4个部分
        # 1. 节点设置
        node_card = self.create_node_card()
        content_layout.addWidget(node_card)
        
        # 2. 上传和下载流量
        traffic_card = self.create_traffic_card()
        content_layout.addWidget(traffic_card)
        
        # 3. 网络关联
        network_card = self.create_network_card()
        content_layout.addWidget(network_card)
        
        # 4. 已连接的设备（4个正方形卡片）
        devices_card = self.create_devices_card()
        content_layout.addWidget(devices_card)
        
        main_layout.addWidget(content_widget)
    
    def create_ip_bar(self):
        """创建 IP 显示栏（最上方）"""
        bar = QWidget()
        bar.setFixedHeight(60)
        bar.setStyleSheet("background-color: #f5f5f5; border-bottom: 1px solid #e0e0e0;")
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(30, 0, 30, 0)
        
        # IP地址显示
        self.current_ip_label = SubtitleLabel("当前 IP: 未连接")
        layout.addWidget(self.current_ip_label)
        
        layout.addStretch()
        
        return bar
    
    def create_node_card(self):
        """创建节点设置卡片"""
        card = CardWidget()
        card.setFixedSize(320, 280)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(18)
        
        # 标题
        title = SubtitleLabel("节点设置")
        title.setStyleSheet("font-weight: 600; font-size: 16px;")
        card_layout.addWidget(title)
        
        # 节点选择
        node_label = CaptionLabel("当前节点")
        node_label.setStyleSheet("color: #666;")
        card_layout.addWidget(node_label)
        
        self.node_combo = ComboBox()
        self.node_combo.addItem("官方节点")
        self.node_combo.setEnabled(False)
        card_layout.addWidget(self.node_combo)
        
        card_layout.addStretch()
        
        # 配置按钮
        config_btn = PushButton(FluentIcon.SETTING, "配置节点")
        config_btn.setMinimumHeight(36)
        config_btn.clicked.connect(self.show_peer_manager)
        card_layout.addWidget(config_btn)
        
        return card
    
    def create_traffic_card(self):
        """创建流量卡片"""
        card = CardWidget()
        card.setFixedSize(320, 280)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(18)
        
        # 标题
        title = SubtitleLabel("流量统计")
        title.setStyleSheet("font-weight: 600; font-size: 16px;")
        card_layout.addWidget(title)
        
        # 上传流量
        upload_label = CaptionLabel("上传流量")
        upload_label.setStyleSheet("color: #666;")
        card_layout.addWidget(upload_label)
        
        upload_row = QHBoxLayout()
        # 使用PNG图标
        upload_icon = QLabel()
        upload_icon.setFixedSize(20, 20)
        upload_icon.setAlignment(Qt.AlignCenter)
        upload_icon_path = str(Config.RESOURCES_DIR / "icons" / "upload.png")
        if os.path.exists(upload_icon_path):
            pixmap = QPixmap(upload_icon_path)
            upload_icon.setPixmap(pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        upload_row.addWidget(upload_icon)
        
        self.upload_value = BodyLabel("0 MB")
        self.upload_value.setStyleSheet("color: #0078d4; font-weight: 600; font-size: 15px;")
        upload_row.addWidget(self.upload_value)
        upload_row.addStretch()
        
        self.upload_speed = CaptionLabel("0 KB/s")
        self.upload_speed.setStyleSheet("color: #999;")
        upload_row.addWidget(self.upload_speed)
        card_layout.addLayout(upload_row)
        
        # 下载流量
        download_label = CaptionLabel("下载流量")
        download_label.setStyleSheet("color: #666;")
        card_layout.addWidget(download_label)
        
        download_row = QHBoxLayout()
        # 使用PNG图标
        download_icon = QLabel()
        download_icon.setFixedSize(20, 20)
        download_icon.setAlignment(Qt.AlignCenter)
        download_icon_path = str(Config.RESOURCES_DIR / "icons" / "download.png")
        if os.path.exists(download_icon_path):
            pixmap = QPixmap(download_icon_path)
            download_icon.setPixmap(pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        download_row.addWidget(download_icon)
        
        self.download_value = BodyLabel("0 MB")
        self.download_value.setStyleSheet("color: #10893e; font-weight: 600; font-size: 15px;")
        download_row.addWidget(self.download_value)
        download_row.addStretch()
        
        self.download_speed = CaptionLabel("0 KB/s")
        self.download_speed.setStyleSheet("color: #999;")
        download_row.addWidget(self.download_speed)
        card_layout.addLayout(download_row)
        
        card_layout.addStretch()
        
        return card
    
    def create_network_card(self):
        """创建网络关联卡片"""
        card = CardWidget()
        card.setFixedSize(320, 280)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(18)
        
        # 标题
        title = SubtitleLabel("网络关联")
        title.setStyleSheet("font-weight: 600; font-size: 16px;")
        card_layout.addWidget(title)
        
        # 房间号
        room_label = CaptionLabel("房间号")
        room_label.setStyleSheet("color: #666;")
        card_layout.addWidget(room_label)
        
        self.room_input = LineEdit()
        self.room_input.setPlaceholderText("请输入房间号")
        self.room_input.setClearButtonEnabled(True)
        
        # 加载配置
        network_config = self.parent_window.config_data.get("network", {})
        if network_config.get("room_name"):
            self.room_input.setText(network_config["room_name"])
        
        card_layout.addWidget(self.room_input)
        
        # 密码
        password_label = CaptionLabel("密码")
        password_label.setStyleSheet("color: #666;")
        card_layout.addWidget(password_label)
        
        self.password_input = PasswordLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setClearButtonEnabled(True)
        
        if network_config.get("password"):
            self.password_input.setText(network_config["password"])
        
        card_layout.addWidget(self.password_input)
        
        card_layout.addStretch()
        
        # 连接按钮
        self.connect_btn = PrimaryPushButton(FluentIcon.CONNECT, "连接网络")
        self.connect_btn.setMinimumHeight(36)
        self.connect_btn.clicked.connect(self.connect_to_network)
        card_layout.addWidget(self.connect_btn)
        
        return card
    
    def create_devices_card(self):
        """创建设备列表区域（无外边框）"""
        # 使用透明容器，不显示边框
        container = QWidget()
        container.setFixedSize(1000, 280)
        container.setStyleSheet("background: transparent;")
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)
        
        # 标题
        title = SubtitleLabel("已连接设备")
        title.setStyleSheet("font-weight: 600; font-size: 16px; background: transparent;")
        container_layout.addWidget(title)
        
        # 设备容器（横向布局，动态添加设备）
        devices_container = QWidget()
        devices_container.setStyleSheet("background: transparent;")
        devices_layout = QHBoxLayout(devices_container)
        devices_layout.setContentsMargins(0, 0, 0, 0)
        devices_layout.setSpacing(18)
        devices_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # 保存布局引用
        self.devices_layout = devices_layout
        self.device_widgets = []  # 存储当前显示的设备卡片
        
        container_layout.addWidget(devices_container)
        container_layout.addStretch()
        
        return container
    
    def create_single_device_card(self, device_name="", device_ip="", is_self=False, latency=0):
        """创建单个设备卡片（使用 ElevatedCardWidget 有阴影效果）"""
        device = ElevatedCardWidget()
        device.setFixedSize(140, 170)  # 统一固定尺寸
        
        layout = QVBoxLayout(device)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)
        
        # 状态图标（根据延迟显示不同图片）
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(64, 64)
        
        # 根据延迟选择图标
        if is_self:
            icon_name = "good.png"  # 本机默认良好
        elif latency == 0 or latency < 50:
            icon_name = "fluid.png"  # 流畅
        elif latency < 100:
            icon_name = "good.png"  # 良好
        elif latency < 200:
            icon_name = "laggy.png"  # 卡顿
        else:
            icon_name = "drop.png"  # 断开/极差
        
        # 使用Config获取正确的资源路径
        icon_path = str(Config.RESOURCES_DIR / "icons" / icon_name)
        
        # 加载图片
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            icon_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # 如果图片不存在，使用表情作为后备
            logger.warning(f"找不到图标文件: {icon_path}")
            if is_self:
                emoji = "💻"
            elif latency < 50:
                emoji = "😊"
            elif latency < 100:
                emoji = "🙂"
            else:
                emoji = "😐"
            icon_label.setText(emoji)
            icon_label.setStyleSheet("font-size: 52px;")
        
        layout.addWidget(icon_label, 0, Qt.AlignCenter)
        
        # 设备名（支持滚动显示，固定高度）
        name_color = "#0078d4" if is_self else "#107c10"
        name_container = QWidget()
        name_container.setFixedSize(116, 22)  # 固定宽度和高度
        name_layout = QHBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)
        
        name_label = BodyLabel(device_name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(f"""
            color: {name_color}; 
            font-size: 13px;
            font-weight: 600;
            background: transparent;
        """)
        name_label.setWordWrap(False)
        name_layout.addWidget(name_label)
        
        # 如果设备名过长，启用滚动动画
        if len(device_name) > 8:  # 超过8个字符启用滚动
            # 创建滚动动画
            self._setup_scroll_animation(name_label, device_name)
        
        layout.addWidget(name_container, 0, Qt.AlignCenter)
        
        # IP地址（加大字号，固定高度）
        ip_container = QWidget()
        ip_container.setFixedSize(116, 18)  # 固定高度确保对齐
        ip_layout = QHBoxLayout(ip_container)
        ip_layout.setContentsMargins(0, 0, 0, 0)
        ip_layout.setSpacing(0)
        
        ip_label = BodyLabel(device_ip)
        ip_label.setAlignment(Qt.AlignCenter)
        ip_label.setStyleSheet(f"""
            color: #555555; 
            font-size: 12px;
            font-weight: 500;
            font-family: 'Consolas', monospace;
            background: transparent;
        """)
        # 设置工具提示显示设备名称
        ip_label.setToolTip(f"设备名称: {device_name}")
        ip_layout.addWidget(ip_label)
        
        layout.addWidget(ip_container, 0, Qt.AlignCenter)
        
        # 延迟信息（如果不是本机，固定高度）
        if not is_self:
            latency_container = QWidget()
            latency_container.setFixedSize(116, 16)  # 固定高度
            latency_layout = QHBoxLayout(latency_container)
            latency_layout.setContentsMargins(0, 0, 0, 0)
            latency_layout.setSpacing(0)
            
            latency_label = CaptionLabel(f"{latency}ms" if latency > 0 else "-")
            latency_label.setAlignment(Qt.AlignCenter)
            latency_color = "#10893e" if latency < 50 else "#ca5010" if latency < 100 else "#d13438"
            latency_label.setStyleSheet(f"""
                color: {latency_color}; 
                font-size: 10px;
                font-weight: 500;
                background: transparent;
            """)
            latency_layout.addWidget(latency_label)
            layout.addWidget(latency_container, 0, Qt.AlignCenter)
        else:
            # 本机设备也添加一个空的容器占位，保持高度一致
            spacer_container = QWidget()
            spacer_container.setFixedSize(116, 16)
            layout.addWidget(spacer_container, 0, Qt.AlignCenter)
        
        # 存储引用
        device.icon_label = icon_label
        device.name_label = name_label
        device.ip_label = ip_label
        device.device_name = device_name
        device.device_ip = device_ip
        device.is_self = is_self
        
        return device
    
    def _setup_scroll_animation(self, label, text):
        """设置文本滚动动画（优化版）"""
        # 只有在需要时才创建定时器，减少性能开销
        if len(text) <= 8:
            return
        
        # 创建定时器实现滚动效果（加大间隔减少CPU占用）
        timer = QTimer(label)
        scroll_pos = [0]  # 使用列表以便在闭包中修改
        
        def scroll_text():
            # 循环滚动文本
            scroll_pos[0] = (scroll_pos[0] + 1) % len(text)
            scrolled_text = text[scroll_pos[0]:] + "  " + text[:scroll_pos[0]]
            label.setText(scrolled_text)
        
        timer.timeout.connect(scroll_text)
        timer.start(500)  # 从300ms增加到50 0ms，减少更新频率
        label.scroll_timer = timer  # 保存引用防止被回收
    
    def show_peer_manager(self):
        """显示节点管理器"""
        dialog = PeerManagerDialog(self.parent_window, self.parent_window.config_data)
        dialog.exec_()
    
    def connect_to_network(self):
        """连接到网络"""
        room_name = self.room_input.text().strip()
        password = self.password_input.text().strip()
        
        if not room_name or not password:
            InfoBar.warning(
                title='输入错误',
                content="请输入房间号和密码",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 保存配置
        self.parent_window.config_data["network"] = {
            "room_name": room_name,
            "password": password
        }
        ConfigCache.save(self.parent_window.config_data)
        
        # 启动连接线程（固定使用官方节点）
        self.parent_window.connect_thread = ConnectThread(
            self.parent_window.controller, 
            room_name, 
            password, 
            None,  # selected_peer
            True   # use_peer
        )
        self.parent_window.connect_thread.connected.connect(self.on_connected)
        self.parent_window.connect_thread.progress.connect(self.on_connect_progress)
        self.parent_window.connect_thread.start()
        
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("正在连接...")
    
    def on_connect_progress(self, message):
        """连接进度回调"""
        # 不在连接过程中显示IP，避免显示TUN设备IP
        # 只显示进度信息
        if message and not message.startswith("10.144"):
            self.current_ip_label.setText(f"当前 IP: {message}")
        else:
            # 连接过程中不显示IP，等待成功后再显示
            pass
    
    def on_connected(self, success, message):
        """连接完成回调"""
        self.connect_btn.setEnabled(True)
        
        if success:
            self.parent_window.is_connected = True
            
            # 将Syncthing管理器暴露给主窗口使用
            self.parent_window.syncthing_manager = self.parent_window.controller.syncthing
            logger.info("Syncthing管理器已准备好")
            
            # 注册Syncthing事件回调
            self.parent_window.syncthing_manager.register_event_callback(self.parent_window.on_syncthing_event)
            logger.info("已注册Syncthing事件监听")
            
            # 初始化TCP广播（传入EasyTier管理器引用）
            from managers.tcp_broadcast import TCPBroadcast
            self.parent_window.tcp_broadcast = TCPBroadcast(easytier_manager=self.parent_window.controller.easytier)
            self.parent_window.tcp_broadcast.connect(broker_port=9999)
            self.parent_window.tcp_broadcast.register_callback(self.parent_window.on_tcp_message)
            logger.info("TCP广播已启动")
            
            # 广播设备上线消息
            self.parent_window.tcp_broadcast.publish("device/online", {
                "device_id": self.parent_window.syncthing_manager.device_id,
                "virtual_ip": message,
                "hostname": Config.HOSTNAME
            })
            logger.info("已广播设备上线消息")
            
            # 更新IP显示
            self.current_ip_label.setText(f"当前 IP: {message}")
            
            # 连接成功后按钮变为断开连接
            self.connect_btn.setText("断开")
            self.connect_btn.setIcon(FluentIcon.CLOSE)
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.disconnect_network)
            
            # 开启客户端监控
            self.parent_window.last_peer_ips = set()
            self.parent_window.last_peer_count = 0
            self.update_clients_list()
            
            # 启动流量统计定时器（每2秒更新一次）
            self.traffic_timer.start(2000)
            logger.info("流量统计定时器已启动")
            
            # 启动设备列表刷新定时器（从5秒增加到10秒，减少频繁调用）
            self.device_refresh_timer.start(10000)
            logger.info("设备列表刷新定时器已启动")
            
            # 不再启动持续轮询线程，改为连接时发现一次
            # self._start_device_discovery_thread()  # 已禁用
            logger.info("设备发现已完成，不启动持续监测")
            
            InfoBar.success(
                title='连接成功',
                content=f"已连接到虚拟网络，IP: {message}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            self.parent_window.is_connected = False
            self.connect_btn.setText("连接")
            
            InfoBar.error(
                title='连接失败',
                content=f"{message}\n\n请尝试切换节点",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
    
    
    def disconnect_network(self):
        """断开网络连接"""
        try:
            # 停止设备发现线程
            self._stop_device_discovery_thread()
            
            # 停止流量统计定时器
            if self.traffic_timer.isActive():
                self.traffic_timer.stop()
                logger.info("流量统计定时器已停止")
            
            # 停止设备列表刷新定时器
            if self.device_refresh_timer.isActive():
                self.device_refresh_timer.stop()
                logger.info("设备列表刷新定时器已停止")
            
            # TODO: 实现断开逻辑
            self.parent_window.is_connected = False
            self.current_ip_label.setText("当前 IP: 未连接")
            self.connect_btn.setText("连接")
            self.connect_btn.setIcon(FluentIcon.CONNECT)
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.connect_to_network)
            
            # 清空设备卡片
            for widget in self.device_widgets:
                widget.deleteLater()
            self.device_widgets.clear()
            
            # 重置流量显示
            self.upload_value.setText("0 MB")
            self.download_value.setText("0 MB")
            self.upload_speed.setText("0 KB/s")
            self.download_speed.setText("0 KB/s")
            
            InfoBar.info(
                title='已断开',
                content="已断开网络连接",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            logger.error(f"断开连接失败: {e}")
    
    def update_clients_list(self):
        """更新客户端列表（显示在设备卡片中）——异步版本，不阻塞UI"""
        if not self.parent_window.is_connected:
            return
        
        # 在后台线程中执行，不阻塞UI
        import threading
        def update_thread():
            try:
                # 获取对等设备列表
                peers = self.parent_window.controller.easytier.discover_peers(timeout=1)
                
                # 收集设备信息
                devices = []
                
                # 添加本机（总是显示）
                my_ip = self.parent_window.controller.easytier.virtual_ip or "unknown"
                devices.append({
                    "name": "本机",
                    "ip": my_ip,
                    "is_self": True
                })
                
                # 如果有对等设备，处理它们
                if peers:
                    # 获取当前Syncthing连接状态
                    connections = self.parent_window.syncthing_manager.get_connections()
                    connected_device_ids = set()
                    if connections and connections.get('connections'):
                        for dev_id, conn_info in connections['connections'].items():
                            if conn_info.get('connected'):
                                connected_device_ids.add(dev_id)
                    
                    # 添加其他设备（过滤掉本机）
                    seen_ips = set([my_ip])
                    
                    for peer in peers:
                        ipv4 = peer.get('ipv4', '')
                        hostname = peer.get('hostname', 'Unknown')
                        
                        # 过滤掉本机（通过IP和hostname双重检查）
                        if ipv4 and ipv4 not in seen_ips and hostname != Config.HOSTNAME:
                            # 尝试获取远程设备的Syncthing ID
                            device_id = self._get_remote_syncthing_id(ipv4)
                            if device_id and device_id != self.parent_window.syncthing_manager.device_id:
                                # 添加设备到Syncthing（如果已存在则返回None）
                                # 传递虚拟IP地址，使Syncthing可以通过虚拟网络连接
                                result = self.parent_window.syncthing_manager.add_device(
                                    device_id=device_id,
                                    device_name=hostname,
                                    device_address=ipv4  # 传递虚拟IP
                                )
                                # 只有新增成功时才打印日志（None表示已存在）
                                if result is True:
                                    logger.info(f"自动发现并添加设备: {hostname} ({device_id[:7]}...) - {ipv4}")
                                    # 将设备添加到所有正在同步的文件夹
                                    self._add_device_to_active_folders(device_id)
                                # 如果设备已存在但未连接，触发重连
                                elif result is None and device_id not in connected_device_ids:
                                    # 日志去重：只有距离上次日志超过30秒才输出
                                    import time
                                    current_time = time.time()
                                    last_log_time = self.last_reconnect_log_time.get(device_id, 0)
                                    if current_time - last_log_time > 30:  # 30秒内不重复输出
                                        logger.info(f"🔄 设备 {hostname} ({device_id[:7]}...) 已上线但未连接，触发重连...")
                                        self.last_reconnect_log_time[device_id] = current_time
                                    self.parent_window.syncthing_manager._restart_device_connection(device_id)
                            
                            # 获取延迟（如果有）
                            latency_str = peer.get('latency', '0ms')
                            latency = 0
                            if latency_str and latency_str != '-':
                                try:
                                    latency = int(latency_str.replace('ms', '').strip())
                                except:
                                    latency = 0
                            
                            devices.append({
                                "name": hostname,
                                "ip": ipv4,
                                "is_self": False,
                                "latency": latency
                            })
                            
                            seen_ips.add(ipv4)
                else:
                    logger.debug("未发现对等设备，仅显示本机")
                
                # 在主线程中更新UI
                from PyQt5.QtCore import QTimer
                def update_ui():
                    try:
                        # 更新设备卡片（动态添加/删除）
                        # 先清空现有设备
                        for widget in self.device_widgets:
                            widget.deleteLater()
                        self.device_widgets.clear()
                        
                        # 动态添加设备卡片
                        for device in devices:
                            device_card = self.create_single_device_card(
                                device_name=device["name"],
                                device_ip=device["ip"],
                                is_self=device["is_self"],
                                latency=device.get("latency", 0)
                            )
                            self.devices_layout.addWidget(device_card)
                            self.device_widgets.append(device_card)
                        
                        logger.info(f"更新客户端列表: 总计 {len(devices)} 台设备")
                    except Exception as e:
                        logger.error(f"更新UI失败: {e}")
                
                # 使用QTimer.singleShot在主线程执行
                QTimer.singleShot(0, update_ui)
                
            except Exception as e:
                logger.error(f"后台更新客户端列表失败: {e}")
        
        threading.Thread(target=update_thread, daemon=True, name="UpdateClientsThread").start()
    
    def _get_remote_syncthing_id(self, peer_ip):
        """获取远程设备的Syncthing ID"""
        try:
            import requests
            
            url = f"http://{peer_ip}:{Config.SYNCTHING_API_PORT}/rest/system/status"
            headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
            
            resp = requests.get(url, headers=headers, timeout=5)
            resp.raise_for_status()
            
            device_id = resp.json()["myID"]
            return device_id
        except requests.exceptions.Timeout:
            logger.warning(f"❌ 连接到 {peer_ip} 超时（可能对方Syncthing还未启动）")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"❌ HTTP错误（{peer_ip}）: {e} - 可能是API Key不匹配")
            return None
        except Exception as e:
            logger.warning(f"❌ 无法从 {peer_ip} 获取Syncthing ID: {type(e).__name__}: {e}")
            return None
    
    def show_all_devices(self):
        """显示所有设备"""
        dialog = DeviceListDialog(self.parent_window, self.parent_window.controller)
        dialog.exec_()
    
    def _start_device_discovery_thread(self):
        """启动设备自动发现线程（定期扫描并添加新设备到Syncthing）"""
        if self.discovery_running:
            logger.info("设备发现线程已经在运行")
            return
        
        import threading
        import time
        
        def discovery_loop():
            """设备发现循环线程"""
            logger.info("启动设备自动发现线程...")
            
            while self.discovery_running:
                try:
                    if not self.parent_window.is_connected:
                        # 如果断开连接，停止扫描
                        logger.info("网络已断开，停止设备发现")
                        break
                    
                    # 获取对等设备列表
                    peers = self.parent_window.controller.easytier.discover_peers(timeout=3)
                    
                    my_syncthing_id = self.parent_window.syncthing_manager.device_id
                    my_ip = self.parent_window.controller.easytier.virtual_ip or "unknown"
                    
                    # 获取当前Syncthing连接状态
                    connections = self.parent_window.syncthing_manager.get_connections()
                    connected_device_ids = set()
                    if connections and connections.get('connections'):
                        for dev_id, conn_info in connections['connections'].items():
                            if conn_info.get('connected'):
                                connected_device_ids.add(dev_id)
                    
                    # 收集在线的EasyTier设备ID
                    online_device_ids = set()
                    
                    # 遍历所有对等设备
                    for peer in peers:
                        ipv4 = peer.get('ipv4', '')
                        hostname = peer.get('hostname', 'Unknown')
                        
                        # 过滤掉本机
                        if not ipv4 or ipv4 == my_ip or hostname == Config.HOSTNAME:
                            continue
                        
                        # 尝试获取远程设备的Syncthing ID
                        device_id = self._get_remote_syncthing_id(ipv4)
                        
                        if device_id and device_id != my_syncthing_id:
                            online_device_ids.add(device_id)
                            
                            # 添加设备到Syncthing（如果已存在则返回None）
                            # 传递虚拟IP地址，使Syncthing可以通过虚拟网络连接
                            result = self.parent_window.syncthing_manager.add_device(
                                device_id=device_id,
                                device_name=hostname,
                                device_address=ipv4  # 传递虚拟IP
                            )
                            # 只有真正添加了新设备时才执行后续操作
                            if result is True:
                                logger.info(f"自动发现并添加设备: {hostname} ({device_id[:7]}...) - {ipv4}")
                                
                                # 将设备添加到所有正在同步的文件夹
                                self._add_device_to_active_folders(device_id)
                            # 如果设备已存在但未连接，触发重连
                            elif result is None and device_id not in connected_device_ids:
                                # 日志去重：只有距离上次日志超过30秒才输出
                                import time
                                current_time = time.time()
                                last_log_time = self.last_reconnect_log_time.get(device_id, 0)
                                if current_time - last_log_time > 30:  # 30秒内不重复输出
                                    logger.info(f"🔄 设备 {hostname} ({device_id[:7]}...) 已上线但未连接，触发重连...")
                                    self.last_reconnect_log_time[device_id] = current_time
                                self.parent_window.syncthing_manager._restart_device_connection(device_id)
                    
                    # 每10秒扫描一次
                    time.sleep(10)
                    
                except Exception as e:
                    logger.error(f"设备发现线程错误: {e}")
                    time.sleep(5)  # 出错后等待更长时间
            
            logger.info("设备自动发现线程已停止")
        
        self.discovery_running = True
        self.discovery_thread = threading.Thread(target=discovery_loop, daemon=True)
        self.discovery_thread.start()
        logger.info("设备自动发现线程已启动")
    
    def _stop_device_discovery_thread(self):
        """停止设备自动发现线程"""
        if self.discovery_running:
            self.discovery_running = False
            if self.discovery_thread:
                self.discovery_thread.join(timeout=2)
                self.discovery_thread = None
            logger.info("设备自动发现线程已停止")
    
    def _add_device_to_active_folders(self, device_id):
        """将新发现的设备添加到所有同步文件夹（包括暂停的）"""
        try:
            config = self.parent_window.syncthing_manager.get_config()
            if not config:
                return
            
            folders = config.get('folders', [])
            updated = False
            
            for folder in folders:
                # 处理所有文件夹（包括暂停的），确保设备列表完整
                # 检查设备是否已在文件夹中
                folder_devices = folder.get('devices', [])
                device_ids = [d['deviceID'] for d in folder_devices]
                
                if device_id not in device_ids:
                    # 添加设备到文件夹
                    folder_devices.append({'deviceID': device_id})
                    folder['devices'] = folder_devices
                    updated = True
                    is_paused = folder.get('paused', False)
                    logger.info(f"将设备 {device_id[:7]}... 添加到文件夹 {folder.get('id')} (暂停={is_paused})")
            
            if updated:
                self.parent_window.syncthing_manager.set_config(config, async_mode=True)
                logger.info("已更新Syncthing配置，新设备已添加到所有同步文件夹")
        except Exception as e:
            logger.error(f"添加设备到文件夹失败: {e}")
    
    def update_traffic_stats(self):
        """更新流量统计（定时调用）"""
        if not self.parent_window.is_connected:
            return
        
        # 检查 controller 和 easytier 是否存在
        if not hasattr(self.parent_window, 'controller') or not self.parent_window.controller:
            return
        
        if not hasattr(self.parent_window.controller, 'easytier') or not self.parent_window.controller.easytier:
            return
        
        try:
            # 获取流量统计
            stats = self.parent_window.controller.easytier.get_traffic_stats()
            
            # 格式化流量显示
            tx_bytes = stats.get('tx_bytes', 0)
            rx_bytes = stats.get('rx_bytes', 0)
            tx_speed = stats.get('tx_speed', 0)
            rx_speed = stats.get('rx_speed', 0)
            
            # 转换为合适的单位
            self.upload_value.setText(self._format_bytes(tx_bytes))
            self.download_value.setText(self._format_bytes(rx_bytes))
            self.upload_speed.setText(self._format_speed(tx_speed))
            self.download_speed.setText(self._format_speed(rx_speed))
            
        except Exception as e:
            logger.error(f"更新流量统计失败: {e}")
    
    def _format_bytes(self, bytes_value):
        """格式化字节数为可读格式"""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 * 1024:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024 * 1024 * 1024:
            return f"{bytes_value / 1024 / 1024:.2f} MB"
        else:
            return f"{bytes_value / 1024 / 1024 / 1024:.2f} GB"
    
    def _format_speed(self, speed_bytes_per_sec):
        """格式化速度为可读格式"""
        if speed_bytes_per_sec < 1024:
            return f"{speed_bytes_per_sec:.0f} B/s"
        elif speed_bytes_per_sec < 1024 * 1024:
            return f"{speed_bytes_per_sec / 1024:.2f} KB/s"
        else:
            return f"{speed_bytes_per_sec / 1024 / 1024:.2f} MB/s"

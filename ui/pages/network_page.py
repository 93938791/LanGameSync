"""
联机设置页面 - Fluent Design 风格
"""
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidgetItem, QHeaderView
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
    
    def create_content(self, main_layout):
        """创建内容 - 流式布局"""
        
        # 最上方：显示当前IP
        ip_bar = self.create_ip_bar()
        main_layout.addWidget(ip_bar)
        
        # 主内容区域（流式布局）
        content_widget = QWidget()
        content_layout = FlowLayout(content_widget, needAni=False)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setHorizontalSpacing(20)
        content_layout.setVerticalSpacing(20)
        
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
        card.setFixedSize(280, 200)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 15, 20, 15)
        card_layout.setSpacing(12)
        
        # 标题
        title = BodyLabel("节点设置")
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        card_layout.addWidget(title)
        
        # 节点选择
        self.node_combo = ComboBox()
        self.node_combo.addItem("官方节点")
        self.node_combo.setEnabled(False)
        card_layout.addWidget(self.node_combo)
        
        card_layout.addStretch()
        
        # 配置按钮
        config_btn = PushButton(FluentIcon.SETTING, "配置")
        config_btn.clicked.connect(self.show_peer_manager)
        card_layout.addWidget(config_btn)
        
        return card
    
    def create_traffic_card(self):
        """创建流量卡片"""
        card = CardWidget()
        card.setFixedSize(280, 200)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 15, 20, 15)
        card_layout.setSpacing(12)
        
        # 标题
        title = BodyLabel("流量统计")
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        card_layout.addWidget(title)
        
        # 上传
        upload_row = QHBoxLayout()
        upload_icon = IconWidget(FluentIcon.UP)
        upload_icon.setFixedSize(16, 16)
        upload_row.addWidget(upload_icon)
        
        upload_label = BodyLabel("上传:")
        upload_row.addWidget(upload_label)
        
        self.upload_value = BodyLabel("0 MB")
        self.upload_value.setStyleSheet("color: #0078d4; font-weight: 600;")
        upload_row.addWidget(self.upload_value)
        upload_row.addStretch()
        card_layout.addLayout(upload_row)
        
        # 下载
        download_row = QHBoxLayout()
        download_icon = IconWidget(FluentIcon.DOWN)
        download_icon.setFixedSize(16, 16)
        download_row.addWidget(download_icon)
        
        download_label = BodyLabel("下载:")
        download_row.addWidget(download_label)
        
        self.download_value = BodyLabel("0 MB")
        self.download_value.setStyleSheet("color: #10893e; font-weight: 600;")
        download_row.addWidget(self.download_value)
        download_row.addStretch()
        card_layout.addLayout(download_row)
        
        card_layout.addStretch()
        
        return card
    
    def create_network_card(self):
        """创建网络关联卡片"""
        card = CardWidget()
        card.setFixedSize(280, 200)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 15, 20, 15)
        card_layout.setSpacing(12)
        
        # 标题
        title = BodyLabel("网络关联")
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        card_layout.addWidget(title)
        
        # 房间号
        self.room_input = LineEdit()
        self.room_input.setPlaceholderText("房间号")
        self.room_input.setClearButtonEnabled(True)
        
        # 加载配置
        network_config = self.parent_window.config_data.get("network", {})
        if network_config.get("room_name"):
            self.room_input.setText(network_config["room_name"])
        
        card_layout.addWidget(self.room_input)
        
        # 密码
        self.password_input = PasswordLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setClearButtonEnabled(True)
        
        if network_config.get("password"):
            self.password_input.setText(network_config["password"])
        
        card_layout.addWidget(self.password_input)
        
        card_layout.addStretch()
        
        # 连接按钮
        self.connect_btn = PrimaryPushButton(FluentIcon.CONNECT, "连接")
        self.connect_btn.clicked.connect(self.connect_to_network)
        card_layout.addWidget(self.connect_btn)
        
        return card
    
    def create_devices_card(self):
        """创建设备列表区域（无外框，动态显示）"""
        # 直接返回一个透明容器，不用 CardWidget
        container = QWidget()
        container.setFixedSize(580, 200)
        
        # 设备容器（流式布局，动态添加设备）
        devices_layout = QHBoxLayout(container)
        devices_layout.setContentsMargins(0, 0, 0, 0)
        devices_layout.setSpacing(15)
        devices_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # 保存布局引用
        self.devices_layout = devices_layout
        self.device_widgets = []  # 存储当前显示的设备卡片
        
        return container
    
    def create_single_device_card(self, device_name="", device_ip="", is_self=False, latency=0):
        """创建单个设备卡片（使用 ElevatedCardWidget 有阴影效果）"""
        device = ElevatedCardWidget()
        device.setFixedSize(100, 110)
        
        layout = QVBoxLayout(device)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignCenter)
        
        # 状态图标（根据延迟显示不同图片）
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(48, 48)
        
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
            icon_label.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
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
            icon_label.setStyleSheet("font-size: 38px;")
        
        layout.addWidget(icon_label, 0, Qt.AlignCenter)
        
        # 设备名
        name_color = "#0078d4" if is_self else "#107c10"
        name_label = CaptionLabel(device_name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(f"""
            color: {name_color}; 
            font-size: 11px;
            font-weight: 600;
        """)
        layout.addWidget(name_label)
        
        # IP地址
        ip_label = CaptionLabel(device_ip)
        ip_label.setAlignment(Qt.AlignCenter)
        ip_label.setStyleSheet(f"""
            color: #888888; 
            font-size: 9px;
            font-family: 'Consolas', monospace;
        """)
        layout.addWidget(ip_label)
        
        # 存储引用
        device.icon_label = icon_label
        device.name_label = name_label
        device.ip_label = ip_label
        device.device_name = device_name
        device.device_ip = device_ip
        device.is_self = is_self
        
        return device
    
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
        # 可以在IP栏显示进度
        self.current_ip_label.setText(f"当前 IP: {message}")
    
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
            
            # 自动暂停所有同步文件夹（防止自动同步）
            self._pause_all_folders_on_connect()
            
            # 初始化UDP广播
            from managers.udp_broadcast import UDPBroadcast
            self.parent_window.udp_broadcast = UDPBroadcast()
            self.parent_window.udp_broadcast.connect(broker_port=9999)
            self.parent_window.udp_broadcast.register_callback(self.parent_window.on_udp_message)
            logger.info("UDP广播已启动")
            
            # 广播设备上线消息
            self.parent_window.udp_broadcast.publish("device/online", {
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
    
    def _pause_all_folders_on_connect(self):
        """连接成功后自动暂停所有文件夹（防止自动同步）"""
        try:
            if not hasattr(self.parent_window, 'syncthing_manager') or not self.parent_window.syncthing_manager:
                return
            
            config = self.parent_window.syncthing_manager.get_config()
            if not config:
                return
            
            folders = config.get('folders', [])
            paused_count = 0
            
            for folder in folders:
                if not folder.get('paused', False):
                    folder['paused'] = True
                    paused_count += 1
            
            if paused_count > 0:
                self.parent_window.syncthing_manager.set_config(config)
                logger.info(f"连接成功后自动暂停了 {paused_count} 个文件夹，防止自动同步")
        except Exception as e:
            logger.error(f"自动暂停文件夹失败: {e}")
    
    def disconnect_network(self):
        """断开网络连接"""
        try:
            # 停止设备发现线程
            self._stop_device_discovery_thread()
            
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
        """更新客户端列表（显示在设备卡片中）"""
        if not self.parent_window.is_connected:
            return
        
        try:
            # 获取对等设备列表
            peers = self.parent_window.controller.easytier.discover_peers(timeout=3)
            
            # 收集设备信息
            devices = []
            
            # 添加本机
            my_ip = self.parent_window.controller.easytier.virtual_ip or "unknown"
            devices.append({
                "name": "本机",
                "ip": my_ip,
                "is_self": True
            })
            
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
                        result = self.parent_window.syncthing_manager.add_device(device_id, hostname)
                        # 只有新增成功时才打印日志（None表示已存在）
                        if result is True:
                            logger.info(f"自动发现并添加设备: {hostname} ({device_id[:7]}...) - {ipv4}")
                            # 将设备添加到所有正在同步的文件夹
                            self._add_device_to_active_folders(device_id)
                    
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
            logger.error(f"更新客户端列表失败: {e}")
    
    def _get_remote_syncthing_id(self, peer_ip):
        """获取远程设备的Syncthing ID"""
        try:
            import requests
            
            proxies = {
                'http': f'socks5h://127.0.0.1:{Config.EASYTIER_SOCKS5_PORT}',
                'https': f'socks5h://127.0.0.1:{Config.EASYTIER_SOCKS5_PORT}'
            }
            
            url = f"http://{peer_ip}:{Config.SYNCTHING_API_PORT}/rest/system/status"
            headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
            
            logger.info(f"尝试通过SOCKS5访问: {url}")
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=5)
            resp.raise_for_status()
            
            device_id = resp.json()["myID"]
            logger.info(f"✅ 成功从 {peer_ip} 获取到设备ID: {device_id[:7]}...")
            return device_id
        except requests.exceptions.ProxyError as e:
            logger.warning(f"❌ SOCKS5代理连接失败（{peer_ip}）: {e}")
            return None
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
        """将新发现的设备添加到所有正在同步的文件夹"""
        try:
            config = self.parent_window.syncthing_manager.get_config()
            if not config:
                return
            
            folders = config.get('folders', [])
            updated = False
            
            for folder in folders:
                # 只处理未暂停的文件夹
                if folder.get('paused', False):
                    continue
                
                # 检查设备是否已在文件夹中
                folder_devices = folder.get('devices', [])
                device_ids = [d['deviceID'] for d in folder_devices]
                
                if device_id not in device_ids:
                    # 添加设备到文件夹
                    folder_devices.append({'deviceID': device_id})
                    folder['devices'] = folder_devices
                    updated = True
                    logger.info(f"将设备 {device_id[:7]}... 添加到文件夹 {folder.get('id')}")
            
            if updated:
                self.parent_window.syncthing_manager.set_config(config, async_mode=True)
                logger.info("已更新Syncthing配置，新设备已添加到同步文件夹")
        except Exception as e:
            logger.error(f"添加设备到文件夹失败: {e}")

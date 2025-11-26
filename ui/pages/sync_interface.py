"""
存档同步界面
展示Syncthing同步目录列表和状态
"""
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem
from PyQt5.QtGui import QColor
from qfluentwidgets import (
    ScrollArea, CardWidget, BodyLabel, SubtitleLabel,
    PushButton, PrimaryPushButton, TableWidget, InfoBar, InfoBarPosition
)
import requests

from utils.logger import Logger
from config import Config

logger = Logger().get_logger("SyncInterface")


class SyncInterface(ScrollArea):
    """存档同步界面"""
    
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        
        # 创建自动刷新定时器（每5秒刷新一次）
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self._auto_refresh)
        self.auto_refresh_timer.setInterval(5000)  # 5秒
        
        # 设置滚动区域样式
        self.setObjectName("syncInterface")
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea {border: none; background: transparent;}")
        
        # 创建主容器
        self.view = QWidget()
        self.view.setStyleSheet("background: transparent;")
        self.setWidget(self.view)
        
        # 创建布局
        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.setSpacing(20)
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 标题
        title = SubtitleLabel("存档同步")
        title.setObjectName("pageTitle")
        title.setStyleSheet("background: transparent; border: none;")
        self.vBoxLayout.addWidget(title)
        
        # Syncthing 同步卡片（让卡片占满剩余空间）
        sync_card = self.create_sync_card()
        self.vBoxLayout.addWidget(sync_card, 1)  # stretch=1，让卡片占据剩余空间
        
        # 已连接设备卡片
        device_card = self.create_device_card()
        self.vBoxLayout.addWidget(device_card)
    
    def create_sync_card(self):
        """创建同步目录卡片"""
        card = CardWidget()
        card.setStyleSheet("""
            CardWidget {
                background: white;
                border: none;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(20)
        
        # 标题
        title = BodyLabel("🔄 Syncthing 同步目录")
        title.setStyleSheet("font-size: 15px; font-weight: 600; background: transparent; border: none;")
        card_layout.addWidget(title)
        
        # 同步文件夹表格
        self.sync_folders_table = TableWidget()
        self.sync_folders_table.setColumnCount(4)
        self.sync_folders_table.setHorizontalHeaderLabels(["文件夹ID", "路径", "状态", "设备数"])
        
        # 设置表格样式：无边框、透明背景、文字无边框
        self.sync_folders_table.setStyleSheet("""
            TableWidget {
                background: white;
                border: none;
                border-radius: 4px;
            }
            QTableWidget::item {
                border: none;
                padding: 8px;
                background: transparent;
            }
            QTableWidget::item:selected {
                background: #f0f0f0;
            }
            QHeaderView::section {
                background: #f5f5f5;
                border: none;
                padding: 8px;
                font-weight: 600;
            }
        """)
        
        # 让表格自动伸展填充空间
        self.sync_folders_table.setMinimumHeight(300)
        card_layout.addWidget(self.sync_folders_table, 1)  # stretch=1，让表格占据剩余空间
        
        # 空状态提示（初始显示）
        self.empty_hint = BodyLabel("暂无同步目录\n\n请先连接到网络后点击刷新按钮")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("""
            QLabel {
                color: #999;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 60px;
            }
        """)
        card_layout.addWidget(self.empty_hint)
        self.sync_folders_table.hide()  # 初始隐藏表格
        
        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        pause_btn = PushButton("⏸️ 暂停所有")
        pause_btn.setFixedWidth(120)
        pause_btn.clicked.connect(self.pause_all_sync)
        btn_row.addWidget(pause_btn)
        
        refresh_btn = PrimaryPushButton("🔄 刷新")
        refresh_btn.setFixedWidth(120)
        refresh_btn.clicked.connect(self.refresh_sync)
        btn_row.addWidget(refresh_btn)
        
        card_layout.addLayout(btn_row)
        
        return card
    
    def create_device_card(self):
        """创建已连接设备卡片"""
        card = CardWidget()
        card.setStyleSheet("""
            CardWidget {
                background: white;
                border: none;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(20)
        
        # 标题
        title = BodyLabel("🔗 已连接设备")
        title.setStyleSheet("font-size: 15px; font-weight: 600; background: transparent; border: none;")
        card_layout.addWidget(title)
        
        # 设备表格
        self.devices_table = TableWidget()
        self.devices_table.setColumnCount(4)
        self.devices_table.setHorizontalHeaderLabels(["设备名称", "设备ID", "状态", "地址"])
        
        # 设置表格样式
        self.devices_table.setStyleSheet("""
            TableWidget {
                background: white;
                border: none;
                border-radius: 4px;
            }
            QTableWidget::item {
                border: none;
                padding: 8px;
                background: transparent;
            }
            QTableWidget::item:selected {
                background: #f0f0f0;
            }
            QHeaderView::section {
                background: #f5f5f5;
                border: none;
                padding: 8px;
                font-weight: 600;
            }
        """)
        
        self.devices_table.setMinimumHeight(150)
        self.devices_table.setMaximumHeight(250)
        card_layout.addWidget(self.devices_table)
        
        # 空状态提示
        self.device_empty_hint = BodyLabel("暂无已连接设备\n\n请确保其他设备已加入网络")
        self.device_empty_hint.setAlignment(Qt.AlignCenter)
        self.device_empty_hint.setStyleSheet("""
            QLabel {
                color: #999;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 40px;
            }
        """)
        card_layout.addWidget(self.device_empty_hint)
        self.devices_table.hide()
        
        return card
    
    def pause_all_sync(self):
        """暂停所有同步"""
        try:
            if not hasattr(self.parent_window, 'syncthing_manager') or not self.parent_window.syncthing_manager:
                InfoBar.warning(
                    title='警告',
                    content="请先连接到网络",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            config = self.parent_window.syncthing_manager.get_config()
            if not config:
                InfoBar.error(
                    title='错误',
                    content="无法获取Syncthing配置",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            folders = config.get('folders', [])
            paused_count = 0
            
            for folder in folders:
                if not folder.get('paused', False):
                    folder['paused'] = True
                    paused_count += 1
            
            if paused_count > 0:
                self.parent_window.syncthing_manager.set_config(config)
                InfoBar.success(
                    title='成功',
                    content=f"已暂停 {paused_count} 个同步文件夹",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                # 刷新列表
                self.refresh_sync()
            else:
                InfoBar.info(
                    title='提示',
                    content="所有文件夹已经是暂停状态",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            logger.error(f"暂停同步失败: {e}")
            InfoBar.error(
                title='错误',
                content=f"暂停失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def refresh_sync(self):
        """刷新同步列表和设备列表"""
        try:
            if not hasattr(self.parent_window, 'syncthing_manager') or not self.parent_window.syncthing_manager:
                InfoBar.warning(
                    title='警告',
                    content="请先连接到网络",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            # 触发所有设备重连（用于设备重新上线后重连）
            self.parent_window.syncthing_manager.restart_all_devices()
            
            # 刷新同步文件夹列表
            self.refresh_folders()
            
            # 刷新设备列表
            self.refresh_devices()
            
        except Exception as e:
            logger.error(f"刷新失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def refresh_folders(self):
        """刷新同步文件夹列表"""
        try:
            # 清空表格
            self.sync_folders_table.setRowCount(0)
            
            # 获取配置
            config = self.parent_window.syncthing_manager.get_config()
            if not config:
                return
            
            # 获取连接状态
            connections = self.parent_window.syncthing_manager.get_connections()
            connected_devices = set()
            if connections and connections.get('connections'):
                for dev_id, conn_info in connections['connections'].items():
                    if conn_info.get('connected'):
                        connected_devices.add(dev_id)
            
            # 填充表格
            folders = config.get('folders', [])
            
            # 根据是否有数据显示不同内容
            if len(folders) == 0:
                # 无数据，显示空状态提示
                self.sync_folders_table.hide()
                self.empty_hint.show()
            else:
                # 有数据，显示表格
                self.empty_hint.hide()
                self.sync_folders_table.show()
                
                for folder in folders:
                    row = self.sync_folders_table.rowCount()
                    self.sync_folders_table.insertRow(row)
                    
                    # 文件夹ID
                    id_item = QTableWidgetItem(folder.get('id', ''))
                    id_item.setTextAlignment(Qt.AlignCenter)
                    self.sync_folders_table.setItem(row, 0, id_item)
                    
                    # 路径
                    path_item = QTableWidgetItem(folder.get('path', ''))
                    self.sync_folders_table.setItem(row, 1, path_item)
                    
                    # 状态
                    status = "⏸️ 暂停" if folder.get('paused', False) else "✅ 同步中"
                    status_item = QTableWidgetItem(status)
                    status_item.setTextAlignment(Qt.AlignCenter)
                    self.sync_folders_table.setItem(row, 2, status_item)
                    
                    # 设备数统计：远程设备 + 本机
                    folder_devices = [d['deviceID'] for d in folder.get('devices', [])]
                    # 统计已连接的远程设备数
                    connected_count = sum(1 for dev_id in folder_devices if dev_id in connected_devices)
                    # 总设备数 = 远程设备数 + 1（本机）
                    total_devices = len(folder_devices) + 1
                    # 已连接设备数 = 已连接的远程设备数 + 1（本机）
                    total_connected = connected_count + 1
                    device_item = QTableWidgetItem(f"{total_connected}/{total_devices}")
                    device_item.setTextAlignment(Qt.AlignCenter)
                    self.sync_folders_table.setItem(row, 3, device_item)
                
                # 调整列宽
                from PyQt5.QtWidgets import QHeaderView
                self.sync_folders_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
                self.sync_folders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
                self.sync_folders_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
                self.sync_folders_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        except Exception as e:
            logger.error(f"刷新同步文件夹列表失败: {e}")
    
    def refresh_devices(self):
        """刷新已连接设备列表"""
        try:
            # 清空表格
            self.devices_table.setRowCount(0)
            
            # 获取配置
            config = self.parent_window.syncthing_manager.get_config()
            if not config:
                self.devices_table.hide()
                self.device_empty_hint.show()
                return
            
            # 获取连接状态
            connections = self.parent_window.syncthing_manager.get_connections()
            connected_devices = {}
            if connections and connections.get('connections'):
                connected_devices = connections['connections']
            
            # 获取EasyTier对等设备列表（用于获取虚拟IP）
            peer_ips = {}  # {hostname: ipv4}
            if hasattr(self.parent_window, 'controller') and hasattr(self.parent_window.controller, 'easytier'):
                peers = self.parent_window.controller.easytier.discover_peers(timeout=1)
                if peers:
                    for peer in peers:
                        hostname = peer.get('hostname', '')
                        ipv4 = peer.get('ipv4', '')
                        if hostname and ipv4:
                            peer_ips[hostname] = ipv4
            
            device_count = 0
            
            # 1. 首先显示本机
            my_device_id = self.parent_window.syncthing_manager.device_id
            if my_device_id:
                device_count += 1
                row = self.devices_table.rowCount()
                self.devices_table.insertRow(row)
                
                # 设备名称
                name_item = QTableWidgetItem("💻 本机")
                self.devices_table.setItem(row, 0, name_item)
                
                # 设备ID（显示更多字符）
                id_item = QTableWidgetItem(f"{my_device_id[:12]}...")
                id_item.setTextAlignment(Qt.AlignCenter)
                self.devices_table.setItem(row, 1, id_item)
                
                # 状态
                status_item = QTableWidgetItem("✅ 在线")
                status_item.setTextAlignment(Qt.AlignCenter)
                self.devices_table.setItem(row, 2, status_item)
                
                # 地址 - 获取虚拟IP
                virtual_ip = "127.0.0.1"
                if hasattr(self.parent_window, 'controller') and hasattr(self.parent_window.controller, 'easytier'):
                    virtual_ip = self.parent_window.controller.easytier.virtual_ip or "127.0.0.1"
                address_item = QTableWidgetItem(virtual_ip)
                self.devices_table.setItem(row, 3, address_item)
            
            # 2. 显示其他设备
            devices = config.get('devices', [])
            
            for device in devices:
                device_id = device.get('deviceID')
                device_name = device.get('name', device_id[:7] if device_id else '未知')
                
                # 跳过本机
                if device_id == my_device_id:
                    continue
                
                device_count += 1
                row = self.devices_table.rowCount()
                self.devices_table.insertRow(row)
                
                # 设备名称
                name_item = QTableWidgetItem(device_name)
                self.devices_table.setItem(row, 0, name_item)
                
                # 设备ID（显示更多字符）
                id_item = QTableWidgetItem(f"{device_id[:12]}...")
                id_item.setTextAlignment(Qt.AlignCenter)
                self.devices_table.setItem(row, 1, id_item)
                
                # 检查设备是否已连接
                conn_info = connected_devices.get(device_id, {})
                is_connected = conn_info.get('connected', False)
                
                # 状态
                if is_connected:
                    status_item = QTableWidgetItem("✅ 在线")
                else:
                    status_item = QTableWidgetItem("⚪ 离线")
                status_item.setTextAlignment(Qt.AlignCenter)
                self.devices_table.setItem(row, 2, status_item)
                
                # 地址 - 优先从EasyTier对等列表获取虚拟IPv4地址
                if is_connected:
                    # 尝试从EasyTier对等列表中获取虚拟IP
                    virtual_ip = peer_ips.get(device_name, '')
                    
                    if virtual_ip:
                        # 找到了虚拟IP，使用它
                        address_item = QTableWidgetItem(virtual_ip)
                    else:
                        # 没找到虚拟IP，从Syncthing连接信息获取并过滤IPv6
                        address = conn_info.get('address', '未知')
                        # 只显示IP部分，去掉端口
                        if ':' in address:
                            # 检查是否为IPv6（包含多个冒号）
                            if address.count(':') > 1:
                                # 这是IPv6地址，跳过
                                address = "-"
                            else:
                                # 这是IPv4:port格式
                                address = address.rsplit(':', 1)[0]
                        address_item = QTableWidgetItem(address)
                else:
                    address_item = QTableWidgetItem("-")
                self.devices_table.setItem(row, 3, address_item)
            
            # 根据是否有设备显示不同内容
            if device_count == 0:
                self.devices_table.hide()
                self.device_empty_hint.show()
            else:
                self.device_empty_hint.hide()
                self.devices_table.show()
                
                # 调整列宽：设备名称自适应，设备ID占用更多空间
                from PyQt5.QtWidgets import QHeaderView
                self.devices_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
                self.devices_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 设备ID占据主要空间
                self.devices_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
                self.devices_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
                
                # 移除频繁的设备列表日志
                # logger.info(f"设备列表: 总计 {device_count} 个设备")
        except Exception as e:
            logger.error(f"刷新设备列表失败: {e}")
    
    def showEvent(self, event):
        """页面显示事件：进入页面时发现设备并启动自动刷新"""
        super().showEvent(event)
        logger.info("进入存档同步页面，开始发现设备...")
        
        # 刷新页面显示
        self.refresh_sync()
        
        # 启动设备发现（只发现一次）
        if hasattr(self.parent_window, 'is_connected') and self.parent_window.is_connected:
            self._discover_devices_once()
        
        # 启动自动刷新定时器
        self.auto_refresh_timer.start()
        logger.info("已启动自动刷新，每5秒刷新一次")
    
    def hideEvent(self, event):
        """页面隐藏事件：离开页面时停止自动刷新"""
        super().hideEvent(event)
        logger.info("离开存档同步页面")
        
        # 停止自动刷新
        self.auto_refresh_timer.stop()
        logger.info("已停止自动刷新")
    
    def _auto_refresh(self):
        """自动刷新（静默刷新，不显示提示）"""
        try:
            if not hasattr(self.parent_window, 'syncthing_manager') or not self.parent_window.syncthing_manager:
                return
            
            # 静默刷新文件夹和设备列表
            self.refresh_folders()
            self.refresh_devices()
                
        except Exception as e:
            logger.error(f"自动刷新失败: {e}")
    
    def _discover_devices_once(self):
        """发现设备（只执行一次）"""
        try:
            if not hasattr(self.parent_window, 'controller') or not self.parent_window.controller:
                return
            
            if not hasattr(self.parent_window, 'syncthing_manager') or not self.parent_window.syncthing_manager:
                return
            
            # 获取对等设备列表
            peers = self.parent_window.controller.easytier.discover_peers(timeout=3)
            if not peers:
                logger.info("未发现对等设备")
                return
            
            my_syncthing_id = self.parent_window.syncthing_manager.device_id
            my_ip = self.parent_window.controller.easytier.virtual_ip or "unknown"
            
            discovered_count = 0
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
                        discovered_count += 1
                        
                        # 将设备添加到所有正在同步的文件夹
                        self._add_device_to_active_folders(device_id)
            
            if discovered_count > 0:
                logger.info(f"设备发现完成，新增 {discovered_count} 个设备")
                # 刷新设备列表
                self.refresh_devices()
            else:
                logger.info("设备发现完成，未发现新设备")
                
        except Exception as e:
            logger.error(f"设备发现失败: {e}")
    
    def _get_remote_syncthing_id(self, peer_ip):
        """获取远程设备的Syncthing ID"""
        try:
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

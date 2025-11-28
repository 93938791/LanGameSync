"""
存档同步界面
展示Syncthing同步目录列表和状态
"""
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QAbstractScrollArea
from qfluentwidgets import (
    ScrollArea, CardWidget, BodyLabel, SubtitleLabel,
    PushButton, PrimaryPushButton, TableWidget, InfoBar, InfoBarPosition
)

from utils.logger import Logger
from config import Config

logger = Logger().get_logger("SyncInterface")


class SyncInterface(ScrollArea):
    """存档同步界面"""
    
    # 定义信号用于线程间通信
    folders_data_ready = pyqtSignal(object, object)  # local_config, all_shares
    
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        
        # 连接信号
        self.folders_data_ready.connect(self._update_folders_ui)
        
        # 创建自动刷新定时器
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
        
        # 同步卡片
        sync_card = self.create_sync_card()
        self.vBoxLayout.addWidget(sync_card, 1)
        
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
        
        # 主标题
        title = BodyLabel("🔄 Syncthing 同步目录")
        title.setStyleSheet("font-size: 15px; font-weight: 600; background: transparent; border: none;")
        card_layout.addWidget(title)
        
        # ========== 第一部分：进行中的同步 ==========
        syncing_title = BodyLabel("📥 进行中的同步")
        syncing_title.setStyleSheet("font-size: 14px; font-weight: 600; background: transparent; border: none; color: #107c10;")
        card_layout.addWidget(syncing_title)
        
        # 进行中的同步表格
        self.syncing_table = TableWidget()
        self.syncing_table.setColumnCount(5)
        self.syncing_table.setHorizontalHeaderLabels(["分享名称", "来源设备", "远程路径", "本地路径", "操作"])
        self.syncing_table.horizontalHeader().setStretchLastSection(False)
        self.syncing_table.setMinimumHeight(150)
        self.syncing_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContentsOnFirstShow)
        self._setup_table_style(self.syncing_table)
        card_layout.addWidget(self.syncing_table)
        
        # 进行中的同步空状态提示
        self.syncing_empty_hint = BodyLabel("暂无进行中的同步")
        self.syncing_empty_hint.setAlignment(Qt.AlignCenter)
        self.syncing_empty_hint.setStyleSheet("color: #999; font-size: 14px; background: transparent; border: none; padding: 30px;")
        card_layout.addWidget(self.syncing_empty_hint)
        self.syncing_table.hide()
        
        # ========== 第二部分：公开的分享 ==========
        sharing_title = BodyLabel("📤 公开的分享")
        sharing_title.setStyleSheet("font-size: 14px; font-weight: 600; background: transparent; border: none; color: #0078d4;")
        card_layout.addWidget(sharing_title)
        
        # 公开的分享表格
        self.sharing_table = TableWidget()
        self.sharing_table.setColumnCount(5)
        self.sharing_table.setHorizontalHeaderLabels(["分享名称", "来源设备", "远程路径", "本地路径", "操作"])
        self.sharing_table.horizontalHeader().setStretchLastSection(False)
        self.sharing_table.setMinimumHeight(200)
        self.sharing_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContentsOnFirstShow)
        self._setup_table_style(self.sharing_table)
        card_layout.addWidget(self.sharing_table, 1)
        
        # 公开的分享空状态提示
        self.sharing_empty_hint = BodyLabel("暂无公开的分享\n\n请确保其他设备已加入分享并连接到网络")
        self.sharing_empty_hint.setAlignment(Qt.AlignCenter)
        self.sharing_empty_hint.setStyleSheet("color: #999; font-size: 14px; background: transparent; border: none; padding: 60px;")
        card_layout.addWidget(self.sharing_empty_hint)
        self.sharing_table.hide()
        
        # 刷新按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        refresh_btn = PrimaryPushButton("🔄 刷新")
        refresh_btn.setFixedWidth(120)
        refresh_btn.clicked.connect(self.refresh_sync)
        btn_row.addWidget(refresh_btn)
        card_layout.addLayout(btn_row)
        
        return card
    
    def _setup_table_style(self, table):
        """设置表格样式"""
        table.setStyleSheet("""
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
        self.devices_table.setMinimumHeight(150)
        self.devices_table.setMaximumHeight(250)
        self._setup_table_style(self.devices_table)
        card_layout.addWidget(self.devices_table)
        
        # 空状态提示
        self.device_empty_hint = BodyLabel("暂无已连接设备\n\n请确保其他设备已加入网络")
        self.device_empty_hint.setAlignment(Qt.AlignCenter)
        self.device_empty_hint.setStyleSheet("color: #999; font-size: 14px; background: transparent; border: none; padding: 40px;")
        card_layout.addWidget(self.device_empty_hint)
        self.devices_table.hide()
        
        return card
    
    def start_sync_folder(self, button):
        """开始同步文件夹"""
        try:
            folder_info = button.folder_info
            folder_id = folder_info.get('id')
            folder_label = folder_info.get('label', folder_id)
            device_id = folder_info.get('device_id')
            
            # 检查是否已连接网络
            if not hasattr(self.parent_window, 'is_connected') or not self.parent_window.is_connected:
                InfoBar.warning(
                    title='提示',
                    content="请先连接到网络！",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            # 让用户选择存放目录
            from PyQt5.QtWidgets import QFileDialog
            save_dir = QFileDialog.getExistingDirectory(
                self,
                f"选择「{folder_label}」的存放目录",
                "",
                QFileDialog.ShowDirsOnly
            )
            
            if not save_dir:
                return
            
            # 检查目录是否存在，不存在则创建
            from pathlib import Path
            save_path = Path(save_dir)
            if not save_path.exists():
                save_path.mkdir(parents=True, exist_ok=True)
            
            # 添加同步文件夹
            success = self.parent_window.syncthing_manager.add_folder(
                folder_path=str(save_path),
                folder_id=folder_id,
                folder_label=folder_label,
                devices=[device_id],
                paused=False,
                async_mode=False
            )
            
            if success:
                InfoBar.success(
                    title='成功',
                    content=f"已开始同步「{folder_label}」到 {save_dir}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                # 使用 QTimer 延迟刷新，避免阻塞主线程
                QTimer.singleShot(1000, self.refresh_folders)
            else:
                InfoBar.error(
                    title='错误',
                    content="同步失败，请检查配置",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            logger.error(f"开始同步失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            InfoBar.error(
                title='错误',
                content=f"同步失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def cancel_share(self, button):
        """取消分享（暂停本机分享的文件夹）"""
        try:
            folder_id = button.folder_id
            folder_label = button.folder_info.get('label', folder_id)
            
            # 暂停文件夹（停止分享）
            success = self.parent_window.syncthing_manager.pause_folder(folder_id)
            
            if success:
                InfoBar.success(
                    title='成功',
                    content=f"已取消分享「{folder_label}」",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                # 使用 QTimer 延迟刷新，避免阻塞主线程
                QTimer.singleShot(1000, self.refresh_folders)
            else:
                InfoBar.error(
                    title='错误',
                    content="取消分享失败",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            logger.error(f"取消分享失败: {e}")
            InfoBar.error(
                title='错误',
                content=f"取消分享失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def stop_sync_folder(self, button):
        """停止同步文件夹"""
        try:
            folder_id = button.folder_id
            folder_label = button.folder_info.get('label', folder_id)
            
            # 暂停文件夹
            success = self.parent_window.syncthing_manager.pause_folder(folder_id)
            
            if success:
                InfoBar.success(
                    title='成功',
                    content=f"已停止同步「{folder_label}」",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                # 使用 QTimer 延迟刷新，避免阻塞主线程
                QTimer.singleShot(1000, self.refresh_folders)
            else:
                InfoBar.error(
                    title='错误',
                    content="停止同步失败",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            logger.error(f"停止同步失败: {e}")
            InfoBar.error(
                title='错误',
                content=f"停止同步失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
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
            
            # 在后台线程中获取数据
            import threading
            def refresh_thread():
                try:
                    self._update_device_addresses()
                    from PyQt5.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(self, "_refresh_ui_safe", Qt.QueuedConnection)
                except Exception as e:
                    logger.error(f"后台刷新失败: {e}")
            
            threading.Thread(target=refresh_thread, daemon=True, name="SyncRefreshThread").start()
            
        except Exception as e:
            logger.error(f"刷新失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    @pyqtSlot()
    def _refresh_ui_safe(self):
        """线程安全的UI刷新（避免重复刷新）"""
        try:
            # 使用 QTimer 延迟刷新，避免在 start_sync 执行期间立即刷新导致卡顿
            QTimer.singleShot(100, lambda: (self.refresh_folders(), self.refresh_devices()))
        except Exception as e:
            logger.error(f"UI刷新失败: {e}")
    
    def refresh_folders(self):
        """刷新同步文件夹列表（在后台线程执行，避免阻塞UI）"""
        # 在后台线程中执行耗时操作
        import threading
        def refresh_in_thread():
            try:
                # 获取数据（耗时操作）
                local_config = self.parent_window.syncthing_manager.get_config()
                all_shares = self._get_all_shares()  # 使用正确的方法名
                
                # 通过信号发送数据到主线程
                self.folders_data_ready.emit(local_config, all_shares)
            except Exception as e:
                logger.error(f"后台刷新文件夹列表失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        threading.Thread(target=refresh_in_thread, daemon=True, name="RefreshFoldersThread").start()
    
    def _update_folders_ui(self, local_config, all_shares):
        """在主线程中更新UI（线程安全）"""
        try:
            # 清空表格
            self.syncing_table.setRowCount(0)
            self.sharing_table.setRowCount(0)
            
            # 获取本地已同步的文件夹（未暂停的）
            syncing_folder_ids = set()
            local_folder_paths = {}
            
            if local_config:
                my_device_id = self.parent_window.syncthing_manager.device_id
                for folder in local_config.get('folders', []):
                    if not folder.get('paused', False):
                        folder_id = folder.get('id')
                        syncing_folder_ids.add(folder_id)
                        local_folder_paths[folder_id] = folder.get('path', '')
            
            # all_shares 已经从参数传入，不需要再次获取
            
            # 分离：进行中的同步 vs 公开的分享
            syncing_list = []  # 进行中的同步：从其他设备同步过来的
            sharing_list = []  # 公开的分享：所有未同步的分享（包括本机分享）
            
            my_device_id = self.parent_window.syncthing_manager.device_id
            
            for share in all_shares:
                folder_id = share.get('id')
                is_my_share = share.get('is_my_share', False)
                share_device_id = share.get('device_id')
                
                # 判断是否在同步中
                is_syncing = folder_id in syncing_folder_ids
                
                if is_my_share:
                    # 本机分享：始终显示在"公开的分享"中
                    sharing_list.append(share)
                else:
                    # 其他设备的分享
                    if is_syncing:
                        # 已同步：显示在"进行中的同步"
                        syncing_list.append(share)
                    else:
                        # 未同步：显示在"公开的分享"
                        sharing_list.append(share)
            
            logger.info(f"刷新列表：进行中的同步 {len(syncing_list)} 个，公开的分享 {len(sharing_list)} 个")
            
            # 显示"进行中的同步"
            if len(syncing_list) == 0:
                self.syncing_table.hide()
                self.syncing_empty_hint.show()
            else:
                self.syncing_empty_hint.hide()
                self.syncing_table.show()
                self._populate_table(self.syncing_table, syncing_list, local_folder_paths, show_stop_button=True)
            
            # 显示"公开的分享"
            if len(sharing_list) == 0:
                self.sharing_table.hide()
                self.sharing_empty_hint.show()
            else:
                self.sharing_empty_hint.hide()
                self.sharing_table.show()
                self._populate_table(self.sharing_table, sharing_list, local_folder_paths, show_stop_button=False)
                
        except Exception as e:
            logger.error(f"刷新同步文件夹列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _populate_table(self, table, shares, local_folder_paths, show_stop_button):
        """填充表格数据"""
        for share in shares:
            row = table.rowCount()
            table.insertRow(row)
            
            folder_id = share.get('id')
            folder_label = share.get('label', folder_id)
            device_name = share.get('device_name', '未知设备')
            device_id = share.get('device_id')
            remote_path = share.get('path', '')
            is_my_share = share.get('is_my_share', False)
            
            # 分享名称
            table.setItem(row, 0, QTableWidgetItem(folder_label))
            
            # 来源设备
            if is_my_share:
                device_display_name = "💻 本机"
            else:
                # 尝试从配置获取设备名称
                device_display_name = device_name
                if device_name == 'Unknown' or not device_name:
                    if device_id:
                        config = self.parent_window.syncthing_manager.get_config()
                        if config:
                            for dev in config.get('devices', []):
                                if dev.get('deviceID') == device_id:
                                    real_name = dev.get('name', '')
                                    if real_name:
                                        device_display_name = real_name
                                        break
                    if device_display_name == 'Unknown' or not device_display_name:
                        device_display_name = "未知设备"
            
            table.setItem(row, 1, QTableWidgetItem(device_display_name))
            
            # 远程路径
            table.setItem(row, 2, QTableWidgetItem(remote_path))
            
            # 本地路径
            local_path = local_folder_paths.get(folder_id, '-')
            table.setItem(row, 3, QTableWidgetItem(local_path))
            
            # 操作按钮
            from PyQt5.QtWidgets import QWidget, QHBoxLayout
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(5, 2, 5, 2)
            btn_layout.setAlignment(Qt.AlignCenter)
            
            if is_my_share:
                # 本机分享：显示"取消分享"按钮
                btn = PushButton("❌ 取消分享")
                btn.setFixedWidth(100)
                btn.folder_info = share
                btn.folder_id = folder_id
                btn.clicked.connect(lambda checked, b=btn: self.cancel_share(b))
                btn_layout.addWidget(btn)
            else:
                # 其他设备分享：显示按钮
                if show_stop_button:
                    # 进行中的同步：显示"停止"按钮
                    btn = PushButton("⏸️ 停止")
                    btn.setFixedWidth(80)
                    btn.folder_info = share
                    btn.folder_id = folder_id
                    btn.clicked.connect(lambda checked, b=btn: self.stop_sync_folder(b))
                else:
                    # 公开的分享：显示"同步"按钮
                    btn = PushButton("✅ 同步")
                    btn.setFixedWidth(80)
                    btn.folder_info = share
                    btn.folder_id = folder_id
                    btn.clicked.connect(lambda checked, b=btn: self.start_sync_folder(b))
                btn_layout.addWidget(btn)
            
            table.setCellWidget(row, 4, btn_widget)
        
        # 调整列宽
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        table.resizeColumnsToContents()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
    
    def _get_all_shares(self):
        """获取所有可用的分享（包括本机分享和其他设备的分享）"""
        all_shares = []
        
        try:
            my_device_id = self.parent_window.syncthing_manager.device_id
            if not my_device_id:
                return all_shares
            
            # 1. 获取本机的分享（只显示游戏管理中配置的分享）
            from utils.config_cache import ConfigCache
            config_data = ConfigCache.load()
            game_list = config_data.get("game_list", [])
            
            # 获取所有游戏管理中已加入分享的文件夹ID
            game_folder_ids = set()
            for game in game_list:
                if game.get('is_syncing', False):
                    folder_id = game.get('sync_folder_id')
                    if folder_id:
                        game_folder_ids.add(folder_id)
            
            # 从Syncthing配置中获取本机分享，但只显示游戏管理中配置的
            full_config = self.parent_window.syncthing_manager.get_config(filter_self=False)
            if full_config:
                for folder in full_config.get('folders', []):
                    folder_id = folder.get('id')
                    # 只显示未暂停且在游戏管理中配置的文件夹
                    if not folder.get('paused', False) and folder_id in game_folder_ids:
                        folder_devices = [d.get('deviceID') for d in folder.get('devices', [])]
                        other_devices = [d for d in folder_devices if d != my_device_id]
                        if len(other_devices) > 0:  # 有共享给其他设备
                            all_shares.append({
                                'id': folder_id,
                                'label': folder.get('label', folder_id),
                                'path': folder.get('path'),
                                'device_id': my_device_id,
                                'device_ip': '127.0.0.1',
                                'device_name': '本机',
                                'is_my_share': True
                            })
            
            # 2. 获取远程设备的分享
            connections = self.parent_window.syncthing_manager.get_connections()
            if not connections or not connections.get('connections'):
                return all_shares
            
            config = self.parent_window.syncthing_manager.get_config()
            if not config:
                return all_shares
            
            # 获取EasyTier对等设备列表
            peer_ips = {}
            peers = None
            if hasattr(self.parent_window, 'controller') and hasattr(self.parent_window.controller, 'easytier'):
                peers = self.parent_window.controller.easytier.discover_peers(timeout=1)  # 减少超时时间，避免阻塞
                if peers:
                    for peer in peers:
                        hostname = peer.get('hostname', '')
                        ipv4 = peer.get('ipv4', '')
                        if hostname and ipv4:
                            peer_ips[hostname] = ipv4
            
            # 遍历所有已连接的设备
            for device in config.get('devices', []):
                device_id = device.get('deviceID')
                device_name = device.get('name', '')
                
                if device_id == my_device_id:
                    continue
                
                # 检查设备是否已连接
                conn_info = connections['connections'].get(device_id, {})
                if not conn_info.get('connected', False):
                    continue
                
                # 获取设备的虚拟IP
                device_ip = self._get_device_ip(device_id, device_name, peer_ips, peers, conn_info)
                if not device_ip:
                    continue
                
                # 获取远程设备的文件夹列表
                remote_folders = self.parent_window.syncthing_manager.get_remote_device_folders(device_ip, device_id)
                if remote_folders:
                    for folder in remote_folders:
                        folder['is_my_share'] = False
                    all_shares.extend(remote_folders)
            
            return all_shares
            
        except Exception as e:
            logger.error(f"获取所有分享失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return all_shares
    
    def _get_device_ip(self, device_id, device_name, peer_ips, peers, conn_info):
        """获取设备的虚拟IP"""
        device_ip = None
        
        # 方法1：快速匹配
        if device_name in peer_ips:
            candidate_ip = peer_ips[device_name]
            try:
                import requests
                url = f"http://{candidate_ip}:{Config.SYNCTHING_API_PORT}/rest/system/status"
                headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
                resp = requests.get(url, headers=headers, timeout=2)
                if resp.status_code == 200:
                    remote_device_id = resp.json().get('myID', '')
                    if remote_device_id == device_id:
                        device_ip = candidate_ip
            except:
                pass
        
        # 方法2：遍历匹配
        if not device_ip and peers:
            import concurrent.futures
            def check_peer(peer):
                peer_ipv4 = peer.get('ipv4', '')
                if not peer_ipv4:
                    return None
                try:
                    import requests
                    url = f"http://{peer_ipv4}:{Config.SYNCTHING_API_PORT}/rest/system/status"
                    headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
                    resp = requests.get(url, headers=headers, timeout=2)
                    if resp.status_code == 200:
                        remote_device_id = resp.json().get('myID', '')
                        if remote_device_id == device_id:
                            return peer_ipv4
                except:
                    pass
                return None
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(check_peer, peer): peer for peer in peers}
                for future in concurrent.futures.as_completed(futures):
                    result_ip = future.result()
                    if result_ip:
                        device_ip = result_ip
                        for f in futures:
                            f.cancel()
                        break
        
        # 方法3：从连接信息获取（只接受虚拟IP）
        if not device_ip:
            address = conn_info.get('address', '')
            if address and '://' in address:
                parts = address.split('://')
                if len(parts) > 1:
                    ip_part = parts[1].split(':')[0]
                    if '.' in ip_part and ip_part.count('.') == 3:
                        if ip_part.startswith('10.126.126.'):
                            device_ip = ip_part
        
        return device_ip
    
    def refresh_devices(self):
        """刷新设备列表"""
        try:
            self.devices_table.setRowCount(0)
            
            if not hasattr(self.parent_window, 'syncthing_manager') or not self.parent_window.syncthing_manager:
                self.devices_table.hide()
                self.device_empty_hint.show()
                return
            
            config = self.parent_window.syncthing_manager.get_config()
            if not config:
                self.devices_table.hide()
                self.device_empty_hint.show()
                return
            
            connections = self.parent_window.syncthing_manager.get_connections()
            if not connections:
                self.devices_table.hide()
                self.device_empty_hint.show()
                return
            
            my_device_id = self.parent_window.syncthing_manager.device_id
            connected_devices = connections.get('connections', {})
            
            # 获取EasyTier对等设备列表
            peer_ips = {}
            if hasattr(self.parent_window, 'controller') and hasattr(self.parent_window.controller, 'easytier'):
                peers = self.parent_window.controller.easytier.discover_peers(timeout=1)  # 减少超时时间，避免阻塞
                if peers:
                    for peer in peers:
                        hostname = peer.get('hostname', '')
                        ipv4 = peer.get('ipv4', '')
                        if hostname and ipv4:
                            peer_ips[hostname] = ipv4
            
            # 添加本机
            if my_device_id:
                row = self.devices_table.rowCount()
                self.devices_table.insertRow(row)
                self.devices_table.setItem(row, 0, QTableWidgetItem("💻 本机"))
                self.devices_table.setItem(row, 1, QTableWidgetItem(my_device_id))
                self.devices_table.setItem(row, 2, QTableWidgetItem("✅ 已连接"))
                self.devices_table.setItem(row, 3, QTableWidgetItem("127.0.0.1"))
            
            # 添加其他设备（只显示真正在线的设备）
            for device in config.get('devices', []):
                device_id = device.get('deviceID')
                device_name = device.get('name', device_id[:7] if device_id else '未知')
                
                if device_id == my_device_id:
                    continue
                
                conn_info = connected_devices.get(device_id, {})
                is_connected = conn_info.get('connected', False)
                
                # 只显示真正在线的设备（connected=True）
                if not is_connected:
                    continue
                
                row = self.devices_table.rowCount()
                self.devices_table.insertRow(row)
                self.devices_table.setItem(row, 0, QTableWidgetItem(device_name))
                self.devices_table.setItem(row, 1, QTableWidgetItem(device_id))
                self.devices_table.setItem(row, 2, QTableWidgetItem("✅ 已连接"))
                
                # 获取虚拟IP
                virtual_ip = peer_ips.get(device_name, '')
                self.devices_table.setItem(row, 3, QTableWidgetItem(virtual_ip if virtual_ip else "-"))
            
            if self.devices_table.rowCount() > 0:
                self.device_empty_hint.hide()
                self.devices_table.show()
            else:
                self.devices_table.hide()
                self.device_empty_hint.show()
                
        except Exception as e:
            logger.error(f"刷新设备列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _update_device_addresses(self):
        """更新设备地址（用于设备IP变化后重新配置）"""
        try:
            if not hasattr(self.parent_window, 'controller'):
                return
            # 更新设备地址的逻辑（如果需要）
        except Exception as e:
            logger.error(f"更新设备地址失败: {e}")
    
    def _auto_refresh(self):
        """自动刷新"""
        if hasattr(self.parent_window, 'is_connected') and self.parent_window.is_connected:
            self.refresh_sync()
    
    def showEvent(self, event):
        """显示事件（异步刷新，避免卡顿）"""
        super().showEvent(event)
        # 使用 QTimer 延迟刷新，避免切换菜单时卡顿
        QTimer.singleShot(300, lambda: (self.refresh_sync(), self.auto_refresh_timer.start()))
    
    def hideEvent(self, event):
        """隐藏事件"""
        super().hideEvent(event)
        self.auto_refresh_timer.stop()

"""
游戏管理页面
"""
from PyQt5.QtCore import Qt, pyqtSlot, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel, QTableWidgetItem
from PyQt5.QtGui import QPixmap
from qfluentwidgets import (
    ScrollArea, CardWidget, BodyLabel, SubtitleLabel, CaptionLabel,
    PrimaryPushButton, PushButton, TableWidget, ElevatedCardWidget,
    InfoBar, InfoBarPosition, IconWidget, FluentIcon
)
import os

from utils.logger import Logger

logger = Logger().get_logger("GameInterface")


class GameInterface(QWidget):
    """游戏管理界面 - 左右布局：左侧游戏列表，右侧存档详情"""
    
    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
        self.selected_game = None
        
        # 设置全局唯一的对象名称（必须）
        self.setObjectName("gameInterface")
        
        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 左侧：游戏列表
        self.create_left_panel(main_layout)
        
        # 右侧：存档详情
        self.create_right_panel(main_layout)
    
    def create_left_panel(self, parent_layout):
        """创建左侧游戏列表面板"""
        left_card = CardWidget()
        left_card.setFixedWidth(280)
        
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        title_icon = IconWidget(FluentIcon.GAME)
        title_icon.setFixedSize(24, 24)
        header_layout.addWidget(title_icon)
        
        title = SubtitleLabel("游戏列表")
        title.setStyleSheet("font-weight: 600; margin-left: 6px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        left_layout.addLayout(header_layout)
        
        # 游戏列表
        self.game_list = QListWidget()
        self.game_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 10px;
                border-radius: 6px;
                margin: 3px 2px;
                border: 1px solid #e5e5e5;
                background: #fafafa;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 120, 212, 0.15),
                    stop:1 rgba(0, 120, 212, 0.08));
                color: #0078d4;
                border: 1px solid #0078d4;
                border-left: 3px solid #0078d4;
            }
            QListWidget::item:hover {
                background: #f0f0f0;
                border: 1px solid #d0d0d0;
            }
        """)
        self.game_list.itemClicked.connect(self.on_game_selected)
        left_layout.addWidget(self.game_list)
        
        # 按钮区
        btn_layout = QHBoxLayout()
        
        add_game_btn = PrimaryPushButton(FluentIcon.ADD, "添加游戏存档")
        add_game_btn.setFixedHeight(36)
        add_game_btn.clicked.connect(self.add_game)
        btn_layout.addWidget(add_game_btn)
        
        left_layout.addLayout(btn_layout)
        
        parent_layout.addWidget(left_card)
        
        # 加载游戏列表
        self.load_game_list()
    
    def create_right_panel(self, parent_layout):
        """创建右侧存档详情面板"""
        right_card = CardWidget()
        
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(16)
        
        # 空状态显示
        self.empty_state = self.create_empty_state()
        right_layout.addWidget(self.empty_state)
        
        # 游戏信息区域
        self.game_info_card = self.create_game_info_area()
        right_layout.addWidget(self.game_info_card)
        
        # 存档列表区域
        self.saves_area = self.create_saves_area()
        right_layout.addWidget(self.saves_area)
        
        # 操作按钮区
        self.action_buttons = self.create_action_buttons()
        right_layout.addWidget(self.action_buttons)
        
        parent_layout.addWidget(right_card)
    
    def create_empty_state(self):
        """创建空状态显示"""
        container = QWidget()
        container.setVisible(True)  # 默认显示
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        
        # 空状态图片
        empty_image = QLabel()
        empty_image.setAlignment(Qt.AlignCenter)
        
        # 加载 empty.png
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources', 'icons')
        empty_path = os.path.join(icon_dir, 'empty.png')
        if os.path.exists(empty_path):
            pixmap = QPixmap(empty_path)
            # 设置图片大小，保持宽高比
            scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            empty_image.setPixmap(scaled_pixmap)
        else:
            # 如果图片不存在，显示文字
            empty_image.setText("🎮")
            empty_image.setStyleSheet("font-size: 120px; color: #e0e0e0;")
        
        layout.addStretch()
        layout.addWidget(empty_image)
        layout.addStretch()
        
        return container
    
    def create_game_info_area(self):
        """创建游戏信息区域"""
        card = CardWidget()
        card.setVisible(False)  # 默认隐藏
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 游戏信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        self.game_name_label = SubtitleLabel("")
        self.game_name_label.setStyleSheet("font-weight: 600; font-size: 16px;")
        info_layout.addWidget(self.game_name_label)
        
        self.game_path_label = CaptionLabel("")
        self.game_path_label.setStyleSheet("color: #666666; font-size: 12px;")
        info_layout.addWidget(self.game_path_label)
        
        # 同步状态标签
        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        
        self.sync_status_icon = IconWidget(FluentIcon.SYNC)
        self.sync_status_icon.setFixedSize(16, 16)
        status_layout.addWidget(self.sync_status_icon)
        
        self.sync_status_label = BodyLabel("")
        self.sync_status_label.setStyleSheet("color: #107c10; font-size: 13px; font-weight: 500;")
        status_layout.addWidget(self.sync_status_label)
        status_layout.addStretch()
        
        info_layout.addLayout(status_layout)
        info_layout.addStretch()
        
        layout.addLayout(info_layout, 1)
        
        return card
    
    def create_saves_area(self):
        """创建存档列表区域"""
        card = CardWidget()
        card.setVisible(False)  # 默认隐藏
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 标题
        header = QHBoxLayout()
        
        saves_title = SubtitleLabel("文件列表")
        saves_title.setStyleSheet("font-weight: 600;")
        header.addWidget(saves_title)
        header.addStretch()
        
        layout.addLayout(header)
        
        # 文件列表表格
        self.saves_table = TableWidget()
        self.saves_table.setColumnCount(2)
        self.saves_table.setHorizontalHeaderLabels(["文件名", "修改时间"])
        self.saves_table.setFixedHeight(260)
        self.saves_table.verticalHeader().setVisible(False)
        
        # 设置表格自适应拉伸
        from PyQt5.QtWidgets import QHeaderView
        self.saves_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # 存档名称列自适应
        self.saves_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 更新时间列自适应内容
        
        layout.addWidget(self.saves_table)
        
        return card
    
    def create_action_buttons(self):
        """创建操作按钮区"""
        card = CardWidget()
        card.setVisible(False)  # 默认隐藏
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # 加入分享
        self.sync_btn = PushButton(FluentIcon.SYNC, "加入分享")
        self.sync_btn.setFixedHeight(40)
        self.sync_btn.clicked.connect(self.toggle_sync)
        layout.addWidget(self.sync_btn)
        
        layout.addStretch()
        
        # 停止分享
        self.delete_game_btn = PushButton(FluentIcon.DELETE, "停止分享")
        self.delete_game_btn.setFixedHeight(40)
        self.delete_game_btn.clicked.connect(self.delete_game)
        self.delete_game_btn.setStyleSheet("""
            PushButton {
                color: #d13438;
                border: 1px solid rgba(209, 52, 56, 0.3);
            }
            PushButton:hover {
                background: rgba(209, 52, 56, 0.1);
                border: 1px solid #d13438;
            }
            PushButton:pressed {
                background: rgba(209, 52, 56, 0.2);
            }
        """)
        layout.addWidget(self.delete_game_btn)
        
        return card
    
    def load_game_list(self):
        """加载游戏列表"""
        from utils.config_cache import ConfigCache
        
        self.game_list.clear()
        config_data = ConfigCache.load()
        game_list = config_data.get("game_list", [])
        
        if not game_list:
            # 无游戏，显示提示
            item = QListWidgetItem("⚠️ 暂无游戏\n点击下方按钮添加")
            item.setForeground(Qt.gray)
            self.game_list.addItem(item)
            return
        
        for game in game_list:
            item = QListWidgetItem()
            # 只显示游戏名称，不显示同步状态（状态在详情中显示）
            item.setText(game.get('name', '未命名'))
            item.setData(Qt.UserRole, game)
            self.game_list.addItem(item)
    
    def on_game_selected(self, item):
        """游戏选中事件"""
        game_data = item.data(Qt.UserRole)
        if not game_data:
            return
        
        self.selected_game = game_data
        
        # 隐藏空状态
        self.empty_state.setVisible(False)
        
        # 显示游戏信息
        self.game_info_card.setVisible(True)
        self.game_name_label.setText(game_data.get('name', '未命名'))
        self.game_path_label.setText(game_data.get('save_path', ''))
        
        # 检查实际的同步状态（从 Syncthing 获取）
        is_syncing = self._check_actual_sync_status(game_data)
                
        # 同步更新 selected_game 中的状态（关键修复：确保 toggle_sync 可以正确判断）
        self.selected_game['is_syncing'] = is_syncing
                
        sync_status = "🔄 已加入分享" if is_syncing else "⚪ 未加入分享"
        self.sync_status_label.setText(sync_status)
        self.sync_status_label.setStyleSheet(f"color: {'#107c10' if is_syncing else '#999999'}; font-size: 13px; font-weight: 500;")
        
        # 更新同步状态图标
        if is_syncing:
            self.sync_status_icon.setIcon(FluentIcon.ACCEPT)
        else:
            self.sync_status_icon.setIcon(FluentIcon.CANCEL)
        
            # 更新同步按钮文本
        if is_syncing:
            self.sync_btn.setText("⏸️ 停止分享")
        else:
            self.sync_btn.setText("✅ 加入分享")
        
        # 显示文件列表和操作按钮
        self.load_file_list(game_data)
        self.saves_area.setVisible(True)
        self.action_buttons.setVisible(True)
    
    def add_game(self):
        """添加游戏 - 直接选择目录"""
        from PyQt5.QtWidgets import QFileDialog
        from utils.config_cache import ConfigCache
        
        # 直接选择游戏目录
        game_dir = QFileDialog.getExistingDirectory(
            self,
            "选择游戏目录",
            "",
            QFileDialog.ShowDirsOnly
        )
        if game_dir:
            # 保存到配置
            config_data = ConfigCache.load()
            game_list = config_data.get("game_list", [])
            game_list.append({
                "name": os.path.basename(game_dir),
                "type": "other",
                "save_path": game_dir,
                "is_syncing": False
            })
            config_data["game_list"] = game_list
            ConfigCache.save(config_data)
            
            InfoBar.success(
                title='成功',
                content=f"已添加游戏：{os.path.basename(game_dir)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            # 重新加载游戏列表
            self.load_game_list()
    
    def load_saves_list(self, game_data):
        """加载存档列表（保留兼容性）"""
        self.load_file_list(game_data)
    
    def load_file_list(self, game_data):
        """加载目录文件列表（包括文件和文件夹）"""
        import datetime
        
        self.saves_table.setRowCount(0)
        
        save_path = game_data.get('save_path')
        if not save_path or not os.path.exists(save_path):
            return
        
        # 扫描目录中的所有文件和文件夹
        try:
            items = []
            for item in os.listdir(save_path):
                item_path = os.path.join(save_path, item)
                try:
                    # 获取最后修改时间
                    mtime = os.path.getmtime(item_path)
                    update_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 标记是文件还是文件夹
                    if os.path.isdir(item_path):
                        display_name = f"📁 {item}"
                    else:
                        display_name = f"📄 {item}"
                    
                    items.append((display_name, update_time, mtime))
                except Exception as e:
                    logger.warning(f"无法获取文件信息 {item_path}: {e}")
                    continue
            
            # 按修改时间排序（最新的在前）
            items.sort(key=lambda x: x[2], reverse=True)
            
            # 填充表格
            self.saves_table.setRowCount(len(items))
            for i, (item_name, update_time, _) in enumerate(items):
                self.saves_table.setItem(i, 0, QTableWidgetItem(item_name))
                time_item = QTableWidgetItem(update_time)
                time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.saves_table.setItem(i, 1, time_item)
        except Exception as e:
            logger.error(f"加载文件列表失败: {e}")
    
    
    
    @pyqtSlot(bool)
    def toggle_sync(self, checked=False):
        """切换同步状态"""
        if not self.selected_game:
            InfoBar.warning(
                title='提示',
                content="请先选择游戏",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        is_syncing = self.selected_game.get('is_syncing', False)
        
        if is_syncing:
            # 停止同步
            self.stop_sync()
        else:
            # 启动同步
            self.start_sync()
    
    def start_sync(self):
        """启动同步"""
        from utils.config_cache import ConfigCache
        
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
        
        # 检查Syncthing是否启动
        if not hasattr(self.parent_window, 'syncthing_manager') or not self.parent_window.syncthing_manager:
            InfoBar.warning(
                title='提示',
                content="Syncthing服务未启动，请先连接网络！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        try:
            game_name = self.selected_game.get('name')
            save_path = self.selected_game.get('save_path')
            
            if not save_path:
                InfoBar.error(
                    title='错误',
                    content="无法获取存档路径",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            logger.info(f"启用同步: {game_name}, 路径: {save_path}")
            
            # 生成文件夹ID
            folder_id = f"game-{self.selected_game.get('type', 'unknown')}-{self.selected_game.get('version', 'default')}".replace(' ', '-').replace('.', '-')
            folder_label = f"{game_name} - 存档同步"
            
            # 获取Syncthing配置中的所有设备（不管是否已连接）
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
            
            # 获取已连接的设备列表
            connections = self.parent_window.syncthing_manager.get_connections()
            connected_device_ids = set()
            if connections and connections.get('connections'):
                for dev_id, conn_info in connections['connections'].items():
                    if conn_info.get('connected'):
                        connected_device_ids.add(dev_id)
            
            logger.info(f"当前在线设备数: {len(connected_device_ids)}")
            
            # 检查文件夹是否已存在
            folder_exists = False
            for folder in config.get('folders', []):
                if folder.get('id') == folder_id:
                    folder_exists = True
                    logger.info(f"文件夹已存在: {folder_id}，直接恢复同步")
                    break
            
            if folder_exists:
                # 文件夹已存在，直接恢复同步
                success = self.parent_window.syncthing_manager.resume_folder(folder_id)
                if not success:
                    InfoBar.error(
                        title='错误',
                        content="恢复同步失败",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    return
                
                # 使用 QTimer 延迟验证，避免阻塞主线程
                def verify_folder():
                    try:
                        # 验证文件夹是否成功恢复
                        config_verify = self.parent_window.syncthing_manager.get_config()
                        if config_verify:
                            for folder in config_verify.get('folders', []):
                                if folder.get('id') == folder_id:
                                    is_paused = folder.get('paused', True)
                                    if is_paused:
                                        InfoBar.error(
                                            title='错误',
                                            content="文件夹恢复失败，仍处于暂停状态",
                                            orient=Qt.Horizontal,
                                            isClosable=True,
                                            position=InfoBarPosition.TOP,
                                            duration=3000,
                                            parent=self
                                        )
                                        return
                                    logger.info(f"文件夹已成功恢复: {folder_id}, 暂停状态: {is_paused}")
                                    # 通知存档同步页面刷新（延迟执行，避免卡顿）
                                    if hasattr(self.parent_window, 'sync_interface'):
                                        QTimer.singleShot(500, self.parent_window.sync_interface.refresh_sync)
                                    break
                    except Exception as e:
                        logger.error(f"验证文件夹失败: {e}")
                
                QTimer.singleShot(2000, verify_folder)
            else:
                # 文件夹不存在，需要创建
                # 获取所有设备ID（除了本机）
                my_device_id = self.parent_window.syncthing_manager.device_id
                device_ids = []
                for device in config.get('devices', []):
                    dev_id = device.get('deviceID')
                    if dev_id and dev_id != my_device_id:
                        device_ids.append(dev_id)
                            
                logger.info(f"将同步文件夹共享给 {len(device_ids)} 个设备")
                
                # 检查是否有在线设备
                online_device_count = sum(1 for dev_id in device_ids if dev_id in connected_device_ids)
                logger.info(f"其中在线设备: {online_device_count}/{len(device_ids)}")
                            
                if len(device_ids) == 0:
                    InfoBar.warning(
                        title='提示',
                        content="没有检测到其他设备，请确保其他玩家已连接到同一房间",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                elif online_device_count == 0:
                    InfoBar.warning(
                        title='提示',
                        content=f"检测到 {len(device_ids)} 个设备，但均未在线。同步将在设备上线后自动开始。",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=4000,
                        parent=self
                    )
                
                # 添加同步文件夹（直接启用）
                success = self.parent_window.syncthing_manager.add_folder(
                    folder_path=save_path,
                    folder_id=folder_id,
                    folder_label=folder_label,
                    devices=device_ids,
                    paused=False,  # 直接启用同步
                    async_mode=False  # 同步执行，确保配置成功
                )
                
                if not success:
                    InfoBar.error(
                        title='错误',
                        content="添加同步文件夹失败",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    return
                
                # 使用 QTimer 延迟验证，避免阻塞主线程
                def verify_folder_added():
                    try:
                        # 验证文件夹是否成功添加
                        config_verify = self.parent_window.syncthing_manager.get_config()
                        folder_added = False
                        if config_verify:
                            for folder in config_verify.get('folders', []):
                                if folder.get('id') == folder_id:
                                    folder_added = True
                                    is_paused = folder.get('paused', True)
                                    logger.info(f"文件夹已添加: {folder_id}, 暂停状态: {is_paused}")
                                    break
                        
                        if not folder_added:
                            InfoBar.error(
                                title='错误',
                                content="文件夹配置验证失败，请检查Syncthing状态",
                                orient=Qt.Horizontal,
                                isClosable=True,
                                position=InfoBarPosition.TOP,
                                duration=3000,
                                parent=self
                            )
                            # 恢复状态
                            self.selected_game['is_syncing'] = False
                            self.sync_btn.setText("✅ 加入分享")
                            self.sync_status_label.setText("⚪ 未加入分享")
                            return
                        
                        # 通知存档同步页面刷新（延迟执行，避免卡顿）
                        if hasattr(self.parent_window, 'sync_interface'):
                            QTimer.singleShot(500, self.parent_window.sync_interface.refresh_sync)
                    except Exception as e:
                        logger.error(f"验证文件夹添加失败: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                QTimer.singleShot(2000, verify_folder_added)
                # 先更新UI，不等待验证
                self.selected_game['is_syncing'] = True
                self.selected_game['sync_folder_id'] = folder_id
                
                # 保存配置
                config_data = ConfigCache.load()
                game_list = config_data.get("game_list", [])
                for game in game_list:
                    if game.get('name') == self.selected_game.get('name'):
                        game['is_syncing'] = True
                        game['sync_folder_id'] = folder_id
                        break
                ConfigCache.save(config_data)
                
                # 更新按钮样式
                self.sync_btn.setText("⏸️ 停止分享")
                self.sync_status_label.setText("🔄 已加入分享")
                self.sync_status_label.setStyleSheet("color: #107c10; font-size: 12px;")
                
                InfoBar.success(
                    title='成功',
                    content=f"「{game_name}」已加入分享",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                
                # 刷新游戏列表显示状态
                self.load_game_list()
                # 重新选中当前游戏
                for i in range(self.game_list.count()):
                    item = self.game_list.item(i)
                    if item.data(Qt.UserRole) and item.data(Qt.UserRole).get('name') == self.selected_game.get('name'):
                        self.game_list.setCurrentItem(item)
                        break
            
        except Exception as e:
            logger.error(f"启用同步失败: {e}")
            InfoBar.error(
                title='错误',
                content=f"启用同步失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def stop_sync(self):
        """停止同步（暂停文件夹，不删除配置）"""
        from utils.config_cache import ConfigCache
        
        try:
            folder_id = self.selected_game.get('sync_folder_id')
            if not folder_id:
                return
            
            # 暂停同步文件夹（而不是删除）
            if hasattr(self.parent_window, 'syncthing_manager') and self.parent_window.syncthing_manager:
                self.parent_window.syncthing_manager.pause_folder(folder_id)
            
            # 更新状态
            self.selected_game['is_syncing'] = False
            
            # 保存配置
            config_data = ConfigCache.load()
            game_list = config_data.get("game_list", [])
            for game in game_list:
                if game.get('name') == self.selected_game.get('name'):
                    game['is_syncing'] = False
                    break
            ConfigCache.save(config_data)
            
            # 更新按钮样式
            self.sync_btn.setText("✅ 加入分享")
            self.sync_status_label.setText("⚪ 未加入分享")
            self.sync_status_label.setStyleSheet("color: #999999; font-size: 12px;")
            
            InfoBar.success(
                title='成功',
                content=f"「{self.selected_game.get('name')}」已停止分享",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            # 通知存档同步页面刷新
            if hasattr(self.parent_window, 'sync_interface'):
                self.parent_window.sync_interface.refresh_sync()
            
            # 刷新游戏列表显示状态
            self.load_game_list()
            # 重新选中当前游戏
            for i in range(self.game_list.count()):
                item = self.game_list.item(i)
                if item.data(Qt.UserRole) and item.data(Qt.UserRole).get('name') == self.selected_game.get('name'):
                    self.game_list.setCurrentItem(item)
                    break
            
        except Exception as e:
            logger.error(f"停止同步失败: {e}")
    
    def _check_actual_sync_status(self, game_data):
        """检查游戏的实际同步状态（从Syncthing获取）"""
        try:
            # 如果未连接网络或Syncthing未启动，返回False
            if not hasattr(self.parent_window, 'syncthing_manager') or not self.parent_window.syncthing_manager:
                return False
            
            # 获取文件夹ID
            folder_id = game_data.get('sync_folder_id')
            if not folder_id:
                return False
            
            # 从Syncthing配置中获取文件夹状态
            config = self.parent_window.syncthing_manager.get_config()
            if not config:
                return False
            
            # 检查文件夹是否存在且未暂停
            for folder in config.get('folders', []):
                if folder.get('id') == folder_id:
                    # 如果文件夹未暂停，则返回True
                    return not folder.get('paused', True)
            
            return False
        except Exception as e:
            logger.error(f"检查同步状态失败: {e}")
            return False
    
    def delete_game(self, checked=False):
        """停止分享"""
        if not self.selected_game:
            InfoBar.warning(
                title='提示',
                content="请先选择游戏",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        from qfluentwidgets import MessageBox
        from utils.config_cache import ConfigCache
        
        game_name = self.selected_game.get('name')
        
        # 确认停止分享
        w = MessageBox(
            "确认停止分享",
            f"确定要停止分享游戏 \"{game_name}\" 吗？\n\n注：停止分享后，其他设备将无法同步此存档。",
            self
        )
        if not w.exec_():
            return
        
        try:
            # 如果正在同步，先停止同步
            if self.selected_game.get('is_syncing'):
                folder_id = self.selected_game.get('sync_folder_id')
                if folder_id and hasattr(self.parent_window, 'syncthing_manager') and self.parent_window.syncthing_manager:
                    self.parent_window.syncthing_manager.remove_folder(folder_id)
            
            # 从配置中删除
            config_data = ConfigCache.load()
            game_list = config_data.get("game_list", [])
            config_data["game_list"] = [
                g for g in game_list if g.get('name') != game_name
            ]
            ConfigCache.save(config_data)
            
            # 重新加载游戏列表
            self.load_game_list()
            
            # 清空当前选中的游戏
            self.selected_game = None
            
            # 显示空状态
            self.empty_state.setVisible(True)
            
            # 隐藏右侧区域
            self.game_info_card.setVisible(False)
            self.saves_area.setVisible(False)
            self.action_buttons.setVisible(False)
            
            logger.info(f"已停止分享游戏: {game_name}")
            
        except Exception as e:
            logger.error(f"停止分享失败: {e}")
            InfoBar.error(
                title='错误',
                content=f"停止分享失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    

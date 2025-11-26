"""
游戏管理页面
"""
from PyQt5.QtCore import Qt, pyqtSlot
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
        
        # 游戏状态
        self.game_host = None  # 当前游戏主机
        self.game_port = None  # 当前游戏端口
        self.game_world = None  # 当前游戏世界
        self.is_host = False  # 是否是主机
        self.game_process = None  # 游戏进程对象
        self.process_monitor_thread = None  # 进程监控线程
        self.broadcast_timer = None  # 主机广播定时器
        self.starting_broadcast_timer = None  # “启动中”状态广播定时器
        
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
        
        add_game_btn = PrimaryPushButton(FluentIcon.ADD, "添加游戏")
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
        
        # 玩家信息区域
        self.player_info_card = self.create_player_info_area()
        right_layout.addWidget(self.player_info_card)
        
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
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 游戏图标
        icon_container = QWidget()
        icon_container.setFixedSize(72, 72)
        icon_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f0f9ff,
                    stop:1 #e0f2fe);
                border: 2px solid #0078d4;
                border-radius: 12px;
            }
        """)
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        self.game_icon_label = QLabel()
        self.game_icon_label.setAlignment(Qt.AlignCenter)
        self.game_icon_label.setStyleSheet("background: transparent; border: none;")
        icon_layout.addWidget(self.game_icon_label)
        
        layout.addWidget(icon_container)
        
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
    
    def create_player_info_area(self):
        """创建玩家信息区域"""
        card = CardWidget()
        card.setVisible(False)  # 默认隐藏
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 玩家头像
        avatar_container = QWidget()
        avatar_container.setFixedSize(72, 72)
        avatar_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f0f9ff,
                    stop:1 #e0f2fe);
                border: 2px solid #0078d4;
                border-radius: 12px;
            }
        """)
        
        avatar_layout = QVBoxLayout(avatar_container)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setAlignment(Qt.AlignCenter)
        
        self.player_avatar_label = QLabel()
        self.player_avatar_label.setAlignment(Qt.AlignCenter)
        self.player_avatar_label.setStyleSheet("background: transparent; border: none;")
        avatar_layout.addWidget(self.player_avatar_label)
        
        layout.addWidget(avatar_container)
        
        # 玩家信息
        player_layout = QVBoxLayout()
        player_layout.setSpacing(6)
        
        player_title_layout = QHBoxLayout()
        player_title_layout.setSpacing(6)
        
        player_icon = IconWidget(FluentIcon.PEOPLE)
        player_icon.setFixedSize(16, 16)
        player_title_layout.addWidget(player_icon)
        
        player_title = BodyLabel("当前玩家")
        player_title.setStyleSheet("color: #666666; font-size: 12px;")
        player_title_layout.addWidget(player_title)
        player_title_layout.addStretch()
        
        player_layout.addLayout(player_title_layout)
        
        self.player_name_label = SubtitleLabel("")
        self.player_name_label.setStyleSheet("font-weight: 600; font-size: 16px;")
        player_layout.addWidget(self.player_name_label)
        
        player_layout.addStretch()
        layout.addLayout(player_layout, 1)
        
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
        
        saves_icon = IconWidget(FluentIcon.FOLDER)
        saves_icon.setFixedSize(20, 20)
        header.addWidget(saves_icon)
        
        saves_title = SubtitleLabel("存档列表")
        saves_title.setStyleSheet("font-weight: 600; margin-left: 6px;")
        header.addWidget(saves_title)
        header.addStretch()
        
        layout.addLayout(header)
        
        # 存档表格
        self.saves_table = TableWidget()
        self.saves_table.setColumnCount(2)
        self.saves_table.setHorizontalHeaderLabels(["存档名称", "更新时间"])
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
        
        # 选择用户
        self.select_user_btn = PushButton(FluentIcon.PEOPLE, "选择用户")
        self.select_user_btn.setFixedHeight(40)
        self.select_user_btn.clicked.connect(self.select_account)
        layout.addWidget(self.select_user_btn)
        
        # 启动游戏按钮（默认显示）
        self.launch_game_btn = PrimaryPushButton(FluentIcon.PLAY, "启动游戏")
        self.launch_game_btn.setFixedHeight(40)
        self.launch_game_btn.clicked.connect(self.launch_game)
        layout.addWidget(self.launch_game_btn)
        
        # 加入游戏按钮（默认隐藏）
        self.join_game_btn = PrimaryPushButton(FluentIcon.LINK, "加入游戏")
        self.join_game_btn.setFixedHeight(40)
        self.join_game_btn.clicked.connect(self.join_game)
        self.join_game_btn.setVisible(False)  # 默认隐藏
        layout.addWidget(self.join_game_btn)
        
        # 关闭游戏按钮（默认隐藏）
        self.close_game_btn = PrimaryPushButton(FluentIcon.CANCEL, "关闭游戏")
        self.close_game_btn.setFixedHeight(40)
        self.close_game_btn.clicked.connect(self.close_game)
        self.close_game_btn.setVisible(False)  # 默认隐藏
        self.close_game_btn.setStyleSheet("""
            PrimaryPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #d13438,
                    stop:1 #a61e22);
                color: white;
            }
            PrimaryPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #a61e22,
                    stop:1 #8b1a1d);
            }
        """)
        layout.addWidget(self.close_game_btn)
        
        # 启动同步
        self.sync_btn = PushButton(FluentIcon.SYNC, "启动同步")
        self.sync_btn.setFixedHeight(40)
        self.sync_btn.clicked.connect(self.toggle_sync)
        layout.addWidget(self.sync_btn)
        
        layout.addStretch()
        
        # 删除游戏
        self.delete_game_btn = PushButton(FluentIcon.DELETE, "删除游戏")
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
            # 检查实际的同步状态（从Syncthing获取）
            is_syncing = self._check_actual_sync_status(game)
            sync_status = "🔄 启用同步" if is_syncing else "⚪ 停止同步"
            item.setText(f"{game.get('name', '未命名')}\n{sync_status}")
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
                
        sync_status = "🔄 启用同步" if is_syncing else "⚪ 停止同步"
        self.sync_status_label.setText(sync_status)
        self.sync_status_label.setStyleSheet(f"color: {'#107c10' if is_syncing else '#999999'}; font-size: 13px; font-weight: 500;")
        
        # 更新同步状态图标
        if is_syncing:
            self.sync_status_icon.setIcon(FluentIcon.ACCEPT)
        else:
            self.sync_status_icon.setIcon(FluentIcon.CANCEL)
        
        # 更新同步按钮文本
        if is_syncing:
            self.sync_btn.setText("⏸️ 停止同步")
        else:
            self.sync_btn.setText("✅ 启动同步")
        
        # 加载游戏图标
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources', 'icons')
        icon_path = os.path.join(icon_dir, 'mc.png' if game_data.get('type') == 'minecraft' else 'game3.png')
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.game_icon_label.setPixmap(pixmap)
        else:
            # 如果图标不存在，显示默认图标
            self.game_icon_label.setText("🎮")
            self.game_icon_label.setStyleSheet("background: transparent; border: none; font-size: 36px;")
        
        # 根据游戏类型加载玩家信息和存档列表
        if game_data.get('type') == 'minecraft':
            # Minecraft 显示玩家信息和存档
            self.load_player_info(game_data)
            self.load_saves_list(game_data)
            
            self.player_info_card.setVisible(True)
            self.saves_area.setVisible(True)
            self.action_buttons.setVisible(True)
        else:
            # 其他游戏隐藏玩家信息
            self.player_info_card.setVisible(False)
            self.saves_area.setVisible(False)
            self.action_buttons.setVisible(True)
            
            InfoBar.info(
                title='提示',
                content="请先配置游戏启动器和存档目录",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def add_game(self):
        """添加游戏"""
        from ui.components.dialogs.add_game_dialog import AddGameDialog
        from ui.components.dialogs.launcher_selector import LauncherSelectorDialog
        from PyQt5.QtWidgets import QDialog, QFileDialog
        from utils.config_cache import ConfigCache
        
        # 显示游戏类型选择对话框
        dialog = AddGameDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.game_type == 'minecraft':
                # 我的世界 - 显示启动器选择对话框
                launcher_dialog = LauncherSelectorDialog(self.parent_window)
                if launcher_dialog.exec_() == QDialog.Accepted:
                    # 重新加载游戏列表
                    self.load_game_list()
            elif dialog.game_type == 'other':
                # 其他游戏 - 直接选择游戏目录
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
    
    def load_player_info(self, game_data):
        """加载玩家信息"""
        player_name = game_data.get('selected_account', 'Steve')
        self.player_name_label.setText(player_name)
        
        # 加载玩家头像
        self.load_player_avatar(player_name, game_data)
    
    def load_player_avatar(self, player_name, game_data):
        """加载玩家头像"""
        try:
            from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
            from PyQt5.QtCore import QUrl
            
            # 先尝试从启动器读取 UUID
            launcher_path = game_data.get('launcher_path')
            uuid_formatted = None
            
            if launcher_path:
                try:
                    from managers.launcher_account_reader import LauncherAccountReader
                    reader = LauncherAccountReader(launcher_path)
                    accounts = reader.get_all_accounts()
                    
                    # 查找匹配的账号
                    for account in accounts:
                        if account.get('player_name') == player_name:
                            uuid_formatted = account.get('uuid')  # 带横线的 UUID
                            break
                except Exception as e:
                    logger.warning(f"无法从启动器读取 UUID: {e}")
            
            # 如果没有 UUID，显示默认头像
            if not uuid_formatted:
                logger.info(f"未找到 {player_name} 的 UUID，使用默认头像")
                self.player_avatar_label.setText("👤")
                self.player_avatar_label.setStyleSheet("background: transparent; border: none; font-size: 40px;")
                return
            
            # 检查缓存
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'cache', 'avatars')
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"{uuid_formatted}.png")
            
            # 如果缓存存在，直接加载
            if os.path.exists(cache_file):
                pixmap = QPixmap(cache_file)
                if not pixmap.isNull():
                    logger.info(f"从缓存加载头像: {player_name}")
                    scaled_pixmap = pixmap.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.player_avatar_label.setPixmap(scaled_pixmap)
                    return
            
            # 下载头像
            if not hasattr(self, 'avatar_manager'):
                self.avatar_manager = QNetworkAccessManager()
            
            # 使用 Minotar API
            url = f"https://minotar.net/avatar/{uuid_formatted}/64.png"
            logger.info(f"下载头像: {url}")
            
            request = QNetworkRequest(QUrl(url))
            reply = self.avatar_manager.get(request)
            
            def on_finished():
                try:
                    if reply.error() == reply.NoError:
                        image_data = reply.readAll()
                        pixmap = QPixmap()
                        if pixmap.loadFromData(image_data):
                            # 保存到缓存
                            pixmap.save(cache_file, "PNG")
                            logger.info(f"头像下载成功: {player_name}")
                            
                            # 显示头像
                            scaled_pixmap = pixmap.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            self.player_avatar_label.setPixmap(scaled_pixmap)
                        else:
                            logger.error("头像数据解析失败")
                            self.player_avatar_label.setText("👤")
                            self.player_avatar_label.setStyleSheet("background: transparent; border: none; font-size: 40px;")
                    else:
                        logger.error(f"头像请求失败: {reply.errorString()}")
                        self.player_avatar_label.setText("👤")
                        self.player_avatar_label.setStyleSheet("background: transparent; border: none; font-size: 40px;")
                except Exception as e:
                    logger.error(f"处理头像响应失败: {e}")
                finally:
                    reply.deleteLater()
            
            reply.finished.connect(on_finished)
            
        except Exception as e:
            logger.error(f"加载头像异常: {e}")
            self.player_avatar_label.setText("👤")
            self.player_avatar_label.setStyleSheet("background: transparent; border: none; font-size: 40px;")
    
    def load_saves_list(self, game_data):
        """加载存档列表"""
        import datetime
        
        self.saves_table.setRowCount(0)
        
        save_path = game_data.get('save_path')
        if not save_path or not os.path.exists(save_path):
            return
        
        # 扫描存档目录
        try:
            saves = []
            for item in os.listdir(save_path):
                item_path = os.path.join(save_path, item)
                if os.path.isdir(item_path):
                    # 获取最后修改时间
                    mtime = os.path.getmtime(item_path)
                    update_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                    saves.append((item, update_time))
            
            # 按修改时间排序
            saves.sort(key=lambda x: x[1], reverse=True)
            
            # 填充表格
            self.saves_table.setRowCount(len(saves))
            for i, (save_name, update_time) in enumerate(saves):
                self.saves_table.setItem(i, 0, QTableWidgetItem(save_name))
                time_item = QTableWidgetItem(update_time)
                time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.saves_table.setItem(i, 1, time_item)
        except Exception as e:
            logger.error(f"加载存档列表失败: {e}")
    
    def select_account(self):
        """选择用户"""
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
        
        # 检查是否有启动器路径
        launcher_path = self.selected_game.get('launcher_path')
        if not launcher_path:
            InfoBar.warning(
                title='提示',
                content="该游戏没有配置启动器路径",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        from ui.components.dialogs.account_selector import AccountSelectorDialog
        from PyQt5.QtWidgets import QDialog
        from utils.config_cache import ConfigCache
        
        dialog = AccountSelectorDialog(launcher_path, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_account = dialog.selected_account
            if selected_account:
                player_name = selected_account.get('player_name', 'Unknown')
                
                # 保存到游戏配置
                config_data = ConfigCache.load()
                game_list = config_data.get("game_list", [])
                for game in game_list:
                    if game.get('name') == self.selected_game.get('name'):
                        game['selected_account'] = player_name
                        break
                ConfigCache.save(config_data)
                
                # 更新当前选中的游戏对象（关键！）
                self.selected_game['selected_account'] = player_name
                
                # 更新显示
                self.player_name_label.setText(player_name)
                
                # 加载玩家头像
                self.load_player_avatar(player_name, self.selected_game)
                
                InfoBar.success(
                    title='成功',
                    content=f"已选择玩家：{player_name}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def launch_game(self):
        """启动游戏"""
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
        
        # 检查是否选择了玩家
        if not self.selected_game.get('selected_account'):
            InfoBar.warning(
                title='提示',
                content="请先选择玩家！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 检查是否选择了存档
        selected_items = self.saves_table.selectedItems()
        if not selected_items:
            InfoBar.warning(
                title='提示',
                content="请先选择要启动的存档！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        try:
            from managers.game_launcher import GameLauncher
            from PyQt5.QtCore import QMetaObject, Q_ARG
            import threading
            
            game_name = self.selected_game.get('name')
            version = self.selected_game.get('version')
            save_path = self.selected_game.get('save_path', '')
            launcher_path = self.selected_game.get('launcher_path')
            player_name = self.selected_game.get('selected_account')
            
            # 获取选中的存档名称
            row = selected_items[0].row()
            world_name = self.saves_table.item(row, 0).text()
            logger.info(f"选中的存档: {world_name}")
            
            # 从存档路径推断 Minecraft 目录
            minecraft_dir = self._get_minecraft_dir_from_save_path(save_path)
            
            if not minecraft_dir:
                InfoBar.error(
                    title='错误',
                    content="未找到 Minecraft 目录！",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            logger.info(f"Minecraft 目录: {minecraft_dir}")
            logger.info(f"游戏版本: {version}")
            logger.info(f"玩家: {player_name}")
            if world_name:
                logger.info(f"自动进入世界: {world_name}")
            
            # 广播游戏启动中（禁用其他人的启动按钮）
            logger.info("检查TCP广播对象...")
            if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                logger.info("tcp_broadcast 存在，开始广播 game/starting")
                self.parent_window.tcp_broadcast.publish(
                    "game/starting",
                    {
                        "game_name": game_name,
                        "world_name": world_name,
                        "player_name": player_name
                    }
                )
                
                # 启动“启动中”状态广播定时器，让新进来的玩家也能感知到
                self._start_starting_broadcast(game_name, world_name, player_name)
            else:
                logger.warning("tcp_broadcast 不存在！")
            
           # 设置为主机状态（防止自己的按钮被禁用）
            self.is_host = True
            
            # 禁用启动按钮，显示"正在启动..."
            self.launch_game_btn.setEnabled(False)
            self.launch_game_btn.setText("正在启动...")
            
            # 在子线程中启动游戏
            def launch_thread():
                try:
                    # 创建游戏启动器
                    game_launcher = GameLauncher(minecraft_dir, version)
                    
                    # 启动游戏
                    success = game_launcher.launch_minecraft(
                        launcher_path=launcher_path,
                        world_name=world_name  # 传递选中的存档名称
                    )
                    
                    if not success:
                        logger.error("游戏启动失败")
                        
                        # 停止启动中广播
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self._stop_starting_broadcast())
                        
                        # 广播启动失败
                        if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                            self.parent_window.tcp_broadcast.publish(
                                "game/failed",
                                {
                                    "game_name": game_name,
                                    "world_name": world_name,
                                    "player_name": player_name,
                                    "error": "游戏启动失败"
                                }
                            )
                        
                        QMetaObject.invokeMethod(
                            self,
                            "_show_error_message",
                            Qt.QueuedConnection,
                            Q_ARG(str, "游戏启动失败")
                        )
                        return
                    
                    logger.info("游戏启动成功，等待游戏窗口...")
                    
                    # 等待游戏窗口出现
                    if game_launcher.wait_for_game_window(timeout=90):
                        logger.info("检测到游戏窗口，等待进入世界...")
                        
                        # 等待进入世界
                        if game_launcher.wait_for_world_loaded(timeout=120):
                            logger.info("已进入世界，开始开启局域网...")
                            
                            # 自动开启局域网
                            if game_launcher.auto_open_lan():
                                lan_port = game_launcher.lan_port
                                logger.info(f"✅ 局域网开启成功，端口: {lan_port}")
                                
                                # 设置主机状态
                                self.is_host = True
                                self.game_port = lan_port
                                self.game_world = world_name
                                self.game_process = game_launcher.game_process  # 保存游戏进程
                                
                                # 启动进程监控
                                self._start_process_monitor(game_name, world_name, player_name)
                                
                                # 广播游戏启动成功（其他人按钮变为"加入游戏"）
                                if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                                    # 停止"启动中"广播
                                    from PyQt5.QtCore import QTimer
                                    QTimer.singleShot(0, lambda: self._stop_starting_broadcast())
                                    
                                    # 获取本机EasyTier虚拟IP
                                    virtual_ip = ""
                                    if hasattr(self.parent_window, 'controller') and hasattr(self.parent_window.controller, 'easytier'):
                                        virtual_ip = self.parent_window.controller.easytier.virtual_ip or ''
                                    
                                    if not virtual_ip:
                                        logger.warning("未获取到EasyTier虚拟IP，其他玩家可能无法加入")
                                    
                                    self.parent_window.tcp_broadcast.publish(
                                        "game/started",
                                        {
                                            "game_name": game_name,
                                            "world_name": world_name,
                                            "player_name": player_name,
                                            "port": lan_port,
                                            "host_ip": virtual_ip
                                        }
                                    )
                                else:
                                    logger.warning("tcp_broadcast 不存在！")
                                
                                # 启动定时广播（每10秒广播一次，让新加入的玩家知道服务器在运行）
                                self._start_host_broadcast(game_name, world_name, player_name, lan_port)
                                
                                # 恢复按钮状态（先恢复再显示消息）
                                from PyQt5.QtCore import QTimer
                                QTimer.singleShot(0, lambda: self.launch_game_btn.setVisible(False))
                                QTimer.singleShot(0, lambda: self.close_game_btn.setVisible(True))
                                QTimer.singleShot(0, lambda: self.close_game_btn.setEnabled(True))
                                
                                QMetaObject.invokeMethod(
                                    self,
                                    "_show_success_message",
                                    Qt.QueuedConnection,
                                    Q_ARG(str, f"游戏已启动并开启局域网，端口: {lan_port}")
                                )
                                return  # 成功后直接返回，不再执行 finally
                            else:
                                logger.warning("自动开启局域网失败，请手动开启")
                                
                                # 停止启动中广播
                                from PyQt5.QtCore import QTimer
                                QTimer.singleShot(0, lambda: self._stop_starting_broadcast())
                                
                                # 广播启动失败（需要手动开启局域网）
                                if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                                    self.parent_window.tcp_broadcast.publish(
                                        "game/failed",
                                        {
                                            "game_name": game_name,
                                            "world_name": world_name,
                                            "player_name": player_name,
                                            "error": "需要手动开启局域网"
                                        }
                                    )
                                
                                # 恢复按钮状态
                                QTimer.singleShot(0, lambda: self.launch_game_btn.setEnabled(True))
                                QTimer.singleShot(0, lambda: self.launch_game_btn.setText("启动游戏"))
                                
                                QMetaObject.invokeMethod(
                                    self,
                                    "_show_success_message",
                                    Qt.QueuedConnection,
                                    Q_ARG(str, f"游戏已启动，请手动开启局域网（按ESC -> 对局域网开放）")
                                )
                                return
                        else:
                            logger.warning("等待进入世界超时")
                            
                            # 停止启动中广播
                            from PyQt5.QtCore import QTimer
                            QTimer.singleShot(0, lambda: self._stop_starting_broadcast())
                            
                            # 广播启动失败
                            if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                                self.parent_window.tcp_broadcast.publish(
                                    "game/failed",
                                    {
                                        "game_name": game_name,
                                        "world_name": world_name,
                                        "player_name": player_name,
                                        "error": "等待进入世界超时"
                                    }
                                )
                            
                            # 恢复按钮状态
                            QTimer.singleShot(0, lambda: self.launch_game_btn.setEnabled(True))
                            QTimer.singleShot(0, lambda: self.launch_game_btn.setText("启动游戏"))
                            
                            QMetaObject.invokeMethod(
                                self,
                                "_show_success_message",
                                Qt.QueuedConnection,
                                Q_ARG(str, f"游戏已启动，请手动开启局域网")
                            )
                            return
                    else:
                        logger.warning("未检测到游戏窗口")
                        
                        # 停止启动中广播
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self._stop_starting_broadcast())
                        
                        # 广播启动失败
                        if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                            self.parent_window.tcp_broadcast.publish(
                                "game/failed",
                                {
                                    "game_name": game_name,
                                    "world_name": world_name,
                                    "player_name": player_name,
                                    "error": "未检测到游戏窗口"
                                }
                            )
                        
                        # 恢复按钮状态
                        QTimer.singleShot(0, lambda: self.launch_game_btn.setEnabled(True))
                        QTimer.singleShot(0, lambda: self.launch_game_btn.setText("启动游戏"))
                        
                        QMetaObject.invokeMethod(
                            self,
                            "_show_success_message",
                            Qt.QueuedConnection,
                            Q_ARG(str, f"游戏已启动")
                        )
                        return
                    
                except Exception as e:
                    logger.error(f"启动游戏异常: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    
                    # 重置is_host状态
                    self.is_host = False
                    
                    # 停止广播定时器
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self._stop_starting_broadcast())
                    QTimer.singleShot(0, lambda: self._stop_host_broadcast())
                    
                    # 广播游戏启动失败（恢复所有人的启动按钮）
                    if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                        self.parent_window.tcp_broadcast.publish(
                            "game/failed",
                            {
                                "game_name": game_name,
                                "world_name": world_name,
                                "player_name": player_name,
                                "error": str(e)
                            }
                        )
                    
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_message",
                        Qt.QueuedConnection,
                        Q_ARG(str, f"启动失败: {str(e)}")
                    )
                finally:
                    # 恢复按钮状态（使用 lambda 避免 setText 问题）
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self.launch_game_btn.setEnabled(True))
                    QTimer.singleShot(0, lambda: self.launch_game_btn.setText("启动游戏"))
            
            threading.Thread(target=launch_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"启动游戏失败: {e}")
            InfoBar.error(
                title='错误',
                content=f"启动失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            self.launch_game_btn.setEnabled(True)
            self.launch_game_btn.setText("启动游戏")
    
    def _get_minecraft_dir_from_save_path(self, save_path):
        """从存档路径推断 Minecraft 目录"""
        if not save_path:
            return None
        
        # save_path 格式: .minecraft/versions/{version}/saves
        # 需要回溯到 .minecraft
        parts = save_path.replace('\\', '/').split('/')
        
        # 查找 .minecraft 目录
        if '.minecraft' in parts:
            idx = parts.index('.minecraft')
            minecraft_dir = '/'.join(parts[:idx+1])
            return minecraft_dir
        
        return None
    
    @pyqtSlot(str)
    def _show_success_message(self, message):
        """线程安全的成功消息显示"""
        InfoBar.success(
            title='成功',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    @pyqtSlot(str)
    def _show_error_message(self, message):
        """线程安全的错误消息显示"""
        InfoBar.error(
            title='错误',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    @pyqtSlot(str)
    def _show_success_message(self, message):
        """线程安全的成功消息显示"""
        InfoBar.success(
            title='成功',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    @pyqtSlot(str, str)
    def _handle_game_message_safe(self, message_type, data_json):
        """
        线程安全的游戏消息处理（在主线程中调用）
        
        Args:
            message_type: 消息类型
            data_json: JSON字符串格式的消息数据
        """
        try:
            import json
            from PyQt5.QtCore import QTimer
            
            # 解析JSON数据
            data = json.loads(data_json)
            
            if message_type == "game/starting":
                # 收到游戏启动中消息，禁用启动按钮（只有在非主机状态下才禁用）
                if not self.is_host:
                    logger.info(f"收到游戏启动中消息: {data.get('player_name')} 正在启动 {data.get('world_name')}")
                    # 隐藏启动按钮，显示禁用的加入按钮
                    self.launch_game_btn.setVisible(False)
                    self.join_game_btn.setVisible(True)
                    self.join_game_btn.setEnabled(False)
                    self.join_game_btn.setText("他人启动中...")
            
            elif message_type == "game/started":
                # 收到游戏启动成功消息，按钮变为"加入游戏"（只有在非主机状态下才切换）
                if not self.is_host:
                    logger.info(f"收到游戏启动成功消息: {data.get('player_name')} 已开启服务器")
                    self.game_host = data.get('host_ip', '')
                    self.game_port = data.get('port', 0)
                    self.game_world = data.get('world_name', '')
                    
                    # 隐藏启动按钮，显示加入按钮
                    self.launch_game_btn.setVisible(False)
                    self.join_game_btn.setVisible(True)
                    self.join_game_btn.setEnabled(True)
                    self.join_game_btn.setText("加入游戏")
                    
                    logger.info(f"主机: {self.game_host}:{self.game_port}, 世界: {self.game_world}")
            
            elif message_type == "game/failed" or message_type == "game/host_offline":
                # 游戏启动失败或主机掉线，恢复启动按钮
                logger.info(f"收到游戏结束消息: {message_type}")
                self.game_host = None
                self.game_port = None
                self.game_world = None
                
                # 显示启动按钮，隐藏加入按钮
                self.launch_game_btn.setVisible(True)
                self.launch_game_btn.setEnabled(True)
                self.join_game_btn.setVisible(False)
        
        except Exception as e:
            logger.error(f"处理游戏消息失败: {e}")
    
    def toggle_sync(self):
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
                
                # 等待 Syncthing 处理配置
                import time
                time.sleep(2)
                
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
                            break
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
                
                # 等待Syncthing处理配置
                import time
                time.sleep(2)
                
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
                    return
            
            # 更新状态
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
            self.sync_btn.setText("⏸️ 停止同步")
            self.sync_status_label.setText("🔄 启用同步")
            self.sync_status_label.setStyleSheet("color: #107c10; font-size: 12px;")
            
            InfoBar.success(
                title='成功',
                content=f"已启用「{game_name}」的存档同步",
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
            self.sync_btn.setText("✅ 启动同步")
            self.sync_status_label.setText("⚪ 停止同步")
            self.sync_status_label.setStyleSheet("color: #999999; font-size: 12px;")
            
            InfoBar.success(
                title='成功',
                content=f"已停止「{self.selected_game.get('name')}」的存档同步",
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
    
    def delete_game(self):
        """删除游戏"""
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
        
        # 确认删除
        w = MessageBox(
            "确认删除",
            f"确定要删除游戏 \"{game_name}\" 吗？\n\n注：只会删除配置，不会删除游戏文件。",
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
            self.player_info_card.setVisible(False)
            self.saves_area.setVisible(False)
            self.action_buttons.setVisible(False)
            
            logger.info(f"已删除游戏: {game_name}")
            
        except Exception as e:
            logger.error(f"删除游戏失败: {e}")
            InfoBar.error(
                title='错误',
                content=f"删除游戏失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def join_game(self):
        """加入游戏（自动连接到主机）"""
        if not self.game_host or not self.game_port:
            InfoBar.warning(
                title='提示',
                content="未找到游戏主机信息！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
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
        
        # 检查是否选择了玩家
        if not self.selected_game.get('selected_account'):
            InfoBar.warning(
                title='提示',
                content="请先选择玩家！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        try:
            from managers.game_launcher import GameLauncher
            from PyQt5.QtCore import QMetaObject, Q_ARG
            import threading
            
            game_name = self.selected_game.get('name')
            version = self.selected_game.get('version')
            save_path = self.selected_game.get('save_path', '')
            launcher_path = self.selected_game.get('launcher_path')
            # 获取玩家名称（selected_account直接保存的是字符串）
            player_name = self.selected_game.get('selected_account', '')
            
            # 记录调试信息
            logger.info(f"准备加入游戏: {game_name}")
            logger.info(f"版本: {version}")
            logger.info(f"玩家: {player_name}")
            logger.info(f"启动器: {launcher_path}")
            logger.info(f"服务器: {self.game_host}:{self.game_port}")
            
            # 从存档路径推断 Minecraft 目录
            minecraft_dir = self._get_minecraft_dir_from_save_path(save_path)
            
            if not minecraft_dir:
                InfoBar.error(
                    title='错误',
                    content="未找到 Minecraft 目录！",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            # 禁用加入按钮
            self.join_game_btn.setEnabled(False)
            self.join_game_btn.setText("正在加入...")
            
            # 在子线程中启动游戏
            def join_thread():
                try:
                    logger.info(f"=== 开始加入游戏线程 ===")
                    logger.info(f"Minecraft目录: {minecraft_dir}")
                    logger.info(f"游戏版本: {version}")
                    logger.info(f"启动器路径: {launcher_path}")
                    logger.info(f"服务器: {self.game_host}:{self.game_port}")
                    
                    # 创建游戏启动器
                    game_launcher = GameLauncher(minecraft_dir, version)
                    
                    # 使用专用的 join_server 方法
                    logger.info("调用 join_server...")
                    success = game_launcher.join_server(
                        server_ip=self.game_host,
                        server_port=self.game_port,
                        player_name=player_name,
                        launcher_path=launcher_path
                    )
                    
                    logger.info(f"launch_minecraft 返回: {success}")
                    
                    if success:
                        logger.info("加入游戏成功")
                        
                        # 保存游戏进程（用于关闭游戏）
                        self.game_process = game_launcher.game_process
                        
                        # 更新按钮状态：隐藏加入按钮，显示关闭按钮
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self.join_game_btn.setVisible(False))
                        QTimer.singleShot(0, lambda: self.close_game_btn.setVisible(True))
                        QTimer.singleShot(0, lambda: self.close_game_btn.setEnabled(True))
                        
                        QMetaObject.invokeMethod(
                            self,
                            "_show_success_message",
                            Qt.QueuedConnection,
                            Q_ARG(str, f"已启动游戏，正在连接到 {self.game_host}:{self.game_port}")
                        )
                    else:
                        logger.error("加入游戏失败")
                        
                        # 恢复按钮状态
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self.join_game_btn.setEnabled(True))
                        QTimer.singleShot(0, lambda: self.join_game_btn.setText("加入游戏"))
                        QTimer.singleShot(0, lambda: self.join_game_btn.setVisible(True))
                        
                        QMetaObject.invokeMethod(
                            self,
                            "_show_error_message",
                            Qt.QueuedConnection,
                            Q_ARG(str, "加入游戏失败")
                        )
                        
                except Exception as e:
                    logger.error(f"加入游戏异常: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_message",
                        Qt.QueuedConnection,
                        Q_ARG(str, f"加入失败: {str(e)}")
                    )
                finally:
                    pass  # 按钮状态已在 success/error 分支中处理
            
            threading.Thread(target=join_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"加入游戏失败: {e}")
            InfoBar.error(
                title='错误',
                content=f"加入失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            self.join_game_btn.setEnabled(True)
    
    def _start_process_monitor(self, game_name, world_name, player_name):
        """
        启动游戏进程监控，当进程结束时广播主机掉线消息
        
        Args:
            game_name: 游戏名称
            world_name: 世界名称
            player_name: 玩家名称
        """
        import threading
        
        def monitor_thread():
            try:
                if not self.game_process:
                    logger.warning("游戏进程不存在，无法监控")
                    return
                
                logger.info(f"开始监控游戏进程 PID={self.game_process.pid}")
                
                # 等待进程结束
                self.game_process.wait()
                
                logger.info(f"游戏进程已结束，退出码: {self.game_process.returncode}")
                
                # 停止广播定时器
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._stop_host_broadcast())
                
                # 广播主机掉线消息
                if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                    self.parent_window.tcp_broadcast.publish(
                        "game/host_offline",
                        {
                            "game_name": game_name,
                            "world_name": world_name,
                            "player_name": player_name
                        }
                    )
                    logger.info("已广播主机掉线消息")
                
                # 重置主机状态
                self.is_host = False
                self.game_process = None
                self.game_port = None
                self.game_world = None
                
                # 恢复按钮状态（显示启动按钮，隐藏加入和关闭按钮）
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: self.launch_game_btn.setVisible(True))
                QTimer.singleShot(0, lambda: self.launch_game_btn.setEnabled(True))
                QTimer.singleShot(0, lambda: self.join_game_btn.setVisible(False))
                QTimer.singleShot(0, lambda: self.close_game_btn.setVisible(False))
                
            except Exception as e:
                logger.error(f"监控游戏进程失败: {e}")
        
        # 启动监控线程
        self.process_monitor_thread = threading.Thread(target=monitor_thread, daemon=True)
        self.process_monitor_thread.start()
        logger.info("已启动游戏进程监控线程")
    
    def _start_host_broadcast(self, game_name, world_name, player_name, port):
        """
        启动主机广播定时器，每10秒广播一次服务器信息
        
        Args:
            game_name: 游戏名称
            world_name: 世界名称
            player_name: 玩家名称
            port: 游戏端口
        """
        from PyQt5.QtCore import QTimer
        
        # 先停止旧的定时器
        self._stop_host_broadcast()
        
        def broadcast_server_info():
            """broadcast服务器信息"""
            try:
                if not self.is_host:
                    # 已经不是主机了，停止广播
                    self._stop_host_broadcast()
                    return
                
                if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                    # 获取本机EasyTier虚拟IP
                    virtual_ip = ""
                    if hasattr(self.parent_window, 'controller') and hasattr(self.parent_window.controller, 'easytier'):
                        virtual_ip = self.parent_window.controller.easytier.virtual_ip or ''
                    
                    self.parent_window.tcp_broadcast.publish(
                        "game/started",
                        {
                            "game_name": game_name,
                            "world_name": world_name,
                            "player_name": player_name,
                            "port": port,
                            "host_ip": virtual_ip
                        }
                    )
                    logger.info(f"✅ 持续广播服务器信息: {virtual_ip}:{port}")
            except Exception as e:
                logger.error(f"广播服务器信息失败: {e}")
        
        # 创建定时器，每10秒广播一次
        self.broadcast_timer = QTimer()
        self.broadcast_timer.timeout.connect(broadcast_server_info)
        self.broadcast_timer.start(10000)  # 10秒
        logger.info("已启动主机广播定时器，每10秒广播一次")
    
    def _stop_host_broadcast(self):
        """停止主机广播定时器"""
        if self.broadcast_timer:
            self.broadcast_timer.stop()
            self.broadcast_timer.deleteLater()
            self.broadcast_timer = None
            logger.info("已停止主机广播定时器")
    
    def _start_starting_broadcast(self, game_name, world_name, player_name):
        """
        启动"启动中"状态广播定时器，每5秒广播一次，让新进来的玩家也能感知
        
        Args:
            game_name: 游戏名称
            world_name: 世界名称
            player_name: 玩家名称
        """
        from PyQt5.QtCore import QTimer
        
        # 先停止旧的定时器
        self._stop_starting_broadcast()
        
        def broadcast_starting():
            """广播游戏启动中消息"""
            try:
                if not self.is_host or self.game_port:
                    # 已经启动成功或不再是主机，停止广播
                    self._stop_starting_broadcast()
                    return
                
                if hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                    self.parent_window.tcp_broadcast.publish(
                        "game/starting",
                        {
                            "game_name": game_name,
                            "world_name": world_name,
                            "player_name": player_name
                        }
                    )
                    logger.info(f"⌚ 持续广播启动中: {game_name}/{world_name}")
            except Exception as e:
                logger.error(f"广播启动中消息失败: {e}")
        
        # 创建定时器，每5秒广播一次
        self.starting_broadcast_timer = QTimer()
        self.starting_broadcast_timer.timeout.connect(broadcast_starting)
        self.starting_broadcast_timer.start(5000)  # 5秒
        logger.info("已启动'启动中'广播定时器，每5秒广播一次")
    
    def _stop_starting_broadcast(self):
        """停止'启动中'状态广播定时器"""
        if self.starting_broadcast_timer:
            self.starting_broadcast_timer.stop()
            self.starting_broadcast_timer.deleteLater()
            self.starting_broadcast_timer = None
            logger.info("已停止'启动中'广播定时器")
    
    def close_game(self):
        """关闭游戏进程"""
        try:
            if not self.game_process:
                InfoBar.warning(
                    title='提示',
                    content="没有正在运行的游戏进程",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            logger.info(f"准备关闭游戏进程 PID={self.game_process.pid}")
            
            # 先停止广播
            self._stop_host_broadcast()
            
            # 终止游戏进程
            import psutil
            try:
                process = psutil.Process(self.game_process.pid)
                # 先尝试优雅关闭
                process.terminate()
                # 等待3秒
                try:
                    process.wait(timeout=3)
                    logger.info("游戏进程已优雅关闭")
                except psutil.TimeoutExpired:
                    # 如果超时，强制杀死
                    process.kill()
                    logger.warning("游戏进程强制关闭")
            except psutil.NoSuchProcess:
                logger.warning("游戏进程已经不存在")
            except Exception as e:
                logger.error(f"关闭游戏进程失败: {e}")
                # 如果psutil失败，尝试使用原始方法
                try:
                    self.game_process.terminate()
                    self.game_process.wait(timeout=3)
                except:
                    self.game_process.kill()
            
            # 广播主机掉线消息
            if self.is_host and hasattr(self.parent_window, 'tcp_broadcast') and self.parent_window.tcp_broadcast:
                game_name = self.selected_game.get('name', '') if self.selected_game else ''
                world_name = self.game_world or ''
                player_name = self.selected_game.get('selected_account', {}).get('name', '') if self.selected_game else ''
                
                self.parent_window.tcp_broadcast.publish(
                    "game/host_offline",
                    {
                        "game_name": game_name,
                        "world_name": world_name,
                        "player_name": player_name
                    }
                )
                logger.info("已广播主机掉线消息")
            
            # 重置状态
            self.is_host = False
            self.game_process = None
            self.game_port = None
            self.game_world = None
            
            # 恢复按钮状态
            self.launch_game_btn.setVisible(True)
            self.launch_game_btn.setEnabled(True)
            self.join_game_btn.setVisible(False)
            self.close_game_btn.setVisible(False)
            
            InfoBar.success(
                title='成功',
                content="游戏已关闭",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
        except Exception as e:
            logger.error(f"关闭游戏失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            InfoBar.error(
                title='错误',
                content=f"关闭游戏失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

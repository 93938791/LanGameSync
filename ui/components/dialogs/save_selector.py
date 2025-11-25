"""
存档选择对话框
显示版本隔离的游戏版本和存档,供用户选择
"""
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTreeWidget, QTreeWidgetItem, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QColor
from utils.logger import Logger

logger = Logger().get_logger("SaveSelector")


class SaveSelectorDialog(QDialog):
    """存档选择对话框 - 选择版本并配置存档同步锁定状态"""
    
    def __init__(self, parent, versions_data):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            versions_data: 版本数据列表
        """
        super().__init__(parent)
        self.versions_data = versions_data
        self.selected_version = None
        self.unlocked_saves = []  # 解锁的存档列表(只有这些会被同步)
        
        self.setWindowTitle("选择版本实例")
        self.setModal(True)
        self.setFixedSize(700, 600)
        
        # 无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 主容器
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 标题栏
        title_bar = self.create_title_bar()
        container_layout.addWidget(title_bar)
        
        # 内容区域
        content = QWidget()
        content.setStyleSheet("background: #f7f7f7;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(25, 20, 25, 20)
        content_layout.setSpacing(15)
        
        # 提示文字
        tip_label = QLabel("💡 请选择要同步的游戏版本:")
        tip_label.setStyleSheet("font-size: 13px; color: #666666;")
        content_layout.addWidget(tip_label)
        
        info_label = QLabel("提示: 选择版本即可,不需要选择存档(后续可解锁指定存档)")
        info_label.setStyleSheet("font-size: 12px; color: #999999; margin-bottom: 5px;")
        content_layout.addWidget(info_label)
        
        # 版本树形列表
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["版本 / 存档", "同步状态"])
        self.tree_widget.setColumnWidth(0, 450)
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 13px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f5f5f5;
            }
            QTreeWidget::item:hover {
                background: #f7f7f7;
            }
            QTreeWidget::item:selected {
                background: #e7f4ed;
                color: #07c160;
            }
            QTreeWidget::branch:has-children {
                background: transparent;
            }
        """)
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        
        # 加载版本数据
        self.load_versions()
        
        content_layout.addWidget(self.tree_widget, 1)
        
        # 空状态提示
        if not self.versions_data:
            empty_label = QLabel("⚠️ 未检测到版本隔离的游戏版本\n\n请确保:\n1. 已启用版本隔离\n2. 至少启动过一次游戏")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("font-size: 14px; color: #999999; padding: 40px;")
            content_layout.addWidget(empty_label)
        
        container_layout.addWidget(content, 1)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(25, 15, 25, 20)
        btn_layout.setSpacing(10)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        
        confirm_btn = QPushButton("确定")
        confirm_btn.setFixedHeight(40)
        confirm_btn.setMinimumWidth(120)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.clicked.connect(self.on_confirm)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        
        container_layout.addLayout(btn_layout)
        
        layout.addWidget(container)
    
    def create_title_bar(self):
        """创建标题栏"""
        title_bar = QWidget()
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("""
            QWidget {
                background: #fafafa;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(20, 0, 10, 0)
        
        title_label = QLabel("选择要同步的版本实例")
        title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #2c2c2c; background: transparent; border: none;")
        layout.addWidget(title_label)
        layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton()
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons')
        close_icon_path = os.path.join(icon_dir, 'close.png')
        if os.path.exists(close_icon_path):
            close_btn.setIcon(QIcon(close_icon_path))
            close_btn.setIconSize(QPixmap(16, 16).size())
        else:
            close_btn.setText("✕")
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #666666;
                font-size: 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #f0f0f0;
                color: #333333;
            }
        """)
        layout.addWidget(close_btn)
        
        return title_bar
    
    def load_versions(self):
        """加载版本数据到树形列表 - 只显示版本,不显示存档"""
        self.tree_widget.clear()
        
        for version_data in self.versions_data:
            version_name = version_data['name']
            saves = version_data['saves']
            save_count = len(saves)
            game_version = version_data.get('game_version', version_name)
            loader_type = version_data.get('loader_type', 'vanilla')
            
            # 构建显示文本
            display_text = f"📦 {version_name}"
            if game_version != version_name:
                display_text += f" ({game_version})"
            
            # 添加加载器信息
            loader_display = {
                'vanilla': '原版',
                'fabric': 'Fabric',
                'forge': 'Forge',
                'neoforge': 'NeoForge'
            }.get(loader_type, loader_type)
            
            # 创建版本节点 - 不再添加子节点
            version_item = QTreeWidgetItem(self.tree_widget)
            version_item.setText(0, display_text)
            version_item.setText(1, f"{loader_display} | {save_count}个存档")
            version_item.setData(0, Qt.UserRole, {'type': 'version', 'data': version_data})
    
    def on_item_clicked(self, item, column):
        """树形项点击事件 - 点击版本选中"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        if data['type'] == 'version':
            # 选中了版本
            version_data = data['data']
            self.selected_version = version_data['name']
            logger.info(f"选中版本: {self.selected_version}")
    
    def on_confirm(self):
        """确认按钮点击"""
        if not self.selected_version:
            from ui.components import MessageBox
            MessageBox.show_warning(self, "提示", "请选择要同步的版本!")
            return
        
        self.accept()

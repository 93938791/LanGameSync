"""
账号选择对话框
从启动器读取所有账号并让用户选择
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QWidget, QListWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from qfluentwidgets import (
    CardWidget, SubtitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, ListWidget, IconWidget, FluentIcon
)
from managers.launcher_account_reader import LauncherAccountReader
from utils.logger import logger


class AccountSelectorDialog(QDialog):
    """账号选择对话框"""
    
    def __init__(self, launcher_path, parent=None):
        super().__init__(parent)
        self.launcher_path = launcher_path
        self.selected_account = None
        self.accounts = []
        
        self.setWindowTitle("选择账号")
        self.setFixedSize(450, 500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        self.init_ui()
        self.load_accounts()
    
    def init_ui(self):
        """初始化UI"""
        # 主容器
        main_container = CardWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        # 图标 + 标题
        icon_widget = IconWidget(FluentIcon.PEOPLE)
        icon_widget.setFixedSize(28, 28)
        header_layout.addWidget(icon_widget)
        
        title = SubtitleLabel("选择账号")
        title.setStyleSheet("font-weight: 600; margin-left: 8px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 关闭按钮
        close_btn = PushButton(FluentIcon.CLOSE, "")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            PushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            PushButton:hover {
                background: rgba(0, 0, 0, 0.06);
            }
            PushButton:pressed {
                background: rgba(0, 0, 0, 0.1);
            }
        """)
        header_layout.addWidget(close_btn)
        
        main_layout.addLayout(header_layout)
        
        # 启动器信息
        self.launcher_info = BodyLabel("正在读取启动器账号...")
        self.launcher_info.setStyleSheet("color: #606060;")
        main_layout.addWidget(self.launcher_info)
        
        # 账号列表卡片
        list_card = CardWidget()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.account_list = ListWidget()
        self.account_list.setStyleSheet("""
            ListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 16px;
                border-radius: 6px;
                margin: 3px 4px;
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
        self.account_list.itemDoubleClicked.connect(self.on_account_double_clicked)
        list_layout.addWidget(self.account_list)
        
        main_layout.addWidget(list_card, 1)
        
        # 提示信息
        hint_card = CardWidget()
        hint_card.setStyleSheet("""
            CardWidget {
                background: #e8f4fd;
                border: 1px solid #91d5ff;
            }
        """)
        hint_layout = QHBoxLayout(hint_card)
        hint_layout.setContentsMargins(12, 8, 12, 8)
        
        hint_icon = IconWidget(FluentIcon.INFO)
        hint_icon.setFixedSize(16, 16)
        hint_layout.addWidget(hint_icon)
        
        hint = CaptionLabel("双击账号或点击确定按钮选择")
        hint.setStyleSheet("color: #096dd9; margin-left: 6px;")
        hint_layout.addWidget(hint)
        hint_layout.addStretch()
        
        main_layout.addWidget(hint_card)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        cancel_btn = PushButton("取消")
        cancel_btn.setFixedSize(100, 36)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = PrimaryPushButton("确定")
        ok_btn.setFixedSize(100, 36)
        ok_btn.clicked.connect(self.on_ok_clicked)
        btn_layout.addWidget(ok_btn)
        
        main_layout.addLayout(btn_layout)
        
        # 设置主布局
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(main_container)
    
    def load_accounts(self):
        """加载启动器中的所有账号"""
        try:
            reader = LauncherAccountReader(self.launcher_path)
            launcher_type = reader.get_launcher_type()
            
            # 读取所有账号
            all_accounts = reader.get_all_accounts()
            
            if not all_accounts:
                self.launcher_info.setText("❌ 启动器中没有账号")
                self.launcher_info.setStyleSheet("color: #d13438;")
                return
            
            self.accounts = all_accounts
            self.launcher_info.setText(f"✅ 启动器类型: {launcher_type} | 共 {len(all_accounts)} 个账号")
            self.launcher_info.setStyleSheet("color: #107c10;")
            
            # 显示账号列表
            for account in all_accounts:
                self.add_account_item(account)
            
            # 默认选中第一个（最近使用的通常在最后，但这里显示第一个方便选择）
            if self.account_list.count() > 0:
                # 选中最后一个（最近使用的）
                last_index = self.account_list.count() - 1
                self.account_list.setCurrentRow(last_index)
            
        except Exception as e:
            logger.error(f"加载账号失败: {e}")
            self.launcher_info.setText(f"❌ 加载失败: {str(e)}")
            self.launcher_info.setStyleSheet("color: #d13438;")
    
    def add_account_item(self, account):
        """添加账号项到列表"""
        player_name = account.get('player_name', 'Unknown')
        account_type = account.get('account_type', 'offline')
        is_valid = account.get('is_valid', False)
        
        # 账号类型图标
        type_icon = {
            'offline': '🔵',
            'microsoft': '🟢',
            'mojang': '🟠',
            'authlib': '🟣'
        }.get(account_type, '⚪')
        
        # 账号类型文字
        type_text = {
            'offline': '离线',
            'microsoft': 'Microsoft',
            'mojang': 'Mojang',
            'authlib': 'AuthLib'
        }.get(account_type, '未知')
        
        # 状态
        status = '✅ 有效' if is_valid else '❌ 无效'
        
        # 构建显示文本
        text = f"{type_icon} {player_name}\n    类型: {type_text} | 状态: {status}"
        
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, account)
        
        # 如果无效，设置灰色
        if not is_valid:
            item.setForeground(QColor("#999999"))
        
        self.account_list.addItem(item)
    
    def on_account_double_clicked(self, item):
        """账号双击事件"""
        account = item.data(Qt.UserRole)
        if account and account.get('is_valid'):
            self.selected_account = account
            self.accept()
    
    def on_ok_clicked(self):
        """确定按钮点击"""
        current_item = self.account_list.currentItem()
        if current_item:
            account = current_item.data(Qt.UserRole)
            if account and account.get('is_valid'):
                self.selected_account = account
                self.accept()
            else:
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.warning(
                    title='提示',
                    content="所选账号无效，请选择有效账号",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        else:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning(
                title='提示',
                content="请先选择一个账号",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def get_selected_account(self):
        """获取选中的账号"""
        return self.selected_account

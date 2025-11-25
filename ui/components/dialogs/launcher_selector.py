"""
启动器选择对话框 - Fluent Design 风格
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from qfluentwidgets import (
    CardWidget, SubtitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, IconWidget, FluentIcon
)
from utils.logger import Logger

logger = Logger().get_logger("LauncherSelector")


class LauncherSelectorDialog(QDialog):
    """启动器选择对话框（拖放）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择启动器")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.resize(680, 650)
        self.setAcceptDrops(True)
        
        self.show_tips = True  # 是否显示提示页面
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 主容器 - 使用 CardWidget
        main_container = CardWidget()
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(28, 28, 28, 28)
        container_layout.setSpacing(20)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        # 图标
        icon = IconWidget(FluentIcon.GAME)
        icon.setFixedSize(28, 28)
        title_layout.addWidget(icon)
        
        # 标题
        title_label = SubtitleLabel("添加我的世界")
        title_label.setStyleSheet("font-weight: 600; margin-left: 8px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
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
        title_layout.addWidget(close_btn)
        
        container_layout.addLayout(title_layout)
        
        # 提示卡片
        tips_card = CardWidget()
        tips_card.setStyleSheet("""
            CardWidget {
                background: #fffbe6;
                border: 1px solid #ffe58f;
            }
        """)
        tips_layout = QVBoxLayout(tips_card)
        tips_layout.setContentsMargins(16, 16, 16, 16)
        tips_layout.setSpacing(12)
        
        # 提示标题
        tips_title_layout = QHBoxLayout()
        tips_icon = IconWidget(FluentIcon.INFO)
        tips_icon.setFixedSize(20, 20)
        tips_title_layout.addWidget(tips_icon)
        
        tips_title = BodyLabel("拖入启动器前,请确保已完成以下准备:")
        tips_title.setStyleSheet("font-weight: 600; color: #d48806; margin-left: 6px;")
        tips_title_layout.addWidget(tips_title)
        tips_title_layout.addStretch()
        tips_layout.addLayout(tips_title_layout)
        
        # 提示内容
        tips_text = BodyLabel(
            "<b>1. 启用版本隔离</b><br>"
            "   • <b>HMCL:</b> 设置 → 版本隔离 → 各实例独立<br>"
            "   • <b>PCL2:</b> 设置 → 启动选项 → 隔离所有版本<br><br>"
            "<b>2. 准备游戏版本</b><br>"
            "   • 所有玩家必须使用<b>相同版本</b>(如1.21.4)<br><br>"
            "<b>3. 主机玩家至少启动一次游戏</b><br>"
            "   • 确保生成saves文件夹<br><br>"
            "<b>💡 提示:</b> 本程序只同步存档,不同步mod和配置!"
        )
        tips_text.setWordWrap(True)
        tips_text.setOpenExternalLinks(True)
        tips_text.setStyleSheet("""
            color: #595959;
            font-size: 13px;
            line-height: 1.6;
        """)
        tips_layout.addWidget(tips_text)
        
        container_layout.addWidget(tips_card)
        
        # 拖放区域
        from PyQt5.QtWidgets import QLabel
        self.drop_area = QLabel("📥\n\n将 HMCL 或 PCL 启动器\n拖入此处\n\n或点击下方按钮选择")
        self.drop_area.setObjectName("dropArea")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setMinimumHeight(160)
        self.drop_area.setStyleSheet("""
            QLabel#dropArea {
                background: #fafafa;
                border: 2px dashed #d9d9d9;
                border-radius: 8px;
                color: #999999;
                font-size: 14px;
                padding: 20px;
            }
        """)
        container_layout.addWidget(self.drop_area)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = PushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        browse_btn = PrimaryPushButton(FluentIcon.FOLDER, "浏览选择")
        browse_btn.setFixedHeight(40)
        browse_btn.setMinimumWidth(120)
        browse_btn.clicked.connect(self.browse_file)
        btn_layout.addWidget(browse_btn)
        
        btn_layout.addStretch()
        
        container_layout.addLayout(btn_layout)
        
        layout.addWidget(main_container)
    
    def browse_file(self):
        """浏览文件"""
        launcher_file, _ = QFileDialog.getOpenFileName(
            self,
            "选择 HMCL 或 PCL 启动器",
            "",
            "Launcher Files (*.jar *.exe);;All Files (*.*)"
        )
        if launcher_file:
            self.handle_launcher_file(launcher_file)
    
    def handle_launcher_file(self, launcher_file):
        """处理启动器文件"""
        try:
            # 扫描版本和存档
            from ui.minecraft.version_scanner import MinecraftVersionScanner
            from ui.components.dialogs.save_selector import SaveSelectorDialog
            from ui.components import MessageBox
            from utils.config_cache import ConfigCache
            
            logger.info(f"开始扫描启动器: {launcher_file}")
            
            scanner = MinecraftVersionScanner(launcher_file)
            versions = scanner.scan_versions()
            
            if not versions:
                MessageBox.show_warning(
                    self,
                    "未检测到版本",
                    "未检测到版本隔离的游戏版本!\n\n请确保:\n1. 已启用版本隔离\n2. 至少启动过一次游戏"
                )
                return
            
            # 显示存档选择对话框
            save_dialog = SaveSelectorDialog(self, versions)
            if save_dialog.exec_() == save_dialog.Accepted:
                # 获取选中的版本和解锁的存档列表
                version_name = save_dialog.selected_version
                unlocked_saves = save_dialog.unlocked_saves  # 格式: ["version/save1", "version/save2"]
                
                # 获取saves文件夹路径
                save_path = scanner.get_save_full_path(version_name, None)
                
                logger.info(f"选中版本: {version_name}")
                logger.info(f"saves文件夹路径: {save_path}")
                logger.info(f"解锁的存档: {unlocked_saves}")
                
                # 提取存档名列表(去掉版本前缀)
                unlocked_save_names = [s.split('/')[-1] for s in unlocked_saves if s.startswith(f"{version_name}/")]
                
                # 保存到配置
                config_data = ConfigCache.load()
                if "game_list" not in config_data:
                    config_data["game_list"] = []
                
                game_name = f"我的世界 - {version_name}"
                
                config_data["game_list"].append({
                    "name": game_name,
                    "type": "minecraft",
                    "launcher": scanner.launcher_type,
                    "launcher_path": launcher_file,  # 保存启动器路径
                    "version": version_name,
                    "save_path": save_path,  # saves文件夹路径
                    "minecraft_dir": scanner.minecraft_dir,
                    "unlocked_saves": unlocked_save_names  # 解锁的存档列表(只同步这些)
                })
                
                ConfigCache.save(config_data)
                
                unlock_count = len(unlocked_save_names)
                if unlock_count > 0:
                    MessageBox.show_info(self, "成功", f"已添加游戏:\n{game_name}\n解锁存档: {unlock_count}个")
                else:
                    MessageBox.show_info(self, "成功", f"已添加游戏:\n{game_name}\n所有存档已锁定(不会同步)")
                
                self.accept()
        
        except Exception as e:
            logger.error(f"处理启动器文件时出错: {e}")
            from ui.components import MessageBox
            MessageBox.show_error(self, "错误", f"处理失败:\n{str(e)}")
    
    def dragEnterEvent(self, event):
        """拖入事件"""
        if event.mimeData().hasUrls():
            event.accept()
            self.drop_area.setStyleSheet("""
                QLabel#dropArea {
                    background: #e6f7ff;
                    border: 2px dashed #1890ff;
                    border-radius: 8px;
                    color: #0078d4;
                    font-size: 14px;
                    padding: 20px;
                }
            """)
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """拖出事件"""
        self.drop_area.setStyleSheet("""
            QLabel#dropArea {
                background: #fafafa;
                border: 2px dashed #d9d9d9;
                border-radius: 8px;
                color: #999999;
                font-size: 14px;
                padding: 20px;
            }
        """)
    
    def dropEvent(self, event):
        """放下事件"""
        try:
            import os
            from ui.components import MessageBox
            
            files = [u.toLocalFile() for u in event.mimeData().urls()]
            if not files:
                logger.warning("拖入操作没有文件")
                return
            
            launcher_file = files[0]
            if not launcher_file or not os.path.exists(launcher_file):
                MessageBox.show_warning(self, "警告", "文件不存在或无效")
                return
            
            if launcher_file.lower().endswith(('.jar', '.exe')):
                self.handle_launcher_file(launcher_file)
            else:
                MessageBox.show_warning(self, "警告", "请选择 .jar 或 .exe 文件")
        except Exception as e:
            logger.error(f"处理拖入文件时出错: {e}")
            from ui.components import MessageBox
            MessageBox.show_error(self, "错误", f"处理文件失败：{str(e)}")

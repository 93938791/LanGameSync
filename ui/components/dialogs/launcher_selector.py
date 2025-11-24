"""
启动器选择对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QWidget, QFileDialog
)
from PyQt5.QtCore import Qt
from utils.logger import Logger

logger = Logger().get_logger("LauncherSelector")


class LauncherSelectorDialog(QDialog):
    """启动器选择对话框（拖放）"""
    
    def __init__(self, parent=None, on_file_selected=None):
        super().__init__(parent)
        self.on_file_selected = on_file_selected
        self.setWindowTitle("选择启动器")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.resize(500, 350)
        self.setAcceptDrops(True)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 主容器
        main_container = QWidget()
        main_container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 8px;
            }
        """)
        
        container_layout = QVBoxLayout(self)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("选择 HMCL/PCL 启动器")
        title_label.setStyleSheet("""
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # 拖放区域
        self.drop_area = QLabel("📥\n\n将 HMCL 或 PCL 启动器\n拖入此处\n\n或点击下方按钮选择")
        self.drop_area.setObjectName("dropArea")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setMinimumHeight(150)
        self.drop_area.setStyleSheet("""
            QLabel#dropArea {
                background: #f5f5f5;
                border: 2px dashed #d0d0d0;
                border-radius: 8px;
                color: #999999;
                font-size: 14px;
                padding: 20px;
            }
        """)
        layout.addWidget(self.drop_area)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        browse_btn = QPushButton("📂 浏览选择")
        browse_btn.setFixedHeight(40)
        browse_btn.setMinimumWidth(120)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_file)
        browse_btn.setStyleSheet("""
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
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(browse_btn)
        
        layout.addLayout(btn_layout)
        container_layout.addWidget(main_container)
        
        # 居中显示
        self.adjustSize()
    
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
        self.accept()
        if self.on_file_selected:
            self.on_file_selected(launcher_file)
    
    def dragEnterEvent(self, event):
        """拖入事件"""
        if event.mimeData().hasUrls():
            event.accept()
            self.drop_area.setStyleSheet("""
                QLabel#dropArea {
                    background: #e8f5e9;
                    border: 2px dashed #07c160;
                    border-radius: 8px;
                    color: #07c160;
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
                background: #f5f5f5;
                border: 2px dashed #d0d0d0;
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

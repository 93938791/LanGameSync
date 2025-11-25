"""
设备列表对话框
显示所有已连接的设备
"""
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPixmap, QIcon
from utils.logger import Logger

logger = Logger().get_logger("DeviceListDialog")


class DeviceListDialog(QDialog):
    """设备列表对话框"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("所有已连接设备")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        
        # 无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui()
        self.load_devices()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 主容器
        container = QLabel()
        container.setStyleSheet("""
            QLabel {
                background: #ffffff;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 标题栏
        title_bar = QLabel()
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("""
            QLabel {
                background: #f7f7f7;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 10, 0)
        
        # 标题文字
        title_label = QLabel("所有已连接设备")
        title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #2c2c2c;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
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
        close_btn.clicked.connect(self.accept)
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
        title_layout.addWidget(close_btn)
        
        container_layout.addWidget(title_bar)
        
        # 设备列表表格
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(3)
        self.devices_table.setHorizontalHeaderLabels(["设备名", "IP地址", "延迟"])
        self.devices_table.horizontalHeader().setStretchLastSection(True)
        self.devices_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.devices_table.setColumnWidth(1, 180)
        self.devices_table.setColumnWidth(2, 100)
        self.devices_table.verticalHeader().setVisible(False)
        self.devices_table.setAlternatingRowColors(False)
        self.devices_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.devices_table.setShowGrid(False)
        self.devices_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: none;
                font-size: 13px;
                outline: none;
            }
            QTableWidget::item {
                padding: 18px 15px;
                border-bottom: 1px solid #f0f0f0;
                color: #2c2c2c;
            }
            QHeaderView::section {
                background: #fafafa;
                padding: 15px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                font-weight: 600;
                color: #4a4a4a;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background: #e7f4ed;
                color: #07c160;
            }
            QTableWidget::item:hover {
                background: #f7f7f7;
            }
        """)
        
        container_layout.addWidget(self.devices_table, 1)
        
        layout.addWidget(container)
    
    def load_devices(self):
        """加载设备列表"""
        try:
            # 获取对等设备列表
            peers = self.controller.easytier.discover_peers(timeout=3)
            
            # 清空表格
            self.devices_table.setRowCount(0)
            
            # 添加本机
            row = 0
            self.devices_table.insertRow(row)
            
            # 设备名
            device_name_item = QTableWidgetItem("💻 本机")
            device_name_item.setFont(QFont("Microsoft YaHei", 13))
            self.devices_table.setItem(row, 0, device_name_item)
            
            # IP地址
            ip_item = QTableWidgetItem(self.controller.easytier.virtual_ip or "unknown")
            ip_item.setFont(QFont("Consolas", 12))
            self.devices_table.setItem(row, 1, ip_item)
            
            # 延迟
            latency_item = QTableWidgetItem("-")
            self.devices_table.setItem(row, 2, latency_item)
            
            # 添加其他设备（去除重复）
            seen_ips = set([self.controller.easytier.virtual_ip])
            
            for peer in peers:
                ipv4 = peer.get('ipv4', '')
                if ipv4 and ipv4 not in seen_ips:
                    row += 1
                    self.devices_table.insertRow(row)
                    
                    hostname = peer.get('hostname', 'Unknown')
                    latency = peer.get('latency', '-')
                    
                    # 设备名
                    device_item = QTableWidgetItem(f"🖥️ {hostname}")
                    device_item.setFont(QFont("Microsoft YaHei", 13))
                    self.devices_table.setItem(row, 0, device_item)
                    
                    # IP地址
                    ip_item = QTableWidgetItem(ipv4)
                    ip_item.setFont(QFont("Consolas", 12))
                    self.devices_table.setItem(row, 1, ip_item)
                    
                    # 延迟 - 添加颜色区分
                    latency_item = QTableWidgetItem(latency)
                    if latency != '-':
                        try:
                            lat_ms = float(latency.replace('ms', '').strip())
                            if lat_ms < 50:
                                latency_item.setForeground(Qt.green)
                            elif lat_ms < 100:
                                latency_item.setForeground(QColor("#07c160"))
                            else:
                                latency_item.setForeground(QColor("#fa5151"))
                        except:
                            pass
                    self.devices_table.setItem(row, 2, latency_item)
                    
                    seen_ips.add(ipv4)
            
            logger.info(f"加载设备列表: 总计 {row + 1} 台设备")
            
        except Exception as e:
            logger.error(f"加载设备列表失败: {e}")

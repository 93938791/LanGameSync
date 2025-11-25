"""
联机消息页面
显示UDP广播的发送和接收消息
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from qfluentwidgets import (
    CardWidget, SubtitleLabel, BodyLabel, CaptionLabel,
    PushButton, TableWidget, IconWidget, FluentIcon
)
from datetime import datetime
from utils.logger import Logger

logger = Logger().get_logger("MessageInterface")


class MessageInterface(QWidget):
    """联机消息界面"""
    
    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
        
        # 设置全局唯一的对象名称（必须）
        self.setObjectName("messageInterface")
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 创建消息面板
        self.create_message_panel(main_layout)
    
    def create_message_panel(self, parent_layout):
        """创建消息面板"""
        card = CardWidget()
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        title_icon = IconWidget(FluentIcon.MESSAGE)
        title_icon.setFixedSize(24, 24)
        header_layout.addWidget(title_icon)
        
        title = SubtitleLabel("UDP消息推送")
        title.setStyleSheet("font-weight: 600; margin-left: 8px;")
        header_layout.addWidget(title)
        
        # 统计信息
        self.stats_label = BodyLabel("总计: 0 | 发送: 0 | 接收: 0")
        self.stats_label.setStyleSheet("color: #606060; margin-left: 16px;")
        header_layout.addWidget(self.stats_label)
        
        header_layout.addStretch()
        
        # 清空按钮
        clear_btn = PushButton(FluentIcon.DELETE, "清空")
        clear_btn.setFixedHeight(32)
        clear_btn.clicked.connect(self.clear_messages)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # 提示卡片
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
        
        hint = CaptionLabel("实时显示UDP广播消息，包括设备上线、游戏启动等联机通信消息")
        hint.setStyleSheet("color: #096dd9; margin-left: 6px;")
        hint_layout.addWidget(hint)
        hint_layout.addStretch()
        
        layout.addWidget(hint_card)
        
        # 消息列表
        self.message_table = TableWidget()
        self.message_table.setColumnCount(5)
        self.message_table.setHorizontalHeaderLabels(["时间", "类型", "主题", "详细信息", "来源IP"])
        
        # 设置列宽
        from PyQt5.QtWidgets import QHeaderView
        self.message_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 时间
        self.message_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 类型
        self.message_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 主题
        self.message_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # 详细信息
        self.message_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 来源
        
        self.message_table.setStyleSheet("""
            TableWidget {
                background: transparent;
                border: 1px solid #e5e5e5;
                border-radius: 6px;
            }
        """)
        
        layout.addWidget(self.message_table, 1)
        
        parent_layout.addWidget(card)
        
        # 统计数据
        self.total_count = 0
        self.send_count = 0
        self.receive_count = 0
    
    def clear_messages(self):
        """清空消息列表"""
        self.message_table.setRowCount(0)
        self.total_count = 0
        self.send_count = 0
        self.receive_count = 0
        self.update_stats()
    
    def add_message(self, message_type, topic, source_ip, data=None):
        """
        添加消息到列表
        
        Args:
            message_type: 消息类型（发送/接收）
            topic: 消息主题
            source_ip: 来源IP
            data: 消息数据（dict）
        """
        # 插入新行（在顶部）
        self.message_table.insertRow(0)
        
        # 时间
        time_str = datetime.now().strftime("%H:%M:%S")
        time_item = QTableWidgetItem(time_str)
        time_item.setTextAlignment(Qt.AlignCenter)
        self.message_table.setItem(0, 0, time_item)
        
        # 类型
        type_item = QTableWidgetItem(message_type)
        type_item.setTextAlignment(Qt.AlignCenter)
        if message_type == "发送":
            type_item.setForeground(QColor("#0078d4"))  # 蓝色
            self.send_count += 1
        else:
            type_item.setForeground(QColor("#107c10"))  # 绿色
            self.receive_count += 1
        self.message_table.setItem(0, 1, type_item)
        
        # 主题
        topic_item = QTableWidgetItem(topic)
        self.message_table.setItem(0, 2, topic_item)
        
        # 详细信息（根据主题解析data）
        detail = self._format_message_detail(topic, data)
        detail_item = QTableWidgetItem(detail)
        self.message_table.setItem(0, 3, detail_item)
        
        # 来源
        source_item = QTableWidgetItem(source_ip)
        source_item.setTextAlignment(Qt.AlignCenter)
        self.message_table.setItem(0, 4, source_item)
        
        # 限制最多200条消息
        if self.message_table.rowCount() > 200:
            self.message_table.removeRow(200)
        else:
            self.total_count += 1
        
        # 更新统计
        self.update_stats()
    
    def _format_message_detail(self, topic, data):
        """
        格式化消息详情
        
        Args:
            topic: 消息主题
            data: 消息数据
            
        Returns:
            格式化后的详细信息
        """
        if not data:
            return "-"
        
        try:
            if topic == "device/online":
                # 设备上线
                hostname = data.get('hostname', '')
                virtual_ip = data.get('virtual_ip', '')
                return f"设备: {hostname} ({virtual_ip})"
            
            elif topic == "game/starting":
                # 游戏启动中
                player = data.get('player_name', '')
                world = data.get('world_name', '')
                return f"玩家: {player}, 世界: {world}"
            
            elif topic == "game/started":
                # 游戏已启动
                player = data.get('player_name', '')
                world = data.get('world_name', '')
                port = data.get('port', '')
                host_ip = data.get('host_ip', '')
                return f"玩家: {player}, 世界: {world}, 端口: {port}, 主机IP: {host_ip}"
            
            elif topic == "game/failed":
                # 游戏启动失败
                player = data.get('player_name', '')
                error = data.get('error', '')
                return f"玩家: {player}, 错误: {error}"
            
            else:
                # 其他消息，显示所有字段
                details = []
                for key, value in data.items():
                    if key not in ['type']:  # 过滤type字段
                        details.append(f"{key}: {value}")
                return ", ".join(details) if details else "-"
                
        except Exception as e:
            logger.error(f"格式化消息详情失败: {e}")
            return "-"
    
    def update_stats(self):
        """更新统计信息"""
        self.stats_label.setText(
            f"总计: {self.total_count} | 发送: {self.send_count} | 接收: {self.receive_count}"
        )

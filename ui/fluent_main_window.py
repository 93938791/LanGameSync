"""
Fluent Design 风格主窗口
使用 PyQt-Fluent-Widgets 组件库
"""
import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon, 
    setTheme, Theme, setThemeColor
)

from config import Config
from managers.sync_controller import SyncController
from utils.logger import Logger
from utils.config_cache import ConfigCache
from ui.minecraft import MinecraftPathResolver
from ui.pages import NetworkInterface, GameInterface, SettingsInterface, MessageInterface, SyncInterface

logger = Logger().get_logger("FluentMainWindow")


class FluentMainWindow(FluentWindow):
    """Fluent Design 风格主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化控制器
        self.controller = SyncController()
        self.connect_thread = None
        self.scan_thread = None
        
        # 状态跟踪
        self.last_sync_state = None
        self.last_peer_ips = set()
        self.last_peer_count = 0
        self.scan_count = 0
        self.is_connected = False
        
        # MQTT和游戏启动器
        self.udp_broadcast = None
        self.game_launcher = None
        self.server_info = None
        
        # 加载配置
        self.config_data = ConfigCache.load()
        MinecraftPathResolver.update_minecraft_paths(self.config_data)
        
        # 初始化UI
        self.init_window()
        self.init_navigation()
        
        # 设置主题
        setTheme(Theme.LIGHT)
        setThemeColor('#07c160')  # 微信绿主题色
    
    def init_window(self):
        """初始化窗口"""
        self.setWindowTitle(f"{Config.APP_NAME}")
        
        # 设置固定尺寸（横向长方形窗口，宽度足够放下三个卡片）
        fixed_width = 1120
        fixed_height = 700
        self.setFixedSize(fixed_width, fixed_height)
        
        # 禁用最大化按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        
        # 不设置窗口图标（去掉logo）
        # icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'logo.ico')
        # if os.path.exists(icon_path):
        #     self.setWindowIcon(QIcon(icon_path))
        
        # 移动到屏幕中央
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
    
    def init_navigation(self):
        """初始化导航"""
        # 创建页面
        self.network_interface = NetworkInterface(self)
        self.game_interface = GameInterface(self)
        self.message_interface = MessageInterface(self)
        self.sync_interface = SyncInterface(self)
        self.settings_interface = SettingsInterface(self)
        
        # 添加导航项（必须设置唯一的objectName）
        self.addSubInterface(
            interface=self.network_interface, 
            icon=FluentIcon.WIFI, 
            text='联机设置',
            position=NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            interface=self.game_interface, 
            icon=FluentIcon.GAME, 
            text='游戏管理',
            position=NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            interface=self.message_interface, 
            icon=FluentIcon.MESSAGE, 
            text='联机消息',
            position=NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            interface=self.sync_interface, 
            icon=FluentIcon.SYNC, 
            text='存档同步',
            position=NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            interface=self.settings_interface, 
            icon=FluentIcon.SETTING, 
            text='设置',
            position=NavigationItemPosition.BOTTOM
        )
        
        # 设置默认页面
        self.switchTo(self.network_interface)
        
        # 启动时自动暂停所有同步文件夹
        self._pause_all_folders_on_startup()
    
    def on_syncthing_event(self, event_type, event_data):
        """
Syncthing事件回调(收到同步事件时自动调用)
        
        Args:
            event_type: 事件类型 (ItemFinished, FolderSummary, DownloadProgress)
            event_data: 事件数据
        """
        try:
            # 这里可以处理Syncthing事件
            logger.debug(f"Syncthing事件: {event_type}")
        except Exception as e:
            logger.debug(f"Syncthing事件处理失败: {e}")
    
    def on_udp_message(self, message_type, data, source_ip="", is_send=False):
        """
        UDP消息回调
        
        Args:
            message_type: 消息类型
            data: 消息数据
            source_ip: 来源IP
            is_send: 是否是发送的消息
        """
        try:
            logger.info(f"收到UDP消息: {message_type}")
            
            # 更新联机消息页面
            if hasattr(self, 'message_interface'):
                msg_type = "发送" if is_send else "接收"
                self.message_interface.add_message(msg_type, message_type, source_ip, data)
            
            # 处理游戏相关消息
            if message_type.startswith("game/") and not is_send:
                if hasattr(self, 'game_interface'):
                    self.game_interface.handle_game_message(message_type, data)
            
            if message_type == "device/online":
                # 收到设备上线消息，刷新客户端列表
                device_id = data.get('device_id', '')
                virtual_ip = data.get('virtual_ip', '')
                hostname = data.get('hostname', '')
                logger.info(f"设备上线: {hostname} ({virtual_ip})")
                
                # 刷新客户端列表
                if self.is_connected:
                    self.network_interface.update_clients_list()
                    logger.info("已刷新客户端列表")
        except Exception as e:
            logger.error(f"UDP消息处理失败: {e}")
    
    def _pause_all_folders_on_startup(self):
        """程序启动时，将所有游戏的同步状态设置为停止"""
        try:
            from utils.config_cache import ConfigCache
            
            config_data = ConfigCache.load()
            game_list = config_data.get("game_list", [])
            
            # 将所有游戏的is_syncing设置为False
            for game in game_list:
                game['is_syncing'] = False
            
            ConfigCache.save(config_data)
            logger.info(f"已将 {len(game_list)} 个游戏的同步状态重置为停止")
        except Exception as e:
            logger.error(f"重置同步状态失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件 - 断开网络和停止Syncthing"""
        try:
            logger.info("正在关闭程序...")
            
            # 1. 断开UDP广播
            if hasattr(self, 'udp_broadcast') and self.udp_broadcast:
                logger.info("正在关闭UDP广播...")
                self.udp_broadcast.disconnect()
                self.udp_broadcast = None
            
            # 2. 停止Syncthing
            if hasattr(self, 'syncthing_manager') and self.syncthing_manager:
                logger.info("正在停止Syncthing...")
                self.syncthing_manager.stop()
                self.syncthing_manager = None
            
            # 3. 断开EasyTier网络
            if hasattr(self, 'controller') and self.controller:
                if hasattr(self.controller, 'easytier') and self.controller.easytier:
                    logger.info("正在断开EasyTier网络...")
                    self.controller.easytier.stop()
            
            # 4. 重置连接状态
            self.is_connected = False
            
            logger.info("程序关闭清理完成")
            
        except Exception as e:
            logger.error(f"关闭程序时清理失败: {e}")
        finally:
            # 接受关闭事件
            event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FluentMainWindow()
    window.show()
    sys.exit(app.exec_())

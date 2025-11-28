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
    MSFluentWindow, NavigationItemPosition, FluentIcon, 
    setTheme, Theme, setThemeColor
)

from config import Config
from managers.sync_controller import SyncController
from utils.logger import Logger
from utils.config_cache import ConfigCache
from ui.minecraft import MinecraftPathResolver
from ui.pages import NetworkInterface, GameInterface, SettingsInterface, SyncInterface

logger = Logger().get_logger("FluentMainWindow")


class FluentMainWindow(MSFluentWindow):
    """微软风格流畅窗口"""
    
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
        
        # TCP广播
        self.tcp_broadcast = None
        
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
        
        # 设置固定尺寸（更宽，更矮）
        fixed_width = 1200
        fixed_height = 700
        self.setFixedSize(fixed_width, fixed_height)
        
        # 禁用最大化按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        
        # 设置窗口图标（logo）- 用于任务栏显示
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'logo.ico')
        if not os.path.exists(icon_path):
            # 尝试png格式
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'logo.png')
        
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
            # 同时设置应用图标（确保任务栏显示）
            QApplication.setWindowIcon(icon)
            logger.info(f"已设置窗口图标: {icon_path}")
        else:
            logger.warning(f"Logo文件不存在: {icon_path}")
        
        # 移动到屏幕中央
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
    
    def init_navigation(self):
        """初始化导航"""
        # 创建页面
        self.network_interface = NetworkInterface(self)
        self.game_interface = GameInterface(self)
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
        
        # 隐藏导航栏展开/收起按钮
        # 方法1: 设置导航栏不可折叠
        try:
            # 查找并隐藏折叠按钮
            if hasattr(self.navigationInterface, 'toggleButton'):
                self.navigationInterface.toggleButton.hide()
            # 或者设置为固定宽度，不允许折叠
            if hasattr(self.navigationInterface, 'setMinimumExpandWidth'):
                self.navigationInterface.setMinimumExpandWidth(200)
        except Exception as e:
            logger.warning(f"隐藏导航栏按钮失败: {e}")
        
        # 设置默认页面
        self.switchTo(self.network_interface)
        
        # 隐藏导航栏按钮（延迟执行确保UI已初始化）
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._hide_navigation_buttons)
        
        # 启动时清理不在游戏管理中的文件夹
        self._cleanup_orphaned_folders()
    
    def _hide_navigation_buttons(self):
        """隐藏导航栏按钮"""
        try:
            # 查找并隐藏导航栏中的所有按钮
            from PyQt5.QtWidgets import QPushButton
            
            # 隐藏 toggleButton（展开/收起按钮）
            for child in self.navigationInterface.children():
                if isinstance(child, QPushButton):
                    # 检查是否是折叠按钮
                    if hasattr(child, 'objectName') and 'toggle' in child.objectName().lower():
                        child.hide()
                        logger.info("已隐藏导航栏折叠按钮")
            
            # 尝试直接访问 toggleButton 属性
            if hasattr(self.navigationInterface, 'toggleButton'):
                self.navigationInterface.toggleButton.hide()
                logger.info("已隐藏 toggleButton")
                
            # 尝试访问 menuButton
            if hasattr(self.navigationInterface, 'menuButton'):
                self.navigationInterface.menuButton.hide()
                logger.info("已隐藏 menuButton")
                
        except Exception as e:
            logger.warning(f"隐藏导航栏按钮失败: {e}")
    
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
    
    def on_tcp_message(self, message_type, data, source_ip="", is_send=False):
        """
        TCP消息回调（在子线程中调用）
        
        Args:
            message_type: 消息类型
            data: 消息数据
            source_ip: 来源IP
            is_send: 是否是发送的消息
        """
        try:
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            import json
            
            logger.info(f"收到TCP消息: {message_type}")
            
            # 处理游戏相关消息
            if message_type.startswith("game/") and not is_send:
                if hasattr(self, 'game_interface'):
                    # 将data转为JSON字符串
                    data_json = json.dumps(data, ensure_ascii=False)
                    QMetaObject.invokeMethod(
                        self.game_interface,
                        "_handle_game_message_safe",
                        Qt.QueuedConnection,
                        Q_ARG(str, message_type),
                        Q_ARG(str, data_json)
                    )
            
            if message_type == "device/online":
                # 收到设备上线消息，刷新客户端列表
                device_id = data.get('device_id', '')
                virtual_ip = data.get('virtual_ip', '')
                hostname = data.get('hostname', '')
                logger.info(f"设备上线: {hostname} ({virtual_ip})")
                
                # 刷新客户端列表
                if self.is_connected:
                    QMetaObject.invokeMethod(
                        self.network_interface,
                        "update_clients_list",
                        Qt.QueuedConnection
                    )
                    logger.info("已调度刷新客户端列表")
        except Exception as e:
            logger.error(f"TCP消息处理失败: {e}")
    
    def _cleanup_orphaned_folders(self):
        """程序启动时，清理不在游戏管理中的Syncthing文件夹"""
        try:
            from utils.config_cache import ConfigCache
            
            # 等待Syncthing启动完成
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(3000, self._do_cleanup_orphaned_folders)
        except Exception as e:
            logger.error(f"清理孤立文件夹失败: {e}")
    
    def _do_cleanup_orphaned_folders(self):
        """执行清理孤立文件夹的操作"""
        try:
            from utils.config_cache import ConfigCache
            
            # 检查是否有syncthing_manager
            if not hasattr(self, 'controller') or not self.controller:
                return
            
            syncthing_manager = self.controller.syncthing
            if not syncthing_manager or not syncthing_manager.device_id:
                logger.warning("Syncthing未启动，跳过清理孤立文件夹")
                return
            
            # 获取游戏管理中的文件夹ID
            config_data = ConfigCache.load()
            game_list = config_data.get("game_list", [])
            game_folder_ids = set()
            for game in game_list:
                folder_id = game.get('sync_folder_id')
                if folder_id:
                    game_folder_ids.add(folder_id)
            
            # 获取Syncthing配置中的所有文件夹
            full_config = syncthing_manager.get_config(filter_self=False)
            if not full_config:
                return
            
            folders = full_config.get('folders', [])
            orphaned_folders = []
            
            for folder in folders:
                folder_id = folder.get('id')
                # 如果文件夹不在游戏管理中，则标记为孤立文件夹
                if folder_id not in game_folder_ids:
                    orphaned_folders.append(folder_id)
            
            # 删除孤立文件夹
            if orphaned_folders:
                logger.info(f"发现 {len(orphaned_folders)} 个孤立文件夹，开始清理: {orphaned_folders}")
                for folder_id in orphaned_folders:
                    try:
                        success = syncthing_manager.remove_folder(folder_id)
                        if success:
                            logger.info(f"已删除孤立文件夹: {folder_id}")
                        else:
                            logger.warning(f"删除孤立文件夹失败: {folder_id}")
                    except Exception as e:
                        logger.error(f"删除孤立文件夹 {folder_id} 时出错: {e}")
            else:
                logger.info("未发现孤立文件夹")
        except Exception as e:
            logger.error(f"清理孤立文件夹失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def closeEvent(self, event):
        """窗口关闭事件 - 同步清理资源，确保进程被终止"""
        try:
            logger.info("正在关闭程序...")
            
            # 重置连接状态（立即生效）
            self.is_connected = False
            
            # 停止所有定时器（立即生效）
            if hasattr(self, 'network_interface'):
                if hasattr(self.network_interface, 'traffic_timer') and self.network_interface.traffic_timer.isActive():
                    self.network_interface.traffic_timer.stop()
                if hasattr(self.network_interface, 'device_refresh_timer') and self.network_interface.device_refresh_timer.isActive():
                    self.network_interface.device_refresh_timer.stop()
            
            if hasattr(self, 'sync_interface'):
                if hasattr(self.sync_interface, 'auto_refresh_timer') and self.sync_interface.auto_refresh_timer.isActive():
                    self.sync_interface.auto_refresh_timer.stop()
            
            # 同步清理资源（确保进程被终止）
            logger.info("开始清理资源...")
            
            # 1. 断开TCP广播
            if hasattr(self, 'tcp_broadcast') and self.tcp_broadcast:
                try:
                    logger.info("正在关闭TCP广播...")
                    self.tcp_broadcast.disconnect()
                    self.tcp_broadcast = None
                    logger.info("TCP广播已关闭")
                except Exception as e:
                    logger.error(f"关闭TCP广播失败: {e}")
            
            # 2. 停止Syncthing（最耗时的操作）
            if hasattr(self, 'syncthing_manager') and self.syncthing_manager:
                try:
                    logger.info("正在停止Syncthing...")
                    self.syncthing_manager.stop()
                    self.syncthing_manager = None
                    logger.info("Syncthing已停止")
                except Exception as e:
                    logger.error(f"停止Syncthing失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # 再次确认清理所有Syncthing残留进程
            try:
                import psutil
                import time
                time.sleep(0.5)  # 等待一下
                
                syncthing_names = ['syncthing.exe', 'syncthing']
                remaining_count = 0
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        proc_name = proc.info.get('name', '').lower()
                        for name in syncthing_names:
                            if name.lower() in proc_name:
                                remaining_count += 1
                                logger.warning(f"发现残留Syncthing进程: {proc_name} (PID: {proc.info['pid']})，强制清理...")
                                try:
                                    proc.kill()
                                    proc.wait(timeout=1)
                                except:
                                    pass
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                    except Exception:
                        pass
                
                if remaining_count > 0:
                    logger.info(f"✅ 清理了 {remaining_count} 个残留的Syncthing进程")
            except Exception as e:
                logger.error(f"清理残留Syncthing进程失败: {e}")
            
            # 3. 断开EasyTier网络（确保完全清理）
            if hasattr(self, 'controller') and self.controller:
                if hasattr(self.controller, 'easytier') and self.controller.easytier:
                    try:
                        logger.info("正在断开EasyTier网络...")
                        self.controller.easytier.stop()
                        logger.info("EasyTier网络已断开")
                        
                        # 再次确认清理（防止残留）
                        import psutil
                        import time
                        time.sleep(1)  # 等待1秒
                        
                        remaining_count = 0
                        for proc in psutil.process_iter(['pid', 'name']):
                                    try:
                                        if proc.info['name'] and 'easytier-core' in proc.info['name'].lower():
                                            remaining_count += 1
                                            logger.warning(f"发现残留进程: {proc.info['name']} (PID: {proc.info['pid']})，强制清理...")
                                            proc.kill()
                                            proc.wait(timeout=2)
                                    except:
                                        pass
                                
                                if remaining_count > 0:
                                    logger.info(f"清理了 {remaining_count} 个残留的EasyTier进程")
                            except Exception as e:
                                logger.error(f"断开EasyTier失败: {e}")
            
            logger.info("✅ 资源清理完成")
            
            # 最后接受关闭事件，关闭窗口
            event.accept()
            
        except Exception as e:
            logger.error(f"关闭程序时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 即使出错也要强制清理进程
            try:
                import psutil
                # 强制清理所有相关进程
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        proc_name = proc.info.get('name', '').lower()
                        if 'syncthing' in proc_name or 'easytier-core' in proc_name:
                            logger.warning(f"强制清理残留进程: {proc_name} (PID: {proc.info['pid']})")
                            proc.kill()
                            proc.wait(timeout=1)
                    except:
                        pass
            except:
                pass
            
            # 确保窗口能关闭
            event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FluentMainWindow()
    window.show()
    sys.exit(app.exec_())

"""
Fluent Design 页面模块
"""
from .network_page import NetworkInterface
from .game_page import GameInterface
from .settings_page import SettingsInterface
from .sync_interface import SyncInterface

__all__ = [
    'NetworkInterface',
    'GameInterface',
    'SettingsInterface',
    'SyncInterface'
]

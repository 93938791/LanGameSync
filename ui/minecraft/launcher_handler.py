"""
Minecraft启动器文件处理器
负责检测和处理HMCL/PCL启动器文件
"""
import os
from utils.logger import Logger

logger = Logger().get_logger("MinecraftLauncher")


class MinecraftLauncherHandler:
    """Minecraft启动器处理器"""
    
    @staticmethod
    def detect_launcher_type(launcher_file):
        """
        检测启动器类型
        
        Args:
            launcher_file: 启动器文件路径
        
        Returns:
            启动器类型字符串 (HMCL/PCL/Minecraft)
        """
        launcher_name = os.path.basename(launcher_file).lower()
        
        if "hmcl" in launcher_name:
            return "HMCL"
        elif "pcl" in launcher_name or "plain craft launcher" in launcher_name:
            return "PCL"
        else:
            return "Minecraft"
    
    @staticmethod
    def find_minecraft_dir(launcher_file):
        """
        查找Minecraft目录
        
        Args:
            launcher_file: 启动器文件路径
        
        Returns:
            .minecraft目录路径，未找到返回None
        """
        launcher_dir = os.path.dirname(launcher_file)
        
        potential_dirs = [
            launcher_dir,
            os.path.join(launcher_dir, ".minecraft"),
            os.path.join(launcher_dir, "minecraft"),
        ]
        
        for potential_dir in potential_dirs:
            saves_dir = os.path.join(potential_dir, "saves")
            versions_dir = os.path.join(potential_dir, "versions")
            
            if (os.path.exists(saves_dir) and os.path.isdir(saves_dir)) or \
               (os.path.exists(versions_dir) and os.path.isdir(versions_dir)):
                logger.info(f"找到Minecraft目录: {potential_dir}")
                return potential_dir
        
        logger.warning("未找到Minecraft目录")
        return None
    
    @staticmethod
    def scan_saves(minecraft_dir):
        """
        扫描所有存档（包括版本隔离）
        
        Args:
            minecraft_dir: .minecraft目录路径
        
        Returns:
            存档列表，格式: ["存档名"] 或 ["存档名 [版本号]"]
        """
        all_saves = []
        
        # 1. 扫描标准位置
        standard_saves_dir = os.path.join(minecraft_dir, "saves")
        if os.path.exists(standard_saves_dir):
            for save_name in os.listdir(standard_saves_dir):
                save_path = os.path.join(standard_saves_dir, save_name)
                if os.path.isdir(save_path):
                    level_dat = os.path.join(save_path, "level.dat")
                    if os.path.exists(level_dat):
                        all_saves.append(save_name)
                        logger.debug(f"找到标准存档: {save_name}")
        
        # 2. 扫描版本隔离位置
        versions_dir = os.path.join(minecraft_dir, "versions")
        if os.path.exists(versions_dir):
            for version_name in os.listdir(versions_dir):
                version_path = os.path.join(versions_dir, version_name)
                if os.path.isdir(version_path):
                    version_saves_dir = os.path.join(version_path, "saves")
                    if os.path.exists(version_saves_dir):
                        for save_name in os.listdir(version_saves_dir):
                            save_path = os.path.join(version_saves_dir, save_name)
                            if os.path.isdir(save_path):
                                level_dat = os.path.join(save_path, "level.dat")
                                if os.path.exists(level_dat):
                                    display_name = f"{save_name} [{version_name}]"
                                    all_saves.append(display_name)
                                    logger.debug(f"找到版本隔离存档: {display_name}")
        
        logger.info(f"共找到 {len(all_saves)} 个存档")
        return all_saves
    
    @staticmethod
    def parse_save_info(save_display_name):
        """
        解析存档显示名称
        
        Args:
            save_display_name: 显示名称 "存档名" 或 "存档名 [版本号]"
        
        Returns:
            (save_name, version, is_version_isolated)
        """
        import re
        match = re.match(r"(.+?) \[(.+?)\]$", save_display_name)
        
        if match:
            # 版本隔离存档
            return match.group(1), match.group(2), True
        else:
            # 标准存档
            return save_display_name, "通用", False

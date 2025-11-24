"""
Minecraft路径解析器
负责智能解析和映射Minecraft存档路径
"""
import os
import re
from utils.logger import Logger

logger = Logger().get_logger("MinecraftPathResolver")


class MinecraftPathResolver:
    """Minecraft路径解析器"""
    
    @staticmethod
    def resolve_save_path(config_data, relative_path, sync_type="save", save_name=None):
        """
        根据相对路径计算本地存档绝对路径
        支持智能映射：
        - 如果本地有对应版本 -> 使用版本隔离路径
        - 如果本地没有对应版本 -> 使用标准路径
        
        Args:
            config_data: 配置数据
            relative_path: 相对于 .minecraft 的路径
            sync_type: 同步类型 (save/version)
            save_name: 存档名称
        
        Returns:
            本地绝对路径
        """
        minecraft_config = config_data.get("minecraft_config", {})
        minecraft_dir = minecraft_config.get("minecraft_dir")
        
        if not minecraft_dir:
            return None
        
        # 新逻辑：处理版本目录同步 (sync_type == "version")
        if sync_type == "version":
            match = re.match(r"versions/(.+)", relative_path)
            if match:
                version = match.group(1)
                version_dir = os.path.join(minecraft_dir, "versions", version)
                
                if os.path.exists(version_dir):
                    logger.info(f"本地已有版本 {version}，使用现有版本目录")
                    return version_dir
                else:
                    logger.info(f"本地没有版本 {version}，将创建并接收完整版本文件")
                    if not os.path.exists(version_dir):
                        os.makedirs(version_dir)
                    return version_dir
        
        # 旧逻辑：处理单独存档同步
        match = re.match(r"versions/([^/]+)/saves/(.+)", relative_path)
        if match:
            version = match.group(1)
            save = match.group(2)
            
            version_save_path = os.path.join(minecraft_dir, "versions", version, "saves", save)
            standard_save_path = os.path.join(minecraft_dir, "saves", save)
            
            if os.path.exists(version_save_path):
                logger.info(f"使用版本隔离路径: {version_save_path}")
                return version_save_path
            elif os.path.exists(standard_save_path):
                logger.info(f"使用标准存档路径: {standard_save_path}")
                return standard_save_path
            else:
                version_dir = os.path.join(minecraft_dir, "versions", version)
                if os.path.exists(version_dir):
                    logger.info(f"创建版本隔离存档路径: {version_save_path}")
                    return version_save_path
                else:
                    logger.info(f"创建标准存档路径: {standard_save_path}")
                    return standard_save_path
        
        match = re.match(r"saves/(.+)", relative_path)
        if match:
            save = match.group(1)
            return os.path.join(minecraft_dir, "saves", save)
        
        return None
    
    @staticmethod
    def update_minecraft_paths(config_data):
        """
        更新所有 Minecraft 存档的本地路径
        根据 relative_path 重新计算 path
        """
        from utils.config_cache import ConfigCache
        
        game_list = config_data.get("game_list", [])
        updated = False
        
        for game in game_list:
            if game.get("type") == "minecraft" and game.get("relative_path"):
                sync_type = game.get("sync_type", "save")
                save_name = game.get("save_name")
                
                new_path = MinecraftPathResolver.resolve_save_path(
                    config_data,
                    game["relative_path"],
                    sync_type=sync_type,
                    save_name=save_name
                )
                
                if new_path and new_path != game.get("path"):
                    old_path = game.get("path")
                    game["path"] = new_path
                    updated = True
                    logger.info(f"更新 Minecraft 路径: {old_path} -> {new_path}")
        
        if updated:
            ConfigCache.save(config_data)
            logger.info("已更新 Minecraft 路径")
        
        return updated

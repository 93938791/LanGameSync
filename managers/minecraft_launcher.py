"""
Minecraft原生启动器
直接构造启动参数,绕过HMCL/PCL2
"""
import json
import os
import subprocess
from pathlib import Path
from utils.logger import Logger

logger = Logger().get_logger("MinecraftLauncher")


class MinecraftLauncher:
    """Minecraft原生启动器"""
    
    def __init__(self, minecraft_dir, version):
        """
        Args:
            minecraft_dir: .minecraft目录
            version: 游戏版本
        """
        self.minecraft_dir = Path(minecraft_dir)
        self.version = version
        self.version_dir = self.minecraft_dir / 'versions' / version
        self.version_json_path = self.version_dir / f'{version}.json'
        
    def launch(self, username="Player", java_path=None):
        """
        启动Minecraft
        
        Args:
            username: 玩家名(离线模式)
            java_path: Java路径,None则自动查找
        
        Returns:
            subprocess.Popen: 游戏进程
        """
        try:
            # 1. 读取版本json
            with open(self.version_json_path, 'r', encoding='utf-8') as f:
                version_data = json.load(f)
            
            logger.info(f"读取版本配置: {self.version}")
            
            # 2. 构造启动参数
            cmd = self._build_launch_command(version_data, username, java_path)
            
            logger.info(f"启动Minecraft: {self.version}")
            logger.info(f"完整启动命令: {' '.join(cmd)}")
            
            # 3. 保存命令到文件供调试
            cmd_file = Path('launch_command.txt')
            with open(cmd_file, 'w', encoding='utf-8') as f:
                f.write(' '.join(cmd))
            logger.info(f"启动命令已保存到: {cmd_file.absolute()}")
            
            # 4. 启动游戏
            process = subprocess.Popen(
                cmd,
                cwd=str(self.minecraft_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return process
            
        except Exception as e:
            logger.error(f"启动失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _build_launch_command(self, version_data, username, java_path):
        """构造启动命令"""
        try:
            # Java路径
            if not java_path:
                java_path = self._find_java()
            
            logger.info(f"使用Java: {java_path}")
            cmd = [java_path]
            
            # JVM参数
            jvm_args = [
                f'-Xmx2G',  # 最大内存
                f'-Xms512M',  # 最小内存
                f'-Djava.library.path={self.version_dir / "natives"}',
                f'-cp',
                self._get_classpath(version_data)
            ]
            cmd.extend(jvm_args)
            logger.info(f"添加JVM参数: {len(jvm_args)}个")
            
            # 主类
            main_class = version_data.get('mainClass', 'net.minecraft.client.main.Main')
            cmd.append(main_class)
            logger.info(f"主类: {main_class}")
            
            # 游戏参数
            game_args = self._get_game_arguments(version_data, username)
            cmd.extend(game_args)
            logger.info(f"添加游戏参数: {len(game_args)}个")
            
            return cmd
        except Exception as e:
            logger.error(f"构造启动命令失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _get_classpath(self, version_data):
        """获取classpath"""
        libraries = []
        
        # 添加libraries
        for lib in version_data.get('libraries', []):
            lib_path = self._get_library_path(lib)
            if lib_path and lib_path.exists():
                libraries.append(str(lib_path))
        
        # 添加游戏jar
        game_jar = self.version_dir / f'{self.version}.jar'
        libraries.append(str(game_jar))
        
        return ';'.join(libraries)  # Windows用;
    
    def _get_library_path(self, lib):
        """获取library路径"""
        try:
            name = lib.get('name', '')
            # 格式: group:artifact:version
            parts = name.split(':')
            if len(parts) != 3:
                return None
            
            group, artifact, version = parts
            group_path = group.replace('.', '/')
            
            lib_path = self.minecraft_dir / 'libraries' / group_path / artifact / version / f'{artifact}-{version}.jar'
            return lib_path
        except:
            return None
    
    def _get_game_arguments(self, version_data, username):
        """获取游戏参数"""
        args = []
        
        # 新版本格式
        if 'arguments' in version_data:
            game_arguments = version_data['arguments'].get('game', [])
            for arg in game_arguments:
                if isinstance(arg, str):
                    args.append(self._replace_variables(arg, username))
        # 旧版本格式
        elif 'minecraftArguments' in version_data:
            old_args = version_data['minecraftArguments'].split()
            for arg in old_args:
                args.append(self._replace_variables(arg, username))
        
        return args
    
    def _replace_variables(self, arg, username):
        """替换变量"""
        replacements = {
            '${auth_player_name}': username,
            '${version_name}': self.version,
            '${game_directory}': str(self.minecraft_dir),
            '${assets_root}': str(self.minecraft_dir / 'assets'),
            '${assets_index_name}': self.version,
            '${auth_uuid}': '00000000-0000-0000-0000-000000000000',
            '${auth_access_token}': 'null',
            '${user_type}': 'legacy',
            '${version_type}': 'release',
        }
        
        for key, value in replacements.items():
            arg = arg.replace(key, value)
        
        return arg
    
    def _find_java(self):
        """查找Java"""
        # 简单返回java命令,系统会自动查找PATH
        return 'java'

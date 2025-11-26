"""
游戏启动管理器
负责直接启动Minecraft游戏（不依赖启动器）
"""
import os
import time
import json
import subprocess
import re
from pathlib import Path
from utils.logger import Logger

logger = Logger().get_logger("GameLauncher")

try:
    import win32gui
    import win32con
    import win32api
    import win32process
    WIN32_AVAILABLE = True
except ImportError:
    logger.warning("pywin32未安装,自动开局域网功能不可用")
    WIN32_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    logger.warning("pyautogui未安装,自动点击功能不可用")
    PYAUTOGUI_AVAILABLE = False


class GameLauncher:
    """游戏启动器 - 直接构建 Java 启动命令"""
    
    def __init__(self, minecraft_dir=None, version=None):
        """
        初始化游戏启动器
        
        Args:
            minecraft_dir: .minecraft 根目录
            version: 游戏版本
        """
        self.minecraft_dir = Path(minecraft_dir) if minecraft_dir else None
        self.version = version
        self.version_dir = None
        self.game_dir = None  # 版本隔离目录
        
        if self.minecraft_dir and self.version:
            self.version_dir = self.minecraft_dir / "versions" / self.version
            self.game_dir = self.version_dir  # 版本隔离
        
        self.game_process = None
        self.game_hwnd = None
        self.lan_port = None
        
    def join_server(self, server_ip, server_port, player_name=None, launcher_path=None):
        """
        加入服务器（专用于加入游戏）
        
        Args:
            server_ip: 服务器IP
            server_port: 服务器端口
            player_name: 玩家名称
            launcher_path: 启动器路径
            
        Returns:
            bool: 是否成功启动
        """
        try:
            if not self.minecraft_dir or not self.version:
                logger.error("未设置 Minecraft 目录或版本")
                return False
            
            # 从启动器读取账号信息
            use_offline = True
            mojang_uuid = None
            mojang_token = None
            account_type = 'offline'
            
            if launcher_path:
                logger.info(f"尝试从启动器读取账号信息: {launcher_path}")
                account_info = self._read_launcher_account(launcher_path)
                
                if account_info:
                    if player_name is None:
                        player_name = account_info.get('player_name', 'Player')
                    mojang_uuid = account_info.get('uuid')
                    mojang_token = account_info.get('access_token')
                    account_type = account_info.get('account_type', 'offline')
                    use_offline = (account_type == 'offline')
                    logger.info(f"从启动器读取到账号: {player_name} (类型: {account_type})")
            
            if player_name is None:
                player_name = 'Player'
            
            # 读取版本 JSON
            version_json = self._read_version_json()
            if not version_json:
                return False
            
            # 构建加入服务器的命令
            cmd = self._build_join_server_command(version_json, player_name, use_offline, mojang_uuid, mojang_token, account_type, server_ip, server_port)
            if not cmd:
                return False
            
            logger.info(f"游戏目录: {self.game_dir}")
            logger.info(f"主类: {version_json.get('mainClass')}")
            logger.info(f"加入服务器: {server_ip}:{server_port}")
            logger.info(f"===== 完整启动命令 =====")
            logger.info(f"{' '.join(cmd)}")
            logger.info(f"=======================")
            
            # 创建游戏日志文件
            game_log_dir = self.game_dir / 'logs'
            game_log_dir.mkdir(parents=True, exist_ok=True)
            game_output_log = game_log_dir / 'game_output.log'
            
            # 启动进程
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            with open(game_output_log, 'w', encoding='utf-8') as log_file:
                self.game_process = subprocess.Popen(
                    cmd,
                    cwd=str(self.game_dir),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            
            logger.info(f"游戏进程已启动，PID: {self.game_process.pid}")
            logger.info(f"游戏输出日志: {game_output_log}")
            
            # 检查进程是否立即退出
            time.sleep(2)
            if self.game_process.poll() is not None:
                logger.error(f"游戏进程立即退出，退出码: {self.game_process.returncode}")
                logger.error("请检查游戏日志文件获取详细错误信息")
                return False
            
            logger.info("游戏进程正常运行")
            return True
            
        except Exception as e:
            logger.error(f"加入服务器失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _build_join_server_command(self, version_data, player_name, use_offline, mojang_uuid, mojang_token, account_type, server_ip, server_port):
        """构建加入服务器的命令"""
        try:
            # 1. 获取库文件
            libraries = self._get_libraries(version_data)
            if not libraries:
                logger.error("没有找到库文件")
                return None
            
            # 2. 构建 classpath
            classpath = ';'.join(libraries)
            
            # 3. 获取主类
            main_class = version_data.get('mainClass', 'net.minecraft.client.main.Main')
            
            # 4. 获取游戏参数
            game_args = self._get_game_arguments(version_data)
            game_args = [self._replace_variables(arg, player_name, use_offline, mojang_uuid, mojang_token, version_data, account_type) for arg in game_args]
            
            # 5. 找到 natives 目录
            natives_dir = self.version_dir / "natives-windows-x86_64"
            if not natives_dir.exists():
                for possible_name in ["natives", f"{self.version}-natives"]:
                    possible_dir = self.version_dir / possible_name
                    if possible_dir.exists():
                        natives_dir = possible_dir
                        break
            
            logger.info(f"Native 库目录: {natives_dir}")
            
            # 6. 构建完整命令
            cmd = [
                'java',
                '-Xmx2G',
                '-Xms512M',
                '-XX:+UnlockExperimentalVMOptions',
                '-XX:+UseG1GC',
                '-XX:G1NewSizePercent=20',
                '-XX:G1ReservePercent=20',
                '-XX:MaxGCPauseMillis=50',
                '-XX:G1HeapRegionSize=32M',
                f'-Djava.library.path={natives_dir}',
                f'-Djna.tmpdir={natives_dir}',
                f'-Dorg.lwjgl.system.SharedLibraryExtractPath={natives_dir}',
                f'-Dio.netty.native.workdir={natives_dir}',
                '-Dminecraft.launcher.brand=java-minecraft-launcher',
                '-Dminecraft.launcher.version=1.6.91',
                '-cp',
                classpath,
                main_class,
            ]
            cmd.extend(game_args)
            
            # 7. 添加服务器连接参数（1.20+ 版本使用 quickPlayMultiplayer）
            version_parts = self.version.split('.')
            try:
                major_version = int(version_parts[1]) if len(version_parts) > 1 else 0
                
                if major_version >= 20:
                    # 1.20+ 版本使用 --quickPlayMultiplayer
                    cmd.append('--quickPlayMultiplayer')
                    cmd.append(f"{server_ip}:{server_port}")
                    logger.info(f"添加服务器连接参数: --quickPlayMultiplayer {server_ip}:{server_port}")
                else:
                    # 旧版本使用 --server 和 --port
                    cmd.append('--server')
                    cmd.append(server_ip)
                    cmd.append('--port')
                    cmd.append(str(server_port))
                    logger.info(f"添加服务器连接参数: --server {server_ip} --port {server_port}")
            except (ValueError, IndexError):
                # 解析版本号失败，使用默认方式
                cmd.append('--server')
                cmd.append(server_ip)
                cmd.append('--port')
                cmd.append(str(server_port))
                logger.warning(f"无法解析版本号: {self.version}，使用 --server/--port 参数")
            
            # 8. 添加窗口化参数（去掉全屏）
            cmd.append('--width')
            cmd.append('1280')
            cmd.append('--height')
            cmd.append('720')
            logger.info(f"添加服务器连接参数: --server {server_ip} --port {server_port} （窗口模式 1280x720）")
            
            return cmd
            
        except Exception as e:
            logger.error(f"构建加入服务器命令失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def launch_minecraft(self, player_name=None, use_offline=None, mojang_uuid=None, mojang_token=None, launcher_path=None, world_name=None, server_ip=None, server_port=None):
        """
        直接启动Minecraft（不依赖启动器）
        
        Args:
            player_name: 玩家名称（如果为None，则从启动器读取）
            use_offline: 是否使用离线模式（如果为None，则从启动器读取）
            mojang_uuid: 正版UUID（如果为None，则从启动器读取）
            mojang_token: 正版token（如果为None，则从启动器读取）
            launcher_path: 启动器路径（用于读取账号信息）
            world_name: 世界名称（自动进入指定世界）
            server_ip: 服务器IP（自动连接服务器）
            server_port: 服务器端口（自动连接服务器）
            
        Returns:
            bool: 是否成功启动
        """
        try:
            if not self.minecraft_dir or not self.version:
                logger.error("未设置 Minecraft 目录或版本")
                return False
            
            # 如果指定了世界名称，确保该世界允许使用指令
            if world_name:
                self._ensure_world_commands_enabled(world_name)
                # 修正玩家UUID（避免使用上个房主的玩家数据）
                if mojang_uuid:
                    self._fix_player_uuid(world_name, player_name, mojang_uuid)
            
            # 如果提供了启动器路径，尝试从启动器读取账号信息
            if launcher_path and (player_name is None or use_offline is None):
                logger.info(f"尝试从启动器读取账号信息: {launcher_path}")
                account_info = self._read_launcher_account(launcher_path)
                
                if account_info:
                    if player_name is None:
                        player_name = account_info.get('player_name', 'Player')
                    if mojang_uuid is None:
                        mojang_uuid = account_info.get('uuid')
                    if mojang_token is None:
                        mojang_token = account_info.get('access_token')
                    
                    # 根据账号类型判断是否离线模式
                    if use_offline is None:
                        account_type = account_info.get('account_type', 'offline')
                        use_offline = (account_type == 'offline')
                    else:
                        account_type = 'offline' if use_offline else account_info.get('account_type', 'microsoft')
                    
                    logger.info(f"从启动器读取到账号: {player_name} (类型: {account_type})")
                else:
                    logger.warning("未能从启动器读取账号信息，使用默认值")
            
            # 设置默认值
            if player_name is None:
                player_name = 'Player'
            if use_offline is None:
                use_offline = True
                account_type = 'offline'
            else:
                # 如果没有从Launcher读取，设置默认account_type
                if 'account_type' not in locals():
                    account_type = 'offline' if use_offline else 'microsoft'
            
            # 读取版本 JSON
            version_json = self._read_version_json()
            if not version_json:
                return False
            
            # 构建启动命令
            cmd = self._build_launch_command(version_json, player_name, use_offline, mojang_uuid, mojang_token, account_type, world_name, server_ip, server_port)
            if not cmd:
                return False
            
            logger.info(f"游戏目录: {self.game_dir}")
            logger.info(f"主类: {version_json.get('mainClass')}")
            logger.info(f"启动游戏...")
            logger.debug(f"启动命令: {' '.join(cmd)}")
            
            # 创建游戏日志文件
            game_log_dir = self.game_dir / 'logs'
            game_log_dir.mkdir(parents=True, exist_ok=True)
            game_output_log = game_log_dir / 'game_output.log'
            
            # 启动进程（将输出重定向到日志文件，隐藏控制台窗口）
            startupinfo = None
            if os.name == 'nt':  # Windows系统
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            with open(game_output_log, 'w', encoding='utf-8') as log_file:
                self.game_process = subprocess.Popen(
                    cmd,
                    cwd=str(self.game_dir),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,  # 错误也输出到同一文件
                    startupinfo=startupinfo,  # 隐藏控制台窗口
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            
            logger.info(f"游戏进程已启动，PID: {self.game_process.pid}")
            logger.info(f"游戏输出日志: {game_output_log}")
            
            # 等待一下检查进程是否立即退出
            import time
            time.sleep(2)
            if self.game_process.poll() is not None:
                # 进程已退出
                logger.error(f"游戏进程立即退出，退出码: {self.game_process.returncode}")
                logger.error("请检查游戏日志文件获取详细错误信息")
                return False
            
            logger.info("游戏进程正常运行")
            return True
            
        except Exception as e:
            logger.error(f"启动Minecraft失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _ensure_world_commands_enabled(self, world_name):
        """
        确保指定世界允许使用指令（修改level.dat）
        
        Args:
            world_name: 世界名称
        """
        try:
            import nbtlib
            from pathlib import Path
            
            # 构建世界路径（版本隔离：game_dir已经是版本目录）
            world_path = self.game_dir / 'saves' / world_name
            level_dat = world_path / 'level.dat'
            
            logger.info(f"检查世界设置: {world_path}")
            
            if not level_dat.exists():
                logger.warning(f"世界不存在: {level_dat}")
                return
            
            logger.info(f"读取level.dat: {level_dat}")
            # 读取level.dat
            nbt_file = nbtlib.load(str(level_dat))
            
            # 检查是否已经允许指令
            data = nbt_file.get('Data', nbt_file.get('', {}))
            allow_commands = data.get('allowCommands', nbtlib.Byte(0))
            
            logger.info(f"当前allowCommands值: {allow_commands}")
            
            if allow_commands == nbtlib.Byte(1) or allow_commands == 1:
                logger.info(f"世界 '{world_name}' 已允许使用指令")
                return
            
            # 修改为允许指令
            logger.info("开始修改allowCommands...")
            data['allowCommands'] = nbtlib.Byte(1)
            
            # 保存level.dat
            nbt_file.save(str(level_dat))
            logger.info(f"✅ 已为世界 '{world_name}' 开启指令支持")
            
        except ImportError:
            logger.error("未安装nbtlib库，无法修改世界设置")
            logger.error("请运行: pip install nbtlib")
        except Exception as e:
            logger.error(f"修改世界设置失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _fix_player_uuid(self, world_name, player_name, new_uuid):
        """
        修正level.dat中的玩家UUID（确保使用当前玩家的数据）
        
        Args:
            world_name: 世界名称
            player_name: 玩家名称
            new_uuid: 新的UUID（带横线格式）
        """
        try:
            import nbtlib
            import shutil
            from pathlib import Path
            
            # 构建世界路径
            world_path = self.game_dir / 'saves' / world_name
            level_dat = world_path / 'level.dat'
            
            if not level_dat.exists():
                logger.warning(f"level.dat不存在: {level_dat}")
                return
            
            logger.info(f"修正level.dat中的玩家UUID: {level_dat}")
            
            # 备份level.dat（创建.bak备份）
            backup_file = world_path / 'level.dat_old'
            try:
                if level_dat.exists():
                    shutil.copy2(level_dat, backup_file)
                    logger.info(f"已备份level.dat到: {backup_file}")
            except Exception as e:
                logger.warning(f"备份失败: {e}")
            
            # 读取level.dat
            nbt_file = nbtlib.load(str(level_dat))
            data = nbt_file.get('Data', nbt_file.get('', {}))
            
            # 获取Player数据
            if 'Player' not in data:
                logger.info("level.dat中没有Player数据，无需修正")
                return
            
            player_data = data['Player']
            
            # 检查当前UUID
            old_uuid = player_data.get('UUID', None)
            logger.info(f"当前UUID: {old_uuid}")
            
            # 将新UUID转为整数数组格式（Minecraft NBT格式）
            uuid_parts = new_uuid.replace('-', '')
            
            # UUID格式检查
            if len(uuid_parts) != 32:
                logger.error(f"UUID格式错误，长度应为32: {uuid_parts}")
                return
            
            # 转为4个int值（每8位十六进制=32位）
            try:
                uuid_ints = [
                    int(uuid_parts[0:8], 16),
                    int(uuid_parts[8:16], 16),
                    int(uuid_parts[16:24], 16),
                    int(uuid_parts[24:32], 16)
                ]
            except Exception as e:
                logger.error(f"UUID格式错误: {new_uuid}, {e}")
                return
            
            # 转为有符号32位整数
            def to_signed_int32(n):
                if n > 0x7FFFFFFF:
                    return n - 0x100000000
                return n
            
            uuid_ints = [to_signed_int32(i) for i in uuid_ints]
            
            # 更新UUID
            player_data['UUID'] = nbtlib.IntArray(uuid_ints)
            
            logger.info(f"新UUID: {new_uuid} -> {uuid_ints}")
            
            # 直接保存（与_ensure_world_commands_enabled一致的方式）
            try:
                nbt_file.save(str(level_dat))
                logger.info(f"✅ 已修正level.dat中的玩家UUID: {player_name} -> {new_uuid}")
            except Exception as e:
                logger.error(f"保存level.dat失败: {e}")
                # 尝试恢复备份
                if backup_file.exists():
                    try:
                        shutil.copy2(backup_file, level_dat)
                        logger.info("已从备份恢复level.dat")
                    except Exception as restore_e:
                        logger.error(f"恢复备份失败: {restore_e}")
                raise
            
        except ImportError:
            logger.error("未安装nbtlib库，无法修改玩家UUID")
            logger.error("请运行: pip install nbtlib")
        except Exception as e:
            logger.error(f"修正玩家UUID失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _read_launcher_account(self, launcher_path):
        """
        从启动器读取账号信息
        
        Args:
            launcher_path: 启动器路径
            
        Returns:
            账号信息字典或None
        """
        try:
            from managers.launcher_account_reader import LauncherAccountReader
            
            reader = LauncherAccountReader(launcher_path)
            account_info = reader.get_account_info()
            
            if account_info and account_info.get('is_valid'):
                return account_info
            else:
                logger.warning("启动器中的账号信息无效或不存在")
                return None
                
        except ImportError:
            logger.error("未找到LauncherAccountReader模块")
            return None
        except Exception as e:
            logger.error(f"读取启动器账号失败: {e}")
            return None
    
    def _read_version_json(self):
        """读取版本 JSON 文件"""
        try:
            json_path = self.version_dir / f"{self.version}.json"
            logger.info(f"读取版本 JSON: {json_path}")
            
            if not json_path.exists():
                logger.error(f"版本 JSON 不存在: {json_path}")
                return None
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"主类: {data.get('mainClass')}")
            logger.info(f"资源索引: {data.get('assetIndex', {}).get('id')}")
            return data
            
        except Exception as e:
            logger.error(f"读取版本 JSON 失败: {e}")
            return None
    
    def _get_libraries(self, version_data):
        """获取所有库文件路径"""
        libraries = []
        libraries_dir = self.minecraft_dir / "libraries"
        added_artifacts = set()  # 记录已添加的 artifact，避免重复
        
        for lib in version_data.get('libraries', []):
            # 检查规则
            rules = lib.get('rules', [])
            if rules:
                allowed = True
                for rule in rules:
                    if rule.get('action') == 'disallow':
                        allowed = False
                        break
                if not allowed:
                    continue
            
            # 解析 name
            name = lib.get('name', '')
            if not name:
                continue
            
            # 格式: group:artifact:version
            parts = name.split(':')
            if len(parts) < 3:
                continue
            
            group, artifact, version = parts[0], parts[1], parts[2]
            
            # 检查是否重复
            if artifact in added_artifacts:
                logger.debug(f"跳过重复库: {artifact}-{version}.jar")
                continue
            
            added_artifacts.add(artifact)
            
            # 构造路径
            group_path = group.replace('.', '/')
            jar_name = f"{artifact}-{version}.jar"
            lib_path = libraries_dir / group_path / artifact / version / jar_name
            
            if lib_path.exists():
                libraries.append(str(lib_path))
            else:
                logger.debug(f"缺失库文件: {jar_name}")
        
        # 添加游戏主 jar
        game_jar = self.version_dir / f"{self.version}.jar"
        if game_jar.exists():
            libraries.append(str(game_jar))
        
        logger.info(f"共找到 {len(libraries)} 个库文件")
        return libraries
    
    def _get_game_arguments(self, version_data):
        """获取游戏参数"""
        args = []
        
        # 新版格式
        if 'arguments' in version_data:
            game_args = version_data['arguments'].get('game', [])
            for arg in game_args:
                if isinstance(arg, str):
                    args.append(arg)
                # dict 类型是条件参数，暂时跳过
        # 旧版格式
        elif 'minecraftArguments' in version_data:
            args = version_data['minecraftArguments'].split()
        
        logger.info(f"共 {len(args)} 个游戏参数")
        return args
    
    def _replace_variables(self, arg, player_name, use_offline, mojang_uuid, mojang_token, version_data, account_type='offline'):
        """替换参数中的变量"""
        asset_index = version_data.get('assetIndex', {}).get('id', '19')
        
        # 根据模式设置登录信息
        if use_offline:
            uuid = '00000000-0000-0000-0000-000000000000'
            access_token = 'null'
            user_type = 'legacy'
        else:
            uuid = mojang_uuid or '00000000-0000-0000-0000-000000000000'
            access_token = mojang_token or 'null'
            # 根据账号类型设置user_type
            if account_type == 'microsoft':
                user_type = 'msa'  # Microsoft账号
            elif account_type == 'mojang':
                user_type = 'mojang'  # Mojang账号
            else:
                user_type = 'mojang'  # 默认
        
        replacements = {
            '${auth_player_name}': player_name,
            '${version_name}': self.version,
            '${game_directory}': str(self.game_dir),
            '${assets_root}': str(self.minecraft_dir / 'assets'),
            '${assets_index_name}': str(asset_index),
            '${auth_uuid}': uuid,
            '${auth_access_token}': access_token,
            '${user_type}': user_type,
            '${version_type}': 'release',
            '${user_properties}': '{}',
            '${clientid}': '',
            '${auth_xuid}': '',
        }
        
        for key, value in replacements.items():
            arg = arg.replace(key, value)
        
        return arg
    
    def _build_launch_command(self, version_data, player_name, use_offline, mojang_uuid, mojang_token, account_type='offline', world_name=None, server_ip=None, server_port=None):
        """构建完整的启动命令"""
        try:
            # 1. 获取库文件
            libraries = self._get_libraries(version_data)
            if not libraries:
                logger.error("没有找到库文件")
                return None
            
            # 2. 构建 classpath
            classpath = ';'.join(libraries)
            
            # 3. 获取主类
            main_class = version_data.get('mainClass', 'net.minecraft.client.main.Main')
            
            # 4. 获取游戏参数
            game_args = self._get_game_arguments(version_data)
            game_args = [self._replace_variables(arg, player_name, use_offline, mojang_uuid, mojang_token, version_data, account_type) for arg in game_args]
            
            # 5. 找到 natives 目录
            natives_dir = self.version_dir / "natives-windows-x86_64"
            if not natives_dir.exists():
                for possible_name in ["natives", f"{self.version}-natives"]:
                    possible_dir = self.version_dir / possible_name
                    if possible_dir.exists():
                        natives_dir = possible_dir
                        break
            
            logger.info(f"Native 库目录: {natives_dir}")
            
            # 6. 构建完整命令
            cmd = [
                'java',
                '-Xmx2G',
                '-Xms512M',
                '-XX:+UnlockExperimentalVMOptions',
                '-XX:+UseG1GC',
                '-XX:G1NewSizePercent=20',
                '-XX:G1ReservePercent=20',
                '-XX:MaxGCPauseMillis=50',
                '-XX:G1HeapRegionSize=32M',
                f'-Djava.library.path={natives_dir}',
                f'-Djna.tmpdir={natives_dir}',  # 添加jna临时目录
                f'-Dorg.lwjgl.system.SharedLibraryExtractPath={natives_dir}',  # LWJGL库提取路径
                f'-Dio.netty.native.workdir={natives_dir}',  # Netty原生库工作目录
                '-Dminecraft.launcher.brand=java-minecraft-launcher',
                '-Dminecraft.launcher.version=1.6.91',
                '-cp',
                classpath,
                main_class,
            ]
            cmd.extend(game_args)
            
            # 7. 添加自动连接服务器参数（优先级最高）
            if server_ip and server_port:
                cmd.append('--server')
                cmd.append(server_ip)
                cmd.append('--port')
                cmd.append(str(server_port))
                logger.info(f"添加自动连接服务器: {server_ip}:{server_port}")
            # 8. 添加自动进入世界参数（仅当未指定服务器时）
            elif world_name:
                # 检查是否支持 quickPlay 参数
                version_parts = self.version.split('.')
                try:
                    major_version = int(version_parts[1]) if len(version_parts) > 1 else 0
                    
                    # 1.20+ 版本支持 --quickPlaySingleplayer
                    if major_version >= 20:
                        cmd.append('--quickPlaySingleplayer')
                        cmd.append(world_name)
                        logger.info(f"添加自动进入世界 (quickPlay): {world_name}")
                    else:
                        # 旧版本使用 lastServer 方式（修改 servers.dat）
                        self._set_last_server(world_name)
                        logger.info(f"设置上次游玩世界: {world_name}")
                except (ValueError, IndexError):
                    logger.warning(f"无法解析版本号: {self.version}，跳过自动加载世界")
            
            return cmd
            
        except Exception as e:
            logger.error(f"构建启动命令失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _set_last_server(self, world_name):
        """
        设置上次游玩的世界（旧版本兼容方案）
        通过修改 servers.dat 或 options.txt 来实现
        
        Args:
            world_name: 世界名称
        """
        try:
            # 尝试修改 options.txt 中的 lastServer 设置
            options_file = self.game_dir / 'options.txt'
            
            if not options_file.exists():
                # 如果没有 options.txt，创建一个简单的
                with open(options_file, 'w', encoding='utf-8') as f:
                    f.write(f"lastServer:\n")
                logger.info(f"创建 options.txt: {options_file}")
                return
            
            # 读取现有配置
            with open(options_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 查找并更新 lastServer
            found = False
            for i, line in enumerate(lines):
                if line.startswith('lastServer:'):
                    lines[i] = f'lastServer:\n'
                    found = True
                    break
            
            # 如果没找到，添加到文件末尾
            if not found:
                lines.append(f'lastServer:\n')
            
            # 写回文件
            with open(options_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            logger.info(f"已更新 options.txt 中的 lastServer 设置")
            
            # 注意：旧版本 MC 的自动加载可能需要其他方式
            # 这里只是一个基本实现，可能不能完全解决问题
            logger.warning("注意：旧版本 Minecraft 可能无法自动加载世界，需要手动选择")
            
        except Exception as e:
            logger.error(f"设置 lastServer 失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def wait_for_game_window(self, timeout=60):
        """
        通过进程PID查找游戏窗口
        
        Args:
            timeout: 超时时间(秒)
            
        Returns:
            bool: 是否找到窗口
        """
        if not WIN32_AVAILABLE:
            logger.warning("pywin32不可用,跳过窗口检测")
            return True
        
        if not self.game_process:
            logger.error("游戏进程不存在")
            return False
        
        start_time = time.time()
        pid = self.game_process.pid
        logger.info(f"开始查找进程PID {pid} 的窗口...")
        
        while time.time() - start_time < timeout:
            try:
                # 通过PID查找窗口（包括子进程）
                def enum_callback(hwnd, results):
                    if not win32gui.IsWindowVisible(hwnd):
                        return
                    try:
                        _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                        title = win32gui.GetWindowText(hwnd)
                        
                        # 方法1: 匹配PID
                        if window_pid == pid:
                            logger.info(f"[调试] 找到该PID的窗口: hwnd={hwnd}, title='{title}'")
                            results.append((hwnd, title if title else '<无标题>', 'pid'))
                        # 方法2: 匹配Minecraft窗口标题（处理Java子进程情况）
                        elif title and 'minecraft' in title.lower():
                            logger.info(f"[调试] 找到Minecraft窗口: hwnd={hwnd}, pid={window_pid}, title='{title}'")
                            results.append((hwnd, title, 'title'))
                    except Exception as e:
                        logger.debug(f"枚举窗口出错: {e}")
                
                results = []
                win32gui.EnumWindows(enum_callback, results)
                
                logger.info(f"[调试] 共找到 {len(results)} 个匹配的窗口")
                
                if results:
                    # 优先选择有Minecraft标题的窗口（子进程）
                    minecraft_windows = [r for r in results if r[2] == 'title']
                    if minecraft_windows:
                        self.game_hwnd = minecraft_windows[0][0]
                        logger.info(f"✅ 通过标题找到游戏窗口: {minecraft_windows[0][1]} (句柄: {self.game_hwnd})")
                    else:
                        # 其次选择PID匹配的窗口
                        self.game_hwnd = results[0][0]
                        logger.info(f"✅ 通过PID找到游戏窗口: {results[0][1]} (句柄: {self.game_hwnd})")
                    return True
                
                # 每5秒输出一次等待状态
                elapsed = time.time() - start_time
                if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                    logger.info(f"仍在等待游戏窗口... ({int(elapsed)}秒/{timeout}秒)")
                    
            except Exception as e:
                logger.debug(f"查找窗口时出错: {e}")
            
            time.sleep(1)
        
        logger.warning("等待游戏窗口超时")
        return False
    
    def wait_for_world_loaded(self, timeout=60):
        """
        监听游戏日志，等待进入世界
        
        Args:
            timeout: 超时时间(秒)
            
        Returns:
            bool: 是否检测到进入世界
        """
        try:
            log_file = self.game_dir / 'logs' / 'latest.log'
            
            if not log_file.exists():
                logger.error(f"日志文件不存在: {log_file}")
                return False
            
            start_time = time.time()
            last_size = 0
            
            logger.info("开始监听游戏日志，等待进入世界...")
            
            while time.time() - start_time < timeout:
                try:
                    current_size = log_file.stat().st_size
                    
                    if current_size > last_size:
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            f.seek(last_size)
                            new_content = f.read()
                            
                            # 检测进入世界的标志
                            # 日志样例: [Render thread/INFO]: Loaded 0 advancements
                            # 或: [Render thread/INFO]: Started 0 msec ago
                            if 'Loaded' in new_content and 'advancements' in new_content:
                                logger.info("✅ 检测到进入世界！")
                                return True
                            
                            # 也可以检测: Joining singleplayer world
                            if 'Joining' in new_content and 'world' in new_content:
                                logger.info("✅ 检测到进入世界！")
                                return True
                        
                        last_size = current_size
                
                except Exception as e:
                    logger.debug(f"读取日志失败: {e}")
                
                time.sleep(0.5)
            
            logger.warning("等待进入世界超时")
            return False
            
        except Exception as e:
            logger.error(f"监听游戏日志失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def auto_open_lan(self):
        """
        自动开启局域网（使用/publish指令）
        持续执行直到日志中出现成功标志
        
        Returns:
            bool: 是否成功
        """
        if not WIN32_AVAILABLE or not self.game_hwnd:
            logger.error(f"无法自动开启局域网: WIN32_AVAILABLE={WIN32_AVAILABLE}, game_hwnd={self.game_hwnd}")
            return False
        
        # 验证窗口句柄是否有效
        try:
            if not win32gui.IsWindow(self.game_hwnd):
                logger.error(f"窗口句柄无效: {self.game_hwnd}")
                return False
            window_title = win32gui.GetWindowText(self.game_hwnd)
            logger.info(f"✅ 窗口句柄有效: {self.game_hwnd}, 标题: '{window_title}'")
        except Exception as e:
            logger.error(f"验证窗口句柄失败: {e}")
            return False
        
        try:
            # 查找可用端口
            import socket
            port = self._find_available_port()
            logger.info(f"找到可用端口: {port}")
            
            # 构建命令（不带 / ，因为按键已经输入了 /）
            command_text = f"publish true survival {port}"
            
            # 持续执行，直到检测到成功（最多尝试60秒）
            start_time = time.time()
            timeout = 60
            attempt = 0
            input_locked = False  # 记录是否已锁定键鼠
            caps_lock_state = 0  # 记录原始大写锁定状态
            
            def restore_and_cleanup():
                """恢复设置并清理：还原大写锁定 -> 退出全屏 -> 解锁键鼠"""
                try:
                    import win32api
                    import ctypes
                    
                    logger.info("开始恢复设置...")
                    
                    # 1. 还原大写锁定状态
                    if caps_lock_state == 0:  # 原来未开启，现在关闭
                        win32api.keybd_event(win32con.VK_CAPITAL, 0, 0, 0)
                        time.sleep(0.01)
                        win32api.keybd_event(win32con.VK_CAPITAL, 0, win32con.KEYEVENTF_KEYUP, 0)
                        time.sleep(0.1)
                        logger.info("已还原大写锁定状态")
                    
                    # 2. 按F11退出全屏
                    win32api.keybd_event(win32con.VK_F11, 0, 0, 0)
                    time.sleep(0.01)
                    win32api.keybd_event(win32con.VK_F11, 0, win32con.KEYEVENTF_KEYUP, 0)
                    logger.info("已按F11退出全屏")
                    
                    time.sleep(0.3)
                    
                    # 3. 解锁键鼠（如果之前锁定了）
                    if input_locked:
                        try:
                            ctypes.windll.user32.BlockInput(False)
                            logger.info("已解锁键鼠输入")
                        except Exception as e:
                            logger.debug(f"解锁键鼠失败: {e}")
                except Exception as e:
                    logger.error(f"恢复设置失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            while time.time() - start_time < timeout:
                attempt += 1
                
                # 先检查是否已经开启
                if self._check_lan_opened(port):
                    logger.info(f"✅ 局域网已开启在端口 {port}")
                    self.lan_port = port
                    
                    # 成功后：还原大写锁定 -> 退出全屏 -> 解锁键鼠
                    restore_and_cleanup()
                    
                    return True
                
                # 快速尝试发送命令
                logger.info(f"第{attempt}次尝试开启局域网...")
                
                try:
                    import win32api
                    import ctypes
                    
                    # 第1次尝试时：最大化窗口、激活、保存大写锁定状态、开启大写锁定、锁定键鼠
                    if attempt == 1:
                        # 最大化游戏窗口
                        try:
                            win32gui.ShowWindow(self.game_hwnd, 3)  # SW_MAXIMIZE
                            time.sleep(0.1)
                        except Exception as e:
                            logger.debug(f"最大化窗口失败: {e}")
                        
                        # 激活游戏窗口
                        try:
                            win32gui.SetForegroundWindow(self.game_hwnd)
                            time.sleep(0.2)
                        except Exception as e:
                            logger.debug(f"激活窗口失败: {e}")
                        
                        # 保存当前大写锁定状态
                        try:
                            caps_lock_state = win32api.GetKeyState(win32con.VK_CAPITAL)
                            logger.info(f"当前大写锁定状态: {caps_lock_state}")
                        except Exception as e:
                            caps_lock_state = 0
                            logger.warning(f"获取大写锁定状态失败: {e}")
                        
                        # 开启大写锁定（避免中文输入法干扰）
                        try:
                            # 如果大写锁定未开启，则按一次开启
                            if caps_lock_state == 0:
                                win32api.keybd_event(win32con.VK_CAPITAL, 0, 0, 0)
                                time.sleep(0.01)
                                win32api.keybd_event(win32con.VK_CAPITAL, 0, win32con.KEYEVENTF_KEYUP, 0)
                                time.sleep(0.1)
                                logger.info("已开启大写锁定")
                        except Exception as e:
                            logger.warning(f"开启大写锁定失败: {e}")
                        
                        # 锁定键鼠输入（可选，需要管理员权限）
                        try:
                            ctypes.windll.user32.BlockInput(True)
                            input_locked = True
                            logger.info("已锁定键鼠输入")
                        except Exception as e:
                            # 锁定失败不影响整体功能，继续执行
                            logger.debug(f"锁定键鼠失败(需管理员权限): {e}")
                    
                    # 发送命令（使用剪贴板粘贴）
                    try:
                        import win32clipboard
                        
                        # 将命令复制到剪贴板
                        win32clipboard.OpenClipboard()
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardText(command_text, win32clipboard.CF_UNICODETEXT)
                        win32clipboard.CloseClipboard()
                        logger.info(f"已将命令复制到剪贴板: {command_text}")
                    except Exception as e:
                        logger.error(f"复制到剪贴板失败: {e}")
                    
                    # 按 / 打开命令框
                    win32api.keybd_event(0xBF, 0, 0, 0)  # /
                    time.sleep(0.01)
                    win32api.keybd_event(0xBF, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.15)
                    
                    # Ctrl+V 粘贴命令
                    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                    time.sleep(0.01)
                    win32api.keybd_event(0x56, 0, 0, 0)  # V
                    time.sleep(0.01)
                    win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.01)
                    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.1)
                    logger.info("已粘贴命令")
                    
                    # 回车
                    win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
                    time.sleep(0.01)
                    win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
                    logger.info(f"已发送命令: /{command_text}")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"发送命令失败: {e}")
                    time.sleep(0.5)
            
            # 超时后最后检查一次
            if self._check_lan_opened(port):
                logger.info(f"✅ 局域网开启成功，端口: {port}")
                self.lan_port = port
                return True
            else:
                logger.error("局域网开启超时")
                return False
            
        except Exception as e:
            logger.error(f"自动开启局域网失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _check_lan_opened(self, port):
        """
        检查局域网是否已经开启（通过端口通断测试）
        
        Args:
            port: 端口号
            
        Returns:
            bool: 是否已开启
        """
        try:
            import socket
            
            # 尝试连接本地端口
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)  # 500ms超时
            
            try:
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                # 连接成功说明端口已开启
                if result == 0:
                    logger.debug(f"端口 {port} 已开启")
                    return True
                else:
                    return False
            except Exception as e:
                sock.close()
                return False
            
        except Exception as e:
            logger.debug(f"检查端口失败: {e}")
            return False
    
    def _find_available_port(self, start_port=25565, max_attempts=100):
        """
        查找可用端口
        
        Args:
            start_port: 起始端口
            max_attempts: 最大尝试次数
            
        Returns:
            int: 可用端口
        """
        import socket
        
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(('', port))
                    return port
            except OSError:
                continue
        
        # 如果找不到，返回默认端口
        return start_port
    
    def _send_char(self, char):
        """发送字符输入（前台方式，已废弃）"""
        if not self.game_hwnd:
            return
        
        try:
            # 将字符转换为Unicode
            win32api.PostMessage(self.game_hwnd, win32con.WM_CHAR, ord(char), 0)
        except Exception as e:
            logger.error(f"发送字符失败: {e}")
    
    def _send_char_background(self, char):
        """后台发送字符输入（不抢占焦点）"""
        if not self.game_hwnd:
            logger.warning("窗口句柄为空，无法发送字符")
            return
        
        try:
            # 使用PostMessage后台发送WM_CHAR消息
            result = win32api.PostMessage(self.game_hwnd, win32con.WM_CHAR, ord(char), 0)
            logger.debug(f"发送字符 '{char}' 到窗口 {self.game_hwnd}, 结果: {result}")
        except Exception as e:
            logger.error(f"后台发送字符失败: {e}")
    
    def _send_key(self, vk_code):
        """发送键盘按键（前台方式，已废弃）"""
        if not self.game_hwnd:
            return
        
        try:
            # 按下按键
            win32api.PostMessage(self.game_hwnd, win32con.WM_KEYDOWN, vk_code, 0)
            time.sleep(0.05)
            # 释放按键
            win32api.PostMessage(self.game_hwnd, win32con.WM_KEYUP, vk_code, 0)
            logger.debug(f"发送按键: {vk_code}")
        except Exception as e:
            logger.error(f"发送按键失败: {e}")
    
    def _send_key_background(self, vk_code):
        """后台发送键盘按键（不抢占焦点）"""
        if not self.game_hwnd:
            logger.warning("窗口句柄为空，无法发送按键")
            return
        
        try:
            # 使用PostMessage后台发送按键消息
            # 按下按键
            result1 = win32api.PostMessage(self.game_hwnd, win32con.WM_KEYDOWN, vk_code, 0)
            time.sleep(0.05)
            # 释放按键
            result2 = win32api.PostMessage(self.game_hwnd, win32con.WM_KEYUP, vk_code, 0)
            logger.debug(f"发送按键 {vk_code} 到窗口 {self.game_hwnd}, 结果: down={result1}, up={result2}")
        except Exception as e:
            logger.error(f"后台发送按键失败: {e}")
    
    def _click_at(self, x, y):
        """后台点击指定坐标"""
        if not self.game_hwnd:
            return
        
        try:
            # 转换为窗口坐标
            lParam = win32api.MAKELONG(x, y)
            
            # 发送鼠标消息
            win32api.PostMessage(self.game_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
            time.sleep(0.1)
            win32api.PostMessage(self.game_hwnd, win32con.WM_LBUTTONUP, 0, lParam)
            
            logger.debug(f"点击坐标: ({x}, {y})")
            
        except Exception as e:
            logger.error(f"点击失败: {e}")
    
    def get_lan_port_from_log(self, timeout=30):
        """
        从游戏日志获取局域网端口
        
        Args:
            timeout: 超时时间
            
        Returns:
            int: 端口号,失败返回None
        """
        try:
            # 版本隔离：日志在版本目录下
            log_file = self.game_dir / 'logs' / 'latest.log'
            
            if not log_file.exists():
                logger.error(f"日志文件不存在: {log_file}")
                return None
            
            start_time = time.time()
            last_size = 0
            
            while time.time() - start_time < timeout:
                try:
                    # 检查文件大小变化
                    current_size = log_file.stat().st_size
                    
                    if current_size > last_size:
                        # 读取新增内容
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            f.seek(last_size)
                            new_content = f.read()
                            
                            # 匹配端口号
                            # 日志格式: [Server thread/INFO]: Starting Minecraft server on *:25565
                            match = re.search(r'Starting (?:Minecraft )?server on \*:(\d+)', new_content)
                            if match:
                                port = int(match.group(1))
                                self.lan_port = port
                                logger.info(f"检测到局域网端口: {port}")
                                return port
                        
                        last_size = current_size
                        
                except Exception as e:
                    logger.debug(f"读取日志失败: {e}")
                
                time.sleep(1)
            
            logger.warning("获取局域网端口超时")
            return None
            
        except Exception as e:
            logger.error(f"监听日志失败: {e}")
            return None

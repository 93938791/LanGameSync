"""
Minecraft版本扫描器
扫描版本隔离的游戏版本和存档
"""
import os
from utils.logger import Logger

logger = Logger().get_logger("VersionScanner")


class MinecraftVersionScanner:
    """Minecraft版本扫描器 - 只扫描版本隔离的版本"""
    
    def __init__(self, launcher_path):
        """
        初始化扫描器
        
        Args:
            launcher_path: 启动器exe文件路径
        """
        self.launcher_path = launcher_path
        self.minecraft_dir = self._get_minecraft_dir()
        self.launcher_type = self._detect_launcher_type()
    
    def _detect_launcher_type(self):
        """检测启动器类型"""
        launcher_name = os.path.basename(self.launcher_path).lower()
        
        if 'hmcl' in launcher_name:
            return 'HMCL'
        elif 'pcl' in launcher_name:
            return 'PCL2'
        else:
            return 'Unknown'
    
    def _get_minecraft_dir(self):
        """获取.minecraft文件夹路径"""
        launcher_dir = os.path.dirname(self.launcher_path)
        
        # HMCL: 启动器同级目录下的.minecraft
        # PCL2: 启动器同级目录下的.minecraft
        minecraft_dir = os.path.join(launcher_dir, '.minecraft')
        
        if os.path.exists(minecraft_dir):
            return minecraft_dir
        else:
            # 如果.minecraft不存在,尝试创建
            try:
                os.makedirs(minecraft_dir, exist_ok=True)
                logger.info(f"创建.minecraft文件夹: {minecraft_dir}")
                return minecraft_dir
            except Exception as e:
                logger.warning(f"创建.minecraft文件夹失败: {e}")
                return None
    
    def scan_versions(self):
        """
        扫描所有版本隔离的游戏版本
        
        Returns:
            list: 版本列表,每个元素包含 {name, path, saves}
        """
        if not self.minecraft_dir:
            return []
        
        versions_dir = os.path.join(self.minecraft_dir, "versions")
        if not os.path.exists(versions_dir):
            logger.warning(f"versions文件夹不存在: {versions_dir}")
            return []
        
        versions = []
        
        try:
            for version_name in os.listdir(versions_dir):
                version_path = os.path.join(versions_dir, version_name)
                
                # 跳过文件,只处理文件夹
                if not os.path.isdir(version_path):
                    continue
                
                # 检查是否是有效的游戏版本(包含.json文件)
                json_file = os.path.join(version_path, f"{version_name}.json")
                if not os.path.exists(json_file):
                    continue
                
                # 读取版本信息
                version_info = self._read_version_json(json_file)
                if not version_info:
                    continue
                
                # 检查是否有saves文件夹(版本隔离的标志)
                saves_dir = os.path.join(version_path, "saves")
                if not os.path.exists(saves_dir):
                    # 如果没有saves文件夹,创建一个（支持新版本）
                    try:
                        os.makedirs(saves_dir, exist_ok=True)
                        logger.info(f"为版本 {version_name} 创建 saves 文件夹")
                    except Exception as e:
                        logger.warning(f"创建 saves 文件夹失败: {e}")
                        # 即使创建失败,也继续显示该版本
                        saves_dir = None
                
                # 扫描该版本下的存档
                saves = self._scan_saves(saves_dir) if saves_dir else []
                
                versions.append({
                    "name": version_name,
                    "path": version_path,
                    "saves_dir": saves_dir,
                    "saves": saves,
                    "save_count": len(saves),
                    "game_version": version_info.get('game_version', version_name),  # 真实游戏版本
                    "loader_type": version_info.get('loader_type', 'vanilla'),  # 加载器类型
                    "loader_version": version_info.get('loader_version', '')  # 加载器版本
                })
                
                loader_info = version_info.get('loader_type', 'vanilla')
                if version_info.get('loader_version'):
                    loader_info += f" {version_info.get('loader_version')}"
                
                game_ver = version_info.get('game_version', version_name)
                logger.info(f"检测到版本: {version_name} (游戏: {game_ver}, 加载器: {loader_info}), 存档数: {len(saves)}")
        
        except Exception as e:
            logger.error(f"扫描版本时出错: {e}")
        
        # 按版本名排序(新版本在前)
        versions.sort(key=lambda x: x['name'], reverse=True)
        
        return versions
    
    def _scan_saves(self, saves_dir):
        """
        扫描存档文件夹
        
        Args:
            saves_dir: saves文件夹路径
            
        Returns:
            list: 存档列表,每个元素包含 {name, path, info}
        """
        saves = []
        
        try:
            if not os.path.exists(saves_dir):
                return saves
            
            for save_name in os.listdir(saves_dir):
                save_path = os.path.join(saves_dir, save_name)
                
                # 只处理文件夹
                if not os.path.isdir(save_path):
                    continue
                
                # 检查是否是有效的存档(包含level.dat)
                level_dat = os.path.join(save_path, "level.dat")
                if os.path.exists(level_dat):
                    # 读取存档详细信息
                    save_info = self._read_level_dat(level_dat)
                    
                    saves.append({
                        "name": save_name,
                        "path": save_path,
                        "info": save_info
                    })
        
        except Exception as e:
            logger.error(f"扫描存档时出错: {e}")
        
        return saves
    
    def _read_version_json(self, json_file):
        """
        读取版本 JSON 文件,获取游戏版本和mod加载器信息
        
        Args:
            json_file: JSON文件路径
            
        Returns:
            dict: {
                'game_version': '游戏版本',
                'loader_type': 'vanilla/fabric/forge/neoforge',
                'loader_version': '加载器版本'
            }
        """
        try:
            import json
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            result = {
                'game_version': data.get('id', ''),
                'loader_type': 'vanilla',
                'loader_version': ''
            }
            
            # 检测 Fabric
            if 'arguments' in data:
                # 检查 game arguments
                game_args = data.get('arguments', {}).get('game', [])
                for arg in game_args:
                    if isinstance(arg, str):
                        if 'fabric' in arg.lower():
                            result['loader_type'] = 'fabric'
                            break
            
            # 检测 Forge/NeoForge
            if 'inheritsFrom' in data:
                inherit = data.get('inheritsFrom', '')
                result['game_version'] = inherit  # 真实游戏版本
                
                # 检查mainClass来判断forge类型
                main_class = data.get('mainClass', '')
                if 'forge' in main_class.lower():
                    if 'neoforge' in main_class.lower() or 'neo' in data.get('id', '').lower():
                        result['loader_type'] = 'neoforge'
                    else:
                        result['loader_type'] = 'forge'
                elif 'fabric' in main_class.lower():
                    result['loader_type'] = 'fabric'
            
            # 尝试从id中提取加载器版本
            version_id = data.get('id', '')
            if result['loader_type'] != 'vanilla':
                # 例如: "1.20.1-forge-47.2.0" 或 "fabric-loader-0.15.0-1.20.1"
                if result['loader_type'] in version_id.lower():
                    parts = version_id.split('-')
                    for i, part in enumerate(parts):
                        if result['loader_type'] in part.lower() and i + 1 < len(parts):
                            result['loader_version'] = parts[i + 1]
                            break
            
            return result
        
        except Exception as e:
            logger.error(f"读取版本 JSON 失败: {e}")
            return None
    
    def _read_level_dat(self, level_dat_path):
        """
        读取 level.dat 文件,获取存档详细信息
        
        Args:
            level_dat_path: level.dat文件路径
            
        Returns:
            dict: {
                'game_mode': '游戏模式',
                'difficulty': '难度',
                'day_time': '游戏天数',
                'version_name': '版本名称',
                'level_name': '世界名称'
            }
        """
        try:
            import nbtlib
            
            # 读取NBT数据
            nbt_file = nbtlib.load(level_dat_path)
            
            # 获取Data标签
            if 'Data' not in nbt_file:
                logger.warning(f"level.dat中没有Data标签: {level_dat_path}")
                return self._get_empty_save_info()
            
            data = nbt_file['Data']
            
            # 游戏模式
            game_type = int(data.get('GameType', 0))
            game_modes = {
                0: '生存',
                1: '创造',
                2: '冒险',
                3: '旁观'
            }
            
            # 难度
            difficulty = int(data.get('Difficulty', 0))
            difficulties = {
                0: '和平',
                1: '简单',
                2: '普通',
                3: '困难'
            }
            
            # 游戏时间(转tick转换为天数)
            day_time = int(data.get('DayTime', 0))
            days = day_time // 24000
            
            # 版本信息
            version_name = '-'
            if 'Version' in data:
                version_data = data['Version']
                if 'Name' in version_data:
                    version_name = str(version_data['Name'])
            
            # 世界名称
            level_name = str(data.get('LevelName', ''))
            
            logger.info(f"读取存档信息: 模式={game_modes.get(game_type)}, 难度={difficulties.get(difficulty)}, 天数={days}")
            
            return {
                'game_mode': game_modes.get(game_type, f'未知({game_type})'),
                'difficulty': difficulties.get(difficulty, f'未知({difficulty})'),
                'day_time': days,
                'version_name': version_name,
                'level_name': level_name
            }
        
        except ImportError:
            logger.warning("未安装 nbtlib 库,无法读取存档详细信息")
            return self._get_empty_save_info()
        except Exception as e:
            logger.error(f"读取 level.dat 失败: {level_dat_path}, 错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_empty_save_info()
    
    def _get_empty_save_info(self):
        """返回空的存档信息"""
        return {
            'game_mode': '-',
            'difficulty': '-',
            'day_time': 0,
            'version_name': '-',
            'level_name': '-'
        }
    
    def get_save_players(self, save_path):
        """
        获取存档中的玩家列表
        
        Args:
            save_path: 存档文件夹路径
            
        Returns:
            list: 玩家列表 [{'uuid': 'xxx', 'uuid_formatted': 'xxx-xxx', 'name': 'xxx'}, ...]
        """
        try:
            import os
            import json
            
            # 先尝试从usernamecache.json读取(包含带连字符的UUID和玩家名)
            minecraft_dir = os.path.dirname(os.path.dirname(save_path))  # 回到.minecraft目录
            usercache_file = os.path.join(minecraft_dir, "usercache.json")
            
            player_cache = {}
            if os.path.exists(usercache_file):
                try:
                    with open(usercache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        # 构建无连字符UUID到玩家信息的映射
                        for entry in cache_data:
                            uuid_with_dash = entry.get('uuid', '')
                            name = entry.get('name', '')
                            if uuid_with_dash:
                                uuid_no_dash = uuid_with_dash.replace('-', '')
                                player_cache[uuid_no_dash] = {
                                    'uuid_formatted': uuid_with_dash,
                                    'name': name
                                }
                    logger.info(f"从usernamecache.json读取到 {len(player_cache)} 个玩家缓存")
                except Exception as e:
                    logger.warning(f"读取usercache.json失败: {e}")
            
            playerdata_dir = os.path.join(save_path, "playerdata")
            if not os.path.exists(playerdata_dir):
                return []
            
            players = []
            
            # 遍历playerdata文件夹中的所有.dat文件
            for filename in os.listdir(playerdata_dir):
                if not filename.endswith('.dat'):
                    continue
                
                # 提取UUID(文件名,无连字符)
                uuid_from_file = filename.replace('.dat', '')
                logger.info(f"扫描到玩家文件: {filename}, UUID: {uuid_from_file}")
                
                # 确保UUID是无连字符格式
                uuid_no_dash = uuid_from_file.replace('-', '')
                
                # 从usernamecache中查找带连字符的UUID和玩家名
                if uuid_no_dash in player_cache:
                    cache_info = player_cache[uuid_no_dash]
                    players.append({
                        'uuid': uuid_no_dash,
                        'uuid_formatted': cache_info['uuid_formatted'],
                        'name': cache_info.get('name')
                    })
                else:
                    # 如果缓存中没有,手动转换UUID格式
                    if len(uuid_no_dash) == 32:
                        uuid_formatted = f"{uuid_no_dash[:8]}-{uuid_no_dash[8:12]}-{uuid_no_dash[12:16]}-{uuid_no_dash[16:20]}-{uuid_no_dash[20:]}"
                    else:
                        uuid_formatted = uuid_no_dash
                    
                    players.append({
                        'uuid': uuid_no_dash,
                        'uuid_formatted': uuid_formatted,
                        'name': None
                    })
            
            return players
        
        except Exception as e:
            logger.error(f"获取玩家列表失败: {e}")
            return []
    
    def get_player_name_by_uuid(self, uuid):
        """
        通过UUID查询玩家名称(使用Mojang API)
        
        Args:
            uuid: 玩家UUID
            
        Returns:
            str: 玩家名称,失败返回None
        """
        try:
            import requests
            
            # 去掉UUID中的连字符
            uuid_clean = uuid.replace('-', '')
            
            # Mojang API
            url = f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid_clean}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('name')
            else:
                return None
        
        except Exception as e:
            logger.error(f"查询玩家名称失败: {uuid}, {e}")
            return None
    
    def get_save_full_path(self, version_name, save_name=None):
        """
        获取存档的完整路径
        
        Args:
            version_name: 版本名称
            save_name: 存档名称,如果None则返回saves文件夹路径
            
        Returns:
            str: 存档完整路径或saves文件夹路径
        """
        if not self.minecraft_dir:
            return None
        
        saves_dir = os.path.join(
            self.minecraft_dir,
            "versions",
            version_name,
            "saves"
        )
        
        if save_name:
            return os.path.join(saves_dir, save_name)
        else:
            return saves_dir

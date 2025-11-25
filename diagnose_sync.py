"""
Syncthing 同步诊断工具
用于检查两台设备的 Syncthing 配置和连接状态
"""
import requests
import json
from config import Config

def diagnose_syncthing():
    """诊断 Syncthing 状态"""
    print("=" * 60)
    print("Syncthing 同步诊断工具")
    print("=" * 60)
    
    api_url = f"http://localhost:{Config.SYNCTHING_API_PORT}"
    headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
    
    try:
        # 1. 检查 Syncthing 是否运行
        print("\n[1] 检查 Syncthing 服务状态...")
        try:
            resp = requests.get(f"{api_url}/rest/system/status", headers=headers, timeout=3)
            resp.raise_for_status()
            status = resp.json()
            print(f"✓ Syncthing 正在运行")
            print(f"  设备ID: {status['myID']}")
            print(f"  版本: {status.get('version', 'unknown')}")
        except Exception as e:
            print(f"✗ Syncthing 未运行或无法连接: {e}")
            return
        
        # 2. 检查配置的设备列表
        print("\n[2] 检查配置的设备列表...")
        try:
            resp = requests.get(f"{api_url}/rest/config", headers=headers, timeout=3)
            resp.raise_for_status()
            config = resp.json()
            
            devices = config.get('devices', [])
            print(f"  配置中的设备数: {len(devices)}")
            
            for i, device in enumerate(devices):
                device_id = device.get('deviceID', '')
                device_name = device.get('name', 'Unknown')
                addresses = device.get('addresses', [])
                paused = device.get('paused', False)
                
                print(f"\n  设备 {i+1}:")
                print(f"    名称: {device_name}")
                print(f"    ID: {device_id[:12]}...")
                print(f"    地址: {addresses}")
                print(f"    暂停: {paused}")
        except Exception as e:
            print(f"✗ 获取配置失败: {e}")
        
        # 3. 检查实际连接状态
        print("\n[3] 检查设备实际连接状态...")
        try:
            resp = requests.get(f"{api_url}/rest/system/connections", headers=headers, timeout=3)
            resp.raise_for_status()
            connections = resp.json()
            
            total_devices = connections.get('total', {})
            print(f"  总连接数: {total_devices.get('connected', 0)}")
            print(f"  总设备数: {len(connections.get('connections', {}))}")
            
            device_connections = connections.get('connections', {})
            
            if not device_connections:
                print("\n  ⚠ 警告: 没有任何设备连接信息！")
            else:
                for dev_id, conn_info in device_connections.items():
                    is_connected = conn_info.get('connected', False)
                    address = conn_info.get('address', 'unknown')
                    in_bytes = conn_info.get('inBytesTotal', 0)
                    out_bytes = conn_info.get('outBytesTotal', 0)
                    
                    status_icon = "✓" if is_connected else "✗"
                    print(f"\n  {status_icon} 设备 {dev_id[:12]}...")
                    print(f"    连接状态: {'已连接' if is_connected else '未连接'}")
                    print(f"    地址: {address}")
                    print(f"    接收: {in_bytes} bytes")
                    print(f"    发送: {out_bytes} bytes")
                    
                    if not is_connected:
                        print(f"    ⚠ 此设备未连接!")
        except Exception as e:
            print(f"✗ 获取连接状态失败: {e}")
        
        # 4. 检查同步文件夹配置
        print("\n[4] 检查同步文件夹配置...")
        try:
            folders = config.get('folders', [])
            print(f"  配置的同步文件夹数: {len(folders)}")
            
            if not folders:
                print("\n  ⚠ 警告: 没有配置任何同步文件夹！")
            else:
                for i, folder in enumerate(folders):
                    folder_id = folder.get('id', '')
                    folder_label = folder.get('label', '')
                    folder_path = folder.get('path', '')
                    folder_paused = folder.get('paused', False)
                    folder_devices = folder.get('devices', [])
                    
                    print(f"\n  文件夹 {i+1}:")
                    print(f"    ID: {folder_id}")
                    print(f"    标签: {folder_label}")
                    print(f"    路径: {folder_path}")
                    print(f"    暂停: {folder_paused}")
                    print(f"    共享给设备数: {len(folder_devices)}")
                    
                    if len(folder_devices) == 0:
                        print(f"    ⚠ 警告: 此文件夹未共享给任何设备！")
                    else:
                        for dev in folder_devices:
                            dev_id = dev.get('deviceID', '')
                            print(f"      - {dev_id[:12]}...")
        except Exception as e:
            print(f"✗ 获取文件夹配置失败: {e}")
        
        # 5. 诊断建议
        print("\n" + "=" * 60)
        print("诊断结果和建议:")
        print("=" * 60)
        
        # 检查是否有设备但未连接
        if len(devices) > 0:
            if len(device_connections) == 0:
                print("\n⚠ 问题: 配置了设备但没有任何连接信息")
                print("  可能原因:")
                print("  1. 两台设备没有在同一虚拟网络中")
                print("  2. Syncthing 的监听地址配置有问题")
                print("  3. 防火墙阻止了 Syncthing 的连接")
                print("\n  建议:")
                print("  - 检查两台设备是否都已连接到相同的 Easytier 网络")
                print("  - 检查 Syncthing 是否监听在 0.0.0.0 (所有接口)")
                print("  - 尝试手动 ping 对方的虚拟 IP")
            else:
                disconnected = [dev_id for dev_id, info in device_connections.items() if not info.get('connected')]
                if disconnected:
                    print(f"\n⚠ 问题: 有 {len(disconnected)} 个设备未连接")
                    print("  可能原因:")
                    print("  1. 对方设备的 Syncthing 未启动")
                    print("  2. 对方设备未将本机添加为设备")
                    print("  3. 网络连接问题")
                    print("\n  建议:")
                    print("  - 确保对方设备也添加了你的设备ID")
                    print("  - 检查双方的虚拟网络连接是否正常")
                else:
                    print("\n✓ 所有设备都已成功连接!")
        else:
            print("\n⚠ 问题: 未配置任何远程设备")
            print("  建议: 使用应用的设备发现功能添加远程设备")
        
        # 检查文件夹配置
        if len(folders) == 0:
            print("\n⚠ 问题: 未配置任何同步文件夹")
            print("  建议: 在游戏页面选择存档并启用同步")
        else:
            for folder in folders:
                if len(folder.get('devices', [])) == 0:
                    print(f"\n⚠ 问题: 文件夹 '{folder.get('id')}' 未共享给任何设备")
                    print("  建议: 确保文件夹已共享给远程设备")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n✗ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 初始化配置
    Config.init_dirs()
    
    # 运行诊断
    diagnose_syncthing()
    
    print("\n按回车键退出...")
    input()

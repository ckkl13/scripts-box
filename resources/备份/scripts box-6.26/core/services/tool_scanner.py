# -*- coding: utf-8 -*-
import os
from core.qt_compat import cmds


def scan_tools_directory(tools_dir):
    """扫描工具目录：仅识别 tool 下直接子文件夹作为分组，分组内只识别 .py 和 .mel 文件（不嵌套）"""
    config = {
        "groups": [],
        "tools": [],
        "recycle_bin": [],
        "button_layout": "single",
        "button_colors": {},
        "sidebar_layout": False,
        "dockable_mode": False
    }
    
    try:
        if not os.path.exists(tools_dir):
            os.makedirs(tools_dir)
        
        for name in sorted(os.listdir(tools_dir)):
            abs_dir = os.path.join(tools_dir, name)
            if not os.path.isdir(abs_dir):
                continue
            group_id = f"group:{name}"
            group = {
                "id": group_id,
                "name": name,
                "path": name,
                "parent": None
            }
            config["groups"].append(group)
            scan_group_directory(abs_dir, group_id, config)
        
        if not config["groups"]:
            new_group_name = "新建分组"
            new_group_dir = os.path.join(tools_dir, new_group_name)
            if not os.path.exists(new_group_dir):
                os.makedirs(new_group_dir)
            config["groups"].append({
                "name": new_group_name,
                "id": f"group:{new_group_name}",
                "path": new_group_name,
                "parent": None
            })
            
    except Exception as e:
        cmds.warning(f"扫描工具目录失败: {str(e)}")
        config["groups"] = [{"name": "新建分组", "id": f"group:新建分组", "path": "新建分组", "parent": None}]
        
    return config


def scan_group_directory(group_path, group_id, config, relative_path=""):
    """扫描分组目录中的脚本文件（支持一层子目录）"""
    try:
        for file_name in os.listdir(group_path):
            file_path = os.path.join(group_path, file_name)
            
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(file_name)
                ext = ext.lower()
                
                if ext in ['.py', '.mel']:
                    script_type = "python" if ext == ".py" else "mel"
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    except:
                        try:
                            with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                                content = f.read()
                        except:
                            with open(file_path, 'r', encoding='latin-1') as f:
                                content = f.read()
                    
                    script_name = os.path.splitext(file_name)[0]
                        
                    tool_info = {
                        "name": script_name,
                        "filename": file_name,
                        "type": script_type,
                        "group": group_id,
                        "path": file_path
                    }
                        
                    config["tools"].append(tool_info)
            
            elif os.path.isdir(file_path):
                # 子目录：递归扫描，工具仍属于父分组
                sub_rel = os.path.join(relative_path, file_name) if relative_path else file_name
                scan_group_directory(file_path, group_id, config, sub_rel)
    except Exception as e:
        cmds.warning(f"扫描分组目录失败: {group_path}, 错误: {str(e)}")

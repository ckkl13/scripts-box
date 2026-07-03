# -*- coding: utf-8 -*-
"""
工具架管理服务
提供工具架的读取、保存、加载功能
"""

import os
import shutil
from pathlib import Path

try:
    import maya.cmds as cmds
    import maya.mel as mel
except ImportError:
    cmds = None
    mel = None


class ShelfService:
    """工具架服务类"""
    
    def __init__(self, data_dir):
        """
        初始化工具架服务
        
        参数:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self.shelves_dir = self.data_dir / "shelves"
        self.shelves_dir.mkdir(parents=True, exist_ok=True)
    
    def get_current_maya_version(self):
        """
        获取当前 Maya 版本号
        
        返回:
            str: Maya 版本号，例如 "2023"
        """
        if cmds:
            try:
                full_version = cmds.about(version=True)
                # 提取主版本号，例如 "2023"
                version = full_version.split()[0]
                if version.isdigit():
                    return version
            except:
                pass
        return None
    
    def get_current_maya_language(self):
        """
        获取当前 Maya 语言设置
        
        返回:
            str: 语言代码，例如 "zh_CN" 或 "en_US"
        """
        if cmds:
            try:
                # 尝试获取 Maya 的语言设置
                # 方法 1: 使用 about 命令
                lang = cmds.about(language=True)
                if lang:
                    # 映射常见语言值
                    lang_map = {
                        "zh_CN": "zh_CN",
                        "zh": "zh_CN",
                        "cn": "zh_CN",
                        "chs": "zh_CN",
                        "en_US": "en_US",
                        "en": "en_US",
                        "eng": "en_US",
                    }
                    return lang_map.get(lang.lower(), "zh_CN")
            except:
                pass
        # 默认返回中文
        return "zh_CN"
    
    def get_maya_shelves_dir(self):
        """
        获取当前 Maya 工具架目录
        
        返回:
            Path: Maya 工具架目录路径
        """
        maya_doc_dir = Path.home() / "Documents" / "maya"
        if not maya_doc_dir.exists():
            return None
        
        # 获取当前运行的 Maya 版本和语言
        current_version = self.get_current_maya_version()
        current_lang = self.get_current_maya_language()
        
        # 构建路径列表，按优先级
        possible_paths = []
        
        if current_version:
            # 1. 当前版本 + 当前语言
            possible_paths.append(maya_doc_dir / current_version / current_lang / "prefs" / "shelves")
            # 2. 当前版本 + 无语言
            possible_paths.append(maya_doc_dir / current_version / "prefs" / "shelves")
            # 3. 当前版本 + 另一种语言备选
            other_lang = "en_US" if current_lang == "zh_CN" else "zh_CN"
            possible_paths.append(maya_doc_dir / current_version / other_lang / "prefs" / "shelves")
        
        # 如果找不到，尝试查找所有版本的目录作为备选
        maya_versions = []
        for item in maya_doc_dir.iterdir():
            if item.is_dir() and item.name.isdigit():
                maya_versions.append(item.name)
        
        if maya_versions:
            latest_version = sorted(maya_versions, key=int, reverse=True)[0]
            possible_paths.extend([
                maya_doc_dir / latest_version / current_lang / "prefs" / "shelves",
                maya_doc_dir / latest_version / "prefs" / "shelves",
            ])
        
        # 返回第一个存在的路径
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def get_all_maya_shelves_dirs(self):
        """
        获取当前 Maya 工具架目录（为了向后兼容）
        
        返回:
            list: 包含当前工具架目录的列表
        """
        shelves_dir = self.get_maya_shelves_dir()
        return [shelves_dir] if shelves_dir else []
    
    def list_maya_shelves(self):
        """
        列出 Maya 中的所有工具架
        
        返回:
            list: 工具架文件路径列表
        """
        shelves_dirs = self.get_all_maya_shelves_dirs()
        if not shelves_dirs:
            return []
        
        shelves = []
        seen_names = set()
        
        # 优先从最新版本的目录收集
        for shelves_dir in shelves_dirs:
            for item in shelves_dir.iterdir():
                if item.is_file() and item.name.startswith("shelf_") and item.name.endswith(".mel"):
                    # 避免重复同名的工具架
                    if item.name not in seen_names:
                        shelves.append(item)
                        seen_names.add(item.name)
        
        return shelves
    
    def list_saved_shelves(self):
        """
        列出已保存的工具架
        
        返回:
            list: 已保存的工具架文件路径列表
        """
        shelves = []
        for item in self.shelves_dir.iterdir():
            if item.is_file() and item.name.endswith(".mel"):
                shelves.append(item)
        
        return shelves
    
    def save_shelf(self, shelf_path):
        """
        保存 Maya 工具架到本地
        
        参数:
            shelf_path: Maya 工具架文件路径
            
        返回:
            str: 保存的文件路径，失败返回 None
        """
        try:
            shelf_path = Path(shelf_path)
            if not shelf_path.exists():
                return None
            
            dest_path = self.shelves_dir / shelf_path.name
            shutil.copy2(shelf_path, dest_path)
            
            return str(dest_path)
        except Exception as e:
            print(f"保存工具架失败: {e}")
            return None
    
    def load_shelf(self, shelf_name):
        """
        加载已保存的工具架到 Maya
        
        参数:
            shelf_name: 工具架文件名
            
        返回:
            bool: 是否成功
        """
        try:
            src_path = self.shelves_dir / shelf_name
            if not src_path.exists():
                return False
            
            # 使用 Maya MEL 命令 loadNewShelf 直接加载
            if mel:
                # 构建 MEL 命令，需要转义路径中的反斜杠
                shelf_path_str = str(src_path).replace('\\', '/')
                mel_cmd = f'loadNewShelf "{shelf_path_str}"'
                mel.eval(mel_cmd)
                return True
            return False
        except Exception as e:
            print(f"加载工具架失败: {e}")
            return False
    
    def delete_saved_shelf(self, shelf_name):
        """
        删除已保存的工具架
        
        参数:
            shelf_name: 工具架文件名
            
        返回:
            bool: 是否成功
        """
        try:
            shelf_path = self.shelves_dir / shelf_name
            if shelf_path.exists():
                shelf_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"删除工具架失败: {e}")
            return False

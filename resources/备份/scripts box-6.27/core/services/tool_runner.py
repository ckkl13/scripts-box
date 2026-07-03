# -*- coding: utf-8 -*-
import os
import sys
import shutil
import tempfile
import time
from core.qt_compat import cmds, mel


class ToolRunner:
    def __init__(self, root_dir, config_service=None):
        self.root_dir = root_dir
        self.tools_dir = os.path.join(self.root_dir, "tools")
        self.config_service = config_service

    def _find_tool_path(self, tool):
        """查找工具文件的实际路径，按优先级尝试"""
        # 1. 优先使用 tool 中的绝对路径
        path = tool.get("path")
        if path and os.path.exists(path):
            return path

        filename = tool.get("filename")
        if not filename:
            return None

        # 2. 按分组名查找（支持分组子目录递归）
        group_id = tool.get("group")
        if group_id and self.config_service:
            group_name = self.config_service.get_group_name_by_id(group_id)
            if group_name:
                group_dir = os.path.join(self.tools_dir, group_name)
                if os.path.exists(group_dir):
                    for root, dirs, files in os.walk(group_dir):
                        if filename in files:
                            return os.path.join(root, filename)

        # 3. 递归搜索整个 tools 目录
        if os.path.exists(self.tools_dir):
            for root, dirs, files in os.walk(self.tools_dir):
                if filename in files:
                    return os.path.join(root, filename)

        return None

    def run_tool(self, tool):
        tool_path = self._find_tool_path(tool)

        if not tool_path or not os.path.exists(tool_path):
            cmds.warning(f"找不到工具文件: {tool.get('name', tool.get('filename', '未知'))}")
            return

        if tool["type"] == "mel":
            mel_path = tool_path.replace('\\', '/')
            mel_basename = os.path.splitext(os.path.basename(mel_path))[0]
            mel_dir = os.path.dirname(tool_path).replace('\\', '/')
            mel_cmd = f'''
import maya.mel as mel
import maya.cmds as cmds
import os

_script_dir = r"{mel_dir}"
_original_dir = os.getcwd()
os.chdir(_script_dir)

try:
    mel.eval('source "{mel_basename}.mel"')
    try:
        mel.eval('{mel_basename}()')
    except Exception:
        pass
finally:
    os.chdir(_original_dir)
'''
            cmds.evalDeferred(mel_cmd)
        else:
            def run_python():
                try:
                    script_dir = os.path.dirname(tool_path)
                    original_dir = os.getcwd()
                    os.chdir(script_dir)

                    if script_dir not in sys.path:
                        sys.path.insert(0, script_dir)

                    with open(tool_path, 'r', encoding='utf-8') as f:
                        code = f.read()

                    exec(compile(code, tool_path, 'exec'), {
                        '__file__': tool_path,
                        '__name__': '__main__'
                    })

                    os.chdir(original_dir)

                except UnicodeDecodeError:
                    try:
                        with open(tool_path, 'r', encoding='gbk') as f:
                            code = f.read()
                        exec(compile(code, tool_path, 'exec'), {
                            '__file__': tool_path,
                            '__name__': '__main__'
                        })
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        cmds.warning(f"运行脚本出错: {str(e)}")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    cmds.warning(f"运行脚本出错: {str(e)}")

            cmds.evalDeferred(run_python)

    def extract_name_from_content(self, content, script_type):
        if script_type == "python":
            name_patterns = [
                r'#\s*名称[:：]\s*(.+)',
                r'#\s*工具名称[:：]\s*(.+)',
                r'#\s*脚本名称[:：]\s*(.+)',
                r'#\s*name[:：]\s*(.+)',
                r'#\s*tool name[:：]\s*(.+)',
                r'"""(.+?)"""',
            ]
        else:
            name_patterns = [
                r'//\s*名称[:：]\s*(.+)',
                r'//\s*工具名称[:：]\s*(.+)',
                r'//\s*脚本名称[:：]\s*(.+)',
                r'//\s*name[:：]\s*(.+)',
                r'//\s*tool name[:：]\s*(.+)'
            ]

        import re
        for pattern in name_patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1).strip()
                if name:
                    return name

        return None

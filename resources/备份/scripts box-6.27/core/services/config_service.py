# -*- coding: utf-8 -*-
import os
import json
from core.qt_compat import cmds
from core.services.tool_scanner import scan_tools_directory


class ConfigService:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.core_dir = os.path.join(root_dir, "core")
        self.config_dir = os.path.join(self.core_dir, "configuration")
        self.tools_dir = os.path.join(root_dir, "tools")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.pinned_file = os.path.join(self.config_dir, "pinned.json")
        self.groups_order_file = os.path.join(self.config_dir, "groups_order.json")
        self.config = None

    def load_config(self):
        default_config = {
            "groups": [],
            "tools": [],
            "recycle_bin": [],
            "button_layout": "single",
            "button_colors": {},
            "splitter_ratio": 0.22,
            "window_size": [950, 700]
        }

        config = scan_tools_directory(self.tools_dir)

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    old_config = json.load(f)

                if "recycle_bin" in old_config:
                    config["recycle_bin"] = old_config["recycle_bin"]
                if "button_layout" in old_config:
                    config["button_layout"] = old_config["button_layout"]
                if "button_colors" in old_config:
                    config["button_colors"] = old_config["button_colors"]
                if "splitter_ratio" in old_config:
                    config["splitter_ratio"] = old_config["splitter_ratio"]
                if "window_size" in old_config:
                    config["window_size"] = old_config["window_size"]
                if "groups_tree" in old_config:
                    config["groups_tree"] = old_config["groups_tree"]
                if "tools_tooltips" in old_config:
                    config["tools_tooltips"] = old_config["tools_tooltips"]
            except Exception as e:
                cmds.warning(f"加载配置文件失败: {str(e)}，将使用默认配置")

        self.config = config
        return config

    def save_config(self, nav_widget=None):
        config_to_save = {
            "recycle_bin": self.config["recycle_bin"],
            "button_layout": self.config["button_layout"],
            "tools_tooltips": {},
            "button_colors": self.config.get("button_colors", {}),
            "splitter_ratio": self.config.get("splitter_ratio", 0.25),
            "window_size": self.config.get("window_size", [950, 700])
        }

        for tool in self.config.get("tools", []):
            if "tooltip" in tool and tool["tooltip"]:
                config_to_save["tools_tooltips"][tool["filename"]] = tool["tooltip"]

        if nav_widget is not None:
            try:
                order_names = []
                for i in range(nav_widget.count()):
                    item = nav_widget.item(i)
                    name = item.text().split(' (')[0]
                    order_names.append(name)
                
                with open(self.groups_order_file, 'w', encoding='utf-8') as gf:
                    json.dump(order_names, gf, indent=4, ensure_ascii=False)
            except Exception as e:
                cmds.warning(f"保存分组顺序失败: {str(e)}")

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=4, ensure_ascii=False)

    def load_pinned(self):
        try:
            if os.path.exists(self.pinned_file):
                with open(self.pinned_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
        except Exception as e:
            cmds.warning(f"读取置顶文件失败: {str(e)}")
        return []

    def save_pinned(self, pinned_list):
        try:
            with open(self.pinned_file, 'w', encoding='utf-8') as f:
                json.dump(pinned_list, f, ensure_ascii=False, indent=4)
        except Exception as e:
            cmds.warning(f"保存置顶文件失败: {str(e)}")

    def get_group_name_by_id(self, group_id):
        if not group_id:
            return None

        for group in self.config.get("groups", []):
            if group["id"] == group_id:
                return group["name"]
        return None

    def get_tool_rel_path(self, tool):
        group_name = self.get_group_name_by_id(tool.get("group"))
        if not group_name:
            group_name = "default"
        return f"{group_name}/{tool.get('filename', '')}".replace("\\", "/")

    def is_tool_pinned(self, tool):
        rel = self.get_tool_rel_path(tool)
        pinned = self.load_pinned()
        norm = [p.replace("\\", "/") for p in pinned]
        return rel in norm

    def set_tool_pinned(self, tool, state):
        rel = self.get_tool_rel_path(tool)
        pinned = self.load_pinned()
        norm = [p.replace("\\", "/") for p in pinned]
        if state:
            if rel not in norm:
                pinned.append(rel)
                self.save_pinned(pinned)
                return True
        else:
            if rel in norm:
                new_pinned = [p for p in pinned if p.replace("\\", "/") != rel]
                self.save_pinned(new_pinned)
                return True
        return False

# -*- coding: utf-8 -*-
import os
import shutil
import time
from datetime import datetime
from core.qt_compat import cmds


class RecycleService:
    def __init__(self, root_dir, config_service):
        self.root_dir = root_dir
        self.config_service = config_service
        self.tools_dir = os.path.join(root_dir, "tools")
        self.recycle_dir = os.path.join(root_dir, "recycle_bin")
        self._ensure_recycle_dir()

    @property
    def config(self):
        return self.config_service.config

    def _ensure_recycle_dir(self):
        if not os.path.exists(self.recycle_dir):
            os.makedirs(self.recycle_dir)

    def get_recycle_bin_items(self):
        return self.config.get("recycle_bin", [])

    def get_recycle_count(self):
        return len(self.config.get("recycle_bin", []))

    def clear_recycle_bin(self):
        try:
            for item in self.config.get("recycle_bin", []):
                recycle_file = os.path.join(self.recycle_dir, item.get("filename", ""))
                if os.path.exists(recycle_file):
                    os.remove(recycle_file)

            self.config["recycle_bin"] = []
            self.config_service.save_config()
            return True
        except Exception as e:
            cmds.warning(f"清空回收站失败: {str(e)}")
            raise

    def restore_from_recycle_bin(self, deleted_item):
        try:
            recycle_file = os.path.join(self.recycle_dir, deleted_item.get("filename", ""))

            if not os.path.exists(recycle_file):
                raise ValueError(f"回收站中的文件不存在: {recycle_file}")

            original_group = deleted_item.get("original_group", deleted_item.get("group"))
            group_name = None
            group_exists = False

            if original_group:
                for group in self.config["groups"]:
                    if group["id"] == original_group:
                        group_name = group["name"]
                        group_exists = True
                        break

            if not group_exists:
                if self.config["groups"]:
                    original_group = self.config["groups"][0]["id"]
                    group_name = self.config["groups"][0]["name"]
                else:
                    new_group_name = "新建分组"
                    new_group_dir = os.path.join(self.tools_dir, new_group_name)

                    counter = 1
                    while os.path.exists(new_group_dir):
                        new_group_name = f"新建分组_{counter}"
                        new_group_dir = os.path.join(self.tools_dir, new_group_name)
                        counter += 1

                    os.makedirs(new_group_dir)

                    original_group = "new_default_" + str(int(time.time()))
                    new_group = {
                        "id": original_group,
                        "name": new_group_name
                    }

                    self.config["groups"].append(new_group)
                    group_name = new_group_name

            group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)

            dest_file = os.path.join(group_dir, deleted_item.get("filename", ""))

            if os.path.exists(dest_file) and recycle_file != dest_file:
                basename, ext = os.path.splitext(deleted_item.get("filename", ""))
                counter = 1
                new_filename = f"{basename}_{counter}{ext}"
                while os.path.exists(os.path.join(group_dir, new_filename)):
                    counter += 1
                    new_filename = f"{basename}_{counter}{ext}"

                dest_file = os.path.join(group_dir, new_filename)
                deleted_item["filename"] = new_filename

            shutil.copy2(recycle_file, dest_file)
            os.remove(recycle_file)

            self.config["recycle_bin"].remove(deleted_item)

            tool_info = {
                "name": deleted_item.get("name", "未命名工具"),
                "filename": deleted_item.get("filename", ""),
                "type": deleted_item.get("type", "python"),
                "group": original_group,
                "tooltip": deleted_item.get("tooltip", "")
            }

            self.config["tools"].append(tool_info)
            self.config_service.save_config()

            return tool_info
        except Exception as e:
            cmds.warning(f"恢复失败: {str(e)}")
            raise

    def permanently_delete(self, deleted_item):
        try:
            recycle_file = os.path.join(self.recycle_dir, deleted_item.get("filename", ""))

            if os.path.exists(recycle_file):
                os.remove(recycle_file)

            self.config["recycle_bin"].remove(deleted_item)
            self.config_service.save_config()
            return True
        except Exception as e:
            cmds.warning(f"删除失败: {str(e)}")
            raise

    def delete_tool(self, tool):
        try:
            group_id = tool.get("group", "default")
            group_name = "常用工具"
            for group in self.config["groups"]:
                if group["id"] == group_id:
                    group_name = group["name"]
                    break

            group_dir = os.path.join(self.tools_dir, group_name)
            tool_file = os.path.join(group_dir, tool.get("filename", ""))
            recycle_file = os.path.join(self.recycle_dir, tool.get("filename", ""))

            if not os.path.exists(tool_file):
                raise ValueError(f"工具文件不存在: {tool_file}")

            if os.path.exists(recycle_file) and tool_file != recycle_file:
                basename, ext = os.path.splitext(tool.get("filename", ""))
                counter = 1
                new_filename = f"{basename}_{counter}{ext}"
                while os.path.exists(os.path.join(self.recycle_dir, new_filename)):
                    counter += 1
                    new_filename = f"{basename}_{counter}{ext}"

                recycle_file = os.path.join(self.recycle_dir, new_filename)
                tool["filename"] = new_filename

            shutil.copy2(tool_file, recycle_file)
            os.remove(tool_file)

            self.config["tools"].remove(tool)

            tool["original_group"] = group_id
            tool["delete_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.config["recycle_bin"].append(tool)
            self.config_service.save_config()

            return tool
        except Exception as e:
            cmds.warning(f"删除失败: {str(e)}")
            raise

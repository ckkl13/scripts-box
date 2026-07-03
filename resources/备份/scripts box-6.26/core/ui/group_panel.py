# -*- coding: utf-8 -*-
"""
分组管理UI组件
处理分组的创建、删除、重命名、颜色设置、导航等功能
"""

import os
import re
import json
import time
import shutil

from core.qt_compat import *
from core.ui.widgets import DraggableGroupButton


class GroupPanel:
    """分组管理UI管理器"""
    
    def __init__(self, parent_window):
        """
        初始化分组管理UI
        
        参数:
            parent_window: 父窗口（ScriptsBox实例）
        """
        self.parent = parent_window
    
    def show_nav_context_menu(self, group, position, button):
        """显示导航按钮的右键菜单"""
        group_id = group["id"]
        
        menu = QMenu(self.parent)
        rename_action = menu.addAction("重命名")
        color_action = menu.addAction("设置颜色")
        reset_color_action = menu.addAction("重置颜色")
        menu.addSeparator()
        delete_action = menu.addAction("删除")
        
        action = menu.exec_(button.mapToGlobal(position))
        
        if action == rename_action:
            self.rename_group(group)
        elif action == color_action:
            self.set_group_color(group)
        elif action == reset_color_action:
            self.reset_group_color(group)
        elif action == delete_action:
            self.delete_group(group)
    
    def set_group_color(self, group):
        """设置分组颜色"""
        from PySide2.QtWidgets import QColorDialog
        from PySide2.QtGui import QColor
        
        group_id = group["id"]
        group_name = group["name"]
        
        # 获取当前颜色
        group_colors = self.parent.config.get("group_colors", {})
        current_color = group_colors.get(group_id, "#444444")
        
        # 弹出颜色选择对话框
        color = QColorDialog.getColor(QColor(current_color), self.parent, f"选择 '{group_name}' 的颜色")
        
        if color.isValid():
            color_hex = color.name()
            
            # 保存颜色到配置
            if "group_colors" not in self.parent.config:
                self.parent.config["group_colors"] = {}
            self.parent.config["group_colors"][group_id] = color_hex
            
            # 保存配置
            self.parent.save_config()
            
            # 更新导航按钮样式
            if group_id in self.parent.nav_buttons:
                nav_button = self.parent.nav_buttons[group_id]
                nav_button.setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        padding: 8px 12px;
                        background-color: {color_hex};
                        border: none;
                        border-radius: 6px;
                        color: #E0E0E0;
                    }}
                    QPushButton:hover {{ background-color: {self.parent.adjust_color_brightness(color_hex, 1.2)}; }}
                    QPushButton:pressed {{ background-color: {self.parent.adjust_color_brightness(color_hex, 1.4)}; }}
                """)
    
    def reset_group_color(self, group):
        """重置分组颜色为默认"""
        group_id = group["id"]
        
        # 从配置中移除颜色设置
        group_colors = self.parent.config.get("group_colors", {})
        if group_id in group_colors:
            del group_colors[group_id]
            
            # 保存配置
            self.parent.save_config()
            
            # 恢复默认样式
            if group_id in self.parent.nav_buttons:
                nav_button = self.parent.nav_buttons[group_id]
                nav_button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 8px 12px;
                        background-color: #262626;
                        border: none;
                        border-radius: 6px;
                        color: #E0E0E0;
                    }
                    QPushButton:hover { background-color: #3a3a3a; }
                    QPushButton:pressed { background-color: #1a1a1a; }
                """)
    
    def rename_group(self, group):
        """重命名组：重命名磁盘文件夹、更新 id/name/path、更新所有引用和 groups_order.json"""
        old_id = group["id"]
        old_name = group["name"]
        old_path = group.get("path", old_name)
        
        new_name, ok = QInputDialog.getText(
            self.parent, "重命名分组", "请输入新的分组名称:",
            QLineEdit.Normal, old_name
        )
        if not ok or not new_name or new_name.strip() == "" or new_name == old_name:
            return
        new_name = new_name.strip()
        if "/" in new_name or "\\" in new_name:
            cmds.warning("分组名称不能包含路径字符")
            return
        
        new_group_dir = os.path.join(self.parent.tools_dir, new_name)
        if os.path.exists(new_group_dir):
            cmds.warning(f"已存在名为 '{new_name}' 的文件夹，请换一个名称")
            return
        
        old_group_dir = os.path.join(self.parent.tools_dir, old_path)
        if not os.path.isdir(old_group_dir):
            cmds.warning(f"分组目录不存在: {old_group_dir}")
            return
        
        try:
            os.rename(old_group_dir, new_group_dir)
        except Exception as e:
            cmds.warning(f"重命名文件夹失败: {str(e)}")
            return
        
        new_id = f"group:{new_name}"
        
        # 更新 config["groups"]
        for g in self.parent.config["groups"]:
            if g["id"] == old_id:
                g["id"] = new_id
                g["name"] = new_name
                g["path"] = new_name
                break
        
        # 更新所有工具的 group 引用
        for tool in self.parent.config.get("tools", []):
            if tool.get("group") == old_id:
                tool["group"] = new_id
        
        # 更新 group_containers 的键
        if old_id in self.parent.group_containers:
            self.parent.group_containers[new_id] = self.parent.group_containers.pop(old_id)
            self.parent.group_containers[new_id]["name"] = new_name
        
        # 更新 nav_items 的键，并更新树节点文字和 UserRole
        if old_id in self.parent.nav_items:
            item = self.parent.nav_items.pop(old_id)
            item.setText(0, new_name)
            item.setData(0, Qt.UserRole, new_id)
            self.parent.nav_items[new_id] = item
        
        # 更新 nav_buttons 的键和按钮文字
        if old_id in self.parent.nav_buttons:
            btn = self.parent.nav_buttons.pop(old_id)
            count_match = re.search(r'\((\d+)\)$', btn.text())
            count_text = f" ({count_match.group(1)})" if count_match else ""
            btn.setText(f"{new_name}{count_text}")
            self.parent.nav_buttons[new_id] = btn
        
        if self.parent.active_group_id == old_id:
            self.parent.active_group_id = new_id
        if self.parent.content_title and self.parent.active_group_id == new_id:
            self.parent.content_title.setText(new_name)
        
        # 更新 groups_order.json：把旧名称替换为新名称
        try:
            if os.path.exists(self.parent.groups_order_file):
                with open(self.parent.groups_order_file, 'r', encoding='utf-8') as gf:
                    order_data = json.load(gf)
                if isinstance(order_data, list):
                    order_data = [new_name if n == old_name else n for n in order_data]
                    with open(self.parent.groups_order_file, 'w', encoding='utf-8') as gf:
                        json.dump(order_data, gf, indent=4, ensure_ascii=False)
        except Exception as e:
            cmds.warning(f"更新分组顺序文件失败: {str(e)}")
        
        self.parent.save_config()
        self.update_nav_button_counters()
        cmds.inViewMessage(message=f"已重命名为 '{new_name}'", pos='midCenter', fade=True)
    
    def delete_group(self, group):
        """删除组：将该组下所有脚本移入回收站，然后删除分组"""
        group_id = group["id"]
        group_name = group["name"]
        
        # 确认删除
        reply = QMessageBox.question(
            self.parent, "删除分组",
            f"确定要删除分组 '{group_name}' 吗？\n该分组下的所有脚本将移入回收站。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 若只剩一个分组，先新建一个空分组，避免没有分组可选
        if len(self.parent.config["groups"]) <= 1:
            new_group_name = "分组1"
            new_group_dir = os.path.join(self.parent.tools_dir, new_group_name)
            counter = 1
            while os.path.exists(new_group_dir):
                new_group_name = f"分组{counter}"
                new_group_dir = os.path.join(self.parent.tools_dir, new_group_name)
                counter += 1
            os.makedirs(new_group_dir)
            new_group_id = f"group_{int(time.time())}"
            new_group = {"id": new_group_id, "name": new_group_name}
            self.parent.config["groups"].append(new_group)
        
        group_dir = os.path.join(self.parent.tools_dir, group_name)
        # 收集本组内所有工具（用副本列表，避免遍历时修改）
        tools_in_group = [t for t in self.parent.config["tools"] if t.get("group") == group_id]
        
        for tool in tools_in_group:
            tool_file = os.path.join(group_dir, tool.get("filename", ""))
            recycle_file = os.path.join(self.parent.recycle_dir, tool.get("filename", ""))
            if not os.path.exists(tool_file):
                continue
            # 回收站内文件名冲突时重命名
            if os.path.exists(recycle_file) and tool_file != recycle_file:
                basename, ext = os.path.splitext(tool.get("filename", ""))
                n = 1
                new_filename = f"{basename}_{n}{ext}"
                while os.path.exists(os.path.join(self.parent.recycle_dir, new_filename)):
                    n += 1
                    new_filename = f"{basename}_{n}{ext}"
                recycle_file = os.path.join(self.parent.recycle_dir, new_filename)
                tool["filename"] = new_filename
            try:
                shutil.copy2(tool_file, recycle_file)
                os.remove(tool_file)
            except Exception as e:
                cmds.warning(f"移入回收站失败: {tool_file}, 错误: {str(e)}")
                continue
            tool["original_group"] = group_id
            tool["delete_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.parent.config["tools"].remove(tool)
            self.parent.config["recycle_bin"].append(tool)
        
        # 组目录内可能还有未在 config["tools"] 中的文件，一并移入回收站后删除目录
        try:
            if os.path.exists(group_dir):
                for file_name in os.listdir(group_dir):
                    path = os.path.join(group_dir, file_name)
                    if os.path.isfile(path):
                        dest = os.path.join(self.parent.recycle_dir, file_name)
                        if os.path.exists(dest):
                            basename, ext = os.path.splitext(file_name)
                            n = 1
                            dest = os.path.join(self.parent.recycle_dir, f"{basename}_{n}{ext}")
                            while os.path.exists(dest):
                                n += 1
                                dest = os.path.join(self.parent.recycle_dir, f"{basename}_{n}{ext}")
                        try:
                            shutil.copy2(path, dest)
                            os.remove(path)
                        except Exception as e:
                            cmds.warning(f"移入回收站失败: {path}, 错误: {str(e)}")
                shutil.rmtree(group_dir, ignore_errors=True)
        except Exception as e:
            cmds.warning(f"删除分组目录失败: {group_dir}, 错误: {str(e)}")
        
        self.parent.config["groups"] = [g for g in self.parent.config["groups"] if g["id"] != group_id]
        need_select_new = (self.parent.active_group_id == group_id)
        self.parent.refresh_tools()
        
        if need_select_new and self.parent.config["groups"]:
            self.parent.show_group(self.parent.config["groups"][0]["id"])
        elif self.parent.active_group_id and self.parent.active_group_id in self.parent.group_containers:
            self.parent.show_group(self.parent.active_group_id)
        
        cmds.inViewMessage(message=f"已删除分组 '{group_name}'，脚本已移入回收站", pos='midCenter', fade=True)
    
    def create_nav_button(self, group):
        """创建导航栏按钮（或树形界面下向树添加一项）"""
        group_id = group["id"]
        group_name = group["name"]
        
        # 当前界面为树形导航（无 nav_buttons_layout）时，向树添加新项即可
        if not getattr(self.parent, 'nav_buttons_layout', None):
            root = self.parent.nav_tree.invisibleRootItem()
            item = QTreeWidgetItem(root, [f"{group_name} (0)"])
            item.setData(0, Qt.UserRole, group_id)
            self.parent.nav_items[group_id] = item
            self.parent.nav_tree.expandAll()
            return None
        
        # 创建导航按钮（按钮布局模式）
        nav_button = DraggableGroupButton(group_name, group_id, self.parent)
        
        # 获取分组自定义颜色
        group_colors = self.parent.config.get("group_colors", {})
        custom_color = group_colors.get(group_id, None)
        
        if custom_color:
            # 使用自定义颜色
            nav_button.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 8px 10px;
                    background-color: {custom_color};
                    border: none;
                    border-radius: 3px;
                    margin: 2px;
                    color: #E0E0E0;
                }}
                QPushButton:hover {{
                    background-color: {self.parent.adjust_color_brightness(custom_color, 1.2)};
                }}
                QPushButton:pressed {{
                    background-color: {self.parent.adjust_color_brightness(custom_color, 1.4)};
                }}
            """)
        else:
            nav_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    background-color: #262626;
                    border: none;
                    border-radius: 6px;
                    color: #E0E0E0;
                }
                QPushButton:hover { background-color: #3a3a3a; }
                QPushButton:pressed { background-color: #1a1a1a; }
            """)
        
        # 设置上下文菜单策略
        nav_button.setContextMenuPolicy(Qt.CustomContextMenu)
        nav_button.customContextMenuRequested.connect(lambda pos, g=group: self.show_nav_context_menu(g, pos, nav_button))
        
        # 点击导航按钮显示对应组
        nav_button.clicked.connect(lambda: self.parent.show_group(group_id))
        
        # 添加到导航栏布局并存储引用
        self.parent.nav_buttons_layout.addWidget(nav_button)
        self.parent.nav_buttons[group_id] = nav_button
        
        return nav_button
    
    def update_nav_button_counters(self):
        """更新树导航项上的工具计数"""
        group_counts = {}
        for group in self.parent.config["groups"]:
            group_counts[group["id"]] = 0
        for tool in self.parent.config["tools"]:
            gid = tool.get("group")
            if gid in group_counts:
                group_counts[gid] += 1
        for gid, count in group_counts.items():
            item = self.parent.nav_items.get(gid)
            if item:
                # 仅替换显示名称，不影响UserRole
                name = None
                for g in self.parent.config["groups"]:
                    if g["id"] == gid:
                        name = g["name"]
                        break
                if name is not None:
                    item.setText(0, f"{name} ({count})")
    
    def on_nav_tree_context_menu(self, pos):
        """树导航右键菜单"""
        item = self.parent.nav_tree.itemAt(pos)
        if not item:
            return
        
        group_id = item.data(0, Qt.UserRole)
        if not group_id:
            return
        
        # 查找分组信息
        group = None
        for g in self.parent.config.get("groups", []):
            if g["id"] == group_id:
                group = g
                break
        
        if not group:
            return
        
        # 获取按钮引用（如果有）
        button = self.parent.nav_buttons.get(group_id)
        
        # 显示右键菜单
        self.show_nav_context_menu(group, pos, button or self.parent.nav_tree)
    
    def add_group(self):
        """添加新组"""
        # 弹出输入对话框
        group_name, ok = QInputDialog.getText(
            self.parent, "添加分组", "请输入分组名称:", 
            QLineEdit.Normal, ""
        )
        
        if ok and group_name:
            # 检查分组名称是否已存在
            for group in self.parent.config["groups"]:
                if group["name"] == group_name:
                    cmds.warning(f"分组名称 '{group_name}' 已存在，请使用其他名称。")
                    return
            
            # 创建分组目录
            group_dir = os.path.join(self.parent.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
            
            # 生成唯一ID
            group_id = f"group_{int(time.time())}"
            
            # 添加到配置
            new_group = {
                "name": group_name,
                "id": group_id
            }
            
            self.parent.config["groups"].append(new_group)
            
            # 保存当前选中的组ID
            current_group_id = self.parent.active_group_id
            
            # 创建组容器和导航按钮
            self.parent.create_group_container(new_group)
            self.create_nav_button(new_group)
            
            # 保持在当前选中的组，而不是跳转到新组
            if current_group_id and current_group_id in self.parent.group_containers:
                self.parent.show_group(current_group_id)
            
            cmds.inViewMessage(message=f"已创建新分组 '{group_name}'", pos='midCenter', fade=True)
    
    def scroll_to_group(self, group_id):
        """滚动到指定组"""
        self.parent.show_group(group_id)

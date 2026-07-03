# -*- coding: utf-8 -*-
"""
工具按钮管理组件
处理工具按钮的创建、编辑、右键菜单、颜色、提示等功能
"""

import os
import re
from functools import partial

from core.qt_compat import *
from core.ui.widgets import MiddleClickButton


class ToolButtonManager:
    """工具按钮UI管理器"""
    
    def __init__(self, parent_window):
        """
        初始化工具按钮管理器
        
        参数:
            parent_window: 父窗口（ScriptsBox实例）
        """
        self.parent = parent_window
    
    def create_tool_button(self, tool, group_id=None):
        """创建工具按钮，并添加到指定组"""
        button = MiddleClickButton(tool["name"])
        button.set_tool_data(tool, self.parent)
        
        # 根据脚本类型设置图标
        try:
            icons_dir = os.path.join(self.parent.root_dir, "resources", "icons")
            if tool["type"] == "mel":
                icon_path = os.path.join(icons_dir, "mel.png")
            else:
                icon_path = os.path.join(icons_dir, "python.png")
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))
                button.setIconSize(QSize(18, 18))
        except Exception:
            pass
        
        # 设置按钮样式（包括自定义颜色）
        self.apply_button_color(button, tool)
        
        # 连接点击事件
        button.clicked.connect(partial(self.run_tool, tool))
        
        # 添加右键菜单
        button.setContextMenuPolicy(Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos, btn=button, t=tool: self.show_context_menu(pos, btn, t))
        
        # 设置提示信息（如果有）
        tooltip_text = ""
        if "tooltip" in tool and tool["tooltip"]:
            tooltip_text = tool["tooltip"]
        else:
            # 不再尝试从脚本内容中提取提示信息
            # 如果没有提示信息，使用脚本名称作为默认提示
            tooltip_text = f"运行 {tool['name']} ({tool['type'].upper()})"
        
        # 确保提示文本被应用，且有适当的格式（移除类型颜色徽标）
        if tooltip_text:
            # 确定标题部分
            title = tool["name"]
            
            styled_tooltip = f"""
            <div style="
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                font-size: 13px;
                color: #EFEFEF;
                background-color: #2A2A2A;
                padding: 10px;
                border: 1px solid #444444;
                border-radius: 5px;
                max-width: 350px;
                box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.3);
            ">
                <div style="
                    font-size: 14px;
                    border-bottom: 1px solid #444444;
                    padding-bottom: 6px;
                    margin-bottom: 8px;
                ">
                    <span>{title}</span>
                </div>
                <div style="
                    white-space: pre-wrap;
                    line-height: 1.4;
                ">{tooltip_text}</div>
            </div>
            """
            button.setToolTip(styled_tooltip)
        
        # 添加到组布局
        if group_id and group_id in self.parent.group_containers:
            container = self.parent.group_containers[group_id]
            layout = container["layout"]
            layout_mode = container.get("layout_mode", "single")
            
            # 根据布局类型添加按钮
            if layout_mode == "double" and isinstance(layout, QGridLayout):
                # 获取当前行列计数
                count = layout.count()
                row = count // 2  # 整除得到行号
                col = count % 2   # 余数得到列号
                layout.addWidget(button, row, col)
            else:
                # 单列布局或默认情况
                layout.addWidget(button)
        else:
            # 如果指定的组不存在，尝试将工具添加到第一个可用分组
            if self.parent.config["groups"]:
                first_group_id = self.parent.config["groups"][0]["id"]
                if first_group_id in self.parent.group_containers:
                    container = self.parent.group_containers[first_group_id]
                    layout = container["layout"]
                    layout_mode = container.get("layout_mode", "single")
                    
                    # 根据布局类型添加按钮
                    if layout_mode == "double" and isinstance(layout, QGridLayout):
                        count = layout.count()
                        row = count // 2
                        col = count % 2
                        layout.addWidget(button, row, col)
                    else:
                        layout.addWidget(button)
                    
                    # 更新工具的组ID
                    tool["group"] = first_group_id
                    group_id = first_group_id
                else:
                    # 如果连第一个组都找不到，添加到主布局
                    self.parent.tools_layout.addWidget(button)
            else:
                # 如果没有任何分组，添加到主布局
                self.parent.tools_layout.addWidget(button)
                
        # 存储按钮引用
        self.parent.tool_buttons[button] = {
            "tool": tool,
            "group_id": group_id
        }
        
        return button
    
    def run_tool(self, tool):
        """运行工具脚本"""
        self.parent.tool_runner.run_tool(tool)
    
    def show_context_menu(self, position, button, tool):
        """显示工具按钮的右键菜单"""
        menu = QMenu(self.parent)
        
        # 编辑脚本
        edit_action = menu.addAction("编辑脚本")
        edit_action.setIcon(self.parent.style().standardIcon(QStyle.SP_FileIcon))
        
        # 设置颜色
        color_action = menu.addAction("设置颜色")
        color_action.setIcon(self.parent.style().standardIcon(QStyle.SP_ColorDialogIcon))
        
        # 重置颜色
        reset_color_action = menu.addAction("重置颜色")
        
        # 添加分隔线
        menu.addSeparator()
        
        # 移动到分组
        move_action = menu.addMenu("移动到分组")
        
        # 获取所有分组
        current_group = tool.get("group")
        for group in self.parent.config["groups"]:
            if group["id"] != current_group:
                group_action = move_action.addAction(group["name"])
        
        # 创建新分组
        create_group_action = move_action.addAction("+ 创建新分组")
        
        menu.addSeparator()
        
        # 编辑提示
        tooltip_action = menu.addAction("编辑提示")
        tooltip_action.setIcon(self.parent.style().standardIcon(QStyle.SP_MessageBoxInformation))
        
        # 打开文件夹
        folder_action = menu.addAction("打开所在文件夹")
        folder_action.setIcon(self.parent.style().standardIcon(QStyle.SP_DirIcon))
        
        # 置顶
        pinned = tool.get("pinned", False)
        if pinned:
            unpin_action = menu.addAction("取消置顶")
        else:
            pin_action = menu.addAction("置顶")
        
        menu.addSeparator()
        
        # 删除
        delete_action = menu.addAction("删除")
        delete_action.setIcon(self.parent.style().standardIcon(QStyle.SP_TrashIcon))
        
        # 显示菜单并获取选中的动作
        action = menu.exec_(button.mapToGlobal(position))
        
        if action == edit_action:
            self.parent.edit_tool(tool)
        elif action == color_action:
            self.show_color_picker(tool, button)
        elif action == reset_color_action:
            self.set_button_color(tool, button, None)
        elif action == tooltip_action:
            self.edit_tool_tooltip(tool, button)
        elif action == folder_action:
            self.open_tool_folder(tool)
        elif action == delete_action:
            self.parent.delete_tool(tool, button)
        elif action == create_group_action:
            self.parent.create_new_group(tool, button)
        elif pinned and (action == unpin_action or action == pin_action):
            self.toggle_pin(tool)
        elif not pinned and action == pin_action:
            self.toggle_pin(tool)
        elif action in [move_action.menuAction()]:
            pass  # 移动分组已在其他地方处理
        else:
            # 检查是否是移动到分组
            for group in self.parent.config["groups"]:
                if group["id"] != current_group and action.text() == group["name"]:
                    self.move_tool_to_group(tool, button, group["id"])
                    break
    
    def show_color_picker(self, tool, button):
        """显示颜色选择器"""
        from PySide2.QtWidgets import QColorDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame
        from PySide2.QtCore import Qt
        from PySide2.QtGui import QColor
        
        # 创建自定义颜色选择对话框
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("选择按钮颜色")
        dialog.setMinimumSize(400, 300)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
                font-size: 12px;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
            QFrame {
                border: 1px solid #555555;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # 标题
        title_label = QLabel(f"为 '{tool['name']}' 选择颜色")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 预设颜色区域
        preset_label = QLabel("预设颜色:")
        layout.addWidget(preset_label)
        
        preset_frame = QFrame()
        preset_layout = QGridLayout(preset_frame)
        preset_layout.setSpacing(5)
        
        # 预设颜色列表
        preset_colors = [
            ("默认", None),
            ("红色", "#FF6B6B"),
            ("橙色", "#FFB347"),
            ("黄色", "#FFD93D"),
            ("绿色", "#6BCF7F"),
            ("蓝色", "#4ECDC4"),
            ("青色", "#A8E6CF"),
            ("粉色", "#FFB6C1"),
            ("灰色", "#95A5A6")
        ]
        
        selected_color = None
        
        def create_color_button(name, color_value):
            btn = QPushButton(name)
            if color_value:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color_value};
                        color: #000000;
                        border: 2px solid #555555;
                        padding: 8px;
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #FFFFFF;
                    }}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #555555;
                        color: #FFFFFF;
                        border: 2px solid #555555;
                        padding: 8px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        border: 2px solid #FFFFFF;
                    }
                """)
            
            def on_color_selected():
                nonlocal selected_color
                selected_color = color_value
                # 应用颜色但不关闭对话框
                self.set_button_color(tool, button, selected_color)
            
            btn.clicked.connect(on_color_selected)
            return btn
        
        # 添加预设颜色按钮
        row, col = 0, 0
        for name, color_value in preset_colors:
            btn = create_color_button(name, color_value)
            preset_layout.addWidget(btn, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        layout.addWidget(preset_frame)
        
        # 自定义颜色按钮
        custom_btn = QPushButton("自定义颜色...")
        def show_custom_color():
            nonlocal selected_color
            color = QColorDialog.getColor(QColor(255, 255, 255), dialog, "选择自定义颜色")
            if color.isValid():
                selected_color = color.name()
                # 应用颜色但不关闭对话框
                self.set_button_color(tool, button, selected_color)
        
        custom_btn.clicked.connect(show_custom_color)
        layout.addWidget(custom_btn)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        dialog.exec_()
    
    def set_button_color(self, tool, button, color):
        """设置按钮颜色并保存到配置"""
        # 初始化按钮颜色配置
        if "button_colors" not in self.parent.config:
            self.parent.config["button_colors"] = {}
        
        # 使用文件名作为键
        tool_key = tool["filename"]
        
        if color is None:
            # 移除自定义颜色，使用默认颜色
            if tool_key in self.parent.config["button_colors"]:
                del self.parent.config["button_colors"][tool_key]
        else:
            # 设置自定义颜色
            self.parent.config["button_colors"][tool_key] = color
        
        # 保存配置
        self.parent.save_config()
        
        # 更新按钮样式
        self.apply_button_color(button, tool)
    
    def apply_button_color(self, button, tool):
        """应用按钮颜色"""
        # 获取自定义颜色
        custom_color = None
        if "button_colors" in self.parent.config:
            custom_color = self.parent.config["button_colors"].get(tool["filename"])
        
        # 置顶视觉标记
        pinned_border = "border-left: 8px solid #4A90E2;" if tool.get("pinned") else ""
        
        if custom_color:
            # 使用自定义颜色（文件按钮字体比全局大 2px）
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {custom_color};
                    color: #000000;
                    text-align: left;
                    padding: 10px 12px;
                    border-radius: 8px;
                    border: 1px solid #555555;
                    font-size: 17px;
                    {pinned_border}
                }}
                QPushButton:hover {{
                    background-color: {self.parent.lighten_color(custom_color)};
                    border: 1px solid #FFFFFF;
                    {pinned_border}
                }}
                QPushButton:pressed {{
                    background-color: {self.parent.darken_color(custom_color)};
                    {pinned_border}
                }}
            """)
        else:
            # 使用统一的默认颜色（文件按钮字体比全局大 2px）
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #4c4c4c;
                    color: #FFFFFF;
                    text-align: left;
                    padding: 10px 12px;
                    border-radius: 8px;
                    border: 1px solid #555555;
                    font-size: 17px;
                    {pinned_border}
                }}
                QPushButton:hover {{
                    background-color: #5a5a5a;
                    border: 1px solid #6a6a6a;
                    {pinned_border}
                }}
                QPushButton:pressed {{
                    background-color: #3e3e3e;
                    border: 1px solid #555555;
                    {pinned_border}
                }}
            """)
    
    def edit_tool_tooltip(self, tool, button):
        """编辑工具的提示信息"""
        # 获取当前提示信息
        current_tooltip = tool.get("tooltip", "")
        
        # 创建输入对话框
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("编辑提示信息")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QTextEdit {
                background-color: #2A2A2A;
                color: #E0E0E0;
                border: 1px solid #555555;
                padding: 5px;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        
        # 布局
        layout = QVBoxLayout(dialog)
        
        # 说明标签
        info_label = QLabel("输入脚本提示信息，当鼠标悬停在按钮上时将显示此信息:", dialog)
        layout.addWidget(info_label)
        
        # 提示输入框
        tooltip_edit = QTextEdit(dialog)
        tooltip_edit.setPlainText(current_tooltip)
        tooltip_edit.setAcceptRichText(False)  # 只接受纯文本
        layout.addWidget(tooltip_edit)
        
        # 说明标签
        comment_pattern_label = QLabel("也可以在脚本中使用注释设置提示，例如：", dialog)
        layout.addWidget(comment_pattern_label)
        
        if tool["type"] == "python":
            comment_example = "# 提示: 这是一个提示信息"
        else:
            comment_example = "// 提示: 这是一个提示信息"
            
        example_label = QLabel(comment_example, dialog)
        example_label.setStyleSheet("color: #8899AA; font-family: monospace;")
        layout.addWidget(example_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 保存按钮
        save_btn = QPushButton("保存", dialog)
        save_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(save_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("取消", dialog)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            # 获取新的提示信息
            new_tooltip = tooltip_edit.toPlainText().strip()
            
            # 更新提示信息
            tool["tooltip"] = new_tooltip
            
            # 保存配置
            self.parent.save_config()
            
            # 更新按钮提示
            if new_tooltip:
                title = tool["name"]
                styled_tooltip = f"""
                <div style="
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    font-size: 13px;
                    color: #EFEFEF;
                    background-color: #2A2A2A;
                    padding: 10px;
                    border: 1px solid #444444;
                    border-radius: 5px;
                    max-width: 350px;
                    box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.3);
                ">
                    <div style="
                        font-weight: bold;
                        font-size: 14px;
                        border-bottom: 1px solid #444444;
                        padding-bottom: 6px;
                        margin-bottom: 8px;
                    ">
                        <span>{title}</span>
                    </div>
                    <div style="
                        white-space: pre-wrap;
                        line-height: 1.4;
                    ">{new_tooltip}</div>
                </div>
                """
                button.setToolTip(styled_tooltip)
            else:
                title = tool["name"]
                default_tooltip = f"运行 {tool['name']}"
                
                styled_default_tooltip = f"""
                <div style="
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    font-size: 13px;
                    color: #EFEFEF;
                    background-color: #2A2A2A;
                    padding: 10px;
                    border: 1px solid #444444;
                    border-radius: 5px;
                    max-width: 350px;
                    box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.3);
                ">
                    <div style="
                        font-weight: bold;
                        font-size: 14px;
                        border-bottom: 1px solid #444444;
                        padding-bottom: 6px;
                        margin-bottom: 8px;
                    ">
                        <span>{title}</span>
                    </div>
                    <div style="
                        white-space: pre-wrap;
                        line-height: 1.4;
                    ">{default_tooltip}</div>
                </div>
                """
                button.setToolTip(styled_default_tooltip)
            
            # 显示成功消息
            status_text = "提示信息已更新" if new_tooltip else "提示信息已清空"
            cmds.inViewMessage(message=status_text, pos='midCenter', fade=True)
    
    def open_tool_folder(self, tool):
        """打开工具所在的文件夹"""
        try:
            # 获取工具文件的完整路径
            tool_path = tool.get("path", "")
            if not tool_path or not os.path.exists(tool_path):
                cmds.inViewMessage(message="无法找到文件路径", pos='midCenter', fade=True)
                return
            
            # 获取文件所在目录
            folder_path = os.path.dirname(tool_path)
            
            # 打开文件资源管理器
            if os.path.exists(folder_path):
                import subprocess
                if sys.platform == 'win32':
                    subprocess.Popen(f'explorer /select,"{tool_path}"')
                else:
                    subprocess.Popen(['xdg-open', folder_path])
            else:
                cmds.inViewMessage(message="无法找到文件所在文件夹", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"打开文件夹失败: {str(e)}")
    
    def move_tool_to_group(self, tool, button, new_group_id):
        """将工具移动到新分组"""
        if new_group_id not in self.parent.group_containers:
            return
            
        # 旧组ID
        old_group_id = tool.get("group", "default")
        
        # 如果组没变，不做任何操作
        if old_group_id == new_group_id:
            return
            
        # 查找新旧组的名称
        old_group_name = "常用工具"
        new_group_name = "常用工具"
        
        for group in self.parent.config["groups"]:
            if group["id"] == old_group_id:
                old_group_name = group["name"]
            if group["id"] == new_group_id:
                new_group_name = group["name"]
        
        # 源文件和目标文件路径
        old_group_dir = os.path.join(self.parent.tools_dir, old_group_name)
        new_group_dir = os.path.join(self.parent.tools_dir, new_group_name)
        
        # 确保目标目录存在
        if not os.path.exists(new_group_dir):
            os.makedirs(new_group_dir)
            
        # 文件路径
        source_file = os.path.join(old_group_dir, tool["filename"])
        dest_file = os.path.join(new_group_dir, tool["filename"])
        
        # 如果目标文件已存在，生成一个新的文件名
        if os.path.exists(dest_file) and source_file != dest_file:
            # 获取文件名和扩展名
            basename, ext = os.path.splitext(tool["filename"])
            
            # 生成新文件名
            counter = 1
            new_filename = f"{basename}_{counter}{ext}"
            while os.path.exists(os.path.join(new_group_dir, new_filename)):
                counter += 1
                new_filename = f"{basename}_{counter}{ext}"
                
            # 更新目标文件路径
            dest_file = os.path.join(new_group_dir, new_filename)
            
            # 更新工具文件名
            tool["filename"] = new_filename
        
        # 复制文件到新组目录
        try:
            # 读取源文件内容
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 写入目标文件
            with open(dest_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            # 删除源文件
            if os.path.exists(source_file) and source_file != dest_file:
                os.remove(source_file)
        except Exception as e:
            cmds.warning(f"移动文件失败: {str(e)}")
            return
        
        # 修改工具分组
        tool["group"] = new_group_id
        
        # 保存当前选中的组ID
        current_group_id = self.parent.active_group_id
        
        # 重新加载UI
        self.parent.refresh_tools()
        
        # 保持在当前选中的组，而不是跳转到目标组
        if current_group_id and current_group_id in self.parent.group_containers:
            self.parent.show_group(current_group_id)
        
        # 显示操作成功消息
        cmds.inViewMessage(message=f"已将工具移动到 '{new_group_name}' 组", pos='midCenter', fade=True)
    
    def toggle_pin(self, tool):
        """切换工具的置顶状态"""
        try:
            # 切换置顶状态
            is_pinned = tool.get("pinned", False)
            self.parent.set_tool_pinned(tool, not is_pinned)
            
            # 更新按钮样式
            for button, button_info in list(self.parent.tool_buttons.items()):
                if button_info.get("tool", {}).get("filename") == tool["filename"]:
                    self.apply_button_color(button, tool)
                    break
            
            # 保存配置
            self.parent.save_config()
            
            # 显示消息
            action = "取消置顶" if is_pinned else "置顶"
            cmds.inViewMessage(message=f"已{action}: {tool['name']}", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"置顶操作失败: {str(e)}")
    
    def delete_tool(self, tool, button):
        """将工具移动到回收站"""
        try:
            result = QMessageBox.question(
                self.parent,
                "删除工具",
                f"确定要将 '{tool['name']}' 移到回收站吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
                
            deleted_tool = self.parent.recycle_service.delete_tool(tool)
            
            if button in self.parent.tool_buttons:
                button_item = self.parent.tool_buttons[button]
                group_id = button_item.get("group_id")
                
                if group_id in self.parent.group_containers:
                    layout = self.parent.group_containers[group_id]["layout"]
                    
                    if isinstance(layout, QVBoxLayout) or isinstance(layout, QHBoxLayout):
                        for i in range(layout.count()):
                            if layout.itemAt(i).widget() == button:
                                layout.removeItem(layout.itemAt(i))
                                break
                    elif isinstance(layout, QGridLayout):
                        for i in range(layout.count()):
                            if layout.itemAt(i).widget() == button:
                                row, col, _, _ = layout.getItemPosition(i)
                                layout.removeItem(layout.itemAt(i))
                                break
                    
                    button.deleteLater()
                    del self.parent.tool_buttons[button]
            
            self.parent.update_nav_button_counters()
            
            recycle_count = self.parent.recycle_service.get_recycle_count()
            self.parent.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            cmds.inViewMessage(message=f"已将 '{tool['name']}' 移动到回收站", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"删除失败: {str(e)}")
            QMessageBox.critical(self.parent, "删除失败", f"删除失败: {str(e)}")

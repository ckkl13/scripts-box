# -*- coding: utf-8 -*-
"""
搜索结果UI组件
处理搜索结果的显示、创建、上下文菜单、跳转等功能
"""

import os
from functools import partial

from core.qt_compat import *


class SearchResultsUI:
    """搜索结果UI管理器"""
    
    def __init__(self, parent_window):
        """
        初始化搜索结果UI
        
        参数:
            parent_window: 父窗口（ScriptsBox实例）
        """
        self.parent = parent_window
    
    def on_search_text_changed(self, text):
        """搜索文本改变时的处理"""
        if not text.strip():
            self.parent.clear_search()
        else:
            self.perform_search()
    
    def perform_search(self):
        """执行搜索（委托给 search_service）"""
        search_text = self.parent.search_input.text().strip().lower()
        if not search_text:
            self.parent.clear_search()
            return
        
        self.clear_search_results()
        
        self.parent.search_results = self.parent.search_service.search_tools(search_text)
        
        self.show_search_results()
        self.switch_to_search_view()
    
    def clear_search(self):
        """清除搜索"""
        self.parent.search_input.clear()
        self.clear_search_results()
        self.switch_to_normal_view()
    
    def clear_search_results(self):
        """清空搜索结果容器"""
        while self.parent.search_results_layout.count():
            child = self.parent.search_results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.parent.search_results = []
    
    def show_search_results(self):
        """显示搜索结果"""
        if not self.parent.search_results:
            no_result_label = QLabel("没有找到匹配的脚本")
            no_result_label.setStyleSheet("""
                QLabel {
                    color: #999999;
                    font-size: 14px;
                    padding: 20px;
                    text-align: center;
                }
            """)
            no_result_label.setAlignment(Qt.AlignCenter)
            self.parent.search_results_layout.addWidget(no_result_label)
            return
        
        for tool in self.parent.search_results:
            result_widget = self.create_search_result_item(tool)
            self.parent.search_results_layout.addWidget(result_widget)
    
    def create_search_result_item(self, tool):
        """创建搜索结果项"""
        item_widget = QWidget()
        item_widget.setStyleSheet("""
            QWidget {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 5px;
                margin: 2px;
            }
            QWidget:hover {
                background-color: #454545;
                border-color: #666666;
            }
        """)
        
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        try:
            icons_dir = os.path.join(self.parent.root_dir, "resources", "icons")
            icon_file = "mel.png" if tool["type"] == "mel" else "python.png"
            icon_path = os.path.join(icons_dir, icon_file)
            if os.path.exists(icon_path):
                icon_pix = QPixmap(icon_path).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label = QLabel()
                icon_label.setPixmap(icon_pix)
                icon_label.setFixedSize(18, 18)
                layout.addWidget(icon_label)
        except Exception:
            pass
        
        name_label = QLabel(tool["name"])
        name_label.setStyleSheet("""
            QLabel {
                color: #EEEEEE;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        layout.addWidget(name_label)
        
        group_name = self.parent.get_group_name_by_id(tool.get("group"))
        if group_name:
            group_label = QLabel(f"分组: {group_name}")
            group_label.setStyleSheet("""
                QLabel {
                    color: #AAAAAA;
                    font-size: 12px;
                    background-color: transparent;
                    border: none;
                }
            """)
            layout.addWidget(group_label)
        
        layout.addStretch()
        
        jump_btn = QPushButton("跳转")
        jump_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B4A7D;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B5A8D;
            }
            QPushButton:pressed {
                background-color: #5B3A6D;
            }
        """)
        jump_btn.clicked.connect(partial(self.jump_to_tool, tool))
        layout.addWidget(jump_btn)
        
        run_btn = QPushButton("运行")
        run_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A6D4A;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A7D5A;
            }
            QPushButton:pressed {
                background-color: #3A5D3A;
            }
        """)
        run_btn.clicked.connect(partial(self.parent.run_tool, tool))
        layout.addWidget(run_btn)
        
        tooltip_text = tool.get("tooltip", f"运行 {tool['name']}")
        item_widget.setToolTip(tooltip_text)
        
        item_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        item_widget.customContextMenuRequested.connect(lambda pos, t=tool: self.show_search_context_menu(pos, item_widget, t))
        
        def handle_mouse_press(event):
            if event.button() == Qt.MiddleButton:
                self.parent.add_to_shelf(tool)
            else:
                QWidget.mousePressEvent(item_widget, event)
        
        item_widget.mousePressEvent = handle_mouse_press
        
        return item_widget
    
    def switch_to_search_view(self):
        """切换到搜索结果视图"""
        self.parent.is_searching = True
        
        self.parent.tool_scroll.setVisible(False)
        self.parent.recycle_bin_scroll.setVisible(False)
        
        self.parent.search_results_scroll.setVisible(True)
        
        search_text = self.parent.search_input.text().strip()
        result_count = len(self.parent.search_results)
        self.parent.content_title.setText(f"搜索结果: \"{search_text}\" ({result_count}个结果)")
    
    def switch_to_normal_view(self):
        """切换到正常视图"""
        self.parent.is_searching = False
        
        self.parent.search_results_scroll.setVisible(False)
        
        if self.parent.recycle_bin_visible:
            self.parent.recycle_bin_scroll.setVisible(True)
            self.parent.content_title.setText("回收站")
        else:
            self.parent.tool_scroll.setVisible(True)
            if self.parent.active_group_id:
                group_name = self.parent.get_group_name_by_id(self.parent.active_group_id)
                if group_name:
                    self.parent.content_title.setText(group_name)
                else:
                    self.parent.content_title.setText("工具")
            else:
                self.parent.content_title.setText("工具")
    
    def jump_to_group(self, group_id):
        """跳转到指定的脚本组"""
        if not group_id:
            return
        
        if hasattr(self.parent, 'is_searching') and self.parent.is_searching:
            search_text = self.parent.search_input.text()
            self.switch_to_normal_view()
            self.parent.search_input.setText(search_text)
            self.parent.is_searching = False
        
        self.parent.show_group(group_id)
        
        if group_id in self.parent.nav_buttons:
            for btn_id, btn in self.parent.nav_buttons.items():
                if btn_id != group_id:
                    btn.setStyleSheet(btn.styleSheet().replace("background-color: #666666;", "background-color: #444;"))
            
            current_btn = self.parent.nav_buttons[group_id]
            current_style = current_btn.styleSheet()
            if "background-color: #666666;" not in current_style:
                current_style = current_style.replace("background-color: #444;", "background-color: #666666;")
                current_btn.setStyleSheet(current_style)
    
    def jump_to_tool(self, tool):
        """从搜索结果跳转到工具并高亮该工具按钮"""
        try:
            gid = tool.get("group")
            if not gid:
                return
            self.jump_to_group(gid)
            btn = self.find_button_for_tool(tool)
            if btn:
                try:
                    self.parent.tool_scroll.ensureWidgetVisible(btn, 10, 10)
                except Exception:
                    pass
                self.highlight_tool_button(btn)
        except Exception as e:
            try:
                cmds.warning(f"跳转并高亮失败: {str(e)}")
            except:
                pass
    
    def find_button_for_tool(self, tool):
        """根据tool信息在当前按钮映射中找到对应按钮"""
        try:
            target_fn = tool.get("filename")
            target_gid = tool.get("group")
            buttons_to_remove = []
            for btn, info in list(self.parent.tool_buttons.items()):
                # 检查按钮是否还存在
                try:
                    if btn is None:
                        buttons_to_remove.append(btn)
                        continue
                    btn.objectName()  # 测试按钮是否还存在
                except RuntimeError:
                    buttons_to_remove.append(btn)
                    continue
                
                t = info.get("tool", {})
                if t.get("filename") == target_fn and t.get("group") == target_gid:
                    # 清理无效按钮
                    for b in buttons_to_remove:
                        if b in self.parent.tool_buttons:
                            del self.parent.tool_buttons[b]
                    return btn
            
            # 清理无效按钮
            for b in buttons_to_remove:
                if b in self.parent.tool_buttons:
                    del self.parent.tool_buttons[b]
        except Exception:
            pass
        return None
    
    def highlight_tool_button(self, button):
        """高亮指定按钮，直到用户点击或鼠标滑过或切换组"""
        try:
            # 首先检查按钮是否还存在
            if button is None:
                return
            
            try:
                button.objectName()  # 测试按钮是否还存在
            except RuntimeError:
                return
            
            self.clear_tool_highlight()
            self.parent._highlight_prev_btn = button
            self.parent._highlight_prev_style = button.styleSheet()
            highlight_append = """
            QPushButton {
                border: 4px solid #FFFFFF;
                background-color: #5a5a5a;
                box-shadow: 0 0 10px #FFFFFF;
            }
            QPushButton:hover {
                border: 4px solid #FFFFFF;
                background-color: #6a6a6a;
            }
            """
            button.setStyleSheet(self.parent._highlight_prev_style + "\n" + highlight_append)
            if not hasattr(button, "_orig_enterEvent"):
                button._orig_enterEvent = button.enterEvent if hasattr(button, "enterEvent") else None
            if not hasattr(button, "_orig_mousePressEvent"):
                button._orig_mousePressEvent = button.mousePressEvent if hasattr(button, "mousePressEvent") else None
            
            def _enter(ev):
                self.clear_tool_highlight()
                if callable(button._orig_enterEvent):
                    try:
                        button._orig_enterEvent(ev)
                    except Exception:
                        pass
            
            def _press(ev):
                self.clear_tool_highlight()
                if callable(button._orig_mousePressEvent):
                    try:
                        button._orig_mousePressEvent(ev)
                    except Exception:
                        pass
            
            button.enterEvent = _enter
            button.mousePressEvent = _press
        except Exception as e:
            try:
                cmds.warning(f"应用按钮高亮失败: {str(e)}")
            except:
                pass
    
    def clear_tool_highlight(self):
        """恢复被高亮按钮的原样式与事件"""
        btn = getattr(self.parent, "_highlight_prev_btn", None)
        if not btn:
            return
        try:
            # 首先检查按钮是否还存在
            try:
                btn.objectName()  # 测试按钮是否还存在
            except RuntimeError:
                self.parent._highlight_prev_btn = None
                self.parent._highlight_prev_style = ""
                return
            
            prev = getattr(self.parent, "_highlight_prev_style", "")
            btn.setStyleSheet(prev)
            if hasattr(btn, "_orig_enterEvent") and btn._orig_enterEvent is not None:
                btn.enterEvent = btn._orig_enterEvent
            if hasattr(btn, "_orig_mousePressEvent") and btn._orig_mousePressEvent is not None:
                btn.mousePressEvent = btn._orig_mousePressEvent
        except Exception:
            pass
        self.parent._highlight_prev_btn = None
        self.parent._highlight_prev_style = ""
    
    def show_search_context_menu(self, position, widget, tool):
        """显示搜索结果中脚本的右键菜单"""
        menu = QMenu(self.parent)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 25px 5px 20px;
                border: 1px solid transparent;
            }
            QMenu::item:selected {
                background-color: #3a3a3a;
                color: #ffffff;
            }
        """)

        edit_action = QAction("编辑", self.parent)
        edit_tooltip_action = QAction("编辑提示", self.parent)
        color_action = QAction("自定义颜色", self.parent)
        move_action = QAction("移动到组", self.parent)
        open_folder_action = QAction("打开文件夹", self.parent)
        delete_action = QAction("删除", self.parent)
        settings_action = QAction("设置", self.parent)

        menu.addAction(edit_action)
        menu.addAction(edit_tooltip_action)
        menu.addAction(color_action)
        
        move_menu = QMenu("移动到组", self.parent)
        move_menu.setStyleSheet(menu.styleSheet())
        
        move_actions = {}
        current_group_id = tool.get("group", "default")
        
        if self.parent.config and "groups" in self.parent.config:
            for group in self.parent.config["groups"]:
                if "id" in group and "name" in group:
                    group_id = group["id"]
                    group_name = group["name"]
                    
                    if group_id == current_group_id:
                        continue
                        
                    group_action = QAction(group_name, self.parent)
                    move_menu.addAction(group_action)
                    move_actions[group_action] = group_id
        
        move_menu.addSeparator()
        new_group_action = QAction("新建分组", self.parent)
        move_menu.addAction(new_group_action)
        
        menu.addMenu(move_menu)
        
        menu.addSeparator()
        menu.addAction(open_folder_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(settings_action)

        action = menu.exec_(widget.mapToGlobal(position))
        
        if action == delete_action:
            self.parent.delete_tool(tool, None)
            self.perform_search()
        elif action and isinstance(action, QAction) and action.text() in ("置顶", "取消置顶"):
            self.parent.toggle_pin(tool)
            self.perform_search()
        elif action == edit_action:
            self.parent.edit_tool(tool)
        elif action == edit_tooltip_action:
            self.parent.edit_tool_tooltip(tool, None)
        elif action == color_action:
            self.parent.show_color_picker(tool, None)
        elif action == open_folder_action:
            self.parent.open_tool_folder(tool)
        elif action == settings_action:
            self.parent.show_settings_dialog()
        elif action == new_group_action:
            self.parent.create_new_group(tool, None)
        elif action in move_actions:
            new_group_id = move_actions[action]
            self.parent.move_tool_to_group(tool, None, new_group_id)
            self.perform_search()

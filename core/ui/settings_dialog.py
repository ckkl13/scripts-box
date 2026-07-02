# -*- coding: utf-8 -*-
"""
设置对话框组件
处理设置对话框、配置导入导出等功能
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

from core.utils.qt_compat import *
from core.services.shelf_service import ShelfService
from core.ui.github_sync_dialog import GitHubSyncDialog


class SettingsDialog:
    """设置对话框管理器"""
    
    def __init__(self, parent_window):
        """
        初始化设置对话框
        
        参数:
            parent_window: 父窗口（ScriptsBox实例）
        """
        self.parent = parent_window
        self.dialog = None
        self.shelf_service = None
        self.maya_shelf_list = None
        self.saved_shelf_list = None
        self.github_sync_dialog = None
    
    def show_settings_dialog(self):
        """显示设置对话框"""
        # 重新导入并初始化工具架服务，确保使用最新代码
        from core.services.shelf_service import ShelfService
        data_dir = Path(self.parent.root_dir) / "data"
        self.shelf_service = ShelfService(data_dir)
        
        self.dialog = QDialog(self.parent)
        self.dialog.setWindowTitle("设置")
        self.dialog.setFixedWidth(500)
        self.dialog.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:disabled {
                background-color: #444444;
                color: #888888;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
                color: #E0E0E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QRadioButton {
                color: #E0E0E0;
            }
            QRadioButton::indicator {
                width: 15px;
                height: 15px;
            }
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #E0E0E0;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        
        # 对话框布局
        layout = QVBoxLayout(self.dialog)
        layout.setSpacing(15)
        
        # 布局设置组
        layout_group = QGroupBox("按钮布局设置")
        layout_group_layout = QVBoxLayout(layout_group)
        
        # 布局选项
        current_layout = self.parent.config.get("button_layout", "single")
        
        # 单列布局选项
        single_layout_radio = QRadioButton("单列布局")
        single_layout_radio.setChecked(current_layout == "single")
        layout_group_layout.addWidget(single_layout_radio)
        
        # 双列布局选项
        double_layout_radio = QRadioButton("双列布局")
        double_layout_radio.setChecked(current_layout == "double")
        layout_group_layout.addWidget(double_layout_radio)
        
        # 添加布局组到主布局
        layout.addWidget(layout_group)

        # 配置导入/导出组
        config_group = QGroupBox("配置管理")
        config_group_layout = QVBoxLayout(config_group)
        
        # 导出配置按钮
        export_btn = QPushButton("导出配置")
        export_btn.clicked.connect(self.export_config)
        config_group_layout.addWidget(export_btn)
        
        # 导入配置按钮
        import_btn = QPushButton("导入配置")
        import_btn.clicked.connect(self.import_config)
        config_group_layout.addWidget(import_btn)
        
        # 打开脚本目录按钮
        open_scripts_dir_btn = QPushButton("打开脚本目录")
        open_scripts_dir_btn.clicked.connect(self.open_scripts_directory)
        config_group_layout.addWidget(open_scripts_dir_btn)
        
        # GitHub 同步按钮
        github_sync_btn = QPushButton("GitHub 同步")
        github_sync_btn.clicked.connect(self.open_github_sync)
        config_group_layout.addWidget(github_sync_btn)
        
        # 添加配置组到主布局
        layout.addWidget(config_group)
        
        # 工具架管理组
        shelf_group = QGroupBox("工具架管理")
        shelf_group_layout = QVBoxLayout(shelf_group)
        
        # 显示工具架目录信息
        shelves_dir_label = QLabel()
        shelves_dir_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        shelves_dir_label.setWordWrap(True)
        shelf_group_layout.addWidget(shelves_dir_label)
        
        # 更新目录信息显示
        if self.shelf_service:
            current_version = self.shelf_service.get_current_maya_version()
            current_lang = self.shelf_service.get_current_maya_language()
            shelves_dir = self.shelf_service.get_maya_shelves_dir()
            
            if shelves_dir:
                dir_text = f"当前 Maya: 版本 {current_version or '未知'}, 语言 {current_lang}\n"
                dir_text += f"工具架目录: {shelves_dir}"
                shelves_dir_label.setText(dir_text)
            else:
                dir_text = f"当前 Maya: 版本 {current_version or '未知'}, 语言 {current_lang}\n"
                dir_text += "未找到工具架目录"
                shelves_dir_label.setText(dir_text)
        
        # 工具架列表区域 - 左右布局
        shelf_lists_layout = QHBoxLayout()
        
        # Maya 工具架列表
        maya_shelf_layout = QVBoxLayout()
        maya_shelf_label = QLabel("Maya 工具架")
        self.maya_shelf_list = QListWidget()
        self.maya_shelf_list.setSelectionMode(QListWidget.SingleSelection)
        maya_shelf_layout.addWidget(maya_shelf_label)
        maya_shelf_layout.addWidget(self.maya_shelf_list)
        
        # 中间操作按钮
        middle_btns_layout = QVBoxLayout()
        middle_btns_layout.addStretch()
        
        save_shelf_btn = QPushButton("→ 保存")
        save_shelf_btn.setToolTip("将选中的 Maya 工具架保存到本地")
        save_shelf_btn.clicked.connect(self.save_selected_maya_shelf)
        middle_btns_layout.addWidget(save_shelf_btn)
        
        load_shelf_btn = QPushButton("← 加载")
        load_shelf_btn.setToolTip("将选中的本地工具架加载到 Maya")
        load_shelf_btn.clicked.connect(self.load_selected_saved_shelf)
        middle_btns_layout.addWidget(load_shelf_btn)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.setToolTip("刷新工具架列表")
        refresh_btn.clicked.connect(self.refresh_shelf_lists)
        middle_btns_layout.addWidget(refresh_btn)
        
        middle_btns_layout.addStretch()
        
        # 已保存工具架列表
        saved_shelf_layout = QVBoxLayout()
        saved_shelf_label = QLabel("已保存工具架")
        self.saved_shelf_list = QListWidget()
        self.saved_shelf_list.setSelectionMode(QListWidget.SingleSelection)
        saved_shelf_layout.addWidget(saved_shelf_label)
        saved_shelf_layout.addWidget(self.saved_shelf_list)
        
        # 删除按钮
        delete_shelf_btn = QPushButton("删除")
        delete_shelf_btn.setToolTip("删除选中的已保存工具架")
        delete_shelf_btn.clicked.connect(self.delete_selected_saved_shelf)
        saved_shelf_layout.addWidget(delete_shelf_btn)
        
        shelf_lists_layout.addLayout(maya_shelf_layout, 1)
        shelf_lists_layout.addLayout(middle_btns_layout)
        shelf_lists_layout.addLayout(saved_shelf_layout, 1)
        
        shelf_group_layout.addLayout(shelf_lists_layout)
        
        # 添加工具架管理组到主布局
        layout.addWidget(shelf_group)
        
        # 刷新工具架列表
        self.refresh_shelf_lists()
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        # 应用按钮
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(lambda: self.apply_settings(
            single_layout_radio.isChecked()
        ))
        button_layout.addWidget(apply_btn)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.dialog.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框（非模态）
        self.dialog.show()
    
    def apply_settings(self, single_layout_selected):
        """应用设置"""
        old_layout = self.parent.config.get("button_layout", "single")
        
        new_layout = "single" if single_layout_selected else "double"
        
        if old_layout != new_layout:
            self.parent.config["button_layout"] = new_layout
            self.parent.save_config()
            self.parent.refresh_tools()
            self.dialog.accept()
            cmds.inViewMessage(message=f"已切换到{('单' if new_layout == 'single' else '双')}列按钮布局", pos='midCenter', fade=True)
    
    def open_scripts_directory(self):
        """打开脚本目录"""
        try:
            # 获取脚本目录路径
            scripts_dir = self.parent.tools_dir
            
            if not os.path.exists(scripts_dir):
                cmds.inViewMessage(message="脚本目录不存在", pos='midCenter', fade=True)
                return
            
            # 在资源管理器中打开脚本目录
            if os.name == 'nt':  # Windows
                import subprocess
                subprocess.Popen(['explorer', scripts_dir])
            else:  # macOS/Linux
                import subprocess
                if sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', scripts_dir])
                else:  # Linux
                    subprocess.Popen(['xdg-open', scripts_dir])
            
            cmds.inViewMessage(message="已打开脚本目录", pos='midCenter', fade=True)
            
        except Exception as e:
            cmds.inViewMessage(message=f"打开脚本目录失败: {str(e)}", pos='midCenter', fade=True)
    
    def export_config(self):
        """导出配置（含分组顺序、按钮/分组颜色、置顶、回收站、布局、提示信息，可选导出脚本文件）"""
        default_name = "scripts_box_config_%s.json" % datetime.now().strftime("%Y%m%d_%H%M")
        default_path = os.path.join(os.path.expanduser("~"), default_name)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "导出配置",
            default_path,
            "JSON文件 (*.json)"
        )
        
        if not file_path:
            return
        
        if not file_path.lower().endswith('.json'):
            file_path += '.json'
        
        try:
            msg_box = QMessageBox(self.parent)
            msg_box.setWindowTitle("导出配置")
            msg_box.setText("请选择导出范围：")
            msg_box.setIcon(QMessageBox.Question)
            export_config_btn = msg_box.addButton("仅导出配置", QMessageBox.ActionRole)
            export_all_btn = msg_box.addButton("导出配置和脚本文件", QMessageBox.ActionRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
            msg_box.exec_()
            
            if msg_box.clickedButton() == cancel_btn:
                return
            
            export_tools = (msg_box.clickedButton() == export_all_btn)
            
            # 分组顺序：优先从列表导航收集（名称列表，与 groups_order.json 一致）
            groups_order = []
            try:
                if getattr(self.parent, 'nav_list', None):
                    for i in range(self.parent.nav_list.count()):
                        item = self.parent.nav_list.item(i)
                        name = item.text().split(' (')[0].strip()
                        if name:
                            groups_order.append(name)
                if not groups_order and os.path.exists(self.parent.groups_order_file):
                    with open(self.parent.groups_order_file, 'r', encoding='utf-8') as gf:
                        data = json.load(gf)
                    groups_order = data if isinstance(data, list) else [n.get("name", "") for n in data if n.get("name")]
            except Exception as e:
                cmds.warning(f"读取分组顺序失败: {str(e)}")
            
            # 完整配置：回收站、布局、分组顺序、按钮颜色、分组颜色、置顶、提示信息、停靠与分隔比例
            export_config = {
                "recycle_bin": self.parent.config.get("recycle_bin", []),
                "button_layout": self.parent.config.get("button_layout", "single"),
                "groups_order": groups_order,
                "button_colors": self.parent.config.get("button_colors", {}),
                "group_colors": self.parent.config.get("group_colors", {}),
                "pinned": self.parent.load_pinned(),
                "tools_tooltips": {},
                "splitter_ratio": self.parent.config.get("splitter_ratio", 0.22),
            }
            for tool in self.parent.config.get("tools", []):
                if tool.get("tooltip"):
                    export_config["tools_tooltips"][tool["filename"]] = tool["tooltip"]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_config, f, indent=4, ensure_ascii=False)
            
            exported_files = []
            if export_tools:
                export_dir = os.path.dirname(file_path)
                tools_export_dir = os.path.join(export_dir, "tool")
                if not os.path.exists(tools_export_dir):
                    os.makedirs(tools_export_dir)
                for group in self.parent.config.get("groups", []):
                    group_name = group["name"]
                    group_dir = os.path.join(self.parent.tools_dir, group_name)
                    export_group_dir = os.path.join(tools_export_dir, group_name)
                    if not os.path.exists(export_group_dir):
                        os.makedirs(export_group_dir)
                    if os.path.exists(group_dir):
                        for file_name in os.listdir(group_dir):
                            source_file = os.path.join(group_dir, file_name)
                            if os.path.isfile(source_file) and file_name.lower().endswith(('.py', '.mel')):
                                dest_file = os.path.join(export_group_dir, file_name)
                                shutil.copy2(source_file, dest_file)
                                exported_files.append(os.path.join(group_name, file_name))
                cmds.inViewMessage(
                    message="已导出配置和 %d 个脚本文件到 %s" % (len(exported_files), export_dir),
                    pos='midCenter', fade=True
                )
            else:
                cmds.inViewMessage(message="已导出配置到 %s" % file_path, pos='midCenter', fade=True)
        
        except Exception as e:
            cmds.warning("导出失败: %s" % str(e))
            QMessageBox.critical(self.parent, "导出失败", "导出配置失败: %s" % str(e))
    
    def import_config(self):
        """从JSON文件导入配置"""
        # 获取导入文件路径
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent, "导入配置", 
            os.path.expanduser("~"),
            "JSON文件 (*.json)"
        )
        
        if not file_path or not os.path.exists(file_path):
            return
            
        try:
            # 读取配置文件
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 检查是否有相关的工具脚本文件夹
            import_dir = os.path.dirname(file_path)
            tools_folder = os.path.join(import_dir, "tool")
            has_tools_folder = os.path.exists(tools_folder) and os.path.isdir(tools_folder)
            
            # 确认导入选项
            msg_box = QMessageBox(self.parent)
            msg_box.setWindowTitle("导入配置")
            msg_box.setText("请选择导入选项:")
            msg_box.setIcon(QMessageBox.Question)
            
            # 添加导入选项
            import_config_btn = msg_box.addButton("仅导入配置", QMessageBox.ActionRole)
            import_all_btn = msg_box.addButton("导入配置和脚本文件", QMessageBox.ActionRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
            
            # 如果没有找到工具文件夹，禁用导入脚本选项
            if not has_tools_folder:
                import_all_btn.setEnabled(False)
                import_all_btn.setToolTip("未在配置文件同级目录找到 'tool' 文件夹")
            
            msg_box.exec_()
            
            # 用户选择取消
            if msg_box.clickedButton() == cancel_btn:
                return
                
            # 是否导入脚本文件
            import_tools = (msg_box.clickedButton() == import_all_btn)
            
            # 备份当前配置中的回收站信息
            recycle_bin = self.parent.config.get("recycle_bin", [])
            button_layout = self.parent.config.get("button_layout", "single")
            
            imported_tooltips = imported_config.get("tools_tooltips", {})
            
            # 导入配置
            if "button_layout" in imported_config:
                self.parent.config["button_layout"] = imported_config["button_layout"]
            if "button_colors" in imported_config:
                self.parent.config["button_colors"] = imported_config["button_colors"]
            if "group_colors" in imported_config:
                self.parent.config["group_colors"] = imported_config["group_colors"]
            if "recycle_bin" in imported_config:
                self.parent.config["recycle_bin"] = imported_config["recycle_bin"]
            if "splitter_ratio" in imported_config:
                self.parent.config["splitter_ratio"] = imported_config["splitter_ratio"]
            
            # 导入置顶列表
            imported_pinned = imported_config.get("pinned", [])
            if imported_pinned:
                self.parent.save_pinned(imported_pinned)
            
            # 导入分组顺序
            imported_groups_order = imported_config.get("groups_order", [])
            if imported_groups_order:
                with open(self.parent.groups_order_file, 'w', encoding='utf-8') as gf:
                    json.dump(imported_groups_order, gf, indent=4, ensure_ascii=False)
            
            # 导入工具提示信息
            for tool in self.parent.config.get("tools", []):
                filename = tool.get("filename")
                if filename in imported_tooltips:
                    tool["tooltip"] = imported_tooltips[filename]
            
            # 复制脚本文件
            imported_tools_count = 0
            if import_tools and has_tools_folder:
                for group_name in os.listdir(tools_folder):
                    source_group_dir = os.path.join(tools_folder, group_name)
                    if os.path.isdir(source_group_dir):
                        # 确保目标分组目录存在
                        target_group_dir = os.path.join(self.parent.tools_dir, group_name)
                        if not os.path.exists(target_group_dir):
                            os.makedirs(target_group_dir)
                        
                        # 复制脚本文件
                        for file_name in os.listdir(source_group_dir):
                            source_file = os.path.join(source_group_dir, file_name)
                            if os.path.isfile(source_file) and file_name.lower().endswith(('.py', '.mel')):
                                target_file = os.path.join(target_group_dir, file_name)
                                shutil.copy2(source_file, target_file)
                                imported_tools_count += 1
            
            # 保存配置
            self.parent.save_config()
            
            # 重新加载工具
            self.parent.refresh_tools()
            
            # 显示导入结果
            if import_tools and has_tools_folder:
                cmds.inViewMessage(message="已导入配置和 %d 个脚本文件" % imported_tools_count, pos='midCenter', fade=True)
            else:
                cmds.inViewMessage(message="已导入配置", pos='midCenter', fade=True)
            
            # 询问是否重启
            result = QMessageBox.question(
                self.parent,
                "导入完成",
                "配置已导入。是否重启脚本管理器以应用更改？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # 重新创建窗口
                self.parent.close()
                import maya.cmds
                maya.cmds.evalDeferred("from core import scripts_box; scripts_box.show_scripts_box()")
            
        except Exception as e:
            cmds.warning("导入失败: %s" % str(e))
            QMessageBox.critical(self.parent, "导入失败", "导入配置失败: %s" % str(e))
    
    def refresh_shelf_lists(self):
        """刷新工具架列表"""
        if not self.shelf_service or not self.maya_shelf_list or not self.saved_shelf_list:
            return
        
        # 刷新 Maya 工具架列表
        self.maya_shelf_list.clear()
        maya_shelves = self.shelf_service.list_maya_shelves()
        for shelf_path in maya_shelves:
            # 显示文件名和所在目录
            item_text = shelf_path.name
            self.maya_shelf_list.addItem(item_text)
        
        # 刷新已保存工具架列表
        self.saved_shelf_list.clear()
        saved_shelves = self.shelf_service.list_saved_shelves()
        for shelf_path in saved_shelves:
            self.saved_shelf_list.addItem(shelf_path.name)
    
    def save_selected_maya_shelf(self):
        """保存选中的 Maya 工具架"""
        if not self.shelf_service or not self.maya_shelf_list:
            return
        
        selected_items = self.maya_shelf_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self.dialog, "提示", "请先选择要保存的工具架")
            return
        
        shelf_name = selected_items[0].text()
        maya_shelves_dir = self.shelf_service.get_maya_shelves_dir()
        
        if not maya_shelves_dir:
            QMessageBox.warning(self.dialog, "警告", "无法找到 Maya 工具架目录")
            return
        
        shelf_path = maya_shelves_dir / shelf_name
        result = self.shelf_service.save_shelf(shelf_path)
        
        if result:
            cmds.inViewMessage(message=f"已保存工具架: {shelf_name}", pos='midCenter', fade=True)
            self.refresh_shelf_lists()
        else:
            QMessageBox.warning(self.dialog, "警告", f"保存工具架失败: {shelf_name}")
    
    def load_selected_saved_shelf(self):
        """加载选中的已保存工具架"""
        if not self.shelf_service or not self.saved_shelf_list:
            return
        
        selected_items = self.saved_shelf_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self.dialog, "提示", "请先选择要加载的工具架")
            return
        
        shelf_name = selected_items[0].text()
        
        result = QMessageBox.question(
            self.dialog,
            "确认加载",
            f"确定要加载工具架 '{shelf_name}' 到 Maya 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            if self.shelf_service.load_shelf(shelf_name):
                cmds.inViewMessage(message=f"已加载工具架: {shelf_name}", pos='midCenter', fade=True)
            else:
                QMessageBox.warning(self.dialog, "警告", f"加载工具架失败: {shelf_name}")
    
    def delete_selected_saved_shelf(self):
        """删除选中的已保存工具架"""
        if not self.shelf_service or not self.saved_shelf_list:
            return
        
        selected_items = self.saved_shelf_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self.dialog, "提示", "请先选择要删除的工具架")
            return
        
        shelf_name = selected_items[0].text()
        
        result = QMessageBox.question(
            self.dialog,
            "确认删除",
            f"确定要删除工具架 '{shelf_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            if self.shelf_service.delete_saved_shelf(shelf_name):
                cmds.inViewMessage(message=f"已删除工具架: {shelf_name}", pos='midCenter', fade=True)
                self.refresh_shelf_lists()
            else:
                QMessageBox.warning(self.dialog, "警告", f"删除工具架失败: {shelf_name}")
    
    def open_github_sync(self):
        """打开 GitHub 同步对话框"""
        # 强制重新导入模块，避免缓存问题
        import importlib
        import core.ui.github_sync_dialog
        importlib.reload(core.ui.github_sync_dialog)
        from core.ui.github_sync_dialog import GitHubSyncDialog
        
        # 获取 GitHub 配置文件路径
        config_dir = Path(self.parent.root_dir) / "core" / "utils" / "configuration"
        config_path = config_dir / "github_config.json"
        
        # 创建并显示 GitHub 同步对话框
        self.github_sync_dialog = GitHubSyncDialog(self.parent, config_path)
        self.github_sync_dialog.show_dialog()

# -*- coding: utf-8 -*-
"""
回收站UI组件
处理回收站的显示、加载、恢复、删除等功能
"""

import os
import shutil
import time
from functools import partial

from core.utils.qt_compat import *


class RecycleBinUI:
    """回收站UI管理器"""
    
    def __init__(self, parent_window):
        """
        初始化回收站UI
        
        参数:
            parent_window: 父窗口（ScriptsBox实例）
        """
        self.parent = parent_window
    
    def show_recycle_bin(self):
        """显示回收站内容"""
        # 如果正在搜索，暂时切换到正常视图显示回收站，但保持搜索文本
        if hasattr(self.parent, 'is_searching') and self.parent.is_searching:
            # 保存当前搜索文本
            search_text = self.parent.search_input.text()
            # 切换到正常视图
            self.parent.switch_to_normal_view()
            # 恢复搜索文本但不执行搜索
            self.parent.search_input.setText(search_text)
            # 标记为非搜索状态，这样用户可以看到回收站
            self.parent.is_searching = False
        
        # 隐藏搜索结果和工具区域
        if hasattr(self.parent, 'search_results_scroll'):
            self.parent.search_results_scroll.setVisible(False)
        if hasattr(self.parent, 'tool_scroll'):
            self.parent.tool_scroll.setVisible(False)
        
        # 隐藏当前显示的组
        if self.parent.active_group_id and self.parent.active_group_id in self.parent.group_containers:
            self.parent.group_containers[self.parent.active_group_id]["panel"].setVisible(False)
            
            # 重置导航按钮样式
            if self.parent.active_group_id in self.parent.nav_buttons:
                self.parent.nav_buttons[self.parent.active_group_id].setStyleSheet("""
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
        
        # 加载回收站内容
        self.load_recycle_bin()
        
        # 设置回收站可见
        self.parent.recycle_bin_scroll.setVisible(True)
        self.parent.content_title.setText("回收站")
        self.parent.recycle_bin_visible = True
        
        # 高亮回收站按钮（与选中分组一致的主色）
        self.parent.recycle_bin_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                background-color: #3A6EA5;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4A7EB5; }
            QPushButton:pressed { background-color: #2A5E95; }
        """)
        
        # 更新当前活动组ID为null，表示在回收站中
        self.parent.active_group_id = None
    
    def load_recycle_bin(self):
        """加载回收站内容"""
        # 清除当前回收站UI中的项目
        self.parent.clear_layout(self.parent.recycle_bin_layout)
        
        # 添加回收站顶部操作区域
        header_widget = QWidget()
        header_widget.setObjectName("recycleHeader")
        header_widget.setStyleSheet("""
            #recycleHeader {
                background-color: #2D2D2D;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_layout.setSpacing(10)
        
        # 添加说明文本
        desc_label = QLabel("此处显示已删除的脚本，您可以选择恢复或永久删除它们。")
        desc_label.setStyleSheet("color: #BBBBBB; font-style: italic; padding: 0px;")
        desc_label.setWordWrap(True)
        header_layout.addWidget(desc_label)
        
        # 操作按钮区域
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 5, 0, 5)
        actions_layout.setSpacing(10)
        
        # 清空回收站按钮
        clear_btn = QPushButton("清空回收站")
        clear_btn.setIcon(self.parent.style().standardIcon(QStyle.SP_TrashIcon))
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #303030;
                color: #E0E0E0;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #202020;
            }
        """)
        clear_btn.clicked.connect(self.clear_recycle_bin)
        
        # 刷新按钮
        refresh_btn = QPushButton()
        refresh_btn.setFixedSize(40, 32)
        recycle_refresh_icon = os.path.join(self.parent.icons_dir, "refresh.svg")
        if os.path.exists(recycle_refresh_icon):
            refresh_btn.setIcon(QIcon(recycle_refresh_icon))
            refresh_btn.setIconSize(QSize(20, 20))
        else:
            refresh_btn.setText("🔄")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #303030;
                color: #E0E0E0;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #202020;
            }
        """)
        refresh_btn.clicked.connect(self.load_recycle_bin)
        
        # 添加按钮到布局
        actions_layout.addWidget(refresh_btn)
        actions_layout.addStretch(1)
        actions_layout.addWidget(clear_btn)
        
        header_layout.addLayout(actions_layout)
        self.parent.recycle_bin_layout.addWidget(header_widget)
        
        # 如果回收站为空，显示一个提示信息
        if not self.parent.config.get("recycle_bin"):
            empty_widget = QWidget()
            empty_widget.setObjectName("emptyRecycleBin")
            empty_widget.setStyleSheet("""
                #emptyRecycleBin {
                    background-color: #2D2D2D;
                    border-radius: 5px;
                }
            """)
            empty_layout = QVBoxLayout(empty_widget)
            
            # 添加空回收站图标
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignCenter)
            # 获取标准图标并设置大小
            pixmap = self.parent.style().standardIcon(QStyle.SP_TrashIcon).pixmap(64, 64)
            icon_label.setPixmap(pixmap)
            empty_layout.addWidget(icon_label)
            
            # 添加文本
            empty_label = QLabel("回收站为空")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #AAAAAA; font-size: 16px; padding: 10px;")
            empty_layout.addWidget(empty_label)
            
            empty_layout.setContentsMargins(20, 30, 20, 30)
            self.parent.recycle_bin_layout.addWidget(empty_widget)
            
            # 添加底部空间
            spacer = QWidget()
            spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.parent.recycle_bin_layout.addWidget(spacer)
            return
        
        # 添加已删除项目的列表容器
        items_container = QWidget()
        items_container.setObjectName("recycleItems")
        items_container.setStyleSheet("""
            #recycleItems {
                background-color: #2D2D2D;
                border-radius: 5px;
            }
        """)
        items_layout = QVBoxLayout(items_container)
        items_layout.setContentsMargins(15, 15, 15, 15)
        items_layout.setSpacing(8)
        
        # 添加标题
        items_count = len(self.parent.config.get("recycle_bin", []))
        title_label = QLabel(f"已删除项目 ({items_count})")
        title_label.setStyleSheet("color: #CCCCCC; font-size: 14px; font-weight: bold;")
        items_layout.addWidget(title_label)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #555555; margin: 5px 0;")
        items_layout.addWidget(line)
        
        # 为每个回收站项目创建一个卡片（与全局面板风格一致）
        for deleted_item in self.parent.config["recycle_bin"]:
            item_widget = QWidget()
            item_widget.setObjectName("recycleItem")
            item_widget.setStyleSheet("""
                #recycleItem {
                    background-color: #3a3a3a;
                    border: 1px solid #444444;
                    border-radius: 6px;
                    margin: 2px 0;
                }
                #recycleItem:hover {
                    background-color: #444444;
                }
            """)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(12, 10, 12, 10)
            item_layout.setSpacing(10)
            
            # 判断是分组还是脚本
            is_group = deleted_item.get("type") == "group"
            
            # 图标
            icon_label = QLabel()
            if is_group:
                # 分组图标
                pixmap = self.parent.style().standardIcon(QStyle.SP_DirIcon).pixmap(32, 32)
                icon_label.setPixmap(pixmap)
                icon_label.setStyleSheet("background-color: #8A6D3B; border-radius: 4px; padding: 2px;")
            else:
                if deleted_item['type'] == 'python':
                    # Python脚本图标
                    pixmap = self.parent.style().standardIcon(QStyle.SP_FileIcon).pixmap(32, 32)
                    icon_label.setPixmap(pixmap)
                    icon_label.setStyleSheet("background-color: #4A6D4A; border-radius: 4px; padding: 2px;")
                else:
                    # MEL脚本图标
                    pixmap = self.parent.style().standardIcon(QStyle.SP_FileIcon).pixmap(32, 32)
                    icon_label.setPixmap(pixmap)
                    icon_label.setStyleSheet("background-color: #4D6B8A; border-radius: 4px; padding: 2px;")
            
            icon_label.setFixedSize(36, 36)
            item_layout.addWidget(icon_label)
            
            # 信息区域
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(3)
            
            # 名称
            name_label = QLabel(deleted_item["name"])
            name_label.setStyleSheet("font-weight: bold; color: #E0E0E0; font-size: 13px;")
            info_layout.addWidget(name_label)
            
            if is_group:
                # 分组的额外信息
                tool_count = len(deleted_item.get("tools", []))
                filename_label = QLabel(f"包含 {tool_count} 个脚本")
                filename_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
            else:
                # 脚本的文件名
                filename_label = QLabel(f"文件: {deleted_item.get('filename', '未知')}")
                filename_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
            info_layout.addWidget(filename_label)
            
            # 详情布局
            details_layout = QHBoxLayout()
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setSpacing(10)
            
            # 类型标签
            if is_group:
                type_badge = "分组"
                type_color = "#8A6D3B"
            else:
                type_badge = "Python" if deleted_item['type'] == 'python' else "MEL"
                type_color = "#4A6D4A" if deleted_item['type'] == 'python' else "#4D6B8A"
            type_label = QLabel(f"<span style='background-color:{type_color}; padding:2px 8px; border-radius:3px; color:white; font-size:11px;'>{type_badge}</span>")
            details_layout.addWidget(type_label)
            
            # 删除日期
            if "delete_date" in deleted_item:
                date_label = QLabel(f"删除于: {deleted_item['delete_date']}")
                date_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
                details_layout.addWidget(date_label)
            
            # 原分组信息（仅对脚本有效）
            if not is_group and "original_group" in deleted_item:
                group_id = deleted_item["original_group"]
                group_name = "默认分组"
                for group in self.parent.config["groups"]:
                    if group["id"] == group_id:
                        group_name = group["name"]
                        break
                original_group_label = QLabel(f"原分组: {group_name}")
                original_group_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
                details_layout.addWidget(original_group_label)
            
            details_layout.addStretch(1)
            info_layout.addLayout(details_layout)
            
            item_layout.addWidget(info_widget, 1)
            
            # 操作按钮区域
            buttons_widget = QWidget()
            buttons_layout = QHBoxLayout(buttons_widget)
            buttons_layout.setContentsMargins(0, 0, 0, 0)
            buttons_layout.setSpacing(6)
            
            # 恢复按钮
            restore_btn = QPushButton("恢复")
            restore_btn.setIcon(self.parent.style().standardIcon(QStyle.SP_DialogApplyButton))
            restore_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3A6EA5;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #4A7EB5; }
                QPushButton:pressed { background-color: #2A5E95; }
            """)
            if is_group:
                restore_btn.setToolTip("恢复此分组")
                restore_btn.clicked.connect(partial(self.restore_group_from_recycle_bin, deleted_item))
            else:
                restore_btn.setToolTip("恢复此脚本到原分组")
                restore_btn.clicked.connect(partial(self.restore_from_recycle_bin, deleted_item))
            buttons_layout.addWidget(restore_btn)
            
            # 永久删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.setIcon(self.parent.style().standardIcon(QStyle.SP_DialogDiscardButton))
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a83232;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #b84242; }
                QPushButton:pressed { background-color: #982222; }
            """)
            if is_group:
                delete_btn.setToolTip("永久删除此分组")
                delete_btn.clicked.connect(partial(self.permanently_delete_group, deleted_item))
            else:
                delete_btn.setToolTip("永久删除此脚本")
                delete_btn.clicked.connect(partial(self.permanently_delete, deleted_item))
            buttons_layout.addWidget(delete_btn)
            
            item_layout.addWidget(buttons_widget)
            
            # 添加到回收站容器
            items_layout.addWidget(item_widget)
        
        self.parent.recycle_bin_layout.addWidget(items_container)
        
        # 添加底部空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.parent.recycle_bin_layout.addWidget(spacer)
    
    def clear_recycle_bin(self):
        """清空回收站"""
        # 确认对话框
        result = QMessageBox.question(
            self.parent,
            "清空回收站",
            "确定要永久删除回收站中的所有项目吗？此操作无法撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
            
        try:
            # 清空回收站目录中的所有内容
            for item in self.parent.config.get("recycle_bin", []):
                if item.get("type") == "group":
                    # 删除分组文件夹
                    recycle_folder = os.path.join(self.parent.recycle_dir, item.get("folder_name", ""))
                    if os.path.exists(recycle_folder):
                        shutil.rmtree(recycle_folder, ignore_errors=True)
                else:
                    # 删除脚本文件
                    recycle_file = os.path.join(self.parent.recycle_dir, item.get("filename", ""))
                    if os.path.exists(recycle_file):
                        os.remove(recycle_file)
            
            # 清空回收站配置
            self.parent.config["recycle_bin"] = []
            
            # 保存配置
            self.parent.save_config()
            
            # 重新加载回收站
            self.load_recycle_bin()
            
            # 更新回收站按钮文本
            self.parent.recycle_bin_btn.setText(f"回收站 (0)")
            
            cmds.inViewMessage(message="回收站已清空", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"清空回收站失败: {str(e)}")
            QMessageBox.critical(self.parent, "操作失败", f"清空回收站失败: {str(e)}")
    
    def restore_group_from_recycle_bin(self, deleted_group):
        """从回收站恢复分组"""
        try:
            # 获取分组文件夹路径
            recycle_folder = os.path.join(self.parent.recycle_dir, deleted_group.get("folder_name", ""))
            
            # 确保文件夹存在
            if not os.path.exists(recycle_folder):
                raise ValueError(f"回收站中的分组文件夹不存在: {recycle_folder}")
            
            group_name = deleted_group["name"]
            
            # 检查是否有同名分组存在
            target_group_dir = os.path.join(self.parent.tools_dir, group_name)
            if os.path.exists(target_group_dir):
                counter = 1
                while os.path.exists(os.path.join(self.parent.tools_dir, f"{group_name}_{counter}")):
                    counter += 1
                group_name = f"{group_name}_{counter}"
                target_group_dir = os.path.join(self.parent.tools_dir, group_name)
            
            # 移动文件夹回工具目录
            shutil.move(recycle_folder, target_group_dir)
            
            # 重新创建分组信息
            new_group_id = deleted_group["original_group_id"]
            new_group = {
                "id": new_group_id,
                "name": group_name
            }
            
            # 检查分组 ID 是否已经存在
            group_id_exists = any(g["id"] == new_group_id for g in self.parent.config["groups"])
            if group_id_exists:
                new_group_id = f"group_{int(time.time())}"
                new_group["id"] = new_group_id
            
            # 添加分组到配置
            self.parent.config["groups"].append(new_group)
            
            # 恢复分组中的脚本
            for tool in deleted_group.get("tools", []):
                tool["group"] = new_group_id
                self.parent.config["tools"].append(tool)
            
            # 从回收站移除
            self.parent.config["recycle_bin"].remove(deleted_group)
            
            # 保存配置
            self.parent.save_config()
            
            # 刷新工具显示
            self.parent.refresh_tools()
            
            # 更新回收站按钮
            recycle_count = len(self.parent.config.get("recycle_bin", []))
            self.parent.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            # 刷新回收站显示
            self.load_recycle_bin()
            
            # 自动显示恢复的分组
            self.parent.show_group(new_group_id)
            
            cmds.inViewMessage(message=f"已恢复分组: {group_name}", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"恢复分组失败: {str(e)}")
            QMessageBox.critical(self.parent, "恢复失败", f"恢复分组失败: {str(e)}")
    
    def permanently_delete_group(self, deleted_group):
        """永久删除回收站中的分组"""
        try:
            # 确认对话框
            result = QMessageBox.question(
                self.parent,
                "永久删除",
                f"确定要永久删除分组 '{deleted_group.get('name', '未命名分组')}' 吗？此操作无法撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
            
            # 获取文件夹路径
            recycle_folder = os.path.join(self.parent.recycle_dir, deleted_group.get("folder_name", ""))
            
            # 删除文件夹
            if os.path.exists(recycle_folder):
                shutil.rmtree(recycle_folder, ignore_errors=True)
            
            # 从回收站列表中移除
            self.parent.config["recycle_bin"].remove(deleted_group)
            
            # 保存配置
            self.parent.save_config()
            
            # 更新回收站按钮
            recycle_count = len(self.parent.config.get("recycle_bin", []))
            self.parent.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            # 刷新回收站显示
            self.load_recycle_bin()
            
            cmds.inViewMessage(message=f"已永久删除分组: {deleted_group.get('name', '未命名分组')}", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"删除分组失败: {str(e)}")
            QMessageBox.critical(self.parent, "删除失败", f"删除分组失败: {str(e)}")
    
    def restore_from_recycle_bin(self, deleted_item):
        """从回收站恢复项目"""
        try:
            # 获取文件路径
            recycle_file = os.path.join(self.parent.recycle_dir, deleted_item.get("filename", ""))
            
            # 确保文件存在
            if not os.path.exists(recycle_file):
                raise ValueError(f"回收站中的文件不存在: {recycle_file}")
            
            # 确定目标组
            original_group = deleted_item.get("original_group", deleted_item.get("group"))
            
            # 检查组是否存在
            group_name = None
            group_exists = False
            
            # 查找原始组
            if original_group:
                for group in self.parent.config["groups"]:
                    if group["id"] == original_group:
                        group_name = group["name"]
                        group_exists = True
                        break
            
            # 如果组不存在，使用第一个可用组
            if not group_exists:
                if self.parent.config["groups"]:
                    original_group = self.parent.config["groups"][0]["id"]
                    group_name = self.parent.config["groups"][0]["name"]
                else:
                    # 如果没有任何分组，创建一个新分组
                    new_group_name = "新建分组"
                    new_group_dir = os.path.join(self.parent.tools_dir, new_group_name)
                    
                    # 确保目录名称唯一
                    counter = 1
                    while os.path.exists(new_group_dir):
                        new_group_name = f"新建分组_{counter}"
                        new_group_dir = os.path.join(self.parent.tools_dir, new_group_name)
                        counter += 1
                    
                    # 创建新目录
                    os.makedirs(new_group_dir)
                    
                    # 创建新分组对象
                    original_group = "new_default_" + str(int(time.time()))
                    new_group = {
                        "id": original_group,
                        "name": new_group_name
                    }
                    
                    # 添加到配置
                    self.parent.config["groups"].append(new_group)
                    group_name = new_group_name
            
            # 确保目标组目录存在
            group_dir = os.path.join(self.parent.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
            
            # 目标文件路径
            dest_file = os.path.join(group_dir, deleted_item.get("filename", ""))
            
            # 检查目标文件是否存在，如果存在则重命名
            if os.path.exists(dest_file) and recycle_file != dest_file:
                basename, ext = os.path.splitext(deleted_item.get("filename", ""))
                counter = 1
                new_filename = f"{basename}_{counter}{ext}"
                while os.path.exists(os.path.join(group_dir, new_filename)):
                    counter += 1
                    new_filename = f"{basename}_{counter}{ext}"
                
                # 更新目标文件路径和工具文件名
                dest_file = os.path.join(group_dir, new_filename)
                deleted_item["filename"] = new_filename
            
            # 复制文件到目标目录
            shutil.copy2(recycle_file, dest_file)
            
            # 从回收站删除文件
            os.remove(recycle_file)
            
            # 从回收站列表中移除
            self.parent.config["recycle_bin"].remove(deleted_item)
            
            # 重新添加到工具列表
            tool_info = {
                "name": deleted_item.get("name", "未命名工具"),
                "filename": deleted_item.get("filename", ""),
                "type": deleted_item.get("type", "python"),
                "group": original_group,
                "tooltip": deleted_item.get("tooltip", "")
            }
            
            # 保存配置
            self.parent.save_config()
            
            # 刷新工具显示
            self.parent.refresh_tools()
            
            # 更新回收站按钮
            recycle_count = len(self.parent.config.get("recycle_bin", []))
            self.parent.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            # 刷新回收站显示
            self.load_recycle_bin()
            
            cmds.inViewMessage(message=f"已恢复: {tool_info['name']}", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"恢复失败: {str(e)}")
            QMessageBox.critical(self.parent, "恢复失败", f"恢复失败: {str(e)}")
    
    def permanently_delete(self, deleted_item):
        """永久删除回收站中的项目"""
        try:
            # 确认对话框
            result = QMessageBox.question(
                self.parent,
                "永久删除",
                f"确定要永久删除 '{deleted_item.get('name', '未命名工具')}' 吗？此操作无法撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
                
            # 获取文件路径
            recycle_file = os.path.join(self.parent.recycle_dir, deleted_item.get("filename", ""))
            
            # 删除文件
            if os.path.exists(recycle_file):
                os.remove(recycle_file)
            
            # 从回收站列表中移除
            self.parent.config["recycle_bin"].remove(deleted_item)
            
            # 保存配置
            self.parent.save_config()
            
            # 更新回收站按钮
            recycle_count = len(self.parent.config.get("recycle_bin", []))
            self.parent.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            # 刷新回收站显示
            self.load_recycle_bin()
            
            cmds.inViewMessage(message=f"已永久删除: {deleted_item.get('name', '未命名工具')}", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"删除失败: {str(e)}")
            QMessageBox.critical(self.parent, "删除失败", f"删除失败: {str(e)}")

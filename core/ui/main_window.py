# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import shutil
import time
import traceback
import subprocess
from datetime import datetime
from functools import partial

from core.utils.qt_compat import *
from core.utils.color_utils import adjust_color_brightness, lighten_color, darken_color
from core.ui.widgets import DraggableGroupButton, MiddleClickButton
from core.ui.code_editor import ScriptEditor
from core.services.config_service import ConfigService
from core.services.tool_runner import ToolRunner
from core.services.search_service import SearchService
from core.services.recycle_service import RecycleService
from core.ui.recycle_bin_ui import RecycleBinUI
from core.ui.group_panel import GroupPanel
from core.ui.tool_button_manager import ToolButtonManager
from core.ui.settings_dialog import SettingsDialog
from core.ui.help_dialog import HelpDialog
from core.ui.search_results_ui import SearchResultsUI


class ScriptsBox(QDialog):
    def __init__(self, parent=maya_main_window()):
        QDialog.__init__(self, parent)
        
        # 记录Qt和Maya版本信息，用于兼容性处理
        self.qt_version = qt_version
        self.maya_version = MAYA_VERSION
        
        # 设置窗口关闭属性
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # 应用兼容性修复
        self.apply_compatibility_fixes()
        
        self.setWindowTitle("Maya 脚本管理器")
        # 窗口大小会在 load_config 之后设置
        # 移除对最小尺寸的限制，允许自由缩放
        
        # 设置窗口标志，确保关闭按钮可见
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        
        # 统一 UI 风格：配色与圆角一致
        self._style = {
            "bg_dialog": "#2b2b2b",
            "bg_nav": "#262626",
            "bg_content": "#303030",
            "bg_input": "#2f2f2f",
            "bg_btn": "#3a3a3a",
            "bg_btn_hover": "#4a4a4a",
            "bg_btn_press": "#2f2f2f",
            "border": "#3a3a3a",
            "border_input": "#444444",
            "accent": "#3A6EA5",
            "accent_hover": "#4A7EB5",
            "accent_press": "#2A5E95",
            "success": "#4A6D4A",
            "success_hover": "#5A7D5A",
            "danger": "#a83232",
            "danger_hover": "#b84242",
            "text": "#E0E0E0",
            "text_dim": "#AAAAAA",
            "scroll_track": "#2A2A2A",
            "scroll_handle": "#555555",
            "radius_panel": "8px",
            "radius_btn": "6px",
        }
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #E0E0E0;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }
            QLabel {
                color: #E0E0E0;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #E0E0E0;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2f2f2f;
            }
            QLineEdit, QComboBox {
                background-color: #2f2f2f;
                color: #E0E0E0;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 10px;
                selection-background-color: #3A6EA5;
                selection-color: #ffffff;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #3A6EA5;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #2A2A2A;
                margin: 0px;
            }
            QScrollBar:vertical { width: 10px; }
            QScrollBar:horizontal { height: 10px; }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #555555;
                min-height: 20px;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
            }
            QTreeWidget {
                background-color: transparent;
            }
            QTreeWidget::item {
                height: 24px;
                padding: 2px 4px;
            }
            QMenu {
                background-color: #303030;
                color: #E0E0E0;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3A6EA5;
            }
            QMenu::item:disabled {
                color: #777777;
            }
            QFrame {
                background-color: transparent;
            }
        """)
        
        # 设置接受拖放
        self.setAcceptDrops(True)
        
        # 添加回收站相关属性
        self.recycle_bin_visible = False
        
        # 路径计算：main_window.py 在 core/ui/ 下，往上两级是根目录（scripts box/）
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.core_dir = os.path.dirname(self.current_dir)
        self.root_dir = os.path.dirname(self.core_dir)
        # tools 目录
        self.tools_dir = os.path.join(self.root_dir, "tools")
        # 配置文件在 core/utils/configuration/ 目录下
        self.config_file = os.path.join(self.core_dir, "utils", "configuration", "config.json")
        self.pinned_file = os.path.join(self.core_dir, "utils", "configuration", "pinned.json")
        self.groups_order_file = os.path.join(self.core_dir, "utils", "configuration", "groups_order.json")
        # 回收站目录
        self.recycle_dir = os.path.join(self.root_dir, "recycle_bin")
        # 图标目录
        self.icons_dir = os.path.join(self.root_dir, "resources", "icons")
        
        # 创建工具目录（如果不存在）
        if not os.path.exists(self.tools_dir):
            os.makedirs(self.tools_dir)
            
        # 创建回收站目录（如果不存在）
        if not os.path.exists(self.recycle_dir):
            os.makedirs(self.recycle_dir)
            
        # 初始化服务层（必须在 load_config 之前）
        self.config_service = ConfigService(self.root_dir)
        self.tool_runner = ToolRunner(self.root_dir, self.config_service)
        self.search_service = SearchService(self.config_service)
        self.recycle_service = RecycleService(self.root_dir, self.config_service)

        # 初始化UI组件
        self.recycle_bin_ui = RecycleBinUI(self)
        self.group_panel = GroupPanel(self)
        self.tool_button_manager = ToolButtonManager(self)
        self.settings_dialog = SettingsDialog(self)
        self.help_dialog = HelpDialog(self)
        self.search_results_ui = SearchResultsUI(self)

        # 初始化配置
        self.config = self.load_config()
        
        # 应用保存的窗口大小
        try:
            window_size = self.config.get("window_size", [950, 700])
            if isinstance(window_size, list) and len(window_size) == 2:
                self.resize(window_size[0], window_size[1])
        except Exception as e:
            cmds.warning(f"应用窗口大小失败: {str(e)}")
            self.resize(950, 700)
        
        # 工具按钮字典，用于存储按钮引用
        self.tool_buttons = {}
        
        # 创建UI
        self.create_ui()
        
        # 加载已有工具
        self.load_tools()
        
        # 脚本编辑器实例
        self.script_editor = None
    
    
    def apply_compatibility_fixes(self):
        """应用不同版本的兼容性修复"""
        try:
            # Maya 2024+使用PySide6时的特殊处理
            if self.maya_version >= 2024 and self.qt_version == "PySide6":
                # PySide6的某些Qt信号可能需要特殊处理
                pass
                
            # Maya 2021-2023使用PySide2时的特殊处理
            elif 2021 <= self.maya_version <= 2023 and self.qt_version == "PySide2":
                pass
            
            # Maya 2025特殊处理 - 窗口关闭问题修复
            if self.maya_version >= 2025:
                # 确保窗口可以通过叉叉关闭
                self.setAttribute(Qt.WA_DeleteOnClose, True)
                
                # 调整窗口标志，确保关闭按钮可用
                flags = self.windowFlags()
                self.setWindowFlags(flags | Qt.WindowCloseButtonHint)
                
        except Exception as e:
            cmds.warning(f"应用兼容性修复时出错: {str(e)}")
            traceback.print_exc()
    
    def closeEvent(self, event):
        """重写关闭事件处理"""
        try:
            # 保存当前窗口大小
            try:
                size = self.size()
                self.config["window_size"] = [size.width(), size.height()]
                self.save_config()
            except Exception as e:
                cmds.warning(f"保存窗口大小失败: {str(e)}")
            
            # 清理资源，确保窗口能够正确关闭
            if hasattr(self, 'script_editor') and self.script_editor:
                try:
                    self.script_editor.close()
                    self.script_editor.deleteLater()
                except:
                    pass
            
            # 如果是Maya 2025+，进行特殊处理
            if self.maya_version >= 2025:
                
                # 延迟删除自身对象
                self.deleteLater()
            
            # 接受关闭事件
            event.accept()
            
        except Exception as e:
            # 如果出现错误，仍然允许窗口关闭
            cmds.warning(f"关闭窗口时出错: {str(e)}")
            event.accept()
    
    def eventFilter(self, obj, event):
        """拖放分组后保存顺序（rowsMoved 在部分 Qt 版本不触发时备用）"""
        # 检查是否是我们关心的事件
        result = False
        try:
            if obj == getattr(self, "_nav_list_viewport", None) and event.type() == QEvent.Drop:
                QTimer.singleShot(0, self.save_config)
                result = True
        except Exception:
            pass
        
        # 安全地调用父类方法
        try:
            return QDialog.eventFilter(self, obj, event)
        except Exception:
            # 如果父类调用也失败，返回我们自己的处理结果
            return result
    
    def create_ui(self):
        """创建UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 左侧导航栏区域
        nav_widget = QWidget()
        self.nav_widget = nav_widget
        nav_widget.setObjectName("navPanel")
        nav_widget.setStyleSheet("""
            #navPanel {
                background-color: #262626;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }
        """)
        nav_layout = QVBoxLayout(nav_widget)
        self.nav_layout = nav_layout
        nav_layout.setAlignment(Qt.AlignTop)
        nav_layout.setContentsMargins(5, 10, 5, 10)
        nav_layout.setSpacing(5)
        
        # 导航标题（图标+文字）
        nav_title_layout = QHBoxLayout()
        nav_title_layout.setAlignment(Qt.AlignCenter)
        nav_title_layout.setSpacing(8)
        nav_icon = QLabel()
        nav_icon_path = os.path.join(self.icons_dir, "groups.svg")
        if os.path.exists(nav_icon_path):
            nav_pixmap = QPixmap(nav_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            nav_icon.setPixmap(nav_pixmap)
        nav_title_text = QLabel("脚本分组")
        self.nav_title = nav_title_text
        nav_title_text.setStyleSheet("font-weight: bold; font-size: 16px; color: #E0E0E0;")
        nav_title_layout.addWidget(nav_icon)
        nav_title_layout.addWidget(nav_title_text)
        nav_layout.addLayout(nav_title_layout)
        
        # 添加分组按钮
        add_group_btn = QPushButton()
        add_group_btn.setFixedHeight(40)
        icon_path = os.path.join(self.icons_dir, "add_group.svg")
        if os.path.exists(icon_path):
            add_group_btn.setIcon(QIcon(icon_path))
            add_group_btn.setIconSize(QSize(24, 24))
        else:
            add_group_btn.setText("➕")
        add_group_btn.clicked.connect(self.add_group)
        add_group_btn.setStyleSheet("""
            QPushButton {
                background-color: #262626;
                color: #E0E0E0;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton:pressed { background-color: #1a1a1a; }
        """)
        nav_layout.addWidget(add_group_btn)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #3a3a3a;")
        nav_layout.addWidget(line)
        
        # 回收站按钮（与全局按钮风格一致，左对齐）
        self.recycle_bin_btn = QPushButton("回收站")
        self.recycle_bin_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                background-color: #262626;
                color: #E0E0E0;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton:pressed { background-color: #1a1a1a; }
        """)
        self.recycle_bin_btn.clicked.connect(self.show_recycle_bin)
        nav_layout.addWidget(self.recycle_bin_btn)
        
        # 分组列表（使用 QListWidget，完全不能嵌套）
        self.nav_list = QListWidget()
        self.nav_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.nav_list.setDefaultDropAction(Qt.MoveAction)
        self.nav_list.itemClicked.connect(lambda item: self.show_group(item.data(Qt.UserRole)))
        # 自动保存顺序：拖拽排序后更新 groups_order.json
        self.nav_list.model().rowsMoved.connect(lambda *args: self.save_config())
        # 拖放结束后也保存（备用）
        self.nav_list.viewport().installEventFilter(self)
        self._nav_list_viewport = self.nav_list.viewport()
        # 右键菜单
        self.nav_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.nav_list.customContextMenuRequested.connect(self.on_nav_tree_context_menu)
        nav_layout.addWidget(self.nav_list)
        
        # 存储导航项与兼容旧属性
        self.nav_items = {}
        self.nav_buttons = {}
        self.active_group_id = None
        
        # 右侧主内容区域
        content_widget = QWidget()
        self.content_widget = content_widget
        content_widget.setObjectName("contentPanel")
        content_widget.setStyleSheet("#contentPanel { background-color: #303030; border: 1px solid #3a3a3a; border-radius: 8px; }")
        content_layout = QVBoxLayout(content_widget)
        self.content_layout = content_layout
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # 顶部工具栏 
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        
        # 工具栏按钮统一样式
        toolbar_btn_style = """
            QPushButton {
                background-color: #3a3a3a;
                color: #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:pressed { background-color: #2f2f2f; }
        """
        
        # 添加脚本按钮
        add_btn = QPushButton()
        add_btn.setFixedSize(40, 32)
        new_script_icon = os.path.join(self.icons_dir, "new_script.svg")
        if os.path.exists(new_script_icon):
            add_btn.setIcon(QIcon(new_script_icon))
            add_btn.setIconSize(QSize(20, 20))
        else:
            add_btn.setText("➕")
        add_btn.setStyleSheet(toolbar_btn_style)
        add_btn.clicked.connect(self.open_script_editor)
        toolbar.addWidget(add_btn)
        
        # 刷新按钮
        refresh_btn = QPushButton()
        refresh_btn.setFixedSize(40, 32)
        refresh_icon = os.path.join(self.icons_dir, "refresh.svg")
        if os.path.exists(refresh_icon):
            refresh_btn.setIcon(QIcon(refresh_icon))
            refresh_btn.setIconSize(QSize(20, 20))
        else:
            refresh_btn.setText("🔄")
        refresh_btn.setStyleSheet(toolbar_btn_style)
        refresh_btn.clicked.connect(self.refresh_tools)
        toolbar.addWidget(refresh_btn)
        
        # 设置按钮
        settings_btn = QPushButton()
        settings_btn.setFixedSize(40, 32)
        settings_icon = os.path.join(self.icons_dir, "settings.svg")
        if os.path.exists(settings_icon):
            settings_btn.setIcon(QIcon(settings_icon))
            settings_btn.setIconSize(QSize(20, 20))
        else:
            settings_btn.setText("⚙️")
        settings_btn.setStyleSheet(toolbar_btn_style)
        settings_btn.clicked.connect(self.show_settings_dialog)
        toolbar.addWidget(settings_btn)
        
        # 搜索框
        search_label = QLabel("搜索:")
        search_label.setStyleSheet("color: #E0E0E0; margin-left: 10px;")
        toolbar.addWidget(search_label)
        
        # 创建搜索区域容器
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(5)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入脚本名称搜索...")
        self.search_input.setMinimumWidth(0)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_input)
        
        # 搜索按钮
        search_btn = QPushButton()
        search_btn.setFixedSize(40, 32)
        search_icon = os.path.join(self.icons_dir, "search.svg")
        if os.path.exists(search_icon):
            search_btn.setIcon(QIcon(search_icon))
            search_btn.setIconSize(QSize(20, 20))
        else:
            search_btn.setText("🔍")
        search_btn.setStyleSheet(toolbar_btn_style)
        search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(search_btn)
        
        # 清除搜索按钮
        clear_search_btn = QPushButton()
        clear_search_btn.setFixedSize(40, 32)
        clear_icon = os.path.join(self.icons_dir, "clear.svg")
        if os.path.exists(clear_icon):
            clear_search_btn.setIcon(QIcon(clear_icon))
            clear_search_btn.setIconSize(QSize(20, 20))
        else:
            clear_search_btn.setText("✕")
        clear_search_btn.setStyleSheet(toolbar_btn_style)
        clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_search_btn)
        
        toolbar.addWidget(search_container)
        
        # 伸缩器
        toolbar.addStretch()
        
        # 帮助按钮
        help_btn = QPushButton("?")
        help_btn.setFixedSize(32, 32)
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #E0E0E0;
                font-weight: bold;
                border-radius: 16px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:pressed { background-color: #2f2f2f; }
        """)
        help_btn.clicked.connect(self.show_help)
        toolbar.addWidget(help_btn)
        
        content_layout.addLayout(toolbar)
        
        # 右侧内容区标题
        self.content_title = QLabel("常用工具")
        self.content_title.setStyleSheet("font-weight: bold; font-size: 16px; padding: 8px; color: #E0E0E0;")
        self.content_title.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.content_title)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #3a3a3a;")
        content_layout.addWidget(line)
        
        # 创建滚动区域（滚动条样式已在全局统一）
        self.tool_scroll = QScrollArea()
        self.tool_scroll.setWidgetResizable(True)
        self.tool_scroll.setFrameShape(QFrame.NoFrame)
        self.tool_scroll.setStyleSheet("QScrollArea { background-color: transparent; }")
        
        # 工具按钮容器 - 使用 QVBoxLayout 作为主容器
        self.tools_container = QWidget()
        self.tools_container.setStyleSheet("background-color: transparent;")
        self.tools_layout = QVBoxLayout(self.tools_container)
        self.tools_layout.setAlignment(Qt.AlignTop)
        self.tools_layout.setContentsMargins(10, 10, 10, 10)
        self.tools_layout.setSpacing(8)
        
        # 用于存储各组的工具面板
        self.group_containers = {}
        
        self.tool_scroll.setWidget(self.tools_container)
        content_layout.addWidget(self.tool_scroll)
        
        # 回收站滚动区域
        self.recycle_bin_scroll = QScrollArea()
        self.recycle_bin_scroll.setWidgetResizable(True)
        self.recycle_bin_scroll.setFrameShape(QFrame.NoFrame)
        self.recycle_bin_scroll.setStyleSheet("QScrollArea { background-color: transparent; }")
        
        # 回收站容器
        self.recycle_bin_container = QWidget()
        self.recycle_bin_container.setStyleSheet("background-color: transparent;")
        self.recycle_bin_layout = QVBoxLayout(self.recycle_bin_container)
        self.recycle_bin_layout.setAlignment(Qt.AlignTop)
        self.recycle_bin_layout.setContentsMargins(10, 10, 10, 10)
        self.recycle_bin_layout.setSpacing(8)
        
        self.recycle_bin_scroll.setWidget(self.recycle_bin_container)
        self.recycle_bin_scroll.setVisible(False)
        content_layout.addWidget(self.recycle_bin_scroll)
        
        # 搜索结果滚动区域
        self.search_results_scroll = QScrollArea()
        self.search_results_scroll.setWidgetResizable(True)
        self.search_results_scroll.setFrameShape(QFrame.NoFrame)
        self.search_results_scroll.setStyleSheet("QScrollArea { background-color: transparent; }")
        self.search_results_scroll.setVisible(False)
        
        # 搜索结果容器
        self.search_results_container = QWidget()
        self.search_results_container.setStyleSheet("background-color: transparent;")
        self.search_results_layout = QVBoxLayout(self.search_results_container)
        self.search_results_layout.setAlignment(Qt.AlignTop)
        self.search_results_layout.setContentsMargins(10, 10, 10, 10)
        self.search_results_layout.setSpacing(8)
        
        self.search_results_scroll.setWidget(self.search_results_container)
        content_layout.addWidget(self.search_results_scroll)
        
        # 搜索相关属性
        self.is_searching = False
        self.search_results = []
        
        # 使用分隔条(QSplitter)添加左侧导航栏和右侧内容区域
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(nav_widget)
        self.main_splitter.addWidget(content_widget)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        # 设置更小的最小宽度，便于整体窗口缩小
        self.nav_widget.setMinimumWidth(80)
        self.content_widget.setMinimumWidth(160)
        # 保存用户拖动分隔条的位置
        self.main_splitter.splitterMoved.connect(self.on_splitter_moved)
        main_layout.addWidget(self.main_splitter)
        # 根据保存的比例设置初始宽度
        QTimer.singleShot(0, self.apply_splitter_ratio)

    def apply_splitter_ratio(self):
        try:
            ratio = float(self.config.get("splitter_ratio", 0.25))
            w = max(1, self.main_splitter.width())
            left = max(60, int(w * ratio))
            right = max(120, w - left)
            self.main_splitter.setSizes([left, right])
        except Exception:
            pass

    def on_splitter_moved(self, pos, index):
        try:
            w = float(max(1, self.main_splitter.width()))
            ratio = max(0.05, min(0.8, pos / w))
            self.config["splitter_ratio"] = ratio
            self.save_config()
        except Exception:
            pass
    
    def load_config(self):
        """加载配置文件（委托给 config_service）"""
        self.config = self.config_service.load_config()
        return self.config
    

    def scan_tools_directory(self):
        """扫描工具目录：仅识别 tool 下直接子文件夹作为分组，分组内只识别 .py 和 .mel 文件（不嵌套）"""
        config = {
            "groups": [],
            "tools": [],
            "recycle_bin": [],
            "button_layout": "single",
            "button_colors": {},
            "window_size": [950, 700]
        }
        
        try:
            if not os.path.exists(self.tools_dir):
                os.makedirs(self.tools_dir)
            
            # 只遍历 tool 下的直接子文件夹，不递归嵌套
            for name in sorted(os.listdir(self.tools_dir)):
                abs_dir = os.path.join(self.tools_dir, name)
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
                self.scan_group_directory(abs_dir, group_id, config)
            
            if not config["groups"]:
                new_group_name = "新建分组"
                new_group_dir = os.path.join(self.tools_dir, new_group_name)
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
    
    def scan_group_directory(self, group_path, group_id, config):
        """扫描分组目录中的脚本文件"""
        try:
            for file_name in os.listdir(group_path):
                file_path = os.path.join(group_path, file_name)
                
                # 只处理文件，跳过子目录
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(file_name)
                    ext = ext.lower()
                    
                    # 仅处理.py和.mel文件
                    if ext in ['.py', '.mel']:
                        script_type = "python" if ext == ".py" else "mel"
                        
                        # 读取文件内容
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
                        
                        # 直接使用文件名作为脚本名称
                        script_name = os.path.splitext(file_name)[0]
                            
                        # 创建工具信息
                        tool_info = {
                            "name": script_name,
                            "filename": file_name,
                            "type": script_type,
                            "group": group_id,
                            "path": file_path
                        }
                        
                        # 不再自动提取提示信息
                            
                        # 添加到工具列表
                        config["tools"].append(tool_info)
        except Exception as e:
            cmds.warning(f"扫描分组目录失败: {group_path}, 错误: {str(e)}")
    
    def save_config(self):
        """保存配置到文件（委托给 config_service）"""
        # 先同步 config，确保两个地方一致
        if hasattr(self, 'config_service') and hasattr(self, 'config'):
            self.config_service.config = self.config
        if hasattr(self, 'nav_list'):
            self.config_service.save_config(self.nav_list)
        else:
            self.config_service.save_config()
    
    def load_pinned(self):
        """加载置顶列表（委托给 config_service）"""
        return self.config_service.load_pinned()
    

    def save_pinned(self, pinned_list):
        """保存置顶列表（委托给 config_service）"""
        self.config_service.save_pinned(pinned_list)
    

    def get_tool_rel_path(self, tool):
        """获取工具相对路径标识（委托给 config_service）"""
        return self.config_service.get_tool_rel_path(tool)
    

    def is_tool_pinned(self, tool):
        """判断工具是否置顶（委托给 config_service）"""
        return self.config_service.is_tool_pinned(tool)
    

    def set_tool_pinned(self, tool, state):
        """设置工具置顶状态（委托给 config_service）"""
        return self.config_service.set_tool_pinned(tool, state)
    

    def load_tools(self, keep_current_group=False):
        """从文件夹结构加载工具按钮，按组分类
        
        参数:
            keep_current_group (bool): 是否保持在当前选中的组
        """
        # 保存当前选中的组
        current_group_id = self.active_group_id if keep_current_group else None

        # 重新扫描工具目录
        self.config = self.scan_tools_directory()
        
        # 读取置顶列表
        pinned_list = self.load_pinned()
        pinned_order = {p.replace("\\", "/"): idx for idx, p in enumerate(pinned_list)}
        
        # 保存已保存的提示信息的临时变量
        saved_tooltips = {}
        
        # 保存分组顺序的临时变量
        groups_order = []
        groups_order_names = []
        
        # 如果存在config.json，读取回收站和按钮布局信息
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    
                # 更新回收站和布局设置
                if "recycle_bin" in saved_config:
                    self.config["recycle_bin"] = saved_config["recycle_bin"]
                if "button_layout" in saved_config:
                    self.config["button_layout"] = saved_config["button_layout"]
                if "button_colors" in saved_config:
                    self.config["button_colors"] = saved_config["button_colors"]
                if "splitter_ratio" in saved_config:
                    self.config["splitter_ratio"] = saved_config["splitter_ratio"]
                if "window_size" in saved_config:
                    self.config["window_size"] = saved_config["window_size"]
                # 重要：读取 groups_tree 嵌套结构
                if "groups_tree" in saved_config:
                    self.config["groups_tree"] = saved_config["groups_tree"]
                
                # 读取保存的工具提示信息
                if "tools_tooltips" in saved_config:
                    saved_tooltips = saved_config["tools_tooltips"]
                    
                # 读取保存的分组顺序
                if "groups_order" in saved_config:
                    groups_order = saved_config["groups_order"]
            except Exception as e:
                cmds.warning(f"加载配置文件失败: {str(e)}")
        
        # 读取基于名称的分组顺序JSON（支持纯名称列表或 [{"name": "xx"}, ...]）
        try:
            if os.path.exists(self.groups_order_file):
                with open(self.groups_order_file, 'r', encoding='utf-8') as gf:
                    data = json.load(gf)
                    if isinstance(data, list) and data:
                        if isinstance(data[0], dict):
                            groups_order_names = [n.get("name", "") for n in data if n.get("name")]
                        else:
                            groups_order_names = data
        except Exception as e:
            cmds.warning(f"读取分组名称顺序失败: {str(e)}")
        
        # 使用名称顺序优先生成ID顺序
        if groups_order_names:
            name_to_id = {g["name"]: g["id"] for g in self.config["groups"]}
            ordered_ids = []
            for name in groups_order_names:
                gid = name_to_id.get(name)
                if gid:
                    ordered_ids.append(gid)
            # 追加未在名称顺序中的新组
            existing = set(ordered_ids)
            for g in self.config["groups"]:
                if g["id"] not in existing:
                    ordered_ids.append(g["id"])
            groups_order = ordered_ids
        
        # 为工具打上置顶标记并排序（置顶优先，置顶按pinned.json顺序）
        for tool in self.config["tools"]:
            tool["pinned"] = self.is_tool_pinned(tool)
        def _rank(tool):
            rel = self.get_tool_rel_path(tool)
            return (0 if tool.get("pinned") else 1, pinned_order.get(rel, 10**9), tool.get("name", "").lower())
        self.config["tools"].sort(key=_rank)
        
        # 清除现有按钮和组容器
        for i in reversed(range(self.tools_layout.count())):
            widget = self.tools_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 清除列表导航
        self.nav_list.clear()
        
        self.group_containers = {}
        self.nav_items = {}
        
        # 确保至少有一个分组
        if not self.config.get("groups"):
            # 创建一个新的分组
            new_group_name = "分组1"
            new_group_id = f"group_{int(time.time())}"
            self.config["groups"] = [{
                "name": new_group_name,
                "id": new_group_id
            }]
            
            # 创建分组目录
            new_group_dir = os.path.join(self.tools_dir, new_group_name)
            if not os.path.exists(new_group_dir):
                os.makedirs(new_group_dir)
        
        # 创建所有组的容器
        for group in self.config["groups"]:
            self.create_group_container(group)
        
        # 构建树形导航（从 groups_order.json 读取）
        def read_order_tree():
            try:
                if os.path.exists(self.groups_order_file):
                    with open(self.groups_order_file, 'r', encoding='utf-8') as gf:
                        data = json.load(gf)
                        if isinstance(data, list) and data:
                            return [{"name": n} for n in data]
            except Exception as e:
                cmds.warning(f"读取分组顺序失败: {str(e)}")
            return []
        
        order_tree = read_order_tree()
        
        # 按名称排序
        self.config["groups"].sort(key=lambda x: x["name"].lower())
        
        # 添加到列表中
        for node in order_tree:
            name = node.get("name")
            group = next((x for x in self.config["groups"] if x["name"] == name), None)
            if group:
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, group["id"])
                self.nav_list.addItem(item)
                self.nav_items[group["id"]] = item
        
        # 添加剩余未在顺序中的分组
        for group in self.config["groups"]:
            if group["id"] not in self.nav_items:
                item = QListWidgetItem(group["name"])
                item.setData(Qt.UserRole, group["id"])
                self.nav_list.addItem(item)
                self.nav_items[group["id"]] = item
        
        # 首次运行或缺少名称顺序时，按当前列表顺序写入 groups_order.json
        try:
            if not os.path.exists(self.groups_order_file):
                current_names = []
                for i in range(self.nav_list.count()):
                    item = self.nav_list.item(i)
                    name = item.text().split(' (')[0]
                    current_names.append(name)
                if current_names:
                    with open(self.groups_order_file, 'w', encoding='utf-8') as gf:
                        json.dump(current_names, gf, indent=4, ensure_ascii=False)
        except Exception as e:
            cmds.warning(f"初始化分组顺序失败: {str(e)}")
        
        # 应用保存的提示信息到工具
        for tool in self.config["tools"]:
            # 从保存的提示信息中查找并应用
            if tool["filename"] in saved_tooltips:
                tool["tooltip"] = saved_tooltips[tool["filename"]]
            
            # 获取工具所属的分组ID
            group_id = tool.get("group", None)
            
            # 如果工具没有指定组或其组不存在，将其添加到第一个可用分组
            if group_id not in self.group_containers:
                if self.config["groups"]:
                    group_id = self.config["groups"][0]["id"]
                    tool["group"] = group_id
            
            # 创建按钮并添加到对应的组
            if group_id:
                self.create_tool_button(tool, group_id)
        
        # 更新导航项的工具计数
        self.update_nav_button_counters()
        
        # 更新回收站按钮文本
        recycle_count = len(self.config.get("recycle_bin", []))
        self.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
        
        # 同步 config 到 config_service
        if hasattr(self, 'config_service'):
            self.config_service.config = self.config
        
        # 决定显示哪个组
        if current_group_id and current_group_id in self.group_containers:
            # 保持在当前选中的组
            self.show_group(current_group_id)
        elif self.config["groups"]:
            # 显示第一个组
            # 优先使用列表中的第一个可见项
            first = self.nav_list.item(0)
            gid = first.data(Qt.UserRole) if first else self.config["groups"][0]["id"]
            self.show_group(gid)
    
    def create_group_container(self, group):
        """创建组容器"""
        group_id = group["id"]
        group_name = group["name"]
        
        # 创建组容器面板
        group_panel = QWidget()
        group_panel.setVisible(False)  # 初始不可见
        
        # 获取当前布局模式
        layout_mode = self.config.get("button_layout", "single")
        
        # 根据布局模式选择布局类型
        if layout_mode == "double":
            # 双列布局 - 使用QGridLayout
            group_layout = QGridLayout(group_panel)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(3)
            group_layout.setAlignment(Qt.AlignTop)
        else:
            # 单列布局 - 使用QVBoxLayout
            group_layout = QVBoxLayout(group_panel)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(3)
            group_layout.setAlignment(Qt.AlignTop)
        
        # 存储组引用和布局模式
        self.group_containers[group_id] = {
            "panel": group_panel,
            "layout": group_layout,
            "name": group_name,
            "layout_mode": layout_mode
        }
        
        # 设置拖放接受
        group_panel.setAcceptDrops(True)
        
        # 添加自定义拖放事件处理
        original_dragEnterEvent = group_panel.dragEnterEvent
        original_dropEvent = group_panel.dropEvent
        
        def custom_dragEnterEvent(event, gid=group_id):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            elif hasattr(original_dragEnterEvent, '__call__'):
                original_dragEnterEvent(event)
        
        def custom_dropEvent(event, gid=group_id):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    file_path = url.toLocalFile()
                    self.process_dropped_file(file_path, gid)
                event.acceptProposedAction()
            elif hasattr(original_dropEvent, '__call__'):
                original_dropEvent(event)
        
        group_panel.dragEnterEvent = custom_dragEnterEvent
        group_panel.dropEvent = custom_dropEvent
        
        # 添加到主布局
        self.tools_layout.addWidget(group_panel)
        
        return group_panel
    
    def show_group(self, group_id):
        """显示指定组的内容"""
        # 切换组时清除搜索高亮
        self.clear_tool_highlight()
        # 注释掉自动清除搜索状态的逻辑，让用户手动控制
        # if hasattr(self, 'is_searching') and self.is_searching:
        #     self.clear_search()
        
        # 隐藏回收站和搜索结果，显示工具区域
        self.recycle_bin_scroll.setVisible(False)
        if hasattr(self, 'search_results_container'):
            self.search_results_scroll.setVisible(False)
        if hasattr(self, 'tool_scroll'):
            self.tool_scroll.setVisible(True)
        self.recycle_bin_visible = False
        self.recycle_bin_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                background-color: #262626;
                color: #E0E0E0;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton:pressed { background-color: #1a1a1a; }
        """)
        
        # 隐藏当前显示的组
        if self.active_group_id and self.active_group_id in self.group_containers:
            self.group_containers[self.active_group_id]["panel"].setVisible(False)
            
            # 重置导航按钮样式（与全局按钮一致）
            if self.active_group_id in self.nav_buttons:
                self.nav_buttons[self.active_group_id].setStyleSheet("""
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
        
        # 显示新选择的组
        if group_id in self.group_containers:
            self.group_containers[group_id]["panel"].setVisible(True)
            self.content_title.setText(self.group_containers[group_id]["name"])
            
            # 高亮当前导航按钮（主色）
            if group_id in self.nav_buttons:
                self.nav_buttons[group_id].setStyleSheet("""
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
            
            # 更新当前活动组ID
            self.active_group_id = group_id
    
    def show_nav_context_menu(self, group, position, button):
        """show_nav_context_menu 代理方法"""
        self.group_panel.show_nav_context_menu(group, position, button)
    def set_group_color(self, group):
        """set_group_color 代理方法"""
        self.group_panel.set_group_color(group)
    def reset_group_color(self, group):
        """reset_group_color 代理方法"""
        self.group_panel.reset_group_color(group)
    def rename_group(self, group):
        """rename_group 代理方法"""
        self.group_panel.rename_group(group)
    def delete_group(self, group):
        """delete_group 代理方法"""
        self.group_panel.delete_group(group)
    def show_recycle_bin(self):
        """show_recycle_bin 代理方法"""
        self.recycle_bin_ui.show_recycle_bin()
    def load_recycle_bin(self):
        """load_recycle_bin 代理方法"""
        self.recycle_bin_ui.load_recycle_bin()
    def clear_layout(self, layout):
        """清除布局中的所有控件"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())
    
    def clear_recycle_bin(self):
        """clear_recycle_bin 代理方法"""
        self.recycle_bin_ui.clear_recycle_bin()
    def restore_from_recycle_bin(self, deleted_item):
        """restore_from_recycle_bin 代理方法"""
        self.recycle_bin_ui.restore_from_recycle_bin(deleted_item)
    def permanently_delete(self, deleted_item):
        """permanently_delete 代理方法"""
        self.recycle_bin_ui.permanently_delete(deleted_item)
    def delete_tool(self, tool, button):
        """delete_tool 代理方法"""
        self.tool_button_manager.delete_tool(tool, button)
    def create_nav_button(self, group):
        """create_nav_button 代理方法"""
        return self.group_panel.create_nav_button(group)
    def adjust_color_brightness(self, color, factor):
        """调整颜色亮度（使用 color_utils 工具函数）"""
        return adjust_color_brightness(color, factor)
    

    def update_nav_button_counters(self):
        """update_nav_button_counters 代理方法"""
        self.group_panel.update_nav_button_counters()
    def on_nav_tree_context_menu(self, pos):
        """on_nav_tree_context_menu 代理方法"""
        self.group_panel.on_nav_tree_context_menu(pos)
    def create_tool_button(self, tool, group_id=None):
        """create_tool_button 代理方法"""
        return self.tool_button_manager.create_tool_button(tool, group_id)
    def run_tool(self, tool):
        """run_tool 代理方法"""
        self.tool_button_manager.run_tool(tool)
    def extract_name_from_content(self, content, script_type):
        """从文件内容中提取名称"""
        # 尝试查找注释中的名称
        if script_type == "python":
            # 查找Python文件中的名称
            name_patterns = [
                r'#\s*名称[:：]\s*(.+)',
                r'#\s*工具名称[:：]\s*(.+)',
                r'#\s*脚本名称[:：]\s*(.+)',
                r'#\s*name[:：]\s*(.+)',
                r'#\s*tool name[:：]\s*(.+)',
                r'"""(.+?)"""'
            ]
        else:
            # 查找MEL文件中的名称
            name_patterns = [
                r'//\s*名称[:：]\s*(.+)',
                r'//\s*工具名称[:：]\s*(.+)',
                r'//\s*脚本名称[:：]\s*(.+)',
                r'//\s*name[:：]\s*(.+)',
                r'//\s*tool name[:：]\s*(.+)'
            ]
        
        # 尝试每个模式
        for pattern in name_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def show_context_menu(self, position, button, tool):
        """show_context_menu 代理方法"""
        self.tool_button_manager.show_context_menu(position, button, tool)
    def show_color_picker(self, tool, button):
        """show_color_picker 代理方法"""
        self.tool_button_manager.show_color_picker(tool, button)
    def set_button_color(self, tool, button, color):
        """set_button_color 代理方法"""
        self.tool_button_manager.set_button_color(tool, button, color)
    def apply_button_color(self, button, tool):
        """apply_button_color 代理方法"""
        self.tool_button_manager.apply_button_color(button, tool)
    def lighten_color(self, color_hex):
        """使颜色变亮（使用 color_utils 工具函数）"""
        return lighten_color(color_hex)
    

    def darken_color(self, color_hex):
        """使颜色变暗（使用 color_utils 工具函数）"""
        return darken_color(color_hex)
    

    def edit_tool_tooltip(self, tool, button):
        """edit_tool_tooltip 代理方法"""
        self.tool_button_manager.edit_tool_tooltip(tool, button)
    def open_tool_folder(self, tool):
        """open_tool_folder 代理方法"""
        self.tool_button_manager.open_tool_folder(tool)
    def move_tool_to_group(self, tool, button, new_group_id):
        """move_tool_to_group 代理方法"""
        self.tool_button_manager.move_tool_to_group(tool, button, new_group_id)
    def create_new_group(self, tool=None, button=None):
        """创建新分组并可选移动工具到这个分组"""
        # 创建输入对话框
        group_name, ok = QInputDialog.getText(
            self, 
            "新建分组", 
            "请输入分组名称:",
            QLineEdit.Normal, 
            ""
        )
        
        if ok and group_name.strip():
            group_name = group_name.strip()
            
            # 检查分组名称是否已存在
            for group in self.config["groups"]:
                if group["name"] == group_name:
                    cmds.warning(f"分组名称 '{group_name}' 已存在，请使用其他名称。")
                    return
            
            # 创建新分组ID
            group_id = f"group_{int(time.time())}_{len(self.config['groups'])}"
            
            # 添加新分组
            new_group = {
                "id": group_id,
                "name": group_name
            }
            
            # 创建分组目录
            new_group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(new_group_dir):
                os.makedirs(new_group_dir)
            
            self.config["groups"].append(new_group)
            
            # 保存当前选中的组ID
            current_group_id = self.active_group_id
            
            # 刷新UI以添加新分组
            self.refresh_tools()
            
            # 如果提供了工具和按钮，则移动工具到新分组
            if tool and button:
                self.move_tool_to_group(tool, button, group_id)
            else:
                # 保持在当前选中的组，而不是跳转到新组
                if current_group_id and current_group_id in self.group_containers:
                    self.show_group(current_group_id)
            
            cmds.inViewMessage(message=f"已创建新分组 '{group_name}'", pos='midCenter', fade=True)
    
    def edit_tool(self, tool):
        """编辑工具"""
        # 查找工具所在组
        group_id = tool.get("group")
        if not group_id:
            cmds.warning(f"工具没有指定分组: {tool['name']}")
            return
            
        group_name = None
        for group in self.config["groups"]:
            if group["id"] == group_id:
                group_name = group["name"]
                break
                
        if not group_name:
            cmds.warning(f"找不到工具所属分组: {tool['name']}")
            return
        
        # 获取组目录
        group_dir = os.path.join(self.tools_dir, group_name)
        tool_path = os.path.join(group_dir, tool["filename"])
        
        # 如果在组目录中找不到文件，尝试在工具根目录查找（兼容旧版本）
        if not os.path.exists(tool_path):
            old_path = os.path.join(self.tools_dir, tool["filename"])
            if os.path.exists(old_path):
                # 找到文件，复制到正确的组目录
                try:
                    # 确保组目录存在
                    if not os.path.exists(group_dir):
                        os.makedirs(group_dir)
                    
                    # 复制文件到正确位置
                    shutil.copy2(old_path, tool_path)
                    cmds.warning(f"文件已从旧位置移动到分组目录: {old_path} -> {tool_path}")
                except Exception as e:
                    cmds.warning(f"移动文件失败: {str(e)}")
                    # 使用旧路径继续操作
                    tool_path = old_path
            else:
                cmds.warning(f"找不到工具文件: {tool_path}")
                cmds.warning(f"尝试在旧位置查找也未找到: {old_path}")
                # 尝试在所有组目录中查找该文件
                found = False
                for search_group in self.config["groups"]:
                    search_group_name = search_group["name"]
                    search_dir = os.path.join(self.tools_dir, search_group_name)
                    search_path = os.path.join(search_dir, tool["filename"])
                    if os.path.exists(search_path):
                        tool_path = search_path
                        tool["group"] = search_group["id"]
                        cmds.warning(f"在组 '{search_group_name}' 中找到工具文件，已更新工具分组")
                        found = True
                        break
                
                if not found:
                    # 尝试找到文件名相似的文件
                    basename, ext = os.path.splitext(tool["filename"])
                    found_similar = False
                    similar_files = []
                    
                    # 搜索所有分组目录
                    for search_group in self.config["groups"]:
                        search_group_name = search_group["name"]
                        search_dir = os.path.join(self.tools_dir, search_group_name)
                        if os.path.exists(search_dir):
                            for file_name in os.listdir(search_dir):
                                file_basename, file_ext = os.path.splitext(file_name)
                                # 检查文件类型是否匹配
                                if file_ext.lower() == ext.lower():
                                    # 检查文件名是否相似 (包含关系或开头相似)
                                    if basename.lower() in file_basename.lower() or file_basename.lower().startswith(basename.lower()):
                                        similar_path = os.path.join(search_dir, file_name)
                                        similar_files.append({
                                            "path": similar_path,
                                            "name": file_name,
                                            "group_id": search_group["id"],
                                            "group_name": search_group_name
                                        })
                    
                    if similar_files:
                        # 找到了相似文件，使用第一个
                        similar = similar_files[0]
                        tool_path = similar["path"]
                        tool["filename"] = similar["name"]
                        tool["group"] = similar["group_id"]
                        cmds.warning(f"找到相似文件: {similar['name']} (在 {similar['group_name']} 分组中)，将使用此文件")
                        found_similar = True
                    
                    if not found_similar:
                        cmds.warning(f"在所有分组中都找不到工具文件或相似文件: {tool['filename']}")
                        QMessageBox.critical(self, "文件未找到", f"无法找到工具文件: {tool['filename']}\n请检查文件是否已被删除或移动。")
                        return
        
        # 读取文件内容
        script_content = ""
        try:
            # 尝试不同编码读取文件
            try:
                with open(tool_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(tool_path, 'r', encoding='gbk') as f:
                        script_content = f.read()
                except UnicodeDecodeError:
                    with open(tool_path, 'r', encoding='latin-1') as f:
                        script_content = f.read()
        except Exception as e:
            cmds.warning(f"无法读取文件: {tool_path}，错误: {str(e)}")
            QMessageBox.critical(self, "读取错误", f"无法读取文件: {tool_path}\n错误: {str(e)}")
            return
        
        # 打开脚本编辑器
        self.open_script_editor(
            script_content=script_content,
            script_type=tool["type"],
            script_name=tool["name"],
            edit_mode=True,
            filename=tool["filename"]
        )
    
    def open_script_editor(self, script_content="", script_type="python", script_name="", edit_mode=False, filename=""):
        """打开脚本编辑器"""
        # 关闭之前的编辑器（如果存在）
        if self.script_editor:
            try:
                self.script_editor.close()
                self.script_editor.deleteLater()
            except:
                pass
        
        # 提取提示信息
        tooltip = ""
        if edit_mode and filename:
            # 存储当前编辑文件名以便回调使用
            self.script_editor_filename = filename
            # 查找工具配置中的提示
            for tool in self.config["tools"]:
                if tool["filename"] == filename:
                    tooltip = tool.get("tooltip", "")
                    break
            
            # 不再尝试从内容中提取提示信息
        
        # 创建回调函数
        def save_callback(name, content, type, is_edit):
            # 获取提示信息
            tooltip = self.script_editor.tooltip_edit.toPlainText().strip()
            print(f"保存脚本: {name}, 编辑模式: {is_edit}")
            print(f"脚本中包含提示信息: {tooltip}")
            
            if is_edit:
                # 编辑现有脚本，找到对应的工具
                for tool in self.config["tools"]:
                    if tool["filename"] == filename:
                        # 保存提示信息
                        if tooltip:
                            tool["tooltip"] = tooltip
                        elif "tooltip" in tool:
                            # 如果用户清空了提示，删除提示字段
                            del tool["tooltip"]
                        break
                # 保存配置
                self.save_config()
                # 更新工具
                return self.update_tool(filename, name, content, type)
            else:
                # 创建新脚本，使用当前选中的组
                result = self.create_new_tool(name, content, type, target_group_id=self.active_group_id)
                # 如果创建成功且有提示信息，添加到工具
                if result and tooltip:
                    # 查找刚创建的工具
                    for tool in self.config["tools"]:
                        if tool["name"] == name and tool["type"] == type:
                            tool["tooltip"] = tooltip
                            # 保存配置
                            self.save_config()
                            break
                return result
        
        # 创建新编辑器
        self.script_editor = ScriptEditor(
            self,
            script_content=script_content,
            script_type=script_type,
            script_name=script_name,
            edit_mode=edit_mode,
            callback=save_callback,
            tooltip=tooltip
        )
        
        # 显示编辑器
        self.script_editor.show()
    
    def update_tool(self, filename, name, content, script_type):
        """更新工具脚本"""
        try:
            # 查找工具所在的组
            tool_info = None
            group_id = None
            for tool in self.config["tools"]:
                if tool["filename"] == filename:
                    tool_info = tool
                    group_id = tool.get("group")
                    break
            
            if not tool_info:
                cmds.warning(f"找不到要更新的工具: {filename}")
                return False
                
            if not group_id:
                cmds.warning(f"工具没有指定分组: {name}")
                return False
                
            # 获取组名称
            group_name = None
            for group in self.config["groups"]:
                if group["id"] == group_id:
                    group_name = group["name"]
                    break
                    
            if not group_name:
                cmds.warning(f"找不到工具所属分组: {name}")
                return False
                
            # 获取组目录路径
            group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
                
            # 原始文件路径
            original_file_path = os.path.join(group_dir, filename)
            
            # 如果名称发生变化，生成新的文件名
            if name != tool_info["name"]:
                # 获取扩展名
                suffix = ".py" if script_type == "python" else ".mel"
                
                # 使用新名称生成文件名
                clean_name = re.sub(r'[\\/*?:"<>|]', '_', name)  # 替换Windows非法文件名字符
                clean_name = clean_name.strip()  # 移除前后空格
                
                # 确保文件名唯一
                base_filename = clean_name
                new_filename = f"{base_filename}{suffix}"
                counter = 1
                while os.path.exists(os.path.join(group_dir, new_filename)) and new_filename != filename:
                    new_filename = f"{base_filename}_{counter}{suffix}"
                    counter += 1
            else:
                # 名称没变，保持原文件名
                new_filename = filename
            
            # 安全保存文件 - 使用临时文件方式，避免权限问题
            def safe_save(file_path, content_data):
                """安全保存文件，使用临时文件方式"""
                import tempfile
                temp_dir = os.path.dirname(file_path)
                # 创建临时文件
                fd, temp_path = tempfile.mkstemp(suffix='.tmp', dir=temp_dir)
                try:
                    # 写入临时文件
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        f.write(content_data)
                    # 如果目标文件存在，先删除（Windows上需要）
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            # 如果删除失败，尝试重命名原文件为备份
                            backup_path = file_path + '.bak'
                            if os.path.exists(backup_path):
                                os.remove(backup_path)
                            os.rename(file_path, backup_path)
                    # 重命名临时文件为目标文件
                    os.rename(temp_path, file_path)
                    return True
                except Exception as e:
                    # 清理临时文件
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except:
                        pass
                    raise e
            
            # 如果文件名发生变化，需要重命名文件
            if new_filename != filename:
                new_file_path = os.path.join(group_dir, new_filename)
                # 删除可能的同名文件(不太可能，因为我们已经避免了冲突)
                if os.path.exists(new_file_path):
                    os.remove(new_file_path)
                # 使用安全方式保存
                safe_save(new_file_path, content)
                # 删除旧文件
                if os.path.exists(original_file_path) and original_file_path != new_file_path:
                    try:
                        os.remove(original_file_path)
                    except:
                        pass  # 忽略删除旧文件的错误
            else:
                # 文件名没变，只更新内容
                safe_save(original_file_path, content)
            
            # 更新工具配置信息
            tool_info["name"] = name
            # 如果文件名发生变化，更新filename字段
            if new_filename != filename:
                tool_info["filename"] = new_filename
                
                # 同时更新button_colors中的键名以保持颜色设置
                if "button_colors" in self.config and filename in self.config["button_colors"]:
                    # 保存原有颜色
                    color = self.config["button_colors"][filename]
                    # 删除旧键
                    del self.config["button_colors"][filename]
                    # 添加新键
                    self.config["button_colors"][new_filename] = color
            
            # 保存配置
            self.save_config()
            
            # 重新加载工具
            self.refresh_tools()
            
            return True
        except Exception as e:
            cmds.warning(f"更新脚本失败: {str(e)}")
            return False
    
    def create_new_tool(self, name, content, script_type, target_group_id=None):
        """创建新工具脚本
        
        参数:
            name (str): 工具名称
            content (str): 脚本内容
            script_type (str): 脚本类型，"python"或"mel"
            target_group_id (str, optional): 目标组ID，如果为None则使用当前选中的组
        """
        try:
            # 生成文件名
            suffix = ".py" if script_type == "python" else ".mel"
            
            # 使用脚本名称作为文件名（移除非法字符）
            clean_name = re.sub(r'[\\/*?:"<>|]', '_', name)  # 替换Windows非法文件名字符
            clean_name = clean_name.strip()  # 移除前后空格
            
            # 确定目标分组ID和名称
            group_id = target_group_id
            group_name = None
            
            # 如果未指定目标分组或找不到目标分组，使用当前选中分组或第一个可用分组
            if not group_id or group_id not in [g["id"] for g in self.config["groups"]]:
                # 尝试使用当前选中的分组
                if self.active_group_id and self.active_group_id in [g["id"] for g in self.config["groups"]]:
                    group_id = self.active_group_id
                # 或者使用第一个可用分组
                elif self.config["groups"]:
                    group_id = self.config["groups"][0]["id"]
                # 如果没有分组，创建一个新分组
                else:
                    new_group_name = "新建分组"
                    new_group_dir = os.path.join(self.tools_dir, new_group_name)
                    
                    # 确保目录名称唯一
                    counter = 1
                    while os.path.exists(new_group_dir):
                        new_group_name = f"新建分组_{counter}"
                        new_group_dir = os.path.join(self.tools_dir, new_group_name)
                        counter += 1
                    
                    # 创建新目录
                    os.makedirs(new_group_dir)
                    
                    # 创建新分组对象
                    group_id = "new_default_" + str(int(time.time()))
                    new_group = {
                        "id": group_id,
                        "name": new_group_name
                    }
                    
                    # 添加到配置
                    self.config["groups"].append(new_group)
                    group_name = new_group_name
            
            # 查找目标组名称
            if not group_name:
                for group in self.config["groups"]:
                    if group["id"] == group_id:
                        group_name = group["name"]
                        break
            
            # 如果仍找不到组名称，出错返回
            if not group_name:
                cmds.warning(f"无法确定目标分组，创建工具失败")
                return False
            
            # 获取组目录路径
            group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
            
            # 确保文件名唯一
            base_filename = clean_name
            filename = f"{base_filename}{suffix}"
            counter = 1
            while os.path.exists(os.path.join(group_dir, filename)):
                filename = f"{base_filename}_{counter}{suffix}"
                counter += 1
            
            # 安全保存文件 - 使用临时文件方式
            def safe_save(file_path, content_data):
                """安全保存文件，使用临时文件方式"""
                import tempfile
                temp_dir = os.path.dirname(file_path)
                # 创建临时文件
                fd, temp_path = tempfile.mkstemp(suffix='.tmp', dir=temp_dir)
                try:
                    # 写入临时文件
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        f.write(content_data)
                    # 如果目标文件存在，先删除（Windows上需要）
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            # 如果删除失败，尝试重命名原文件为备份
                            backup_path = file_path + '.bak'
                            if os.path.exists(backup_path):
                                os.remove(backup_path)
                            os.rename(file_path, backup_path)
                    # 重命名临时文件为目标文件
                    os.rename(temp_path, file_path)
                    return True
                except Exception as e:
                    # 清理临时文件
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except:
                        pass
                    raise e
            
            # 保存文件
            file_path = os.path.join(group_dir, filename)
            safe_save(file_path, content)
            
            # 添加到配置
            tool_info = {
                "name": name,  # 保存原始名称
                "filename": filename,
                "type": script_type,
                "group": group_id
            }
            
            # 注意：提示信息将由save_callback方法设置，不在此处添加
            
            # 添加工具到配置中
            if "tools" not in self.config:
                self.config["tools"] = []
            self.config["tools"].append(tool_info)
            
            # 重新加载工具
            self.refresh_tools()
            
            return True
        except Exception as e:
            cmds.warning(f"创建脚本失败: {str(e)}")
            return False
    
    def refresh_tools(self):
        """刷新工具列表，重新扫描工具目录"""
        # 保存当前状态 - 是否在回收站中
        was_in_recycle_bin = self.recycle_bin_visible
        
        # 保存当前选中的组
        current_group_id = self.active_group_id
        
        # 保存当前选中组的名称（以防ID变化但名称相同）
        current_group_name = None
        if current_group_id and current_group_id in self.group_containers:
            current_group_name = self.group_containers[current_group_id]["name"]
        
        # 保存回收站和布局设置以及工具提示信息
        recycle_bin = self.config.get("recycle_bin", [])
        button_layout = self.config.get("button_layout", "single")
        button_colors = self.config.get("button_colors", {})
        
        # 保存分组顺序
        groups_order = []
        if hasattr(self, 'nav_buttons_layout'):
            for i in range(self.nav_buttons_layout.count()):
                widget = self.nav_buttons_layout.itemAt(i).widget()
                if isinstance(widget, DraggableGroupButton):
                    groups_order.append(widget.group_id)
        
        # 保存已有工具的提示信息
        tools_tooltips = {}
        for tool in self.config.get("tools", []):
            if "tooltip" in tool and tool["tooltip"]:
                # 使用filename作为键，保存提示信息
                tools_tooltips[tool["filename"]] = tool["tooltip"]
        
        # 保存 groups_tree（嵌套结构）
        groups_tree = self.config.get("groups_tree", [])
        splitter_ratio = self.config.get("splitter_ratio", 0.22)
        
        # 重新扫描目录获取分组和工具
        self.config = self.scan_tools_directory()
        
        # 恢复回收站和布局设置
        self.config["recycle_bin"] = recycle_bin
        self.config["button_layout"] = button_layout
        self.config["button_colors"] = button_colors
        self.config["splitter_ratio"] = splitter_ratio
        self.config["groups_tree"] = groups_tree
        
        # 恢复工具的提示信息
        for tool in self.config.get("tools", []):
            if tool["filename"] in tools_tooltips:
                tool["tooltip"] = tools_tooltips[tool["filename"]]
        
        # 保存配置，包括分组顺序和嵌套结构
        config_to_save = {
            "recycle_bin": self.config["recycle_bin"],
            "button_layout": self.config["button_layout"],
            "tools_tooltips": tools_tooltips,
            "groups_order": groups_order,
            "groups_tree": groups_tree,
            "button_colors": self.config["button_colors"],
            "splitter_ratio": self.config["splitter_ratio"]
        }
        
        # 保存到配置文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=4, ensure_ascii=False)
        
        # 重新加载工具，保持在当前组
        self.load_tools(keep_current_group=True)
        
        # 如果之前在回收站中，重新显示回收站
        if was_in_recycle_bin:
            self.show_recycle_bin()
        # 否则如果有保存的组ID，显示该组
        elif current_group_id and current_group_id in self.group_containers:
            self.show_group(current_group_id)
        # 如果组ID不存在但有组名，尝试通过名称找到组
        elif current_group_name:
            found = False
            for group in self.config["groups"]:
                if group["name"] == current_group_name:
                    self.show_group(group["id"])
                    found = True
                    break
            
            # 如果找不到匹配的组名，显示第一个组
            if not found and self.config["groups"]:
                self.show_group(self.config["groups"][0]["id"])
    
    def on_search_text_changed(self, text):
        """on_search_text_changed 代理方法"""
        self.search_results_ui.on_search_text_changed(text)
    def perform_search(self):
        """perform_search 代理方法"""
        self.search_results_ui.perform_search()
    def clear_search(self):
        """clear_search 代理方法"""
        self.search_results_ui.clear_search()
    def clear_search_results(self):
        """clear_search_results 代理方法"""
        self.search_results_ui.clear_search_results()
    def show_search_results(self):
        """show_search_results 代理方法"""
        self.search_results_ui.show_search_results()
    def create_search_result_item(self, tool):
        """create_search_result_item 代理方法"""
        return self.search_results_ui.create_search_result_item(tool)
    def get_group_name_by_id(self, group_id):
        """根据组ID获取组名称（委托给 config_service）"""
        return self.config_service.get_group_name_by_id(group_id)
    

    def switch_to_search_view(self):
        """switch_to_search_view 代理方法"""
        self.search_results_ui.switch_to_search_view()
    def switch_to_normal_view(self):
        """switch_to_normal_view 代理方法"""
        self.search_results_ui.switch_to_normal_view()
    def jump_to_group(self, group_id):
        """jump_to_group 代理方法"""
        self.search_results_ui.jump_to_group(group_id)
    def jump_to_tool(self, tool):
        """jump_to_tool 代理方法"""
        self.search_results_ui.jump_to_tool(tool)
    def find_button_for_tool(self, tool):
        """find_button_for_tool 代理方法"""
        return self.search_results_ui.find_button_for_tool(tool)
    def highlight_tool_button(self, button):
        """highlight_tool_button 代理方法"""
        self.search_results_ui.highlight_tool_button(button)
    def clear_tool_highlight(self):
        """clear_tool_highlight 代理方法"""
        self.search_results_ui.clear_tool_highlight()
    def show_search_context_menu(self, position, widget, tool):
        """show_search_context_menu 代理方法"""
        self.search_results_ui.show_search_context_menu(position, widget, tool)
    def toggle_pin(self, tool):
        """切换置顶状态并刷新UI"""
        current = self.is_tool_pinned(tool)
        changed = self.set_tool_pinned(tool, not current)
        if changed:
            self.refresh_tools()
    
    def show_settings_dialog(self):
        """show_settings_dialog 代理方法"""
        # 重新初始化设置对话框，确保使用最新代码
        from core.ui.settings_dialog import SettingsDialog
        self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.show_settings_dialog()
    def apply_settings(self, single_layout_selected, dialog):
        """apply_settings 代理方法"""
        self.settings_dialog.apply_settings(single_layout_selected, dialog)
    def open_scripts_directory(self):
        """open_scripts_directory 代理方法"""
        self.settings_dialog.open_scripts_directory()
    def export_config(self):
        """export_config 代理方法"""
        self.settings_dialog.export_config()
    def import_config(self):
        """import_config 代理方法"""
        self.settings_dialog.import_config()
    def dragEnterEvent(self, event):
        """拖放进入事件处理"""
        # 接受文件拖放
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """拖放事件处理"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                # 默认添加到当前显示的分组
                current_group_id = "default"
                
                # 遍历所有分组容器，找出当前可见的一个
                for group_id, container in self.group_containers.items():
                    if container["panel"].isVisible():
                        current_group_id = group_id
                        break
                
                # 处理拖放的文件
                self.process_dropped_file(file_path, current_group_id)
            
            event.acceptProposedAction()
    
    def process_dropped_file(self, file_path, target_group_id=None):
        """处理拖放的文件"""
        # 检查文件扩展名
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext not in ['.py', '.mel']:
            cmds.warning(f"只支持.py和.mel文件，跳过: {file_path}")
            return
            
        # 确定脚本类型
        script_type = 'python' if ext == '.py' else 'mel'
        
        # 提取文件名
        file_name = os.path.basename(file_path)
        
        # 尝试读取文件内容
        try:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
        except Exception as e:
            cmds.warning(f"读取文件失败: {file_path}，错误: {str(e)}")
            return
            
        # 直接使用文件名作为显示名称（不再尝试从内容中提取）
        display_name = os.path.splitext(file_name)[0]
        
        # 确定目标分组ID和名称
        group_name = None
        target_group_id = target_group_id
        
        # 如果未指定目标分组或找不到目标分组，使用当前选中分组或第一个可用分组
        if not target_group_id or target_group_id not in [g["id"] for g in self.config["groups"]]:
            # 尝试使用当前选中的分组
            if self.active_group_id and self.active_group_id in [g["id"] for g in self.config["groups"]]:
                target_group_id = self.active_group_id
            # 或者使用第一个可用分组
            elif self.config["groups"]:
                target_group_id = self.config["groups"][0]["id"]
            # 如果没有分组，创建一个新分组
            else:
                new_group_name = "分组1"
                new_group_dir = os.path.join(self.tools_dir, new_group_name)
                
                # 确保目录名称唯一
                counter = 1
                while os.path.exists(new_group_dir):
                    new_group_name = f"分组{counter}"
                    new_group_dir = os.path.join(self.tools_dir, new_group_name)
                    counter += 1
                
                # 创建新目录
                os.makedirs(new_group_dir)
                
                # 创建新分组对象
                target_group_id = f"group_{int(time.time())}"
                new_group = {
                    "id": target_group_id,
                    "name": new_group_name
                }
                
                # 添加到配置
                self.config["groups"].append(new_group)
                group_name = new_group_name
        
        # 查找目标组名称
        if not group_name:
            for group in self.config["groups"]:
                if group["id"] == target_group_id:
                    group_name = group["name"]
                    break
        
        # 确保目标组目录存在
        group_dir = os.path.join(self.tools_dir, group_name)
        if not os.path.exists(group_dir):
            os.makedirs(group_dir)
        
        # 使用脚本名称作为文件名（移除非法字符）
        clean_name = re.sub(r'[\\/*?:"<>|]', '_', display_name)  # 替换Windows非法文件名字符
        clean_name = clean_name.strip()  # 移除前后空格
        
        # 确保文件名唯一
        base_filename = clean_name
        dest_filename = f"{base_filename}{ext}"
        counter = 1
        while os.path.exists(os.path.join(group_dir, dest_filename)):
            dest_filename = f"{base_filename}_{counter}{ext}"
            counter += 1
        
        # 复制文件到目标组目录
        dest_file = os.path.join(group_dir, dest_filename)
        try:
            shutil.copy2(file_path, dest_file)
        except Exception as e:
            cmds.warning(f"复制文件失败: {file_path}，错误: {str(e)}")
            return
        
        # 保存当前选中的组
        current_group_id = self.active_group_id
        
        # 重新扫描并加载工具
        self.refresh_tools()
        
        # 不自动跳转到目标组，保持在当前选中的组
        if current_group_id and current_group_id in self.group_containers:
            self.show_group(current_group_id)
        
        cmds.inViewMessage(message=f"工具已添加到 '{self.get_group_name(target_group_id)}' 组: {display_name}", pos='midCenter', fade=True)
    
    def get_group_name(self, group_id):
        """根据组ID获取组名"""
        for group in self.config["groups"]:
            if group["id"] == group_id:
                return group["name"]
        return "未知组"
    
    def scroll_to_group(self, group_id):
        """scroll_to_group 代理方法"""
        self.group_panel.scroll_to_group(group_id)
    def add_group(self):
        """add_group 代理方法"""
        self.group_panel.add_group()
    def show_help(self):
        """show_help 代理方法"""
        self.help_dialog.show_help()
    def open_external_url(self, url):
        """open_external_url 代理方法"""
        self.help_dialog.open_external_url(url)
    def extract_tooltip_from_content(self, content, script_type):
        """extract_tooltip_from_content 代理方法"""
        return self.help_dialog.extract_tooltip_from_content(content, script_type)
    def add_to_shelf(self, tool):
        """add_to_shelf 代理方法"""
        self.help_dialog.add_to_shelf(tool)


# 全局变量，存储当前活动的脚本管理器窗口
scripts_box_dialog = None

# 创建启动函数
def show_scripts_box():
    global scripts_box_dialog
    
    try:
        if scripts_box_dialog is not None:
            try:
                if scripts_box_dialog.isVisible():
                    scripts_box_dialog.close()
                scripts_box_dialog.deleteLater()
            except:
                pass
    except:
        pass
    
    try:
        version_info = get_version_info()
        print("Maya脚本管理器启动中...")
        print(f"版本信息: {version_info}")
        
        scripts_box_dialog = ScriptsBox()
        try:
            scripts_box_dialog.resize(950, 700)
        except Exception:
            pass
        if MAYA_VERSION >= 2025:
            scripts_box_dialog.show()
            scripts_box_dialog.raise_()
            scripts_box_dialog.activateWindow()
        else:
            scripts_box_dialog.show()
        
        return scripts_box_dialog
    except Exception as e:
        error_msg = traceback.format_exc()
        cmds.warning(f"启动脚本管理器失败: {str(e)}\n{error_msg}")
        return None

# 安全关闭函数
def close_scripts_box():
    global scripts_box_dialog
    
    try:
        if scripts_box_dialog is not None:
            # 尝试正常关闭
            scripts_box_dialog.close()
            scripts_box_dialog.deleteLater()
            scripts_box_dialog = None
            return True
    except Exception as e:
        cmds.warning(f"关闭脚本管理器失败: {str(e)}")
    
    return False

# 当直接运行此脚本时启动
if __name__ == "__main__":
    show_scripts_box()

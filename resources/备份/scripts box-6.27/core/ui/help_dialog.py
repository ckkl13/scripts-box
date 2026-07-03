# -*- coding: utf-8 -*-
"""
帮助对话框组件
处理帮助信息、添加工具架等功能
"""

import os
import re

from core.qt_compat import *


class HelpDialog:
    """帮助对话框管理器"""
    
    def __init__(self, parent_window):
        """
        初始化帮助对话框
        
        参数:
            parent_window: 父窗口（ScriptsBox实例）
        """
        self.parent = parent_window
        self.help_dialog = None  # 保存对话框引用，防止被垃圾回收
    
    def show_help(self):
        """显示帮助信息"""
        # 如果对话框已存在且可见，则显示到前面
        if self.help_dialog is not None and self.help_dialog.isVisible():
            self.help_dialog.raise_()
            self.help_dialog.activateWindow()
            return
        
        self.help_dialog = QDialog(self.parent)
        self.help_dialog.setWindowTitle("脚本管理器 - 帮助信息")
        self.help_dialog.setMinimumWidth(700)
        self.help_dialog.setMinimumHeight(600)
        
        # 设置对话框样式
        self.help_dialog.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QTextBrowser {
                background-color: #2A2A2A;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton {
                background-color: #3a6ea5;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a7eb5;
            }
            QPushButton:pressed {
                background-color: #2a5e95;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(self.help_dialog)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 创建标题
        title_label = QLabel("Maya脚本管理器使用指南")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #E0E0E0; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建文本浏览器以显示帮助内容
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)  # 允许打开外部链接
        layout.addWidget(text_browser)
        
        # 设置帮助信息文本
        help_html = """
        <style>
            body { color: #E0E0E0; font-family: Arial, sans-serif; }
            h2 { color: #4a7eb5; margin-top: 20px; margin-bottom: 10px; }
            h3 { color: #66BBFF; margin-top: 15px; margin-bottom: 5px; }
            ul { margin-top: 5px; padding-left: 20px; }
            li { margin-bottom: 5px; }
            .note { background-color: #2D4056; padding: 8px; border-radius: 4px; margin: 10px 0; }
            .tip { color: #AAFFAA; }
            .highlight { color: #FFCC66; font-weight: bold; }
            a { color: #66BBFF; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .section { border-bottom: 1px solid #555555; padding-bottom: 10px; margin-bottom: 10px; }
        </style>
        
        <div class="section">
            <p>脚本管理器可以帮助您更高效地组织和运行Maya中的Python和MEL脚本，提高工作效率。</p>
        </div>
        
        <h2>主要功能</h2>
        <ul>
            <li><b>脚本管理</b> - 创建、编辑、组织和运行Python/MEL脚本</li>
            <li><b>分组功能</b> - 将脚本整理到不同分组中，便于管理</li>
            <li><b>一键执行</b> - 点击按钮即可运行脚本</li>
            <li><b>拖放支持</b> - 直接拖放外部.py或.mel文件导入</li>
            <li><b>回收站机制</b> - 删除的脚本可从回收站恢复</li>
            <li><b>脚本提示</b> - 鼠标悬停时显示脚本功能说明</li>
            <li><b>配置导入/导出</b> - 备份和共享您的脚本集合</li>
            <li><b>文件夹管理</b> - 可在tool文件夹下添加文件夹，然后放入对应脚本，然后回maya点刷新</li>
        </ul>
        
        <h2>基础操作</h2>
        <h3>脚本管理</h3>
        <ul>
            <li><b>创建脚本</b>：点击顶部工具栏中的"新建脚本"按钮</li>
            <li><b>运行脚本</b>：点击脚本按钮</li>
            <li><b>编辑脚本</b>：右键点击脚本按钮，选择"编辑脚本"</li>
            <li><b>删除脚本</b>：右键点击脚本按钮，选择"删除"</li>
            <li><b>修改提示信息</b>：右键点击脚本按钮，选择"编辑提示信息"</li>
        </ul>
        
        <h3>分组操作</h3>
        <ul>
            <li><b>创建分组</b>：点击左侧导航栏底部的"+"按钮</li>
            <li><b>重命名分组</b>：右键点击左侧导航栏中的分组按钮，选择"重命名"</li>
            <li><b>删除分组</b>：右键点击左侧导航栏中的分组按钮，选择"删除"</li>
            <li><b>移动脚本</b>：右键点击脚本按钮，选择"移动到分组"→选择目标分组</li>
        </ul>
        
        <h3>导入与导出</h3>
        <ul>
            <li><b>导入脚本</b>：直接将.py或.mel文件拖放到窗口中</li>
            <li><b>导出配置</b>：点击顶部"设置"按钮，选择"导出配置"</li>
            <li><b>导入配置</b>：点击顶部"设置"按钮，选择"导入配置"</li>
        </ul>
        
        <div class="note">
            <p><span class="highlight">提示：</span>您可以在脚本中添加注释来提供提示信息，格式如下：</p>
            <p>Python: <span class="tip"># 提示: 这是脚本的功能说明</span></p>
            <p>MEL: <span class="tip">// 提示: 这是脚本的功能说明</span></p>
        </div>
        
        <h2>高级功能</h2>
        <h3>回收站操作</h3>
        <ul>
            <li><b>查看回收站</b>：点击左侧导航栏底部的"回收站"按钮</li>
            <li><b>恢复脚本</b>：在回收站中点击脚本卡片上的"恢复"按钮</li>
            <li><b>永久删除</b>：在回收站中点击脚本卡片上的"删除"按钮</li>
            <li><b>清空回收站</b>：在回收站顶部点击"清空回收站"按钮</li>
        </ul>
        
        <h3>错误处理与调试</h3>
        <ul>
            <li>运行脚本报错会在Maya的脚本编辑器中显示详细错误信息</li>
            <li>找不到脚本文件时会自动在所有分组中搜索</li>
            <li>支持自动修复工具文件路径问题</li>
        </ul>
        
        <h2>常见问题</h2>
        <ul>
            <li><b>无法运行脚本</b>：检查脚本语法是否正确，Maya版本是否兼容</li>
            <li><b>脚本丢失</b>：检查回收站，或检查电脑中是否有备份</li>
            <li><b>无法导入配置</b>：确保导入的配置文件格式正确，且包含必要的工具目录结构</li>
        </ul>
        
        <div class="section">
            <p style="margin-top: 20px;"><b>作者信息:</b></p>
            <p>如有问题或建议，请通过以下方式联系作者:</p>
            <p><a href="https://space.bilibili.com/431406403">哔哩哔哩主页</a></p>
        </div>
        """
        
        text_browser.setHtml(help_html)
        
        # 创建底部按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(10)
        
        # 添加版本信息
        version_info = get_version_info()
        version_label = QLabel(f"Maya版本: {version_info['maya_version']}, Qt版本: {version_info['qt_version']}")
        version_label.setStyleSheet("color: #999999; font-style: italic;")
        button_layout.addWidget(version_label)
        
        button_layout.addStretch(1)
        
        # 创建按钮
        open_link_btn = QPushButton("访问B站主页")
        open_link_btn.setIcon(self.parent.style().standardIcon(QStyle.SP_DriveNetIcon))
        close_btn = QPushButton("关闭")
        close_btn.setIcon(self.parent.style().standardIcon(QStyle.SP_DialogCloseButton))
        
        button_layout.addWidget(open_link_btn)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 连接按钮事件
        open_link_btn.clicked.connect(lambda: self.open_external_url("https://space.bilibili.com/431406403"))
        close_btn.clicked.connect(self.help_dialog.accept)
        
        # 显示对话框（非模态）
        self.help_dialog.show()
    
    def open_external_url(self, url):
        """打开外部URL链接"""
        try:
            if qt_version == "PySide6":
                from PySide6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(url))
            elif qt_version == "PySide2":
                from PySide2.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(url))
            elif qt_version == "PyQt5":
                from PyQt5.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(url))
            else:
                # 对于旧版Qt
                QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            cmds.warning(f"打开链接失败: {str(e)}")
    
    def extract_tooltip_from_content(self, content, script_type):
        """从文件内容中提取提示信息"""
        # 尝试查找注释中的提示信息
        if script_type == "python":
            # 查找Python文件中的提示信息
            tooltip_patterns = [
                r'#\s*提示[:：]\s*(.+)',
                r'#\s*说明[:：]\s*(.+)',
                r'#\s*tooltip[:：]\s*(.+)',
                r'#\s*description[:：]\s*(.+)'
            ]
        else:
            # 查找MEL文件中的提示信息
            tooltip_patterns = [
                r'//\s*提示[:：]\s*(.+)',
                r'//\s*说明[:：]\s*(.+)',
                r'//\s*tooltip[:：]\s*(.+)',
                r'//\s*description[:：]\s*(.+)'
            ]
        
        # 尝试每个模式
        for pattern in tooltip_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # 如果没有找到提示，尝试提取多行注释作为提示
        if script_type == "python":
            # 尝试提取Python多行注释
            docstring_pattern = r'"""(.*?)"""'
            match = re.search(docstring_pattern, content, re.DOTALL)
            if match:
                # 将多行注释转换为单行
                docstring = match.group(1).strip()
                # 如果多行注释太长，截断它
                if len(docstring) > 200:
                    docstring = docstring[:197] + "..."
                return docstring
        
        # 如果没有找到任何提示，返回None
        return None
    
    def add_to_shelf(self, tool):
        """将脚本添加到Maya工具架"""
        try:
            # 获取当前活动的工具架
            current_shelf = cmds.tabLayout("ShelfLayout", query=True, selectTab=True)
            if not current_shelf:
                cmds.warning("无法获取当前工具架")
                return
            
            # 获取脚本文件路径
            group_id = tool.get("group")
            if not group_id:
                cmds.warning(f"工具没有指定分组: {tool['name']}")
                return
                
            group_name = None
            for group in self.parent.config["groups"]:
                if group["id"] == group_id:
                    group_name = group["name"]
                    break
                    
            if not group_name:
                cmds.warning(f"找不到工具所属分组: {tool['name']}")
                return
            
            # 获取组目录和脚本路径
            group_dir = os.path.join(self.parent.tools_dir, group_name)
            tool_path = os.path.join(group_dir, tool["filename"])
            
            # 检查文件是否存在
            if not os.path.exists(tool_path):
                cmds.warning(f"找不到工具文件: {tool_path}")
                return
            
            # 读取脚本内容
            try:
                with open(tool_path, 'r', encoding='utf-8', errors='ignore') as f:
                    script_content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(tool_path, 'r', encoding='gbk', errors='ignore') as f:
                        script_content = f.read()
                except UnicodeDecodeError:
                    with open(tool_path, 'r', encoding='latin-1') as f:
                        script_content = f.read()
            
            # 准备工具架按钮的命令
            if tool["type"] == "mel":
                # MEL脚本命令 - 直接使用脚本内容
                shelf_command = script_content
                source_type = "mel"
            else:
                # Python脚本命令
                # 为了确保脚本能正确执行，我们直接执行脚本内容
                shelf_command = script_content
                source_type = "python"
            
            # 获取工具提示
            tooltip = tool.get("tooltip", tool["name"])
            
            # 创建工具架按钮
            cmds.shelfButton(
                parent=current_shelf,
                command=shelf_command,
                sourceType=source_type,
                imageOverlayLabel=tool["name"][:8],  # 限制标签长度
                overlayLabelColor=(1, 1, 0.5),  # 浅黄色
                overlayLabelBackColor=(0, 0, 0, 0.5),  # 半透明黑色背景
                annotation=tooltip
            )
            
            cmds.inViewMessage(message=f"已将 '{tool['name']}' 添加到工具架", pos='midCenter', fade=True)
            
        except Exception as e:
            cmds.warning(f"添加工具架失败: {str(e)}")
            QMessageBox.critical(self.parent, "添加失败", f"添加工具架失败: {str(e)}")

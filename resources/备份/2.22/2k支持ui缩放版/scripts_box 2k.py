# -*- coding: utf-8 -*-
"""
Maya脚本管理器 - 兼容Maya 2021-2026
支持PySide2和PySide6
"""
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

# UI缩放比例
UI_SCALE = 0.65

def s(value):
    """根据缩放比例调整数值"""
    return max(1, int(value * UI_SCALE))

# 尝试为Maya 2021-2026添加Qt兼容性
try:
    # 首先尝试从Maya导入PySide2
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    import maya.cmds as cmds
    import maya.mel as mel
    try:
        from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
    except Exception:
        MayaQWidgetDockableMixin = object
    qt_version = "PySide2"
except ImportError:
    try:
        # 如果PySide2导入失败，尝试导入PySide6（Maya 2024+）
        from PySide6.QtCore import *
        from PySide6.QtGui import *
        from PySide6.QtWidgets import *
        import maya.cmds as cmds
        import maya.mel as mel
        try:
            from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
        except Exception:
            MayaQWidgetDockableMixin = object
        qt_version = "PySide6"
    except ImportError:
        # 如果都失败了，可能不在Maya中运行
        print("未能导入PySide，此脚本需要在Maya中运行")
        sys.exit()

# 获取Maya版本
def get_maya_version():
    """获取Maya版本号"""
    maya_version = cmds.about(version=True)
    # 提取年份
    try:
        version_year = int(maya_version.split()[0])
        return version_year
    except:
        return 2023  # 默认版本

# 设置全局Maya版本变量
MAYA_VERSION = get_maya_version()

def get_version_info():
    """获取版本信息用于调试"""
    return {
        "maya_version": MAYA_VERSION,
        "qt_version": qt_version,
        "python_version": sys.version,
        "os_platform": sys.platform
    }

# Maya主窗口获取函数
def maya_main_window():
    """获取Maya主窗口作为父窗口"""
    # 使用更可靠的方法获取Maya主窗口
    if qt_version == "PySide2":
        for obj in QApplication.topLevelWidgets():
            if obj.objectName() == 'MayaWindow':
                return obj
    else:  # PySide6
        for obj in QApplication.allWidgets():
            if obj.objectName() == 'MayaWindow':
                return obj
    # 如果上面的方法失败，尝试通过窗口标题查找
    for obj in QApplication.topLevelWidgets():
        if 'Maya' in obj.windowTitle():
            return obj
    # 如果还找不到，返回None
    return None

# 行号显示小部件
class LineNumberArea(QWidget):
    """行号显示区域"""
    def __init__(self, editor):
        super(LineNumberArea, self).__init__(editor)
        self.code_editor = editor
        
    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)
        
    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

# 带行号的代码编辑器
class CodeEditor(QPlainTextEdit):
    """带行号的代码编辑器"""
    def __init__(self, parent=None):
        super(CodeEditor, self).__init__(parent)
        
        self.line_number_area = LineNumberArea(self)
        
        # 连接信号
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        
        self.update_line_number_area_width(0)
        
    def line_number_area_width(self):
        """计算行号区域宽度"""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        # 兼容PySide2和PySide6
        if hasattr(self.fontMetrics(), 'horizontalAdvance'):
            space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        else:
            space = 3 + self.fontMetrics().width('9') * digits
        return space
        
    def update_line_number_area_width(self, new_block_count):
        """更新行号区域宽度"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
        
    def update_line_number_area(self, rect, dy):
        """更新行号区域"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
            
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)
            
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super(CodeEditor, self).resizeEvent(event)
        
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))
        
    def update_line_number_style(self):
        """更新行号区域样式"""
        self.line_number_area.update()
        
    def line_number_area_paint_event(self, event):
        """绘制行号"""
        painter = QPainter(self.line_number_area)
        
        # 根据编辑器背景色动态调整行号区域颜色
        editor_bg = self.palette().color(self.backgroundRole())
        if editor_bg.lightness() < 128:  # 深色主题
            bg_color = QColor(60, 60, 60)  # 深灰色背景
            text_color = QColor(150, 150, 150)  # 浅灰色文字
        else:  # 浅色主题
            bg_color = QColor(240, 240, 240)  # 浅灰色背景
            text_color = QColor(120, 120, 120)  # 深灰色文字
            
        painter.fillRect(event.rect(), bg_color)
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(text_color)
                painter.drawText(0, top, self.line_number_area.width() - 3, self.fontMetrics().height(),
                               Qt.AlignRight, number)
                               
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

# 脚本编辑器类 - 用于编辑和创建脚本
class ScriptEditor(QDialog):
    """脚本编辑器窗口"""
    def __init__(self, parent=None, script_content="", script_type="python", script_name="", edit_mode=False, callback=None, tooltip=""):
        super(ScriptEditor, self).__init__(parent)
        
        # 设置窗口属性
        self.setWindowTitle("脚本编辑器")
        # 移除对最小尺寸的限制，允许自由缩放
        
        # 设置拖放支持
        self.setAcceptDrops(True)
        
        # 保存脚本类型、名称和编辑模式
        self.script_type = script_type
        self.script_name = script_name
        self.edit_mode = edit_mode
        self.callback = callback  # 保存回调函数
        
        # 创建UI
        self.create_ui()
        
        # 设置初始内容
        if script_content:
            self.editor.setPlainText(script_content)
            
        if script_name:
            self.name_edit.setText(script_name)
            
        # 设置脚本类型
        if script_type == "python":
            self.python_radio.setChecked(True)
        else:
            self.mel_radio.setChecked(True)
            
        # 如果是编辑模式，设置名称不可编辑
        if edit_mode:
            # 名称依然可以编辑，但会给用户提示这是编辑模式
            self.setWindowTitle(f"编辑脚本 - {script_name}")
        
        # 设置提示信息
        if tooltip:
            self.tooltip_edit.setPlainText(tooltip)
        
        # 更新编辑器样式
        self.update_editor_style()
        
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """放下事件"""
        if event.mimeData().hasUrls():
            # 获取第一个拖放的文件
            url = event.mimeData().urls()[0]
            file_path = url.toLocalFile()
            
            # 尝试加载文件内容
            self.load_script_from_file(file_path)
            
            event.acceptProposedAction()
            
    def load_script_from_file(self, file_path):
        """从文件加载脚本内容"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "文件不存在", f"找不到文件: {file_path}")
            return False
            
        # 检查文件类型
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # 确定脚本类型
        if ext == '.py':
            self.python_radio.setChecked(True)
            self.script_type = "python"
        elif ext == '.mel':
            self.mel_radio.setChecked(True)
            self.script_type = "mel"
        else:
            # 未知文件类型，尝试检测内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)  # 读取前1000个字符以检测类型
                if "maya.cmds" in content or "import cmds" in content or "from maya import cmds" in content:
                    self.python_radio.setChecked(True)
                    self.script_type = "python"
                elif "proc" in content and "{" in content:
                    self.mel_radio.setChecked(True)
                    self.script_type = "mel"
                else:
                    # 默认按Python处理
                    self.python_radio.setChecked(True)
                    self.script_type = "python"
        
        # 尝试不同编码读取文件
        content = ""
        try:
            # 首先尝试UTF-8
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                # 然后尝试GBK（中文Windows常用）
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 最后使用latin-1（可以读取任何文件但可能有乱码）
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        # 设置编辑器内容
        self.editor.setPlainText(content)
        
        # 从文件名中提取脚本名称
        script_name = os.path.basename(file_path)
        script_name = os.path.splitext(script_name)[0]  # 去除扩展名
        self.name_edit.setText(script_name)
        
        return True
            
    def create_ui(self):
        """创建界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(s(10), s(10), s(10), s(10))
        main_layout.setSpacing(s(10))
        
        # 顶部工具栏
        top_layout = QHBoxLayout()
        
        # 脚本名称
        name_label = QLabel("脚本名称:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入脚本名称...")
        
        # 脚本类型选择
        type_label = QLabel("脚本类型:")
        type_group = QButtonGroup(self)
        self.python_radio = QRadioButton("Python")
        self.mel_radio = QRadioButton("MEL")
        type_group.addButton(self.python_radio)
        type_group.addButton(self.mel_radio)
        self.python_radio.setChecked(True)  # 默认选择Python
        
        # 连接脚本类型变更事件
        self.python_radio.toggled.connect(self.update_editor_style)
        
        # 添加到顶部布局
        top_layout.addWidget(name_label)
        top_layout.addWidget(self.name_edit, 1)
        top_layout.addSpacing(s(20))
        top_layout.addWidget(type_label)
        top_layout.addWidget(self.python_radio)
        top_layout.addWidget(self.mel_radio)
        
        main_layout.addLayout(top_layout)
        
        # 提示信息编辑区
        tooltip_layout = QHBoxLayout()
        tooltip_label = QLabel("提示信息:")
        self.tooltip_edit = QPlainTextEdit()
        self.tooltip_edit.setMaximumHeight(s(60))
        self.tooltip_edit.setPlaceholderText("输入工具提示信息（可选）...")
        tooltip_layout.addWidget(tooltip_label)
        tooltip_layout.addWidget(self.tooltip_edit, 1)
        main_layout.addLayout(tooltip_layout)
        
        # 代码编辑器（带行号）
        self.editor = CodeEditor()
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        # 设置等宽字体
        font = QFont("Consolas, Courier New, monospace")
        font.setPointSize(s(14))
        self.editor.setFont(font)
        
        # 启用Tab键
        self.editor.setTabStopDistance(s(40))  # 相当于4个空格
        
        # 添加自定义拖放支持
        original_dragEnterEvent = self.editor.dragEnterEvent
        original_dropEvent = self.editor.dropEvent
        
        def editor_dragEnterEvent(event):
            """编辑器拖拽进入事件"""
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            elif hasattr(original_dragEnterEvent, '__call__'):
                original_dragEnterEvent(event)
                
        def editor_dropEvent(event):
            """编辑器放下事件"""
            if event.mimeData().hasUrls():
                url = event.mimeData().urls()[0]
                file_path = url.toLocalFile()
                self.load_script_from_file(file_path)
                event.acceptProposedAction()
            elif hasattr(original_dropEvent, '__call__'):
                original_dropEvent(event)
                
        self.editor.dragEnterEvent = editor_dragEnterEvent
        self.editor.dropEvent = editor_dropEvent
        
        main_layout.addWidget(self.editor, 1)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(s(10))
        
        # 保存按钮
        save_text = "保存" if self.edit_mode else "保存并创建"
        self.save_button = QPushButton(save_text)
        self.save_button.clicked.connect(self.save_script)
        self.save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                padding: {s(8)}px {s(16)}px;
                border: none;
                border-radius: {s(4)}px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
            QPushButton:pressed {{
                background-color: #3d8b40;
            }}
        """)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.close)
        cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #f44336;
                color: white;
                padding: {s(8)}px {s(16)}px;
                border: none;
                border-radius: {s(4)}px;
            }}
            QPushButton:hover {{
                background-color: #e53935;
            }}
            QPushButton:pressed {{
                background-color: #d32f2f;
            }}
        """)
        
        # 状态栏
        self.status_bar = QLabel("")
        self.status_bar.setStyleSheet("color: #999;")
        
        button_layout.addWidget(self.status_bar, 1)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
    def update_editor_style(self):
        """根据脚本类型更新编辑器样式"""
        if self.python_radio.isChecked():
            self.script_type = "python"
            self.editor.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #282c34;
                    color: #abb2bf;
                    border: 1px solid #555;
                    border-radius: 3px;
                    selection-background-color: #3e4451;
                    selection-color: #ffffff;
                }
            """)
        else:
            self.script_type = "mel"
            self.editor.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #263238;
                    color: #eeffff;
                    border: 1px solid #555;
                    border-radius: 3px;
                    selection-background-color: #546e7a;
                    selection-color: #ffffff;
                }
            """)
        
        # 更新行号区域样式
        if hasattr(self.editor, 'update_line_number_style'):
            self.editor.update_line_number_style()
            
    def save_script(self):
        """保存脚本"""
        # 获取脚本内容
        script_content = self.editor.toPlainText().strip()
        if not script_content:
            self.status_bar.setText("脚本内容不能为空")
            self.status_bar.setStyleSheet("color: #FF6666;")
            return
            
        # 获取脚本名称
        script_name = self.name_edit.text().strip()
        if not script_name:
            self.status_bar.setText("脚本名称不能为空")
            self.status_bar.setStyleSheet("color: #FF6666;")
            return
            
        # 获取脚本类型
        script_type = "python" if self.python_radio.isChecked() else "mel"
        
        # 获取提示信息
        tooltip = self.tooltip_edit.toPlainText().strip()
        
        # 调用回调函数
        success = False
        
        if self.callback:
            # 检查父对象是否有配置更新方法
            if hasattr(self.parent(), "create_new_tool") or hasattr(self.parent(), "update_tool"):
                # 创建自定义回调代理函数，添加提示信息参数
                def callback_with_tooltip(name, content, script_type, edit_mode):
                    # 获取当前工具对象
                    for tool in self.parent().config["tools"]:
                        if tool["name"] == name or (edit_mode and tool["filename"] == self.parent().script_editor_filename):
                            # 设置提示信息
                            tool["tooltip"] = tooltip
                            self.parent().save_config()
                            break
                    
                    # 调用原始回调
                    return self.callback(name, content, script_type, edit_mode)
                
                success = callback_with_tooltip(script_name, script_content, script_type, self.edit_mode)
            else:
                success = self.callback(script_name, script_content, script_type, self.edit_mode)
                
            if success:
                self.status_bar.setText(f"脚本已保存: {script_name}")
                self.status_bar.setStyleSheet("color: #66CC66;")
                # 如果是新建模式，在保存后重置编辑器
                if not self.edit_mode:
                    self.editor.clear()
                    self.name_edit.clear()
                    self.tooltip_edit.clear()
                    self.status_bar.setText("新建脚本已保存，请继续编辑或关闭窗口")
            else:
                self.status_bar.setText("保存脚本失败")
                self.status_bar.setStyleSheet("color: #FF6666;")
                
    def run_script(self):
        """运行当前脚本"""
        script_content = self.editor.toPlainText()
        
        if not script_content.strip():
            self.status_bar.setText("没有脚本内容可运行")
            self.status_bar.setStyleSheet("color: #FF6666;")
            return
            
        try:
            # 根据脚本类型执行
            if self.script_type == "python":
                # 执行Python脚本
                exec(script_content)
                self.status_bar.setText("Python脚本执行成功")
                self.status_bar.setStyleSheet("color: #66CC66;")
            else:
                # 执行MEL脚本
                try:
                    # 保存当前工作目录
                    original_dir = os.getcwd()
                    
                    # 如果脚本已保存，则设置工作目录为脚本所在目录
                    if hasattr(self, 'temp_mel_file'):
                        # 创建临时MEL文件
                        import tempfile
                        temp_dir = tempfile.gettempdir()
                        temp_file = os.path.join(temp_dir, f"temp_mel_script_{int(time.time())}.mel")
                        
                        try:
                            with open(temp_file, 'w', encoding='utf-8') as f:
                                f.write(script_content)
                            
                            # 设置工作目录为临时文件所在目录
                            os.chdir(temp_dir)
                            
                            # 将临时目录添加到MEL路径
                            mel_script_path = mel.eval('getenv "MAYA_SCRIPT_PATH"')
                            if temp_dir not in mel_script_path.split(';'):
                                mel.eval(f'putenv "MAYA_SCRIPT_PATH" "{temp_dir};{mel_script_path}"')
                            
                            # 先尝试source临时文件
                            try:
                                mel.eval(f'source "{temp_file}";')
                                self.status_bar.setText("MEL脚本执行成功 (通过source)")
                                self.status_bar.setStyleSheet("color: #66CC66;")
                            except Exception as e:
                                # 如果source失败，尝试直接执行内容
                                mel.eval(script_content)
                                self.status_bar.setText("MEL脚本执行成功 (直接执行)")
                                self.status_bar.setStyleSheet("color: #66CC66;")
                        finally:
                            # 删除临时文件
                            try:
                                if os.path.exists(temp_file):
                                    os.remove(temp_file)
                            except:
                                pass
                    else:
                        # 直接执行MEL代码
                        mel.eval(script_content)
                        self.status_bar.setText("MEL脚本执行成功")
                        self.status_bar.setStyleSheet("color: #66CC66;")
                    
                    # 恢复原始工作目录
                    os.chdir(original_dir)
                    
                except Exception as mel_error:
                    error_msg = str(mel_error)
                    self.status_bar.setText(f"执行MEL脚本错误: {error_msg}")
                    self.status_bar.setStyleSheet("color: #FF6666;")
                    traceback.print_exc()
                
        except Exception as e:
            error_msg = str(e)
            self.status_bar.setText(f"执行错误: {error_msg}")
            self.status_bar.setStyleSheet("color: #FF6666;")
            traceback.print_exc()

# 添加一个可拖拽的按钮类
class DraggableGroupButton(QPushButton):
    """可拖拽的分组按钮类"""
    
    def __init__(self, text, group_id, parent=None):
        super(DraggableGroupButton, self).__init__(text, parent)
        self.group_id = group_id
        self.parent_widget = parent
        self.setAcceptDrops(True)
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        super(DraggableGroupButton, self).mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not (event.buttons() & Qt.LeftButton):
            return
            
        # 检查是否达到拖动阈值
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        # 创建拖拽对象
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # 设置拖拽数据 - 使用组ID作为标识
        mime_data.setText(self.group_id)
        drag.setMimeData(mime_data)
        
        # 设置拖拽时的视觉效果
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # 执行拖拽
        drag.exec_(Qt.MoveAction)
        
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
        
    def dropEvent(self, event):
        """放置事件"""
        if event.mimeData().hasText():
            source_group_id = event.mimeData().text()
            target_group_id = self.group_id
            
            # 如果源和目标相同，不执行任何操作
            if source_group_id == target_group_id:
                event.acceptProposedAction()
                return
                
            # 获取源按钮和目标按钮
            source_button = self.parent_widget.nav_buttons.get(source_group_id)
            target_button = self
            
            if source_button and target_button:
                # 获取按钮在布局中的位置
                source_index = self.parent_widget.nav_buttons_layout.indexOf(source_button)
                target_index = self.parent_widget.nav_buttons_layout.indexOf(target_button)
                
                # 如果找到了位置，执行重新排序
                if source_index != -1 and target_index != -1:
                    # 从布局中移除源按钮
                    self.parent_widget.nav_buttons_layout.removeWidget(source_button)
                    
                    # 重新插入到目标位置
                    self.parent_widget.nav_buttons_layout.insertWidget(target_index, source_button)
                    
                    # 保存配置
                    self.parent_widget.save_config()
                    
                    # 提示用户排序已保存
                    cmds.inViewMessage(message="分组顺序已更新", pos='midCenter', fade=True, fadeStayTime=1000)
            
            event.acceptProposedAction()

class MiddleClickButton(QPushButton):
    """支持中键点击的自定义按钮类"""
    def __init__(self, text, parent=None):
        super(MiddleClickButton, self).__init__(text, parent)
        self.tool_data = None
        self.scripts_box = None
    
    def set_tool_data(self, tool_data, scripts_box):
        """设置工具数据和脚本管理器引用"""
        self.tool_data = tool_data
        self.scripts_box = scripts_box
    
    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.MiddleButton and self.tool_data and self.scripts_box:
            # 中键点击，添加到工具架
            self.scripts_box.add_to_shelf(self.tool_data)
        else:
            # 其他按键，调用父类处理
            super(MiddleClickButton, self).mousePressEvent(event)

class ScriptsBox(QDialog):
    def __init__(self, parent=maya_main_window()):
        super(ScriptsBox, self).__init__(parent)
        
        # 记录Qt和Maya版本信息，用于兼容性处理
        self.qt_version = qt_version
        self.maya_version = MAYA_VERSION
        
        # 设置窗口关闭属性
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # 应用兼容性修复
        self.apply_compatibility_fixes()
        
        self.setWindowTitle("Maya 脚本管理器")
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
            "radius_panel": f"{s(8)}px",
            "radius_btn": f"{s(6)}px",
        }
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #2b2b2b;
                color: #E0E0E0;
                border: 1px solid #3a3a3a;
                border-radius: {s(8)}px;
            }}
            QLabel {{
                color: #E0E0E0;
            }}
            QPushButton {{
                background-color: #3a3a3a;
                color: #E0E0E0;
                border: none;
                padding: {s(8)}px {s(12)}px;
                border-radius: {s(6)}px;
                font-size: {s(13)}px;
            }}
            QPushButton:hover {{
                background-color: #4a4a4a;
            }}
            QPushButton:pressed {{
                background-color: #2f2f2f;
            }}
            QLineEdit, QComboBox {{
                background-color: #2f2f2f;
                color: #E0E0E0;
                border: 1px solid #444444;
                border-radius: {s(6)}px;
                padding: {s(6)}px {s(10)}px;
                selection-background-color: #3A6EA5;
                selection-color: #ffffff;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid #3A6EA5;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: #2A2A2A;
                margin: 0px;
            }}
            QScrollBar:vertical {{ width: {s(10)}px; }}
            QScrollBar:horizontal {{ height: {s(10)}px; }}
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
                background: #555555;
                min-height: {s(20)}px;
                min-width: {s(20)}px;
                border-radius: {s(5)}px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                height: 0px;
                width: 0px;
            }}
            QTreeWidget {{
                background-color: transparent;
            }}
            QTreeWidget::item {{
                height: {s(24)}px;
                padding: {s(2)}px {s(4)}px;
            }}
            QMenu {{
                background-color: #303030;
                color: #E0E0E0;
                border: 1px solid #3a3a3a;
                border-radius: {s(6)}px;
                padding: {s(4)}px;
            }}
            QMenu::item {{
                padding: {s(6)}px {s(20)}px;
                border-radius: {s(4)}px;
            }}
            QMenu::item:selected {{
                background-color: #3A6EA5;
            }}
            QMenu::item:disabled {{
                color: #777777;
            }}
            QFrame {{
                background-color: transparent;
            }}
        """)
        
        # 设置接受拖放
        self.setAcceptDrops(True)
        
        # 添加回收站相关属性
        self.recycle_bin_visible = False
        
        # 配置文件路径
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.tools_dir = os.path.join(self.current_dir, "tool")
        self.config_file = os.path.join(self.current_dir, "config.json")
        self.pinned_file = os.path.join(self.current_dir, "pinned.json")
        self.groups_order_file = os.path.join(self.current_dir, "groups_order.json")
        
        # 回收站目录
        self.recycle_dir = os.path.join(self.current_dir, "recycle_bin")
        
        # 创建工具目录（如果不存在）
        if not os.path.exists(self.tools_dir):
            os.makedirs(self.tools_dir)
            
        # 创建回收站目录（如果不存在）
        if not os.path.exists(self.recycle_dir):
            os.makedirs(self.recycle_dir)
            
        # 初始化配置
        self.config = self.load_config()
        
        # 应用UI缩放设置
        global UI_SCALE
        if "ui_scale" in self.config:
            UI_SCALE = self.config["ui_scale"]
        
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
        if obj == getattr(self, "_nav_tree_viewport", None) and event.type() == QEvent.Drop:
            QTimer.singleShot(0, self.save_config)
        return super(ScriptsBox, self).eventFilter(obj, event)
    
    def create_ui(self):
        """创建UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(s(5), s(5), s(5), s(5))
        main_layout.setSpacing(s(5))
        
        # 左侧导航栏区域
        nav_widget = QWidget()
        self.nav_widget = nav_widget
        nav_widget.setObjectName("navPanel")
        nav_widget.setStyleSheet(f"""
            #navPanel {{
                background-color: #262626;
                border: 1px solid #3a3a3a;
                border-radius: {s(8)}px;
            }}
        """)
        nav_layout = QVBoxLayout(nav_widget)
        self.nav_layout = nav_layout
        nav_layout.setAlignment(Qt.AlignTop)
        nav_layout.setContentsMargins(5, 10, 5, 10)
        nav_layout.setSpacing(5)
        
        # 导航标题
        nav_title = QLabel("脚本分组")
        self.nav_title = nav_title
        nav_title.setStyleSheet(f"font-weight: bold; font-size: {s(16)}px; color: #E0E0E0;")
        nav_title.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(nav_title)
        
        # 添加分组按钮（主操作 - 蓝色）
        add_group_btn = QPushButton("+ 新建分组")
        add_group_btn.clicked.connect(self.add_group)
        add_group_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {s(8)}px {s(12)}px;
                font-weight: bold;
                font-size: {s(14)}px;
                background-color: #3A6EA5;
                color: white;
                text-align: center;
                border-radius: {s(6)}px;
            }}
            QPushButton:hover {{ background-color: #4A7EB5; }}
            QPushButton:pressed {{ background-color: #2A5E95; }}
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
        self.recycle_bin_btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: {s(8)}px {s(12)}px;
                border-radius: {s(6)}px;
            }}
        """)
        self.recycle_bin_btn.clicked.connect(self.show_recycle_bin)
        nav_layout.addWidget(self.recycle_bin_btn)
        
        # 分组列表（仅 tool 下直接子文件夹，不嵌套）
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setIndentation(s(18))
        self.nav_tree.setAnimated(True)
        self.nav_tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.nav_tree.setDefaultDropAction(Qt.MoveAction)
        self.nav_tree.itemClicked.connect(lambda item, col: self.show_group(item.data(0, Qt.UserRole)))
        # 自动保存顺序：拖拽排序后更新 groups_order.json
        try:
            self.nav_tree.model().rowsMoved.connect(lambda *args: self.save_config())
        except Exception:
            pass
        # 拖放结束后也保存（部分 Qt 版本 rowsMoved 不触发）
        self.nav_tree.viewport().installEventFilter(self)
        self._nav_tree_viewport = self.nav_tree.viewport()
        # 树右键菜单
        self.nav_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.nav_tree.customContextMenuRequested.connect(self.on_nav_tree_context_menu)
        nav_layout.addWidget(self.nav_tree)
        
        # 存储导航项与兼容旧属性
        self.nav_items = {}
        self.nav_buttons = {}
        self.active_group_id = None
        
        # 右侧主内容区域
        content_widget = QWidget()
        self.content_widget = content_widget
        content_widget.setObjectName("contentPanel")
        content_widget.setStyleSheet(f"#contentPanel {{ background-color: #303030; border: 1px solid #3a3a3a; border-radius: {s(8)}px; }}")
        content_layout = QVBoxLayout(content_widget)
        self.content_layout = content_layout
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # 顶部工具栏 
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        
        # 添加脚本按钮（成功/创建 - 绿色）
        add_btn = QPushButton("新建脚本")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4A6D4A;
                color: white;
                font-weight: bold;
                border-radius: {s(6)}px;
                padding: {s(8)}px {s(12)}px;
            }}
            QPushButton:hover {{ background-color: #5A7D5A; }}
            QPushButton:pressed {{ background-color: #3d5c3d; }}
        """)
        add_btn.clicked.connect(self.open_script_editor)
        toolbar.addWidget(add_btn)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_tools)
        toolbar.addWidget(refresh_btn)
        
        # 设置按钮
        settings_btn = QPushButton("设置")
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
        
        # 搜索按钮（与主色一致）
        search_btn = QPushButton("搜索")
        search_btn.setFixedSize(s(56), s(32))
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #3A6EA5;
                color: white;
                border-radius: {s(6)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #4A7EB5; }}
            QPushButton:pressed {{ background-color: #2A5E95; }}
        """)
        search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(search_btn)
        
        # 清除搜索按钮
        clear_search_btn = QPushButton("清除")
        clear_search_btn.setFixedSize(s(56), s(32))
        clear_search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #555555;
                color: white;
                border-radius: {s(6)}px;
            }}
            QPushButton:hover {{ background-color: #666666; }}
            QPushButton:pressed {{ background-color: #444444; }}
        """)
        clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_search_btn)
        
        toolbar.addWidget(search_container)
        
        # 伸缩器
        toolbar.addStretch()
        
        # 帮助按钮（圆形、主色）
        help_btn = QPushButton("?")
        help_btn.setFixedSize(s(32), s(32))
        help_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #3A6EA5;
                color: white;
                font-weight: bold;
                border-radius: {s(16)}px;
                font-size: {s(14)}px;
            }}
            QPushButton:hover {{ background-color: #4A7EB5; }}
            QPushButton:pressed {{ background-color: #2A5E95; }}
        """)
        help_btn.clicked.connect(self.show_help)
        toolbar.addWidget(help_btn)
        
        content_layout.addLayout(toolbar)
        
        # 右侧内容区标题
        self.content_title = QLabel("常用工具")
        self.content_title.setStyleSheet(f"font-weight: bold; font-size: {s(16)}px; padding: {s(8)}px; color: #E0E0E0;")
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
        self.main_splitter.setHandleWidth(s(4))
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(nav_widget)
        self.main_splitter.addWidget(content_widget)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        # 设置更小的最小宽度，便于整体窗口缩小
        self.nav_widget.setMinimumWidth(s(80))
        self.content_widget.setMinimumWidth(s(160))
        # 保存用户拖动分隔条的位置
        self.main_splitter.splitterMoved.connect(self.on_splitter_moved)
        main_layout.addWidget(self.main_splitter)
        self.apply_sidebar_layout_styles()
        # 根据保存的比例设置初始宽度
        QTimer.singleShot(0, self.apply_splitter_ratio)

    def apply_splitter_ratio(self):
        try:
            ratio = float(self.config.get("splitter_ratio", 0.25))
            w = max(1, self.main_splitter.width())
            left = max(s(60), int(w * ratio))
            right = max(s(120), w - left)
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
        """加载配置文件"""
        default_config = {
            "groups": [],
            "tools": [],
            "recycle_bin": [],  # 添加回收站列表
            "button_layout": "single",
            "button_colors": {},
            "sidebar_layout": False,
            "dockable_mode": False,
            "splitter_ratio": 0.22,
            "ui_scale": 0.65
        }
        
        # 扫描tools目录，获取基于文件夹结构的分组和工具
        config = self.scan_tools_directory()
        
        # 如果存在config.json，仅读取回收站和按钮布局信息
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    old_config = json.load(f)
                    
                # 仅保留回收站和布局设置，其他信息从文件夹结构获取
                if "recycle_bin" in old_config:
                    config["recycle_bin"] = old_config["recycle_bin"]
                if "button_layout" in old_config:
                    config["button_layout"] = old_config["button_layout"]
                if "button_colors" in old_config:
                    config["button_colors"] = old_config["button_colors"]
                if "sidebar_layout" in old_config:
                    config["sidebar_layout"] = old_config["sidebar_layout"]
                if "dockable_mode" in old_config:
                    config["dockable_mode"] = old_config["dockable_mode"]
                if "splitter_ratio" in old_config:
                    config["splitter_ratio"] = old_config["splitter_ratio"]
                if "ui_scale" in old_config:
                    config["ui_scale"] = old_config["ui_scale"]
            except Exception as e:
                cmds.warning(f"加载配置文件失败: {str(e)}，将使用默认配置")
                
        return config
    
    def scan_tools_directory(self):
        """扫描工具目录：仅识别 tool 下直接子文件夹作为分组，分组内只识别 .py 和 .mel 文件（不嵌套）"""
        config = {
            "groups": [],
            "tools": [],
            "recycle_bin": [],
            "button_layout": "single",
            "button_colors": {},
            "sidebar_layout": False,
            "dockable_mode": False
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
        """保存配置到文件，保存必要信息，包括工具提示信息"""
        # 创建要保存的配置对象
        config_to_save = {
            "recycle_bin": self.config["recycle_bin"],
            "button_layout": self.config["button_layout"],
            "tools_tooltips": {},
            "groups_order": [],  # 兼容旧版（按ID顺序）
            "button_colors": self.config.get("button_colors", {}),
            "sidebar_layout": self.config.get("sidebar_layout", False),
            "dockable_mode": self.config.get("dockable_mode", False),
            "splitter_ratio": self.config.get("splitter_ratio", 0.25),
            "ui_scale": self.config.get("ui_scale", 0.65)
        }
        
        # 保存所有工具的提示信息
        for tool in self.config.get("tools", []):
            if "tooltip" in tool and tool["tooltip"]:
                # 使用filename作为键，保存提示信息
                config_to_save["tools_tooltips"][tool["filename"]] = tool["tooltip"]
        
        # 保存分组顺序：按树中顺序收集名称，写入 groups_order.json 为名称列表
        def collect_order_names(parent_item):
            names = []
            for i in range(parent_item.childCount()):
                item = parent_item.child(i)
                gid = item.data(0, Qt.UserRole)
                config_to_save["groups_order"].append(gid)
                name = item.text(0).split(' (')[0]
                names.append(name)
            return names
        
        try:
            root = self.nav_tree.invisibleRootItem()
            order_names = collect_order_names(root)
            with open(self.groups_order_file, 'w', encoding='utf-8') as gf:
                json.dump(order_names, gf, indent=4, ensure_ascii=False)
        except Exception as e:
            cmds.warning(f"保存分组顺序失败: {str(e)}")
        
        # 保存到文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=4, ensure_ascii=False)
    
    def load_pinned(self):
        """加载置顶列表"""
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
        """保存置顶列表"""
        try:
            with open(self.pinned_file, 'w', encoding='utf-8') as f:
                json.dump(pinned_list, f, ensure_ascii=False, indent=4)
        except Exception as e:
            cmds.warning(f"保存置顶文件失败: {str(e)}")
    
    def get_tool_rel_path(self, tool):
        """获取工具相对路径标识: 分组名/文件名"""
        group_name = self.get_group_name_by_id(tool.get("group"))
        if not group_name:
            group_name = "default"
        return f"{group_name}/{tool.get('filename', '')}".replace("\\", "/")
    
    def is_tool_pinned(self, tool):
        """判断工具是否置顶"""
        rel = self.get_tool_rel_path(tool)
        pinned = self.load_pinned()
        norm = [p.replace("\\", "/") for p in pinned]
        return rel in norm
    
    def set_tool_pinned(self, tool, state):
        """设置工具置顶状态"""
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
                if "sidebar_layout" in saved_config:
                    self.config["sidebar_layout"] = saved_config["sidebar_layout"]
                if "dockable_mode" in saved_config:
                    self.config["dockable_mode"] = saved_config["dockable_mode"]
                if "splitter_ratio" in saved_config:
                    self.config["splitter_ratio"] = saved_config["splitter_ratio"]
                
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
        
        # 清除树导航
        self.nav_tree.clear()
        
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
        
        # 构建树形导航（依据名称顺序）
        def read_order_tree():
            try:
                if os.path.exists(self.groups_order_file):
                    with open(self.groups_order_file, 'r', encoding='utf-8') as gf:
                        data = json.load(gf)
                        if isinstance(data, list) and data:
                            # 纯名称列表 ["BS", "a常用", ...]
                            if isinstance(data[0], dict):
                                return [{"name": n.get("name", "")} for n in data if n.get("name")]
                            return [{"name": n} for n in data]
            except Exception as e:
                cmds.warning(f"读取分组顺序失败: {str(e)}")
            return []
        
        order_tree = read_order_tree()
        # 构建父子索引
        by_parent = {}
        id_by_name_under_parent = {}
        for g in self.config["groups"]:
            parent = g.get("parent")
            by_parent.setdefault(parent, []).append(g)
        # 名称排序（默认字母序）
        for parent, arr in by_parent.items():
            arr.sort(key=lambda x: x["name"].lower())
            id_by_name_under_parent[parent] = {x["name"]: x["id"] for x in arr}
        
        def add_items(parent_item, parent_id, children_order_nodes):
            # 根据名称顺序添加
            used = set()
            for node in children_order_nodes or []:
                name = node.get("name")
                gid = id_by_name_under_parent.get(parent_id, {}).get(name)
                if gid:
                    group = next((x for x in self.config["groups"] if x["id"] == gid), None)
                    if not group:
                        continue
                    item = QTreeWidgetItem(parent_item, [name])
                    item.setData(0, Qt.UserRole, gid)
                    self.nav_items[gid] = item
                    # 递归子项
                    add_items(item, gid, node.get("children", []))
                    used.add(gid)
            # 添加未在顺序中的剩余项
            for g in by_parent.get(parent_id, []):
                if g["id"] in used:
                    continue
                item = QTreeWidgetItem(parent_item, [g["name"]])
                item.setData(0, Qt.UserRole, g["id"])
                self.nav_items[g["id"]] = item
                add_items(item, g["id"], [])
        
        # 顶层项
        root = self.nav_tree.invisibleRootItem()
        add_items(root, None, order_tree)
        self.nav_tree.expandAll()
        
        # 首次运行或缺少名称顺序时，按当前树顺序写入 groups_order.json
        try:
            if not os.path.exists(self.groups_order_file):
                current_names = []
                for i in range(self.nav_tree.topLevelItemCount()):
                    item = self.nav_tree.topLevelItem(i)
                    name = item.text(0).split(' (')[0]
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
        
        # 决定显示哪个组
        if current_group_id and current_group_id in self.group_containers:
            # 保持在当前选中的组
            self.show_group(current_group_id)
        elif self.config["groups"]:
            # 显示第一个组
            # 优先使用树中的第一个可见项
            first = self.nav_tree.topLevelItem(0)
            gid = first.data(0, Qt.UserRole) if first else self.config["groups"][0]["id"]
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
        self.recycle_bin_btn.setStyleSheet(f"QPushButton {{ text-align: left; padding: {s(8)}px {s(12)}px; border-radius: {s(6)}px; }}")
        
        # 隐藏当前显示的组
        if self.active_group_id and self.active_group_id in self.group_containers:
            self.group_containers[self.active_group_id]["panel"].setVisible(False)
            
            # 重置导航按钮样式（与全局按钮一致）
            if self.active_group_id in self.nav_buttons:
                self.nav_buttons[self.active_group_id].setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        padding: {s(8)}px {s(12)}px;
                        background-color: #3a3a3a;
                        border: none;
                        border-radius: {s(6)}px;
                        color: #E0E0E0;
                    }}
                    QPushButton:hover {{ background-color: #4a4a4a; }}
                    QPushButton:pressed {{ background-color: #2f2f2f; }}
                """)
        
        # 显示新选择的组
        if group_id in self.group_containers:
            self.group_containers[group_id]["panel"].setVisible(True)
            self.content_title.setText(self.group_containers[group_id]["name"])
            
            # 高亮当前导航按钮（主色）
            if group_id in self.nav_buttons:
                self.nav_buttons[group_id].setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        padding: {s(8)}px {s(12)}px;
                        background-color: #3A6EA5;
                        border: none;
                        border-radius: {s(6)}px;
                        color: white;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: #4A7EB5; }}
                    QPushButton:pressed {{ background-color: #2A5E95; }}
                """)
            
            # 更新当前活动组ID
            self.active_group_id = group_id
    
    def show_nav_context_menu(self, group, position, button):
        """显示导航按钮的右键菜单（样式已由全局 QMenu 统一）"""
        group_id = group["id"]
        
        menu = QMenu(self)
        rename_action = menu.addAction("重命名")
        color_action = menu.addAction("设置颜色")
        reset_color_action = menu.addAction("重置颜色")
        menu.addSeparator()
        delete_action = menu.addAction("删除")
        
        # 移除禁止删除默认分组的限制
        # if group_id == "default":
        #     delete_action.setEnabled(False)
        
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
        group_colors = self.config.get("group_colors", {})
        current_color = group_colors.get(group_id, "#444444")
        
        # 弹出颜色选择对话框
        color = QColorDialog.getColor(QColor(current_color), self, f"选择 '{group_name}' 的颜色")
        
        if color.isValid():
            color_hex = color.name()
            
            # 保存颜色到配置
            if "group_colors" not in self.config:
                self.config["group_colors"] = {}
            self.config["group_colors"][group_id] = color_hex
            
            # 保存配置
            self.save_config()
            
            # 更新导航按钮样式
            if group_id in self.nav_buttons:
                nav_button = self.nav_buttons[group_id]
                nav_button.setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        padding: {s(8)}px {s(12)}px;
                        background-color: {color_hex};
                        border: none;
                        border-radius: {s(6)}px;
                        color: #E0E0E0;
                    }}
                    QPushButton:hover {{ background-color: {self.adjust_color_brightness(color_hex, 1.2)}; }}
                    QPushButton:pressed {{ background-color: {self.adjust_color_brightness(color_hex, 1.4)}; }}
                """)
    
    def reset_group_color(self, group):
        """重置分组颜色为默认"""
        group_id = group["id"]
        
        # 从配置中移除颜色设置
        group_colors = self.config.get("group_colors", {})
        if group_id in group_colors:
            del group_colors[group_id]
            
            # 保存配置
            self.save_config()
            
            # 恢复默认样式
            if group_id in self.nav_buttons:
                nav_button = self.nav_buttons[group_id]
                nav_button.setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        padding: {s(8)}px {s(12)}px;
                        background-color: #3a3a3a;
                        border: none;
                        border-radius: {s(6)}px;
                        color: #E0E0E0;
                    }}
                    QPushButton:hover {{ background-color: #4a4a4a; }}
                    QPushButton:pressed {{ background-color: #2f2f2f; }}
                """)
    
    def rename_group(self, group):
        """重命名组：重命名磁盘文件夹、更新 id/name/path、更新所有引用和 groups_order.json"""
        old_id = group["id"]
        old_name = group["name"]
        old_path = group.get("path", old_name)
        
        new_name, ok = QInputDialog.getText(
            self, "重命名分组", "请输入新的分组名称:",
            QLineEdit.Normal, old_name
        )
        if not ok or not new_name or new_name.strip() == "" or new_name == old_name:
            return
        new_name = new_name.strip()
        if "/" in new_name or "\\" in new_name:
            cmds.warning("分组名称不能包含路径字符")
            return
        
        new_group_dir = os.path.join(self.tools_dir, new_name)
        if os.path.exists(new_group_dir):
            cmds.warning(f"已存在名为 '{new_name}' 的文件夹，请换一个名称")
            return
        
        old_group_dir = os.path.join(self.tools_dir, old_path)
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
        for g in self.config["groups"]:
            if g["id"] == old_id:
                g["id"] = new_id
                g["name"] = new_name
                g["path"] = new_name
                break
        
        # 更新所有工具的 group 引用
        for tool in self.config.get("tools", []):
            if tool.get("group") == old_id:
                tool["group"] = new_id
        
        # 更新 group_containers 的键
        if old_id in self.group_containers:
            self.group_containers[new_id] = self.group_containers.pop(old_id)
            self.group_containers[new_id]["name"] = new_name
        
        # 更新 nav_items 的键，并更新树节点文字和 UserRole
        if old_id in self.nav_items:
            item = self.nav_items.pop(old_id)
            item.setText(0, new_name)
            item.setData(0, Qt.UserRole, new_id)
            self.nav_items[new_id] = item
        
        # 更新 nav_buttons 的键和按钮文字
        if old_id in self.nav_buttons:
            btn = self.nav_buttons.pop(old_id)
            count_match = re.search(r'\((\d+)\)$', btn.text())
            count_text = f" ({count_match.group(1)})" if count_match else ""
            btn.setText(f"{new_name}{count_text}")
            self.nav_buttons[new_id] = btn
        
        if self.active_group_id == old_id:
            self.active_group_id = new_id
        if self.content_title and self.active_group_id == new_id:
            self.content_title.setText(new_name)
        
        # 更新 groups_order.json：把旧名称替换为新名称
        try:
            if os.path.exists(self.groups_order_file):
                with open(self.groups_order_file, 'r', encoding='utf-8') as gf:
                    order_data = json.load(gf)
                if isinstance(order_data, list):
                    order_data = [new_name if n == old_name else n for n in order_data]
                    with open(self.groups_order_file, 'w', encoding='utf-8') as gf:
                        json.dump(order_data, gf, indent=4, ensure_ascii=False)
        except Exception as e:
            cmds.warning(f"更新分组顺序文件失败: {str(e)}")
        
        self.save_config()
        self.update_nav_button_counters()
        cmds.inViewMessage(message=f"已重命名为 '{new_name}'", pos='midCenter', fade=True)
    
    def delete_group(self, group):
        """删除组：将该组下所有脚本移入回收站，然后删除分组"""
        group_id = group["id"]
        group_name = group["name"]
        
        # 确认删除
        reply = QMessageBox.question(
            self, "删除分组",
            f"确定要删除分组 '{group_name}' 吗？\n该分组下的所有脚本将移入回收站。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 若只剩一个分组，先新建一个空分组，避免没有分组可选
        if len(self.config["groups"]) <= 1:
            new_group_name = "分组1"
            new_group_dir = os.path.join(self.tools_dir, new_group_name)
            counter = 1
            while os.path.exists(new_group_dir):
                new_group_name = f"分组{counter}"
                new_group_dir = os.path.join(self.tools_dir, new_group_name)
                counter += 1
            os.makedirs(new_group_dir)
            new_group_id = f"group_{int(time.time())}"
            new_group = {"id": new_group_id, "name": new_group_name}
            self.config["groups"].append(new_group)
        
        group_dir = os.path.join(self.tools_dir, group_name)
        # 收集本组内所有工具（用副本列表，避免遍历时修改）
        tools_in_group = [t for t in self.config["tools"] if t.get("group") == group_id]
        
        for tool in tools_in_group:
            tool_file = os.path.join(group_dir, tool.get("filename", ""))
            recycle_file = os.path.join(self.recycle_dir, tool.get("filename", ""))
            if not os.path.exists(tool_file):
                continue
            # 回收站内文件名冲突时重命名
            if os.path.exists(recycle_file) and tool_file != recycle_file:
                basename, ext = os.path.splitext(tool.get("filename", ""))
                n = 1
                new_filename = f"{basename}_{n}{ext}"
                while os.path.exists(os.path.join(self.recycle_dir, new_filename)):
                    n += 1
                    new_filename = f"{basename}_{n}{ext}"
                recycle_file = os.path.join(self.recycle_dir, new_filename)
                tool["filename"] = new_filename
            try:
                shutil.copy2(tool_file, recycle_file)
                os.remove(tool_file)
            except Exception as e:
                cmds.warning(f"移入回收站失败: {tool_file}, 错误: {str(e)}")
                continue
            tool["original_group"] = group_id
            tool["delete_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.config["tools"].remove(tool)
            self.config["recycle_bin"].append(tool)
        
        # 组目录内可能还有未在 config["tools"] 中的文件，一并移入回收站后删除目录
        try:
            if os.path.exists(group_dir):
                for file_name in os.listdir(group_dir):
                    path = os.path.join(group_dir, file_name)
                    if os.path.isfile(path):
                        dest = os.path.join(self.recycle_dir, file_name)
                        if os.path.exists(dest):
                            basename, ext = os.path.splitext(file_name)
                            n = 1
                            dest = os.path.join(self.recycle_dir, f"{basename}_{n}{ext}")
                            while os.path.exists(dest):
                                n += 1
                                dest = os.path.join(self.recycle_dir, f"{basename}_{n}{ext}")
                        try:
                            shutil.copy2(path, dest)
                            os.remove(path)
                        except Exception as e:
                            cmds.warning(f"移入回收站失败: {path}, 错误: {str(e)}")
                shutil.rmtree(group_dir, ignore_errors=True)
        except Exception as e:
            cmds.warning(f"删除分组目录失败: {group_dir}, 错误: {str(e)}")
        
        self.config["groups"] = [g for g in self.config["groups"] if g["id"] != group_id]
        need_select_new = (self.active_group_id == group_id)
        self.refresh_tools()
        
        if need_select_new and self.config["groups"]:
            self.show_group(self.config["groups"][0]["id"])
        elif self.active_group_id and self.active_group_id in self.group_containers:
            self.show_group(self.active_group_id)
        
        cmds.inViewMessage(message=f"已删除分组 '{group_name}'，脚本已移入回收站", pos='midCenter', fade=True)
    
    def show_recycle_bin(self):
        """显示回收站内容"""
        # 如果正在搜索，暂时切换到正常视图显示回收站，但保持搜索文本
        if hasattr(self, 'is_searching') and self.is_searching:
            # 保存当前搜索文本
            search_text = self.search_input.text()
            # 切换到正常视图
            self.switch_to_normal_view()
            # 恢复搜索文本但不执行搜索
            self.search_input.setText(search_text)
            # 标记为非搜索状态，这样用户可以看到回收站
            self.is_searching = False
        
        # 隐藏搜索结果和工具区域
        if hasattr(self, 'search_results_scroll'):
            self.search_results_scroll.setVisible(False)
        if hasattr(self, 'tool_scroll'):
            self.tool_scroll.setVisible(False)
        
        # 隐藏当前显示的组
        if self.active_group_id and self.active_group_id in self.group_containers:
            self.group_containers[self.active_group_id]["panel"].setVisible(False)
            
            # 重置导航按钮样式
            if self.active_group_id in self.nav_buttons:
                self.nav_buttons[self.active_group_id].setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        padding: {s(8)}px {s(12)}px;
                        background-color: #3a3a3a;
                        border: none;
                        border-radius: {s(6)}px;
                        color: #E0E0E0;
                    }}
                    QPushButton:hover {{ background-color: #4a4a4a; }}
                    QPushButton:pressed {{ background-color: #2f2f2f; }}
                """)
        
        # 加载回收站内容
        self.load_recycle_bin()
        
        # 设置回收站可见
        self.recycle_bin_scroll.setVisible(True)
        self.content_title.setText("回收站")
        self.recycle_bin_visible = True
        
        # 高亮回收站按钮（与选中分组一致的主色）
        self.recycle_bin_btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: {s(8)}px {s(12)}px;
                background-color: #3A6EA5;
                border: none;
                border-radius: {s(6)}px;
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #4A7EB5; }}
            QPushButton:pressed {{ background-color: #2A5E95; }}
        """)
        
        # 更新当前活动组ID为null，表示在回收站中
        self.active_group_id = None
    
    def load_recycle_bin(self):
        """加载回收站内容"""
        # 清除当前回收站UI中的项目
        self.clear_layout(self.recycle_bin_layout)
        
        # 添加回收站顶部操作区域
        header_widget = QWidget()
        header_widget.setObjectName("recycleHeader")
        header_widget.setStyleSheet("""
            #recycleHeader {{
                background-color: #2D2D2D;
                border-radius: {s(5)}px;
                margin-bottom: {s(10)}px;
            }}
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(s(15), s(15), s(15), s(15))
        header_layout.setSpacing(s(10))
        
        # 添加说明文本
        desc_label = QLabel("此处显示已删除的脚本，您可以选择恢复或永久删除它们。")
        desc_label.setStyleSheet("color: #BBBBBB; font-style: italic; padding: 0px;")
        desc_label.setWordWrap(True)
        header_layout.addWidget(desc_label)
        
        # 操作按钮区域
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, s(5), 0, s(5))
        actions_layout.setSpacing(s(10))
        
        # 清空回收站按钮
        clear_btn = QPushButton("清空回收站")
        clear_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #a83232; 
                color: white;
                padding: {s(8)}px {s(12)}px;
                border-radius: {s(4)}px;
            }}
            QPushButton:hover {{
                background-color: #b84242;
            }}
            QPushButton:pressed {{
                background-color: #982222;
            }}
        """)
        clear_btn.clicked.connect(self.clear_recycle_bin)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2D5578;
                color: white;
                padding: {s(8)}px {s(12)}px;
                border-radius: {s(4)}px;
            }}
            QPushButton:hover {{
                background-color: #3A6EA5;
            }}
            QPushButton:pressed {{
                background-color: #224466;
            }}
        """)
        refresh_btn.clicked.connect(self.load_recycle_bin)
        
        # 添加按钮到布局
        actions_layout.addWidget(refresh_btn)
        actions_layout.addStretch(1)
        actions_layout.addWidget(clear_btn)
        
        header_layout.addLayout(actions_layout)
        self.recycle_bin_layout.addWidget(header_widget)
        
        # 如果回收站为空，显示一个提示信息
        if not self.config.get("recycle_bin"):
            empty_widget = QWidget()
            empty_widget.setObjectName("emptyRecycleBin")
            empty_widget.setStyleSheet(f"""
                #emptyRecycleBin {{
                    background-color: #2D2D2D;
                    border-radius: {s(5)}px;
                }}
            """)
            empty_layout = QVBoxLayout(empty_widget)
            
            # 添加空回收站图标
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignCenter)
            # 获取标准图标并设置大小
            pixmap = self.style().standardIcon(QStyle.SP_TrashIcon).pixmap(s(64), s(64))
            icon_label.setPixmap(pixmap)
            empty_layout.addWidget(icon_label)
            
            # 添加文本
            empty_label = QLabel("回收站为空")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet(f"color: #AAAAAA; font-size: {s(16)}px; padding: {s(10)}px;")
            empty_layout.addWidget(empty_label)
            
            empty_layout.setContentsMargins(s(20), s(30), s(20), s(30))
            self.recycle_bin_layout.addWidget(empty_widget)
            
            # 添加底部空间
            spacer = QWidget()
            spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.recycle_bin_layout.addWidget(spacer)
            return
        
        # 添加已删除项目的列表容器
        items_container = QWidget()
        items_container.setObjectName("recycleItems")
        items_container.setStyleSheet(f"""
            #recycleItems {{
                background-color: #2D2D2D;
                border-radius: {s(5)}px;
            }}
        """)
        items_layout = QVBoxLayout(items_container)
        items_layout.setContentsMargins(s(15), s(15), s(15), s(15))
        items_layout.setSpacing(s(8))
        
        # 添加标题
        items_count = len(self.config.get("recycle_bin", []))
        title_label = QLabel(f"已删除项目 ({items_count})")
        title_label.setStyleSheet(f"color: #CCCCCC; font-size: {s(14)}px; font-weight: bold;")
        items_layout.addWidget(title_label)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet(f"background-color: #555555; margin: {s(5)}px 0;")
        items_layout.addWidget(line)
        
        # 为每个回收站项目创建一个卡片（与全局面板风格一致）
        for deleted_item in self.config["recycle_bin"]:
            item_widget = QWidget()
            item_widget.setObjectName("recycleItem")
            item_widget.setStyleSheet(f"""
                #recycleItem {{
                    background-color: #3a3a3a;
                    border: 1px solid #444444;
                    border-radius: {s(6)}px;
                    margin: {s(2)}px 0;
                }}
                #recycleItem:hover {{
                    background-color: #444444;
                }}
            """)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(s(12), s(10), s(12), s(10))
            item_layout.setSpacing(s(10))
            
            # 脚本类型图标
            icon_label = QLabel()
            if deleted_item['type'] == 'python':
                # 为Python脚本添加图标
                pixmap = self.style().standardIcon(QStyle.SP_FileIcon).pixmap(s(34), s(34))
                icon_label.setPixmap(pixmap)
                icon_label.setStyleSheet(f"background-color: #4A6D4A; border-radius: {s(6)}px; padding: {s(4)}px;")
            else:
                # 为MEL脚本添加图标
                pixmap = self.style().standardIcon(QStyle.SP_FileIcon).pixmap(s(34), s(34))
                icon_label.setPixmap(pixmap)
                icon_label.setStyleSheet(f"background-color: #4D6B8A; border-radius: {s(6)}px; padding: {s(4)}px;")
            
            icon_label.setFixedSize(s(38), s(38))
            item_layout.addWidget(icon_label)
            
            # 脚本信息区域
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(s(3))
            
            # 脚本名称
            name_label = QLabel(deleted_item["name"])
            name_label.setStyleSheet(f"font-weight: bold; color: #E0E0E0; font-size: {s(14)}px;")
            info_layout.addWidget(name_label)
            
            # 文件名信息
            filename_label = QLabel(f"文件: {deleted_item.get('filename', '未知')}")
            filename_label.setStyleSheet(f"color: #AAAAAA; font-size: {s(12)}px;")
            info_layout.addWidget(filename_label)
            
            # 组合文件类型和删除日期信息
            details_layout = QHBoxLayout()
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setSpacing(s(10))
            
            # 脚本类型
            type_badge = "Python" if deleted_item['type'] == 'python' else "MEL"
            type_color = "#4A6D4A" if deleted_item['type'] == 'python' else "#4D6B8A"
            type_label = QLabel(f"<span style='background-color:{type_color}; padding:{s(4)}px {s(12)}px; border-radius:{s(6)}px; color:white; font-size:{s(12)}px;'>{type_badge}</span>")
            details_layout.addWidget(type_label)
            
            # 添加删除日期信息
            if "delete_date" in deleted_item:
                date_label = QLabel(f"删除于: {deleted_item['delete_date']}")
                date_label.setStyleSheet(f"color: #AAAAAA; font-size: {s(12)}px;")
                details_layout.addWidget(date_label)
            
            # 添加原分组信息
            if "original_group" in deleted_item:
                group_id = deleted_item["original_group"]
                group_name = "默认分组"
                for group in self.config["groups"]:
                    if group["id"] == group_id:
                        group_name = group["name"]
                        break
                original_group_label = QLabel(f"原分组: {group_name}")
                original_group_label.setStyleSheet(f"color: #AAAAAA; font-size: {s(12)}px;")
                details_layout.addWidget(original_group_label)
            
            details_layout.addStretch(1)
            info_layout.addLayout(details_layout)
            
            item_layout.addWidget(info_widget, 1)  # 让信息区域占据主要空间
            
            # 操作按钮区域
            buttons_widget = QWidget()
            buttons_layout = QHBoxLayout(buttons_widget)
            buttons_layout.setContentsMargins(0, 0, 0, 0)
            buttons_layout.setSpacing(s(6))
            
            # 恢复按钮（主色）
            restore_btn = QPushButton("恢复")
            restore_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
            restore_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #3A6EA5;
                    color: white;
                    padding: {s(6)}px {s(12)}px;
                    border-radius: {s(6)}px;
                }}
                QPushButton:hover {{ background-color: #4A7EB5; }}
                QPushButton:pressed {{ background-color: #2A5E95; }}
            """)
            restore_btn.setToolTip("恢复此脚本到原分组")
            restore_btn.clicked.connect(partial(self.restore_from_recycle_bin, deleted_item))
            buttons_layout.addWidget(restore_btn)
            
            # 永久删除按钮（危险色）
            delete_btn = QPushButton("删除")
            delete_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogDiscardButton))
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #a83232;
                    color: white;
                    padding: {s(6)}px {s(12)}px;
                    border-radius: {s(6)}px;
                }}
                QPushButton:hover {{ background-color: #b84242; }}
                QPushButton:pressed {{ background-color: #982222; }}
            """)
            delete_btn.setToolTip("永久删除此脚本")
            delete_btn.clicked.connect(partial(self.permanently_delete, deleted_item))
            buttons_layout.addWidget(delete_btn)
            
            item_layout.addWidget(buttons_widget)
            
            # 添加到回收站容器
            items_layout.addWidget(item_widget)
        
        self.recycle_bin_layout.addWidget(items_container)
        
        # 添加底部空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.recycle_bin_layout.addWidget(spacer)
    
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
        """清空回收站"""
        # 确认对话框
        result = QMessageBox.question(
            self,
            "清空回收站",
            "确定要永久删除回收站中的所有项目吗？此操作无法撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
            
        try:
            # 清空回收站目录中的文件
            for item in self.config.get("recycle_bin", []):
                # 删除脚本文件
                recycle_file = os.path.join(self.recycle_dir, item.get("filename", ""))
                if os.path.exists(recycle_file):
                    os.remove(recycle_file)
            
            # 清空回收站配置
            self.config["recycle_bin"] = []
            
            # 保存配置
            self.save_config()
            
            # 重新加载回收站
            self.load_recycle_bin()
            
            # 更新回收站按钮文本
            self.recycle_bin_btn.setText(f"回收站 (0)")
            
            cmds.inViewMessage(message="回收站已清空", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"清空回收站失败: {str(e)}")
            QMessageBox.critical(self, "操作失败", f"清空回收站失败: {str(e)}")
    
    def restore_from_recycle_bin(self, deleted_item):
        """从回收站恢复项目"""
        try:
            # 获取文件路径
            recycle_file = os.path.join(self.recycle_dir, deleted_item.get("filename", ""))
            
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
                for group in self.config["groups"]:
                    if group["id"] == original_group:
                        group_name = group["name"]
                        group_exists = True
                        break
            
            # 如果组不存在，使用第一个可用组
            if not group_exists:
                if self.config["groups"]:
                    original_group = self.config["groups"][0]["id"]
                    group_name = self.config["groups"][0]["name"]
                else:
                    # 如果没有任何分组，创建一个新分组
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
                    original_group = "new_default_" + str(int(time.time()))
                    new_group = {
                        "id": original_group,
                        "name": new_group_name
                    }
                    
                    # 添加到配置
                    self.config["groups"].append(new_group)
                    group_name = new_group_name
            
            # 确保目标组目录存在
            group_dir = os.path.join(self.tools_dir, group_name)
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
            self.config["recycle_bin"].remove(deleted_item)
            
            # 重新添加到工具列表
            tool_info = {
                "name": deleted_item.get("name", "未命名工具"),
                "filename": deleted_item.get("filename", ""),
                "type": deleted_item.get("type", "python"),
                "group": original_group,
                "tooltip": deleted_item.get("tooltip", "")
            }
            
            # 保存配置
            self.save_config()
            
            # 刷新工具显示
            self.refresh_tools()
            
            # 更新回收站按钮
            recycle_count = len(self.config.get("recycle_bin", []))
            self.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            # 刷新回收站显示
            self.load_recycle_bin()
            
            cmds.inViewMessage(message=f"已恢复: {tool_info['name']}", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"恢复失败: {str(e)}")
            QMessageBox.critical(self, "恢复失败", f"恢复失败: {str(e)}")
    
    def permanently_delete(self, deleted_item):
        """永久删除回收站中的项目"""
        try:
            # 确认对话框
            result = QMessageBox.question(
                self,
                "永久删除",
                f"确定要永久删除 '{deleted_item.get('name', '未命名工具')}' 吗？此操作无法撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
                
            # 获取文件路径
            recycle_file = os.path.join(self.recycle_dir, deleted_item.get("filename", ""))
            
            # 删除文件
            if os.path.exists(recycle_file):
                os.remove(recycle_file)
            
            # 从回收站列表中移除
            self.config["recycle_bin"].remove(deleted_item)
            
            # 保存配置
            self.save_config()
            
            # 更新回收站按钮
            recycle_count = len(self.config.get("recycle_bin", []))
            self.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            # 刷新回收站显示
            self.load_recycle_bin()
            
            cmds.inViewMessage(message=f"已永久删除: {deleted_item.get('name', '未命名工具')}", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"删除失败: {str(e)}")
            QMessageBox.critical(self, "删除失败", f"删除失败: {str(e)}")
    
    def delete_tool(self, tool, button):
        """将工具移动到回收站"""
        try:
            # 确认对话框
            result = QMessageBox.question(
                self,
                "删除工具",
                f"确定要将 '{tool['name']}' 移到回收站吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
                
            # 查找工具所在的组
            group_id = tool.get("group", "default")
            group_name = "常用工具"
            for group in self.config["groups"]:
                if group["id"] == group_id:
                    group_name = group["name"]
                    break
            
            # 获取文件路径
            group_dir = os.path.join(self.tools_dir, group_name)
            tool_file = os.path.join(group_dir, tool.get("filename", ""))
            recycle_file = os.path.join(self.recycle_dir, tool.get("filename", ""))
            
            # 确保文件存在
            if not os.path.exists(tool_file):
                raise ValueError(f"工具文件不存在: {tool_file}")
            
            # 处理文件名冲突
            if os.path.exists(recycle_file) and tool_file != recycle_file:
                basename, ext = os.path.splitext(tool.get("filename", ""))
                counter = 1
                new_filename = f"{basename}_{counter}{ext}"
                while os.path.exists(os.path.join(self.recycle_dir, new_filename)):
                    counter += 1
                    new_filename = f"{basename}_{counter}{ext}"
                
                # 更新回收站文件路径和工具文件名
                recycle_file = os.path.join(self.recycle_dir, new_filename)
                tool["filename"] = new_filename
            
            # 移动文件到回收站目录
            shutil.copy2(tool_file, recycle_file)
            os.remove(tool_file)
            
            # 从工具列表中移除
            self.config["tools"].remove(tool)
            
            # 添加组信息和删除日期到工具信息中
            tool["original_group"] = group_id
            tool["delete_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 添加到回收站列表
            self.config["recycle_bin"].append(tool)
            
            # 保存配置
            self.save_config()
            
            # 删除按钮
            if button in self.tool_buttons:
                button_item = self.tool_buttons[button]
                group_id = button_item.get("group_id")
                
                if group_id in self.group_containers:
                    layout = self.group_containers[group_id]["layout"]
                    
                    # 处理不同的布局类型
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
                    
                    # 删除按钮
                    button.deleteLater()
                    
                    # 移除引用
                    del self.tool_buttons[button]
            
            # 更新导航按钮计数
            self.update_nav_button_counters()
            
            # 更新回收站按钮
            recycle_count = len(self.config.get("recycle_bin", []))
            self.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            cmds.inViewMessage(message=f"已将 '{tool['name']}' 移动到回收站", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"删除失败: {str(e)}")
            QMessageBox.critical(self, "删除失败", f"删除失败: {str(e)}")
    
    def create_nav_button(self, group):
        """创建导航栏按钮（或树形界面下向树添加一项）"""
        group_id = group["id"]
        group_name = group["name"]
        
        # 当前界面为树形导航（无 nav_buttons_layout）时，向树添加新项即可
        if not getattr(self, 'nav_buttons_layout', None):
            root = self.nav_tree.invisibleRootItem()
            item = QTreeWidgetItem(root, [f"{group_name} (0)"])
            item.setData(0, Qt.UserRole, group_id)
            self.nav_items[group_id] = item
            self.nav_tree.expandAll()
            return None
        
        # 创建导航按钮（按钮布局模式）
        nav_button = DraggableGroupButton(group_name, group_id, self)
        
        # 获取分组自定义颜色
        group_colors = self.config.get("group_colors", {})
        custom_color = group_colors.get(group_id, None)
        
        if custom_color:
            # 使用自定义颜色
            nav_button.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: {s(8)}px {s(10)}px;
                    background-color: {custom_color};
                    border: none;
                    border-radius: {s(3)}px;
                    margin: {s(2)}px;
                    color: #E0E0E0;
                }}
                QPushButton:hover {{
                    background-color: {self.adjust_color_brightness(custom_color, 1.2)};
                }}
                QPushButton:pressed {{
                    background-color: {self.adjust_color_brightness(custom_color, 1.4)};
                }}
            """)
        else:
            nav_button.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: {s(8)}px {s(12)}px;
                    background-color: #3a3a3a;
                    border: none;
                    border-radius: {s(6)}px;
                    color: #E0E0E0;
                }}
                QPushButton:hover {{ background-color: #4a4a4a; }}
                QPushButton:pressed {{ background-color: #2f2f2f; }}
            """)
        
        # 设置上下文菜单策略
        nav_button.setContextMenuPolicy(Qt.CustomContextMenu)
        nav_button.customContextMenuRequested.connect(lambda pos, g=group: self.show_nav_context_menu(g, pos, nav_button))
        
        # 点击导航按钮显示对应组
        nav_button.clicked.connect(lambda: self.show_group(group_id))
        
        # 添加到导航栏布局并存储引用
        self.nav_buttons_layout.addWidget(nav_button)
        self.nav_buttons[group_id] = nav_button
        
        return nav_button
    
    def adjust_color_brightness(self, color, factor):
        """调整颜色亮度"""
        try:
            # 移除#号
            if color.startswith('#'):
                color = color[1:]
            
            # 转换为RGB
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            
            # 调整亮度
            r = min(255, int(r * factor))
            g = min(255, int(g * factor))
            b = min(255, int(b * factor))
            
            # 转换回十六进制
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            # 如果转换失败，返回默认颜色
            return "#555" if factor > 1 else "#333"
    
    def update_nav_button_counters(self):
        """更新树导航项上的工具计数"""
        group_counts = {}
        for group in self.config["groups"]:
            group_counts[group["id"]] = 0
        for tool in self.config["tools"]:
            gid = tool.get("group")
            if gid in group_counts:
                group_counts[gid] += 1
        for gid, count in group_counts.items():
            item = self.nav_items.get(gid)
            if item:
                # 仅替换显示名称，不影响UserRole
                name = None
                for g in self.config["groups"]:
                    if g["id"] == gid:
                        name = g["name"]
                        break
                if name is not None:
                    item.setText(0, f"{name} ({count})")
    
    def on_nav_tree_context_menu(self, pos):
        """树导航右键菜单"""
        item = self.nav_tree.itemAt(pos)
        if not item:
            return
        gid = item.data(0, Qt.UserRole)
        group = next((g for g in self.config["groups"] if g["id"] == gid), None)
        if not group:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除分组")
        action = menu.exec_(self.nav_tree.viewport().mapToGlobal(pos))
        if action == rename_action:
            self.rename_group(group)
        elif action == delete_action:
            self.delete_group(group)
    
    def create_tool_button(self, tool, group_id=None):
        """创建工具按钮，并添加到指定组"""
        button = MiddleClickButton(tool["name"])
        button.set_tool_data(tool, self)
        
        # 根据脚本类型设置图标
        try:
            icons_dir = os.path.join(self.current_dir, "icons")
            if tool["type"] == "mel":
                icon_path = os.path.join(icons_dir, "mel.png")
            else:
                icon_path = os.path.join(icons_dir, "python.png")
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))
                button.setIconSize(QSize(s(20), s(20)))
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
                font-size: {s(13)}px;
                color: #EFEFEF;
                background-color: #2A2A2A;
                padding: {s(10)}px;
                border: 1px solid #444444;
                border-radius: {s(5)}px;
                max-width: {s(350)}px;
                box-shadow: {s(2)}px {s(2)}px {s(10)}px rgba(0, 0, 0, 0.3);
            ">
                <div style="
                    font-size: {s(14)}px;
                    border-bottom: 1px solid #444444;
                    padding-bottom: {s(6)}px;
                    margin-bottom: {s(8)}px;
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
        if group_id and group_id in self.group_containers:
            container = self.group_containers[group_id]
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
            if self.config["groups"]:
                first_group_id = self.config["groups"][0]["id"]
                if first_group_id in self.group_containers:
                    container = self.group_containers[first_group_id]
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
                    self.tools_layout.addWidget(button)
            else:
                # 如果没有任何分组，添加到主布局
                self.tools_layout.addWidget(button)
                
        # 存储按钮引用
        self.tool_buttons[button] = {
            "tool": tool,
            "group_id": group_id
        }
        
        return button
    
    def run_tool(self, tool):
        """运行工具脚本"""
        # 查找工具所在组
        group_id = tool.get("group")
        if not group_id:
            cmds.warning(f"工具没有指定分组: {tool['name']}")
            return
            
        group_name = None
        group_path_rel = None
        for group in self.config["groups"]:
            if group["id"] == group_id:
                group_name = group["name"]
                group_path_rel = group.get("path")
                break
                
        if not group_name:
            cmds.warning(f"找不到工具所属分组: {tool['name']}")
            return
        
        # 获取组目录
        if group_path_rel:
            group_dir = os.path.join(self.tools_dir, group_path_rel.replace("/", os.sep))
        else:
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
                        cmds.warning(f"在组 '{search_group_name}' 中找到工具文件")
                        # 更新工具所属组
                        tool["group"] = search_group["id"]
                        found = True
                        break
                
                if not found:
                    cmds.warning(f"在所有分组中都找不到工具文件 {tool['filename']}，无法运行")
                    return
        
        if tool["type"] == "mel":
            # 运行MEL脚本
            mel_path = tool_path.replace('\\', '/')
            # 首先获取文件基本名（不带扩展名）
            basename = os.path.splitext(os.path.basename(mel_path))[0]
            
            # 使用Python包装执行MEL，避免语法问题
            py_cmd = f"""
import os
import sys
import traceback
try:
    import maya.mel as mel
    import maya.cmds as cmds
    
    # 获取脚本路径
    mel_path = r"{mel_path}"
    mel_dir = os.path.dirname(mel_path)
    basename = r"{basename}"  # 直接从外部传入basename
    
    # 保存当前工作目录
    original_dir = os.getcwd()
    
    # 设置工作目录为脚本所在目录，这对MEL脚本很重要
    os.chdir(mel_dir)
    
    # 将脚本目录添加到MEL路径
    mel_script_path = mel.eval('getenv "MAYA_SCRIPT_PATH"')
    if mel_dir not in mel_script_path.split(';'):
        mel.eval(f'putenv "MAYA_SCRIPT_PATH" "{{mel_dir}};{{mel_script_path}}"')
    
    # 检查文件是否存在
    if not os.path.exists(mel_path):
        cmds.warning(f"MEL脚本文件不存在: {{mel_path}}")
        raise FileNotFoundError(f"MEL脚本文件不存在: {{mel_path}}")
    
    # 读取文件内容
    try:
        with open(mel_path, 'r', encoding='utf-8', errors='ignore') as f:
            mel_content = f.read()
    except UnicodeDecodeError:
        try:
            with open(mel_path, 'r', encoding='gbk', errors='ignore') as f:
                mel_content = f.read()
        except UnicodeDecodeError:
            with open(mel_path, 'r', encoding='latin-1') as f:
                mel_content = f.read()
    
    # 首先尝试使用source命令
    try:
        mel.eval(f'source "{{mel_path}}";')
        cmds.inViewMessage(message=f"已执行MEL脚本: {os.path.basename(mel_path)}", pos='midCenter', fade=True, fadeStayTime=1000)
    except Exception as e:
        # 如果source失败，尝试直接执行脚本内容
        cmds.warning(f"使用source执行MEL脚本失败，尝试直接执行脚本内容: {{str(e)}}")
        try:
            mel.eval(mel_content)
            cmds.inViewMessage(message=f"已直接执行MEL脚本: {os.path.basename(mel_path)}", pos='midCenter', fade=True, fadeStayTime=1000)
        except Exception as inner_e:
            # 如果直接执行也失败，尝试检测和执行脚本中的主要过程
            cmds.warning(f"直接执行MEL脚本内容失败: {{str(inner_e)}}")
            
            # 尝试查找并执行主过程（通常是与文件名相同的过程）
            try:
                # 检查过程是否存在
                proc_exists = mel.eval(f'exists "{basename}";')
                if proc_exists:
                    # 执行找到的过程
                    mel.eval(f'{basename};')
                    cmds.inViewMessage(message=f"已执行MEL过程: {basename}", pos='midCenter', fade=True, fadeStayTime=1000)
                else:
                    # 如果没有找到与文件名相同的过程，显示错误
                    raise Exception(f"找不到MEL过程: {basename}")
            except Exception as proc_e:
                error_msg = traceback.format_exc()
                cmds.warning(f"执行MEL过程失败: {{str(proc_e)}}\\n{{error_msg}}")
    
    # 恢复原始工作目录
    os.chdir(original_dir)
    
except Exception as e:
    import maya.cmds as cmds
    error_msg = traceback.format_exc()
    cmds.warning(f"执行MEL脚本出错: {{str(e)}}\\n{{error_msg}}")
"""
            try:
                # 使用evalDeferred确保在Maya主循环中运行
                cmds.evalDeferred(py_cmd)
            except Exception as e:
                cmds.warning(f"运行MEL脚本出错: {str(e)}")
        else:
            # 运行Python脚本
            try:
                # 确保脚本所在目录在路径中
                if self.tools_dir not in sys.path:
                    sys.path.append(self.tools_dir)
                
                # 添加组目录到路径
                script_dir = os.path.dirname(tool_path)
                if script_dir not in sys.path:
                    sys.path.append(script_dir)
                
                # 工具脚本的绝对路径
                abs_script_path = os.path.abspath(tool_path)
                script_dir = os.path.dirname(abs_script_path)
                
                # 创建在Maya主循环中执行的命令
                exec_cmd = f"""
import os
import sys
import traceback

try:
    # 添加脚本目录到路径
    script_dir = r"{script_dir}"
    tools_dir = r"{self.tools_dir}"
    
    # 确保目录在sys.path中
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    
    # 设置工作目录
    original_dir = os.getcwd()
    os.chdir(script_dir)
    
    # 加载脚本
    script_path = r"{abs_script_path}"
    
    # 检查文件是否存在
    if not os.path.exists(script_path):
        import maya.cmds as cmds
        cmds.warning(f"脚本文件不存在: {{script_path}}")
        raise FileNotFoundError(f"脚本文件不存在: {{script_path}}")
    
    # 执行代码
    with open(script_path, 'r', encoding='utf-8') as f:
        code = compile(f.read(), script_path, 'exec')
        exec(code, {{'__file__': script_path, '__name__': '__main__'}})
    
    # 恢复工作目录
    os.chdir(original_dir)
except UnicodeDecodeError:
    # 尝试不同编码
    try:
        with open(r"{abs_script_path}", 'r', encoding='gbk') as f:
            code = compile(f.read(), r"{abs_script_path}", 'exec')
            exec(code, {{'__file__': r"{abs_script_path}", '__name__': '__main__'}})
    except Exception as e:
        import maya.cmds as cmds
        error_msg = traceback.format_exc()
        cmds.warning(f"GBK编码运行脚本出错: {{str(e)}}\\n{{error_msg}}")
except FileNotFoundError as e:
    import maya.cmds as cmds
    cmds.warning(f"文件未找到: {{str(e)}}")
except Exception as e:
    import maya.cmds as cmds
    error_msg = traceback.format_exc()
    cmds.warning(f"运行Python脚本出错: {{str(e)}}\\n{{error_msg}}")
"""
                # 使用evalDeferred执行
                cmds.evalDeferred(exec_cmd)
            except Exception as e:
                cmds.warning(f"准备执行脚本时出错: {str(e)}")
    
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
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: {s(5)}px;
            }}
            QMenu::item {{
                padding: {s(5)}px {s(25)}px {s(5)}px {s(20)}px;
                border: 1px solid transparent;
            }}
            QMenu::item:selected {{
                background-color: #3a3a3a;
                color: #ffffff;
            }}
        """)

        # 创建菜单项
        is_pinned = self.is_tool_pinned(tool)
        pin_action = QAction("取消置顶" if is_pinned else "置顶", self)
        edit_action = QAction("编辑", self)
        edit_tooltip_action = QAction("编辑提示", self)
        color_action = QAction("自定义颜色", self)
        move_action = QAction("移动到组", self)
        open_folder_action = QAction("打开文件夹", self)
        delete_action = QAction("删除", self)
        settings_action = QAction("设置", self)

        # 添加分隔线和菜单项
        menu.addAction(pin_action)
        menu.addAction(edit_action)
        menu.addAction(edit_tooltip_action)
        menu.addAction(color_action)
        
        # 创建移动到组的子菜单
        move_menu = QMenu("移动到组", self)
        move_menu.setStyleSheet(menu.styleSheet())
        
        # 添加现有组到子菜单
        move_actions = {}
        current_group_id = tool.get("group", "default")
        
        if self.config and "groups" in self.config:
            for group in self.config["groups"]:
                if "id" in group and "name" in group:
                    group_id = group["id"]
                    group_name = group["name"]
                    
                    # 当前所在分组不显示
                    if group_id == current_group_id:
                        continue
                        
                    group_action = QAction(group_name, self)
                    move_menu.addAction(group_action)
                    move_actions[group_action] = group_id
        
        # 添加新建组选项
        move_menu.addSeparator()
        new_group_action = QAction("新建分组", self)
        move_menu.addAction(new_group_action)
        
        # 将移动到组子菜单添加到主菜单
        menu.addMenu(move_menu)
        
        menu.addSeparator()
        menu.addAction(open_folder_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(settings_action)

        # 显示菜单
        action = menu.exec_(button.mapToGlobal(position))
        
        # 处理选择
        if action == pin_action:
            self.toggle_pin(tool)
        elif action == delete_action:
            self.delete_tool(tool, button)
        elif action == edit_action:
            self.edit_tool(tool)
        elif action == edit_tooltip_action:
            self.edit_tool_tooltip(tool, button)
        elif action == color_action:
            self.show_color_picker(tool, button)
        elif action == open_folder_action:
            self.open_tool_folder(tool)
        elif action == settings_action:
            self.show_settings_dialog()
        elif action == new_group_action:
            self.create_new_group(tool, button)
        elif action in move_actions:
            # 移动工具到选定的分组
            new_group_id = move_actions[action]
            self.move_tool_to_group(tool, button, new_group_id)
    
    def show_color_picker(self, tool, button):
        """显示颜色选择器"""
        from PySide2.QtWidgets import QColorDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame
        from PySide2.QtCore import Qt
        from PySide2.QtGui import QColor
        
        # 创建自定义颜色选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("选择按钮颜色")
        dialog.setMinimumSize(400, 300)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #333333;
                color: #E0E0E0;
            }}
            QLabel {{
                color: #E0E0E0;
                font-size: {s(14)}px;
            }}
            QPushButton {{
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: {s(8)}px {s(16)}px;
                border-radius: {s(4)}px;
                font-size: {s(14)}px;
            }}
            QPushButton:hover {{
                background-color: #666666;
            }}
            QPushButton:pressed {{
                background-color: #444444;
            }}
            QFrame {{
                border: 1px solid #555555;
                border-radius: {s(4)}px;
            }}
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
            ("紫色", "#A8E6CF"),
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
        if "button_colors" not in self.config:
            self.config["button_colors"] = {}
        
        # 使用文件名作为键
        tool_key = tool["filename"]
        
        if color is None:
            # 移除自定义颜色，使用默认颜色
            if tool_key in self.config["button_colors"]:
                del self.config["button_colors"][tool_key]
        else:
            # 设置自定义颜色
            self.config["button_colors"][tool_key] = color
        
        # 保存配置
        self.save_config()
        
        # 更新按钮样式
        self.apply_button_color(button, tool)
    
    def apply_button_color(self, button, tool):
        """应用按钮颜色"""
        try:
            # 获取自定义颜色
            custom_color = None
            if "button_colors" in self.config:
                custom_color = self.config["button_colors"].get(tool["filename"])
            
            # 置顶视觉标记
            pinned_border = f"border-left: {s(6)}px solid #4A90E2;" if tool.get("pinned") else ""
            
            if custom_color:
                # 使用自定义颜色（文件按钮字体比全局大 2px）
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {custom_color};
                        color: #000000;
                        text-align: left;
                        padding: {s(8)}px {s(12)}px;
                        border-radius: {s(6)}px;
                        border: 1px solid #555555;
                        font-size: {s(18)}px;
                        {pinned_border}
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(custom_color)};
                        border: 1px solid #FFFFFF;
                        {pinned_border}
                    }}
                    QPushButton:pressed {{
                        background-color: {self.darken_color(custom_color)};
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
                        padding: {s(8)}px {s(12)}px;
                        border-radius: {s(6)}px;
                        border: 1px solid #555555;
                        font-size: {s(18)}px;
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
        except RuntimeError:
            # 对象已删除，忽略
            pass
        except Exception as e:
            cmds.warning(f"应用按钮颜色失败: {str(e)}")
    
    def lighten_color(self, color_hex):
        """使颜色变亮"""
        try:
            # 移除#号
            color_hex = color_hex.lstrip('#')
            # 转换为RGB
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
            # 增加亮度
            r = min(255, r + 30)
            g = min(255, g + 30)
            b = min(255, b + 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color_hex
    
    def darken_color(self, color_hex):
        """使颜色变暗"""
        try:
            # 移除#号
            color_hex = color_hex.lstrip('#')
            # 转换为RGB
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
            # 降低亮度
            r = max(0, r - 30)
            g = max(0, g - 30)
            b = max(0, b - 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color_hex
    
    def edit_tool_tooltip(self, tool, button):
        """编辑工具的提示信息"""
        # 获取当前提示信息
        current_tooltip = tool.get("tooltip", "")
        
        # 创建输入对话框
        dialog = QDialog(self)
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
        example_label.setStyleSheet(f"color: #8899AA; font-family: monospace; font-size: {s(12)}px;")
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
            self.save_config()
            
            # 更新按钮提示
            if new_tooltip:
                title = tool["name"]
                styled_tooltip = f"""
                <div style="
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    font-size: {s(13)}px;
                    color: #EFEFEF;
                    background-color: #2A2A2A;
                    padding: {s(10)}px;
                    border: 1px solid #444444;
                    border-radius: {s(5)}px;
                    max-width: {s(350)}px;
                    box-shadow: {s(2)}px {s(2)}px {s(10)}px rgba(0, 0, 0, 0.3);
                ">
                    <div style="
                        font-weight: bold;
                        font-size: {s(14)}px;
                        border-bottom: 1px solid #444444;
                        padding-bottom: {s(6)}px;
                        margin-bottom: {s(8)}px;
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
                    font-size: {s(13)}px;
                    color: #EFEFEF;
                    background-color: #2A2A2A;
                    padding: {s(10)}px;
                    border: 1px solid #444444;
                    border-radius: {s(5)}px;
                    max-width: {s(350)}px;
                    box-shadow: {s(2)}px {s(2)}px {s(10)}px rgba(0, 0, 0, 0.3);
                ">
                    <div style="
                        font-weight: bold;
                        font-size: {s(14)}px;
                        border-bottom: 1px solid #444444;
                        padding-bottom: {s(6)}px;
                        margin-bottom: {s(8)}px;
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
            
            # 获取文件所在的目录
            folder_path = os.path.dirname(tool_path)
            
            # 在Windows资源管理器中打开文件夹并选中文件
            if os.name == 'nt':  # Windows
                subprocess.Popen(['explorer', '/select,', tool_path])
            else:  # macOS/Linux
                if sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', '-R', tool_path])
                else:  # Linux
                    subprocess.Popen(['xdg-open', folder_path])
            
            cmds.inViewMessage(message="已打开文件夹", pos='midCenter', fade=True)
            
        except Exception as e:
            cmds.inViewMessage(message=f"打开文件夹失败: {str(e)}", pos='midCenter', fade=True)
    
    def move_tool_to_group(self, tool, button, new_group_id):
        """将工具移动到新分组"""
        if new_group_id not in self.group_containers:
            return
            
        # 旧组ID
        old_group_id = tool.get("group", "default")
        
        # 如果组没变，不做任何操作
        if old_group_id == new_group_id:
            return
            
        # 查找新旧组的名称
        old_group_name = "常用工具"
        new_group_name = "常用工具"
        
        for group in self.config["groups"]:
            if group["id"] == old_group_id:
                old_group_name = group["name"]
            if group["id"] == new_group_id:
                new_group_name = group["name"]
        
        # 源文件和目标文件路径
        old_group_dir = os.path.join(self.tools_dir, old_group_name)
        new_group_dir = os.path.join(self.tools_dir, new_group_name)
        
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
        current_group_id = self.active_group_id
        
        # 重新加载UI
        self.refresh_tools()
        
        # 保持在当前选中的组，而不是跳转到目标组
        if current_group_id and current_group_id in self.group_containers:
            self.show_group(current_group_id)
        
        # 显示操作成功消息
        cmds.inViewMessage(message=f"已将工具移动到 '{new_group_name}' 组", pos='midCenter', fade=True)
    
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
                
            # 如果文件名发生变化，需要重命名文件
            if new_filename != filename:
                new_file_path = os.path.join(group_dir, new_filename)
                # 删除可能的同名文件(不太可能，因为我们已经避免了冲突)
                if os.path.exists(new_file_path):
                    os.remove(new_file_path)
                # 更新内容并保存到新文件
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                # 删除旧文件
                if os.path.exists(original_file_path) and original_file_path != new_file_path:
                    os.remove(original_file_path)
            else:
                # 文件名没变，只更新内容
                with open(original_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
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
            
            # 保存文件
            file_path = os.path.join(group_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
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
        
        # 重新扫描目录获取分组和工具
        self.config = self.scan_tools_directory()
        
        # 恢复回收站和布局设置
        self.config["recycle_bin"] = recycle_bin
        self.config["button_layout"] = button_layout
        self.config["button_colors"] = button_colors
        
        # 恢复工具的提示信息
        for tool in self.config.get("tools", []):
            if tool["filename"] in tools_tooltips:
                tool["tooltip"] = tools_tooltips[tool["filename"]]
        
        # 保存配置，包括分组顺序
        config_to_save = {
            "recycle_bin": self.config["recycle_bin"],
            "button_layout": self.config["button_layout"],
            "tools_tooltips": tools_tooltips,
            "groups_order": groups_order,
            "button_colors": button_colors
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
        """搜索文本改变时的处理"""
        if not text.strip():
            # 如果搜索框为空，清除搜索结果
            self.clear_search()
        else:
            # 实时搜索
            self.perform_search()
    
    def perform_search(self):
        """执行搜索"""
        search_text = self.search_input.text().strip().lower()
        if not search_text:
            self.clear_search()
            return
        
        # 清空之前的搜索结果
        self.clear_search_results()
        
        # 搜索匹配的工具
        self.search_results = []
        for tool in self.config.get("tools", []):
            tool_name = tool["name"].lower()
            if search_text in tool_name:
                self.search_results.append(tool)
        
        # 显示搜索结果
        self.show_search_results()
        
        # 切换到搜索结果视图
        self.switch_to_search_view()
    
    def clear_search(self):
        """清除搜索"""
        self.search_input.clear()
        self.clear_search_results()
        self.switch_to_normal_view()
    
    def clear_search_results(self):
        """清空搜索结果容器"""
        # 清空搜索结果布局
        while self.search_results_layout.count():
            child = self.search_results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.search_results = []
    
    def show_search_results(self):
        """显示搜索结果"""
        if not self.search_results:
            # 没有搜索结果
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
            self.search_results_layout.addWidget(no_result_label)
            return
        
        # 显示搜索结果
        for tool in self.search_results:
            # 创建搜索结果项
            result_widget = self.create_search_result_item(tool)
            self.search_results_layout.addWidget(result_widget)
    
    def create_search_result_item(self, tool):
        """创建搜索结果项"""
        # 创建主容器
        item_widget = QWidget()
        item_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: {s(5)}px;
                margin: {s(2)}px;
            }}
            QWidget:hover {{
                background-color: #454545;
                border-color: #666666;
            }}
        """)
        
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(s(10), s(8), s(10), s(8))
        layout.setSpacing(s(10))
        
        # 类型图标
        try:
            icons_dir = os.path.join(self.current_dir, "icons")
            icon_file = "mel.png" if tool["type"] == "mel" else "python.png"
            icon_path = os.path.join(icons_dir, icon_file)
            if os.path.exists(icon_path):
                icon_pix = QPixmap(icon_path).scaled(s(18), s(18), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label = QLabel()
                icon_label.setPixmap(icon_pix)
                icon_label.setFixedSize(s(20), s(20))
                layout.addWidget(icon_label)
        except Exception:
            pass
        
        # 脚本名称
        name_label = QLabel(tool["name"])
        name_label.setStyleSheet(f"""
            QLabel {{
                color: #EEEEEE;
                font-size: {s(14)}px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }}
        """)
        layout.addWidget(name_label)
        
        # 不再使用颜色标签区分脚本类型，已改为图标
        
        # 所属分组标签
        group_name = self.get_group_name_by_id(tool.get("group"))
        if group_name:
            group_label = QLabel(f"分组: {group_name}")
            group_label.setStyleSheet(f"""
                QLabel {{
                    color: #AAAAAA;
                    font-size: {s(12)}px;
                    background-color: transparent;
                    border: none;
                }}
            """)
            layout.addWidget(group_label)
        
        layout.addStretch()
        
        # 跳转按钮
        jump_btn = QPushButton("跳转")
        jump_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #6B4A7D;
                color: white;
                border: none;
                padding: {s(5)}px {s(15)}px;
                border-radius: {s(3)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #7B5A8D;
            }}
            QPushButton:pressed {{
                background-color: #5B3A6D;
            }}
        """)
        jump_btn.clicked.connect(partial(self.jump_to_tool, tool))
        layout.addWidget(jump_btn)
        
        # 运行按钮
        run_btn = QPushButton("运行")
        run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4A6D4A;
                color: white;
                border: none;
                padding: {s(5)}px {s(15)}px;
                border-radius: {s(3)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #5A7D5A;
            }}
            QPushButton:pressed {{
                background-color: #3A5D3A;
            }}
        """)
        run_btn.clicked.connect(partial(self.run_tool, tool))
        layout.addWidget(run_btn)
        
        # 设置工具提示
        tooltip_text = tool.get("tooltip", f"运行 {tool['name']}")
        item_widget.setToolTip(tooltip_text)
        
        # 添加右键菜单支持
        item_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        item_widget.customContextMenuRequested.connect(lambda pos, t=tool: self.show_search_context_menu(pos, item_widget, t))
        
        # 添加中键点击支持
        def handle_mouse_press(event):
            if event.button() == Qt.MiddleButton:
                # 中键点击，添加到工具架
                self.add_to_shelf(tool)
            else:
                # 其他按键，正常处理
                QWidget.mousePressEvent(item_widget, event)
        
        # 重写mousePressEvent
        item_widget.mousePressEvent = handle_mouse_press
        
        return item_widget
    
    def get_group_name_by_id(self, group_id):
        """根据组ID获取组名称"""
        if not group_id:
            return None
        
        for group in self.config.get("groups", []):
            if group["id"] == group_id:
                return group["name"]
        return None
    
    def switch_to_search_view(self):
        """切换到搜索结果视图"""
        self.is_searching = True
        
        # 隐藏正常视图
        self.tool_scroll.setVisible(False)
        self.recycle_bin_scroll.setVisible(False)
        
        # 显示搜索结果
        self.search_results_scroll.setVisible(True)
        
        # 更新标题
        search_text = self.search_input.text().strip()
        result_count = len(self.search_results)
        self.content_title.setText(f"搜索结果: \"{search_text}\" ({result_count}个结果)")
    
    def switch_to_normal_view(self):
        """切换到正常视图"""
        self.is_searching = False
        
        # 隐藏搜索结果
        self.search_results_scroll.setVisible(False)
        
        # 显示正常视图
        if self.recycle_bin_visible:
            self.recycle_bin_scroll.setVisible(True)
            self.content_title.setText("回收站")
        else:
            self.tool_scroll.setVisible(True)
            # 恢复原来的标题
            if self.active_group_id:
                group_name = self.get_group_name_by_id(self.active_group_id)
                if group_name:
                    self.content_title.setText(group_name)
                else:
                    self.content_title.setText("工具")
            else:
                self.content_title.setText("工具")
    
    def jump_to_group(self, group_id):
        """跳转到指定的脚本组"""
        if not group_id:
            return
        
        # 如果正在搜索，暂时切换到正常视图显示目标组，但保持搜索文本
        if hasattr(self, 'is_searching') and self.is_searching:
            # 保存当前搜索文本
            search_text = self.search_input.text()
            # 切换到正常视图
            self.switch_to_normal_view()
            # 恢复搜索文本但不执行搜索
            self.search_input.setText(search_text)
            # 标记为非搜索状态，这样用户可以看到目标组
            self.is_searching = False
        
        # 切换到指定的组
        self.show_group(group_id)
        
        # 如果组ID在导航按钮中，高亮显示
        if group_id in self.nav_buttons:
            # 先清除所有按钮的选中状态
            for btn_id, btn in self.nav_buttons.items():
                if btn_id != group_id:
                    btn.setStyleSheet(btn.styleSheet().replace("background-color: #666666;", "background-color: #444;"))
            
            # 高亮当前按钮
            current_btn = self.nav_buttons[group_id]
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
            # 查找对应按钮
            btn = self.find_button_for_tool(tool)
            if btn:
                # 确保按钮在可视区域
                try:
                    self.tool_scroll.ensureWidgetVisible(btn, 10, 10)
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
            for btn, info in list(self.tool_buttons.items()):
                t = info.get("tool", {})
                if t.get("filename") == target_fn and t.get("group") == target_gid:
                    return btn
        except Exception:
            pass
        return None
    
    def highlight_tool_button(self, button):
        """高亮指定按钮，直到用户点击或鼠标滑过或切换组"""
        try:
            # 清理旧的高亮
            self.clear_tool_highlight()
            # 记录旧样式
            self._highlight_prev_btn = button
            self._highlight_prev_style = button.styleSheet()
            # 应用高亮样式（在原样式后追加边框）
            highlight_append = """
            QPushButton {
                border: 2px solid #FFD54F;
            }
            """
            button.setStyleSheet(self._highlight_prev_style + "\n" + highlight_append)
            # 包装原事件以便清除高亮
            if not hasattr(button, "_orig_enterEvent"):
                button._orig_enterEvent = button.enterEvent if hasattr(button, "enterEvent") else None
            if not hasattr(button, "_orig_mousePressEvent"):
                button._orig_mousePressEvent = button.mousePressEvent if hasattr(button, "mousePressEvent") else None
            def _enter(ev):
                self.clear_tool_highlight()
                if callable(button._orig_enterEvent):
                    button._orig_enterEvent(ev)
            def _press(ev):
                self.clear_tool_highlight()
                if callable(button._orig_mousePressEvent):
                    button._orig_mousePressEvent(ev)
            # 绑定临时事件
            button.enterEvent = _enter
            button.mousePressEvent = _press
        except Exception as e:
            try:
                cmds.warning(f"应用按钮高亮失败: {str(e)}")
            except:
                pass
    
    def clear_tool_highlight(self):
        """恢复被高亮按钮的原样式与事件"""
        btn = getattr(self, "_highlight_prev_btn", None)
        if not btn:
            return
        try:
            prev = getattr(self, "_highlight_prev_style", "")
            btn.setStyleSheet(prev)
            # 恢复原事件
            if hasattr(btn, "_orig_enterEvent") and btn._orig_enterEvent is not None:
                btn.enterEvent = btn._orig_enterEvent
            if hasattr(btn, "_orig_mousePressEvent") and btn._orig_mousePressEvent is not None:
                btn.mousePressEvent = btn._orig_mousePressEvent
        except Exception:
            pass
        # 清理记录
        self._highlight_prev_btn = None
        self._highlight_prev_style = ""
    
    def show_search_context_menu(self, position, widget, tool):
        """显示搜索结果中脚本的右键菜单"""
        menu = QMenu(self)
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

        # 创建菜单项
        edit_action = QAction("编辑", self)
        edit_tooltip_action = QAction("编辑提示", self)
        color_action = QAction("自定义颜色", self)
        move_action = QAction("移动到组", self)
        open_folder_action = QAction("打开文件夹", self)
        delete_action = QAction("删除", self)
        settings_action = QAction("设置", self)

        # 添加分隔线和菜单项
        menu.addAction(edit_action)
        menu.addAction(edit_tooltip_action)
        menu.addAction(color_action)
        
        # 创建移动到组的子菜单
        move_menu = QMenu("移动到组", self)
        move_menu.setStyleSheet(menu.styleSheet())
        
        # 添加现有组到子菜单
        move_actions = {}
        current_group_id = tool.get("group", "default")
        
        if self.config and "groups" in self.config:
            for group in self.config["groups"]:
                if "id" in group and "name" in group:
                    group_id = group["id"]
                    group_name = group["name"]
                    
                    # 当前所在分组不显示
                    if group_id == current_group_id:
                        continue
                        
                    group_action = QAction(group_name, self)
                    move_menu.addAction(group_action)
                    move_actions[group_action] = group_id
        
        # 添加新建组选项
        move_menu.addSeparator()
        new_group_action = QAction("新建分组", self)
        move_menu.addAction(new_group_action)
        
        # 将移动到组子菜单添加到主菜单
        menu.addMenu(move_menu)
        
        menu.addSeparator()
        menu.addAction(open_folder_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(settings_action)

        # 显示菜单
        action = menu.exec_(widget.mapToGlobal(position))
        
        # 处理选择
        if action == delete_action:
            self.delete_tool(tool, None)  # 搜索结果中没有具体的按钮引用
            # 删除后重新执行搜索以更新结果
            self.perform_search()
        elif action and isinstance(action, QAction) and action.text() in ("置顶", "取消置顶"):
            self.toggle_pin(tool)
            self.perform_search()
        elif action == edit_action:
            self.edit_tool(tool)
        elif action == edit_tooltip_action:
            self.edit_tool_tooltip(tool, None)  # 搜索结果中没有具体的按钮引用
        elif action == color_action:
            self.show_color_picker(tool, None)  # 搜索结果中没有具体的按钮引用
        elif action == open_folder_action:
            self.open_tool_folder(tool)
        elif action == settings_action:
            self.show_settings_dialog()
        elif action == new_group_action:
            self.create_new_group(tool, None)  # 搜索结果中没有具体的按钮引用
        elif action in move_actions:
            # 移动工具到选定的分组
            new_group_id = move_actions[action]
            self.move_tool_to_group(tool, None, new_group_id)  # 搜索结果中没有具体的按钮引用
            # 移动后重新执行搜索以更新结果
            self.perform_search()
    
    def toggle_pin(self, tool):
        """切换置顶状态并刷新UI"""
        current = self.is_tool_pinned(tool)
        changed = self.set_tool_pinned(tool, not current)
        if changed:
            self.refresh_tools()
    
    def show_settings_dialog(self):
        """显示设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setFixedWidth(s(400))
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #333333;
                color: #E0E0E0;
                font-size: {s(15)}px;
            }}
            QLabel {{
                color: #E0E0E0;
                font-size: {s(15)}px;
            }}
            QPushButton {{
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: {s(8)}px {s(16)}px;
                border-radius: {s(4)}px;
                font-size: {s(15)}px;
            }}
            QPushButton:hover {{
                background-color: #666666;
            }}
            QGroupBox {{
                border: 1px solid #555555;
                border-radius: {s(5)}px;
                margin-top: {s(15)}px;
                padding-top: {s(10)}px;
                color: #E0E0E0;
                font-size: {s(15)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {s(10)}px;
                padding: 0 {s(5)}px;
            }}
            QRadioButton {{
                color: #E0E0E0;
                font-size: {s(15)}px;
            }}
            QRadioButton::indicator {{
                width: {s(18)}px;
                height: {s(18)}px;
            }}
        """)
        
        # 对话框布局
        layout = QVBoxLayout(dialog)
        layout.setSpacing(s(15))
        
        # 布局设置组
        layout_group = QGroupBox("按钮布局设置")
        layout_group_layout = QVBoxLayout(layout_group)
        layout_group_layout.setSpacing(s(8))
        
        # 布局选项
        current_layout = self.config.get("button_layout", "single")
        
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

        sidebar_group = QGroupBox("侧边栏布局")
        sidebar_group_layout = QVBoxLayout(sidebar_group)
        sidebar_group_layout.setSpacing(s(8))
        sidebar_toggle_btn = QPushButton("切换侧边栏布局")
        sidebar_state = {"value": self.config.get("sidebar_layout", False)}
        sidebar_state_label = QLabel("当前：开启" if sidebar_state["value"] else "当前：关闭")
        def _toggle_sidebar_state():
            sidebar_state["value"] = not sidebar_state["value"]
            sidebar_state_label.setText("当前：开启" if sidebar_state["value"] else "当前：关闭")
        sidebar_toggle_btn.clicked.connect(_toggle_sidebar_state)
        sidebar_group_layout.addWidget(sidebar_state_label)
        sidebar_group_layout.addWidget(sidebar_toggle_btn)
        layout.addWidget(sidebar_group)
        
        dock_group = QGroupBox("停靠到侧边栏")
        dock_group_layout = QVBoxLayout(dock_group)
        dock_group_layout.setSpacing(s(8))
        dock_state = {"value": self.config.get("dockable_mode", False)}
        dock_state_label = QLabel("当前：已启用" if dock_state["value"] else "当前：未启用")
        dock_toggle_btn = QPushButton("切换停靠模式")
        def _toggle_dock_state():
            dock_state["value"] = not dock_state["value"]
            dock_state_label.setText("当前：已启用" if dock_state["value"] else "当前：未启用")
        dock_toggle_btn.clicked.connect(_toggle_dock_state)
        dock_group_layout.addWidget(dock_state_label)
        dock_group_layout.addWidget(dock_toggle_btn)
        layout.addWidget(dock_group)
        
        # UI设置组
        ui_group = QGroupBox("UI设置")
        ui_group_layout = QVBoxLayout(ui_group)
        ui_group_layout.setSpacing(s(8))
        
        # 缩放比例滑块
        scale_layout = QHBoxLayout()
        scale_label = QLabel("界面缩放:")
        scale_value_label = QLabel(f"{UI_SCALE:.2f}")
        
        scale_slider = QSlider(Qt.Horizontal)
        scale_slider.setMinimum(50)  # 0.5
        scale_slider.setMaximum(120) # 1.2
        scale_slider.setValue(int(UI_SCALE * 100))
        
        def update_scale_label(value):
            scale = value / 100.0
            scale_value_label.setText(f"{scale:.2f}")
            
        scale_slider.valueChanged.connect(update_scale_label)
        
        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(scale_slider)
        scale_layout.addWidget(scale_value_label)
        ui_group_layout.addLayout(scale_layout)
        
        layout.addWidget(ui_group)
        
        # 配置导入/导出组
        config_group = QGroupBox("配置管理")
        config_group_layout = QVBoxLayout(config_group)
        config_group_layout.setSpacing(s(8))
        
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
        
        # 添加配置组到主布局
        layout.addWidget(config_group)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(s(10))
        
        # 应用按钮
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(lambda: self.apply_settings(
            single_layout_radio.isChecked(),
            sidebar_state["value"],
            dock_state["value"],
            scale_slider.value() / 100.0,
            dialog
        ))
        button_layout.addWidget(apply_btn)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        dialog.exec_()
    
    def apply_settings(self, single_layout_selected, sidebar_enabled, dock_enabled, new_ui_scale, dialog):
        """应用设置"""
        # 获取当前配置
        old_layout = self.config.get("button_layout", "single")
        old_sidebar = self.config.get("sidebar_layout", False)
        old_dock = self.config.get("dockable_mode", False)
        old_ui_scale = self.config.get("ui_scale", 0.65)
        
        # 新配置
        new_layout = "single" if single_layout_selected else "double"
        
        # 检查是否有变化
        layout_changed = old_layout != new_layout
        sidebar_changed = old_sidebar != sidebar_enabled
        dock_changed = old_dock != dock_enabled
        scale_changed = abs(old_ui_scale - new_ui_scale) > 0.001
        
        # 更新配置字典
        self.config["button_layout"] = new_layout
        self.config["sidebar_layout"] = sidebar_enabled
        self.config["dockable_mode"] = dock_enabled
        self.config["ui_scale"] = new_ui_scale
        
        # 如果缩放比例或停靠模式改变，需要重启
        if scale_changed or dock_changed:
            global UI_SCALE
            UI_SCALE = new_ui_scale
            self.save_config()
            
            dialog.accept()
            # 关闭并重启
            try:
                parent = self.parent()
                if parent is not None and hasattr(parent, "WINDOW_NAME"):
                    parent.close()
                else:
                    self.close()
            except:
                self.close()
            
            QTimer.singleShot(200, lambda: show_scripts_box())
            return
            
        # 如果只是布局或侧边栏改变，不需要重启
        if layout_changed or sidebar_changed:
            self.save_config()
            if layout_changed:
                self.refresh_tools()
                cmds.inViewMessage(message=f"已切换到{('单' if new_layout == 'single' else '双')}列按钮布局", pos='midCenter', fade=True)
            if sidebar_changed:
                self.apply_sidebar_layout_styles()
                cmds.inViewMessage(message=f"侧边栏布局已{'开启' if sidebar_enabled else '关闭'}", pos='midCenter', fade=True)
            dialog.accept()
        else:
            # 没有变化
            dialog.accept()
    
    def switch_dock_mode(self, enable):
        self.config["dockable_mode"] = enable
        self.save_config()
        try:
            parent = self.parent()
            if parent is not None and hasattr(parent, "WINDOW_NAME"):
                parent.close()
            else:
                self.close()
        except:
            try:
                self.close()
            except:
                pass
        QTimer.singleShot(200, lambda: show_scripts_box())

    def apply_sidebar_layout_styles(self):
        mode = self.config.get("sidebar_layout", False)
        if getattr(self, "nav_widget", None):
            if mode:
                self.nav_widget.setMinimumWidth(s(60))
                self.nav_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                self.nav_tree.setIndentation(s(14))
                self.nav_layout.setContentsMargins(s(4), s(6), s(4), s(6))
                self.nav_layout.setSpacing(s(4))
            else:
                self.nav_widget.setMinimumWidth(s(80))
                self.nav_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                self.nav_tree.setIndentation(s(18))
                self.nav_layout.setContentsMargins(s(5), s(10), s(5), s(10))
                self.nav_layout.setSpacing(s(5))
        if getattr(self, "content_layout", None):
            if mode:
                self.content_layout.setContentsMargins(s(8), s(8), s(8), s(8))
            else:
                self.content_layout.setContentsMargins(s(10), s(10), s(10), s(10))
        if getattr(self, "tools_layout", None):
            if mode:
                self.tools_layout.setContentsMargins(s(8), s(8), s(8), s(8))
                self.tools_layout.setSpacing(s(4))
            else:
                self.tools_layout.setContentsMargins(s(10), s(10), s(10), s(10))
                self.tools_layout.setSpacing(s(8))
        if getattr(self, "search_input", None):
            if mode:
                self.search_input.setMaximumWidth(s(120))
            else:
                self.search_input.setMaximumWidth(s(400))
        if getattr(self, "content_title", None):
            if mode:
                self.content_title.setVisible(False)
            else:
                self.content_title.setVisible(True)
    
    def open_scripts_directory(self):
        """打开脚本目录"""
        try:
            # 获取脚本目录路径
            scripts_dir = self.tools_dir
            
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
            self, "导出配置",
            default_path,
            "JSON文件 (*.json)"
        )
        
        if not file_path:
            return
        
        if not file_path.lower().endswith('.json'):
            file_path += '.json'
        
        try:
            msg_box = QMessageBox(self)
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
            
            # 分组顺序：优先从树形导航收集（名称列表，与 groups_order.json 一致）
            groups_order = []
            try:
                if getattr(self, 'nav_tree', None):
                    root = self.nav_tree.invisibleRootItem()
                    for i in range(root.childCount()):
                        item = root.child(i)
                        name = item.text(0).split(' (')[0].strip()
                        if name:
                            groups_order.append(name)
                if not groups_order and os.path.exists(self.groups_order_file):
                    with open(self.groups_order_file, 'r', encoding='utf-8') as gf:
                        data = json.load(gf)
                    groups_order = data if isinstance(data, list) else [n.get("name", "") for n in data if n.get("name")]
            except Exception as e:
                cmds.warning(f"读取分组顺序失败: {str(e)}")
            
            # 完整配置：回收站、布局、分组顺序、按钮颜色、分组颜色、置顶、提示信息、停靠与分隔比例
            export_config = {
                "recycle_bin": self.config.get("recycle_bin", []),
                "button_layout": self.config.get("button_layout", "single"),
                "groups_order": groups_order,
                "button_colors": self.config.get("button_colors", {}),
                "group_colors": self.config.get("group_colors", {}),
                "pinned": self.load_pinned(),
                "tools_tooltips": {},
                "sidebar_layout": self.config.get("sidebar_layout", False),
                "dockable_mode": self.config.get("dockable_mode", False),
                "splitter_ratio": self.config.get("splitter_ratio", 0.22),
            }
            for tool in self.config.get("tools", []):
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
                for group in self.config.get("groups", []):
                    group_name = group["name"]
                    group_dir = os.path.join(self.tools_dir, group_name)
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
            QMessageBox.critical(self, "导出失败", "导出配置失败: %s" % str(e))
    
    def import_config(self):
        """从JSON文件导入配置"""
        # 获取导入文件路径
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", 
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
            msg_box = QMessageBox(self)
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
            recycle_bin = self.config.get("recycle_bin", [])
            button_layout = self.config.get("button_layout", "single")
            
            imported_tooltips = imported_config.get("tools_tooltips", {})
            imported_groups_order = imported_config.get("groups_order", [])
            
            if "recycle_bin" in imported_config:
                recycle_bin = imported_config["recycle_bin"]
            if "button_layout" in imported_config:
                button_layout = imported_config["button_layout"]
            
            # 导入分组顺序到 groups_order.json（名称列表），以便刷新后树顺序正确
            if imported_groups_order:
                try:
                    first = imported_groups_order[0] if imported_groups_order else None
                    order_list = (imported_groups_order if isinstance(first, str) else
                                 [n.get("name", "") for n in imported_groups_order if n.get("name")])
                    with open(self.groups_order_file, 'w', encoding='utf-8') as gf:
                        json.dump(order_list, gf, indent=4, ensure_ascii=False)
                except Exception as e:
                    cmds.warning("写入分组顺序失败: %s" % str(e))
            
            # 如果要导入脚本文件
            if import_tools and has_tools_folder:
                # 创建备份文件夹
                backup_dir = os.path.join(self.current_dir, f"tools_backup_{int(time.time())}")
                if os.path.exists(self.tools_dir):
                    shutil.copytree(self.tools_dir, backup_dir)
                
                # 复制整个工具目录结构
                for item in os.listdir(tools_folder):
                    source_path = os.path.join(tools_folder, item)
                    
                    # 只处理目录，作为分组
                    if os.path.isdir(source_path):
                        group_name = item
                        dest_path = os.path.join(self.tools_dir, group_name)
                        
                        # 创建目标目录（如果不存在）
                        if not os.path.exists(dest_path):
                            os.makedirs(dest_path)
                        
                        # 复制该目录中的所有文件
                        for file_name in os.listdir(source_path):
                            source_file = os.path.join(source_path, file_name)
                            if os.path.isfile(source_file):
                                # 只复制.py和.mel文件
                                if file_name.lower().endswith(('.py', '.mel')):
                                    dest_file = os.path.join(dest_path, file_name)
                                    shutil.copy2(source_file, dest_file)
            
            self.config = self.scan_tools_directory()
            self.config["recycle_bin"] = recycle_bin
            self.config["button_layout"] = button_layout
            # 导入布局与停靠配置
            if "sidebar_layout" in imported_config:
                self.config["sidebar_layout"] = imported_config["sidebar_layout"]
            if "dockable_mode" in imported_config:
                self.config["dockable_mode"] = imported_config["dockable_mode"]
            if "splitter_ratio" in imported_config:
                self.config["splitter_ratio"] = imported_config["splitter_ratio"]
            
            # 导入按钮颜色、分组颜色
            if "button_colors" in imported_config and isinstance(imported_config["button_colors"], dict):
                self.config["button_colors"] = imported_config["button_colors"]
            if "group_colors" in imported_config and isinstance(imported_config["group_colors"], dict):
                self.config["group_colors"] = imported_config["group_colors"]
            
            # 导入置顶列表
            if "pinned" in imported_config and isinstance(imported_config["pinned"], list):
                self.save_pinned(imported_config["pinned"])
            
            for tool in self.config.get("tools", []):
                if tool["filename"] in imported_tooltips:
                    tool["tooltip"] = imported_tooltips[tool["filename"]]
            
            config_to_save = {
                "recycle_bin": self.config["recycle_bin"],
                "button_layout": self.config["button_layout"],
                "tools_tooltips": imported_tooltips,
                "groups_order": imported_groups_order,
                "button_colors": self.config.get("button_colors", {}),
                "group_colors": self.config.get("group_colors", {}),
                "sidebar_layout": self.config.get("sidebar_layout", False),
                "dockable_mode": self.config.get("dockable_mode", False),
                "splitter_ratio": self.config.get("splitter_ratio", 0.22),
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            
            # 立即刷新界面显示
            self.refresh_tools()
            
            message = "配置已导入，界面已更新"
            if import_tools and has_tools_folder:
                message += f"，脚本文件已导入。原工具目录已备份至 {backup_dir}"
            
            cmds.inViewMessage(message=message, pos='midCenter', fade=True)
            
        except Exception as e:
            cmds.warning(f"导入失败: {str(e)}")
            QMessageBox.critical(self, "导入失败", f"导入配置失败: {str(e)}")
            
            # 如果已经更改了配置，尝试恢复
            try:
                if 'backup_config' in locals():
                    self.config = backup_config
                    self.save_config()
                    self.load_tools()
            except:
                pass
    
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
        """滚动到指定组 - 在新布局中，这个方法会显示对应的组"""
        self.show_group(group_id)
    
    def add_group(self):
        """添加新组"""
        # 弹出输入对话框
        group_name, ok = QInputDialog.getText(
            self, "添加分组", "请输入分组名称:", 
            QLineEdit.Normal, ""
        )
        
        if ok and group_name:
            # 检查分组名称是否已存在
            for group in self.config["groups"]:
                if group["name"] == group_name:
                    cmds.warning(f"分组名称 '{group_name}' 已存在，请使用其他名称。")
                    return
            
            # 创建分组目录
            group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
            
            # 生成唯一ID
            group_id = f"group_{int(time.time())}"
            
            # 添加到配置
            new_group = {
                "name": group_name,
                "id": group_id
            }
            
            self.config["groups"].append(new_group)
            
            # 保存当前选中的组ID
            current_group_id = self.active_group_id
            
            # 创建组容器和导航按钮
            self.create_group_container(new_group)
            self.create_nav_button(new_group)
            
            # 保持在当前选中的组，而不是跳转到新组
            if current_group_id and current_group_id in self.group_containers:
                self.show_group(current_group_id)
            
            cmds.inViewMessage(message=f"已创建新分组 '{group_name}'", pos='midCenter', fade=True)

    # 添加显示帮助信息的方法
    def show_help(self):
        """显示帮助信息"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("脚本管理器 - 帮助信息")
        help_dialog.setMinimumWidth(s(700))
        help_dialog.setMinimumHeight(s(600))
        
        # 设置对话框样式
        help_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #333333;
                color: #E0E0E0;
            }}
            QLabel {{
                color: #E0E0E0;
            }}
            QTextBrowser {{
                background-color: #2A2A2A;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: {s(4)}px;
                padding: {s(8)}px;
            }}
            QPushButton {{
                background-color: #3a6ea5;
                color: white;
                border: none;
                padding: {s(8)}px {s(16)}px;
                border-radius: {s(4)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4a7eb5;
            }}
            QPushButton:pressed {{
                background-color: #2a5e95;
            }}
        """)
        
        # 创建布局
        layout = QVBoxLayout(help_dialog)
        layout.setContentsMargins(s(15), s(15), s(15), s(15))
        layout.setSpacing(s(10))
        
        # 创建标题
        title_label = QLabel("Maya脚本管理器使用指南")
        title_label.setStyleSheet(f"font-size: {s(18)}px; font-weight: bold; color: #E0E0E0; margin-bottom: {s(10)}px;")
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
        button_layout.setContentsMargins(0, s(10), 0, 0)
        button_layout.setSpacing(s(10))
        
        # 添加版本信息
        version_info = get_version_info()
        version_label = QLabel(f"Maya版本: {version_info['maya_version']}, Qt版本: {version_info['qt_version']}")
        version_label.setStyleSheet("color: #999999; font-style: italic;")
        button_layout.addWidget(version_label)
        
        button_layout.addStretch(1)
        
        # 创建按钮
        open_link_btn = QPushButton("访问B站主页")
        open_link_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon))
        close_btn = QPushButton("关闭")
        close_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        
        button_layout.addWidget(open_link_btn)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 连接按钮事件
        open_link_btn.clicked.connect(lambda: self.open_external_url("https://space.bilibili.com/431406403"))
        close_btn.clicked.connect(help_dialog.accept)
        
        # 显示对话框
        help_dialog.exec_()
    
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
            for group in self.config["groups"]:
                if group["id"] == group_id:
                    group_name = group["name"]
                    break
                    
            if not group_name:
                cmds.warning(f"找不到工具所属分组: {tool['name']}")
                return
            
            # 获取组目录和脚本路径
            group_dir = os.path.join(self.tools_dir, group_name)
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
            tooltip = tool.get("tooltip", "")
            if not tooltip:
                tooltip = f"运行 {tool['name']} ({tool['type'].upper()})"
            
            # 创建工具架按钮
            button_name = cmds.shelfButton(
                parent=current_shelf,
                label=tool["name"],
                annotation=tooltip,
                image="commandButton.png",  # 默认图标
                imageOverlayLabel=tool["name"],  # 在图标上显示文本标签
                command=shelf_command,
                sourceType=source_type,
                style="iconOnly"  # 使用图标样式，但通过imageOverlayLabel显示文本
            )
            
            # 显示成功消息
            cmds.inViewMessage(
                message=f"已将 '{tool['name']}' 添加到工具架", 
                pos='midCenter', 
                fade=True, 
                fadeStayTime=2000
            )
            
        except Exception as e:
            error_msg = traceback.format_exc()
            cmds.warning(f"添加到工具架失败: {str(e)}\n{error_msg}")

# 全局变量，存储当前活动的脚本管理器窗口
scripts_box_dialog = None

# Dockable 包装窗口（放在类定义之后，避免破坏 ScriptsBox 方法缩进）
class DockableScriptsBoxWindow(MayaQWidgetDockableMixin, QWidget):
    WINDOW_NAME = "ScriptsBoxDockWindow"
    CONTROL_NAME = WINDOW_NAME + "WorkspaceControl"
    def __init__(self, parent=None):
        super(DockableScriptsBoxWindow, self).__init__(parent=parent)
        self.setObjectName(self.WINDOW_NAME)
        self.setWindowTitle("脚本管理器")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.inner = ScriptsBox(parent=self)
        try:
            self.inner.setParent(self)
            self.inner.setWindowFlags(Qt.Widget)
        except:
            pass
        layout.addWidget(self.inner)
    
    def dockCloseEventTriggered(self):
        try:
            cn = DockableScriptsBoxWindow.CONTROL_NAME
            if cmds.workspaceControl(cn, exists=True):
                cmds.deleteUI(cn)
        except:
            pass

# 创建启动函数
def show_scripts_box():
    global scripts_box_dialog
    
    try:
        # 尝试安全关闭之前的实例
        if scripts_box_dialog is not None:
            try:
                if scripts_box_dialog.isVisible():
                    # 如果窗口仍然可见，则尝试正常关闭
                    scripts_box_dialog.close()
                    
                # 尝试删除旧窗口
                scripts_box_dialog.deleteLater()
            except:
                # 如果无法关闭，只需记录警告
                pass
    except:
        pass
    
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(current_dir, "config.json")
        dockable = False
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    dockable = bool(cfg.get("dockable_mode", False))
            except:
                dockable = False
        
        version_info = get_version_info()
        print("Maya脚本管理器启动中...")
        print(f"版本信息: {version_info}")
        
        if dockable:
            try:
                cn = DockableScriptsBoxWindow.CONTROL_NAME
                if cmds.workspaceControl(cn, exists=True):
                    cmds.deleteUI(cn)
                if cmds.window(DockableScriptsBoxWindow.WINDOW_NAME, exists=True):
                    cmds.deleteUI(DockableScriptsBoxWindow.WINDOW_NAME)
            except:
                pass
            scripts_box_dialog = DockableScriptsBoxWindow(parent=maya_main_window())
            scripts_box_dialog.show(dockable=True, area='right', floating=False, retain=False)
            try:
                cn = DockableScriptsBoxWindow.CONTROL_NAME
                if cmds.workspaceControl('AttributeEditor', exists=True) and cmds.workspaceControl(cn, exists=True):
                    mel.eval('workspaceControl -e -tabToControl "AttributeEditor" -1 "{}";'.format(cn))
            except:
                pass
        else:
            scripts_box_dialog = ScriptsBox()
            # 非侧边停靠模式下，启动时给更大的默认宽度（约为之前的两倍）
            try:
                scripts_box_dialog.resize(s(950), s(700))
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

# 安全关闭函数 - 可以从外部调用
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
    show_scripts_bo

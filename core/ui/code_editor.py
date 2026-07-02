# -*- coding: utf-8 -*-
"""
代码编辑器组件
包含行号显示、代码编辑器和脚本编辑器对话框
"""
import os
import sys
import time
import traceback
import tempfile

from core.utils.qt_compat import *


# 行号显示小部件
# Python 语法高亮器
class PythonHighlighter(QSyntaxHighlighter):
    """Python 语法高亮器"""
    def __init__(self, parent=None):
        QSyntaxHighlighter.__init__(self, parent)
        
        self.highlighting_rules = []
        
        # 关键字
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(0xC6, 0x78, 0xDD))
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
            'None', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'True', 'try', 'while', 'with', 'yield'
        ]
        for word in keywords:
            self.highlighting_rules.append((QRegExp(r'\b' + word + r'\b'), keyword_format))
        
        # Maya 相关关键字
        maya_keyword_format = QTextCharFormat()
        maya_keyword_format.setForeground(QColor(0x4E, 0xC9, 0xB0))
        maya_keywords = ['cmds', 'mel', 'maya', 'pm', 'pymel']
        for word in maya_keywords:
            self.highlighting_rules.append((QRegExp(r'\b' + word + r'\b'), maya_keyword_format))
        
        # 函数名
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(0x61, 0xAF, 0xEF))
        self.highlighting_rules.append((QRegExp(r'\b[A-Za-z0-9_]+(?=\()'), function_format))
        
        # 字符串
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0x98, 0xC3, 0x79))
        # 双引号字符串
        self.highlighting_rules.append((QRegExp(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        # 单引号字符串
        self.highlighting_rules.append((QRegExp(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
        
        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(0x5C, 0x63, 0x70))
        self.highlighting_rules.append((QRegExp(r'#.*'), comment_format))
        
        # 数字
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(0xF7, 0x8C, 0x6C))
        self.highlighting_rules.append((QRegExp(r'\b[0-9]+\.?[0-9]*\b'), number_format))
        
        # 装饰器
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor(0xD1, 0x9A, 0x66))
        self.highlighting_rules.append((QRegExp(r'@[A-Za-z0-9_]+'), decorator_format))
    
    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

# MEL 语法高亮器
class MELHighlighter(QSyntaxHighlighter):
    """MEL 语法高亮器"""
    def __init__(self, parent=None):
        QSyntaxHighlighter.__init__(self, parent)
        
        self.highlighting_rules = []
        
        # 关键字
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(0xC6, 0x78, 0xDD))
        keywords = [
            'proc', 'global', 'if', 'else', 'for', 'while', 'do', 'switch',
            'case', 'default', 'break', 'continue', 'return', 'int', 'float',
            'string', 'vector', 'matrix', 'true', 'false', 'null', 'source'
        ]
        for word in keywords:
            self.highlighting_rules.append((QRegExp(r'\b' + word + r'\b'), keyword_format))
        
        # Maya 命令（常见的）
        maya_cmd_format = QTextCharFormat()
        maya_cmd_format.setForeground(QColor(0x4E, 0xC9, 0xB0))
        maya_cmds = ['polySphere', 'polyCube', 'polyCone', 'polyCylinder', 'sphere', 'cube', 'cone', 'cylinder', 'circle', 'nurbsSphere', 'nurbsCube']
        for word in maya_cmds:
            self.highlighting_rules.append((QRegExp(r'\b' + word + r'\b'), maya_cmd_format))
        
        # 函数/过程调用
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(0x61, 0xAF, 0xEF))
        self.highlighting_rules.append((QRegExp(r'\b[A-Za-z0-9_]+(?=\()'), function_format))
        
        # 字符串
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0x98, 0xC3, 0x79))
        self.highlighting_rules.append((QRegExp(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        
        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(0x5C, 0x63, 0x70))
        # 单行注释 //
        self.highlighting_rules.append((QRegExp(r'//.*'), comment_format))
        # 多行注释 /* */
        self.comment_start_expr = QRegExp(r'/\*')
        self.comment_end_expr = QRegExp(r'\*/')
        self.comment_format = comment_format
        
        # 数字
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(0xF7, 0x8C, 0x6C))
        self.highlighting_rules.append((QRegExp(r'\b[0-9]+\.?[0-9]*\b'), number_format))
        
        # 变量（$ 开头）
        variable_format = QTextCharFormat()
        variable_format.setForeground(QColor(0xD1, 0x9A, 0x66))
        self.highlighting_rules.append((QRegExp(r'\$[A-Za-z0-9_]+'), variable_format))
    
    def highlightBlock(self, text):
        """高亮文本块"""
        # 常规高亮规则
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        
        # 多行注释处理
        self.setCurrentBlockState(0)
        
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = self.comment_start_expr.indexIn(text)
        
        while start_index >= 0:
            end_index = self.comment_end_expr.indexIn(text, start_index)
            
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + self.comment_end_expr.matchedLength()
            
            self.setFormat(start_index, comment_length, self.comment_format)
            start_index = self.comment_start_expr.indexIn(text, start_index + comment_length)

class LineNumberArea(QWidget):
    """行号显示区域"""
    def __init__(self, editor):
        QWidget.__init__(self, editor)
        self.code_editor = editor
        
    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)
        
    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

# 带行号的代码编辑器
class CodeEditor(QPlainTextEdit):
    """带行号的代码编辑器"""
    def __init__(self, parent=None):
        QPlainTextEdit.__init__(self, parent)
        
        self.line_number_area = LineNumberArea(self)
        self.highlighter = None
        
        # 连接信号
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        
        self.update_line_number_area_width(0)
    
    def set_highlighter(self, highlighter_type):
        """
        设置语法高亮器
        
        参数:
            highlighter_type: "python" 或 "mel"
        """
        if highlighter_type == "python":
            self.highlighter = PythonHighlighter(self.document())
        elif highlighter_type == "mel":
            self.highlighter = MELHighlighter(self.document())
        else:
            self.highlighter = None
        
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
        QPlainTextEdit.resizeEvent(self, event)
        
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
        QDialog.__init__(self, parent)
        
        # 设置窗口属性
        self.setWindowTitle("脚本编辑器")
        # 设置窗口大小（放大一倍）
        self.resize(1200, 800)
        
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
        
        # 更新编辑器样式（包括语法高亮）
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
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
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
        top_layout.addSpacing(20)
        top_layout.addWidget(type_label)
        top_layout.addWidget(self.python_radio)
        top_layout.addWidget(self.mel_radio)
        
        main_layout.addLayout(top_layout)
        
        # 提示信息编辑区
        tooltip_layout = QHBoxLayout()
        tooltip_label = QLabel("提示信息:")
        self.tooltip_edit = QPlainTextEdit()
        self.tooltip_edit.setMaximumHeight(60)
        self.tooltip_edit.setPlaceholderText("输入工具提示信息（可选）...")
        tooltip_layout.addWidget(tooltip_label)
        tooltip_layout.addWidget(self.tooltip_edit, 1)
        main_layout.addLayout(tooltip_layout)
        
        # 代码编辑器（带行号）
        self.editor = CodeEditor()
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        # 设置等宽字体
        font = QFont("Consolas, Courier New, monospace")
        font.setPointSize(10)
        self.editor.setFont(font)
        
        # 启用Tab键
        self.editor.setTabStopDistance(40)  # 相当于4个空格
        
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
        
        # 保存按钮
        save_text = "保存" if self.edit_mode else "保存并创建"
        self.save_button = QPushButton(save_text)
        self.save_button.clicked.connect(self.save_script)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.close)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
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
            # 设置 Python 语法高亮
            if hasattr(self.editor, 'set_highlighter'):
                self.editor.set_highlighter("python")
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
            # 设置 MEL 语法高亮
            if hasattr(self.editor, 'set_highlighter'):
                self.editor.set_highlighter("mel")
        
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

# -*- coding: utf-8 -*-
"""
自定义控件
"""

# 直接从 PySide 导入，确保类继承正确
try:
    from PySide2.QtWidgets import QPushButton, QApplication
    from PySide2.QtCore import Qt, QMimeData
    from PySide2.QtGui import QDrag, QPixmap
except ImportError:
    from PySide6.QtWidgets import QPushButton, QApplication
    from PySide6.QtCore import Qt, QMimeData
    from PySide6.QtGui import QDrag, QPixmap

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None


class DraggableGroupButton(QPushButton):
    """可拖拽的分组按钮类"""
    
    def __init__(self, text, group_id, parent=None):
        QPushButton.__init__(self, text, parent)
        self.group_id = group_id
        self.parent_widget = parent
        self.setAcceptDrops(True)
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        QPushButton.mousePressEvent(self, event)
        
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
        QPushButton.__init__(self, text, parent)
        self.tool_data = None
        self.scripts_box = None
        self._middle_button_pressed = False
    
    def set_tool_data(self, tool_data, scripts_box):
        """设置工具数据和脚本管理器引用"""
        self.tool_data = tool_data
        self.scripts_box = scripts_box
    
    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.MiddleButton:
            if self.tool_data and self.scripts_box:
                self._middle_button_pressed = True
            event.accept()
            return
        # 其他按键，调用父类处理
        QPushButton.mousePressEvent(self, event)
    
    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        if event.button() == Qt.MiddleButton:
            if self._middle_button_pressed and self.tool_data and self.scripts_box:
                # 检查鼠标是否仍在按钮范围内
                if self.rect().contains(event.pos()):
                    try:
                        self.scripts_box.add_to_shelf(self.tool_data)
                    except Exception as e:
                        if cmds:
                            cmds.warning(f"中键添加工具架失败: {str(e)}")
            self._middle_button_pressed = False
            event.accept()
            return
        # 其他按键，调用父类处理
        QPushButton.mouseReleaseEvent(self, event)
    
    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        if self._middle_button_pressed:
            # 中键拖动时不做特殊处理
            event.accept()
            return
        QPushButton.mouseMoveEvent(self, event)

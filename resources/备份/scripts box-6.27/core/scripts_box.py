# -*- coding: utf-8 -*-
"""
Maya脚本管理器 - 兼容Maya 2021-2026
支持PySide2和PySide6

模块入口，提供 show_scripts_box() 函数
"""
import sys
import os
from importlib import reload


def _reload_core_modules():
    """强制重新加载所有 core 子模块，避免 Maya 缓存旧代码"""
    modules_to_reload = [
        "core",  # 根模块
        "core.qt_compat",
        "core.utils",  # utils包
        "core.utils.color_utils",
        "core.ui",  # ui包
        "core.ui.widgets",
        "core.ui.code_editor",
        "core.ui.recycle_bin_ui",
        "core.ui.group_panel",
        "core.ui.tool_button_manager",
        "core.ui.settings_dialog",
        "core.ui.help_dialog",
        "core.ui.search_results_ui",
        "core.ui.main_window",
        "core.services",  # services包
        "core.services.tool_scanner",
        "core.services.config_service",
        "core.services.tool_runner",
        "core.services.search_service",
        "core.services.recycle_service",
        "core.scripts_box",  # 入口模块
    ]
    for mod_name in modules_to_reload:
        if mod_name in sys.modules:
            try:
                reload(sys.modules[mod_name])
            except Exception:
                pass


def show_scripts_box():
    """显示脚本工具箱主窗口"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # 强制刷新模块，避免 Maya 缓存
    _reload_core_modules()

    from core.qt_compat import cmds, QApplication, QDialog
    from core.ui.main_window import ScriptsBox

    try:
        # 方法1：通过 Qt 查找所有窗口并关闭符合条件的
        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                try:
                    # 检查是否是我们的窗口（通过类名或窗口标题）
                    if isinstance(widget, QDialog) and widget.windowTitle() == "Maya 脚本管理器":
                        widget.close()
                        widget.deleteLater()
                except Exception:
                    pass
        
        # 创建新窗口
        window = ScriptsBox()
        window.show()
        return window
    except Exception as e:
        import traceback
        traceback.print_exc()
        cmds.error(f"启动脚本工具箱失败: {e}")
        return None


if __name__ == "__main__":
    show_scripts_box()

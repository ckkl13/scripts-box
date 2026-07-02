# -*- coding: utf-8 -*-
"""
Qt 兼容层 - 兼容 Maya 2021-2026
支持 PySide2 和 PySide6
"""
import sys
import os


def setup_high_dpi_support():
    """设置高DPI支持，解决不同显示器上的显示比例问题"""
    if qt_version == "PySide6":
        # PySide6 的高DPI设置
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    else:
        # PySide2 的高DPI设置
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def get_scaled_font_size(base_size):
    """获取根据DPI缩放后的字体大小"""
    try:
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                logical_dpi = screen.logicalDotsPerInch()
                # 标准DPI是96
                scale_factor = logical_dpi / 96.0
                return max(8, int(base_size * scale_factor))
    except:
        pass
    return base_size


def get_scaled_size(base_size):
    """获取根据DPI缩放后的尺寸（用于图标、按钮大小等）"""
    try:
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                logical_dpi = screen.logicalDotsPerInch()
                scale_factor = logical_dpi / 96.0
                return max(4, int(base_size * scale_factor))
    except:
        pass
    return base_size


try:
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
        print("未能导入PySide，此脚本需要在Maya中运行")
        sys.exit()


def get_maya_version():
    maya_version = cmds.about(version=True)
    try:
        version_year = int(maya_version.split()[0])
        return version_year
    except:
        return 2023


MAYA_VERSION = get_maya_version()


def get_version_info():
    return {
        "maya_version": MAYA_VERSION,
        "qt_version": qt_version,
        "python_version": sys.version,
        "os_platform": sys.platform
    }


def maya_main_window():
    if qt_version == "PySide2":
        for obj in QApplication.topLevelWidgets():
            if obj.objectName() == 'MayaWindow':
                return obj
    else:
        for obj in QApplication.allWidgets():
            if obj.objectName() == 'MayaWindow':
                return obj
    for obj in QApplication.topLevelWidgets():
        if 'Maya' in obj.windowTitle():
            return obj
    return None

# -*- coding: utf-8 -*-
"""
Qt 兼容层 - 兼容 Maya 2021-2026
支持 PySide2 和 PySide6
"""
import sys

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

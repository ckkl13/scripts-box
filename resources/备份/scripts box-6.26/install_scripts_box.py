"""
拖放这个文件到Maya视口中以安装脚本工具箱
Drag and drop this file into the Maya viewport to install Scripts Box
"""

import maya.cmds as cmds
import sys
import os
from importlib import import_module, reload


def add_to_shelf(root_dir):
    """将工具按钮添加到Maya工具架"""
    try:
        current_shelf = cmds.tabLayout("ShelfLayout", query=True, selectTab=True)
        if not current_shelf:
            raise ValueError("未找到活动工具架")

        # 图标路径
        icon_path = os.path.join(root_dir, "resources", "icons", "scripts box.jpg")
        if not os.path.exists(icon_path):
            icon_path = "menuIconHelp.png"

        # 路径转义（用于嵌入 command 脚本）
        root_dir_escaped = root_dir.replace("\\", "\\\\")
        icons_dir = os.path.join(root_dir, "resources", "icons").replace("\\", "\\\\")
        core_dir = os.path.join(root_dir, "core").replace("\\", "\\\\")

        command_script = f'''import maya.cmds as cmds
import sys
import os
from importlib import import_module, reload

root_dir = r"{root_dir_escaped}"
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
core_dir = r"{core_dir}"
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

os.environ["SCRIPTS_BOX_ICONS_DIR"] = r"{icons_dir}"
os.environ["SCRIPTS_BOX_SHOWED_DISCLAIMER"] = "1"

try:
    from core import scripts_box
    reload(scripts_box)
    scripts_box.show_scripts_box()
except ImportError as e:
    cmds.error(f"导入模块失败: {{e}}")
except AttributeError as e:
    cmds.error(f"运行工具失败: {{e}}")
'''

        cmds.shelfButton(
            annotation="脚本工具箱",
            label="Scripts_Box",
            image1=icon_path,
            image=icon_path,
            command=command_script,
            sourceType="python",
            style="iconOnly",
            width=35,
            height=35,
            parent=current_shelf
        )
        return True
    except Exception as e:
        cmds.warning(f"添加到工具架失败: {e}")
        return False


def auto_install():
    """自动安装：从当前脚本所在目录自动检测并安装到工具架"""
    try:
        print("=" * 50)
        print("脚本工具箱 - 自动安装")
        print("=" * 50)

        root_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"根目录: {root_dir}")

        # 检查必要文件
        script_path = os.path.join(root_dir, "core", "scripts_box.py")
        if not os.path.exists(script_path):
            cmds.error("未找到 core/scripts_box.py，请确保 install_scripts_box.py 位于脚本工具箱根目录中")
            return False
        print(f"找到主程序: {script_path}")

        icon_path = os.path.join(root_dir, "resources", "icons", "scripts box.jpg")
        if os.path.exists(icon_path):
            print(f"找到图标: {icon_path}")
        else:
            print("未找到自定义图标，将使用Maya默认图标")

        # 确保必要目录存在
        tools_dir = os.path.join(root_dir, "tools")
        if not os.path.exists(tools_dir):
            os.makedirs(tools_dir)
            print(f"创建 tools 目录: {tools_dir}")

        config_path = os.path.join(root_dir, "core", "config.json")
        if not os.path.exists(config_path):
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write('{\n    "tools": []\n}')
            print(f"创建配置文件: {config_path}")

        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)

        if add_to_shelf(root_dir):
            cmds.inViewMessage(
                message="脚本工具箱安装成功！<br>请到工具架查看",
                pos='midCenter',
                fade=True,
                fadeStayTime=2000,
                backgroundColor=[0.2, 0.5, 0.2, 0.8]
            )
            print("安装成功！脚本工具箱已添加到当前工具架")
            return True
        else:
            return False

    except Exception as e:
        cmds.error(f"自动安装失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def onMayaDroppedPythonFile(*args):
    """拖入Maya视口时自动安装"""
    if sys.version_info.major < 3:
        raise ImportError(f"需要Python 3，当前版本: {sys.version_info.major}")
    auto_install()

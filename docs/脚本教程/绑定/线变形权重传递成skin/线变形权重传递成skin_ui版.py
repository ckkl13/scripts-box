#!/usr/bin/python
# -*- coding: utf-8 -*-
import pymel.core as pm
import traceback
from PySide2 import QtWidgets, QtCore, QtGui
import maya.OpenMayaUI as omui
from shiboken2 import wrapInstance


def maya_main_window():
    """获取Maya主窗口"""
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


def undo_fun(func):
    def wrapper(*args, **kwargs):
        pm.undoInfo(state=True, infinity=True)
        pm.undoInfo(ock=True)
        # do something before the function call

        try:
            r = func(*args, **kwargs)
        except:
            r = None
            traceback.print_exc()
        pm.undoInfo(cck=True)
        return r
    return wrapper


@undo_fun
def deformer_2_skincluster(skin_node='skinCluster1',
                           jnt_list=[],
                           model='nurbsToPoly1',
                           deformer_mesh='',
                           effect_jnt_list=[],
                           ):
    """权重传递主函数"""
    # 获取模型上的所有的点
    model_nt = pm.PyNode(model)

    count_vertex = pm.polyEvaluate(model_nt,  v=True)
    # 获取所有蒙皮骨骼
    skin_node_nt = pm.PyNode(skin_node)
    all_weight_joints = pm.skinCluster(skin_node_nt, q=True, wi=True)
    
    ## 获取 蒙皮数据
    value_dic = get_value(jnt_list=effect_jnt_list, model=deformer_mesh)
    data = get_value_weights(value_dic, axis=1)
    # 解锁骨骼权重
    for jnt in all_weight_joints:
        jnt.liw.set(1)

    for jnt in jnt_list:
        jnt_nt = pm.PyNode(jnt)
        jnt_nt.liw.set(0)
    # 将所有权重给到第一节骨骼

    for i in range(count_vertex):
        vetex = '{}.vtx[{}]'.format(model_nt.name(), i)
        pm.skinPercent(skin_node_nt, vetex, transformValue=[jnt_list[0], 1])

    # 设置模型权重
    for num in data.keys():
        vetex = '{}.vtx[{}]'.format(model_nt.name(), num)
        weight_list = []
        total = 0.0
        data_current = data[num]
        for i, dt in enumerate(data_current.keys()):
            if i == len(data_current.keys())-1:
                weight = round((1.0 - total), 5)
            else:
                weight_current = round(data_current[dt], 5)
                total += weight_current
                if total > 1.0:
                    weight = weight_current - (1.0 - total)
                    break
                else:
                    weight = weight_current

            weight_info = (jnt_list[dt], weight)
            weight_list.append(weight_info)

        pm.skinPercent(skin_node_nt, vetex, transformValue=weight_list)

    print(u'权重传递成功')
    return


def get_value(jnt_list=['joint1', 'joint2', 'joint3', 'joint4'], model='nurbsToPoly1'):
    """获取骨骼影响值"""
    default_pos = get_current_vertexpos(model=model)

    dif_value_dic = {}
    for i, jnt in enumerate(jnt_list):
        jnt_nt = pm.PyNode(jnt)
        pm.move(jnt_nt, (0, 1, 0), r=True, ws=True)
        current_pos = get_current_vertexpos(model=model)
        dif_value_dic[i] = get_difference(dic1=default_pos, dic2=current_pos)
        pm.move(jnt_nt, (0, -1, 0), r=True, ws=True)

    return dif_value_dic


def get_value_weights(dif_value_dic, axis=1):
    """计算权重值"""
    weights_dic = {}

    for i, jntNum in enumerate(dif_value_dic.keys()):
        data = dif_value_dic[jntNum]
        for k, dt in enumerate(data):
            if dt[axis] > 0:
                if k in weights_dic.keys():
                    weights_dic[k][jntNum] = dt[axis]
                else:
                    weights_dic[k] = {}
                    weights_dic[k][jntNum] = dt[axis]

    return weights_dic


def get_difference(dic1=[], dic2=[]):
    """计算位置差值"""
    dif_value_list = []
    for i in range(len(dic1)):
        dif_value = [dic2[i][0] - dic1[i][0], dic2[i][1] - dic1[i][1], dic2[i][2] - dic1[i][2]]
        dif_value_list.append(dif_value)

    return dif_value_list


def get_current_vertexpos(model=''):
    """获取当前顶点位置"""
    # 获取模型上的所有的点
    model_nt = pm.PyNode(model)
    count_vertex = pm.polyEvaluate(model_nt,  v=True)

    defualt_pos = []
    for i in range(count_vertex):
        vertex_name = '{}.vtx[{}]'.format(model_nt.name(), i)
        pos = pm.xform(vertex_name, q=True, t=True, ws=True)
        defualt_pos.append(pos)

    return defualt_pos


class LineRigUI(QtWidgets.QDialog):
    """线性绑定权重传递工具UI"""
    
    def __init__(self, parent=maya_main_window()):
        super(LineRigUI, self).__init__(parent)
        
        self.setWindowTitle("线性绑定权重传递工具 v0.2")
        self.setMinimumSize(400, 500)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        
        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        
    def create_widgets(self):
        """创建UI控件"""
        # 蒙皮集群节点
        self.skin_node_label = QtWidgets.QLabel("蒙皮集群节点:")
        self.skin_node_line = QtWidgets.QLineEdit("skinCluster1")
        self.skin_node_btn = QtWidgets.QPushButton("获取选中")
        
        # 目标蒙皮模型
        self.model_label = QtWidgets.QLabel("目标蒙皮模型:")
        self.model_line = QtWidgets.QLineEdit()
        self.model_btn = QtWidgets.QPushButton("获取选中")
        
        # 源变形网格
        self.deformer_mesh_label = QtWidgets.QLabel("源变形网格:")
        self.deformer_mesh_line = QtWidgets.QLineEdit()
        self.deformer_mesh_btn = QtWidgets.QPushButton("获取选中")
        
        # 参与权重计算的骨骼
        self.jnt_list_label = QtWidgets.QLabel("参与权重计算的骨骼:")
        self.jnt_list_text = QtWidgets.QTextEdit()
        self.jnt_list_text.setMaximumHeight(80)
        self.jnt_list_btn = QtWidgets.QPushButton("获取选中骨骼")
        
        # 影响骨骼列表
        self.effect_jnt_label = QtWidgets.QLabel("影响骨骼列表:")
        self.effect_jnt_text = QtWidgets.QTextEdit()
        self.effect_jnt_text.setMaximumHeight(80)
        self.effect_jnt_btn = QtWidgets.QPushButton("获取选中骨骼")
        
        # 执行按钮
        self.execute_btn = QtWidgets.QPushButton("执行权重传递")
        self.execute_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        
        # 帮助信息
        self.help_label = QtWidgets.QLabel(
            "使用说明:\n"
            "1. 设置蒙皮集群节点名称\n"
            "2. 选择目标蒙皮模型\n"
            "3. 选择源变形网格\n"
            "4. 设置参与权重计算的骨骼\n"
            "5. 设置影响骨骼列表\n"
            "6. 点击执行权重传递"
        )
        self.help_label.setStyleSheet("QLabel { background-color: black; color: white; padding: 10px; border-radius: 5px; }")
        
    def create_layouts(self):
        """创建布局"""
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 蒙皮集群节点布局
        skin_layout = QtWidgets.QHBoxLayout()
        skin_layout.addWidget(self.skin_node_line)
        skin_layout.addWidget(self.skin_node_btn)
        
        # 目标模型布局
        model_layout = QtWidgets.QHBoxLayout()
        model_layout.addWidget(self.model_line)
        model_layout.addWidget(self.model_btn)
        
        # 源变形网格布局
        deformer_layout = QtWidgets.QHBoxLayout()
        deformer_layout.addWidget(self.deformer_mesh_line)
        deformer_layout.addWidget(self.deformer_mesh_btn)
        
        # 添加到主布局
        main_layout.addWidget(self.skin_node_label)
        main_layout.addLayout(skin_layout)
        
        main_layout.addWidget(self.model_label)
        main_layout.addLayout(model_layout)
        
        main_layout.addWidget(self.deformer_mesh_label)
        main_layout.addLayout(deformer_layout)
        
        main_layout.addWidget(self.jnt_list_label)
        main_layout.addWidget(self.jnt_list_text)
        main_layout.addWidget(self.jnt_list_btn)
        
        main_layout.addWidget(self.effect_jnt_label)
        main_layout.addWidget(self.effect_jnt_text)
        main_layout.addWidget(self.effect_jnt_btn)
        
        main_layout.addWidget(self.execute_btn)
        main_layout.addWidget(self.help_label)
        
    def create_connections(self):
        """创建信号连接"""
        self.skin_node_btn.clicked.connect(self.get_skin_cluster)
        self.model_btn.clicked.connect(self.get_selected_model)
        self.deformer_mesh_btn.clicked.connect(self.get_selected_deformer)
        self.jnt_list_btn.clicked.connect(self.get_selected_joints_for_weight)
        self.effect_jnt_btn.clicked.connect(self.get_selected_joints_for_effect)
        self.execute_btn.clicked.connect(self.execute_weight_transfer)
        
    def get_skin_cluster(self):
        """获取选中对象的蒙皮集群"""
        selected = pm.selected()
        if selected:
            obj = selected[0]
            # 查找蒙皮集群
            skin_clusters = pm.listHistory(obj, type='skinCluster')
            if skin_clusters:
                self.skin_node_line.setText(str(skin_clusters[0]))
            else:
                pm.warning("选中对象没有蒙皮集群")
        else:
            pm.warning("请先选择一个对象")
            
    def get_selected_model(self):
        """获取选中的模型"""
        selected = pm.selected()
        if selected:
            self.model_line.setText(str(selected[0]))
        else:
            pm.warning("请先选择一个模型")
            
    def get_selected_deformer(self):
        """获取选中的变形网格"""
        selected = pm.selected()
        if selected:
            self.deformer_mesh_line.setText(str(selected[0]))
        else:
            pm.warning("请先选择一个变形网格")
            
    def get_selected_joints_for_weight(self):
        """获取选中的骨骼用于权重计算"""
        selected = pm.selected()
        if selected:
            joint_names = [str(obj) for obj in selected if pm.nodeType(obj) == 'joint']
            if joint_names:
                self.jnt_list_text.setText(', '.join(joint_names))
            else:
                pm.warning("请选择骨骼对象")
        else:
            pm.warning("请先选择骨骼")
            
    def get_selected_joints_for_effect(self):
        """获取选中的影响骨骼"""
        selected = pm.selected()
        if selected:
            joint_names = [str(obj) for obj in selected]
            if joint_names:
                self.effect_jnt_text.setText(', '.join(joint_names))
            else:
                pm.warning("请选择影响骨骼")
        else:
            pm.warning("请先选择影响骨骼")
            
    def execute_weight_transfer(self):
        """执行权重传递"""
        try:
            # 获取参数
            skin_node = self.skin_node_line.text().strip()
            model = self.model_line.text().strip()
            deformer_mesh = self.deformer_mesh_line.text().strip()
            
            jnt_list_text = self.jnt_list_text.toPlainText().strip()
            jnt_list = [name.strip() for name in jnt_list_text.split(',') if name.strip()]
            
            effect_jnt_text = self.effect_jnt_text.toPlainText().strip()
            effect_jnt_list = [name.strip() for name in effect_jnt_text.split(',') if name.strip()]
            
            # 验证参数
            if not all([skin_node, model, deformer_mesh, jnt_list, effect_jnt_list]):
                pm.warning("请填写所有必要参数")
                return
                
            # 验证对象是否存在
            if not pm.objExists(skin_node):
                pm.warning(f"蒙皮集群节点 '{skin_node}' 不存在")
                return
                
            if not pm.objExists(model):
                pm.warning(f"目标模型 '{model}' 不存在")
                return
                
            if not pm.objExists(deformer_mesh):
                pm.warning(f"源变形网格 '{deformer_mesh}' 不存在")
                return
                
            for jnt in jnt_list:
                if not pm.objExists(jnt):
                    pm.warning(f"骨骼 '{jnt}' 不存在")
                    return
                    
            for jnt in effect_jnt_list:
                if not pm.objExists(jnt):
                    pm.warning(f"影响骨骼 '{jnt}' 不存在")
                    return
            
            # 执行权重传递
            deformer_2_skincluster(
                skin_node=skin_node,
                jnt_list=jnt_list,
                model=model,
                deformer_mesh=deformer_mesh,
                effect_jnt_list=effect_jnt_list
            )
            
            pm.confirmDialog(
                title="成功",
                message="权重传递完成！",
                button=["确定"]
            )
            
        except Exception as e:
            pm.warning(f"执行失败: {str(e)}")
            traceback.print_exc()


def show_ui():
    """显示UI"""
    global line_rig_ui
    try:
        line_rig_ui.close()
        line_rig_ui.deleteLater()
    except:
        pass
    
    line_rig_ui = LineRigUI()
    line_rig_ui.show()


if __name__ == "__main__":
    show_ui()
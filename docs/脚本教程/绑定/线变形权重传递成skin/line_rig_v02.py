#!/usr/bin/python
# -*- coding: utf-8 -*-
import pymel.core as pm
import traceback


def undo_fun(func):
    def wrapper(*args, **kwargs):
        pm.undoInfo(state=True, infinity=True)
        pm.undoInfo(ock=True)
        # do
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

    print(u'成功')
    return


def get_value(jnt_list=['joint1', 'joint2', 'joint3', 'joint4'], model='nurbsToPoly1'):

    default_pos = get_current_vertexpos(model=model)

    dif_value_dic = {}
    for i, jnt in enumerate(jnt_list):

        jnt_nt = pm.PyNode(jnt)

        pm.move(jnt_nt, (0, 1, 0), r=True, ws=True)

        current_pos = get_current_vertexpos(model=model)

        dif_value_dic[i] = get_difference(
            dic1=default_pos, dic2=current_pos)

        pm.move(jnt_nt, (0, -1, 0), r=True, ws=True)

    return dif_value_dic


def get_value_weights(dif_value_dic, axis=1):

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

    dif_value_list = []
    for i in range(len(dic1)):

        dif_value = [dic2[i][0] - dic1[i][0], dic2[i]
                     [1] - dic1[i][1], dic2[i][2] - dic1[i][2]]

        dif_value_list.append(dif_value)

    return dif_value_list


def get_current_vertexpos(model=''):

    # 获取模型上的所有的点
    model_nt = pm.PyNode(model)

    count_vertex = pm.polyEvaluate(model_nt,  v=True)

    defualt_pos = []
    for i in range(count_vertex):

        vertex_name = '{}.vtx[{}]'.format(model_nt.name(), i)
        pos = pm.xform(vertex_name, q=True, t=True, ws=True)
        defualt_pos.append(pos)

    return defualt_pos

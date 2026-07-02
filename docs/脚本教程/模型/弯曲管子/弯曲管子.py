##--------------------------------------------------------------------------
## ScriptName : speedBend
## Author     : Joe Wu
## URL        : https://www.youtube.com/@Im3dJoe
## LastUpdate : 2024/06
##            : bend or extrude tube in one click
## Version    : 1.0  First version for public test
##              1.01 Fixing maya bug strange shape node not connect to transform node and can not be delete by history
##              1.02 continue fix same bug
##              1.03 improve offset slider control
##              1.04 scriptJob bug
##              1.05 scriptJob bug fix
##              1.06 fixing bug in Maya 2024.2
##              1.07 fixing bug 
## Install    : copy and paste script into a python tab in maya script editor
## note       : when checkbox ticked
##              Remember - this will apply the same value from previous setting
##              No Divisions - only setup bend deformer without adding additional edge rings
##              test in maya 2023
##--------------------------------------------------------------------------

import maya.cmds as mc
import math
import re
import maya.mel as mel
from collections import defaultdict

# 初始化全局变量
toBlendMesh = None
passSelection = []

def sBFillHole():
    checkHole = mc.filterExpand(ex=1, sm=(34))
    checkHoleEdge = mc.ls(mc.polyListComponentConversion(checkHole, te=1),fl=1)
    mc.polySelectConstraint(mode=3, type=0x8000, where=1)
    selected_edge = mc.ls(sl=1,fl=1)
    mc.polySelectConstraint(disable=True)
    foundHole = list(set(selected_edge)&set(checkHoleEdge))
    if foundHole:
        mc.select(foundHole)
        mc.FillHole()
        mc.ConvertSelectionToFaces()
        mc.select(checkHole,add=1)
    else:
        mc.select(checkHole)

def isFlat(sel):
    normals = defaultdict(list)
    for face in sel:
        normal = mc.polyInfo(face, faceNormals=True)[0].split()[2:]
        normal = [float(x) for x in normal]
        normals[tuple(normal)].append(face)
    most_common_normal = max(normals, key=lambda x: len(normals[x]))
    facesFlat = 1
    for normal, faces in normals.items():
        if normal == most_common_normal:
            continue
        dot = sum([a*b for a,b in zip(normal, most_common_normal)])
        mag1 = math.sqrt(sum([a*a for a in normal]))
        mag2 = math.sqrt(sum([a*a for a in most_common_normal]))
        cos_angle = dot / (mag1 * mag2)
        angle = math.acos(cos_angle)
        if math.degrees(angle) > 1:
            facesFlat = 0
    return facesFlat

def speedBendExtrudeGO():
    global passSelection
    passSelection = []
    toBlendFace = mc.filterExpand(ex=1, sm=(34))
    if toBlendFace:
        beforeBendClean()
        toBlendFace = mc.filterExpand(ex=1, sm=(34))
        checkFlat = isFlat(toBlendFace)
        if checkFlat == 1:
            singleFaceRecord = mc.filterExpand(ex=1, sm=(34))
            toBlendEdge = mc.ls(mc.polyListComponentConversion(singleFaceRecord, te=1),fl=1)
            totalDistance = 0
            for b in toBlendEdge:
                listVtx = mc.ls(mc.polyListComponentConversion(b, tv=1),fl=1)
                pA = mc.pointPosition(listVtx[0], w=1)
                pB = mc.pointPosition(listVtx[1], w=1)
                checkDistance = math.sqrt((pA[0] - pB[0]) ** 2 + (pA[1] - pB[1]) ** 2 + (pA[2] - pB[2]) ** 2)
                totalDistance = totalDistance + checkDistance
            diameterA = totalDistance / 3.14159
            bendLength = totalDistance / 2
            mc.polyExtrudeFacet(constructionHistory=0, keepFacesTogether=1, divisions=1, twist=0, taper=0, off=0 , thickness = bendLength , smoothingAngle=30)
        finishBendClean()

def speedBendLinkUI():
    checkSetting = mc.checkBox('speedBendSetting',q=1, v= 1)
    checkDivSetting = mc.checkBox('speedBendNoDiv',q=1, v= 1)
    bendV = mc.floatSliderGrp("speedBendBend",q=1,v=1)
    rollV = mc.floatSliderGrp("speedBendRoll",q=1,v=1)
    offsetV = mc.floatSliderGrp('speedBendOffset',q=1,v=1)
    mc.iconTextButton("speedBendGOGO", e=1, en=0 ,bgc=[0.28,0.28,0.28],l='')
    mc.iconTextButton("speedBendExtrude", e=1, en=0 ,bgc=[0.28,0.28,0.28],l='')
    if checkDivSetting == 0:
        divV = mc.intSliderGrp("speedBendDiv",q=1,v=1)
    mc.connectControl( 'speedBendBend', 'speedBend.curvature' )
    mc.connectControl( 'speedBendRoll', 'bendOffsetRot.rotateY' )
    mc.connectControl( 'speedBendOffset', 'speedBendHandle.translateX' )
    if checkDivSetting == 0:
        mc.connectControl( 'speedBendDiv', 'speedBendBridge.divisions' )
    if checkSetting == 1:
        mc.setAttr('speedBend.curvature',bendV)
        mc.setAttr('bendOffsetRot.rotateY',rollV)
        mc.setAttr('speedBendHandle.translateX',offsetV)
        if checkDivSetting == 1:
            mc.setAttr('speedBendBridge.divisions',divV)
            mc.iconTextButton("speedBendExtrude", e=1, en=0 ,bgc=[0.28,0.28,0.28],l='')
    mc.scriptJob (ro=1, event = ["SelectionChanged", finishBendClean])
    mc.scriptJob(uiDeleted=["speedBendUI", finishBendClean])

def speedBendOffsetReset():
    currentV = mc.floatSliderGrp("speedBendOffset",e=1,v=0)
    if mc.objExists('speedBendHandle'):
        mc.setAttr('speedBendHandle.translateX' ,0)

def speedBendOffsetMore(more):
    currentV = mc.floatSliderGrp("speedBendOffset",q=1,max=1)
    if currentV ==  100:
        if (more == -1):
            mc.floatSliderGrp('speedBendOffset',e=1, pre = 0, min = -1, max = 10, v=0)
            mc.button("speedBendOffsetV", e=1 , bgc=[0.34, 0.34, 0.34])
            mc.button('sBOffsetPlus',e=1,en=1,l='+')
    if currentV ==  10:
        if (more == 1):
            mc.floatSliderGrp('speedBendOffset',e=1, pre = 0, min = -10, max = 100, v=0)
            mc.button("speedBendOffsetV", e=1 , bgc=[0.44, 0.44, 0.44])
            mc.button('sBOffsetPlus',e=1,en=0,l='')
        else:
            mc.floatSliderGrp('speedBendOffset',e=1, pre = 1, min = -1.0, max = 1, v=0)
            mc.button("speedBendOffsetV", e=1 , bgc=[0.24, 0.24, 0.24])
    elif currentV ==  1:
        if (more == 1):
            mc.floatSliderGrp('speedBendOffset',e=1, pre = 0, min = -1, max = 10, v=0)
            mc.button("speedBendOffsetV", e=1 , bgc=[0.34, 0.34, 0.34])
        else:
            mc.floatSliderGrp('speedBendOffset',e=1, pre = 3, min = -1.0, max = 0.1, v=0)
            mc.button("speedBendOffsetV", e=1 , bgc=[0.14, 0.14, 0.14])
    elif currentV ==  0.1:
        if (more == 1):
            mc.floatSliderGrp('speedBendOffset',e=1, pre = 2, min = -1.0, max = 1, v=0)
            mc.button("speedBendOffsetV", e=1 , bgc=[0.24, 0.24, 0.24])
        else:
            mc.floatSliderGrp('speedBendOffset',e=1, pre = 4, min = -1.0, max = 0.01, v=0)
            mc.button("speedBendOffsetV", e=1 , bgc=[0.04, 0.04, 0.04])
            mc.button('sBOffsetMinus',e=1,en=0,l='')
    elif currentV ==  0.01:
        if (more == 1):
            mc.floatSliderGrp('speedBendOffset',e=1, pre = 2, min = -1.0, max = 1, v=0)
            mc.button("speedBendOffsetV", e=1 , bgc=[0.24, 0.24, 0.24])
            mc.button('sBOffsetMinus',e=1,en=1,l='-')

def speedBendDivReset():
    currentV = mc.intSliderGrp("speedBendDiv",e=1,v=8)
    if mc.objExists('speedBendBridge'):
        mc.setAttr('speedBendBridge.divisions',8)

def speedBendBendMore(more):
    currentV = mc.floatSliderGrp("speedBendBend", q=1 , v=1)
    currentGap = mc.intField('speedBendBendV', q=1,v =1)
    maxV = mc.floatSliderGrp("speedBendBend", q=1, max=1)
    minV = mc.floatSliderGrp("speedBendBend", q=1, min=1)
    nextCloseV = (int(currentV / currentGap) + int(more)) * currentGap
    if nextCloseV > maxV:
        nextCloseV = maxV
    elif nextCloseV < minV:
        nextCloseV = minV
    mc.floatSliderGrp("speedBendBend", e=1 , v=nextCloseV)
    if mc.objExists('speedBend'):
        mc.setAttr('speedBend.curvature',nextCloseV)

def speedBendBendReset():
    mc.floatSliderGrp("speedBendBend", e=1 , v=90)
    if mc.objExists('speedBend'):
        mc.setAttr('speedBend.curvature',90)

def speedBendBendUpdate():
    currentV = mc.floatSliderGrp("speedBendBend", q=1 , v=1)
    if mc.objExists('speedBendBend'):
        mc.setAttr('speedBend.curvature',currentV)


def speedBendRollMore(more):
    currentV = mc.floatSliderGrp("speedBendRoll", q=1 , v=1)
    currentGap = mc.intField('speedBendRollV', q=1,v =1)
    maxV = mc.floatSliderGrp("speedBendRoll", q=1, max=1)
    minV = mc.floatSliderGrp("speedBendRoll", q=1, min=1)
    nextCloseV = (int(currentV / currentGap) + int(more)) * currentGap
    if nextCloseV > maxV:
        nextCloseV = maxV
    elif nextCloseV < minV:
        nextCloseV = minV
    mc.floatSliderGrp("speedBendRoll", e=1 , v=nextCloseV)
    if mc.objExists('bendOffsetRot'):
        mc.setAttr('bendOffsetRot.rotateY',nextCloseV)

def speedBendRollUpdate():
    currentV = mc.floatSliderGrp("speedBendRoll", q=1 , v=1)
    if mc.objExists('bendOffsetRot'):
        mc.setAttr('bendOffsetRot.rotateY',currentV)

def speedBendRollReset():
    mc.floatSliderGrp("speedBendRoll", e=1 , v=0)
    if mc.objExists('bendOffsetRot'):
        mc.setAttr('bendOffsetRot.rotateY',0)

def speedBendGo():
    global passSelection
    passSelection = []
    checkButton = mc.iconTextButton("speedBendGOGO", q=1, en=1)
    checkDivSetting = mc.checkBox('speedBendNoDiv',q=1, v= 1)
    if checkButton == 1:
        sBFillHole()
        global toBlendMesh
        lockFaceList = []
        beforeBendClean()
        toBlendFace = mc.filterExpand(ex=1, sm=(34))
        if toBlendFace:
            toBlendMesh = toBlendFace[0].split('.')[0]
            toBlendShape = mc.listRelatives(toBlendMesh,f=1, s=1)
            singleFace = 0
            mc.sets(name="toBlendCut", text="toBlendCut")
            if len(toBlendFace) > 0:
                checkFlat = isFlat(toBlendFace)
                if checkFlat == 1:
                    singleFaceRecord = mc.filterExpand(ex=1, sm=(34))
                    toBlendEdgeAll = mc.ls(mc.polyListComponentConversion(singleFaceRecord, te=1),fl=1)
                    toBlendEdgeInside = mc.ls(mc.polyListComponentConversion(singleFaceRecord, te=1,internal=1),fl=1)
                    toBlendEdge = list(set(toBlendEdgeAll)-set(toBlendEdgeInside))
                    totalDistance = 0
                    for b in toBlendEdge:
                        listVtx = mc.ls(mc.polyListComponentConversion(b, tv=1),fl=1)
                        pA = mc.pointPosition(listVtx[0], w=1)
                        pB = mc.pointPosition(listVtx[1], w=1)
                        checkDistance = math.sqrt((pA[0] - pB[0]) ** 2 + (pA[1] - pB[1]) ** 2 + (pA[2] - pB[2]) ** 2)
                        totalDistance = totalDistance + checkDistance
                    diameterA = totalDistance / 3.14159
                    bendLength = totalDistance / 2
                    mc.polyExtrudeFacet(constructionHistory=0, keepFacesTogether=1, divisions=1, twist=0, taper=0, off=0 , thickness = bendLength , smoothingAngle=30)
                    addCapFace = mc.ls(sl=1,fl=1)
                    addCapEdge = mc.ls(mc.polyListComponentConversion(addCapFace, te=1),fl=1)
                    mc.sets(toBlendEdge,name="toBlendCut", text="toBlendCut")
                    mc.sets(addCapEdge, add= 'toBlendCut')
                    toBlendFace = mc.ls(mc.polyListComponentConversion(addCapEdge, tf=1),fl=1)
                    singleFace = 1
            if len(toBlendFace) > 1 :
                convert2EdgeInternal = mc.ls(mc.polyListComponentConversion(toBlendFace, te=1, internal=1),fl=1)
                convert2Edge = mc.ls(mc.polyListComponentConversion(toBlendFace, te=1),fl=1)
                toBlendEdge = list(set(convert2Edge)-set(convert2EdgeInternal))
                mc.sets(toBlendEdge, add= 'toBlendCut')
                fullFace =  mc.ls( (toBlendMesh+'.f[*]'),fl=1)
                lockFaceList = list(set(fullFace)-set(toBlendFace))
                mc.sets(lockFaceList,name="lockFaces", text="lockFaces")
                ringVtx = mc.polyListComponentConversion(toBlendEdge, tv=1)
                ringVtx = mc.ls(ringVtx,fl=1)
                cv_positions = [mc.pointPosition(x,w=1) for x in ringVtx]
                center_position = [sum(axis) / len(ringVtx) for axis in zip(*cv_positions)]
                grp = mc.group(empty=True, name='bendPointA')
                mc.move(center_position[0], center_position[1], center_position[2], grp, absolute=True)
                findFace = mc.polyListComponentConversion(toBlendEdge, tf=1)
                findFace = mc.ls(findFace,fl=1)
                getFaceList = list(set(findFace) & set(toBlendFace))
                ringEdgeList = mc.ls(mc.polyListComponentConversion(getFaceList,te=1,internal=1),fl=1)
                capEdgeLoop = mc.ls(mc.polyListComponentConversion(getFaceList,te=1),fl=1)
                ringB = list(set(capEdgeLoop) - set(ringEdgeList) - set(toBlendEdge))
                ringVtxB = mc.ls(mc.polyListComponentConversion(ringB, tv=1),fl=1)
                cv_positionsB = [mc.pointPosition(x,w=1) for x in ringVtxB]
                center_positionB = [sum(axis) / len(ringVtxB) for axis in zip(*cv_positionsB)]
                grpB = mc.group(empty=True, name='bendPointB')
                mc.move(center_positionB[0], center_positionB[1], center_positionB[2], grpB, absolute=True)
                consNodeA = mc.aimConstraint('bendPointB','bendPointA',offset=[0,0,0], weight=1, aimVector=[0,1,0], upVector=[1,0,0], worldUpType='vector')
                rotationRecord = mc.getAttr('bendPointA.rotate')
                if singleFace == 0:
                    totalDistance = 0
                    for b in toBlendEdge:
                        listVtx = mc.ls(mc.polyListComponentConversion(b, tv=1),fl=1)
                        pA = mc.pointPosition(listVtx[0], w=1)
                        pB = mc.pointPosition(listVtx[1], w=1)
                        checkDistance = math.sqrt((pA[0] - pB[0]) ** 2 + (pA[1] - pB[1]) ** 2 + (pA[2] - pB[2]) ** 2)
                        totalDistance = totalDistance + checkDistance
                    diameterA = totalDistance / 3.14159
                    bendLength = totalDistance / 2
                    mc.polySplitRing(ringEdgeList)
                    newSplitRing = mc.ls(sl=1,fl=1)
                    findNewVerticleFaceA = mc.ls(mc.polyListComponentConversion(newSplitRing , tf=1),fl=1)
                    findNewVerticleFaceB = mc.ls(mc.polyListComponentConversion(toBlendEdge , tf=1),fl=1)
                    findNewVerticleFace = list(set(findNewVerticleFaceA) & set(findNewVerticleFaceB))
                    findNewVerticleVerticleEdge = mc.ls(mc.polyListComponentConversion(findNewVerticleFace,te=1,internal=1),fl=1)
                    mc.sets(newSplitRing, add = 'toBlendCut' )
                    if checkDivSetting == 0:
                        listVtx = mc.ls(mc.polyListComponentConversion(findNewVerticleVerticleEdge[0], tv=1),fl=1)
                        pA = mc.pointPosition(listVtx[0], w=1)
                        pB = mc.pointPosition(listVtx[1], w=1)
                        oldEdgeDistance = math.sqrt((pA[0] - pB[0]) ** 2 + (pA[1] - pB[1]) ** 2 + (pA[2] - pB[2]) ** 2)
                        distanceScaleV = bendLength /oldEdgeDistance
                        for v in findNewVerticleVerticleEdge:
                            listVtx = mc.ls(mc.polyListComponentConversion(v, tv=1),fl=1)
                            getBaseCV = list(set(listVtx) & set(ringVtx))
                            pA = mc.pointPosition(getBaseCV, w=1)
                            mc.scale(distanceScaleV,distanceScaleV,distanceScaleV, v, cs=1, r=1, p= (pA[0],pA[1],pA[2]))
                        mc.delete(findNewVerticleFace)
                        mc.delete(toBlendMesh,ch=1)
                        mc.select('toBlendCut',add=1)
                else:
                    if checkDivSetting == 0:
                        toDeleteFace = list(set(toBlendFace)-set(singleFaceRecord))
                        mc.delete(toDeleteFace)
                        mc.delete(toBlendMesh,ch=1)
                if checkDivSetting == 0:
                    membersLockFaces = mc.ls(mc.sets('lockFaces', query=True),fl=1)
                    mc.polyBridgeEdge('toBlendCut',ch=1, divisions=20, twist=0, taper=1, curveType=0, smoothingAngle=30, direction=0, sourceDirection=0, targetDirection=0)
                    history_nodes = mc.listHistory(toBlendMesh)
                    polyBridgeNode= mc.ls(history_nodes,type='polyBridgeEdge')
                    mc.rename(polyBridgeNode[0],'speedBendBridge')
                    mc.createNode('mesh')
                    mc.rename('toBlendOutShape')
                    unWantTransNode = mc.listRelatives('toBlendOutShape', parent=True)[0]
                    mc.connectAttr((toBlendShape[0] + '.outMesh'), ('toBlendOutShape.inMesh'),f=1)
                    mc.parent('toBlendOutShape',toBlendMesh, relative=True, shape=True)
                    mc.delete(unWantTransNode)
                    shading_group = mc.listConnections(toBlendShape[0], type='shadingEngine')[0]
                    mc.sets('toBlendOutShape', e=1, forceElement=shading_group)
                    mc.HideSelectedObjects(toBlendShape[0])
                    mc.polySoftEdge(toBlendMesh, a=30, ch=1)
                mc.select(toBlendMesh)
                mc.Bend()
                bendHandleNode = mc.ls(sl=1,fl=1,transforms=1)
                mc.rename(bendHandleNode[0],'speedBendHandle')
                history_nodes = mc.listHistory(toBlendMesh)
                bendNode = mc.ls(history_nodes,type='nonLinear')
                mc.rename(bendNode[0],'speedBend')
                mc.setAttr(('speedBendHandle.rotate'),rotationRecord[0][0],rotationRecord[0][1],rotationRecord[0][2])
                mc.setAttr(('speedBendHandle.translate'),center_position[0],center_position[1],center_position[2])
                mc.setAttr(('speedBendHandle.scale'),bendLength,bendLength,bendLength)
                mc.setAttr('speedBend.lowBound',0)
                mc.setAttr('speedBend.curvature',90)
                mc.parent('speedBendHandle',toBlendMesh)
                offSetGrp = mc.group(empty=True, name="bendOffset")
                offSetRotGrp = mc.group(empty=True, name="bendOffsetRot")
                mc.parent(offSetRotGrp,offSetGrp)
                mc.parent(offSetGrp,'speedBendHandle')
                mc.setAttr('bendOffset.translate',0,0,0)
                mc.setAttr('bendOffset.rotate',0,0,0)
                mc.setAttr('bendOffset.scale',1,1,1)
                mc.parent('bendOffset',toBlendMesh)
                mc.parent('speedBendHandle','bendOffsetRot')
                weightZeroList = mc.ls(mc.polyListComponentConversion(membersLockFaces, tv=1),fl=1)
                for f in weightZeroList:
                    mc.percent('speedBend',f , v=0)
                if checkDivSetting == 0:
                    toBlendFaceList  = mc.ls(mc.polyListComponentConversion('toBlendOutShape',tf=1),fl=1)
                    convertList = []
                    for e in lockFaceList:
                        newN =  'toBlendOutShape.' + e.split('.')[-1]
                        convertList.append(newN)
                    selBendArea = list(set(toBlendFaceList) - set(convertList))
                    if singleFace == 1:
                        passSelection = addCapFace
                    else:
                        passSelection = selBendArea
                    mc.hide(toBlendShape)
                    mc.select(cl=1)
                    mc.showHidden('toBlendOutShape')
                mc.select(toBlendMesh)
                cleanList = ('bendPoint*','lockFaces','toBlendCut')
                for c in cleanList:
                    if mc.objExists(c):
                        mc.delete(c)
                mc.setAttr(('speedBendHandle.hiddenInOutliner'),0)
                mc.setAttr(('speedBendHandle.visibility'),0)
                if checkDivSetting == 0:
                    mc.setAttr("speedBendBridge.divisions",8)
                speedBendLinkUI()


def beforeBendClean():
    speedBendScriptJobClean()
    selection  = mc.ls(sl=1,fl=1)
    if selection:
        top_node = selection[0]
        while mc.listRelatives(top_node, parent=True):
            top_node = mc.listRelatives(top_node, parent=True)[0]
        mc.delete(top_node ,ch=1)
        toBlendShape = mc.listRelatives(top_node, s=1)
        if toBlendShape:
            if len(toBlendShape)>1:
                if 'toBlendOutShape' in toBlendShape:
                   for s in toBlendShape:
                       if s != 'toBlendOutShape':
                           mc.delete(s)
                else:
                    faceCount = mc.polyEvaluate(top_node, f=True )
                    for t in toBlendShape:
                        checkFaceCount = mc.polyEvaluate(t, f=True )
                        if checkFaceCount != faceCount:
                            mc.delete(t)
            toBlendShape = mc.listRelatives(top_node,f=1,s=1)[0]
            parentNode = mc.listRelatives(toBlendShape,f=1, p=1)[0]
            mc.rename(toBlendShape,(parentNode[1:]+'Shape'))
        cleanList = ('speedBendBridg*','bendPoint*','lockFace*','toBlendCu*','toBlendOutShap*','speedBen*','bendOffse*')
        for c in cleanList:
            if mc.objExists(c):
                mc.delete(c)
        mc.showHidden(top_node)

def finishBendClean():
    storeSel = mc.ls(sl=1)
    speedBendScriptJobClean()
    global toBlendMesh
    global passSelection
    # 初始化全局变量（如果未定义）
    try:
        toBlendMesh
    except NameError:
        toBlendMesh = None
    try:
        passSelection
    except NameError:
        passSelection = []
    
    if toBlendMesh and mc.objExists(toBlendMesh):
        mc.delete(toBlendMesh ,ch=1)
        toBlendShape = mc.listRelatives(toBlendMesh,s=1)
        if toBlendShape:
            if len(toBlendShape)>1:
                if 'toBlendOutShape' in toBlendShape:
                   for s in toBlendShape:
                       if s != 'toBlendOutShape':
                           mc.delete(s)
                else:
                    faceCount = mc.polyEvaluate(toBlendMesh, f=True )
                    for t in toBlendShape:
                        checkFaceCount = mc.polyEvaluate(t, f=True )
                        if checkFaceCount != faceCount:
                            mc.delete(t)
            toBlendShape = mc.listRelatives(toBlendMesh,f=1,s=1)[0]
            parentNode = mc.listRelatives(toBlendShape,f=1, p=1)[0]
            mc.rename(toBlendShape,(parentNode[1:]+'Shape'))
            mc.showHidden(toBlendMesh)
            if passSelection:
                convertList = []
                for p in passSelection:
                    newN =  toBlendMesh +'.' + p.split('.')[-1]
                    convertList.append(newN)
                mc.select(convertList)
    checkState = mc.iconTextButton("speedBendGOGO", q=1, ex=1 )
    if checkState == 1:
        mc.iconTextButton("speedBendGOGO", e=1, en=1, l ="Bend", bgc=[0.2, 0.2, 0.2] )
    mc.iconTextButton("speedBendExtrude", e=1, en=1 ,bgc=[0.2,0.2,0.2],l='Extrude')

def speedBendScriptJobClean():
    count = 0
    foundError = 1
    while foundError > 0 and count < 10:
        jobs = mc.scriptJob( listJobs=True )
        foundError = 0
        for j in jobs:
            if "finishBendClean" in j:
                jID = j.split(':')[0]
                print(jID)
                try:
                    mc.scriptJob (kill = int(jID),f =1 )
                except:
                    foundError = 1

        count +=  1
    
def speedBend():
    if mc.window("speedBendUI", exists=True):
        mc.deleteUI("speedBendUI")
    speedBendUI = mc.window("speedBendUI",title = "speedBend v1.07",w = 350,h = 150)
    mc.frameLayout(label="Bend Extrude:",lv=0, bv=0, w=295, mw=3, mh=5)
    mc.columnLayout(adj=1)
    mc.rowColumnLayout(nc=5, cw=[(1, 220), (2, 30), (3, 30),(4, 30),(5, 30)])
    mc.floatSliderGrp("speedBendBend", cw3=[50, 50, 0], label="     Bend", f=1, v=90, min=-180, max=180, pre=0, cc='speedBendBendUpdate()')
    mc.button(label="X", c="speedBendBendReset()", bgc=[0.24, 0.24, 0.24])
    mc.intField('speedBendBendV', v =45, bgc =[0.24,0.24,0.24])
    mc.button(label="-", c="speedBendBendMore(-1)", bgc=[0.24, 0.24, 0.24])
    mc.button(label="+", c="speedBendBendMore(1)", bgc=[0.24, 0.24, 0.24])

    mc.floatSliderGrp("speedBendRoll", cw3=[50, 50, 0], label="    Roll", f=1, v=45, min=-180, max=180, fmx=360, pre=0, cc="speedBendRollUpdate()")
    mc.button(label="X", c="speedBendRollReset()", bgc=[0.24, 0.24, 0.24])
    mc.intField('speedBendRollV', v =45, bgc =[0.24,0.24,0.24] )
    mc.button(label="-", c="speedBendRollMore(-1)", bgc=[0.24, 0.24, 0.24])
    mc.button(label="+", c="speedBendRollMore(1)", bgc=[0.24, 0.24, 0.24])

    mc.floatSliderGrp("speedBendOffset", cw3=[50, 50, 0], label="    Offset", f=1, v=0, min=-0.1, max=1, pre=1)
    mc.button(label="X", c="speedBendOffsetReset()", bgc=[0.24, 0.24, 0.24])
    mc.button("speedBendOffsetV", en= 0,label="", bgc=[0.24, 0.24, 0.24])
    mc.button('sBOffsetMinus',label="-", c="speedBendOffsetMore(-1)", bgc=[0.24, 0.24, 0.24])
    mc.button('sBOffsetPlus',label="+", c="speedBendOffsetMore(1)", bgc=[0.24, 0.24, 0.24])

    mc.intSliderGrp("speedBendDiv", cw3=[50, 50, 0], label="Divisions", v=4, f=1, min=1, max=16, fmx=36)
    mc.button(label="X", c="speedBendDivReset()", bgc=[0.24, 0.24, 0.24])
    mc.setParent("..")

    mc.rowColumnLayout(nc=7, cw=[(1, 18),(2, 100), (3, 100), (4, 2), (5, 58), (6, 2), (7, 58)])
    mc.text(l ='')
    mc.columnLayout(adj=1)
    mc.checkBox('speedBendSetting',label="Remember", value= 0)
    mc.checkBox('speedBendNoDiv',label="No Divisions", value= 0)
    mc.setParent("..")
    mc.iconTextButton("speedBendGOGO", style='textOnly', l ="Bend", c="speedBendGo()",rpt = 1, bgc=[0.2, 0.2, 0.2])
    mc.text(l ='')
    mc.iconTextButton("speedBendExtrude", style='textOnly', l ="Extrude", c="speedBendExtrudeGO()",rpt = 1, bgc=[0.2, 0.2, 0.2])
    mc.text(l ='')
    mc.iconTextButton(style='textOnly', l ="Done", c="finishBendClean()", bgc=[0.3, 0.2, 0.2])
    mc.showWindow(speedBendUI)

speedBend()
#face
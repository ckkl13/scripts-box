##--------------------------------------------------------------------------
##
## ScriptName : free Form
## Contents   : polygon bridge/blend between selected edge loops with lots of control.
## Author     : Joe Wu
## URL        : https://www.youtube.com/@Im3dJoe
## Since      : 2021/09
## Version    : 0.2 bug fixing
## Version    : 0.3 global and local switching ,bridge
## Version    : 0.4 adding fan control
## Version    : 0.5 edgeloop order bug fix, world direction algin to middle loop
## Version    : 0.6 mode 1 and mode 2 for different controller
## Version    : 0.7 remove mode switch as not good
## Version    : 0.8 redesign push direcrion
## Version    : 1.0 public release
## Version    : 1.01 fix bug in maya 2022
## Version    : 1.02 improve undo , add drift slider
## Version    : 1.03 enable division slider for blend mode
## Version    : 1.04 division slider only activate when select edges in the edge border
## Version    : 1.05 fix bug in python 3 where int / int = float, use int // int = int
## Version    : 1.1  remove pymel
## Install    : copy and paste script into a python tab in maya script editor
##--------------------------------------------------------------------------

import maya.cmds as mc
import maya.mel as mel
import math
import re
from maya.OpenMaya import MGlobal
#from pymel.core.datatypes import Vector, Matrix, Point
import maya.OpenMaya as om
import maya.OpenMayaUI as omui
import maya.api.OpenMaya as OpenMaya


def pushTypeSwitch():
    typeCheck = mc.radioButtonGrp('PushDirType',q=1, sl=1)
    listAllOffset = mc.ls('*_ControlOffset',fl=1)
    attList = ['NX','NY','NZ','GX','GY','GZ']
    chanelList = ['rotateX','rotateY','rotateZ']
    if typeCheck == 1:
        for l in listAllOffset:
            for x in range(len(chanelList)):
                NV = mc.getAttr(l+'.' + attList[x])
                mc.setAttr((l+'.' + chanelList[x]),NV)
        dirListA = mc.ls('*_A_ControlDirection',fl=1)
        dirListB = mc.ls('*_B_ControlDirection',fl=1)
        for l in dirListA:
            for x in chanelList:
                mc.setAttr(( l + '.' + x ), 0)
        for l in dirListB:
            for x in chanelList:
                mc.setAttr(( l + '.' + x ), 0)
        mc.radioButtonGrp('RotateAlginType',e=1,en=0)
    else:
        for l in listAllOffset:
            for x in range(len(chanelList)):
                GV = mc.getAttr(l+'.' + attList[x+3])
                mc.setAttr((l+'.' + chanelList[x]),GV)
        pushDirectionSwitch()
        mc.radioButtonGrp('RotateAlginType',e=1,en=1)

def pushDirectionSwitch():
    checkDir = mc.radioButtonGrp('RotateAlginType',q=1, sl=1)
    dirListA = mc.ls('*_A_ControlDirection',fl=1)
    dirListB = mc.ls('*_B_ControlDirection',fl=1)
    chanelList = ['rotateX','rotateY','rotateZ']
    if checkDir == 1 :
        for l in dirListA:
                mc.setAttr(( l + '.rotateX'  ), 90)
        for l in dirListB:
                mc.setAttr(( l +  '.rotateX'), -90)

    elif checkDir == 2 :
        for l in dirListA:
            for x in chanelList:
                mc.setAttr(( l + '.' + x ), 0)
        for l in dirListB:
            for x in chanelList:
                mc.setAttr(( l + '.' + x ), 0)


def updateOffsetGap():
    xyzV = mc.floatSliderGrp('xyzSlider',q=1, v=1)
    listAllOffset = mc.ls('*_ControlOffset',fl=1)
    attList = ['NX','NY','NZ','GX','GY','GZ']
    chanelList = ['rotateX','rotateY','rotateZ']
    for l in listAllOffset:
        for x in range(len(chanelList)):
            NV = mc.getAttr(l+'.' + attList[x])
            GV = mc.getAttr(l+'.' + attList[x+3])
            gap = GV - NV
            newV = NV + (gap * xyzV)
            mc.setAttr((l+'.' + chanelList[x]),newV)

def killFreeFrom():
    if mc.objExists('tensionGrp'):
        mc.delete('tensionGrp')

def updateFanRot():
    fanV = mc.floatSliderGrp('fanSlider', q=1, v = 1)
    listAllGlobalA = mc.ls('*A_ControlGlobal',fl=1)
    listAllGlobalB = mc.ls('*B_ControlGlobal',fl=1)
    totalN = len(listAllGlobalA)
    checkEven = totalN % 2
    gapNumber = 0
    if checkEven == 1:
        gapNumber = (totalN/2)
    else:
        gapNumber = (totalN/2)-1
    fanGap = fanV / (gapNumber-1)
    #first Half
    a = gapNumber

    for i in range(int(totalN/2)):
        mc.setAttr( (listAllGlobalA[i]+ '.rotateY') , ((a)*fanGap) + (1.0/gapNumber)*fanGap )
        mc.setAttr( (listAllGlobalB[i]+ '.rotateY') , (-1*(a)*fanGap) - (1.0/gapNumber)*fanGap )
        a = a -1
    #sec Half
    a = gapNumber
    for i in reversed(range((int(totalN/2) + checkEven),totalN)):
        mc.setAttr( (listAllGlobalA[i]+ '.rotateY') ,(-1*(a)*fanGap) - (1.0/gapNumber)*fanGap )
        mc.setAttr( (listAllGlobalB[i]+ '.rotateY') ,((a)*fanGap) + (1.0/gapNumber)*fanGap )
        a = a -1
    if checkEven == 0:
        mc.setAttr( (listAllGlobalA[gapNumber]+ '.rotateY') , (fanGap/2.5))
        mc.setAttr( (listAllGlobalB[gapNumber]+ '.rotateY') , (-1*fanGap/2.5))

        mc.setAttr( (listAllGlobalA[gapNumber+1]+ '.rotateY') , (-1*fanGap/2.5))
        mc.setAttr( (listAllGlobalB[gapNumber+1]+ '.rotateY') , (fanGap/2.5))

def buildBridge():
    global selMeshForDeformer
    selMeshForDeformer = mc.ls(sl=1,o=1)
    mc.intSliderGrp('bridgeDivisionSlider', e =1, en = 1 )
    selEdges = mc.ls(sl=1,fl=1)
    mc.polySelectConstraint(m=2,w=1,type = 0x8000 )
    mc.polySelectConstraint(disable=True)
    checkBorder = mc.ls(sl=1,fl=1)
    freeFromDone()
    mc.select(selEdges)
    meshName = selEdges[0].split('.')[0]
    if len(checkBorder)>0:
        try:
            bridgeNode = mc.polyBridgeEdge(ch=1, divisions=20, twist=0, taper=1, curveType=0, smoothingAngle=30, direction=0, sourceDirection=0, targetDirection=0)
            freeFromRun()
            mc.connectControl( 'bridgeDivisionSlider', bridgeNode[0]+'.divisions')
            mc.intSliderGrp('bridgeDivisionSlider', e=1 , v = 5)
            mc.setAttr((bridgeNode[0]+'.divisions'),5)
            mc.intSliderGrp('bridgeDivisionSlider',e=1,en=1)
        except:
            mc.select(selEdges)
            cmd = 'doMenuComponentSelection("' + meshName +'", "edge");'
            mel.eval(cmd)
            mc.scriptEditorInfo(clearHistory=1)
            print('unable to bridge!')
    else:
        mc.scriptEditorInfo(clearHistory=1)
        cmd = 'doMenuComponentSelection("' + meshName +'", "edge");'
        mel.eval(cmd)
        print('unable to bridge!')


def freeFromDone():
    global selMeshForDeformer
    if len(selMeshForDeformer)>0:
        if mc.objExists(selMeshForDeformer[0]):
            mc.select(selMeshForDeformer[0])
            mc.DeleteHistory()
    if mc.objExists('tensionGrp'):
        mc.delete('tensionGrp')
    freeFormResetAll()
    mc.radioButtonGrp('PushDirType',e=1, sl=1)
    mc.radioButtonGrp('RotateAlginType', e=1, sl=2 ,en=0)


def freeFromRunNew():
    checkSel = mc.filterExpand(expand=True ,sm=32)
    if len(checkSel)>0:
        mc.ConvertSelectionToVertices()
        mc.polySelectConstraint(m=2,t=0x0001,w=1)
        checkBorder = mc.ls(sl=1,fl=1)
        mc.polySelectConstraint(disable =True)
        mc.select(checkSel)
        if len(checkBorder)== 4:
            if mc.objExists('tempSaveEdge'):
                mc.delete('tempSaveEdge')
            mc.sets(name = 'tempSaveEdge', text= 'tempSaveEdge')
            mc.SelectEdgeRingSp()
            sortEdgeLoopGrp =  getEdgeRingGroup(0,'')
            divisionNo = len(sortEdgeLoopGrp) - 2
            mc.ConvertSelectionToVertices()
            mc.ConvertSelectionToContainedFaces()
            mc.delete()
            mc.select('tempSaveEdge')
            buildBridge()
            mc.delete('tempSaveEdge')
            mc.setAttr("polyBridgeEdge1.divisions",divisionNo)
        else:
            freeFromRun()    


def freeFromRun():
    global selMeshForDeformer
    global sideACVList
    selBlendEdgeLoop = mc.filterExpand(expand=True ,sm=32)
    selMeshForDeformer = mc.ls(sl=1,o=1)
    mc.intSliderGrp('bridgeDivisionSlider',e=1,en=0)
    if not mc.objExists('tensionGrp'):
        mc.group(empty=1,n= 'tensionGrp')
    else:
        if len(selMeshForDeformer)>0:
            if mc.objExists(selMeshForDeformer[0]):
                mc.select(selMeshForDeformer[0])
                mc.DeleteHistory()
        if mc.objExists('arcCurve*'):
            mc.delete('arcCurve*')
    mc.setAttr("tensionGrp.visibility", 0)
    if len(selBlendEdgeLoop)>0:
        mc.select(selBlendEdgeLoop)
    sortEdgeLoopGrp =  getEdgeRingGroup(0,'')
    if len(sortEdgeLoopGrp) == 2:
        if len(sortEdgeLoopGrp[0]) == len(sortEdgeLoopGrp[1]):
            mc.select(sortEdgeLoopGrp[0])
            mc.ConvertSelectionToVertices()
            sideACVList = mc.ls(sl=1,fl=1)
            mc.select(selBlendEdgeLoop)
            mc.polySelectSp(ring=1)
            edgeRingList = mc.ls(sl=1)
            mc.ConvertSelectionToVertices()
            mc.ConvertSelectionToContainedFaces()
            mc.ConvertSelectionToEdges()
            mc.select(edgeRingList,d=1)
            edgeLoopsList =  getEdgeRingGroup(1,sortEdgeLoopGrp[0])

            for e in edgeLoopsList:
                strightenEdgeLoopEven(e)
            
            for e in edgeLoopsList:
                tensionCurveSetup(e)

            mc.evalDeferred('pushTypeSwitch()')
            mc.evalDeferred('pushDirectionSwitch()')
            mc.select(selMeshForDeformer,r=1)
            freeFormResetAll()

            listHistoryNode = mc.listHistory( selMeshForDeformer, future=True )
            findBridge = 0
            for h in listHistoryNode:
                nodeTypeCheck = mc.nodeType(h)
                if nodeTypeCheck == 'polyBridgeEdge':
                    findBridge = 1
                mc.intSliderGrp('bridgeDivisionSlider', e=1,en = findBridge)
            connectUI()
        else:
            print('edge loop number not match!')
    else:
        print('please select ONLY two edge loop!')



def freeFormResetAll():
    tensionGlobalReset()
    tensionLocalARest()
    tensionLocalBRest()
    sharpGlobalReset()
    sharpLocalAReset()
    sharpLocalBReset()
    fanRest()

#####################################################################################
                
def connectUI():
    connectList = ["tenstionV","tenstionA","tenstionB","sharpV","sharpA","sharpB","fanV","driftV"]
    for c in connectList:
        checkState = mc.attributeQuery(c,node = "tensionGrp",ex=True)
        if checkState == 0:
            mc.addAttr("tensionGrp", ln= c, attributeType='double', dv=0)
        mc.connectControl((c  + 'Slider'), ('tensionGrp.' + c))
    
    listAllGlobal = mc.ls('*_A_Control',fl=1)
    for l in listAllGlobal:
        expressionConnect(l,"rotateZ","tensionGrp","tenstionA")
        expressionConnect(l,"scaleX","tensionGrp","sharpA")
        expressionConnect(l,"scaleY","tensionGrp","sharpA")
        expressionConnect(l,"scaleZ","tensionGrp","sharpA")
    
    
    listAllGlobal = mc.ls('*_B_Control',fl=1)
    for l in listAllGlobal:
        expressionConnect(l,"rotateZ","tensionGrp","tenstionB")
        expressionConnect(l,"scaleX","tensionGrp","sharpB")
        expressionConnect(l,"scaleY","tensionGrp","sharpB")
        expressionConnect(l,"scaleZ","tensionGrp","sharpB")
    
    listAllGlobal = mc.ls('*_ControlGlobal',fl=1)
    for l in listAllGlobal:
        expressionConnect(l,"rotateZ","tensionGrp","tenstionV")
        expressionConnect(l,"scaleX","tensionGrp","sharpV")
        expressionConnect(l,"scaleY","tensionGrp","sharpV")
        expressionConnect(l,"scaleZ","tensionGrp","sharpV")
    
    mc.setAttr("tensionGrp.sharpA", 1)
    mc.setAttr("tensionGrp.sharpB", 1)
    mc.setAttr("tensionGrp.sharpV", 1)
    mc.setAttr("tensionGrp.tenstionV", 10)


###########################################################################################################

    listAllGlobalA = mc.ls('*A_ControlGlobal',fl=1)
    listAllGlobalB = mc.ls('*B_ControlGlobal',fl=1)
    totalN = len(listAllGlobalA)
    checkEven = totalN % 2
    gapNumber = 0
    
    
    if checkEven == 1:
        gapNumber = (totalN//2)
    else:
        gapNumber = (totalN//2)-1
    
    a = gapNumber        
    fanGap =' tensionGrp.fanV / ' +  str(gapNumber-1)
 
    if checkEven == 0:
        for i in range(int(totalN/2)-1):
            cmdTextA = ( str(listAllGlobalA[i]) + '.rotateY = (' + str(a) + '*' + fanGap + ') +  (1.0/ ' + str(gapNumber) + '*' + fanGap + ') + tensionGrp.driftV;')
            mc.expression( s = cmdTextA, o = listAllGlobalA[i], ae = True, uc = all)
            cmdTextA = ( str(listAllGlobalB[i]) + '.rotateY = (-1*' + str(a) + '*' + fanGap + ') -  (1.0/ ' + str(gapNumber) + '*' + fanGap + ') - tensionGrp.driftV;')
            mc.expression( s = cmdTextA, o = listAllGlobalB[i], ae = True, uc = all)
            a = a -1
    ###########################################################################################################    

        a = gapNumber
        for i in reversed(range(((int(totalN/2)+1) + checkEven),totalN)):
            cmdTextA = ( str(listAllGlobalB[i]) + '.rotateY = (' + str(a) + '*' + fanGap + ') +  (1.0/ ' + str(gapNumber) + '*' + fanGap + ') - tensionGrp.driftV;')
            mc.expression( s = cmdTextA, o = listAllGlobalB[i], ae = True, uc = all)
            cmdTextA = ( str(listAllGlobalA[i]) + '.rotateY = (-1*' + str(a) + '*' + fanGap + ') -  (1.0/ ' + str(gapNumber) + '*' + fanGap + ') + tensionGrp.driftV;')
            mc.expression( s = cmdTextA, o = listAllGlobalA[i], ae = True, uc = all)
            a = a -1
    
        cmdTextA = ( str(listAllGlobalA[gapNumber]) + '.rotateY = (' + fanGap + '/2.5) + tensionGrp.driftV;')
        mc.expression( s = cmdTextA, o = listAllGlobalA[i], ae = True, uc = all)
        cmdTextA = ( str(listAllGlobalB[gapNumber]) + '.rotateY = (-1*' + fanGap + '/2.5) - tensionGrp.driftV;')
        mc.expression( s = cmdTextA, o = listAllGlobalA[i], ae = True, uc = all)
        cmdTextA = ( str(listAllGlobalB[gapNumber+1]) + '.rotateY = (' + fanGap + '/2.5) - tensionGrp.driftV;')
        mc.expression( s = cmdTextA, o = listAllGlobalA[i], ae = True, uc = all)
        cmdTextA = ( str(listAllGlobalA[gapNumber+1]) + '.rotateY = (-1*' + fanGap + '/2.5) + tensionGrp.driftV;')
        mc.expression( s = cmdTextA, o = listAllGlobalA[i], ae = True, uc = all)
        
    else:
        for i in range(int(totalN/2)):
            cmdTextA = ( str(listAllGlobalA[i]) + '.rotateY = (' + str(a) + '*' + fanGap + ') +  (1.0/ ' + str(gapNumber) + '*' + fanGap + ') + tensionGrp.driftV;')
            mc.expression( s = cmdTextA, o = listAllGlobalA[i], ae = True, uc = all)
            cmdTextA = ( str(listAllGlobalB[i]) + '.rotateY = (-1*' + str(a) + '*' + fanGap + ') -  (1.0/ ' + str(gapNumber) + '*' + fanGap + ') - tensionGrp.driftV;')
            mc.expression( s = cmdTextA, o = listAllGlobalB[i], ae = True, uc = all)
            a = a -1
    ###########################################################################################################    

        a = gapNumber
        for i in reversed(range((int(totalN/2) + checkEven),totalN)):
            cmdTextA = ( str(listAllGlobalB[i]) + '.rotateY = (' + str(a) + '*' + fanGap + ') +  (1.0/ ' + str(gapNumber) + '*' + fanGap + ') - tensionGrp.driftV;')
            mc.expression( s = cmdTextA, o = listAllGlobalB[i], ae = True, uc = all)
            cmdTextA = ( str(listAllGlobalA[i]) + '.rotateY = (-1*' + str(a) + '*' + fanGap + ') -  (1.0/ ' + str(gapNumber) + '*' + fanGap + ') + tensionGrp.driftV;')
            mc.expression( s = cmdTextA, o = listAllGlobalA[i], ae = True, uc = all)
            a = a -1
        mid = int(totalN/2)
        cmdTextA = ( str(listAllGlobalA[mid]) + '.rotateY = tensionGrp.driftV;')
        mc.expression( s = cmdTextA, o = listAllGlobalA[mid], ae = True, uc = all)
        cmdTextA = ( str(listAllGlobalB[mid]) + '.rotateY = -1*tensionGrp.driftV;')
        mc.expression( s = cmdTextA, o = listAllGlobalA[mid], ae = True, uc = all)

def expressionConnect(expSource,expSourceV,expTarget,expTargetV):
    cmdTextA = (expSource + '.' + expSourceV + '= ' + expTarget  + '.' + expTargetV +';')
    mc.expression( s = cmdTextA, o = expSource, ae = True, uc = all)
 

#####################################################################################

def sharpGlobalReset():
    mc.floatSliderGrp('sharpVSlider',e=1, v=1 )
    if mc.objExists('tensionGrp'):
        checkState = mc.attributeQuery('sharpV',node = "tensionGrp",ex=True)
        if checkState:
             mc.setAttr("tensionGrp.sharpV", 1)

def sharpLocalAReset():
    mc.floatSliderGrp('sharpASlider',e=1, v=1 )
    if mc.objExists('tensionGrp'):
        checkState = mc.attributeQuery('sharpA',node = "tensionGrp",ex=True)
        if checkState:
            mc.setAttr("tensionGrp.sharpA", 1)

def sharpLocalBReset():
    mc.floatSliderGrp('sharpBSlider',e=1, v=1 )
    if mc.objExists('tensionGrp'):
        checkState = mc.attributeQuery('sharpB',node = "tensionGrp",ex=True)
        if checkState:
            mc.setAttr("tensionGrp.sharpB", 1)

def driftRest():
    mc.floatSliderGrp('driftVSlider',e=1, v=0)
    if mc.objExists('tensionGrp'):
        checkState = mc.attributeQuery('driftV',node = "tensionGrp",ex=True)
        if checkState:
            mc.setAttr("tensionGrp.driftV", 0)

def fanRest():
    mc.floatSliderGrp('fanVSlider',e=1, v=0)
    if mc.objExists('tensionGrp'):
        checkState = mc.attributeQuery('fanV',node = "tensionGrp",ex=True)
        if checkState:
            mc.setAttr("tensionGrp.fanV", 0)

def tensionGlobalReset():
    mc.floatSliderGrp('tenstionVSlider',e=1, v=10)
    if mc.objExists('tensionGrp'):
        checkState = mc.attributeQuery('tenstionV',node = "tensionGrp",ex=True)
        if checkState:
            mc.setAttr("tensionGrp.tenstionV", 10)
    
def tensionLocalARest():
    mc.floatSliderGrp('tenstionASlider',e=1, v=0 )
    if mc.objExists('tensionGrp'):
        checkState = mc.attributeQuery('tenstionA',node = "tensionGrp",ex=True)
        if checkState:
            mc.setAttr("tensionGrp.tenstionA", 0)

def tensionLocalBRest():
    mc.floatSliderGrp('tenstionBSlider',e=1, v=0 )
    if mc.objExists('tensionGrp'):
        checkState = mc.attributeQuery('tenstionB',node = "tensionGrp",ex=True)
        if checkState:
            mc.setAttr("tensionGrp.tenstionB", 0)




def getEdgeRingGroup(listSort,listInput):
    selEdges = mc.ls(sl=1,fl=1)
    trans = selEdges[0].split(".")[0]
    e2vInfos = mc.polyInfo(selEdges, ev=True)
    e2vDict = {}
    fEdges = []
    for info in e2vInfos:
        evList = [ int(i) for i in re.findall('\\d+', info) ]
        e2vDict.update(dict([(evList[0], evList[1:])]))
    while True:
        try:
            startEdge, startVtxs = e2vDict.popitem()
        except:
            break
        edgesGrp = [startEdge]
        num = 0
        for vtx in startVtxs:
            curVtx = vtx
            while True:

                nextEdges = []
                for k in e2vDict:
                    if curVtx in e2vDict[k]:
                        nextEdges.append(k)
                if nextEdges:
                    if len(nextEdges) == 1:
                        if num == 0:
                            edgesGrp.append(nextEdges[0])
                        else:
                            edgesGrp.insert(0, nextEdges[0])
                        nextVtxs = e2vDict[nextEdges[0]]
                        curVtx = [ vtx for vtx in nextVtxs if vtx != curVtx ][0]
                        e2vDict.pop(nextEdges[0])
                    else:
                        break
                else:
                    break
            num += 1
        fEdges.append(edgesGrp)
    retEdges =[]
    for f in fEdges:
        f= list(map(lambda x: (trans +".e["+ str(x) +"]"), f))
        retEdges.append(f)
    if listSort == 1:
        sortEdgeLoopOrder=[]
        getCircleState,listVtx = vtxLoopOrderCheck(listInput)
        for l in listVtx:
            for r in retEdges:
                checkCvList = mc.ls(mc.polyListComponentConversion( r,fe=True, tv=True), fl=True,l=True)
                if l in checkCvList:
                    sortEdgeLoopOrder.append(r)
        return sortEdgeLoopOrder
    else:
        return retEdges


def strightenEdgeLoopEven(selEdge):
    getCircleState,listVtx = vtxLoopOrderCheck(selEdge)
    p1 = mc.pointPosition(listVtx[0], w =1)
    p3 = mc.pointPosition(listVtx[-1], w =1)
    mc.curve( d=1, p= [(p1[0],  p1[1] , p1[2]), (p3[0],  p3[1] , p3[2])] ,k=[0,1])
    mc.rename('strightenCurve')
    storeCurveName = mc.ls(sl=1)
    mc.delete(storeCurveName[0] ,ch=1)
    totalEdgeLoopLength = 0;
    sum = 0
    Llist = []
    uList = []
    pList = []
    for i in selEdge:
        e2v =mc.polyListComponentConversion(i,fe=1, tv=1)
        e2v = mc.ls(e2v,fl=1)
        pA = mc.pointPosition(e2v[0], w =1)
        pB = mc.pointPosition(e2v[1], w =1)
        checkDistance = math.sqrt( ((pA[0] - pB[0])**2)  + ((pA[1] - pB[1])**2)  + ((pA[2] - pB[2])**2) )
        Llist.append(checkDistance)
        totalEdgeLoopLength = totalEdgeLoopLength + checkDistance

    avg = totalEdgeLoopLength / (len(selEdge))
    for j in range(len(selEdge)):
        sum = ((j+1)*avg)
        uList.append(sum)

    for k in uList:
        p = k / totalEdgeLoopLength
        if p > 1:
            p = 1
        pList.append(p)

    for q in range(len(pList)):
        if q+1 == len(listVtx):
            pp = mc.pointOnCurve(storeCurveName[0] , pr = 0, p=1)
            mc.move( pp[0], pp[1], pp[2],listVtx[0] , a =True, ws=True)
        else:
            pp = mc.pointOnCurve(storeCurveName[0] , pr = pList[q], p=1)
            mc.move( pp[0], pp[1], pp[2],listVtx[q+1] , a =True, ws=True)
    mc.delete(storeCurveName[0])

def tensionCurveSetup(selEdge):
    mayaV = mc.about(version=True)
    global sideACVList
    getCircleState,listVtx = vtxLoopOrderCheck(selEdge)
    if listVtx[0].split('|')[-1] in sideACVList:
        pass
    else:
        listVtx.reverse()
    deformerNames = []
    p1 = mc.pointPosition(listVtx[0], w =1)
    p3 = mc.pointPosition(listVtx[-1], w =1)
    mc.curve( d=1, p= [(p1[0],  p1[1] , p1[2]), (p3[0],  p3[1] , p3[2])] ,k=[0,1])
    mc.rename('arcCurve01')
    storeCurveName = mc.ls(sl=1,l=1)
    mc.parent(storeCurveName[0],'tensionGrp')
    storeCurveName = mc.ls(sl=1)
    mc.nurbsCurveToBezier()
    storeCurveName = mc.ls(sl=1)
    midP = int(len(listVtx)/2)
    mc.select(selEdge[midP])
    #get average face normal
    mc.ConvertSelectionToFaces()
    faceList = mc.ls(sl=1,fl=1)

    sumX = 0
    sumY = 0
    sumZ = 0

    for f in faceList:
        rx, ry, rz = checkFaceAngle(f)
        sumX = sumX + rx
        sumY = sumY + ry
        sumZ = sumZ + rz
    avgX =  sumX /len(faceList)
    avgY =  sumY /len(faceList)
    avgZ =  sumZ /len(faceList)

    p2 = mc.pointPosition(listVtx[midP], w =1)
    mc.spaceLocator(p=( p2[0],p2[1],p2[2]),n='midLocator')
    mc.CenterPivot()
    mc.setAttr('midLocator.rotate', avgX,avgY,avgZ)
    mc.select(storeCurveName[0])
    #wireWrap
    deformerNames = []
    if mayaV > '2020':
        deformerNames  = mc.wire( selEdge, gw=0, en = 1, ce = 0, li= 0, dds = [(0,1)], dt=1, uct = 0, w =storeCurveName[0])
    else:
        deformerNames  = mc.wire( selEdge, gw=0, en = 1, ce = 0, li= 0, dds = [(0,1)], dt=1, w =storeCurveName[0])
    mc.setAttr((deformerNames[0] + '.dropoffDistance[0]'),1)

    cA = mc.pointPosition((storeCurveName[0] + '.cv[0]'), w =1)
    cD = mc.pointPosition((storeCurveName[0]+'.cv[3]'), w =1)
    if mayaV > '2020':
        mc.cluster((storeCurveName[0]+'.cv[1]') , uct = 0, name = storeCurveName[0] + '_A_' )
    else:
        mc.cluster((storeCurveName[0]+'.cv[1]') , name = storeCurveName[0] + '_A_' )
    mc.group(empty=1,n= storeCurveName[0] + '_A_Control')
    mc.group(empty=1,n= storeCurveName[0] + '_A_ControlGlobal')
    mc.group(empty=1,n= storeCurveName[0] + '_A_ControlOffset')
    mc.group(empty=1,n= storeCurveName[0] + '_A_ControlDirection')
    mc.move( cA[0], cA[1], cA[2],( storeCurveName[0] + '_A_Handle.scalePivot'),( storeCurveName[0] + '_A_Handle.rotatePivot'), a =True, ws=True)
    mc.move( cA[0], cA[1], cA[2],( storeCurveName[0] + '_A_Control.scalePivot'),( storeCurveName[0] + '_A_Control.rotatePivot'), a =True, ws=True)
    mc.move( cA[0], cA[1], cA[2],( storeCurveName[0] + '_A_ControlGlobal.scalePivot'),( storeCurveName[0] + '_A_ControlGlobal.rotatePivot'), a =True, ws=True)
    mc.move( cA[0], cA[1], cA[2],( storeCurveName[0] + '_A_ControlOffset.scalePivot'),( storeCurveName[0] + '_A_ControlOffset.rotatePivot'), a =True, ws=True)
    mc.move( cA[0], cA[1], cA[2],( storeCurveName[0] + '_A_ControlDirection.scalePivot'),( storeCurveName[0] + '_A_ControlDirection.rotatePivot'), a =True, ws=True)
    if mayaV > '2020':
        mc.cluster((storeCurveName[0]+'.cv[2]') , uct = 0, name = storeCurveName[0] + '_B_' )
    else:
        mc.cluster((storeCurveName[0]+'.cv[2]') , name = storeCurveName[0] + '_B_' )
    mc.group(empty=1,n= storeCurveName[0] + '_B_Control')
    mc.group(empty=1,n= storeCurveName[0] + '_B_ControlGlobal')
    mc.group(empty=1,n= storeCurveName[0] + '_B_ControlOffset')
    mc.group(empty=1,n= storeCurveName[0] + '_B_ControlDirection')
    mc.move(cD[0], cD[1], cD[2],( storeCurveName[0] + '_B_Handle.scalePivot'),( storeCurveName[0] + '_B_Handle.rotatePivot'), a =True, ws=True)
    mc.move(cD[0], cD[1], cD[2],( storeCurveName[0] + '_B_Control.scalePivot'),( storeCurveName[0] + '_B_Control.rotatePivot'), a =True, ws=True)
    mc.move(cD[0], cD[1], cD[2],( storeCurveName[0] + '_B_ControlGlobal.scalePivot'),( storeCurveName[0] + '_B_ControlGlobal.rotatePivot'), a =True, ws=True)
    mc.move(cD[0], cD[1], cD[2],( storeCurveName[0] + '_B_ControlOffset.scalePivot'),( storeCurveName[0] + '_B_ControlOffset.rotatePivot'), a =True, ws=True)
    mc.move(cD[0], cD[1], cD[2],( storeCurveName[0] + '_B_ControlDirection.scalePivot'),( storeCurveName[0] + '_B_ControlDirection.rotatePivot'), a =True, ws=True)

    consNodeA = mc.aimConstraint((storeCurveName[0] + '_A_Control'),(storeCurveName[0] + '_B_Control'),offset=[0,0,0], weight=1, aimVector=[1,0,0], upVector=[0,1,0], worldUpType='scene')
    consNodeB = mc.aimConstraint((storeCurveName[0] + '_B_Control'),(storeCurveName[0] + '_A_Control'),offset=[0,0,0], weight=1, aimVector=[1,0,0], upVector=[0,1,0], worldUpType='scene')

    attList = ['NX','NY','NZ','GX','GY','GZ']
    chanelList = ['rotateX','rotateY','rotateZ']
    # create attr and reocrd
    recordList  = [(storeCurveName[0] + '_A_Control'),(storeCurveName[0] + '_B_Control')]

    for l in recordList:
        for a in attList:
            if not mc.attributeQuery(a, node = l, ex=True ):
                mc.addAttr(l + 'Offset', ln= a,  at= 'double')
                mc.setAttr(( l + 'Offset.' + a),e=True, keyable=True)

        for x in range(len(chanelList)):
                    v = mc.getAttr(l+'.' + chanelList[x])
                    mc.setAttr(( l + 'Offset.' + attList[x+3]), v)
    mc.delete(consNodeA, consNodeB)

    mc.aimConstraint((storeCurveName[0] + '_A_Control'),(storeCurveName[0] + '_B_Control'),offset=[0,0,0], weight=1, aimVector=[1,0,0], upVector=[0,1,0], worldUpType='objectrotation' ,worldUpObject='midLocator')
    mc.aimConstraint((storeCurveName[0] + '_B_Control'),(storeCurveName[0] + '_A_Control'),offset=[0,0,0], weight=1, aimVector=[1,0,0], upVector=[0,1,0], worldUpType='objectrotation' ,worldUpObject='midLocator')

    for l in recordList:
        for x in range(len(chanelList)):
                    v = mc.getAttr(l+'.' + chanelList[x])
                    mc.setAttr(( l + 'Offset.' + attList[x]), v)

    mc.matchTransform((storeCurveName[0] + '_A_ControlOffset'),(storeCurveName[0] + '_A_Control'),rot=1)
    mc.matchTransform((storeCurveName[0] + '_A_ControlGlobal'),(storeCurveName[0] + '_A_Control'),rot=1)
    mc.matchTransform((storeCurveName[0] + '_A_ControlDirection'),(storeCurveName[0] + '_A_Control'),rot=1)
    mc.parent((storeCurveName[0] + '_A_Control'),(storeCurveName[0] + '_A_ControlGlobal'))
    mc.parent((storeCurveName[0] + '_A_ControlGlobal'),(storeCurveName[0] + '_A_ControlDirection'))
    mc.parent((storeCurveName[0] + '_A_ControlDirection'),(storeCurveName[0] + '_A_ControlOffset'))
    mc.parent((storeCurveName[0] + '_A_Handle'),(storeCurveName[0] + '_A_Control'))

    mc.matchTransform((storeCurveName[0] + '_B_ControlOffset'),(storeCurveName[0] + '_B_Control'),rot=1)
    mc.matchTransform((storeCurveName[0] + '_B_ControlGlobal'),(storeCurveName[0] + '_B_Control'),rot=1)
    mc.matchTransform((storeCurveName[0] + '_B_ControlDirection'),(storeCurveName[0] + '_B_Control'),rot=1)
    mc.parent((storeCurveName[0] + '_B_Control'),(storeCurveName[0] + '_B_ControlGlobal'))
    mc.parent((storeCurveName[0] + '_B_ControlGlobal'),(storeCurveName[0] + '_B_ControlDirection'))
    mc.parent((storeCurveName[0] + '_B_ControlDirection'),(storeCurveName[0] + '_B_ControlOffset'))
    mc.parent((storeCurveName[0] + '_B_Handle'),(storeCurveName[0] + '_B_Control'))

    mc.delete((storeCurveName[0] + '*'),constraints=1)
    mc.delete('midLocator')
    mc.parent((storeCurveName[0] + '_A_ControlOffset'),'tensionGrp')
    mc.parent((storeCurveName[0] + '_B_ControlOffset'),'tensionGrp')

def vtxLoopOrderCheck(selEdges):
    shapeNode = mc.listRelatives(selEdges[0], fullPath=True , parent=True )
    transformNode = mc.listRelatives(shapeNode[0], fullPath=True , parent=True )
    edgeNumberList = []
    for a in selEdges:
        checkNumber = ((a.split('.')[1]).split('\n')[0]).split(' ')
        for c in checkNumber:
            findNumber = ''.join([n for n in c.split('|')[-1] if n.isdigit()])
            if findNumber:
                edgeNumberList.append(findNumber)
    getNumber = []
    for s in selEdges:
        evlist = mc.polyInfo(s,ev=True)
        checkNumber = ((evlist[0].split(':')[1]).split('\n')[0]).split(' ')
        for c in checkNumber:
            findNumber = ''.join([n for n in c.split('|')[-1] if n.isdigit()])
            if findNumber:
                getNumber.append(findNumber)
    dup = set([x for x in getNumber if getNumber.count(x) > 1])
    getHeadTail = list(set(getNumber) - dup)
    checkCircleState = 0
    if not getHeadTail: #close curve
        checkCircleState = 1
        getHeadTail.append(getNumber[0])
    vftOrder = []
    vftOrder.append(getHeadTail[0])
    count = 0
    while len(dup)> 0 and count < 1000:
        checkVtx = transformNode[0]+'.vtx['+ vftOrder[-1] + ']'
        velist = mc.polyInfo(checkVtx,ve=True)
        getNumber = []
        checkNumber = ((velist[0].split(':')[1]).split('\n')[0]).split(' ')
        for c in checkNumber:
            findNumber = ''.join([n for n in c.split('|')[-1] if n.isdigit()])
            if findNumber:
                getNumber.append(findNumber)
        findNextEdge = []
        for g in getNumber:
            if g in edgeNumberList:
                findNextEdge = g
        edgeNumberList.remove(findNextEdge)
        checkVtx = transformNode[0]+'.e['+ findNextEdge + ']'
        findVtx = mc.polyInfo(checkVtx,ev=True)
        getNumber = []
        checkNumber = ((findVtx[0].split(':')[1]).split('\n')[0]).split(' ')
        for c in checkNumber:
            findNumber = ''.join([n for n in c.split('|')[-1] if n.isdigit()])
            if findNumber:
                getNumber.append(findNumber)
        gotNextVtx = []
        for g in getNumber:
            if g in dup:
                gotNextVtx = g
        dup.remove(gotNextVtx)
        vftOrder.append(gotNextVtx)
        count +=  1
    if checkCircleState == 0:
        vftOrder.append(getHeadTail[1])
    else:#close curve remove connected vtx
        if vftOrder[0] == vftOrder[1]:
            vftOrder = vftOrder[1:]
        elif vftOrder[0] == vftOrder[-1]:
            vftOrder = vftOrder[0:-1]
    finalList = []
    for v in vftOrder:
        finalList.append(transformNode[0]+'.vtx['+ v + ']' )

    return checkCircleState, finalList


def checkFaceAngle(faceName):
    shapeNode = mc.listRelatives(faceName, fullPath=True , parent=True )
    transformNode = mc.listRelatives(shapeNode[0], fullPath=True , parent=True )
    obj_matrix = OpenMaya.MMatrix(mc.xform(transformNode, query=True, worldSpace=True, matrix=True))
    face_normals_text = mc.polyInfo(faceName, faceNormals=True)[0]
    face_normals = [float(digit) for digit in re.findall(r'-?\d*\.\d*', face_normals_text)]
    v = OpenMaya.MVector(face_normals) * obj_matrix
    upvector = OpenMaya.MVector (0,1,0)
    getHitNormal = v
    quat = OpenMaya.MQuaternion(upvector, getHitNormal)
    quatAsEuler = OpenMaya.MEulerRotation()
    quatAsEuler = quat.asEulerRotation()
    rx, ry, rz = math.degrees(quatAsEuler.x), math.degrees(quatAsEuler.y), math.degrees(quatAsEuler.z)
    return rx, ry, rz

def freeForm():
    if mc.window("freeFromUI", exists = True):
        mc.deleteUI("freeFromUI")
    freeFromUI = mc.window("freeFromUI",title = "freeForm 1.1", w=340)
    mc.frameLayout(labelVisible= False)
    mc.text(l ='')
    mc.rowColumnLayout(nc=4 ,cw=[(1,5),(2,300),(3,5),(4,20)])
    mc.text(l ='')
    mc.floatSliderGrp('tenstionVSlider', cw3=[50, 40, 180], label = 'Tenstion',  field= 1, max= 90, fmx = 180, min = -90,fmn = -180, v = 0 )
    mc.text(l ='')
    mc.button('tensionGlobalResetButton', l= 'X',  c= 'tensionGlobalReset()',bgc = (0.25,0.25,0.25))
    mc.setParent( '..' )
    mc.rowColumnLayout(nc=8 ,cw=[(1,5),(2,150),(3,5),(4,20),(5,5),(6,120),(7,5),(8,20)])
    mc.text(l ='')
    mc.floatSliderGrp('tenstionASlider', cw3=[50, 40, 90], label = ' A ',  field= 1, max=90, fmx = 180, min = -90,fmn = -180, v = 0)
    mc.text(l ='')
    mc.button('tensionLocalARestButton', l= 'X',  c= 'tensionLocalARest()',bgc = (0.25,0.25,0.25))
    mc.text(l ='')
    mc.floatSliderGrp('tenstionBSlider', cw3=[20, 40, 90], label = ' B ',  field= 1, max= 90, fmx = 180, min = -90,fmn = -180, v = 0 )
    mc.text(l ='')
    mc.button('tensionLocalBRestButton', l= 'X',  c= 'tensionLocalBRest()',bgc = (0.25,0.25,0.25))
    mc.setParent( '..' )
    mc.text(l ='------------------------------------------------------------------')
    mc.rowColumnLayout(nc=4 ,cw=[(1,5),(2,300),(3,5),(4,20)])
    mc.text(l ='')
    mc.floatSliderGrp('sharpVSlider', cw3=[50,40, 180], label = 'Sharp',  field= 1, max= 4, min = 0, fmx = 10 , v = 1)
    mc.text(l ='')
    mc.button('sharpGlobalResetButton', l= 'X',  c= 'sharpGlobalReset()' ,bgc = (0.25,0.25,0.25))
    mc.setParent( '..' )
    mc.rowColumnLayout(nc=8 ,cw=[(1,5),(2,150),(3,5),(4,20),(5,5),(6,120),(7,5),(8,20)])
    mc.text(l ='')
    mc.floatSliderGrp('sharpASlider', cw3=[50, 40, 90], label = ' A ', field= 1, max= 2, fmx = 10, min = 0, v = 0 )
    mc.text(l ='')
    mc.button('sharpLocalAResetButton', l= 'X',  c= 'sharpLocalAReset()' ,bgc = (0.25,0.25,0.25))
    mc.text(l ='')
    mc.floatSliderGrp('sharpBSlider', cw3=[20, 40, 90], label = ' B ', field= 1, max= 2, fmx = 10, min = 0, v = 0 )
    mc.text(l ='')
    mc.button('sharpLocalBResetButton', l= 'X',  c= 'sharpLocalBReset()' ,bgc = (0.25,0.25,0.25))
    mc.setParent( '..' )
    mc.text(l ='------------------------------------------------------------------')
    mc.rowColumnLayout(nc=4 ,cw=[(1,5),(2,300),(3,5),(4,20)])
    mc.text(l ='')
    mc.floatSliderGrp('fanVSlider', cw3=[50, 40, 90], label = ' Fan ',  field= 1, max= 10, min =-10, fmx = 50, fmn = -50, v = 0)
    mc.text(l ='')
    mc.button('fanRestButton', l= 'X',  c= 'fanRest()',bgc = (0.25,0.25,0.25))
    mc.text(l ='')
    mc.floatSliderGrp('driftVSlider', cw3=[50, 40, 90], label = ' Drift ',  field= 1, max= 10, min =-10, fmx = 50, fmn = -50, v = 0)
    mc.text(l ='')
    mc.button('driftRestButton', l= 'X',  c= 'driftRest()',bgc = (0.25,0.25,0.25))
    
    mc.setParent( '..' )

    mc.rowColumnLayout(nc=6,cw=[(1,90),(2,5),(3,140),(4,20),(5,5),(6,70)])
    mc.text(l ='Push Direction')
    mc.text(l ='')
    mc.radioButtonGrp('PushDirType', nrb=2, sl=1, labelArray2=['Normal', 'World  |'], cw = [(1,70),(2,50)],cc='pushTypeSwitch()')
    mc.text(l ='Axis')
    mc.text(l ='')
    #mc.radioButtonGrp('RotateAlginType', nrb=3, sl=2, labelArray3=['X', 'Y' ,'Z'], cw = [(1,70),(2,70)],cc='pushDirectionSwitch()',en=0)
    mc.radioButtonGrp('RotateAlginType', nrb=2, sl=2, labelArray2=['X', 'Y' ], cw = [(1,30),(2,30)],cc='pushDirectionSwitch()',en=0)

    mc.setParent( '..' )
    mc.separator( height=10, style='in' )
    mc.rowColumnLayout(nc=2,cw=[(1,10),(2,300)])
    mc.text(l ='')
    mc.intSliderGrp('bridgeDivisionSlider', cw3=[50, 40, 90], label = ' Division ',  field= 1, max= 20, min =1, v = 5,en = 0)

    mc.setParent( '..' )
    mc.rowColumnLayout(nc=10 ,cw=[(1,10),(2,60),(3,5),(4,60),(5,5),(6,60),(7,5),(8,60),(9,5),(10,60),(9,5)])
    mc.text(l ='')
    mc.button( l= 'Bridge',  c= 'buildBridge()')
    mc.text(l ='')
    mc.button( l= 'Blend',  c= 'freeFromRunNew()')
    mc.text(l ='')
    mc.button( l= 'Reset All',  bgc = (0.25,0.25,0.25), c= 'freeFormResetAll()')
    mc.text(l ='')
    mc.button( l= 'Remove', bgc= (0.5,0.3,0.3), c= 'killFreeFrom()')
    mc.text(l ='')
    mc.button( l= 'Done', bgc= (0.5,0.7,0.3),  c= 'freeFromDone()')
    mc.text(l ='')
    mc.setParent( '..' )
    mc.text(l ='')
    mc.showWindow(freeFromUI)
freeForm()
#face
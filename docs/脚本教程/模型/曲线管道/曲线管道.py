##--------------------------------------------------------------------------
## ScriptName : xWire 
##				dulpicate multi curves with some randomness in few click
##
## Author     : Joe Wu
## URL        : https://www.youtube.com/@Im3dJoe
## LastUpdate : 2023/08/22
##            : 
## Version    : 1.0  First version for public test
##
## Other Note : test in maya 2023.3 windows 
##
## Install    : copy and paste script into a python tab in maya script editor
##--------------------------------------------------------------------------


import random
import maya.cmds as mc
import re
import maya.mel as mel


def xCables():
    maya_version = mc.about(version=True)
    if mc.window('xWireUI', exists = True):
            mc.deleteUI('xWireUI')
    xWireUI = mc.window('xWireUI', title='xWire v1.0',w = 250, s = 1 ,mxb = False, mnb = False)
    mc.columnLayout(adj=1, w=350)
    mc.text(label="")
    mc.rowColumnLayout(numberOfColumns=5, columnWidth=[(1,25), (2, 60), (3, 100), (4, 71), (5, 71)])
    mc.text(label="")
    mc.text(label="Base Curve")
    mc.textField('xWireBaseCurve', text="test",en=0)
    mc.button(label="Pick", bgc=[0.2, 0.2, 0.2], height=23, width=62, command="xWirePick()")
    mc.button(label="Remove", bgc=[0.1, 0.1, 0.1], height=23, width=62, command="xWireKill()")
    mc.setParent( '..' )
    
    mc.text(label="")
    mc.intSliderGrp('xCableNo',label="Number", cw3=[70, 50, 0], dc="xWireCreate()",cc="xWireCreate()", value=4, field=True, minValue=0, maxValue=15, fieldMaxValue=30, fieldMinValue=0, fieldStep=1)
    mc.floatSliderGrp('xCableRandom', label="    Random", cw3=[70, 50, 0], dc="xWireCreate()",cc="xWireCreate()", field=True, value=1, minValue=0.1, maxValue=10, fieldMinValue=0.01, fieldMaxValue=500, precision=3)
    mc.text(label="")
    mc.rowColumnLayout(numberOfColumns=6, columnWidth=[(1, 50),(2, 40), (3, 50), (4, 60),(5, 60),(6, 40)])
    mc.text(l='')
    mc.text(l='Lock')
    mc.checkBox('xWireFront',label="Front", value= 1,cc="xWireCreate()")
    mc.checkBox('xWireEnd',label="End", value= 1,cc="xWireCreate()")
    mc.checkBox('xWireSweep',label="Sweep", value= 0,cc="xWireSweepUpdate()")
    mc.button('xWireSweepTab',label="Tab", bgc=[0.2, 0.2, 0.2], height=23, width=62, command="xWirePickSweep()")
    mc.text(label="")
    mc.showWindow(xWireUI)
    if int(maya_version) < 2022:
        mc.checkBox('xWireSweep',e =1 ,en= 0)
        mc.button('xWireSweepTab',e = 1 ,en= 0)
    
def xWirePickSweep():
    base_curve = mc.textField('xWireBaseCurve', query=True, text=True)
    if base_curve:
        sweepNode = (base_curve + '_sweepNode')
        if mc.objExists(sweepNode):
            CMD = 'showEditorExact "' + sweepNode + '";'
            mel.eval(CMD)

def xWireKill():
    base_curve = mc.textField('xWireBaseCurve', query=True, text=True)
    if base_curve:
        sweepNode = (base_curve + '_sweepNode')
        if mc.objExists(sweepNode):
            mc.delete(sweepNode)
        if mc.objExists(base_curve +"_Mesh"):
            mc.delete(base_curve + "_Mesh")
        if mc.objExists(base_curve + '_copy*'):
            mc.delete(base_curve + '_copy*')
        mc.textField('xWireBaseCurve', e=1, text=" ")
        
def xWirePick():
    ref_curve = mc.ls(selection=True,fl=1)
    if ref_curve:
        cableName = []
        for r in ref_curve:
            if '_copy' in r:
                check = r.split("_copy")[0]
                cableName.append(check)
            else:
                cableName.append(r)
        final = list(set(cableName))
        mc.textField('xWireBaseCurve', edit=True, text = str(final[0]))
        xWireCreate()


def xWireSweepUpdate():
    checkSweep = mc.checkBox('xWireSweep',q=1, value= 1)
    base_curve = mc.textField('xWireBaseCurve', query=True, text=True)
    if base_curve:
        shape_nodes = mc.listRelatives(base_curve, shapes=True, fullPath=True)
        sweepNode = (base_curve + '_sweepNode')
        if checkSweep == 1:
            if mc.objExists(sweepNode) == 0:
                mc.sweepMeshFromCurve(base_curve,oneNodePerCurve=0)
                newNode = mc.ls(sl=1)
                mc.rename(sweepNode)
                sweepMesh = mc.listConnections(sweepNode, source=0, destination=1)
                mc.rename(sweepMesh, base_curve +"_Mesh")
                node_name = mc.createNode("polyUnite")
                mc.rename(node_name,(base_curve + '_polyUnite'))  
                mc.connectAttr((base_curve + "_polyUnite.output"), (base_curve +"_Mesh.inMesh"), force=True)
                for i in range(0,100):
                    mc.connectAttr(sweepNode + '.outMeshArray[' + str(i) + ']', base_curve + "_polyUnite.inputPoly[" + str(i) + "]", force=True)
                    mc.connectAttr(shape_nodes[0]+'.worldMatrix[0]', base_curve + "_polyUnite.inputMat[" + str(i) + "]", force=True)
                mc.setAttr(sweepNode+ ".interpolationOptimize", 1)
                mc.setAttr(sweepNode+ ".interpolationPrecision", 60)
            cableList = mc.ls((base_curve+'_copy*'),fl=1,shapes=1)
            for index, c in enumerate(cableList):
                mc.connectAttr(c + '.worldSpace[0]', sweepNode + '.inCurveArray[' + str(index+1) + ']', force=True)
        else:
            if mc.objExists(sweepNode):
                mc.delete(sweepNode)
            if mc.objExists(base_curve +"_Mesh"):
                mc.delete(base_curve +"_Mesh")

def xWireCreate():
    base_curve = mc.textField('xWireBaseCurve', query=True, text=True)
    checkFront = mc.checkBox('xWireFront',q=1, value= 1)
    checkEnd = mc.checkBox('xWireEnd',q=1, value= 1)
    checkSweep = mc.checkBox('xWireSweep',q=1, value= 1)
    if base_curve:
        number_cable = mc.intSliderGrp('xCableNo', query=True, value=True)
        r_pos = mc.floatSliderGrp('xCableRandom', query=True, value=True)
        name = f"{base_curve}_copy"
        
        for n in range(number_cable):
            if mc.objExists(name + 'str(n+1)') == 0:
                duplicate_curve = mc.duplicate(base_curve ,rr=1)
                new_name = f"{base_curve}_copy{n+1}"
                mc.rename(duplicate_curve, new_name)
        
        cableList = mc.ls((name+'*'),fl=1)
        cables_above_check = []
        
        for cable in cableList:
            match = re.search(r'_copy(\d+)$', cable)
            if match:
                cable_number = int(match.group(1))
                if cable_number > number_cable:
                    cables_above_check.append(cable)
                    
        if cables_above_check:
            mc.delete(cables_above_check)
    
    
        old_cv = []
        cvList = mc.ls( (base_curve + ".cv[*]") ,fl=1)
        
        for c in cvList :
            cp = mc.pointPosition(c, world=True)
            old_cv.append(cp)
        
        rx = 0
        ry = 0
        rz = 0
        new_cv_x = 0
        new_cv_y = 0
        new_cv_z = 0
                
        for n in range(number_cable):
            curveName = base_curve + '_copy' + str(n+1)

            for d in range(len(old_cv)):
                goRandom = 1
                getPos = old_cv[d]
                if d == 0:
                    if checkFront == 1:
                        goRandom = 0
                elif d == (len(old_cv)-1):
                    if checkEnd == 1:
                        goRandom = 0
                if goRandom == 1:
                    rx = random.uniform(r_pos*-1, r_pos)
                    ry = random.uniform(r_pos*-1, r_pos)
                    rz = random.uniform(r_pos*-1, r_pos)
                    new_cv_x = getPos[0] + rx
                    new_cv_y = getPos[1] + ry
                    new_cv_z = getPos[2] + rz
                else:
                    new_cv_x = getPos[0] + (rx*0.1)
                    new_cv_y = getPos[1] + (ry*0.1)
                    new_cv_z = getPos[2] + (rz*0.1)
                moveCv = (curveName + '.cv[' + str(d) +']')
                mc.move(new_cv_x, new_cv_y, new_cv_z, moveCv, worldSpace=True, absolute=True)
        xWireSweepUpdate()

xCables()
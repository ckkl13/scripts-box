import maya.cmds as mc
import maya.cmds as mc
import os
#from rerack_tools import edit_ref
import maya.OpenMayaUI as omui
import maya.OpenMaya as om




def camSwitch():
    if mc.window('camSwitchUI', exists=True):
        mc.deleteUI('camSwitchUI')
    camSwitchUI = mc.window('camSwitchUI', title='Camera Switcher Lite v0.4', w=250, s=1, mxb=False, mnb=False)
    mc.columnLayout(adjustableColumn=True)
    mc.text(l='')  
    mc.rowColumnLayout(nc=6, columnWidth=[(1,5),(2,100),(3,10),(4,60),(5,5),(6,60),(7,5),(8,60)])  
    mc.text(l='')
    mc.text(l='Camera:')  
    mc.text(l='')  
    mc.button(label= '+', command='dulpiCam()')
    mc.text(l='')
    mc.button(label= 'refresh', command='updateSwitchCamList()')
    mc.setParent( '..' ) 
    mc.text(l='',h=2) 
    mc.rowColumnLayout(nc=6, columnWidth=[(1,5),(2,100),(3,10),(4,60),(5,5),(6,60),(7,5),(8,60)])  
    mc.text(l='')
    mc.text(l='')
    mc.text(l='')
    mc.button(label= 'Follow',bgc = [0.2,0.3,0.2], command='followCam()')
    mc.text(l='')
    mc.button(label= 'Break' ,bgc = [0.3,0.2,0.2], command='followCamBreak()')
    mc.setParent( '..' )  
    mc.text(l='')  
    mc.columnLayout(adj=1)
    mc.scrollLayout('camSwitchLiscroll', h=300)
    mc.rowColumnLayout('camSwitchListColumn')
    mc.setParent( '..' )   
    mc.setParent( '..' )  
    mc.showWindow(camSwitchUI)
    updateSwitchCamList()

def kill_camera(camera_name):
    if mc.objExists(camera_name): 
        mc.delete(camera_name)
    updateSwitchCamList()

def switch_camera(camera_name):
    if mc.objExists(camera_name): 
        mc.modelPanel("modelPanel4", e=True, camera=camera_name)
        
def updateSwitchCamList():
    checkRowColumnLayout = mc.rowColumnLayout('camSwitchListColumn', q=True, ex=True)
    if checkRowColumnLayout:
        mc.deleteUI('camSwitchListColumn')
        mc.setParent('camSwitchLiscroll')
        mc.rowColumnLayout('camSwitchListColumn')
        cameras = mc.ls(cameras=True,fl=1)
        cameraList = sorted(cameras)
        topList = ['perspShape', 'topShape','sideShape','frontShape']
        for t in topList:
            if t in cameraList:
                render_cam_idx = cameraList.index(t)
                cameraList.pop(render_cam_idx)
                cameraList.insert(0, t) 

        noToKill = ['persp', 'top', 'front','side']
        for camName in cameraList:
            transform_node = mc.listRelatives(camName, parent=True)
            button_label = transform_node[0]
            cmd = 'switch_camera("' + str(button_label) + '")'
            
            newRowColumnName = button_label + '_dataColumn'
            checkRowColumnName = mc.rowColumnLayout(newRowColumnName, nc=4, columnWidth=[(1,30),(2,170),(3,10),(4,20)])
            mc.text(l='')  
           
            if 'renderCam01camera01' in button_label:
                mc.button((button_label + '_show'), label=button_label, command=cmd,bgc=[0.3,0.4,0.3])
            else:
                mc.button((button_label + '_show'),label=button_label, command=cmd)
            mc.text(l='')  
            
            if button_label not in noToKill:
                transform_node = mc.listRelatives(camName, parent=True,f=1)
                cmdX = 'kill_camera("' + str(transform_node[0]) + '")'
                mc.button((button_label + '_kill'),label='x', command=cmdX , bgc = [0.25,0.25,0.25])
            else:
                mc.text(l='')  
            mc.setParent('..')
    

def dulpiCam():
    view = omui.M3dView.active3dView()
    cam = om.MDagPath()
    view.getCamera(cam)
    camPath = cam.fullPathName()
    cameraTrans = mc.listRelatives(camPath,type='transform',p=True)
    newCam = mc.duplicate(cameraTrans[0], rr=1,smartTransform=1,f=1)
    
    mc.modelPanel("modelPanel4", e=True, camera=newCam[0])
    try:
        attributesList = ['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ']
        for attr in attributesList:
            mc.setAttr(newCam[0] + "." + attr, l = False)
        mc.parent(newCam[0],w=1)
        checkCurrent = mc.ls(sl=1,fl=1)
        if '_Follow' in checkCurrent[0]:
            mc.rename(checkCurrent[0],(checkCurrent[0].replace('_Follow', '')))
    except:
        pass
    inMessage = 'Camera Dulpicated'
    mc.optionVar(iv=("inViewMessageEnable", 1))
    mc.inViewMessage( amg='In-view message <hl>'+ inMessage  + '</hl>.', pos='midCenter', fade=True )
    mc.optionVar(iv=("inViewMessageEnable", 0))
    updateSwitchCamList()
    return newCam[0]
    

def followCamBreak():
    view = omui.M3dView.active3dView()
    cam = om.MDagPath()
    view.getCamera(cam)
    camPath = cam.fullPathName()
    cameraTrans = mc.listRelatives(camPath,type='transform',p=True)
    if '_Follow' in cameraTrans[0] :   
        mc.parent(cameraTrans[0],w=1)
        if mc.objExists(cameraTrans[0].replace('_Follow', '_ConsNode')):
            mc.delete(cameraTrans[0].replace('_Follow', '_ConsNode'))
        mc.rename(cameraTrans[0],(cameraTrans[0].replace('_Follow', '')))
        updateSwitchCamList()
        inMessage = 'Follow Off'
        mc.optionVar(iv=("inViewMessageEnable", 1))
        mc.inViewMessage( amg='In-view message <hl>'+ inMessage  + '</hl>.', pos='midCenter', fade=True )
        mc.optionVar(iv=("inViewMessageEnable", 0))


def followCam():
    currentSel = mc.ls(sl=1,fl=1)
    if len(currentSel) == 1:
        newCan = dulpiCam()
        mc.rename(newCan,(newCan + '_Follow'))
        empty_group = mc.group(empty=True, name=(newCan + '_ConsNode'))
        mc.matchTransform(empty_group, (newCan + '_Follow'),pos=1)
        mc.pointConstraint(currentSel[0],empty_group ,mo=1, weight=1.0)
        mc.parent((newCan + '_Follow'),(newCan + '_ConsNode'))
        updateSwitchCamList()
        inMessage = 'Follow On'
        mc.optionVar(iv=("inViewMessageEnable", 1))
        mc.inViewMessage( amg='In-view message <hl>'+ inMessage  + '</hl>.', pos='midCenter', fade=True )
        mc.optionVar(iv=("inViewMessageEnable", 0))
    else:
        inMessage = 'select ONE object to follow~'
        mc.optionVar(iv=("inViewMessageEnable", 1))
        mc.inViewMessage( amg='In-view message <hl>'+ inMessage  + '</hl>.', pos='midCenter', fade=True )
        mc.optionVar(iv=("inViewMessageEnable", 0))
       
def updateOffsetFrame():
    newV = mc.intSliderGrp('editRefOffsetFrame', q=1, value=1)
    if mc.objExists("editRefImgPlaneShape2"):
        mc.setAttr("editRefImgPlaneShape2.frameOffset", newV)

def updateBlend():
    if mc.objExists("editRefImgPlaneShape2"):
        newV = mc.floatSliderGrp('blendCamImage', q=1, value=1)
        newOP = mc.floatSliderGrp('allOP', q=1, value=1)
        mc.setAttr("editRefImgPlaneShape2.alphaGain", ((1 - newV)*newOP) )
    if mc.objExists("renderCam01camera01"):
        mc.setAttr("renderCam01camera01:camera_frustumShape.imagePlaneArray[0].imagePlaneOpacity", (newV*newOP))

def setSwitchCam():
    if mc.objExists("renderCam01camera01"):
        add_edit_ref()  
        editRefIP = mc.listRelatives('editRefCamShape', ad=True)[0]
        mc.setAttr((editRefIP + ".depth"),5)
        mc.setAttr("editRefCamShape.nearClipPlane",0.1)
        mc.setAttr("editRefCamShape.farClipPlane",1000000)
        mc.setAttr("renderCam01camera01:camera_frustumShape.imagePlaneArray[0].imagePlaneMode",1)
        mc.setAttr("renderCam01camera01:camera_frustumShape.imagePlaneArray[0].imagePlaneVisibility",2)
        mc.setAttr("renderCam01camera01:camera_frustumShape.imagePlaneArray[0].imageDist",5)
        mc.setAttr("renderCam01camera01:camera.nearClipPlane",0.1)
        mc.setAttr("renderCam01camera01:camera.farClipPlane",1000000)
        mc.floatSliderGrp('allOP',e=1, en = 1)    
        mc.floatSliderGrp('blendCamImage',e=1, en = 1)    
        mc.intSliderGrp('editRefOffsetFrame',e=1, en = 1)
    

def add_edit_ref(*args):
    if not mc.objExists("editRefCam"):
        if mc.objExists("renderCam"):
            camera_list = mc.listRelatives("renderCam", ad=True, type="camera", pa=True)
            camera_shape = None
            show = os.getenv("SHOW")
            shot = os.getenv("SHOT")
            file_path = edit_ref.get_edit_ref_path(show, shot)
            edit_ref.create_edit_ref_camera(file_path)
            if camera_list:
                for each in camera_list:
                    if each.split(":")[-1] == "cameraShape":
                        camera_shape = each
                if camera_shape:
                    mc.connectAttr(camera_shape + ".horizontalFilmAperture", "editRefCam.horizontalFilmAperture")
                    mc.connectAttr(camera_shape + ".verticalFilmAperture", "editRefCam.verticalFilmAperture")
                    mc.connectAttr(camera_shape + ".fl", "editRefCam.fl")
                    mc.connectAttr(camera_shape + ".filmTranslateV", "editRefCam.filmTranslateV")
                    mc.connectAttr(camera_shape + ".filmTranslateH", "editRefCam.filmTranslateH")
                    parent_node = mc.listRelatives(camera_shape, p=True, pa=True)[0]
                    mc.parentConstraint(parent_node, "editRefCam", mo=False)
                    ip = mc.listConnections("editRefCamShape", type="imagePlane") or []
                    if ip:
                        image_name = ip[0].split('>')[1]
                        x_val = mc.getAttr(camera_shape + ".horizontalFilmAperture")
                        y_val = mc.getAttr(camera_shape + ".verticalFilmAperture")
                        mc.setAttr(image_name + ".sizeX", x_val)
                        mc.setAttr(image_name + ".sizeY", y_val)
                        mc.setAttr(image_name + ".alphaGain", 0.5)
                        mc.setAttr(image_name + ".depth", 15)
                        mc.setAttr(image_name + ".fit", 2)
                        if len(str(file_path).split(".")[1]) == 12:
                            file_path_new = str(file_path).split(".")[0] + "." + str(file_path).split(".")[1][4:-4] + "." + str(file_path).split(".")[2]
                            mc.setAttr(image_name + ".imageName", file_path_new, type="string")
                                                      
camSwitch()                                                                                                                                
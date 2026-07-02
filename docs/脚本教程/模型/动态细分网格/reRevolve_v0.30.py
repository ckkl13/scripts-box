##--------------------------------------------------------------------------
## ScriptName : reRevolve
## Author     : Joe Wu
## URL        : https://www.youtube.com/@Im3dJoe
## LastUpdate : 2022/01
##            : add more subdivision to cylinder when transform froze or history deleted
## Version    : 0.01  prototype
##              0.12 imporve detect more shape
##              0.13 test with more complex shape and debug
##              0.26 added torus shape, still feel not so usful , pause development
##              0.27 fixed function name
##              0.28 fixed nurbs to poly setting bug
##              0.29 fixed HUD bug
##              0.30 fixed error in Maya 2023
##
## Other Note : test in maya 2020.2 windows
##
## Install    : copy and paste script into a python tab in maya script editor
##--------------------------------------------------------------------------


import maya.cmds as mc
import maya.mel as mel
import math
import re
def subDCylinderCreate():
    global storeSubDStep
    global revPNode
    global reSubDMehsNode
    global revPNGon
    global revPQuad
    global revPTris
    global torusOnly
    global findCone
    global newTri
    global openHolePivot
    global noBaseCone
    global diamondCone
    openHolePivot =[]
    checkTipNo = []
    revPQuad = []
    revPNode = []
    verList = []
    holeEdge = []
    newTri = []
    profileEdge = []
    findCone = 0
    checkTipNo = 0
    goRebuild = 0
    noBaseCone = 0
    diamondCone = 0
    torusOnly = 0
    if mc.headsUpDisplay('HUDSubDStep',ex=1):
        mc.headsUpDisplay('HUDSubDStep', rem=1)
    cleanList = ('ppA','ppB','profileCurve','coneTip','endQuadCap')
    for c in cleanList:
        if mc.objExists(c):
            mc.delete(c)
    selGeo =  mc.filterExpand( sm=12)
    if selGeo:
        mc.ConvertSelectionToFaces()
        #type one cap is Ngon
        mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 3,where =0)
        revPNGon = mc.ls(sl=1,fl=1)
        mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 1,where =0)
        revPTris = mc.ls(sl=1,fl=1)
        mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 2,where =0)
        revPQuads = mc.ls(sl=1,fl=1)
        mc.polySelectConstraint(mode =3, type = 0x8000 ,where =1)
        holeEdge = mc.ls(sl=1,fl=1)
        mc.polySelectConstraint(disable=1)
        if len(revPQuads) >0 and len(revPNGon) == 0 and len(revPTris) == 0 and len(holeEdge) ==0:
                torusOnly = 1
        else:
            if revPNGon or revPTris:
                if len(revPNGon) > 0:
                    if len(revPNGon)== 1:
                        if len(revPTris)==0:#found hole
                            if len(holeEdge)>0:
                                mc.select(holeEdge)
                                mc.setToolTo('Move')
                                pointA = mc.manipMoveContext("Move",q=1, p=1)
                                openHolePivot = pointA
                if len(revPTris) > 0:
                    if len(revPNGon)==0:#found hole
                        mc.select(revPTris)
                        mc.ConvertSelectionToVertexPerimeter()
                        getTriExt=mc.ls(sl=1,fl=1)
                        mc.select(revPTris)
                        mc.ConvertSelectionToVertices()
                        mc.select(getTriExt,d=1)
                        mc.setToolTo('Move')
                        pointA = mc.manipMoveContext("Move",q=1, p=1)
                        openHolePivot = pointA
                mc.delete(revPNGon)
            else:
                openHolePivot =[]
                mc.select(selGeo)
                findCapQuad()
                revPQuad = mc.ls(sl=1,fl=1)
                if revPQuad:
                    if len(revPQuad)==1:
                        mc.select(holeEdge)
                        mc.setToolTo('Move')
                        pointA = mc.manipMoveContext("Move",q=1, p=1)
                        openHolePivot = pointA
                    elif len(revPQuad)==2:
                        openHolePivot =[]
                    mc.delete(revPQuad)
        reSubDMehsNode = selGeo[0]
        mc.select(selGeo)
        goRebuild = 1

    if goRebuild == 1:
        intiSubDNo = 0
        if torusOnly == 1:
            totalEdgeNo= mc.polyEvaluate(selGeo[0], e=True )
            heckNo = int(totalEdgeNo)/2
            testEdge = (selGeo[0]+'.e['+ str(heckNo) + ']')
            mc.select(testEdge)
            mc.SelectEdgeLoopSp()
            firstSel = mc.ls(sl=1,fl=1)
            cmd='polySelectEdgesEveryN "edgeRing" 1;'
            mel.eval(cmd)
            growAll = mc.ls(sl=1,fl=1)
            newFace = mc.polyListComponentConversion(firstSel,fe=1, tf=1)
            newEdges =mc.polyListComponentConversion(newFace,ff=1, te=1)
            newEdges = mc.ls(newEdges,flatten=1)
            commonItems = set(growAll) - (set(growAll) - set(newEdges))
            diffItems = list(set(newEdges) - set(commonItems))
            mc.select(commonItems)
            sortGrp =  getEdgeRingGroup()
            listCheck = []
            checkCurveList=[]
            avgDiff=[]
            profileEdge = []
            goodFound = []
            intiSubDNo = 0
            for e in sortGrp:
                mc.select(e)
                checkCurve= mc.polyToCurve(form=0, degree=1,ch=1)
                curveLength = mc.arclen(checkCurve[0])
                listCheck.append(curveLength)
                checkCurveList.append(checkCurve[0])
            mc.delete(checkCurveList)
            avgDiff =(listCheck[0]+listCheck[1]+listCheck[2])/3-listCheck[0]
            avgDiff = math.sqrt(avgDiff*avgDiff)
            if avgDiff < 0.001:
                profileEdge = testEdge
                goodFound = diffItems[0]
            else:
                goodFound = testEdge
                profileEdge = diffItems[0]

            mc.select(goodFound)
            mc.SelectEdgeLoopSp()
            firstSel = mc.ls(sl=1,fl=1)
            intiSubDNo = len(firstSel)
            mc.setToolTo('Move')
            pointA = mc.manipMoveContext("Move",q=1, p=1)
            mc.spaceLocator(p=(pointA[0],pointA[1],pointA[2]),n='ppA')
            mc.CenterPivot()

            mc.select(firstSel)
            cmd='polySelectEdgesEveryN "edgeRing" 1;'
            mel.eval(cmd)
            growAll = mc.ls(sl=1,fl=1)
            newFace = mc.polyListComponentConversion(firstSel,fe=1, tf=1)
            newEdges =mc.polyListComponentConversion(newFace,ff=1, te=1)
            newEdges = mc.ls(newEdges,flatten=1)
            commonItems = set(growAll) - (set(growAll) - set(newEdges))
            mc.select(commonItems)
            mc.select(firstSel,d=1)
            secSel = mc.ls(sl=1,fl=1)
            mc.select(secSel[0])
            mc.SelectEdgeLoopSp()
            mc.setToolTo('Move')
            pointB = mc.manipMoveContext("Move",q=1, p=1)
            mc.spaceLocator(p=(pointB[0],pointB[1],pointB[2]),n='ppB')
            mc.CenterPivot()

        if len(revPTris) > 0:
            mc.select(selGeo)
            mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 1,where =0)
            revPTris = mc.ls(sl=1,fl=1)
            mc.ConvertSelectionToContainedEdges()
            mc.ConvertSelectionToEdgePerimeter()
            mc.ConvertSelectionToVertices()
            storeUnwant = mc.ls(sl=1,fl=1)
            mc.select(revPTris)
            mc.ConvertSelectionToVertices()
            mc.select(storeUnwant,d=1)
            checkTipNo = mc.ls(sl=1,fl=1)
            if len(checkTipNo) == 1:
                mc.select(checkTipNo[0])
                mc.setToolTo('Move')
                pointA = mc.manipMoveContext("Move",q=1, p=1)
                mc.spaceLocator(p=(pointA[0],pointA[1],pointA[2]),n='ppA')
                mc.CenterPivot()
                mc.select(reSubDMehsNode)
                mc.polySelectConstraint(mode =3, type = 0x8000 ,where =1)
                holeEdge = mc.ls(sl=1,fl=1)
                mc.polySelectConstraint(disable=1)
                intiSubDNo =len(holeEdge)
                if len(holeEdge) > 0:
                    if len(revPNGon) == 1:
                        noBaseCone = 0
                    else:
                        noBaseCone = 1
                if noBaseCone == 0:
                    mc.FillHole()
                mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 3,where =0)
                getN = mc.ls(sl=1,fl=1)
                if len(getN)>0:
                    mc.setToolTo('Move')
                    pointB = mc.manipMoveContext("Move",q=1, p=1)
                    mc.spaceLocator(p=(pointB[0],pointB[1],pointB[2]),n='ppB')
                    mc.CenterPivot()
                    mc.delete(getN[0])
                else:
                    if noBaseCone == 0:
                        mc.select(selGeo[0])
                        mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 1,where =0)
                        mc.select(revPTris,d=1)
                        newTri= mc.ls(sl=1,fl=1)
                        mc.ConvertSelectionToVertexPerimeter()
                        storeUnwant = mc.ls(sl=1,fl=1)
                        mc.select(newTri)
                        mc.ConvertSelectionToVertices()
                        mc.select(storeUnwant,d=1)
                        checkTipOther = mc.ls(sl=1,fl=1)
                        if len(checkTipOther)>0:
                            mc.setToolTo('Move')
                            pointB = mc.manipMoveContext("Move",q=1, p=1)
                            mc.spaceLocator(p=(pointB[0],pointB[1],pointB[2]),n='ppB')
                            mc.CenterPivot()
                            #mc.delete(newTri)
                        #check if no division to the cone, keep triangle
                        mc.select(checkTipNo[0])
                        mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 2,where =0)
                        getQuad = mc.ls(sl=1,fl=1)
                        if len(getQuad) > 0:
                            if findCone == 0:
                                mc.select(checkTipNo[0])
                                mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 1,where =0)
                                mc.delete()
                        else:
                            noBaseCone =1
                            findCone = 1
                    else:
                        mc.select(selGeo[0])
                        mc.polySelectConstraint(mode =3, type = 0x8000 ,where =1)
                        mc.setToolTo('Move')
                        pointB = mc.manipMoveContext("Move",q=1, p=1)
                        mc.spaceLocator(p=(pointB[0],pointB[1],pointB[2]),n='ppB')
                        mc.CenterPivot()

            elif len(checkTipNo) == 2:
                mc.select(checkTipNo[0])
                mc.ConvertSelectionToEdges()
                getEdge = mc.ls(sl=1,fl=1)
                intiSubDNo =len(getEdge)
                mc.select(checkTipNo[0])
                mc.setToolTo('Move')
                pointA = mc.manipMoveContext("Move",q=1, p=1)
                mc.spaceLocator(p=(pointA[0],pointA[1],pointA[2]),n='ppA')
                mc.CenterPivot()
                mc.select(checkTipNo[1])
                mc.setToolTo('Move')
                pointB = mc.manipMoveContext("Move",q=1, p=1)
                mc.spaceLocator(p=(pointB[0],pointB[1],pointB[2]),n='ppB')
                mc.CenterPivot()
            elif len(checkTipNo) > 2:
                if len(revPNGon) == 0:
                    mc.select(checkTipNo[0])
                    mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 2,where =0)
                    getQuad = mc.ls(sl=1,fl=1)
                    mc.polySelectConstraint(mode =3, type = 0x8000 ,where =1)
                    holeEdge = mc.ls(sl=1,fl=1)
                    mc.polySelectConstraint(disable=1)
                    if len(getQuad) == 0:
                        mc.select(selGeo[0])
                        mc.ConvertEdge()
                        guessRingEdge = mc.ls(sl=1,fl=1)
                        count = 0
                        findmid = 0
                        while len(guessRingEdge)> 0 and count < 50 and findmid == 0:
                            mc.select(guessRingEdge[0])
                            mc.SelectEdgeLoopSp()
                            checkSide = mc.ls(sl=1,fl=1)
                            if len(checkSide) == 2:
                                mc.select(checkSide[0])
                                mc.ConvertSelectionToVertices()
                                findMidCVA = mc.ls(sl=1,fl=1)
                                mc.select(checkSide[1])
                                mc.ConvertSelectionToVertices()
                                findMidCVB = mc.ls(sl=1,fl=1)
                                findMid = set(findMidCVA) - (set(findMidCVA) - set(findMidCVB))
                                mc.select(findMidCVA,findMidCVB)
                                mc.select(findMid,d=1)
                                checkTipNo = mc.ls(sl=1,fl=1)
                                findmid =1
                            else:
                                getRingEdge=mc.ls(sl=1,fl=1)
                                removeFromList = list(set(guessRingEdge)-set(getRingEdge))
                                guessRingEdge = removeFromList
                            count +=  1
                        # same as len(checkTipNo) ==2 now
                        if len(holeEdge)>0:
                            mc.select(holeEdge)
                            mc.ConvertSelectionToVertices()
                            edgeVer=mc.ls(sl=1,fl=1)
                            mc.select(checkTipNo)
                            mc.select(edgeVer,d=1)
                            mc.setToolTo('Move')
                            pointA = mc.manipMoveContext("Move",q=1, p=1)
                            mc.spaceLocator(p=(pointA[0],pointA[1],pointA[2]),n='ppA')
                            mc.CenterPivot()
                            mc.select(edgeVer)
                            mc.setToolTo('Move')
                            pointB = mc.manipMoveContext("Move",q=1, p=1)
                            mc.spaceLocator(p=(pointB[0],pointB[1],pointB[2]),n='ppB')
                            mc.CenterPivot()
                            intiSubDNo =len(edgeVer)
                            diamondCone = 0
                        else:
                            mc.select(checkTipNo[0])
                            mc.ConvertSelectionToEdges()
                            getEdge = mc.ls(sl=1,fl=1)
                            intiSubDNo =len(getEdge)
                            mc.select(checkTipNo[0])
                            mc.setToolTo('Move')
                            pointA = mc.manipMoveContext("Move",q=1, p=1)
                            mc.spaceLocator(p=(pointA[0],pointA[1],pointA[2]),n='ppA')
                            mc.CenterPivot()
                            mc.select(checkTipNo[1])
                            mc.setToolTo('Move')
                            pointB = mc.manipMoveContext("Move",q=1, p=1)
                            mc.spaceLocator(p=(pointB[0],pointB[1],pointB[2]),n='ppB')
                            mc.CenterPivot()
                            diamondCone = 1
        else:
            checkTipNo = []
            mc.polySelectConstraint(mode =3, type = 0x8000 ,where =1)
            holeEdge = mc.ls(sl=1,fl=1)
            mc.polySelectConstraint(disable=1)
            if len(holeEdge)>0:
                mc.select(holeEdge[0])
                mc.SelectEdgeLoopSp()
                loopA = mc.ls(sl=1,fl=1)
                intiSubDNo =len(loopA)
                mc.setToolTo('Move')
                pointA = mc.manipMoveContext("Move",q=1, p=1)
                mc.spaceLocator(p=(pointA[0],pointA[1],pointA[2]),n='ppA')
                mc.CenterPivot()
                if findCone == 1:
                    mc.select('coneTip')
                    mc.setToolTo('Move')
                    pointB = mc.manipMoveContext("Move",q=1, p=1)
                    mc.spaceLocator(p=(pointB[0],pointB[1],pointB[2]),n='ppB')
                    mc.CenterPivot()
                else:
                    mc.select(holeEdge)
                    mc.select(loopA,d=1)
                    pointB = mc.manipMoveContext("Move",q=1, p=1)
                    mc.spaceLocator(p=(pointB[0],pointB[1],pointB[2]),n='ppB')
                    mc.CenterPivot()
        mc.aimConstraint('ppB','ppA',offset=[0,0,0], weight=1, aimVector=[0,1,0], worldUpVector=[0,1,0], worldUpType='vector')
        mc.parent(selGeo[0],'ppA')
        mc.makeIdentity(selGeo[0],apply=1, t=1, r=1, s=0, n=0)
        mc.parent(w=1)
        mc.makeIdentity(selGeo[0],apply=1, t=1, r=0, s=0, n=0)
        ppX = mc.getAttr((selGeo[0]+'.rotateX'))
        ppY = mc.getAttr((selGeo[0]+'.rotateY'))
        ppZ = mc.getAttr((selGeo[0]+'.rotateZ'))
        mc.setAttr((selGeo[0]+'.rotateX'),0)
        mc.setAttr((selGeo[0]+'.rotateY'),0)
        mc.setAttr((selGeo[0]+'.rotateZ'),0)
        getPos = mc.xform(selGeo[0],q=1, ws=1, pivots=1)
        mc.setAttr((selGeo[0]+'.translateX'),(-1*getPos[0]))
        mc.setAttr((selGeo[0]+'.translateY'),(-1*getPos[1]))
        mc.setAttr((selGeo[0]+'.translateZ'),(-1*getPos[2]))
        #get profile
        if torusOnly == 0:
            if len(checkTipNo)==0:
                mc.select(holeEdge[0])
                mc.GrowPolygonSelectionRegion()
                mc.select(holeEdge,d=1)
                dvEdge = mc.ls(sl=1,fl=1)
                mc.select(dvEdge[0])
                mc.SelectEdgeLoopSp()

            elif len(checkTipNo) == 1:
                mc.select(checkTipNo)
                mc.ConvertSelectionToEdges()
                getEdge = mc.ls(sl=1,fl=1)
                mc.select(getEdge[0])
                mc.SelectEdgeLoopSp()
            elif len(checkTipNo) == 2:
                mc.select(checkTipNo)
                firstVertIndex = checkTipNo[0].split('.')[-1].split('[')[-1].split(']')[0]
                secondVertIndex = checkTipNo[1].split('.')[-1].split('[')[-1].split(']')[0]
                shortEdges = mc.polySelect(asSelectString=1, shortestEdgePath=(int(firstVertIndex),int(secondVertIndex)))
                mc.select(shortEdges)
        else:
            mc.select(profileEdge)
            mc.SelectEdgeLoopSp()
        #if len(checkTipNo>0:
            #add tip point
        #mc.polyToCurve(form=0, degree=1,ch=1,conformToSmoothMeshPreview=0)
        mc.polyToCurve(form=0, degree=1,ch=1)
        mc.rename('profileCurve')
        #listCurveP = mc.ls('profileCurve.cv[*]',fl=1)
        #storeYPA = 0
        #storeYPB = 0
        #mc.setToolTo('Move')
        #if findCone == 1:
        #    mc.select(listCurveP[0])
        #    checkPA = mc.manipMoveContext("Move",q=1, p=1)
        #    storeYPA = checkPA[1]
        #    if checkPA[0] <0.01 and  checkPA[0] > -0.01:
        #        mc.move(0,checkPA[1],checkPA[2],listCurveP[0], absolute = 1, ws = 1 )
        #    if checkPA[2] <0.01 and  checkPA[2] > -0.01:
        #        mc.move(checkPA[0],checkPA[1],0,listCurveP[0], absolute = 1, ws = 1 )
        #    mc.select(listCurveP[-1])
        #    checkPB = mc.manipMoveContext("Move",q=1, p=1)
        #    storeYPB = checkPB[1]
        #    if checkPB[0] <0.01 and  checkPB[0] > -0.01:
        #        mc.move(0,checkPB[1],checkPB[2],listCurveP[-1], absolute = 1, ws = 1 )
        #    if checkPB[2] <0.01 and  checkPB[2] > -0.01:
        #        mc.move(checkPB[0],checkPB[1],0,listCurveP[-1], absolute = 1, ws = 1 )
        #    if  storeYPA <  storeYPB:
        #        mc.reverseCurve('profileCurve',ch=0, rpo=1)
        #else:
        #    mc.select(listCurveP[0])
        #    checkPA = mc.manipMoveContext("Move",q=1, p=1)
        #    storeYPA = checkPA[1]
        #    mc.select(listCurveP[1])
        #    checkPB = mc.manipMoveContext("Move",q=1, p=1)
        #    storeYPB = checkPB[1]
        #    if  storeYPA >  storeYPB:
        #        mc.reverseCurve('profileCurve',ch=1, rpo=1)

        mc.setAttr(('profileCurve.visibility'),0)
        mc.nurbsToPolygonsPref(polyType=1,format=2,uType=3,uNumber=1,vType=3,vNumber=1)
        revNode = mc.revolve('profileCurve',ch=1, po=1, rn=0, ssw=0, esw=360, ut=0, tol=0.01, degree=3, s=intiSubDNo, ulp=1, ax=(0,1,0))
        revPNode = revNode[-1]
        dvNewNode = mc.ls(sl=1,fl=1)
        bboxNew = mc.xform(dvNewNode[0],q=True,bb=True)
        bboxOld = mc.xform(selGeo[0],q=True,bb=True)
        scaleMatching = bboxNew[0]/bboxOld[0]
        if torusOnly == 0:
            if noBaseCone == 0:
                if len(revPNGon)>0:
                    mc.FillHole()
                if len(revPTris)>7:
                    mc.FillHole()
                if len(revPQuad)>0:
                    mc.FillHole()
        mc.setAttr((dvNewNode[0]+'.translateX'),(getPos[0]))
        mc.setAttr((dvNewNode[0]+'.translateY'),(getPos[1]))
        mc.setAttr((dvNewNode[0]+'.translateZ'),(getPos[2]))
        mc.setAttr((dvNewNode[0]+'.rotateX'),ppX)
        mc.setAttr((dvNewNode[0]+'.rotateY'),ppY)
        mc.setAttr((dvNewNode[0]+'.rotateZ'),ppZ)
        mc.setAttr((dvNewNode[0]+'.scaleX'),(1/scaleMatching))
        mc.setAttr((dvNewNode[0]+'.scaleZ'),(1/scaleMatching))
        mc.delete('ppA','ppB',selGeo[0])
        mc.rename(dvNewNode[0],selGeo[0])
        mc.makeIdentity(selGeo[0],apply=1, t=0, r=0, s=1, n=0)
        mc.select(selGeo[0])
        mc.polySoftEdge(selGeo[0],a=30, ch=0)
        mc.select(selGeo[0])
        #if findCone == 1:
        #    mc.polyNormal(normalMode=1, userNormalMode=0, ch=1)
        mc.headsUpDisplay( 'HUDSubDStep', section=1, block=0, blockSize='large', label='SubD No : ', labelFontSize='large', command=currentSubDStep, atr=1)
    else:
        mc.select('persp')
        mc.select(cl=1)
        mc.setToolTo('Move')

def currentSubDStep():
    global revPNode
    getNumber = mc.getAttr(revPNode+'.sections')
    return getNumber

def reRevolve():
    global revPNode
    global ctx
    subDCylinderCreate()
    if revPNode:
        ctx = 'Click2dTo3dCtx'
        if mc.draggerContext(ctx, exists=True):
            mc.deleteUI(ctx)
        mc.draggerContext(ctx, pressCommand = subDCylinderClick, rc = subDCylinderClean, dragCommand = subDCylinderDrag, name=ctx, cursor='crossHair',undoMode='step')
        mc.setToolTo(ctx)
    else:
        print('no volid selection!')

def subDCylinderClick():
    global ctx
    global currentRotRecord
    global screenX,screenY
    global mathNode
    mathNode = 0
    vpX, vpY, _ = mc.draggerContext(ctx, query=True, anchorPoint=True)
    screenX = vpX
    screenY = vpY


def subDCylinderClean():
    global reSubDMehsNode
    global revPTris
    global revPNode
    global findCone
    global newTri
    global openHolePivot
    global noBaseCone
    global diamondCone
    mc.headsUpDisplay( 'HUDSubDStep',rem=True)
    mc.polyMergeVertex(reSubDMehsNode,d=0.005, am=0, ch=0)
    if diamondCone == 1:
        pass
    else:
        if findCone == 1:
            if len(revPTris)>0:
                mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 3,where =0)
                if len(newTri)>0:
                    mc.select(reSubDMehsNode)
                    mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 3,where =0)
                    mc.polyExtrudeFacet(constructionHistory=0, keepFacesTogether=1, pvx=0, pvy=0,pvz=0, divisions=1, twist=0, taper=1, offset=0.1, thickness=0, smoothingAngle=30)
                    mc.polyMergeVertex(d=1000, am=0, ch=0)
        else:
            if revPNode:
                mc.select(reSubDMehsNode)
                if len(revPTris)>0:
                    mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 3,where =0)
                    newNface= mc.ls(sl=1,fl=1)
                    if len(newNface)==0:
                        mc.select(reSubDMehsNode)
                        findCapQuad()
                        newNface= mc.ls(sl=1,fl=1)
                        if newNface:
                            mc.sets(name='endQuadCap', text='endQuadCap')
                            mc.polyExtrudeFacet(newNface[0],constructionHistory=0, keepFacesTogether=1, pvx=0, pvy=0,pvz=0, divisions=1, twist=0, taper=1, offset=0.1, thickness=0, smoothingAngle=30)
                            mc.polyMergeVertex(d=1000, am=0, ch=0)
                            mc.select('endQuadCap')
                            mc.polySelectConstraint(mode =2, type = 0x0008 ,sz= 2,where =0)
                            newNface= mc.ls(sl=1,fl=1)
                            mc.polyExtrudeFacet(newNface[0],constructionHistory=0, keepFacesTogether=1, pvx=0, pvy=0,pvz=0, divisions=1, twist=0, taper=1, offset=0.1, thickness=0, smoothingAngle=30)
                            mc.polyMergeVertex(d=1000, am=0, ch=0)
                    else:
                        if noBaseCone == 1:
                            mc.polyExtrudeFacet(newNface[0],constructionHistory=0, keepFacesTogether=1, pvx=0, pvy=0,pvz=0, divisions=1, twist=0, taper=1, offset=0.1, thickness=0, smoothingAngle=30)
                            mc.polyMergeVertex(d=1000, am=0, ch=0)
                            mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 3,where =0)
                            mc.polySelectConstraint(disable=1)
                            newNface= mc.ls(sl=1,fl=1)
                            mc.polyExtrudeFacet(newNface[0],constructionHistory=0, keepFacesTogether=1, pvx=0, pvy=0,pvz=0, divisions=1, twist=0, taper=1, offset=0.1, thickness=0, smoothingAngle=30)
                            mc.polyMergeVertex(d=1000, am=0, ch=0)
                else:
                    pass
        if openHolePivot:
            if findCone == 0:
                if noBaseCone == 0:
                    mc.select(reSubDMehsNode)
                    mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 3,where =0)
                    checkFinalN = mc.ls(sl=1,fl=1)
                    getKill = []

                    maxDist = 10000000
                    for f in checkFinalN:
                        mc.select(f)
                        mc.setToolTo('Move')
                        pointF = mc.manipMoveContext("Move",q=1, p=1)
                        dist = math.sqrt( ((openHolePivot[0] - pointF[0])**2)  + ((openHolePivot[1] - pointF[1])**2)  + ((openHolePivot[2] - pointF[2])**2) )
                        if dist < maxDist:
                            maxDist = dist
                            getKill = f
                    if getKill:
                        mc.delete(getKill)

                    mc.select(reSubDMehsNode)
                    mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 1,where =0)
                    checkFinalT = mc.ls(sl=1,fl=1)
                    mc.ConvertSelectionToContainedEdges()
                    mc.ConvertSelectionToEdgePerimeter()
                    mc.ConvertSelectionToVertices()
                    storeUnwant = mc.ls(sl=1,fl=1)
                    mc.select(checkFinalT)
                    mc.ConvertSelectionToVertices()
                    mc.select(storeUnwant,d=1)
                    checkFinalTip = mc.ls(sl=1,fl=1)
                    if len(checkFinalTip)==1:
                        mc.setToolTo('Move')
                        pointF = mc.manipMoveContext("Move",q=1, p=1)
                        dist = math.sqrt( ((openHolePivot[0] - pointF[0])**2)  + ((openHolePivot[1] - pointF[1])**2)  + ((openHolePivot[2] - pointF[2])**2) )
                        if dist < 0.001:
                            mc.delete(checkFinalT)
            #else:
        #    mc.FillHole()
    mc.polySelectConstraint(disable=1)
    mc.select(reSubDMehsNode)
    mc.polySoftEdge(a=30, ch=0)
    mc.delete(all=1, e=1, ch=1)
    mc.select(reSubDMehsNode)
    cleanList = ('ppA','ppB','profileCurve','coneTip','endQuadCap')
    for c in cleanList:
        if mc.objExists(c):
            mc.delete(c)
    mc.setToolTo('Move')

def subDCylinderDrag():
    global ctx
    global screenX,screenY
    global revPNode
    global mathNode
    modifiers = mc.getModifiers()
    if revPNode:
        vpX, vpY, _ = mc.draggerContext(ctx, query=True, dragPoint=True)
        distanceCheck = vpX - screenX
        screenX = vpX
        currentendSweep = mc.getAttr(revPNode+'.endSweep')
        currentSections = mc.getAttr(revPNode+'.sections')
        if (modifiers == 1):
            if distanceCheck > 0.1:
                currentendSweep = currentendSweep + 1
            elif distanceCheck < 0.1:
                currentendSweep = currentendSweep - 1
            if currentSections < 0:
                currentSections = 0
            mc.setAttr((revPNode+'.endSweep'),currentendSweep)
        else:
            if distanceCheck > 0.1:
                mathNode = mathNode + 0.15
                if mathNode > 1:
                    currentSections = currentSections + 1
                    mathNode = 0
            elif distanceCheck < 0.1:
                mathNode = mathNode - 0.15
                if mathNode < -1:
                    currentSections = currentSections - 1
                    mathNode = 0
            if currentSections < 4:
                currentSections = 4
            mc.setAttr((revPNode+'.sections'),currentSections)
        mc.refresh(cv=True,f=True)

def findCapQuad():
    selGeoTemp = mc.ls(sl=1,fl=1)
    mc.polySelectConstraint(mode =3, type = 0x0008 ,sz= 1,where =0)
    revPTris = mc.ls(sl=1,fl=1)
    mc.polySelectConstraint(disable=1)
    if len(revPTris) == 0:
        totalEdgeNo= mc.polyEvaluate(selGeoTemp[0], e=True )
        heckNo = int(totalEdgeNo)/2
        mc.select(selGeoTemp[0]+'.e['+ str(heckNo) + ']')
        mc.SelectEdgeRingSp()
        mc.SelectEdgeLoopSp()
        mc.ConvertSelectionToFaces()
        mc.InvertSelection()
        checkFaceGet = mc.ls(sl=1,fl=1)
        if checkFaceGet:
            if len(checkFaceGet) == 2:
                mc.ConvertSelectionToContainedEdges()
                checkConnectEdge = mc.filterExpand( sm=32)
                if not checkConnectEdge:
                    mc.select(checkFaceGet)
                else:
                    mc.SelectEdgeLoopSp()
                    tempRing = mc.ls(sl=1,fl=1)
                    mc.GrowPolygonSelectionRegion()
                    mc.select(tempRing,d=1)
                    mc.SelectEdgeLoopSp()
                    mc.ConvertSelectionToFaces()
                    mc.InvertSelection()
            else:#try again
                mc.select(selGeoTemp[0]+'.e['+ str(heckNo) + ']')
                mc.SelectEdgeLoopSp()
                checkEdgeGet = mc.ls(sl=1,fl=1)
                if len(checkEdgeGet) == 1:#cap edge
                    mc.SelectEdgeRingSp()
                    checkEdgeRingGet = mc.ls(sl=1,fl=1)
                    mc.select(selGeoTemp[0]+'.e[0]')
                    mc.ConvertSelectionToFaces()
                    mc.ConvertSelectionToEdges()
                    checkFaceEdgeGet = mc.ls(sl=1,fl=1)
                    mc.select(selGeoTemp[0])
                    mc.ConvertSelectionToEdges()
                    mc.select(checkEdgeRingGet,d=1)
                    mc.select(checkFaceEdgeGet,d=1)
                    checkNextPossible = mc.ls(sl=1,fl=1)
                    mc.select(checkNextPossible[0])
                    mc.SelectEdgeRingSp()
                    mc.SelectEdgeLoopSp()
                    mc.ConvertSelectionToFaces()
                    mc.InvertSelection()
                    checkFaceGet = mc.ls(sl=1,fl=1)
                    if checkFaceGet:
                        if len(checkFaceGet) == 2:
                            mc.ConvertSelectionToContainedEdges()
                            checkConnectEdge = mc.filterExpand( sm=32)
                            if not checkConnectEdge:
                                mc.select(checkFaceGet)
                elif len(checkEdgeGet) > 1:# find loop, good
                    mc.SelectEdgeRingSp()
                    tempRing = mc.ls(sl=1,fl=1)
                    mc.GrowPolygonSelectionRegion()
                    mc.select(tempRing,d=1)
                    mc.SelectEdgeLoopSp()
                    mc.ConvertSelectionToFaces()
                    mc.InvertSelection()
                    mc.select(checkFaceGet)
    else:
        mc.select(cl=1)

def getEdgeRingGroup():
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
        collectList=[]
        for x in f:
            getCom= (trans +".e["+ str(x) +"]")
            collectList.append(getCom)
        retEdges.append(collectList)
    return retEdges

reRevolve()
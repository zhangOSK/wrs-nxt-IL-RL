import os
from panda3d.core import *
from direct.gui.DirectGui import *
import pandaplotutils.pandactrl as pc
from direct.gui.OnscreenImage import OnscreenImage
from vision import hndcam
import bldgfsettingnear
import database.dbaccess as db
# import manipulation.grip.robotiq85.rtq85nm as rtq85nm
import manipulation.grip.schunk918.sck918 as sck918
import robotsim.nextage.nxtmesh as nxtsimmesh
import robotsim.nextage.nxtball as nxtsimball
import robotsim.nextage.nxtik as nxtik
import robotsim.nextage.nxt as nxtsim
import copy
import numpy as np
import manipulation.regrasp.regriptppfp as regriptppfp
import motionplanning.collisioncheckerball as ccball
import manipulation.regrasp.plannerwaist as rp
import utiltools.robotmath as rm
import nxt_rpyc as nxturx
import math

class NxtDTCtl(object):
    """
    the controller module of the application

    author: weiwei
    date: 20190402
    """

    def __init__(self, objname, markerid = 5):
        self.markerid = markerid
        self.objname = objname
        self.gdb = db.GraspDB(database="nxt", user="root", password="lovemaomao1123")
        self.robot = nxtsim.NxtRobot()
        self.rgthnd = sck918.Sck918(jawwidth=50, hndcolor=(0.5,0.5,0.5,1), ftsensoroffset=0)
        self.lfthnd = sck918.Sck918(jawwidth=25, hndcolor=(0.5,0.5,0.5,1), ftsensoroffset=0)
        self.robotmesh = nxtsimmesh.NxtMesh(rgthand=self.rgthnd, lfthand=self.lfthnd)
        self.robotball = nxtsimball.NxtBall()
        self.robotik = nxtik
        self.env = bldgfsettingnear.Env()
        self.env.reparentTo(base.render)
        self.objcm = self.env.loadobj(objname)
        # self.groove = self.env.loadobj("new_GROOVE.stl")
        self.groove = self.env.loadobj("twostairhole.STL")
        self.groove.setPos(600, 0, 973 - 15)
        self.groove.setRPY(0, 0, 0)
        self.groove.setColor(0, 1, 0, 0.5)
        self.groove.reparentTo(base.render)
        self.obstaclecmlist = self.env.getstationaryobslist()
        # for obstaclecdcm in self.obstaclecmlist:
        #     obstaclecdcm.showcn()

        self.robot.goinitpose()

        # self.rgtwatchpos = [400.0, -200.0, 1200.0]
        # self.rgtwatchrotmat = [[0.09141122, -0.76823672, 0.63360582],
        #                        [-0.99509199, -0.04625775, 0.08747659],
        #                        [-0.03789355, -0.63849242, -0.76869468]]
        # self.rgtwatchjs = self.robot.numik(self.rgtwatchpos, self.rgtwatchrotmat, "rgt")
        #
        # self.robot.movearmfk(self.rgtwatchjs, armname="rgt")
        self.rbtmnp = self.robotmesh.genmnp(self.robot, self.rgthnd.jawwidthopen, self.lfthnd.jawwidthopen)
        self.rbtmnp.reparentTo(base.render)

        # uncomment the following commands to actuate the robot
        # self.nxtu = nxturx.NxtCon()
        # self.nxtu.setJointAnglesOfGroup('rarm', self.robot.initjnts[3:9], 5.0)
        # self.nxtu.setJointAnglesOfGroup('larm', self.robot.initjnts[9:15], 5.0)

        self.hc = hndcam.HndCam(rgtcamid = 0, lftcamid = 1)

        # goallist, a list of 4x4 homo numpy mat
        self.goallist = []
        self.objrenderlist = []
        self.startobjcm = None

        self.rbtmnpani = [None, None]
        self.objmnpani = [None]

    def restart(self):
        """
        reset everything
        :return:

        author: weiwei
        date:20180926
        """
        taskMgr.remove('updatemotionsec')

        # self.robot.movearmfk(self.rgtwatchjs, armname="rgt")
        self.rbtmnp = self.robotmesh.genmnp(self.robot, self.rgthnd.jawwidthopen, self.lfthnd.jawwidthopen)
        self.rbtmnp.reparentTo(base.render)

        # uncomment the following commands to actuate the robot
        # self.nxtu.setJointAnglesOfGroup('torso', 0.0, 5.0)
        # self.nxtu.setJointAnglesOfGroup('rarm', self.robot.initjnts[3:9], 5.0)
        # self.nxtu.setJointAnglesOfGroup('larm', self.robot.initjnts[9:15], 5.0)

        for objrender in self.objrenderlist:
            objrender.removeNode()
        if self.startobjcm is not None:
            self.startobjcm.removeNode()
        self.goallist = []
        self.objrenderlist = []
        if self.rbtmnpani[0] is not None:
            self.rbtmnpani[0].detachNode()
            self.rbtmnpani[1].detachNode()
        if self.objmnpani[0] is not None:
            self.objmnpani[0].detachNode()
        self.rbtmnpani = [None, None]
        self.objmnpani = [None]

    def rgtcapture(self):
        """
        capture one goal pose using the rgt hndcam system

        :return: a 4x4 homo numpy mat

        author: weiwei
        date: 20180926
        """

        # goalT = self.hc.getObjPoseRgtCam(self.rgtwatchpos, self.rgtwatchrotmat, marker_id=self.markerid)
        posG = base.pg.npToMat4(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
                                np.array([600, 0, 973 - 15]))
        # print(posG)
        # relpos1 = np.array([-60.14147593, -0.43612779, 40.08426847])
        # relrot1 = np.array([[0.9672951, 0.003912, 0.25362363],
        #                     [-0.00265115, 0.99998247, -0.00531303],
        #                     [-0.25363992, 0.00446691, 0.9672884]])
        relpos0 = np.array([-65, 0, 65])
        relrot0 = np.array([[1, 0, 0],
                            [0, 1, 0],
                            [0, 0, 1]])
        rel0 = base.pg.npToMat4(relrot0, relpos0)
        posL0 = rel0 * posG
        virtualgoalpos0 = np.array([posL0[3][0], posL0[3][1], posL0[3][2]])
        virtualgoalrot0 = np.array([[posL0[0][0], posL0[1][0], posL0[2][0]],
                                    [posL0[0][1], posL0[1][1], posL0[2][1]],
                                    [posL0[0][2], posL0[1][2], posL0[2][2]]])

        relpos1 = np.array([-65, 0, 50])
        relrot1 = np.array([[1, 0, 0],
                            [0, 1, 0],
                            [0, 0, 1]])
        rel1 = base.pg.npToMat4(relrot1, relpos1)
        posL1 = rel1 * posG
        virtualgoalpos1 = np.array([posL1[3][0], posL1[3][1], posL1[3][2]])
        virtualgoalrot1 = np.array([[posL1[0][0], posL1[1][0], posL1[2][0]],
                                    [posL1[0][1], posL1[1][1], posL1[2][1]],
                                    [posL1[0][2], posL1[1][2], posL1[2][2]]])
        # virtualgoalpos0 = np.array([480,0,973-76+75+20])
        # virtualgoalrot0 = rm.rodrigues([0,1,0,], 20)
        # virtualgoalpos1 = np.array([450,250,1200])
        # virtualgoalrot1 = rm.rodrigues([0,1,0,], -90)
        virtualgoalpos2 = np.array([490,250,1200])
        virtualgoalrot2 = rm.rodrigues([0,1,0,], -90)
        virtualgoalpos3 = np.array([490,350,1200])
        virtualgoalrot3 = rm.rodrigues([0,1,0,], -90)
        goalTlist = [rm.homobuild(virtualgoalpos0, virtualgoalrot0),
                     rm.homobuild(virtualgoalpos1, virtualgoalrot1),
                     rm.homobuild(virtualgoalpos2, virtualgoalrot2),
                     rm.homobuild(virtualgoalpos3, virtualgoalrot3)]

        ngoal = len(self.goallist)
        if ngoal >= len(goalTlist):
            return False
        goalT = goalTlist[ngoal]
        if goalT is None:
            return False
        else:
            self.goallist.append(goalT)
            tmpobjcm = copy.deepcopy(self.objcm)
            tmpobjcm.setMat(base.pg.np4ToMat4(goalT))
            tmpobjcm.reparentTo(base.render)
            tmpobjcm.showLocalFrame()
            self.objrenderlist.append(tmpobjcm)
            for id, tmpobjcm in enumerate(self.objrenderlist):
                tmpobjcm.setColor(0,(id)/float(len(self.objrenderlist)),(id+1)/float(len(self.objrenderlist)), 0.9)
            return True

    def delrgtcapture(self):
        """
        delete the last captured goal

        :return: successfully deleted or not

        author: weiwei
        date: 20180926
        """

        # goalT = self.hc.getObjPoseRgtCam(self.rgtwatchpos, self.rgtwatchrotmat, marker_id=self.markerid)
        ngoal = len(self.goallist)
        if ngoal == 0:
            return False
        self.goallist.pop()
        self.objrenderlist[-1].removeNode()
        self.objrenderlist.pop()
        return True

    def rgtcapturestart(self):
        """
        capture the starting pose using the rgt hndcam system

        :return:

        author: weiwei
        date: 20180926
        """
        # startT = None
        # while startT is None:
        #     startT = self.hc.getObjPoseRgtCam(self.rgtwatchpos, self.rgtwatchrotmat, marker_id=self.markerid)
        # startT = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[500,-350,1100,1.0]]).T

        virtualgoalpos0 = np.array([450,-200,973-14])
        virtualgoalrot0 = rm.rodrigues([0,1,0,],0)
        # virtualgoalrot0 = np.array([[0, 0, -1], [-1, 0, 0], [0, 1, 0]])
        startT = rm.homobuild(virtualgoalpos0, virtualgoalrot0)

        self.goallist = [startT]+self.goallist
        self.startobjcm = copy.deepcopy(self.objcm)
        self.startobjcm.setMat(base.pg.np4ToMat4(startT))
        self.startobjcm.reparentTo(base.render)
        self.startobjcm.showLocalFrame()
        self.startobjcm.setColor(1,0,0,1)

    def plannplay(self, transitoption = "useboth", choice = "startrgtgoalrgt"):
        """
        updated 20190314

        :param transitoption: "useplacement", "usehandover", "useboth"
        :return:
        """

        # capture initial objpose
        self.robot.goinitpose()
        # start OC
        print("Finding motion to goal 1...")
        startrotmat4 = base.pg.np4ToMat4(self.goallist[0])
        goalrotmat4 = base.pg.np4ToMat4(self.goallist[1])
        regrip = regriptppfp.RegripTppFp(self.objcm.objpath, self.robot, sck918, self.gdb, base,
                                         self.obstaclecmlist, transitoption=transitoption)



        regrip.addStartGoal(startrotmat4 = startrotmat4, goalrotmat4 = goalrotmat4, choice = choice, goaltoolvec=(-1,0,0))
        cdchecker = ccball.CollisionCheckerBall(self.robotball)
        # OUTERLOOP collision detection
        objmsmp, numikrmsmp, jawwidthmp, originalpathnidlist = rp.planRegrasp(self.robot, regrip, self.objcm, cdchecker,
                                                                              self.obstaclecmlist+[self.groove], switch="OC",
                                                                              previous = [], end = False, togglemp=True)
        if objmsmp is None:
            return False
        nextid = regrip.regg.node[originalpathnidlist[-1]]['globalgripid']
        for id in range(1, len(self.goallist)-1):
            isend = False
            if id == len(self.goallist)-2:
                isend = True
            print("Finding motion to goal "+str(id+1)+"...")
            print("Start and goal hand global ids are ", nextid)
            startrotmat4 = base.pg.np4ToMat4(self.goallist[id])
            goalrotmat4 = base.pg.np4ToMat4(self.goallist[id+1])
            regrip.reset()
            regrip.addStartGoal(startrotmat4 = startrotmat4, goalrotmat4 = goalrotmat4, choice = "startrgtgoalrgt",
                                startgraspgid=nextid, starttoolvec = [0,0,0], goaltoolvec = [0,0,0])
            # cdchecker = ccball.CollisionCheckerBall(self.robotball)
            # OUTERLOOP collision detection
            objmsmp_t, numikrmsmp_t, jawwidthmp_t, originalpathnidlist_t = rp.planRegrasp(self.robot, regrip,
                                                                                          self.objcm, cdchecker,
                                                                                          self.obstaclecmlist,
                                                                                          switch="CC",
                                                                                          previous=[objmsmp[-1][-1], numikrmsmp[-1][-1], jawwidthmp[-1][-1]],
                                                                                          end = isend,
                                                                                          togglemp=True)
            if objmsmp_t is None and id == len(self.goallist)-2:
                break
            elif objmsmp_t is None:
                return False
            objmsmp = objmsmp+[None]+objmsmp_t
            numikrmsmp = numikrmsmp+[None]+numikrmsmp_t
            jawwidthmp = jawwidthmp+[None]+jawwidthmp_t
            nextid = regrip.regg.node[originalpathnidlist_t[-1]]['globalgripid']
        objmsmp = objmsmp + [None]
        numikrmsmp = numikrmsmp + [None]
        jawwidthmp = jawwidthmp + [None]
        self.rbtmnp.removeNode()

        self.rbtmnpani = [None, None]
        self.objmnpani = [None]
        motioncounter = [0]
        def updatemotionsec(objms, numikrms, jawwidth, rbtmnp, objmnp, motioncounter, robot, objcm, task):
            if motioncounter[0] < len(numikrms):
                if rbtmnp[0] is not None:
                    rbtmnp[0].detachNode()
                    # rbtmnp[1].detachNode()
                if objmnp[0] is not None:
                    objmnp[0].detachNode()
                rgtarmjnts = numikrms[motioncounter[0]][1].tolist()
                lftarmjnts = numikrms[motioncounter[0]][2].tolist()
                robot.movealljnts([numikrms[motioncounter[0]][0], 0, 0] + rgtarmjnts + lftarmjnts)
                rgtjawwidth = jawwidth[motioncounter[0]][0]
                lftjawwidth = jawwidth[motioncounter[0]][1]
                # print rgtjawwidth, lftjawwidth
                rbtmnp[0] = self.robotmesh.genmnp(robot, rgtjawwidth, lftjawwidth)
                bcndict = self.robotball.genfullactivebcndict(robot)
                # rbtmnp[1] = self.robotball.showcn(base, bcndict)
                robot.goinitpose()
                rbtmnp[0].reparentTo(base.render)
                objmnp[0] = copy.deepcopy(objcm)
                objmnp[0].setMat(objms[motioncounter[0]])
                objmnp[0].reparentTo(base.render)
                objmnp[0].showLocalFrame()
                # objmnp[0].showcn()
                motioncounter[0] += 1
            else:
                motioncounter[0] = 0
            # base.win.saveScreenshot(Filename(str(motioncounter[0]) + '.jpg'))
            return task.again

        objmsmpactive = [objmsmp[0]]
        numikrmsmpactive = [numikrmsmp[0]]
        jawwidthmpactive = [jawwidthmp[0]]
        taskMgr.doMethodLater(0.1, updatemotionsec, "updatemotionsec",
                              extraArgs=[objmsmpactive[0], numikrmsmpactive[0], jawwidthmpactive[0], self.rbtmnpani,
                                         self.objmnpani, motioncounter, self.robot, self.objcm],
                              appendTask=True)
        motionseccounter = [0]
        def updatesection(objmsmpactive, numikrmsmpactive, jawwidthmpactive, objmsmp, numikrmsmp, jawwidthmp, rbtmnp,
                          objmnp, motioncounter, motionseccounter, robot, objcm, task):
            if base.inputmgr.keyMap['space'] is True:
                # print(motionseccounter[0], len(objmsmp) - 1)
                if motionseccounter[0] <= len(objmsmp) - 1:
                    motionseccounter[0] = motionseccounter[0] + 1
                    if not (motionseccounter[0] == len(objmsmp)):
                        if objmsmp[motionseccounter[0]] is not None:
                            objmsmpactive[0] = objmsmp[motionseccounter[0]]
                            numikrmsmpactive[0] = numikrmsmp[motionseccounter[0]]
                            jawwidthmpactive[0] = jawwidthmp[motionseccounter[0]]
                            base.inputmgr.keyMap['space'] = False
                            # print(motionseccounter[0])
                            # print(jawwidthmpactive[0])
                            taskMgr.remove('updatemotionsec')
                            motioncounter[0] = 0
                            taskMgr.doMethodLater(0.1, updatemotionsec, "updatemotionsec",
                                                  extraArgs=[objmsmpactive[0], numikrmsmpactive[0], jawwidthmpactive[0], rbtmnp,
                                                             objmnp, motioncounter, robot, objcm],
                                                  appendTask=True)
                    if objmsmp[motionseccounter[0]-1] is not None:
                        # execute the last sequence
                        # temp_objmsmpactive = objmsmp[motionseccounter[0]-1]
                        temp_numikrmsmpactive = numikrmsmp[motionseccounter[0] - 1]
                        # print "temp_numikrmsmpactive is %s" % temp_numikrmsmpactive
                        temp_jawwidthmpactive = jawwidthmp[motionseccounter[0] - 1]  # rgt and left
                        #
                        jntslist_waist = []
                        jntslist_rgt = []
                        jntslist_lft = []
                        jawwidthlist_rgt = []
                        jawwidthlist_lft = []

                        for eachtemp in temp_numikrmsmpactive:
                            jntslist_waist.append(eachtemp[0])
                            # print ("Joint list waist:{} ".format(jntslist_waist))
                            jntslist_rgt.append(eachtemp[1].tolist())
                            # print ("Joint list right:{} ".format(jntslist_rgt))
                            jntslist_lft.append(eachtemp[2].tolist())
                            # print ("Joint list left:{} ".format(jntslist_lft))
                        # print ("Length of joint list is:{} ".format(len(jntslist_rgt)))

                        for eachtemp in temp_jawwidthmpactive:
                            jawwidthlist_rgt.append(eachtemp[0])
                            # print ("jaw width list right:{} ".format(jawwidthlist_rgt))
                            jawwidthlist_lft.append(eachtemp[1])
                            # print ("jaw width list left:{} ".format(jawwidthlist_lft))
                        # print jawwidthlist_rgt

                        # uncomment this part to actuate the Nextage
                        if len(jntslist_rgt) == 2:
                            # do nothing; We dont need to examine lft since they are symmetric
                            pass
                        else:
                            # check if the waist is moved
                            waistdiff = abs(np.array(jntslist_waist[0])-np.array(jntslist_waist[-1]))
                            if waistdiff.max() > 1e-6:
                                # print "jntslist_waist is %s" % jntslist_waist
                                jntslist_waist_rad = []
                                for i in range(len(jntslist_waist)):
                                    # print "jntslist_waist[%d] is %s" % (i, jntslist_waist[i])
                                    jntslist_waist_rad.append(math.radians(jntslist_waist[i]))
                                # print "jntslist_waist_rad is %s" % jntslist_waist_rad
                                new_jntslist_waist_rad = []
                                for j in range(len(jntslist_waist_rad)):
                                    jnt_waist_rad = []
                                    jnt_waist_rad.append(jntslist_waist_rad[j])
                                    new_jntslist_waist_rad.append(jnt_waist_rad)
                                # print "new_jntslist_waist_rad is %s" % new_jntslist_waist_rad
                                # time = [0.2]
                                # para_waist = ['torso', new_jntslist_waist_rad, time*len(new_jntslist_waist_rad)]
                                # self.nxtu.playPatternOfGroup(para_waist)

                            # check if the arm is moved
                            rgtdiff = abs(np.array(jntslist_rgt[0])-np.array(jntslist_rgt[-1]))
                            if rgtdiff.max() > 1e-6:
                                # print "jntslist_rgt is %s" % jntslist_rgt
                                jntslist_rgt_rad = []
                                jnts_rgt_rad = []
                                for i in range(len(jntslist_rgt)):
                                    # print "jntslist_rgt[%d] is %s" % (i, jntslist_rgt[i])
                                    for j in range(len(jntslist_rgt[i])):
                                        jnts_rgt_rad.append(math.radians(jntslist_rgt[i][j]))
                                    # print "jntslist_rgt_rad[%d] is %s" % (i, jnts_rgt_rad[(len(jntslist_rgt[i]) * i):len(jntslist_rgt[i]) * (i + 1)])
                                    jntslist_rgt_rad.append(jnts_rgt_rad[(len(jntslist_rgt[i])*i):len(jntslist_rgt[i])*(i+1)])
                                # print "jntslist_rgt_rad is %s" % jntslist_rgt_rad
                                # time = [0.2]
                                # para_rgt = ['rarm', jntslist_rgt_rad, time*len(jntslist_rgt_rad)]
                                # self.nxtu.playPatternOfGroup(para_rgt)

                            lftdiff = abs(np.array(jntslist_lft[0])-np.array(jntslist_lft[-1]))
                            if lftdiff.max() > 1e-6:
                                # print "jntslist_lft is %s" % jntslist_lft
                                jntslist_lft_rad = []
                                jnts_lft_rad = []
                                for i in range(len(jntslist_lft)):
                                    # print "jntslist_rgt[%d] is %s" % (i, jntslist_lft[i])
                                    for j in range(len(jntslist_lft[i])):
                                        jnts_lft_rad.append(math.radians(jntslist_lft[i][j]))
                                    # print "jntslist_lft_rad[%d] is %s" % (i, jnts_lft_rad[(len(jntslist_lft[i]) * i):len(jntslist_lft[i]) * (i + 1)])
                                    jntslist_lft_rad.append(jnts_lft_rad[(len(jntslist_rgt[i]) * i):len(jntslist_lft[i]) * (i + 1)])
                                # print "jntslist_lft_rad is %s" % jntslist_lft_rad
                                # time = [0.2]
                                # para_lft = ['larm', jntslist_lft_rad, time*len(jntslist_lft_rad)]
                                # self.nxtu.playPatternOfGroup(para_lft)


                        # if jawwidthlist_rgt[-1] <85.0:
                        #     self.ur3u.closegripper("rgt")
                        # else:
                        #     self.ur3u.opengripper("rgt")
                        # if jawwidthlist_lft[-1] < 85.0:
                        #     self.ur3u.closegripper("lft")
                        # else:
                        #     self.ur3u.opengripper("lft")
                    else:
                        #TODO add directokdialog
                        print("One motion section is done!")
                else:
                    motionseccounter[0] = 0
                    taskMgr.remove('updateshow')
                    return task.again
            return task.again
        taskMgr.doMethodLater(0.04, updatesection, "updatesection",
                              extraArgs=[objmsmpactive, numikrmsmpactive, jawwidthmpactive, objmsmp, numikrmsmp,
                                         jawwidthmp, self.rbtmnpani, self.objmnpani, motioncounter, motionseccounter,
                                         self.robot, self.objcm],
                              appendTask=True)
        return True

class HLabGUI(object):
    """
    the graphical user interface of the application

    author: weiwei
    date: 20180925
    """

    def captureFromTeacher(self):
        iscaptured = self.scctrl.rgtcapture()
        self.nposes = len(self.scctrl.goallist)
        self.textNPose['text']='#Poses: '+str(self.nposes)
        if not iscaptured:
            self.textCaptured['text']='Failed to capture!'

    def deleteCapture(self):
        isdeleted = self.scctrl.delrgtcapture()
        self.nposes = len(self.scctrl.goallist)
        self.textNPose['text']='#Poses: '+str(self.nposes)
        if not isdeleted:
            self.textCaptured['text']='All goals cleared!'

    def recognize(self):
        self.scctrl.rgtcapturestart()
        self.nposes = len(self.scctrl.goallist)
        self.textNPose['text']='#Poses: '+str(self.nposes)

    def execplan(self):
        self.textCaptured['text']='Planning!'
        self.scctrl.plannplay(choice = "startrgtgoalrgt")

    def restart(self):
        self.scctrl.restart()
        self.nposes = len(self.scctrl.goallist)
        self.textNPose['text']='#Poses: '+str(self.nposes)
        self.textCaptured['text']='Read to capture'

    def __init__(self, scenarioctrl):
        self.scctrl = scenarioctrl
        this_dir, this_filename = os.path.split(__file__)
        self.imageObject = OnscreenImage(image="./gui/banner250x1080.png", pos=(1.55, 0, 0), scale=(250/1080.0,1,1))

        bcmappath = Filename.fromOsSpecific(os.path.join(this_dir, "gui", "buttoncapture_maps.egg"))
        maps = loader.loadModel(bcmappath)
        self.capturebtn = DirectButton(frameSize=(-1,1,-.25,.25), geom=(maps.find('**/buttoncapture_ready'),
                               maps.find('**/buttoncapture_click'),
                               maps.find('**/buttoncapture_rollover')),
                               pos=(1.45, 0, .54), scale=(.06,.12,.12),
                               command = self.captureFromTeacher)

        brmappath = Filename.fromOsSpecific(os.path.join(this_dir, "gui", "buttondelete_maps.egg"))
        maps = loader.loadModel(brmappath)
        self.runbtn = DirectButton(frameSize=(-1,1,-.25,.25), geom=(maps.find('**/buttondelete_ready'),
                               maps.find('**/buttondelete_click'),
                               maps.find('**/buttondelete_rollover')),
                               pos=(1.575, 0, .54), scale=(.06,.12,.12),
                               command = self.deleteCapture)

        brmappath = Filename.fromOsSpecific(os.path.join(this_dir, "gui", "buttonrecog_maps.egg"))
        maps = loader.loadModel(brmappath)
        self.runbtn = DirectButton(frameSize=(-1,1,-.25,.25), geom=(maps.find('**/buttonrecog_ready'),
                               maps.find('**/buttonrecog_click'),
                               maps.find('**/buttonrecog_rollover')),
                               pos=(1.7, 0, .54), scale=(.06,.12,.12),
                               command = self.recognize)

        brmappath = Filename.fromOsSpecific(os.path.join(this_dir, "gui", "buttonplan_maps.egg"))
        maps = loader.loadModel(brmappath)
        self.runbtn = DirectButton(frameSize=(-1,1,-.25,.25), geom=(maps.find('**/buttonplan_ready'),
                               maps.find('**/buttonplan_click'),
                               maps.find('**/buttonplan_rollover')),
                               pos=(1.45, 0, .47), scale=(.06,.12,.12),
                               command = self.execplan)

        brmappath = Filename.fromOsSpecific(os.path.join(this_dir, "gui", "buttonrun_maps.egg"))
        maps = loader.loadModel(brmappath)
        self.runbtn = DirectButton(frameSize=(-1,1,-.25,.25), geom=(maps.find('**/buttonrun_ready'),
                               maps.find('**/buttonrun_click'),
                               maps.find('**/buttonrun_rollover')),
                               pos=(1.575, 0, .47), scale=(.06,.12,.12),
                               command = self.execplan)

        brmappath = Filename.fromOsSpecific(os.path.join(this_dir, "gui", "buttonrestart_maps.egg"))
        maps = loader.loadModel(brmappath)
        self.runbtn = DirectButton(frameSize=(-1,1,-.25,.25), geom=(maps.find('**/buttonrestart_ready'),
                               maps.find('**/buttonrestart_click'),
                               maps.find('**/buttonrestart_rollover')),
                               pos=(1.7, 0, .47), scale=(.06,.12,.12),
                               command = self.restart)

        self.nposes = 0
        self.textNPose = OnscreenText(text='#Poses: '+str(self.nposes), pos=(1.45, -.9, 0), scale=0.03, fg=(1., 1., 1., 1),
                                      align=TextNode.ALeft, mayChange=1)
        self.textCaptured = OnscreenText(text='Ready to capture', pos=(1.45, -.95, 0), scale=0.03, fg=(1., 1., 1., 1),
                                      align=TextNode.ALeft, mayChange=1)

if __name__=="__main__":
    base = pc.World(camp=[3000,-300,3000], lookatp=[0,200,1000], up = [0,0,1], fov = 40, w = 1920, h = 1080)
    # objname = "housing.stl"
    # objname = "box.stl"
    # objname = "tool_motordriver.stl"
    # objname = "bunnysim.stl"
    # objname = "new_LSHAPE.stl"
    # objname = "twostairpeg.STL"
    objname = "twostairpeg_handle.STL"
    nxtt = NxtDTCtl(objname)
    gui = HLabGUI(nxtt)
    #
    # freeairgripdata = nxtt.gdb.loadFreeAirGrip("LShape","sck918")
    # if freeairgripdata is None:
    #     raise ValueError("Plan the freeairgrip first!")
    #
    # freegripids = freeairgripdata[0]
    # freegripcontacts = freeairgripdata[1]
    # freegripnormals = freeairgripdata[2]
    # freegriprotmats = freeairgripdata[3]
    # freegripjawwidth = freeairgripdata[4]
    #
    # for i in freegriprotmats:
    #     print(i)
    #     sckhnd = sck918.Sck918()
    #     sckhnd.setMat(i)
    #     sckhnd.setPos(Vec3(300,0,1300))
    #     sckhnd.reparentTo(base.render)

    base.run()
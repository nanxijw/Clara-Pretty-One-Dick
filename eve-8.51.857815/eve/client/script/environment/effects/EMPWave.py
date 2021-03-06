#Embedded file name: eve/client/script/environment/effects\EMPWave.py
from eve.client.script.environment.effects.GenericEffect import GenericEffect, STOP_REASON_DEFAULT, STOP_REASON_BALL_REMOVED
import trinity
import audio2
import util

class EMPWave(GenericEffect):
    __guid__ = 'effects.EMPWave'

    def __init__(self, trigger, *args):
        GenericEffect.__init__(self, trigger, *args)
        self.ballIDs = [trigger.shipID]
        self.gfx = None
        self.gfxModel = None
        self.radius = 5000.0
        self.moduleTypeID = trigger.moduleTypeID
        self.translationCurve = None

    def Stop(self, reason = STOP_REASON_DEFAULT):
        if self.gfx is None:
            raise RuntimeError('ShipEffect: no effect defined')
        scene = self.fxSequencer.GetScene()
        scene.objects.fremove(self.gfxModel)
        self.gfx = None
        self.translationCurve = None
        self.gfxModel = None

    def Prepare(self):
        shipID = self.ballIDs[0]
        shipBall = self.fxSequencer.GetBall(shipID)
        if shipBall is None:
            raise RuntimeError('EMPWave: no ball found')
        if self.moduleTypeID == 0:
            self.moduleTypeID = 15957
        graphicID = cfg.invtypes.Get(self.moduleTypeID).graphicID
        if graphicID is None:
            raise RuntimeError('EMPWave: no graphic ID')
        gfxString = util.GraphicFile(graphicID)
        self.gfx = trinity.Load(gfxString)
        if self.gfx is None:
            raise RuntimeError('EMPWave: no effect found')
        entity = audio2.AudEmitter('effect_' + str(shipID))
        obs = trinity.TriObserverLocal()
        obs.observer = entity
        if self.gfx.__bluetype__ in ('trinity.EveTransform',):
            self.gfx.observers.append(obs)
        for curveSet in self.gfx.curveSets:
            for curve in curveSet.curves:
                if curve.__typename__ == 'TriEventCurve' and curve.name == 'audioEvents':
                    curve.eventListener = entity

        self.gfxModel = trinity.EveRootTransform()
        radius = self.fxSequencer.GetTypeAttribute(self.moduleTypeID, const.attributeEmpFieldRange)
        self.gfxModel.scaling = (radius / 1000, radius / 1000, radius / 1000)
        self.radius = radius
        self.gfxModel.name = self.__guid__
        self.gfxModel.children.append(self.gfx)
        self.gfxModel.translationCurve = shipBall
        scene = self.fxSequencer.GetScene()
        scene.objects.append(self.gfxModel)

    def Start(self, duration):
        if self.gfx is None:
            raise RuntimeError('ShipEffect: no effect defined')
        if self.scaleTime and len(self.gfxModel.curveSets) > 0:
            length = self.gfxModel.curveSets[0].GetMaxCurveDuration()
            if length > 0.0:
                scaleValue = length / (duration / 1000.0)
                self.gfxModel.curveSets[0].scale = scaleValue
        self.gfx.curveSets[0].Play()

    def Repeat(self, duration):
        if self.gfx is None:
            raise RuntimeError('EMPWave: no effect defined')
        shipID = self.ballIDs[0]
        shipBall = self.fxSequencer.GetBall(shipID)
        if shipBall is None:
            self.Stop(STOP_REASON_BALL_REMOVED)
        self.gfx.curveSets[0].Play()

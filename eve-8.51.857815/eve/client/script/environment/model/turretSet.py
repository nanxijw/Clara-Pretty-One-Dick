#Embedded file name: eve/client/script/environment/model\turretSet.py
import trinity
import blue
import log
import audio2
import util
import evegraphics.settings as gfxsettings
from stacklesslib.util import block_trap
LASER_MISS_BEHAVIOUR_GROUPS = [53]
PROJECTILE_MISS_BEHAVIOUR_GROUPS = [55]

class TurretSet:
    __guid__ = 'turretSet.TurretSet'
    turretsEnabled = [False]

    def Initialize(self, graphics, locator, overrideBeamGraphicID = None, count = 1):
        """
        Initializes turrets for one or more locators. The locator parameter indicates the lowest locator number.
        """
        self.inWarp = False
        self.isShooting = False
        self.targetsAvailable = False
        self.online = True
        self.targetID = None
        self.turretTypeID = 0
        self.turretGroupID = 0
        if not hasattr(graphics, 'graphicFile'):
            log.LogError('New turret system got wrong initialization data, will use fallback: ' + str(graphics))
            turretPath = 'res:/dx9/model/turret/Special/FallbackTurret.red'
        else:
            turretPath = graphics.graphicFile
            if not turretPath.endswith('.red'):
                log.LogError('BSD data is pointing to an old turret, will use fallback: ' + str(graphics))
                turretPath = 'res:/dx9/model/turret/Special/FallbackTurret.red'
        self.turretSets = []
        for i in range(count):
            tSet = trinity.Load(turretPath)
            if tSet is None:
                continue
            if len(tSet.locatorName) == 0:
                tSet.locatorName = 'locator_turret_'
            elif tSet.locatorName[-1].isdigit():
                tSet.locatorName = tSet.locatorName[:-1]
            if locator < 0:
                tSet.slotNumber = i + 1
            else:
                tSet.slotNumber = locator
            self.turretSets.append(tSet)

        for turretSet in self.turretSets:
            effect = blue.recycler.RecycleOrLoad(turretSet.firingEffectResPath)
            if effect is not None:
                self.AddSoundToEffect(effect, turretSet)
                turretSet.firingEffect = effect
            else:
                log.LogError('Could not find firingeffect ' + turretSet.firingEffectResPath + ' for turret: ' + turretPath)

        return self.turretSets

    def AddSoundToEffect(self, effect, turretSet):
        if len(effect.stretch) < 1:
            return
        srcAudio = audio2.AudEmitter('effect_source_%s' % str(id(self)))
        destAudio = audio2.AudEmitter('effect_dest_%s' % str(id(self)))
        if turretSet.hasCyclingFiringPos:
            sndStretchList = effect.stretch
        else:
            sndStretchList = effect.stretch[:1]
        for sndStretch in sndStretchList:
            if sndStretch.stretchObject:
                sourceAudioLocation = sndStretch.stretchObject
            else:
                sourceAudioLocation = sndStretch.sourceObject
            if sourceAudioLocation:
                obs = trinity.TriObserverLocal()
                obs.front = (0.0, -1.0, 0.0)
                obs.observer = srcAudio
                del sourceAudioLocation.observers[:]
                sourceAudioLocation.observers.append(obs)
            if sndStretch.destObject:
                obs = trinity.TriObserverLocal()
                obs.front = (0.0, -1.0, 0.0)
                obs.observer = destAudio
                del sndStretch.destObject.observers[:]
                sndStretch.destObject.observers.append(obs)
            for eachSet in sndStretch.curveSets:
                for eachCurve in eachSet.curves:
                    if eachCurve.__typename__ == 'TriEventCurve':
                        if eachCurve.name == 'audioEventsSource':
                            eachCurve.eventListener = srcAudio
                        elif eachCurve.name == 'audioEventsDest':
                            eachCurve.eventListener = destAudio

    def GetTurretSet(self, index = 0):
        return self.turretSets[index]

    def GetTurretSets(self):
        return self.turretSets

    def Release(self):
        pass

    def SetTargetsAvailable(self, available):
        if self.targetsAvailable and not available:
            self.Rest()
        self.targetsAvailable = available

    def SetTarget(self, shipID, targetID):
        self.targetID = targetID
        targetBall = sm.GetService('michelle').GetBall(targetID)
        if targetBall is not None:
            if hasattr(targetBall, 'model'):
                for turretSet in self.turretSets:
                    turretSet.targetObject = targetBall.model

    def SetAmmoColorByTypeID(self, ammoTypeID):
        gfx = cfg.invtypes.GetIfExists(ammoTypeID).Graphic()
        if hasattr(gfx, 'ammoColor'):
            color = tuple(gfx.ammoColor)
            self.SetAmmoColor(color)

    def SetAmmoColor(self, color):
        if color is None:
            return
        for turretSet in self.turretSets:
            if turretSet.firingEffect is not None:
                for curve in turretSet.firingEffect.Find('trinity.TriColorCurve'):
                    if curve.name == 'Ammo':
                        curve.value = color

    def IsShooting(self):
        return self.isShooting

    def StartShooting(self, ammoGFXid = None):
        if self.inWarp:
            return
        for turretSet in self.turretSets:
            turretSet.EnterStateFiring()

        self.isShooting = True

    def StopShooting(self):
        for turretSet in self.turretSets:
            if self.inWarp:
                turretSet.EnterStateDeactive()
            elif self.targetsAvailable:
                turretSet.EnterStateTargeting()
            else:
                turretSet.EnterStateIdle()

        self.isShooting = False

    def Rest(self):
        if self.inWarp or not self.online:
            return
        for turretSet in self.turretSets:
            turretSet.EnterStateIdle()

    def Offline(self):
        if self.online == False:
            return
        self.online = False
        for turretSet in self.turretSets:
            turretSet.isOnline = False
            turretSet.EnterStateDeactive()

    def Online(self):
        if self.online:
            return
        self.online = True
        for turretSet in self.turretSets:
            turretSet.isOnline = True
            turretSet.EnterStateIdle()

    def Reload(self):
        for turretSet in self.turretSets:
            turretSet.EnterStateReloading()

    def EnterWarp(self):
        self.inWarp = True
        for turretSet in self.turretSets:
            turretSet.EnterStateDeactive()

    def ExitWarp(self):
        self.inWarp = False
        if self.online:
            for turretSet in self.turretSets:
                turretSet.EnterStateIdle()

    def TakeAim(self, targetID):
        if self.targetID != targetID:
            log.LogWarn('target ids mismatch!')
            return
        if not self.online:
            return
        for turretSet in self.turretSets:
            turretSet.EnterStateTargeting()

    def ApplyTurretPresetsByIDs(self, parentTypeID, turretTypeID):
        godma = sm.GetService('godma')
        turretFaction = 'None'
        if turretTypeID is not None:
            t = cfg.fsdTypeOverrides.Get(turretTypeID)
            turretFaction = getattr(t, 'sofFactionName', 'None')
        parentFaction = 'None'
        if parentTypeID is not None:
            t = cfg.invtypes.GetIfExists(parentTypeID)
            if t is not None:
                g = cfg.graphics.GetIfExists(t.graphicID)
                parentFaction = getattr(g, 'sofFactionName', 'None')
        log.LogInfo('changing turret preset with: shipfaction: ' + parentFaction + ' turretfaction:' + turretFaction)
        spaceObjectFactory = sm.GetService('sofService').spaceObjectFactory
        for turretSet in self.turretSets:
            spaceObjectFactory.SetupTurretMaterial(turretSet, parentFaction, turretFaction)

    @staticmethod
    def AddTurretToModel(model, turretGraphicsID, locatorID, count = 1):
        if model.__bluetype__ not in ('trinity.EveShip2', 'trinity.EveMobile'):
            log.LogError('Wrong object is trying to get turret attached due to wrong authored content! model:' + model.name + ' bluetype:' + model.__bluetype__)
            return
        graphics = cfg.graphics.GetIfExists(turretGraphicsID)
        newTurretSet = TurretSet()
        eveTurretSets = newTurretSet.Initialize(graphics, locatorID, None, count=count)
        for tSet in eveTurretSets:
            model.turretSets.append(tSet)

        return newTurretSet

    @staticmethod
    def FitTurret(model, parentTypeID, turretTypeID, locatorID, count = 1, online = True, checkSettings = True):
        to = cfg.invtypes.GetIfExists(turretTypeID)
        if to is None:
            return
        if checkSettings and not gfxsettings.Get(gfxsettings.UI_TURRETS_ENABLED):
            return
        groupID = to.groupID
        newTurretSet = None
        if model is None:
            log.LogError('FitTurret() called with NoneType, so there is no model to fit the turret to!')
            return
        if groupID not in const.turretModuleGroups:
            return
        if to.graphicID is not None:
            newTurretSet = TurretSet.AddTurretToModel(model, to.graphicID, locatorID, count=count)
            if newTurretSet is None:
                return
            newTurretSet.ApplyTurretPresetsByIDs(parentTypeID, turretTypeID)
            if not online:
                newTurretSet.Offline()
            newTurretSet.turretTypeID = turretTypeID
            newTurretSet.turretGroupID = groupID
            for eveTurretSet in newTurretSet.turretSets:
                eveTurretSet.laserMissBehaviour = groupID in LASER_MISS_BEHAVIOUR_GROUPS
                eveTurretSet.projectileMissBehaviour = groupID in PROJECTILE_MISS_BEHAVIOUR_GROUPS

        return newTurretSet

    @staticmethod
    def FitTurrets(shipID, model, checkSettings = True):
        """
        Fits all turrets for shipID to the model provided.
        Returns a dictionary of turretSets indexed by moduleID of all turrets 
        fitted to the ship.
        This method is block trapped, beacusae we acan't allow different threads
        to be adding and removing turrets at the same time.
        """
        with block_trap():
            if checkSettings and not gfxsettings.Get(gfxsettings.UI_TURRETS_ENABLED):
                return {}
            turretsFitted = {}
            modules = []
            if shipID == util.GetActiveShip():
                dogmaLocation = sm.GetService('clientDogmaIM').GetDogmaLocation()
                if not dogmaLocation.IsItemLoaded(shipID):
                    return {}
                dogmaLocation.LoadItem(shipID)
                ship = dogmaLocation.GetDogmaItem(shipID)
                modules = []
                for module in ship.GetFittedItems().itervalues():
                    if module.groupID in const.turretModuleGroups:
                        modules.append([module.itemID,
                         module.typeID,
                         module.flagID - const.flagHiSlot0 + 1,
                         module.IsOnline()])

                shipTypeID = ship.typeID
            else:
                slimItem = sm.StartService('michelle').GetBallpark().GetInvItem(shipID)
                if slimItem is not None:
                    moduleItems = slimItem.modules
                    modules = [ [module[0],
                     module[1],
                     module[2] - const.flagHiSlot0 + 1,
                     True] for module in moduleItems ]
                    shipTypeID = slimItem.typeID
            del model.turretSets[:]
            modules = sorted(modules, key=lambda x: x[2])
            locatorCounter = 1
            for moduleID, typeID, slot, isOnline in modules:
                slot = slot or locatorCounter
                ts = TurretSet.FitTurret(model, shipTypeID, typeID, slot, checkSettings=checkSettings, online=isOnline)
                if ts is not None:
                    turretsFitted[moduleID] = ts
                    locatorCounter += 1

            return turretsFitted

#Embedded file name: eve/client/script/parklife\turret.py
import service
import states as state

class TurretSvc(service.Service):
    __exportedcalls__ = {}
    __notifyevents__ = ['OnStateChange',
     'ProcessTargetChanged',
     'OnGodmaItemChange',
     'ProcessShipEffect',
     'ProcessActiveShipChanged',
     'OnChargeBeingLoadedToModule']
    __dependencies__ = []
    __guid__ = 'svc.turret'
    __servicename__ = 'turret'
    __displayname__ = 'Turret Service'

    def Run(self, memStream = None):
        self.LogInfo('Starting Turret Service')

    def Startup(self):
        pass

    def Stop(self, memStream = None):
        pass

    def OnStateChange(self, itemID, flag, true, *args):
        """ 
        We want our turrets to track the active target as long as we're not shooting
        something else. 
        """
        if flag == state.targeting:
            pass
        if flag != state.activeTarget:
            return
        targets = sm.GetService('target').GetTargets()
        if len(targets) == 0:
            return
        ship = sm.GetService('michelle').GetBall(eve.session.shipid)
        for turretSet in ship.turrets:
            if not turretSet.IsShooting():
                turretSet.SetTarget(eve.session.shipid, itemID)
                turretSet.TakeAim(itemID)

    def OnGodmaItemChange(self, item, change):
        ball = sm.GetService('michelle').GetBall(eve.session.shipid)
        if ball is None:
            return
        targetSvc = sm.GetService('target')
        if targetSvc is None:
            return
        if item.groupID in const.turretModuleGroups:
            ball.UnfitHardpoints()
            ball.FitHardpoints()
            for turretSet in ball.turrets:
                if len(targetSvc.targets) > 0:
                    turretSet.SetTargetsAvailable(True)
                    turretSet.SetTarget(None, targetSvc.GetActiveTargetID())

    def ProcessTargetChanged(self, what, tid, reason):
        targets = sm.GetService('target').GetTargets()
        ship = sm.GetService('michelle').GetBall(eve.session.shipid)
        if ship is None:
            return
        if not hasattr(ship, 'turrets'):
            return
        for turretSet in ship.turrets:
            turretSet.SetTargetsAvailable(len(targets) != 0)

    def ProcessShipEffect(self, godmaStm, effectState):
        if effectState.effectName == 'online':
            ship = sm.GetService('michelle').GetBall(eve.session.shipid)
            if ship is not None:
                turret = None
                for moduleID in ship.modules:
                    if moduleID == effectState.itemID:
                        turret = ship.modules[moduleID]

                if turret is not None:
                    if effectState.active:
                        turret.Online()
                    else:
                        turret.Offline()

    def ProcessActiveShipChanged(self, shipID, oldShipID):
        if session.solarsystemid is not None:
            bp = sm.GetService('michelle').GetBallpark()
            try:
                ship = bp.balls[shipID]
            except KeyError:
                return

            try:
                ship.UnfitHardpoints()
                ship.FitHardpoints()
            except AttributeError:
                self.LogInfo("Ship didn't have attribute fitted. Probably still being initialized", shipID)

    def OnChargeBeingLoadedToModule(self, moduleIDs, chargeTypeID, reloadTime):
        ship = sm.GetService('michelle').GetBall(eve.session.shipid)
        if ship is not None:
            for launcherID in moduleIDs:
                if launcherID in ship.modules:
                    turret = ship.modules[launcherID]
                    if turret is not None:
                        turret.Reload()

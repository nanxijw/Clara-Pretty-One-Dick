#Embedded file name: eve/client/script/dogma\clientDogmaLocation.py
import dogmax
import sys
import weakref
from inventorycommon.util import IsShipFittingFlag
import util
import math
import uix
import log
import moniker
import blue
import uiutil
import carbonui.const as uiconst
import uthread
import itertools
import localization
import telemetry
from collections import defaultdict
from dogma.attributes.format import GetFormatAndValue
from dogma.effects.environment import Environment
GROUPALL_THROTTLE_TIMER = 2 * const.SEC

class DogmaLocation(dogmax.BaseDogmaLocation):
    """
        This is a local simulation of our active ship. When in a station not in a ship we need
        to still show attributes and be able to fit the ship. The server won't tell us anything
        useful as the character is not in the same location as the ship(probably not even the 
        same node)
    """
    __guid__ = 'dogmax.DogmaLocation'
    __notifyevents__ = ['OnModuleAttributeChanges', 'OnWeaponBanksChanged', 'OnWeaponGroupDestroyed']

    def __init__(self, broker):
        dogmax.BaseDogmaLocation.__init__(self, broker)
        self.instanceCache = {}
        self.scatterAttributeChanges = True
        self.dogmaStaticMgr = sm.GetService('clientDogmaStaticSvc')
        self.remoteDogmaLM = None
        self.godma = sm.GetService('godma')
        self.stateMgr = self.godma.GetStateManager()
        self.fakeInstanceRow = None
        self.items = {}
        self.nextItemID = 0
        self.effectCompiler = sm.GetService('clientEffectCompiler')
        self.shipID = None
        self.LoadItem(session.charid)
        self.lastGroupAllRequest = None
        self.lastUngroupAllRequest = None
        self.shipIDBeingDisembarked = None
        sm.RegisterNotify(self)

    def GetMatchingAmmo(self, shipID, itemID):
        dogmaItem = self.dogmaItems[itemID]
        ammoInfoByTypeID = defaultdict(lambda : util.KeyVal(singletons=[], nonSingletons=[]))
        validGroupIDs = self.dogmaStaticMgr.GetValidChargeGroupsForType(dogmaItem.typeID)
        GetTypeAttribute = self.dogmaStaticMgr.GetTypeAttribute
        preferredChargeSize = GetTypeAttribute(dogmaItem.typeID, const.attributeChargeSize)
        for item in self.broker.invCache.GetInventoryFromId(shipID).List(const.flagCargo):
            if validGroupIDs is not None and item.groupID not in validGroupIDs:
                continue
            if preferredChargeSize is not None and GetTypeAttribute(item.typeID, const.attributeChargeSize) != preferredChargeSize:
                continue
            if item.singleton:
                ammoInfoByTypeID[item.typeID].singletons.append(item)
            else:
                ammoInfoByTypeID[item.typeID].nonSingletons.append(item)

        return ammoInfoByTypeID

    def AddToMenuFromAmmoInfo(self, itemID, chargeTypeID, ammoInfo, minimumAmmoNeeded, labels):
        menu = []
        if sum((item.stacksize for item in ammoInfo.singletons)) >= minimumAmmoNeeded:
            text = uiutil.MenuLabel(labels[0], {'typeID': chargeTypeID})
            menu.append((text, self.LoadChargeToModule, (itemID, chargeTypeID, ammoInfo.singletons)))
        noOfNonSingletons = sum((item.stacksize for item in ammoInfo.nonSingletons))
        if noOfNonSingletons >= minimumAmmoNeeded:
            text = uiutil.MenuLabel(labels[1], {'typeID': chargeTypeID,
             'sumqty': noOfNonSingletons})
            menu.append((text, self.LoadChargeToModule, (itemID, chargeTypeID, ammoInfo.nonSingletons)))
        return menu

    def GetAmmoMenu(self, shipID, itemID, existingChargeID, roomForReload):
        usedChargeType = self.godma.GetStateManager().GetAmmoTypeForModule(itemID)
        ammoInfoByTypeID = self.GetMatchingAmmo(shipID, itemID)
        try:
            minimumAmmoNeeded = len(self.GetModulesInBank(shipID, itemID))
        except TypeError:
            minimumAmmoNeeded = 1

        menu = []
        if usedChargeType in ammoInfoByTypeID and roomForReload:
            ammoInfo = ammoInfoByTypeID[usedChargeType]
            menuItems = self.AddToMenuFromAmmoInfo(itemID, usedChargeType, ammoInfo, minimumAmmoNeeded, ('UI/Inflight/ModuleRacks/ReloadUsed', 'UI/Inflight/ModuleRacks/Reload'))
            if menuItems:
                menu.extend(menuItems)
                menu.append((uiutil.MenuLabel('UI/Inflight/ModuleRacks/ReloadAll'), uicore.cmd.CmdReloadAmmo))
        if existingChargeID:
            menu.append((uiutil.MenuLabel('UI/Inflight/ModuleRacks/UnloadToCargo'), self.UnloadChargeToContainer, (shipID,
              existingChargeID,
              (shipID,),
              const.flagCargo)))
        otherChargeMenu = []
        for chargeTypeID in localization.util.Sort(ammoInfoByTypeID.keys(), key=lambda x: cfg.invtypes.Get(x).typeName):
            ammoInfo = ammoInfoByTypeID[chargeTypeID]
            if chargeTypeID == usedChargeType:
                continue
            otherChargeMenu.extend(self.AddToMenuFromAmmoInfo(itemID, chargeTypeID, ammoInfo, minimumAmmoNeeded, ('UI/Inflight/ModuleRacks/AmmoTypeAndStatus', 'UI/Inflight/ModuleRacks/AmmoTypeAndQuantity')))

        menu.extend(otherChargeMenu)
        return menu

    @telemetry.ZONE_METHOD
    def MakeShipActive(self, shipID, shipState = None):
        """
            We thread this out because we potentially need to wait for two things.
            1. We need to wait until the session is safe. This is called when we actually
               change ships so we might be in a middle of a session change
            2. The inventory item of the ship might not be ready as we've just created the
               ship, like when we are leaving our active ship and creating a pod
        """
        uthread.pool('MakeShipActive', self._MakeShipActive, shipID, shipState)

    @telemetry.ZONE_METHOD
    def _MakeShipActive(self, shipID, shipState):
        self.LoadItem(session.charid)
        uthread.Lock(self, 'makeShipActive')
        self.shipIDBeingDisembarked = self.shipID
        try:
            if self.shipID == shipID:
                return
            while not session.IsItSafe():
                self.LogInfo('MakeShipActive - session is mutating. Sleeping for 250ms')
                blue.pyos.synchro.SleepSim(250)

            if shipID is None:
                log.LogTraceback('Unexpectedly got shipID = None')
                return
            charItem = self.dogmaItems[session.charid]
            oldShipID = charItem.locationID
            if oldShipID == shipID:
                return
            self.UpdateRemoteDogmaLocation()
            oldShipID = self.shipID
            self.shipID = shipID
            if shipState is not None:
                self.instanceCache, self.instanceFlagQuantityCache, self.wbData = shipState
            else:
                try:
                    self.instanceCache, self.instanceFlagQuantityCache, self.wbData = self.remoteShipMgr.ActivateShip(shipID, oldShipID)
                except Exception:
                    self.shipID = oldShipID
                    raise

            charItems = charItem.GetFittedItems()
            self.scatterAttributeChanges = False
            try:
                self.LoadItem(self.shipID)
                if oldShipID is not None:
                    self.UnfitItemFromLocation(oldShipID, session.charid)
                for skill in charItems.itervalues():
                    for effectID in skill.activeEffects.keys():
                        self.StopEffect(effectID, skill.itemID)

                if shipID is not None:
                    self.OnCharacterEmbarkation(session.charid, shipID, switching=oldShipID is not None)
                    for skill in charItems.itervalues():
                        self.StartPassiveEffects(skill.itemID, skill.typeID)

                    shipInv = self.broker.invCache.GetInventoryFromId(shipID, locationID=session.stationid2)
                    self.LoadShipFromInventory(shipID, shipInv)
                    self.SetWeaponBanks(self.shipID, self.wbData)
                    sm.ChainEvent('ProcessActiveShipChanged', shipID, oldShipID)
                    self.UnloadItem(oldShipID)
            finally:
                self.scatterAttributeChanges = True

            self.ClearInstanceCache()
        finally:
            self.shipIDBeingDisembarked = None
            uthread.UnLock(self, 'makeShipActive')

    def WaitForShip(self):
        startTime = blue.os.GetWallclockTime()
        while self.shipIDBeingDisembarked is not None and blue.os.TimeDiffInMs(startTime, blue.os.GetWallclockTime()) < 2000:
            blue.pyos.synchro.Sleep(100)

    def ClearInstanceCache(self):
        self.instanceCache = {}
        self.instanceFlagQuantityCache = {}
        self.wbData = None

    @telemetry.ZONE_METHOD
    def UpdateRemoteDogmaLocation(self):
        """
            If we are located somewhere in a station (worldspace or captains quarters)
            we can assume that the ship we are interested in in located in the station
            dogmaLocation
        """
        if session.stationid2 is not None:
            self.remoteDogmaLM = moniker.GetStationDogmaLocation()
            self.remoteShipMgr = moniker.GetStationShipAccess()
        else:
            self.remoteDogmaLM = moniker.CharGetDogmaLocation()
            self.remoteShipMgr = moniker.GetShipAccess()

    @telemetry.ZONE_METHOD
    def OnModuleAttributeChanges(self, changes):
        changes.sort(key=lambda change: change[4])
        for change in changes:
            try:
                eventName, ownerID, itemID, attributeID, time, newValue, oldValue = change
                if attributeID == const.attributeQuantity:
                    if isinstance(itemID, tuple) and not self.IsItemLoaded(itemID[0]):
                        self.LogWarn("got an module attribute change and the item wasn't loaded", itemID)
                        continue
                    if newValue == 0:
                        self.SetAttributeValue(itemID, const.attributeQuantity, newValue)
                        self.UnfitItemFromLocation(itemID[0], itemID)
                        self.UnloadItem(itemID)
                    else:
                        if itemID != self.GetSubLocation(itemID[0], itemID[1]):
                            self.FitItemToLocation(itemID[0], itemID, itemID[1])
                        self.dogmaItems[itemID].attributes[attributeID] = newValue
                        self.SetAttributeValue(itemID, const.attributeQuantity, newValue)
                elif attributeID == const.attributeIsOnline:
                    if not self.IsItemLoaded(itemID):
                        continue
                    if newValue == self.GetAttributeValue(itemID, const.attributeIsOnline):
                        continue
                    if newValue == 0:
                        self.StopEffect(const.effectOnline, itemID)
                    else:
                        self.Activate(itemID, const.effectOnline)
                elif attributeID in (const.attributeSkillPoints, const.attributeDamage):
                    if not self.IsItemLoaded(itemID):
                        continue
                    dogmaItem = self.dogmaItems[itemID]
                    dogmaItem.attributes[attributeID] = newValue
                    self.SetAttributeValue(itemID, attributeID, newValue)
            except Exception:
                log.LogException('OnModuleAttributeChanges::Unexpected exception')
                sys.exc_clear()

    @telemetry.ZONE_METHOD
    def LoadShipFromInventory(self, shipID, shipInv):
        subSystems = set()
        rigs = set()
        hiSlots = set()
        medSlots = set()
        lowSlots = set()
        drones = set()
        for item in shipInv.List():
            if not (IsShipFittingFlag(item.flagID) or item.flagID == const.flagDroneBay):
                continue
            self.items[item.itemID] = item
            if item.categoryID == const.categorySubSystem:
                subSystems.add(item)
            elif const.flagRigSlot0 <= item.flagID <= const.flagRigSlot7:
                rigs.add(item)
            elif const.flagHiSlot0 <= item.flagID <= const.flagHiSlot7:
                hiSlots.add(item)
            elif const.flagMedSlot0 <= item.flagID <= const.flagMedSlot7:
                medSlots.add(item)
            elif const.flagLoSlot0 <= item.flagID <= const.flagLoSlot7:
                lowSlots.add(item)
            elif item.flagID == const.flagDroneBay:
                drones.add(item.itemID)

        for item in itertools.chain(subSystems, rigs, lowSlots, medSlots, hiSlots):
            self.FitItemToLocation(shipID, item.itemID, item.flagID)

        for flagID, dbrow in self.instanceFlagQuantityCache.get(shipID, {}).iteritems():
            subLocation = (dbrow[0], dbrow[1], dbrow[2])
            if not self.IsItemLoaded(subLocation):
                self.FitItemToLocation(shipID, subLocation, flagID)

        for droneID in drones:
            self.FitItemToLocation(shipID, droneID, const.flagDroneBay)

    @telemetry.ZONE_METHOD
    def FitItemToLocation(self, locationID, itemID, flagID):
        if locationID not in (self.shipID, session.charid):
            return
        dogmax.BaseDogmaLocation.FitItemToLocation(self, locationID, itemID, flagID)

    @telemetry.ZONE_METHOD
    def UnfitItemFromLocation(self, locationID, itemID, flushEffects = False):
        dogmax.BaseDogmaLocation.UnfitItemFromLocation(self, locationID, itemID, flushEffects)
        if locationID not in self.checkShipOnlineModulesPending:
            self.checkShipOnlineModulesPending.add(locationID)
            uthread.pool('LocationManager::CheckShipOnlineModules', self.CheckShipOnlineModules, locationID)

    @telemetry.ZONE_METHOD
    def GetChargeNonDB(self, shipID, flagID):
        for itemID, fittedItem in self.dogmaItems[shipID].GetFittedItems().iteritems():
            if isinstance(itemID, tuple):
                continue
            if fittedItem.flagID != flagID:
                continue
            if fittedItem.categoryID == const.categoryCharge:
                return fittedItem

    @telemetry.ZONE_METHOD
    def GetSubSystemInFlag(self, shipID, flagID):
        """
            We can assume that we only have one sub system in the subsystem flag
        """
        shipInv = self.broker.invCache.GetInventoryFromId(shipID, locationID=session.stationid2)
        items = shipInv.List(flagID)
        if len(items) == 0:
            return None
        else:
            return self.dogmaItems[items[0].itemID]

    @telemetry.ZONE_METHOD
    def GetItem(self, itemID):
        if itemID == self.shipID:
            return self.broker.invCache.GetInventoryFromId(self.shipID, locationID=session.stationid2).GetItem()
        try:
            return self.items[itemID]
        except KeyError:
            sys.exc_clear()

        return self.godma.GetItem(itemID)

    @telemetry.ZONE_METHOD
    def GetCharacter(self, itemID, flush):
        return self.GetItem(itemID)

    @telemetry.ZONE_METHOD
    def Activate(self, itemID, effectID):
        dogmaItem = self.dogmaItems[itemID]
        envInfo = dogmaItem.GetEnvironmentInfo()
        env = Environment(envInfo.itemID, envInfo.charID, envInfo.shipID, envInfo.targetID, envInfo.otherID, effectID, weakref.proxy(self), None)
        env.dogmaLM = self
        self.StartEffect(effectID, itemID, env)

    @telemetry.ZONE_METHOD
    def PostStopEffectAction(self, effectID, dogmaItem, activationInfo, *args):
        dogmax.BaseDogmaLocation.PostStopEffectAction(self, effectID, dogmaItem, activationInfo, *args)
        if effectID == const.effectOnline:
            shipID = dogmaItem.locationID
            if shipID not in self.checkShipOnlineModulesPending:
                self.checkShipOnlineModulesPending.add(shipID)
                uthread.pool('LocationManager::CheckShipOnlineModules', self.CheckShipOnlineModules, shipID)

    @telemetry.ZONE_METHOD
    def GetInstance(self, item):
        try:
            return self.instanceCache[item.itemID]
        except KeyError:
            sys.exc_clear()

        instanceRow = [item.itemID]
        godmaItem = self.broker.godma.GetItem(item.itemID)
        for attributeID in self.GetAttributesByIndex().itervalues():
            instanceRow.append(getattr(godmaItem, self.dogmaStaticMgr.attributes[attributeID].attributeName, 0))

        return instanceRow

    @telemetry.ZONE_METHOD
    def GetAttributesByIndex(self):
        return const.dgmAttributesByIdx

    def GetAccurateAttributeValue(self, itemID, attributeID, *args):
        if session.solarsystemid is None:
            return self.GetAttributeValue(itemID, attributeID)
        else:
            return self.GetGodmaAttributeValue(itemID, attributeID)

    @telemetry.ZONE_METHOD
    def CheckSkillRequirements(self, charID, skillID, errorMsgName):
        skillItem = self.dogmaItems[skillID]
        self.CheckSkillRequirementsForType(skillItem.typeID, errorMsgName)

    def _GetMissingSkills(self, typeID):
        skillSvc = sm.GetService('skills')
        missingSkills = {}
        for requiredSkillTypeID, requiredSkillLevel in self.dogmaStaticMgr.GetRequiredSkills(typeID).iteritems():
            requiredSkill = skillSvc.HasSkill(requiredSkillTypeID)
            if requiredSkill is None:
                missingSkills[requiredSkillTypeID] = requiredSkillLevel
            elif self.GetAttributeValue(requiredSkill.itemID, const.attributeSkillLevel) < requiredSkillLevel:
                missingSkills[requiredSkillTypeID] = requiredSkillLevel

        return missingSkills

    @telemetry.ZONE_METHOD
    def CheckSkillRequirementsForType(self, typeID, errorMsgName):
        missingSkills = self._GetMissingSkills(typeID)
        if len(missingSkills) > 0:
            nameList = []
            for skillTypeID, requiredSkillLevel in missingSkills.iteritems():
                nameList.append(localization.GetByLabel('UI/SkillQueue/Skills/SkillNameAndLevel', skill=skillTypeID, amount=requiredSkillLevel))

            raise UserError(errorMsgName, {'requiredSkills': localization.formatters.FormatGenericList(nameList),
             'item': typeID,
             'skillCount': len(nameList)})
        return missingSkills

    @telemetry.ZONE_METHOD
    def LoadItemsInLocation(self, itemID):
        if itemID == session.charid:
            char = self.godma.GetItem(itemID)
            for item in itertools.chain(char.skills.itervalues(), char.implants, char.boosters):
                self.LoadItem(item.itemID)

    def GetSensorStrengthAttribute(self, shipID):
        maxAttributeID = None
        maxValue = None
        for attributeID in (const.attributeScanGravimetricStrength,
         const.attributeScanLadarStrength,
         const.attributeScanMagnetometricStrength,
         const.attributeScanRadarStrength):
            val = self.GetAttributeValue(shipID, attributeID)
            if val > maxValue:
                maxValue, maxAttributeID = val, attributeID

        return (maxAttributeID, maxValue)

    def UnfitItem(self, itemID):
        if itemID == session.charid:
            self.UnboardShip(session.charid)
        else:
            locationID = self.dogmaItems[itemID].locationID
            self.UnfitItemFromLocation(locationID, itemID)
            self.UnloadItem(itemID)
        if itemID in self.items:
            del self.items[itemID]
        if itemID in self.instanceCache:
            del self.instanceCache[itemID]

    def UnboardShip(self, charID):
        char = self.dogmaItems[charID]
        charItems = char.GetFittedItems()
        for skill in charItems.itervalues():
            for effectID in skill.activeEffects.keys():
                self.StopEffect(effectID, skill.itemID)

        self.UnfitItemFromLocation(self.shipID, charID)
        oldShipID = self.shipID
        self.shipID = None
        sm.ChainEvent('ProcessActiveShipChanged', None, oldShipID)

    def FitItem(self, item):
        self.items[item.itemID] = item
        self.FitItemToLocation(item.locationID, item.itemID, item.flagID)
        if self.dogmaStaticMgr.TypeHasEffect(item.typeID, const.effectOnline):
            try:
                self.OnlineModule(item.itemID)
            except UserError as e:
                if e.msg != 'EffectAlreadyActive2':
                    uthread.pool('FitItem::RaiseUserError', eve.Message, *e.args)
            except Exception:
                log.LogException('Raised during OnlineModule')

    def OnItemChange(self, item, change):
        wasFitted = item.itemID in self.dogmaItems
        isFitted = self.IsFitted(item)
        if wasFitted and not isFitted:
            if isinstance(item.itemID, tuple):
                pass
            elif item.categoryID == const.categoryDrone:
                self.UnfitItemFromLocation(self.shipID, item.itemID)
                self.UnloadItem(item.itemID)
            else:
                self.UnfitItem(item.itemID)
        if not wasFitted and isFitted:
            try:
                self.FitItem(item)
            except Exception:
                log.LogException('OnItemChange unexpectedly failed fitting item %s: (%s)' % (item.itemID, change))
                raise

        if wasFitted and isFitted and const.ixFlag in change:
            self.dogmaItems[item.itemID].flagID = item.flagID
        if isFitted and const.ixStackSize in change:
            self.SetAttributeValue(item.itemID, const.attributeQuantity, item.stacksize)
        if self.scatterAttributeChanges:
            sm.ScatterEvent('OnDogmaItemChange', item, change)
        self.items[item.itemID] = item

    def IsFitted(self, item):
        """
        Checks if item is fitted to ship or in special location and its quantity.
        """
        if item.locationID not in (self.shipID, session.charid):
            return False
        if not IsShipFittingFlag(item.flagID) and item.flagID not in (const.flagDroneBay,
         const.flagSkill,
         const.flagSkillInTraining,
         const.flagImplant,
         const.flagBooster):
            return False
        if item[const.ixStackSize] <= 0:
            return False
        return True

    def OnAttributeChanged(self, attributeID, itemKey, value = None, oldValue = None):
        value = dogmax.BaseDogmaLocation.OnAttributeChanged(self, attributeID, itemKey, value=value, oldValue=oldValue)
        if self.scatterAttributeChanges:
            sm.ScatterEvent('OnDogmaAttributeChanged', self.shipID, itemKey, attributeID, value)

    def GetShip(self):
        return self.dogmaItems[self.shipID]

    def TryFit(self, item, flagID):
        shipID = util.GetActiveShip()
        shipInv = self.broker.invCache.GetInventoryFromId(shipID, locationID=session.stationid2)
        shipInv.Add(item.itemID, item.locationID, qty=1, flag=flagID)

    def GetQuantity(self, itemID):
        if isinstance(itemID, tuple):
            return self.GetAttributeValue(itemID, const.attributeQuantity)
        return self.GetItem(itemID).stacksize

    def GetSublocations(self, shipID):
        ret = set()
        for subLocation in self.dogmaItems[shipID].subLocations.itervalues():
            ret.add(self.dogmaItems[subLocation])

        return ret

    def GetSlotOther(self, shipID, flagID):
        for item in self.dogmaItems[shipID].GetFittedItems().itervalues():
            if item.flagID == flagID and item.categoryID == const.categoryModule:
                return item.itemID

    def GetCapacity(self, shipID, attributeID, flagID):
        ret = self.broker.invCache.GetInventoryFromId(self.shipID, locationID=session.stationid2).GetCapacity(flagID)
        if const.flagLoSlot0 <= flagID <= const.flagHiSlot7:
            shipDogmaItem = self.dogmaItems[shipID]
            subLocation = shipDogmaItem.subLocations.get(flagID, None)
            if subLocation is None:
                used = ret.used
            else:
                used = self.GetAttributeValue(subLocation, const.attributeQuantity) * cfg.invtypes.Get(subLocation[2]).volume
            moduleID = self.GetSlotOther(shipID, flagID)
            if moduleID is None:
                capacity = 0
            else:
                capacity = self.GetAttributeValue(moduleID, const.attributeCapacity)
            return util.KeyVal(capacity=capacity, used=used)
        return ret

    def CapacitorSimulator(self, shipID):
        dogmaItem = self.dogmaItems[shipID]
        capacitorCapacity = self.GetAttributeValue(shipID, const.attributeCapacitorCapacity)
        rechargeTime = self.GetAttributeValue(shipID, const.attributeRechargeRate)
        modules = []
        totalCapNeed = 0
        for moduleID, module in dogmaItem.GetFittedItems().iteritems():
            if not module.IsOnline():
                continue
            try:
                defaultEffectID = self.dogmaStaticMgr.GetDefaultEffect(module.typeID)
            except KeyError:
                defaultEffectID = None
                sys.exc_clear()

            if defaultEffectID is None:
                continue
            defaultEffect = self.dogmaStaticMgr.effects[defaultEffectID]
            durationAttributeID = defaultEffect.durationAttributeID
            dischargeAttributeID = defaultEffect.dischargeAttributeID
            if durationAttributeID is None or dischargeAttributeID is None:
                continue
            duration = self.GetAttributeValue(moduleID, durationAttributeID)
            capNeed = self.GetAttributeValue(moduleID, dischargeAttributeID)
            modules.append([capNeed, long(duration * const.dgmTauConstant), 0])
            totalCapNeed += capNeed / duration

        rechargeRateAverage = capacitorCapacity / rechargeTime
        peakRechargeRate = 2.5 * rechargeRateAverage
        tau = rechargeTime / 5
        TTL = None
        if totalCapNeed > peakRechargeRate:
            TTL = self.RunSimulation(capacitorCapacity, rechargeTime, modules)
            loadBalance = 0
        else:
            c = 2 * capacitorCapacity / tau
            k = totalCapNeed / c
            exponent = (1 - math.sqrt(1 - 4 * k)) / 2
            if exponent == 0:
                loadBalance = 1
            else:
                t = -math.log(exponent) * tau
                loadBalance = (1 - math.exp(-t / tau)) ** 2
        return (peakRechargeRate,
         totalCapNeed,
         loadBalance,
         TTL)

    def RunSimulation(self, capacitorCapacity, rechargeRate, modules):
        """
            This runs activations by simulating the cap consumption
        """
        capacitor = capacitorCapacity
        tauThingy = float(const.dgmTauConstant) * (rechargeRate / 5.0)
        currentTime = nextTime = 0L
        while capacitor > 0.0 and nextTime < const.DAY:
            capacitor = (1.0 + (math.sqrt(capacitor / capacitorCapacity) - 1.0) * math.exp((currentTime - nextTime) / tauThingy)) ** 2 * capacitorCapacity
            currentTime = nextTime
            nextTime = const.DAY
            for data in modules:
                if data[2] == currentTime:
                    data[2] += data[1]
                    capacitor -= data[0]
                nextTime = min(nextTime, data[2])

        if capacitor > 0.0:
            return const.DAY
        return currentTime

    def OnlineModule(self, moduleID):
        """
            We first try to online the module locally. If that succeeds we ask the server to do it. That
            however if the server fails we need to offline it again
        """
        self.Activate(moduleID, const.effectOnline)
        dogmaItem = self.dogmaItems[moduleID]
        try:
            self.remoteDogmaLM.SetModuleOnline(dogmaItem.locationID, moduleID)
        except UserError as e:
            if e.msg != 'EffectAlreadyActive2':
                self.StopEffect(const.effectOnline, moduleID)
                raise
        except Exception:
            self.StopEffect(const.effectOnline, moduleID)
            raise

    def OfflineModule(self, moduleID):
        """
            We first try to offline the module locally. If that succeeds we ask the server to do it. That
            however if the server fails we need to online it again
        """
        dogmaItem = self.dogmaItems[moduleID]
        self.StopEffect(const.effectOnline, moduleID)
        if dogmaItem.locationID != self.shipIDBeingDisembarked:
            try:
                self.remoteDogmaLM.TakeModuleOffline(dogmaItem.locationID, moduleID)
            except Exception:
                self.Activate(moduleID, const.effectOnline)
                raise

    def GetDragData(self, itemID):
        """
            Get the drag data for the item. could of course gotten this through invCache
            but this is the only place where it's tracked by itemID
        """
        if itemID in self.items:
            return [uix.GetItemData(self.items[itemID], 'icons')]
        dogmaItem = self.dogmaItems[itemID]
        data = uiutil.Bunch()
        data.__guid__ = 'listentry.InvItem'
        data.item = util.KeyVal(itemID=dogmaItem.itemID, typeID=dogmaItem.typeID, groupID=dogmaItem.groupID, categoryID=dogmaItem.categoryID, flagID=dogmaItem.flagID, ownerID=dogmaItem.ownerID, locationID=dogmaItem.locationID, stacksize=self.GetAttributeValue(itemID, const.attributeQuantity))
        data.rec = data.item
        data.itemID = itemID
        data.viewMode = 'icons'
        return [data]

    def GetDisplayAttributes(self, itemID, attributes):
        ret = {}
        dogmaItem = self.dogmaItems[itemID]
        for attributeID in itertools.chain(dogmaItem.attributeCache, dogmaItem.attributes, attributes):
            if attributeID == const.attributeVolume:
                continue
            ret[attributeID] = self.GetAttributeValue(itemID, attributeID)

        return ret

    def LinkWeapons(self, shipID, toID, fromID, merge = True):
        """
            There are three ways we can link the weapons.
            1. Standard link. One module is linked to other, either in a group or they
               form one
            2. Both modules are in a group and we merge the groups
            3. Both modules are in a group and we peel one from one group and add it
               to the other group
        """
        if toID == fromID:
            return
        toItem = self.dogmaItems[toID]
        fromItem = self.dogmaItems[fromID]
        for item in (toItem, fromItem):
            if not item.IsOnline():
                raise UserError('CantLinkModuleNotOnline')

        if toItem.typeID != fromItem.typeID:
            self.LogInfo('LinkWeapons::Modules not of same type', toItem, fromItem)
            return
        if toItem.groupID not in const.dgmGroupableGroupIDs:
            self.LogInfo('group not groupable', toItem, fromItem)
            return
        if shipID is None or shipID != fromItem.locationID:
            log.LogTraceback('LinkWeapons::Modules not located in the same place')
        masterID = self.GetMasterModuleID(shipID, toID)
        if not masterID:
            masterID = toID
        slaveID = self.IsInWeaponBank(shipID, fromID)
        if slaveID:
            if merge:
                info = self.remoteDogmaLM.MergeModuleGroups(shipID, masterID, slaveID)
            else:
                info = self.remoteDogmaLM.PeelAndLink(shipID, masterID, slaveID)
        else:
            info = self.remoteDogmaLM.LinkWeapons(shipID, masterID, fromID)
        self.OnWeaponBanksChanged(shipID, info)

    def UngroupModule(self, shipID, moduleID):
        slaveID = self.remoteDogmaLM.UnlinkModule(shipID, moduleID)
        self.slaveModulesByMasterModule[shipID][moduleID].remove(slaveID)
        if not self.slaveModulesByMasterModule[shipID][moduleID]:
            del self.slaveModulesByMasterModule[shipID][moduleID]
        self.SetGroupNumbers(shipID)
        sm.ScatterEvent('OnRefreshModuleBanks')
        return slaveID

    def UnlinkAllWeapons(self, shipID):
        info = self.remoteDogmaLM.UnlinkAllModules(shipID)
        self.OnWeaponBanksChanged(shipID, info)
        self.lastUngroupAllRequest = blue.os.GetSimTime()

    def LinkAllWeapons(self, shipID):
        info = self.remoteDogmaLM.LinkAllWeapons(shipID)
        self.OnWeaponBanksChanged(shipID, info)
        self.lastGroupAllRequest = blue.os.GetSimTime()

    def GetGroupAllOpacity(self, attributeName):
        lastRequest = getattr(self, attributeName)
        if lastRequest is None:
            return 1.0
        timeDiff = blue.os.GetSimTime() - lastRequest
        waitTime = min(GROUPALL_THROTTLE_TIMER, GROUPALL_THROTTLE_TIMER - timeDiff)
        opacity = max(0, 1 - float(waitTime) / GROUPALL_THROTTLE_TIMER)
        return opacity

    def IsInWeaponBank(self, shipID, itemID):
        """
            Checks if the module is in a weapon bank, and if it is the masterID is returned
        """
        slaveModulesByMasterModule = self.slaveModulesByMasterModule.get(shipID, {})
        if itemID in slaveModulesByMasterModule:
            return itemID
        masterID = self.GetMasterModuleID(shipID, itemID)
        if masterID is not None:
            return masterID
        return False

    def GetGroupableTypes(self, shipID):
        groupableTypes = defaultdict(lambda : 0)
        try:
            dogmaItem = self.dogmaItems[shipID]
        except KeyError:
            self.LogInfo('GetGroupableTypes - called before I was ready', shipID)
        else:
            for fittedItem in dogmaItem.GetFittedItems().itervalues():
                if not const.flagHiSlot0 <= fittedItem.flagID <= const.flagHiSlot7:
                    continue
                if fittedItem.groupID not in const.dgmGroupableGroupIDs:
                    continue
                if not fittedItem.IsOnline():
                    continue
                groupableTypes[fittedItem.typeID] += 1

        return groupableTypes

    def CanGroupAll(self, shipID):
        groupableTypes = self.GetGroupableTypes(shipID)
        groups = {}
        dogmaItem = self.dogmaItems[shipID]
        for fittedItem in dogmaItem.GetFittedItems().itervalues():
            if fittedItem.groupID not in const.dgmGroupableGroupIDs:
                continue
            if not fittedItem.IsOnline():
                continue
            if not self.IsInWeaponBank(shipID, fittedItem.itemID) and groupableTypes[fittedItem.typeID] > 1:
                return True
            masterID = self.GetMasterModuleID(shipID, fittedItem.itemID)
            if masterID is None:
                masterID = fittedItem.itemID
            if fittedItem.typeID not in groups:
                groups[fittedItem.typeID] = masterID
            elif groups[fittedItem.typeID] != masterID:
                return True

        return False

    def DestroyWeaponBank(self, shipID, itemID):
        self.remoteDogmaLM.DestroyWeaponBank(shipID, itemID)
        self.OnWeaponGroupDestroyed(shipID, itemID)

    def SetWeaponBanks(self, shipID, data):
        dogmax.BaseDogmaLocation.SetWeaponBanks(self, shipID, data)
        self.SetGroupNumbers(shipID)

    def OnWeaponBanksChanged(self, shipID, info):
        self.SetWeaponBanks(shipID, info)
        sm.ScatterEvent('OnRefreshModuleBanks')

    def OnWeaponGroupDestroyed(self, shipID, itemID):
        del self.slaveModulesByMasterModule[shipID][itemID]
        self.SetGroupNumbers(shipID)
        sm.ScatterEvent('OnRefreshModuleBanks')

    def SetGroupNumbers(self, shipID):
        """
            This puts a unique number on the group. We need it in order to display the grouping
            information in the fitting window
        """
        allGroupsDict = settings.user.ui.Get('linkedWeapons_groupsDict', {})
        groupsDict = allGroupsDict.get(shipID, {})
        for masterID in groupsDict.keys():
            if masterID not in self.slaveModulesByMasterModule[shipID]:
                del groupsDict[masterID]

        for masterID in self.slaveModulesByMasterModule[shipID]:
            if masterID in groupsDict:
                continue
            for i in xrange(1, 9):
                if i not in groupsDict.values():
                    groupsDict[masterID] = i
                    break

        settings.user.ui.Set('linkedWeapons_groupsDict', allGroupsDict)

    def GetModulesInBank(self, shipID, itemID):
        slaveModulesByMasterModule = self.slaveModulesByMasterModule.get(shipID, {})
        masterID = self.GetMasterModuleID(shipID, itemID)
        if masterID is None and itemID in slaveModulesByMasterModule:
            masterID = itemID
        elif masterID is None:
            return
        moduleIDs = self.GetSlaveModules(masterID, shipID)
        moduleIDs.add(masterID)
        return list(moduleIDs)

    def GetAllSlaveModulesByMasterModule(self, shipID):
        slaveModulesByMasterModule = self.slaveModulesByMasterModule.get(shipID, {})
        return slaveModulesByMasterModule

    def GetMasterModuleForFlag(self, shipID, flagID):
        moduleID = self.GetSlotOther(shipID, flagID)
        if moduleID is None:
            raise RuntimeError('GetMasterModuleForFlag, no module in the flag')
        masterID = self.GetMasterModuleID(shipID, moduleID)
        if masterID is not None:
            return masterID
        return moduleID

    def _UnloadDBLessChargesToContainer(self, shipID, itemIDs, containerArgs, flag, quantity):
        if len(itemIDs) > 1:
            ship = self.broker.invCache.GetInventoryFromId(shipID)
            ship.RemoveChargesToLocationFromBank(itemIDs, containerArgs[0])
        else:
            inv = self.broker.invCache.GetInventoryFromId(locationID=session.stationid2, *containerArgs)
            inv.Add(itemIDs[0], shipID, flag=flag, qty=quantity)

    def _UnloadRealItemChargesToContainer(self, shipID, itemIDs, containerArgs, flag, quantity):
        if containerArgs[0] == const.containerHangar:
            inv = self.broker.invCache.GetInventory(const.containerHangar)
        else:
            inv = self.broker.invCache.GetInventoryFromId(locationID=session.stationid2, *containerArgs)
        inv.MultiAdd(itemIDs, shipID, flag=flag, fromManyFlags=True, qty=quantity)

    def UnloadChargeToContainer(self, shipID, itemID, containerArgs, flag, quantity = None):
        """
            Unloads a fitted charge to container. The itemID must be a charge
        """
        if isinstance(itemID, tuple):
            func = self._UnloadDBLessChargesToContainer
            itemIDs = self.GetSubLocationsInBank(shipID, itemID)
        else:
            func = self._UnloadRealItemChargesToContainer
            itemIDs = self.GetCrystalsInBank(shipID, itemID)
        if len(itemIDs) == 0:
            itemIDs = [itemID]
        try:
            func(shipID, itemIDs, containerArgs, flag, quantity)
        except UserError as e:
            if e.msg == 'NotEnoughCargoSpace' and len(itemIDs) > 1:
                eve.Message('NotEnoughCargoSpaceToUnloadBank')
                return
            raise

    def GetSubLocationsInBank(self, shipID, itemID):
        ret = []
        try:
            flagID = self.dogmaItems[itemID].flagID
        except KeyError:
            return []

        moduleID = self.GetSlotOther(shipID, flagID)
        if moduleID is None:
            return []
        moduleIDs = self.GetModulesInBank(shipID, moduleID)
        if not moduleIDs:
            return []
        shipDogmaItem = self.dogmaItems[shipID]
        for moduleID in moduleIDs:
            moduleDogmaItem = self.dogmaItems[moduleID]
            chargeID = shipDogmaItem.subLocations.get(moduleDogmaItem.flagID, None)
            if chargeID is not None:
                ret.append(chargeID)

        return ret

    def GetCrystalsInBank(self, shipID, itemID):
        flagID = self.dogmaItems[itemID].flagID
        moduleID = self.GetSlotOther(shipID, flagID)
        if moduleID is None:
            return []
        moduleIDs = self.GetModulesInBank(shipID, moduleID)
        if not moduleIDs:
            return []
        crystals = []
        for moduleID in moduleIDs:
            moduleDogmaItem = self.dogmaItems[moduleID]
            crystal = self.GetChargeNonDB(shipID, moduleDogmaItem.flagID)
            if crystal is not None:
                crystals.append(crystal.itemID)

        return crystals

    def LoadChargeToModule(self, itemID, chargeTypeID, chargeItems = None, qty = None, preferSingletons = False):
        """
            Calls the server and asks it to load the chargeTypeID to module itemID. It optinally takes args
            chargeItemIDs which is a list of specific charge items and qty.
        """
        shipID = self.dogmaItems[itemID].locationID
        masterID = self.GetMasterModuleID(shipID, itemID)
        if masterID is None:
            masterID = itemID
        if chargeItems is None:
            shipInv = self.broker.invCache.GetInventoryFromId(shipID, locationID=session.stationid2)
            chargeItems = []
            for item in shipInv.List(const.flagCargo):
                if item.typeID == chargeTypeID:
                    chargeItems.append(item)

        if not chargeItems:
            raise UserError('CannotLoadNotEnoughCharges')
        chargeLocationID = chargeItems[0].locationID
        for item in chargeItems:
            if IsShipFittingFlag(item.flagID):
                raise UserError('CantMoveChargesBetweenModules')

        if preferSingletons:
            for item in chargeItems[:]:
                if not item.singleton:
                    chargeItems.remove(item)

        if qty is not None:
            totalQty = 0
            i = 0
            for item in chargeItems:
                if totalQty >= qty:
                    break
                i += 1
                totalQty += item.stacksize

            chargeItems = chargeItems[:i]
        itemIDs = []
        for item in chargeItems:
            itemIDs.append(item.itemID)

        self.remoteDogmaLM.LoadAmmoToBank(shipID, masterID, chargeTypeID, itemIDs, chargeLocationID)

    def LoadAmmoToModules(self, shipID, moduleIDs, chargeTypeID, itemID, ammoLocationID):
        self.CheckSkillRequirementsForType(chargeTypeID, 'FittingHasSkillPrerequisites')
        self.remoteDogmaLM.LoadAmmoToModules(shipID, moduleIDs, chargeTypeID, itemID, ammoLocationID)

    def DropLoadChargeToModule(self, itemID, chargeTypeID, chargeItems, qty = None, preferSingletons = False):
        if uicore.uilib.Key(uiconst.VK_SHIFT):
            maxQty = 0
            for item in chargeItems:
                if item.typeID != chargeTypeID:
                    continue
                maxQty += item.stacksize

            if maxQty == 0:
                errmsg = localization.GetByLabel('UI/Common/NoMoreUnits')
            else:
                errmsg = localization.GetByLabel('UI/Common/NoRoomForMore')
            qty = None
            ret = uix.QtyPopup(int(maxQty), 0, int(maxQty), errmsg)
            if ret is not None:
                qty = ret['qty']
                if qty <= 0:
                    return
        self.LoadChargeToModule(itemID, chargeTypeID, chargeItems=chargeItems, qty=qty, preferSingletons=preferSingletons)

    def UnloadModuleToContainer(self, shipID, itemID, containerArgs, flag = None):
        """
            Unloads the module to a container. If the module is grouped then we
            first break up the group and then remove the charge and then finally
            the module
        """
        if self.IsInWeaponBank(shipID, itemID):
            ret = eve.Message('CustomQuestion', {'header': localization.GetByLabel('UI/Common/Confirm'),
             'question': localization.GetByLabel('UI/Fitting/ClearGroupModule')}, uiconst.YESNO)
            if ret != uiconst.ID_YES:
                return
        item = self.GetItem(itemID)
        containerInv = self.broker.invCache.GetInventoryFromId(*containerArgs)
        if item is not None:
            subLocation = self.GetSubLocation(item.locationID, item.flagID)
            if subLocation is not None:
                containerInv.Add(subLocation, subLocation[0], qty=None, flag=flag)
            crystal = self.GetChargeNonDB(shipID, item.flagID)
            if crystal is not None:
                containerInv.Add(crystal.itemID, item.locationID, qty=None, flag=flag)
        if getattr(containerInv, 'typeID', None) is not None and cfg.invtypes.Get(containerInv.typeID).groupID == const.groupAuditLogSecureContainer:
            flag = settings.user.ui.Get('defaultContainerLock_%s' % containerInv.itemID, None)
        if containerArgs[0] == shipID:
            containerInv.Add(itemID, item.locationID, qty=None, flag=flag)
        elif flag is not None:
            containerInv.Add(itemID, item.locationID, qty=None, flag=flag)
        else:
            containerInv.Add(itemID, item.locationID)

    def CheckCanFit(self, locationID, itemID, flagID, fromLocationID):
        item = self.broker.invCache.FetchItem(itemID, fromLocationID)
        if item is None:
            self.LogInfo('ClientDogmaLocation::CheckCanFit - unable to fetch item', locationID, itemID, flagID, fromLocationID)
            return
        maxGroupFitted = self.dogmaStaticMgr.GetTypeAttribute(item.typeID, const.attributeMaxGroupFitted)
        if maxGroupFitted is not None:
            modulesByGroup = self.GetModuleListByShipGroup(locationID, item.groupID)
            if len(modulesByGroup) >= maxGroupFitted:
                shipItem = self.dogmaItems[locationID]
                raise UserError('CantFitTooManyByGroup', {'ship': shipItem.typeID,
                 'module': item.typeID,
                 'groupName': cfg.invgroups.Get(item.groupID).name,
                 'noOfModules': int(maxGroupFitted),
                 'noOfModulesFitted': len(modulesByGroup)})

    def GetOnlineModules(self, shipID):
        return {module.flagID:moduleID for moduleID, module in self.dogmaItems[shipID].GetFittedItems().iteritems() if module.IsOnline()}

    def ShouldStartChanceBasedEffect(self, effectID, itemID, chanceAttributeID):
        """
            Godma is authorative about what effects should be started so lets query it about it
        """
        dogmaItem = self.dogmaItems[itemID]
        if dogmaItem.groupID == const.groupBooster:
            godmaItem = self.godma.GetItem(itemID)
            if godmaItem is None:
                return False
            effectName = cfg.dgmeffects.Get(effectID).effectName
            godmaEffect = godmaItem.effects.get(effectName, None)
            if godmaEffect is None:
                return False
            if godmaEffect.isActive:
                return True
        return False

    def GetDogmaItemWithWait(self, itemID):
        """
            This will get the dogma item but can wait up to 2 seconds for it though
        """
        startTime = blue.os.GetWallclockTime()
        while blue.os.TimeDiffInMs(startTime, blue.os.GetWallclockTime()) < 2000:
            if itemID in self.dogmaItems:
                return self.dogmaItems[itemID]
            self.LogInfo('GetDogmaItemWithWait::Item not ready, sleeping for 100ms')
            blue.pyos.synchro.Sleep(100)

        self.LogError('Failed to get dogmaItem in time', itemID)

    def GetModifierString(self, itemID, attributeID):
        """
            This is never called in the client but is handy to have for debugging purposes.
            If we ever plan to use this we need to replace the hardcoded strings with localized
            ones.
        """
        dogmaItem = self.dogmaItems[itemID]
        modifiers = self.GetModifiersOnAttribute(itemID, attributeID, dogmaItem.locationID, dogmaItem.groupID, dogmaItem.ownerID, dogmaItem.typeID)
        baseValue = self.dogmaStaticMgr.GetTypeAttribute2(dogmaItem.typeID, attributeID)
        ret = 'Base Value: %s\n' % GetFormatAndValue(cfg.dgmattribs.Get(attributeID), baseValue)
        if modifiers:
            ret += 'modified by\n'
            for op, modifyingItemID, modifyingAttributeID in modifiers:
                value = self.GetAttributeValue(modifyingItemID, modifyingAttributeID)
                if op in (const.dgmAssPostMul,
                 const.dgmAssPreMul,
                 const.dgmAssPostDiv,
                 const.dgmAssPreDiv) and value == 1.0:
                    continue
                elif op in (const.dgmAssPostPercent, const.dgmAssModAdd, const.dgmAssModAdd) and value == 0.0:
                    continue
                modifyingItem = self.dogmaItems[modifyingItemID]
                modifyingAttribute = cfg.dgmattribs.Get(modifyingAttributeID)
                value = GetFormatAndValue(modifyingAttribute, value)
                ret += '  %s: %s\n' % (cfg.invtypes.Get(modifyingItem.typeID).typeName, value)

        return ret

    def GetDamageFromItem(self, itemID):
        accDamage = 0
        for attributeID in (const.attributeEmDamage,
         const.attributeExplosiveDamage,
         const.attributeKineticDamage,
         const.attributeThermalDamage):
            accDamage += self.GetAttributeValue(itemID, attributeID)

        return accDamage

    def GatherDroneInfo(self, shipDogmaItem):
        """
            Returns the drones dps bandwidth and quantity based in a nested dictionary of
            the form.
                drones = {bandwidthNeeded : [(typeID, bw, qty, dps),...]}
            where the list is ordered by dps
        """
        dronesByTypeID = {}
        for droneID in shipDogmaItem.drones:
            damage = self.GetDamageFromItem(droneID)
            if damage == 0:
                continue
            damageMultiplier = self.GetAttributeValue(droneID, const.attributeDamageMultiplier)
            if damageMultiplier == 0:
                continue
            duration = self.GetAttributeValue(droneID, const.attributeRateOfFire)
            droneDps = damage * damageMultiplier / duration
            droneBandwidth = self.GetAttributeValue(droneID, const.attributeDroneBandwidthUsed)
            droneDogmaItem = self.dogmaItems[droneID]
            droneItem = self.GetItem(droneID)
            if droneDogmaItem.typeID not in dronesByTypeID:
                dronesByTypeID[droneItem.typeID] = [droneBandwidth, droneDps, droneItem.stacksize]
            else:
                dronesByTypeID[droneItem.typeID][-1] += droneItem.stacksize

        drones = defaultdict(list)
        for typeID, (bw, dps, qty) in dronesByTypeID.iteritems():
            bw = int(bw)
            drones[bw].append((typeID,
             bw,
             qty,
             dps))

        for l in drones.itervalues():
            l.sort(key=lambda vals: vals[-1], reverse=True)

        return drones

    def SimpleGetDroneDamageOutput(self, drones, bwLeft, dronesLeft):
        """
            This doesn't get the theoretical maximum drone damage output. The base idea is
            that we start with the drone requiring the highest bandwidth and biggest damage
            and work its way down from that.
        """
        dronesUsed = {}
        totalDps = 0
        for bw in sorted(drones.keys(), reverse=True):
            if bw > bwLeft:
                continue
            for typeID, bwNeeded, qty, dps in drones[bw]:
                noOfDrones = min(int(bwLeft) / int(bwNeeded), qty, dronesLeft)
                if noOfDrones == 0:
                    break
                dronesUsed[typeID] = noOfDrones
                totalDps += dps * noOfDrones
                dronesLeft -= noOfDrones
                bwLeft -= noOfDrones * bwNeeded

        return (totalDps, dronesUsed)

    def GetOptimalDroneDamage(self, shipID):
        """
            This might not get the optimal drone damage output but to do that we need to
            solve a 2-dimensional bounded knapsack problem which I really don't think is
            worth it.
        """
        shipDogmaItem = self.dogmaItems[shipID]
        drones = self.GatherDroneInfo(shipDogmaItem)
        self.LogInfo('Gathered drone info and found', len(drones), 'types of drones')
        bandwidth = self.GetAttributeValue(shipID, const.attributeDroneBandwidth)
        if session.solarsystemid:
            maxDrones = self.godma.GetItem(session.charid).maxActiveDrones
        else:
            maxDrones = self.GetAttributeValue(shipDogmaItem.ownerID, const.attributeMaxActiveDrones)
        self.startedKnapsack = blue.os.GetWallclockTime()
        dps, drones = self.SimpleGetDroneDamageOutput(drones, bandwidth, maxDrones)
        return (dps * 1000, drones)

    def GetTurretAndMissileDps(self, shipID):
        shipDogmaItem = self.dogmaItems[shipID]
        chargesByFlag = {}
        turretsByFlag = {}
        launchersByFlag = {}
        IsTurret = lambda typeID: self.dogmaStaticMgr.TypeHasEffect(typeID, const.effectTurretFitted)
        IsLauncher = lambda typeID: self.dogmaStaticMgr.TypeHasEffect(typeID, const.effectLauncherFitted)
        godmaShipItem = self.godma.GetItem(shipID)
        if godmaShipItem is not None:
            GAV = self.GetGodmaAttributeValue
        else:
            GAV = self.GetAttributeValue
        for module in shipDogmaItem.GetFittedItems().itervalues():
            if IsTurret(module.typeID):
                if not module.IsOnline():
                    continue
                turretsByFlag[module.flagID] = module.itemID
            elif IsLauncher(module.typeID):
                if not module.IsOnline():
                    continue
                launchersByFlag[module.flagID] = module.itemID
            elif module.categoryID == const.categoryCharge:
                chargesByFlag[module.flagID] = module.itemID

        turretDps = 0
        for flagID, itemID in turretsByFlag.iteritems():
            chargeKey = chargesByFlag.get(flagID)
            thisTurretDps = self.GetTurretDps(chargeKey, itemID, GAV)
            turretDps += thisTurretDps

        missileDps = 0
        for flagID, itemID in launchersByFlag.iteritems():
            chargeKey = chargesByFlag.get(flagID)
            if chargeKey is None:
                continue
            thisLauncherDps = self.GetLauncherDps(chargeKey, itemID, shipDogmaItem.ownerID, GAV)
            missileDps += thisLauncherDps

        return (turretDps, missileDps)

    def GetTurretDps(self, chargeKey, itemID, GAV, *args):
        turretDps = 0.0
        if chargeKey is not None:
            damage = self.GetDamageFromItem(chargeKey)
        else:
            damage = self.GetDamageFromItem(itemID)
        if abs(damage) > 0:
            damageMultiplier = GAV(itemID, const.attributeDamageMultiplier)
            duration = GAV(itemID, const.attributeRateOfFire)
            if abs(duration) > 0:
                turretDps = damage * damageMultiplier / duration
        return turretDps * 1000

    def GetLauncherDps(self, chargeKey, itemID, ownerID, GAV):
        missileDps = 0.0
        damage = self.GetDamageFromItem(chargeKey)
        duration = GAV(itemID, const.attributeRateOfFire)
        damageMultiplier = GAV(ownerID, const.attributeMissileDamageMultiplier)
        missileDps = damage * damageMultiplier / duration
        return missileDps * 1000

    def GetGodmaAttributeValue(self, itemID, attributeID):
        """
            Gets the value from godma.
        """
        attributeName = self.dogmaStaticMgr.attributes[attributeID].attributeName
        return self.godma.GetStateManager().GetAttribute(itemID, attributeName)

    def GetModulesLackingSkills(self):
        ret = []
        for moduleID, module in self.dogmaItems[self.shipID].GetFittedItems().iteritems():
            if module.categoryID == const.categoryModule and IsShipFittingFlag(module.flagID) and not const.flagRigSlot0 <= module.flagID <= const.flagRigSlot7:
                if self._GetMissingSkills(module.typeID):
                    ret.append(moduleID)

        return ret

#Embedded file name: eve/client/script/parklife\fleetSvc.py
"""
This file contains the implementation of svc.fleet
the client-side part of the Fleet System
"""
import service
import trinity
import uthread
import form
import uix
import util
import blue
import moniker
import copy
import states as state
import fleetbr
import dbg
import types
import chat
import log
import carbonui.const as uiconst
import uiutil
import localization
import yaml
from fleetcommon import BROADCAST_ALL, BROADCAST_NONE, BROADCAST_DOWN, BROADCAST_UP
from fleetcommon import MAX_NAME_LENGTH, FLEET_NONEID, MAX_DAMAGE_SENDERS, ALL_BROADCASTS, RECONNECT_TIMEOUT, MAX_MEMBERS_IN_SQUAD
from fleetcommon import CHANNELSTATE_NONE, CHANNELSTATE_LISTENING, CHANNELSTATE_SPEAKING, CHANNELSTATE_MAYSPEAK
from eve.client.script.ui.shared.fleet.fleet import WingName, SquadronName
from eve.client.script.util.eveMisc import CSPAChargedActionForMany
from eve.client.script.ui.shared.fleet.storeFleetSetupWnd import StoredFleetSetupListWnd
from eve.client.script.ui.shared.fleet.storeFleetSetupWnd import StoreFleetSetupWnd
from eve.client.script.ui.control.eveBaseLink import GetCharIDFromTextLink
FLEETBROADCASTTIMEOUT = 15
UPDATEFLEETFINDERDELAY = 60
UPDATEFLEETMEMBERDELAY_SEC = 30
MIN_BROADCAST_TIME = 2
RECONNECT_DELAY = 10
FLEETCOMPOSITION_CACHE_TIME = 60
MAX_NUM_BROADCASTS = 500
MAX_NUM_LOOTEVENTS = 500
CONNOT_BE_MOVED_INCOMPATIBLE = -1
CANNOT_BE_MOVED = 0
CAN_BE_COMMANDER = 1
CAN_ONLY_BE_MEMBER = 2

class ServiceStopped(Exception):
    __guid__ = 'fleet.ServiceStopped'


class FleetSvc(service.Service):
    __guid__ = 'svc.fleet'
    __notifyevents__ = ['OnFleetBroadcast',
     'ProcessSessionChange',
     'OnFleetInvite',
     'OnFleetJoin',
     'OnFleetJoinReject',
     'OnFleetLeave',
     'OnFleetMove',
     'OnFleetMemberChanged',
     'OnFleetMoveFailed',
     'OnFleetWingAdded',
     'OnFleetWingDeleted',
     'OnFleetSquadAdded',
     'OnFleetSquadDeleted',
     'OnSquadActive',
     'OnWingActive',
     'OnFleetActive',
     'OnFleetStateChange',
     'OnJumpBeaconChange',
     'OnBridgeModeChange',
     'OnFleetWingNameChanged',
     'OnFleetSquadNameChanged',
     'OnVoiceMuteStatusChange',
     'OnExcludeFromVoiceMute',
     'OnAddToVoiceMute',
     'OnFleetOptionsChanged',
     'OnJoinedFleet',
     'OnLeftFleet',
     'OnFleetJoinRequest',
     'OnFleetJoinRejected',
     'OnJoinRequestUpdate',
     'OnContactChange',
     'OnSpeakingEvent',
     'OnFleetLootEvent',
     'OnFleetMotdChanged',
     'ProcessShutdown']
    __exportedcalls__ = {'Invite': [],
     'LeaveFleet': [],
     'IsMember': [],
     'GetMembers': [],
     'GetWings': [],
     'GetMembersInWing': [],
     'GetMembersInSquad': [],
     'ChangeWingName': [],
     'ChangeSquadName': [],
     'MoveMember': [],
     'SetBooster': [],
     'Regroup': [],
     'GetActiveBeacons': [],
     'HasActiveBeacon': [],
     'GetActiveBeaconForChar': [],
     'GetActiveBridgeForShip': [],
     'HasActiveBridge': [],
     'CanJumpThrough': [],
     'CurrentFleetBroadcastOnItem': [],
     'GetCurrentFleetBroadcastOnItem': [],
     'GetFleetLocationAndInfo': [],
     'GetFleetComposition': [],
     'DistanceToFleetMate': [],
     'SetVoiceMuteStatus': [],
     'IsVoiceMuted': [],
     'GetChannelMuteStatus': [],
     'ExcludeFromVoiceMute': [],
     'AddToVoiceMute': [],
     'IsExcludedFromMute': [],
     'GetExclusionList': [],
     'AddFavorite': [],
     'AddFavoriteSquad': [],
     'RemoveFavorite': [],
     'GetFavorites': [],
     'GetMemberInfo': [],
     'GetOptions': [],
     'SetOptions': [],
     'SetAutoJoinVoice': [],
     'IsDamageUpdates': [],
     'SetDamageUpdates': [],
     'CanIJoinChannel': [],
     'AddToVoiceChat': []}
    __startupdependencies__ = ['settings']
    __dependencies__ = ['clientPathfinderService']

    def Run(self, *etc):
        service.Service.Run(self, *etc)
        self.semaphore = uthread.Semaphore()
        self.Clear()
        sm.FavourMe(self.OnFleetMemberChanged)

    def GetFleetSetups(self):
        if self.fleetSetupsByName is None:
            self.characterSettings = sm.GetService('characterSettings')
            self.fleetSetupsByName = self.FetchFiltersFromServer()
        return self.fleetSetupsByName

    def FetchFiltersFromServer(self):
        ret = {}
        yamlStr = self.characterSettings.Get('fleetSetups')
        if yamlStr is not None:
            filters = yaml.load(yamlStr, Loader=yaml.CLoader)
            ret = {f['setupName']:f for f in filters}
        return ret

    def Clear(self):
        self.leader = None
        self.initedFleet = None
        self.members = {}
        self.wings = {}
        self.targetTags = {}
        self.fleetState = None
        self.activeBeacon = {}
        self.activeBridge = {}
        self.fleetID = None
        self.fleet = None
        self.isMutedByLeader = {}
        self.isExcludedFromMuting = {}
        self.favorites = []
        self.options = util.KeyVal(isFreeMove=False, isVoiceEnabled=False, isRegistered=False)
        self.isAutoJoinVoice = False
        self.isDamageUpdates = True
        self.joinRequests = {}
        self.CleanupBroadcasts()
        self.currentBroadcastOnItem = {}
        self.targetBroadcasts = {}
        self.currentTargetBroadcast = {}
        self.activeStatus = None
        self.locationUpdateRegistrations = {}
        self.lastBroadcast = util.KeyVal(name=None, timestamp=0)
        self.voiceHistory = []
        self.broadcastHistory = []
        self.broadcastScope = settings.user.ui.Get('fleetBroadcastScope', BROADCAST_ALL)
        self.updateThreadRunning = False
        self.updateAdvertThreadRunning = False
        self.lootHistory = []
        self.memberHistory = []
        self.fleetComposition = None
        self.fleetCompositionTimestamp = 0
        self.expectingInvite = None
        self.motd = None
        self.fleetSetupsByName = None
        self.lastLoadedSetup = None
        self.takesFleetWarp = True

    def CleanupBroadcasts(self):
        for itemID, (gbID, gbState, data) in getattr(self, 'currentBroadcastOnItem', {}).iteritems():
            sm.GetService('state').SetState(itemID, gbState, False, gbID, *data)

    def ProcessShutdown(self):
        if session.fleetid and len(self.members) > 0:
            self.LogNotice('I will attempt to reconnect to this fleet', session.fleetid, ' when the client starts up again')
            settings.char.ui.Set('fleetReconnect', (session.fleetid, blue.os.GetWallclockTime()))
            settingsSvc = sm.GetServiceIfRunning('settings')
            if settingsSvc:
                settingsSvc.SaveSettings()

    def OnFleetStateChange(self, fleetState):
        self.fleetState = fleetState

    def OnBridgeModeChange(self, shipID, solarsystemID, itemID, active):
        self.LogInfo('OnBridgeModeChange called:', shipID, solarsystemID, itemID, active)
        if active:
            self.activeBridge[shipID] = (solarsystemID, itemID)
        elif shipID in self.activeBridge:
            del self.activeBridge[shipID]

    def OnJumpBeaconChange(self, charID, solarsystemID, itemID, active):
        self.LogInfo('OnJumpBeaconChange:', charID, solarsystemID, itemID, active)
        if active:
            self.activeBeacon[charID] = (solarsystemID, itemID)
        elif charID in self.activeBeacon:
            del self.activeBeacon[charID]

    def GetTargetTag(self, itemID):
        if self.fleetState:
            return self.fleetState.targetTags.get(itemID, None)

    def CanJumpThrough(self, shipItem):
        if shipItem.groupID not in [const.groupTitan, const.groupBlackOps]:
            return False
        charID = shipItem.charID or shipItem.ownerID
        if not self.IsMember(charID):
            return False
        if not self.HasActiveBridge(shipItem.itemID):
            return False
        bridge = self.activeBridge[shipItem.itemID]
        return bridge[0]

    def HasActiveBridge(self, shipID):
        return shipID in self.activeBridge

    def GetActiveBeacons(self):
        return self.activeBeacon

    def HasActiveBeacon(self, charID):
        return charID in self.activeBeacon

    def GetActiveBridgeForShip(self, shipID):
        if shipID not in self.activeBridge:
            return None
        return self.activeBridge[shipID]

    def GetActiveBeaconForChar(self, charID):
        if charID not in self.activeBeacon:
            return None
        return self.activeBeacon[charID]

    def InitFleet(self):
        if self.fleet is None:
            return
        oldOptions = self.options
        initState = self.fleet.GetInitState()
        self.fleetID = initState.fleetID
        self.members = initState.members
        self.wings = initState.wings
        self.options = initState.options
        self.isMutedByLeader = initState.isMutedByLeader
        self.isExcludedFromMuting = initState.isExcludedFromMuting
        self.motd = initState.motd
        cfg.eveowners.Prime(self.members.keys())
        self.fleetMemberLocations = {}
        if oldOptions != self.options:
            sm.ScatterEvent('OnFleetOptionsChanged_Local', oldOptions, self.options)
        sm.ScatterEvent('OnMyFleetInfoChanged')
        sm.ScatterEvent('OnMyFleetInited')

    def SingleChoiceBox(self, title, body, choices, suppressID):
        import triui
        supp = settings.user.suppress.Get('suppress.' + suppressID, None)
        if supp is not None and not uicore.uilib.Key(uiconst.VK_SHIFT):
            return supp
        ret, block = sm.GetService('gameui').RadioButtonMessageBox(text=body, title=title, buttons=uiconst.OKCANCEL, icon=triui.QUESTION, radioOptions=choices, height=210, width=300, suppText=localization.GetByLabel('UI/Common/SuppressionShowMessageRemember'))
        if ret[0] in [uiconst.ID_CANCEL, uiconst.ID_CLOSE]:
            return
        retNum = 1
        if ret[1] == 'radioboxOption2Selected':
            retNum = 2
        if block:
            settings.user.suppress.Set('suppress.' + suppressID, retNum)
        else:
            settings.user.suppress.Delete('suppress.' + suppressID)
        return retNum

    def CreateFleet(self):
        """
        Asks the user which type of fleet to create and then gets a new Fleet Object and initializes local state
        """
        if session.fleetid:
            raise UserError('FleetError')
        self.fleet = sm.RemoteSvc('fleetObjectHandler').CreateFleet()
        self.LogInfo('Created fleet %s' % self.fleet)
        self.fleet.Init(self.GetMyShipTypeID())
        self.InitFleet()
        self.fleetID = self.fleet.GetFleetID()
        return True

    def Invite(self, charID, wingID, squadID, role):
        if self.fleet is None:
            if not self.CreateFleet():
                return
        if util.IsNPC(charID) or not util.IsCharacter(charID):
            eve.Message('NotRealPilotInvite')
            return
        msgName = None
        if charID != eve.session.charid:
            util.CSPAChargedAction('CSPAFleetCheck', self.fleet, 'Invite', charID, wingID, squadID, role)

    def WaitForLSCAndLeave(self):
        if getattr(self, 'leavingFleet', False):
            return
        setattr(self, 'leavingFleet', True)
        loopCount = 0
        while loopCount < 20:
            if (('fleetid', session.fleetid),) in sm.GetService('LSC').channels:
                break
            self.LogInfo('Waiting for LSC channel to quit fleet')
            loopCount += 1
            blue.pyos.synchro.SleepWallclock(500)

        setattr(self, 'leavingFleet', False)
        self.LeaveFleetNoCheck()

    def LeaveFleet(self):
        uthread.worker('Fleet::WaitForLSCAndLeave', self.WaitForLSCAndLeave)

    def LeaveFleetNoCheck(self):
        if self.fleet is None and session.fleetid:
            sm.RemoteSvc('fleetMgr').ForceLeaveFleet()
        else:
            self.fleet.LeaveFleet()
            self.Clear()

    def IsMember(self, charID):
        return charID in self.members

    def GetMembers(self):
        return self.members

    def GetWings(self):
        if self.fleet is None:
            return {}
        return self.wings

    def GetMembersInWing(self, wingID):
        members = {}
        for mid, m in self.members.iteritems():
            if m.wingID == wingID:
                members[mid] = m

        return members

    def GetMembersInSquad(self, squadID):
        members = {}
        for mid, m in self.members.iteritems():
            if m.squadID == squadID:
                members[mid] = m

        return members

    def ChangeWingName(self, wingID):
        if self.fleet is None:
            return
        name = ''
        ret = uiutil.NamePopup(localization.GetByLabel('UI/Fleet/ChangeWingName'), localization.GetByLabel('UI/Common/Name/TypeInName'), name, maxLength=MAX_NAME_LENGTH)
        if ret is not None:
            self.fleet.ChangeWingName(wingID, ret[:MAX_NAME_LENGTH])

    def ChangeSquadName(self, squadID):
        if self.fleet is None:
            return
        name = ''
        ret = uiutil.NamePopup(localization.GetByLabel('UI/Fleet/ChangeSquadName'), localization.GetByLabel('UI/Common/Name/TypeInName'), name, maxLength=MAX_NAME_LENGTH)
        if ret is not None:
            self.fleet.ChangeSquadName(squadID, ret[:MAX_NAME_LENGTH])

    def SetTakeFleetWarp(self):
        self.fleet.SetTakesFleetWarp(True)

    def SetIgnoreFleetWarp(self):
        self.fleet.SetTakesFleetWarp(False)

    def TakesFleetWarp(self):
        return self.members[session.charid].takesFleetWarp

    def GetOptions(self):
        return self.options

    def SetOptions(self, isFreeMove = None, isVoiceEnabled = None):
        options = copy.copy(self.options)
        if isFreeMove != None:
            options.isFreeMove = isFreeMove
        if isVoiceEnabled != None:
            if isVoiceEnabled:
                if eve.Message('FleetConfirmVoiceEnable', {}, uiconst.YESNO, suppress=uiconst.ID_YES) != uiconst.ID_YES:
                    return
            options.isVoiceEnabled = isVoiceEnabled
        return self.fleet.SetOptions(options)

    def SetAutoJoinVoice(self):
        self.isAutoJoinVoice = True
        sm.GetService('vivox').JoinFleetChannels()

    def SetDamageUpdates(self, isit):
        self.isDamageUpdates = isit
        self.RegisterForDamageUpdates()

    def IsDamageUpdates(self):
        return self.isDamageUpdates

    def CanIJoinChannel(self, groupType, groupID):
        isUnderMe = False
        role = eve.session.fleetrole
        if role == const.fleetRoleLeader:
            isUnderMe = True
        elif role == const.fleetRoleWingCmdr:
            mySquads = self.GetWings()[eve.session.wingid].squads.keys()
            if groupType == 'wing' and groupID == eve.session.wingid:
                isUnderMe = True
            elif groupType == 'squad' and groupID in mySquads:
                isUnderMe = True
            elif groupType == 'fleet':
                isUnderMe = True
        elif groupType == 'squad' and groupID == eve.session.squadid:
            isUnderMe = True
        elif groupType == 'wing' and groupID == eve.session.wingid:
            isUnderMe = True
        elif groupType == 'fleet':
            isUnderMe = True
        return isUnderMe

    def GetJoinRequests(self):
        if not self.joinRequests:
            self.joinRequests = self.fleet.GetJoinRequests()
        return self.joinRequests

    def GetFleetHierarchy(self, members = None):
        if members is None:
            members = self.GetMembers()
        ret = {'commander': None,
         'wings': {},
         'squads': {},
         'name': ''}
        for wingID, wing in self.GetWings().iteritems():
            ret['wings'][wingID] = {'commander': None,
             'squads': wing.squads.keys(),
             'name': wing.name}
            for squadID, squad in wing.squads.iteritems():
                ret['squads'][squadID] = {'commander': None,
                 'members': [],
                 'name': squad.name}

        ast = self.GetActiveStatus()
        if ast is None:
            ret['active'] = False
            for wingID, wing in ret['wings'].iteritems():
                wing['active'] = False

            for squadID, squad in ret['squads'].iteritems():
                squad['active'] = False

        else:
            ret['active'] = ast.fleet
            for wingID, wing in ret['wings'].iteritems():
                wing['active'] = ast.wings.get(wingID, False)

            for squadID, squad in ret['squads'].iteritems():
                squad['active'] = ast.squads.get(squadID, False)

        for rec in members.itervalues():
            if rec.squadID:
                self.AddToFleet(ret, rec)

        return ret

    def AddToFleet(self, fleet, rec):
        try:
            if rec.squadID != -1:
                allSquads = fleet['squads']
                squad = allSquads[rec.squadID]
                if rec.role == const.fleetRoleSquadCmdr:
                    squad['commander'] = rec.charID
                    squad['members'].insert(0, rec.charID)
                elif rec.role == const.fleetRoleMember:
                    squad['members'].append(rec.charID)
                else:
                    log.LogError('Unknown role in squad!', rec.role)
            elif rec.wingID != -1:
                allWings = fleet['wings']
                wing = allWings[rec.wingID]
                if rec.role == const.fleetRoleWingCmdr:
                    wing['commander'] = rec.charID
            elif rec.role == const.fleetRoleLeader:
                fleet['commander'] = rec.charID
            else:
                log.LogTraceback()
                log.LogError("don't know how to add this guy!", dbg.Prettify(rec), str(rec))
        except KeyError as e:
            log.LogTraceback()

    def CheckIfIsOKWithDemotion(self, role):
        myself = self.members[session.charid]
        if myself.job & const.fleetJobCreator != 0:
            return True
        if role > myself.role and eve.Message('FleetConfirmDemoteSelf', {}, uiconst.YESNO) != uiconst.ID_YES:
            return False
        return True

    def MoveMember(self, charID, wingID, squadID, role, roleBooster = None):
        self.CheckIsInFleet()
        if charID == session.charid:
            if not self.CheckIfIsOKWithDemotion(role):
                return
        if self.fleet.MoveMember(charID, wingID, squadID, role, roleBooster):
            sm.ScatterEvent('OnFleetMemberChanging', charID)

    def MassMove(self, charIDs, wingID, squadID, role):
        charIDs = self.FilterOutNonCharacters(charIDs)
        if len(charIDs) == 1:
            return self.MoveMember(charIDs[0], wingID, squadID, role)
        if session.charid in charIDs:
            isOkWithDemotion = self.CheckIfIsOKWithDemotion(role=role)
            if not isOkWithDemotion:
                charIDs.remove(session.charid)
        if charIDs:
            wereMoved = self.fleet.MassMoveMembers(charIDs, wingID, squadID, role)
            if wereMoved:
                sm.ScatterEvent('OnManyFleetMembersChanging', wereMoved)

    def MassInvite(self, charIDs, wingID, squadID, role):
        charIDs = self.FilterOutNonCharacters(charIDs)
        if self.fleet is None and charIDs:
            if not self.CreateFleet():
                return
        if session.charid in charIDs:
            charIDs.remove(session.charid)
        if len(charIDs) == 1:
            charID = charIDs[0]
            self.Invite(charID, wingID, squadID, role)
            if role == const.fleetRoleMember:
                eve.Message('CharacterAddedAsSquadMember', {'char': charID})
            elif role == const.fleetRoleSquadCmdr:
                eve.Message('CharacterAddedAsSquadCommander', {'char': charID})
            elif role == const.fleetRoleWingCmdr:
                eve.Message('CharacterAddedAsWingCommander', {'char': charID})
            elif role == const.fleetRoleLeader:
                eve.Message('CharacterAddedAsFleetCommander', {'char': charID})
        elif charIDs:
            try:
                CSPAChargedActionForMany('CSPAFleetCheckMany', self.fleet, 'MassInvite', charIDs, wingID, squadID, role)
            except UserError as e:
                if e.msg in ('FleetErrorMany', 'FleetNotAllowedMany', 'FleetNoPositionFoundMany', 'FleetTooManyMembersMany', 'FleetInviteMultipleErrors'):
                    notInvited = e.dict.get('notInvited', [])
                    charNameList = [ cfg.eveowners.Get(charID).name for charID in notInvited ]
                    charNames = ', '.join(charNameList)
                    if e.dict:
                        e.dict['namelist'] = charNames
                    raise UserError(e.msg, e.dict)
                else:
                    raise

    def FilterOutNonCharacters(self, charIDs):
        realCharIDs = [ eachID for eachID in charIDs if not util.IsNPC(eachID) and util.IsCharacter(eachID) ]
        return realCharIDs

    def SetBooster(self, charID, roleBooster):
        self.CheckIsInFleet()
        if self.fleet.SetBooster(charID, roleBooster):
            sm.ScatterEvent('OnFleetMemberChanging', charID)

    def CreateWing(self):
        self.CheckIsInFleet()
        wingID = self.fleet.CreateWing()
        if wingID:
            self.CreateSquad(wingID)

    def DeleteWing(self, wingID):
        self.CheckIsInFleet()
        self.fleet.DeleteWing(wingID)

    def CreateSquad(self, wingID):
        self.CheckIsInFleet()
        self.fleet.CreateSquad(wingID)

    def DeleteSquad(self, wingID):
        self.CheckIsInFleet()
        self.fleet.DeleteSquad(wingID)

    def MakeLeader(self, charID):
        self.fleet.MakeLeader(charID)

    def KickMember(self, charID):
        if charID == eve.session.charid:
            self.LeaveFleet()
        else:
            self.fleet.KickMember(charID)

    def __VerifyRightsToRestrict(self, channel):
        return True
        ret = False
        if session.fleetrole > 3:
            ret = False
        elif session.fleetrole == 3:
            squads = self.GetFleetHierarchy()['squads']
            if squads[channel]['commander'] == session.charid:
                ret = True
        elif session.fleetrole == 2:
            wings = self.GetFleetHierarchy()['wings']
            if wings[channel]['commander'] == session.charid:
                ret = True
        elif session.fleetrole == 1:
            if session.fleetid == channel[1]:
                ret = True
        if not ret:
            raise UserError('FleetNotAllowed')

    def AddToVoiceChat(self, channelName):
        return self.fleet.AddToVoiceChat(channelName)

    def IsVoiceMuted(self, channel):
        channel = self.FixChannel(channel)
        if self.isMutedByLeader.has_key(channel) and self.isMutedByLeader[channel] == True and eve.session.charid not in self.isExcludedFromMuting[channel]:
            return True
        else:
            return False

    def GetChannelMuteStatus(self, channel):
        channel = self.FixChannel(channel)
        if self.isMutedByLeader.has_key(channel):
            return self.isMutedByLeader[channel]
        else:
            return False

    def SetVoiceMuteStatus(self, status, channel):
        channel = self.FixChannel(channel)
        if self.__VerifyRightsToRestrict(channel):
            self.fleet.SetVoiceMuteStatus(status, channel)

    def ExcludeFromVoiceMute(self, charid, channel = None):
        if channel is None:
            channel = self.GetMyVoiceChannel()
        channel = self.FixChannel(channel)
        if self.__VerifyRightsToRestrict(channel):
            self.fleet.ExcludeFromVoiceMute(charid, channel)
            if not self.isExcludedFromMuting.has_key(channel):
                self.isExcludedFromMuting[channel] = []
            self.isExcludedFromMuting[channel].append(charid)

    def AddToVoiceMute(self, charid, channel = None):
        if channel is None:
            channel = self.GetMyVoiceChannel()
        channel = self.FixChannel(channel)
        if self.__VerifyRightsToRestrict(channel):
            self.fleet.AddToVoiceMute(charid, channel)
            if not self.isExcludedFromMuting.has_key(channel):
                self.isExcludedFromMuting[channel] = []
            if charid in self.isExcludedFromMuting[channel]:
                self.isExcludedFromMuting[channel].remove(charid)

    def IsExcludedFromMute(self, charid, channel):
        channel = self.FixChannel(channel)
        if self.isExcludedFromMuting.has_key(channel) and charid in self.isExcludedFromMuting[channel]:
            return True
        else:
            return False

    def GetExclusionList(self):
        return self.isExcludedFromMuting

    def GetMyVoiceChannel(self):
        myChannel = None
        if session.fleetrole == const.fleetRoleLeader:
            myChannel = ('fleetid', eve.session.fleetid)
        elif session.fleetrole == const.fleetRoleWingCmdr:
            myChannel = ('wingid', eve.session.wingid)
        elif session.fleetrole == const.fleetRoleSquadCmdr:
            myChannel = ('squadid', eve.session.squadid)
        return self.FixChannel(myChannel)

    def CanIMuteOrUnmuteCharInMyChannel(self, charID):
        CAN_MUTE = 1
        CAN_UNMUTE = -1
        CAN_NOTHING = 0
        channel = self.GetMyVoiceChannel()
        if channel is None or charID is None or not self.GetChannelMuteStatus(channel):
            return CAN_NOTHING
        member = self.members[charID]
        canMuteOrUnmute = False
        canUnmute = False
        if session.fleetrole == const.fleetRoleLeader:
            canMuteOrUnmute = True
        elif session.fleetrole == const.fleetRoleWingCmdr:
            if member.wingID == eve.session.wingid:
                canMuteOrUnmute = True
        elif session.fleetrole == const.fleetRoleSquadCmdr:
            if member.squadID == eve.session.squadid:
                canMuteOrUnmute = True
        if not canMuteOrUnmute:
            return CAN_NOTHING
        elif self.IsExcludedFromMute(charID, channel):
            return CAN_MUTE
        else:
            return CAN_UNMUTE

    def AddFavorite(self, charIDs):
        """
            adds "charIDs" to the current character's favorite list.
            TODO: Right now this just adds the character to damage updates, but this is
            the basis of a "favorites" panel in the fleet UI
        """
        self.CheckIsInFleet()
        if session.charid in charIDs:
            charIDs.remove(session.charid)
        if not charIDs:
            return
        if len(self.favorites) >= MAX_DAMAGE_SENDERS:
            raise UserError('FleetTooManyFavorites', {'num': MAX_DAMAGE_SENDERS})
        for eachCharID in charIDs[:]:
            if self.GetFavorite(eachCharID):
                charIDs.remove(eachCharID)

        if not charIDs:
            return
        newCharsAdded = []
        for eachCharID in charIDs:
            if len(self.favorites) >= MAX_DAMAGE_SENDERS:
                break
            favorite = util.KeyVal(charID=eachCharID, orderID=len(self.favorites))
            self.favorites.append(favorite)
            newCharsAdded.append(eachCharID)

        if not newCharsAdded:
            return
        fav = self.GetWatchlistMembers()
        sm.RemoteSvc('fleetMgr').AddToWatchlist(newCharsAdded, fav)
        sm.ScatterEvent('OnFleetFavoriteAdded', fav)
        wnd = form.WatchListPanel.Open(showActions=False, panelName=localization.GetByLabel('UI/Fleet/WatchList'))
        wnd.OnFleetFavoriteAdded(fav)

    def AddFavoriteSquad(self, squadID):
        squadMembers = [ memberID for memberID, m in self.members.iteritems() if m.squadID == squadID ]
        self.AddFavorite(squadMembers)

    def GetFavorite(self, charID):
        for favorite in self.favorites:
            if charID == favorite.charID:
                return favorite

    def RemoveAllFavorites(self):
        for i in range(len(self.favorites)):
            self.favorites = []

        self.CloseWatchlistWindow()

    def RemoveFavorite(self, charID):
        self.CheckIsInFleet()
        for i in range(len(self.favorites)):
            if self.favorites[i].charID == charID:
                del self.favorites[i]
                break

        fav = self.GetWatchlistMembers()
        sm.RemoteSvc('fleetMgr').RemoveFromWatchlist(charID, fav)
        sm.ScatterEvent('OnFleetFavoriteRemoved', charID)
        if not self.GetFavorites():
            self.CloseWatchlistWindow()

    def ChangeFavoriteSorting(self, charID, orderID = -1, *args):
        if getattr(self, 'isChangingOrder', False):
            return
        try:
            setattr(self, 'isChangingOrder', True)
            favorite = self.GetFavorite(charID)
            if not favorite:
                return
            favoriteIndex = favorite.orderID
            if favoriteIndex < 0:
                return
            if favoriteIndex > len(self.favorites):
                return
            self.favorites.remove(favorite)
            if orderID == -1:
                orderID = len(self.favorites)
            newFavorite = util.KeyVal(charID=charID, orderID=orderID)
            self.favorites.insert(orderID, newFavorite)
        finally:
            setattr(self, 'isChangingOrder', False)

    def CloseWatchlistWindow(self):
        form.WatchListPanel.CloseIfOpen()

    def CloseFleetSetupList(self):
        StoredFleetSetupListWnd.CloseIfOpen()

    def GetFavorites(self):
        return self.favorites

    def IsFavorite(self, charid):
        if self.GetFavorite(charid):
            return True
        else:
            return False

    def GetMemberInfo(self, charID, fleetHierarchy = None):
        member = self.members.get(charID, None)
        if member is None:
            return
        wing = self.wings.get(member.wingID, None)
        wingName = squadName = ''
        fleet = fleetHierarchy or self.GetFleetHierarchy()
        if wing:
            wingName = WingName(fleet, wingID=member.wingID)
            squad = wing.squads.get(member.squadID, None)
            if squad:
                squadName = SquadronName(fleet, squadID=member.squadID)
        jobName = ''
        if member.job & const.fleetJobCreator:
            jobName = localization.GetByLabel('UI/Fleet/Ranks/Boss')
        boosterName = fleetbr.GetBoosterName(member.roleBooster)
        roleName = fleetbr.GetRankName(member)
        ret = util.KeyVal(charID=charID, charName=cfg.eveowners.Get(charID).name, wingID=member.wingID, wingName=wingName, squadID=member.squadID, squadName=squadName, role=member.role, roleName=roleName, job=member.job, jobName=jobName, booster=member.roleBooster, boosterName=boosterName)
        return ret

    def GetWatchlistMembers(self):
        return [None, [ f.charID for f in self.favorites ]][self.isDamageUpdates]

    def RegisterForDamageUpdates(self):
        fav = self.GetWatchlistMembers()
        sm.RemoteSvc('fleetMgr').RegisterForDamageUpdates(fav)

    def Regroup(self):
        bp = sm.StartService('michelle').GetRemotePark()
        if bp is not None:
            bp.CmdFleetRegroup()

    def GetNearestBall(self, fromBall = None, getDist = 0):
        ballPark = sm.GetService('michelle').GetBallpark()
        if not ballPark:
            return
        lst = []
        validNearBy = [const.groupAsteroidBelt,
         const.groupMoon,
         const.groupPlanet,
         const.groupWarpGate,
         const.groupStargate,
         const.groupStation]
        for ballID, ball in ballPark.balls.iteritems():
            slimItem = ballPark.GetInvItem(ballID)
            if slimItem and slimItem.groupID in validNearBy:
                if fromBall:
                    dist = trinity.TriVector(ball.x - fromBall.x, ball.y - fromBall.y, ball.z - fromBall.z).Length()
                    lst.append((dist, ball))
                else:
                    lst.append((ball.surfaceDist, slimItem))

        lst.sort()
        if getDist:
            return lst[0]
        if lst:
            return lst[0][1]

    def CurrentFleetBroadcastOnItem(self, itemID, gbType = None):
        currGBID, currGBType, currGBData = self.currentBroadcastOnItem.get(itemID, (None, None, None))
        if gbType in (None, currGBType):
            return currGBData
        else:
            return

    def GetCurrentFleetBroadcastOnItem(self, itemID):
        """
            Returns all available fleet broadcast data for an itemID.
            Return order is fleet broadcast ID, fleet broadcast type, fleet broadcast data
            All 3 will be None in the case that no broadcast is set.
        """
        return self.currentBroadcastOnItem.get(itemID, (None, None, None))

    def GetCurrentFleetBroadcasts(self):
        return self.currentBroadcastOnItem

    def CheckIsInFleet(self, inSpace = False):
        if self.fleet is None:
            raise UserError('FleetNotInFleet')
        if inSpace and not eve.session.solarsystemid:
            raise UserError('FleetCannotDoInStation')

    def CheckCanAddFavorite(self, charid):
        if charid == session.charid:
            return False
        if self.fleet is None:
            return False
        if self.IsFavorite(charid):
            return False
        return True

    def GetFleetLocationAndInfo(self):
        """
        Return a KeyVal with "pos", "typeID" and "nearestBallID".
        """
        ret = sm.StartService('michelle').GetRemotePark().GetFleetLocationAndInfo()
        for memberID, inf in ret.iteritems():
            ball = util.KeyVal(x=inf.pos[0], y=inf.pos[1], z=inf.pos[2])
            nearestBallID = self.GetNearestBall(ball).itemID
            inf.nearestBallID = nearestBallID
            nearestName = cfg.evelocations.Get(nearestBallID).name

        return ret

    def GetFleetComposition(self):
        if self.fleet is None:
            return
        now = blue.os.GetWallclockTime()
        if self.fleetCompositionTimestamp < now:
            self.LogInfo('Fetching fleet composition')
            self.fleetComposition = self.fleet.GetFleetComposition()
            self.fleetCompositionTimestamp = now + FLEETCOMPOSITION_CACHE_TIME * const.SEC
        return self.fleetComposition

    def DistanceToFleetMate(self, solarSystemID, nearID):
        toSystem = cfg.evelocations.Get(solarSystemID)
        if toSystem is None or eve.session.solarsystemid2 is None:
            raise AttributeError('Invalid solarsystem')
        fromSystem = cfg.evelocations.Get(eve.session.solarsystemid2)
        dist = uix.GetLightYearDistance(fromSystem, toSystem)
        if dist is None:
            eve.Message('MapDistanceUnknown', {'fromSystem': cfg.FormatConvert(const.UE_LOCID, eve.session.solarsystemid2),
             'toSystem': cfg.FormatConvert(const.UE_LOCID, solarSystemID)})
        else:
            jumps = self.clientPathfinderService.GetJumpCountFromCurrent(solarSystemID)
            eve.Message('MapDistance', {'fromSystem': cfg.FormatConvert(const.UE_LOCID, eve.session.solarsystemid2),
             'toSystem': cfg.FormatConvert(const.UE_LOCID, solarSystemID),
             'dist': dist,
             'jumps': jumps})

    def GetActiveStatus(self):
        if self.activeStatus is None:
            if session.solarsystemid is None or session.fleetid is None:
                return util.KeyVal(fleet=False, wings={}, squads={})
            self.activeStatus = sm.RemoteSvc('fleetMgr').GetActiveStatus()
        return self.activeStatus

    def GetVoiceChannels(self):
        channelNames = sm.GetService('vivox').GetJoinedChannels()
        channels = {'fleet': None,
         'wing': None,
         'squad': None,
         'op1': None,
         'op2': None}
        for c in channelNames:
            if type(c) is types.TupleType and c[0] in ('fleetid', 'wingid', 'squadid'):
                for k in channels.keys():
                    if c[0].startswith(k):
                        channels[k] = util.KeyVal(name=c, state=self.GetVoiceChannelState(c))

            elif type(c) is not types.TupleType or not c[0].startswith('inst'):
                n = 'op1'
                if channels[n] is not None:
                    n = 'op2'
                channels[n] = util.KeyVal(name=c, state=self.GetVoiceChannelState(c))

        return channels

    def GetVoiceChannelState(self, channelName):
        channelName = self.FixChannel(channelName)
        if not sm.GetService('vivox').IsVoiceChannel(channelName):
            return CHANNELSTATE_NONE
        if self.IsVoiceMuted(channelName):
            return CHANNELSTATE_LISTENING
        speakingChannel = sm.GetService('vivox').GetSpeakingChannel()
        if type(channelName) is types.TupleType:
            channelName = channelName[0]
        if speakingChannel == channelName:
            return CHANNELSTATE_SPEAKING
        return CHANNELSTATE_MAYSPEAK

    def RejectJoinRequest(self, charID):
        self.fleet.RejectJoinRequest(charID)

    def RemoveAndUpdateFleetFinderAdvert(self, what):
        if session.fleetid is None:
            return
        if not self.IsBoss():
            return
        if not getattr(self.options, 'isRegistered', False):
            return
        ret = sm.ProxySvc('fleetProxy').RemoveFleetFinderAdvert()
        if ret:
            if eve.Message('FleetUpdateFleetFinderAd_%s' % what, {}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
                self.OpenRegisterFleetWindow(ret)

    def BroadcastTimeRestriction(self, name):
        if self.lastBroadcast.name == name and self.lastBroadcast.timestamp + MIN_BROADCAST_TIME * const.SEC > blue.os.GetWallclockTime() or self.lastBroadcast.timestamp + int(float(MIN_BROADCAST_TIME) / 3.0 * float(const.SEC)) > blue.os.GetWallclockTime():
            self.LogInfo('Will not send broadcast', name, 'as not enough time has passed since the last one')
            return True
        else:
            self.lastBroadcast.name = name
            self.lastBroadcast.timestamp = blue.os.GetWallclockTime()
            return False

    def SendGlobalBroadcast(self, name, itemID, typeID = None):
        """
            Send a broadcast event to the fleet object which will percolate to everyone in the fleet
            no matter where they are in the universe
        """
        self.CheckIsInFleet(inSpace=True)
        if self.BroadcastTimeRestriction(name):
            return
        if name not in ALL_BROADCASTS:
            raise RuntimeError('Illegal broadcast')
        self.fleet.SendBroadcast(name, self.broadcastScope, itemID, typeID)

    def SendBubbleBroadcast(self, name, itemID, typeID = None):
        """
            Send a broadcast event to the location-bound fleet service to everyone in the current bubble
        """
        self.CheckIsInFleet(inSpace=True)
        if self.BroadcastTimeRestriction(name):
            return
        if name not in ALL_BROADCASTS:
            raise RuntimeError('Illegal broadcast')
        sm.RemoteSvc('fleetMgr').BroadcastToBubble(name, self.broadcastScope, itemID, typeID)

    def SendSystemBroadcast(self, name, itemID, typeID = None):
        """
            Send a broadcast event to the location-bound fleet service to everyone in the current system
        """
        self.CheckIsInFleet(inSpace=True)
        if self.BroadcastTimeRestriction(name):
            return
        if name not in ALL_BROADCASTS:
            raise RuntimeError('Illegal broadcast')
        sm.RemoteSvc('fleetMgr').BroadcastToSystem(name, self.broadcastScope, itemID, typeID)

    def SendBroadcast_EnemySpotted(self):
        nearestBall = self.GetNearestBall()
        nearID = None
        if nearestBall is not None:
            nearID = nearestBall.itemID
        self.SendGlobalBroadcast('EnemySpotted', nearID)

    def SendBroadcast_NeedBackup(self):
        nearestBall = self.GetNearestBall()
        nearID = None
        if nearestBall is not None:
            nearID = nearestBall.itemID
        self.SendGlobalBroadcast('NeedBackup', nearID)

    def SendBroadcast_HoldPosition(self):
        nearestBall = self.GetNearestBall()
        nearID = None
        if nearestBall is not None:
            nearID = nearestBall.itemID
        self.SendGlobalBroadcast('HoldPosition', nearID)

    def SendBroadcast_TravelTo(self, solarSystemID):
        self.SendGlobalBroadcast('TravelTo', solarSystemID)

    def SendBroadcast_HealArmor(self):
        self.SendBubbleBroadcast('HealArmor', session.shipid)

    def SendBroadcast_HealShield(self):
        self.SendBubbleBroadcast('HealShield', session.shipid)

    def SendBroadcast_HealCapacitor(self):
        self.SendBubbleBroadcast('HealCapacitor', session.shipid)

    def SendBroadcast_Target(self, itemID):
        self.SendBubbleBroadcast('Target', itemID)

    def SendBroadcast_WarpTo(self, itemID, typeID):
        self.SendSystemBroadcast('WarpTo', itemID, typeID)

    def SendBroadcast_AlignTo(self, itemID, typeID):
        self.SendSystemBroadcast('AlignTo', itemID, typeID)

    def SendBroadcast_JumpTo(self, itemID, typeID):
        self.SendSystemBroadcast('JumpTo', itemID, typeID)

    def SendBroadcast_InPosition(self):
        nearestBall = self.GetNearestBall()
        nearID = None
        typeID = None
        if nearestBall is not None:
            nearID = nearestBall.itemID
            typeID = nearestBall.typeID
        self.SendGlobalBroadcast('InPosition', nearID, typeID)

    def SendBroadcast_JumpBeacon(self):
        beacon = self.GetActiveBeaconForChar(session.charid)
        if beacon is None:
            raise UserError('NoActiveBeacon')
        self.SendGlobalBroadcast('JumpBeacon', beacon[1])

    def SendBroadcast_Location(self):
        locationID = eve.session.solarsystemid2
        nearestBall = self.GetNearestBall()
        nearID = None
        if nearestBall is not None:
            nearID = nearestBall.itemID
        self.SendGlobalBroadcast('Location', nearID)

    def OnFleetWingNameChanged(self, wingID, name):
        self.wings = self.fleet.GetWings()
        sm.ScatterEvent('OnFleetWingNameChanged_Local', wingID, name)
        sm.ScatterEvent('OnMyFleetInfoChanged')

    def OnFleetSquadNameChanged(self, squadID, name):
        self.wings = self.fleet.GetWings()
        sm.ScatterEvent('OnFleetSquadNameChanged_Local', squadID, name)
        sm.ScatterEvent('OnMyFleetInfoChanged')

    def OnFleetInvite(self, fleetID, inviteID, msgName, msgDict):
        __fleetMoniker = moniker.GetFleet(fleetID)
        if session.fleetid is not None:
            __fleetMoniker.RejectInvite(True)
            return
        if settings.user.ui.Get('autoRejectInvitations', 0) and self.expectingInvite != fleetID:
            __fleetMoniker.RejectInvite(False)
            return
        self.expectingInvite = None
        try:
            if eve.Message(msgName, msgDict, uiconst.YESNO, default=uiconst.ID_NO, modal=False) == uiconst.ID_YES:
                self.PerformSelectiveSessionChange('fleet.acceptinvite', __fleetMoniker.AcceptInvite, self.GetMyShipTypeID())
                self.fleet = __fleetMoniker
                self.InitFleet()
            else:
                __fleetMoniker.RejectInvite()
        except UserError as e:
            eve.Message(e.msg, e.dict)

    def OnFleetJoin(self, member):
        if member.charID == eve.session.charid:
            self.InitFleet()
            sm.GetService('tactical').InvalidateFlags()
        else:
            self.members[member.charID] = member
            self.AddToMemberHistory(member.charID, localization.GetByLabel('UI/Fleet/FleetBroadcast/MemberHistoryJoined', charID=member.charID, role=fleetbr.GetRankName(member)))
            self.UpdateFleetFinderInfo()
            sm.GetService('tactical').InvalidateFlagsExtraLimited(member.charID)
        sm.ScatterEvent('OnFleetJoin_Local', member)
        if self.isAutoJoinVoice:
            sm.GetService('vivox').JoinFleetChannels()

    def OnFleetJoinReject(self, memberID, reasonCode):
        if reasonCode and reasonCode in const.fleetRejectionReasons:
            reason = localization.GetByLabel(const.fleetRejectionReasons[reasonCode])
            msg = localization.GetByLabel('UI/Fleet/InviteRejectedWithReason', charID=memberID, reason=reason)
        else:
            msg = localization.GetByLabel('UI/Fleet/InviteRejected', charID=memberID)
        eve.Message('CustomNotify', {'notify': msg})

    def OnFleetLeave(self, charID):
        self.AddToMemberHistory(charID, localization.GetByLabel('UI/Fleet/FleetBroadcast/MemberHistoryLeft', charID=charID))
        if charID == eve.session.charid:
            self.Clear()
        if charID in self.members:
            rec = self.members.pop(charID)
            sm.GetService('tactical').InvalidateFlagsExtraLimited(charID)
        else:
            rec = util.KeyVal(charID=charID)
        if charID in self.activeBeacon:
            del self.activeBeacon[charID]
        if charID in self.activeBridge:
            del self.activeBridge[charID]
        if self.GetFavorite(charID):
            self.RemoveFavorite(charID)
        if charID == self.leader:
            self.leader = None
        if charID != eve.session.charid:
            if len(self.members) == 1:
                self.RemoveAndUpdateFleetFinderAdvert('LastMember')
            else:
                self.UpdateFleetFinderInfo()
        sm.ScatterEvent('OnFleetLeave_Local', rec)

    def OnFleetMemberChanged(self, charID, fleetID, oldWingID, oldSquadID, oldRole, oldJob, oldBooster, oldTakesFleetWarp, newWingID, newSquadID, newRole, newJob, newBooster, newTakesFleetWarp, isOnlyMember):
        self.members[charID] = util.KeyVal()
        self.members[charID].charID = charID
        self.members[charID].wingID = newWingID
        self.members[charID].squadID = newSquadID
        self.members[charID].role = newRole
        self.members[charID].job = newJob
        self.members[charID].roleBooster = newBooster
        self.members[charID].takesFleetWarp = newTakesFleetWarp
        sm.ScatterEvent('OnFleetMemberChanged_Local', charID, fleetID, oldWingID, oldSquadID, oldRole, oldJob, oldBooster, oldTakesFleetWarp, newWingID, newSquadID, newRole, newJob, newBooster, newTakesFleetWarp)
        if oldRole != newRole:
            self.AddToMemberHistory(charID, localization.GetByLabel('UI/Fleet/FleetBroadcast/MemberHistoryChangedRole', charID=charID, role=fleetbr.GetRoleName(newRole)))
        if oldJob != newJob:
            if newJob & const.fleetJobCreator:
                self.AddToMemberHistory(charID, localization.GetByLabel('UI/Fleet/FleetBroadcast/MemberHistoryIsBoss', charID=charID))
            else:
                self.AddToMemberHistory(charID, localization.GetByLabel('UI/Fleet/FleetBroadcast/MemberHistoryIsNotBoss', charID=charID))
        if newRole not in (None, -1):
            self.UpdateTargetBroadcasts(charID)
        if charID == eve.session.charid:
            self.fleetCompositionTimestamp = 0
            sm.ScatterEvent('OnMyFleetInfoChanged')
            if oldRole != newRole:
                sm.GetService('vivox').LeaveChannelByType('inst')
            if oldJob & const.fleetJobCreator == 0 and newJob & const.fleetJobCreator > 0 and not isOnlyMember:
                self.RemoveAndUpdateFleetFinderAdvert('NewBoss')
        if newJob != oldJob or newRole != oldRole:
            info = self.GetMemberInfo(charID)
            if newJob != oldJob:
                r = info.jobName
            elif newRole != oldRole:
                r = info.roleName

    def OnFleetMoveFailed(self, charID, isKicked):
        if isKicked:
            eve.Message('CustomNotify', {'notify': localization.GetByLabel('UI/Fleet/MoveFailedKicked', charID=charID)})
        else:
            eve.Message('CustomNotify', {'notify': localization.GetByLabel('UI/Fleet/MoveFailed', charID=charID)})

    def OnFleetWingAdded(self, wingID):
        self.wings = self.fleet.GetWings()
        sm.ScatterEvent('OnFleetWingAdded_Local', wingID)

    def OnFleetWingDeleted(self, wingID):
        self.wings = self.fleet.GetWings()
        sm.ScatterEvent('OnFleetWingDeleted_Local', wingID)

    def OnFleetSquadAdded(self, wingID, squadID):
        self.wings = self.fleet.GetWings()
        sm.ScatterEvent('OnFleetSquadAdded_Local', wingID, squadID)

    def OnFleetSquadDeleted(self, squadID):
        self.wings = self.fleet.GetWings()
        sm.ScatterEvent('OnFleetSquadDeleted_Local', squadID)

    def OnSquadActive(self, squadID, isActive):
        self.LogInfo('OnSquadActive', squadID, isActive)
        self.GetActiveStatus().squads[squadID] = isActive
        sm.ScatterEvent('OnSquadActive_Local', squadID, isActive)

    def OnWingActive(self, wingID, isActive):
        self.LogInfo('OnWingActive', wingID, isActive)
        self.GetActiveStatus().wings[wingID] = isActive
        sm.ScatterEvent('OnWingActive_Local', wingID, isActive)

    def OnFleetActive(self, isActive):
        self.LogInfo('OnFleetActive', isActive)
        self.GetActiveStatus().fleet = isActive
        sm.ScatterEvent('OnFleetActive_Local', isActive)

    def OnVoiceMuteStatusChange(self, status, channel, leader, exclusionList):
        if type(channel) is not types.TupleType:
            return
        channel = self.FixChannel(channel)
        if status == False and self.isMutedByLeader.has_key(channel):
            self.isMutedByLeader.pop(channel)
        elif status == True:
            self.isMutedByLeader[channel] = status
        sm.GetService('vivox').LeaderGagging(channel, leader, exclusionList, state=status)
        sm.ScatterEvent('OnVoiceMuteStatusChange_Local', status, channel, leader, exclusionList)

    def OnExcludeFromVoiceMute(self, charid, channel):
        channel = self.FixChannel(channel)
        if not self.isExcludedFromMuting.has_key(channel):
            self.isExcludedFromMuting[channel] = []
        if charid not in self.isExcludedFromMuting[channel]:
            self.isExcludedFromMuting[channel].append(charid)
        sm.GetService('vivox').ExclusionChange(charid, channel, 0)
        sm.ScatterEvent('OnMemberMuted_Local', charid, channel, False)

    def OnAddToVoiceMute(self, charid, channel):
        channel = self.FixChannel(channel)
        if not self.isExcludedFromMuting.has_key(channel):
            sm.GetService('vivox').ExclusionChange(charid, channel, 1)
        elif charid in self.isExcludedFromMuting[channel]:
            for i in range(len(self.isExcludedFromMuting[channel])):
                if self.isExcludedFromMuting[channel][i] == charid:
                    del self.isExcludedFromMuting[channel][i]
                    break

        sm.GetService('vivox').ExclusionChange(charid, channel, 1)
        sm.ScatterEvent('OnMemberMuted_Local', charid, channel, True)

    def FixChannel(self, name):
        """
        This hack turns (type, id) into ((type, id),) for the LSC system
        """
        if type(name) is types.TupleType:
            if type(name[0]) is not types.TupleType:
                name = (name,)
        return name

    def OnFleetOptionsChanged(self, oldOptions, options):
        self.options = options
        if self.options.isRegistered != oldOptions.isRegistered:
            sm.ScatterEvent('OnFleetFinderAdvertChanged')
            if self.options.isRegistered:
                self.AddBroadcast('FleetFinderAdvertAdded', BROADCAST_NONE, self.GetBossID(), broadcastName=localization.GetByLabel('UI/Fleet/FleetBroadcast/FleetFinderAdvertAdded'))
        if options.isFreeMove != oldOptions.isFreeMove:
            self.AddBroadcast('FleetOptionsChanged', BROADCAST_NONE, self.GetBossID(), broadcastName=[localization.GetByLabel('UI/Fleet/FleetBroadcast/FreeMoveUnset'), localization.GetByLabel('UI/Fleet/FleetBroadcast/FreeMoveSet')][options.isFreeMove])
        if options.isVoiceEnabled != oldOptions.isVoiceEnabled:
            self.AddBroadcast('FleetOptionsChanged', BROADCAST_NONE, self.GetBossID(), broadcastName=[localization.GetByLabel('UI/Fleet/FleetBroadcast/VoiceEnableUnset'), localization.GetByLabel('UI/Fleet/FleetBroadcast/VoiceEnableSet')][options.isVoiceEnabled])
        sm.ScatterEvent('OnFleetOptionsChanged_Local', oldOptions, options)

    def OnJoinedFleet(self):
        self.RefreshFleetWindow()

    def OnLeftFleet(self):
        self.CloseFleetWindow()
        self.CloseWatchlistWindow()
        self.CloseFleetCompositionWindow()
        self.CloseJoinRequestWindow()
        self.CloseRegisterFleetWindow()
        self.CloseFleetBroadcastWindow()
        self.CloseFleetSetupList()

    def OnFleetJoinRequest(self, info):
        self.joinRequests[info.charID] = info
        eve.Message('FleetMemberJoinRequest', {'name': (const.UE_OWNERID, info.charID),
         'corpname': (const.UE_OWNERID, info.corpID)})
        self.OpenJoinRequestWindow()

    def OnFleetJoinRejected(self, charID):
        eve.Message('FleetJoinRequestRejected', {'name': (const.UE_OWNERID, charID)})

    def OnJoinRequestUpdate(self, joinRequests):
        self.joinRequests = joinRequests
        self.OpenJoinRequestWindow()

    def OnContactChange(self, contactIDs, contactType = None):
        self.RemoveAndUpdateFleetFinderAdvert('Standing')

    def OpenJoinRequestWindow(self):
        self.CloseJoinRequestWindow()
        form.FleetJoinRequestWindow.Open()

    def CloseJoinRequestWindow(self):
        form.FleetJoinRequestWindow.CloseIfOpen()

    def OpenFleetCompositionWindow(self):
        self.CloseFleetCompositionWindow()
        form.FleetComposition.Open()

    def CloseFleetCompositionWindow(self):
        form.FleetComposition.CloseIfOpen()

    def CloseFleetBroadcastWindow(self):
        form.BroadcastSettings.CloseIfOpen()

    def OpenRegisterFleetWindow(self, info = None):
        if session.fleetid is None:
            raise UserError('FleetNotFound')
        if not self.IsBoss():
            raise UserError('FleetNotCreator')
        if info is None and self.options.isRegistered:
            info = self.GetMyFleetFinderAdvert()
        self.CloseRegisterFleetWindow()
        form.RegisterFleetWindow.Open(fleetInfo=info)

    def CloseRegisterFleetWindow(self):
        form.RegisterFleetWindow.CloseIfOpen()

    def RefreshFleetWindow(self):
        self.InitFleet()
        self.CloseFleetWindow()
        form.FleetWindow.Open(tabIdx=0)

    def CloseFleetWindow(self):
        form.FleetWindow.CloseIfOpen()

    def AddBroadcast(self, name, scope, charID, solarSystemID = None, itemID = None, broadcastName = None, typeID = None):
        time = blue.os.GetWallclockTime()
        spaceAndOptionalGroupName = ' '
        if name in ('InPosition', 'WarpTo', 'AlignTo', 'JumpTo', 'TravelTo') and typeID is not None and itemID is not None:
            type = cfg.invtypes.Get(typeID)
            if type.groupID == const.groupStargate:
                spaceAndOptionalGroupName = ' %s ' % localization.CleanImportantMarkup(cfg.invgroups.Get(type.groupID).name)
        if name == 'EnemySpotted':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventEnemySpotted', charID=charID)
        elif name == 'NeedBackup':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventNeedBackup', charID=charID)
        elif name == 'HealArmor':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventHealArmor', charID=charID)
        elif name == 'HealShield':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventHealShield', charID=charID)
        elif name == 'HealCapacitor':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventHealCapacitor', charID=charID)
        elif name == 'InPosition':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventInPosition2', charID=charID, locationID=itemID, spaceAndOptionalGroupName=spaceAndOptionalGroupName)
        elif name == 'HoldPosition':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventHoldPosition', charID=charID)
        elif name == 'JumpBeacon':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventJumpToBeacon', charID=charID)
        elif name == 'Location':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventLocation', charID=charID, solarsystemID=solarSystemID)
        elif name == 'WarpTo':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventWarpTo2', charID=charID, locationID=itemID, spaceAndOptionalGroupName=spaceAndOptionalGroupName)
        elif name == 'AlignTo':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventAlignTo2', charID=charID, locationID=itemID, spaceAndOptionalGroupName=spaceAndOptionalGroupName)
        elif name == 'JumpTo':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventJumpTo2', charID=charID, locationID=itemID, spaceAndOptionalGroupName=spaceAndOptionalGroupName)
        elif name == 'TravelTo':
            label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventTravelTo2', charID=charID, locationID=itemID, spaceAndOptionalGroupName=spaceAndOptionalGroupName)
        elif name == 'Target':
            m = sm.GetService('michelle')
            bp = m.GetBallpark()
            slimItem = bp.GetInvItem(itemID)
            if slimItem is not None:
                targetName = uix.GetSlimItemName(slimItem)
                targetTypeName = cfg.invtypes.Get(slimItem.typeID).name
                label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventTargetWithType', targetName=targetName, targetTypeName=targetTypeName)
            else:
                label = localization.GetByLabel('UI/Fleet/FleetBroadcast/BroadcastEventTarget')
        elif broadcastName is not None:
            label = broadcastName
        else:
            log.LogTraceback('Unknown broadcast label:%s' % name)
            label = 'Unknown broadcast label:%s' % name
        where = fleetbr.GetBroadcastWhere(name)
        broadcast = util.KeyVal(name=name, charID=charID, solarSystemID=solarSystemID, itemID=itemID, time=time, broadcastLabel=label, scope=scope, where=where)
        self.broadcastHistory.insert(0, broadcast)
        if len(self.broadcastHistory) > MAX_NUM_BROADCASTS:
            self.broadcastHistory.pop()
        if self.WantBroadcast(name):
            sm.ScatterEvent('OnFleetBroadcast_Local', broadcast)

    def WantBroadcast(self, name):
        if name not in fleetbr.types:
            name = 'Event'
        if settings.user.ui.Get('listenBroadcast_%s' % name, True):
            return True
        return False

    def OnFleetBroadcast(self, name, scope, charID, solarSystemID, itemID, typeID):
        self.LogInfo('OnFleetBroadcast', name, scope, charID, solarSystemID, itemID, ' I now have', len(self.broadcastHistory) + 1, 'broadcasts in my history')
        self.AddBroadcast(name, scope, charID, solarSystemID, itemID, typeID=typeID)
        if name == 'Target':
            targets = self.targetBroadcasts.setdefault(charID, [])
            if itemID in targets:
                targets.remove(itemID)
                targets.insert(0, itemID)
            else:
                targets.append(itemID)
            self.UpdateTargetBroadcasts(charID)
        else:
            stateID = getattr(state, 'gb%s' % name)
            self.BroadcastState(itemID, stateID, charID)

    def BroadcastState(self, itemID, brState, *data):
        gbID = self.NewFleetBroadcastID()
        self.currentBroadcastOnItem[itemID] = (gbID, brState, data)
        sm.GetService('state').SetState(itemID, brState, True, gbID, *data)
        blue.pyos.synchro.SleepWallclock(FLEETBROADCASTTIMEOUT * 1000)
        savedgbid, savedgbtype, saveddata = self.currentBroadcastOnItem.get(itemID, (None, None, None))
        if savedgbid == gbID:
            sm.GetService('state').SetState(itemID, brState, False, gbID, *data)
            del self.currentBroadcastOnItem[itemID]

    def CycleBroadcastScope(self):
        if self.broadcastScope == BROADCAST_DOWN:
            self.broadcastScope = BROADCAST_UP
        elif self.broadcastScope == BROADCAST_UP:
            self.broadcastScope = BROADCAST_ALL
        else:
            self.broadcastScope = BROADCAST_DOWN
        settings.user.ui.Set('fleetBroadcastScope', self.broadcastScope)
        eve.Message('FleetBroadcastScopeChange', {'name': fleetbr.GetBroadcastScopeName(self.broadcastScope)})
        sm.ScatterEvent('OnBroadcastScopeChange')

    def OnSpeakingEvent(self, charID, channelID, isSpeaking):
        if not isSpeaking:
            return
        time = blue.os.GetWallclockTime()
        charName = cfg.eveowners.Get(charID).name
        channelName = chat.GetDisplayName(channelID)
        if type(channelID) is types.TupleType:
            if channelID[0].startswith('inst'):
                channelName = localization.GetByLabel('UI/Fleet/Private')
        data = util.KeyVal(channelID=channelID, charID=charID, time=time, charName=charName, channelName=channelName)
        self.voiceHistory = [ each for each in self.voiceHistory if not (each.charID == charID and each.channelID == channelID) ]
        self.voiceHistory.insert(0, data)
        sm.ScatterEvent('OnSpeakingEvent_Local', data)

    def GetVoiceHistory(self):
        return self.voiceHistory

    def OnFleetLootEvent(self, lootEvents):
        for k, v in lootEvents.iteritems():
            loot = util.KeyVal(charID=k[0], solarSystemID=session.solarsystemid2, typeID=k[1], quantity=v, time=blue.os.GetWallclockTime())
            for i, l in enumerate(self.lootHistory):
                if (l.typeID, l.charID, l.solarSystemID) == (loot.typeID, loot.charID, loot.solarSystemID):
                    self.lootHistory[i].quantity += loot.quantity
                    self.lootHistory[i].time = loot.time
                    break
            else:
                self.lootHistory.insert(0, loot)

        if len(self.lootHistory) > MAX_NUM_LOOTEVENTS:
            self.lootHistory.pop()
        sm.ScatterEvent('OnFleetLootEvent_Local')

    def GetLootHistory(self):
        return self.lootHistory

    def GetBroadcastHistory(self):
        history = [ h for h in self.broadcastHistory if self.WantBroadcast(h.name) ]
        return history

    def AddToMemberHistory(self, charID, event):
        self.memberHistory.insert(0, util.KeyVal(charID=charID, event=event, time=blue.os.GetWallclockTime()))
        if len(self.memberHistory) > MAX_NUM_BROADCASTS:
            self.memberHistory.pop()

    def GetMemberHistory(self):
        return self.memberHistory

    def UpdateTargetBroadcasts(self, charID):

        def BroadcastWithLabel(itemID, label):
            gbID = self.NewFleetBroadcastID()
            self.currentTargetBroadcast[itemID] = gbID
            self.BroadcastState(itemID, state.gbTarget, charID, label)
            if self.currentTargetBroadcast.get(itemID) == gbID:
                self.targetBroadcasts[charID].remove(itemID)

        role = self.members[charID].role
        for i, id_ in enumerate(self.targetBroadcasts.get(charID, [])):
            gbID, gbType, data = self.currentBroadcastOnItem.get(id_, (None, None, None))
            if gbType == state.gbTarget:
                prevCharID, number = data
                if self.IsSuperior(charID, prevCharID):
                    continue
            if role == const.fleetRoleSquadCmdr:
                label = localization.GetByLabel('UI/Fleet/FleetBroadcast/TargetCodeFleet', targetID=i + 1)
            elif role == const.fleetRoleSquadCmdr:
                label = localization.GetByLabel('UI/Fleet/FleetBroadcast/TargetCodeWing', targetID=i + 1)
            elif role == const.fleetRoleSquadCmdr:
                label = localization.GetByLabel('UI/Fleet/FleetBroadcast/TargetCodeSquad', targetID=i + 1)
            else:
                label = localization.GetByLabel('UI/Fleet/FleetBroadcast/TargetCodeMember', targetID=i + 1)
            uthread.pool('FleetSvc::UpdateTargetBroadcasts', BroadcastWithLabel, id_, label)

    @util.Memoized
    def GetRankOrder(self):
        return [const.fleetRoleMember,
         const.fleetRoleSquadCmdr,
         const.fleetRoleWingCmdr,
         const.fleetRoleLeader]

    def IsSuperior(self, charID, otherCharID):

        def Rank(charID):
            return self.GetRankOrder().index(self.members[charID].role)

        return Rank(charID) > Rank(otherCharID)

    def NewFleetBroadcastID(self):
        if not hasattr(self, 'lastFleetBroadcastID'):
            self.lastFleetBroadcastID = 0
        self.lastFleetBroadcastID += 1
        return self.lastFleetBroadcastID

    def ProcessSessionChange(self, isRemote, session, change):
        if 'fleetid' in change:
            self.activeStatus = None
            self.activeBeacon = {}
            self.activeBridge = {}
            self.initedFleet = None
            myrec = self.members.get(session.charid, util.KeyVal(charID=session.charid))
            self.members = {}
            self.leader = None
            if change['fleetid'][1] is None:
                self.fleet = None
                sm.GetService('vivox').LeaveChannelByType('fleetid')
                sm.GetService('vivox').LeaveChannelByType('wingid')
                sm.GetService('vivox').LeaveChannelByType('squadid')
                sm.GetService('vivox').LeaveChannelByType('inst')
                self.favorites = []
                sm.ScatterEvent('OnFleetLeave_Local', myrec)
                sm.ScatterEvent('OnLeftFleet')
            else:
                sm.ScatterEvent('OnJoinedFleet')
            sm.GetService('tactical').InvalidateFlags()
        if 'solarsystemid' in change:
            self.CleanupBroadcasts()
            self.activeStatus = None
            status = self.GetActiveStatus()
            if session.solarsystemid is not None and session.fleetid is not None:
                status = self.RegisterForDamageUpdates()
            if status:
                self.OnFleetActive(status.fleet)
                for wid, w in status.wings.iteritems():
                    self.OnWingActive(wid, w)

                for sid, s in status.squads.iteritems():
                    self.OnSquadActive(sid, s)

            self.UpdateFleetInfo()
        if 'shipid' in change:
            self.UpdateFleetInfo()
        if 'charid' in change:
            if change['charid'][1] is not None:
                uthread.new(self.AttemptReconnectLazy)
        if 'corpid' in change:
            uthread.new(self.RemoveAndUpdateFleetFinderAdvert, 'ChangedCorp')

    def AttemptReconnectLazy(self):
        """
        We wait a few seconds and then try to reconnect to the fleet if we should.
        We do this to allow the client to recover from the trauma of login and to 
        cut off some of the session change timer
        """
        blue.pyos.synchro.SleepSim(RECONNECT_DELAY * 1000)
        try:
            if session.fleetid is not None or session.charid is None:
                return
            fleetReconnect = settings.char.ui.Get('fleetReconnect', None)
            if fleetReconnect:
                if fleetReconnect[1] > blue.os.GetWallclockTime() - RECONNECT_TIMEOUT * const.MIN:
                    self.LogNotice('I will try to reconnect to a lost fleet', fleetReconnect[0])
                    fleet = moniker.GetFleet(fleetReconnect[0])
                    fleet.Reconnect()
                else:
                    self.LogInfo('Reconnect request', fleetReconnect, ' out of date')
        except Exception as e:
            self.LogWarn('Unable to reconnect. Error =', e)
        finally:
            settings.char.ui.Set('fleetReconnect', None)

    def UpdateFleetFinderInfo(self):
        """
        Wait for a minute and then update the Fleet Finder with the current status of the fleet
        The reason for waiting a bit is that we might have more events coming in during that interval
        and we want to limit the number of updates that we do.
        Keep in mind that tht enumber of members is supplied by the client and is therefore spoofable.
        """
        if session.fleetid is None:
            return
        if not self.updateAdvertThreadRunning and self.IsBoss() and self.options.isRegistered:
            self.updateAdvertThreadRunning = True
            uthread.worker('Fleet::UpdateAdvertInfoThread', self.UpdateAdvertInfoThread)

    def UpdateAdvertInfoThread(self):
        try:
            self.LogInfo('Starting UpdateAdvertInfoThread...')
            self.updateAdvertThreadRunning = True
            blue.pyos.synchro.SleepWallclock(UPDATEFLEETFINDERDELAY * 1000)
            if session.fleetid is None:
                return
            if self.IsBoss() and self.options.isRegistered:
                numMembers = len(self.members)
                self.LogInfo('Calling UpdateAdvertInfo', session.solarsystemid2, numMembers)
                sm.ProxySvc('fleetProxy').UpdateAdvertInfo(numMembers)
        finally:
            self.updateAdvertThreadRunning = False

    def UpdateFleetInfo(self):
        if session.fleetid is None:
            return
        self.UpdateFleetFinderInfo()
        if not self.updateThreadRunning:
            self.updateThreadRunning = True
            uthread.worker('Fleet::UpdateFleetInfoThread', self.UpdateFleetInfoThread)

    def UpdateFleetInfoThread(self):
        try:
            self.LogInfo('Starting UpdateFleetInfoThread...')
            self.updateThreadRunning = True
            blue.pyos.synchro.SleepWallclock(UPDATEFLEETMEMBERDELAY_SEC * 1000)
            if session.fleetid is None:
                return
            self.LogInfo('Calling UpdateMemberInfo')
            self.fleet.UpdateMemberInfo(self.GetMyShipTypeID())
        finally:
            self.updateThreadRunning = False

    def OnFleetMove(self):
        oldSquadID = eve.session.squadid
        oldWingID = eve.session.wingid
        self.PerformSelectiveSessionChange('fleet.finishmove', self.fleet.FinishMove)
        if sm.StartService('vivox').Enabled():
            if self.isAutoJoinVoice:
                sm.StartService('vivox').JoinFleetChannels()
            else:
                if oldSquadID != eve.session.squadid:
                    sm.StartService('vivox').LeaveChannelByType('squadid')
                if oldWingID != eve.session.wingid:
                    sm.StartService('vivox').LeaveChannelByType('wingid')

    def PerformSelectiveSessionChange(self, reason, func, *args, **keywords):
        violateSafetyTimer = 0
        if session.nextSessionChange is not None and session.nextSessionChange > blue.os.GetSimTime():
            if session.sessionChangeReason.startswith('fleet.'):
                violateSafetyTimer = 1
        if violateSafetyTimer > 0:
            print 'I will perform a session change even though I should wait %d more seconds' % ((session.nextSessionChange - blue.os.GetSimTime()) / const.SEC)
        kw2 = copy.copy(keywords)
        kw2['violateSafetyTimer'] = violateSafetyTimer
        kw2['wait'] = 1
        sm.StartService('sessionMgr').PerformSessionChange(reason, func, *args, **kw2)

    def IsBoss(self):
        myrec = self.GetMembers().get(eve.session.charid)
        return bool(myrec and myrec.job & const.fleetJobCreator)

    def IsCommanderOrBoss(self):
        if self.IsBoss() or session.fleetrole in (const.fleetRoleLeader, const.fleetRoleWingCmdr, const.fleetRoleSquadCmdr):
            return True
        return False

    def GetBossID(self):
        myrec = self.GetMembers()
        for mid, m in self.members.iteritems():
            if m.job & const.fleetJobCreator:
                return mid

    def IsMySubordinate(self, charID):
        member = self.members.get(charID, None)
        if member is None:
            return False
        isSubordinate = False
        if session.fleetrole == const.fleetRoleLeader or session.fleetrole == const.fleetRoleWingCmdr and member.wingID == session.wingid or session.fleetrole == const.fleetRoleSquadCmdr and member.squadID == session.squadid:
            isSubordinate = True
        return isSubordinate

    def RegisterFleet(self, info):
        self.LogInfo('RegisterFleet', info)
        if session.fleetid is None:
            raise UserError('FleetNotFound')
        if not self.IsBoss():
            raise UserError('FleetNotCreator')
        isEdit = self.options.isRegistered
        sm.ProxySvc('fleetProxy').AddFleetFinderAdvert(info)
        if isEdit:
            sm.ScatterEvent('OnFleetFinderAdvertChanged')

    def UnregisterFleet(self):
        if session.fleetid is None:
            raise UserError('FleetNotFound')
        if not self.IsBoss():
            raise UserError('FleetNotCreator')
        if eve.Message('FleetRemoveFleetFinderAd', {}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
            sm.ProxySvc('fleetProxy').RemoveFleetFinderAdvert()

    def GetFleetsForChar(self):
        return sm.ProxySvc('fleetProxy').GetAvailableFleets()

    def ApplyToJoinFleet(self, fleetID):
        self.expectingInvite = fleetID
        ret = sm.ProxySvc('fleetProxy').ApplyToJoinFleet(fleetID)
        if ret:
            raise UserError('FleetApplicationReceived')

    def AskJoinFleetFromLink(self, fleetID):
        """
        We need to find out whether the character is eligable for the fleet in question
        and then we ask him whether he wants to join.
        """
        if session.fleetid is not None:
            raise UserError('FleetYouAreAlreadyInFleet')
        fleets = self.GetFleetsForChar()
        if fleetID not in fleets:
            raise UserError('FleetJoinFleetFromLinkError')
        self.ApplyToJoinFleet(fleetID)

    def GetMyFleetFinderAdvert(self):
        if session.fleetid is None or not self.options.isRegistered:
            return
        fleet = sm.ProxySvc('fleetProxy').GetMyFleetFinderAdvert()
        if fleet is None:
            return
        fleet.standing = None
        if fleet.Get('solarSystemID', 0):
            mapSvc = sm.GetService('map')
            numJumps = self.clientPathfinderService.GetJumpCountFromCurrent(fleet.solarSystemID)
            fleet.numJumps = numJumps
            constellationID = mapSvc.GetParent(fleet.solarSystemID)
            fleet.regionID = mapSvc.GetParent(constellationID)
            fleet.standing = sm.GetService('standing').GetStanding(session.charid, fleet.leader.charID)
        return fleet

    def SetListenBroadcast(self, name, isit):
        if name not in fleetbr.types:
            name = 'Event'
        settings.user.ui.Set('listenBroadcast_%s' % name, isit)
        sm.ScatterEvent('OnFleetBroadcastFilterChange')

    def GetMyShipTypeID(self):
        shipTypeID = None
        if session.shipid and session.solarsystemid:
            shipTypeID = sm.GetService('godma').GetItem(session.shipid).typeID
        elif util.GetActiveShip():
            activeShipID = util.GetActiveShip()
            dl = sm.GetService('clientDogmaIM').GetDogmaLocation()
            shipItem = dl.GetItem(activeShipID)
            shipTypeID = shipItem.typeID
        return shipTypeID

    def SetRemoteMotd(self, motd):
        """ Sets the MOTD of the fleet chat channel by going to the server """
        self.CheckIsInFleet()
        self.fleet.SetMotdEx(motd)

    def GetMotd(self):
        """ Gets the MOTD for the fleet chat channel, possibly querying the server """
        self.CheckIsInFleet()
        if self.motd is None:
            self.motd = self.fleet.GetMotd()
        return self.motd

    def OnFleetMotdChanged(self, motd):
        self.LogInfo('OnFleetMotdChanged', motd, session.fleetid)
        self.CheckIsInFleet()
        self.motd = motd
        channelWindow = sm.GetService('LSC').GetChannelWindow((('fleetid', session.fleetid),))
        if channelWindow is not None:
            channelWindow.SpeakMOTD()
        else:
            self.LogError('OnFleetMotdChanged could not find fleet chat window', session.fleetid)

    def OnDropCommanderDropData(self, dragObject, draggedGuys, receivingNode, *args):
        draggedGuy = draggedGuys[0]
        groupType = receivingNode.groupType
        groupID = getattr(receivingNode, 'groupID', None)
        canMove = self.CanMoveAtLeastOneToThisEntry(draggedGuys, receivingNode, groupType, groupID)
        if canMove in (CANNOT_BE_MOVED, CONNOT_BE_MOVED_INCOMPATIBLE):
            return
        if groupType == 'squad':
            return self.DropOnSquadCommander(draggedGuys, groupID, canMove)
        if groupType == 'wing':
            return self.DropOnWingcommander(draggedGuys, groupID, canMove)
        if groupType == 'fleet':
            return self.DropOnFleetCommander(draggedGuys, canMove)
        if groupType == 'fleetMember':
            return self.DropOnFleetMember(draggedGuys, receivingNode)

    def DropOnSquadCommander(self, draggedGuys, newSquadID, canMove, *args):
        newWingID = self.FindWingID(newSquadID)
        if newWingID is None:
            return
        if canMove == CAN_BE_COMMANDER and len(draggedGuys) == 1:
            role = const.fleetRoleSquadCmdr
        else:
            role = const.fleetRoleMember
        self.HandleDroppingInGroup(draggedGuys, newWingID, newSquadID, role=role)

    def DropOnWingcommander(self, draggedGuys, newWingID, canMove):
        if canMove == CAN_BE_COMMANDER and len(draggedGuys) == 1:
            role = const.fleetRoleWingCmdr
        else:
            role = const.fleetRoleMember
        self.HandleDroppingInGroup(draggedGuys, newWingID, None, role=role)

    def DropOnFleetCommander(self, draggedGuys, canMove):
        members = self.GetMembers()
        if canMove == CAN_BE_COMMANDER and len(draggedGuys) == 1:
            role = const.fleetRoleLeader
        else:
            role = const.fleetRoleMember
        self.HandleDroppingInGroup(draggedGuys, None, None, role=role)

    def DropOnFleetMember(self, draggedGuys, receivingNode):
        droppedOnMember = receivingNode.member
        newWingID = droppedOnMember.get('wingID', None)
        newSquadID = droppedOnMember.get('squadID', None)
        self.HandleDroppingInGroup(draggedGuys, newWingID, newSquadID)

    def HandleDroppingInGroup(self, draggedGuys, newWingID, newSquadID, role = const.fleetRoleMember):
        self.CheckIsInFleet()
        members = self.GetMembers()
        tryMove = []
        tryInvite = []

        def SkipBecauseAlreadyInWing(eachCharID):
            if role != const.fleetRoleMember:
                return False
            member = members[eachCharID]
            if newWingID and newSquadID is None and newWingID == member.get('wingID', None):
                return True
            return False

        for eachDraggedGuy in draggedGuys:
            charID = eachDraggedGuy.charID
            if charID in members:
                if newWingID is None and newSquadID is None and role != const.fleetRoleLeader:
                    continue
                if not SkipBecauseAlreadyInWing(charID):
                    tryMove.append(charID)
            else:
                tryInvite.append(charID)

        self.MassMove(tryMove, newWingID, newSquadID, role=role)
        self.MassInvite(tryInvite, newWingID, newSquadID, role=role)

    def FindWingID(self, squadID):
        for wingID, wingInfo in self.wings.iteritems():
            if getattr(wingInfo, 'squads', {}):
                if squadID in wingInfo['squads']:
                    return wingID

    def CanMoveToSquad(self, canMoveAll, draggedGuy, groupType, isFreeMove, myMemberInfo, receivingNode, isMultiMove):
        members = self.GetMembers()
        if groupType == 'fleetMember':
            droppedOnMember = receivingNode.member
            newWingID = droppedOnMember.get('wingID', None)
            newSquadID = droppedOnMember.get('squadID', None)
            allowedMove = CAN_ONLY_BE_MEMBER
        else:
            shiftDown = uicore.uilib.Key(uiconst.VK_SHIFT)
            newSquadID = receivingNode.groupID
            squadCommander = self.GetSquadCommander(newSquadID)
            newWingID = None
            if squadCommander:
                allowedMove = CAN_ONLY_BE_MEMBER
                newWingID = squadCommander.get('wingID', None)
            elif isMultiMove or shiftDown:
                allowedMove = CAN_ONLY_BE_MEMBER
            else:
                allowedMove = CAN_BE_COMMANDER
            if newWingID is None:
                newWingID = self.FindWingID(newSquadID)
                if newWingID is None:
                    return CANNOT_BE_MOVED
        memberCount = len([ guy for guy in members.itervalues() if guy.squadID == newSquadID and guy.charID != draggedGuy.charID ])
        if memberCount >= MAX_MEMBERS_IN_SQUAD:
            return CANNOT_BE_MOVED
        elif canMoveAll or isFreeMove:
            return allowedMove
        draggedGuysMemberInfo = self.GetDraggedGuysMemberInfo(draggedGuy)
        if newWingID != session.wingid or draggedGuysMemberInfo and draggedGuysMemberInfo.wingID != session.wingid:
            return CANNOT_BE_MOVED
        elif myMemberInfo.role == const.fleetRoleWingCmdr:
            return allowedMove
        elif not draggedGuysMemberInfo and myMemberInfo.role == const.fleetRoleSquadCmdr and session.squadid == newSquadID:
            return allowedMove
        else:
            return CANNOT_BE_MOVED

    def CanMoveAtLeastOneToThisEntry(self, draggedGuys, receivingNode, groupType, groupID):
        isMultiMove = len(draggedGuys) > 1
        moveSet = {self.CanMoveToThisEntry(eachGuy, receivingNode, groupType, groupID, isMultiMove) for eachGuy in draggedGuys}
        if len(draggedGuys) == 1 and CAN_BE_COMMANDER in moveSet:
            return CAN_BE_COMMANDER
        if CAN_ONLY_BE_MEMBER in moveSet or CAN_BE_COMMANDER in moveSet:
            return CAN_ONLY_BE_MEMBER
        return CANNOT_BE_MOVED

    def CanMoveToThisEntry(self, draggedGuy, receivingNode, groupType, groupID, isMultiMove = False):
        """
            This function finds if the guy you are dragging can be moved where you want to move it.
            - returns CANNOT_BE_MOVED (=0) if he cannot be moved
            - returns CAN_BE_COMMANDER (=1) if he can be moved, and made commander
            - returns CAN_ONLY_BE_MEMBER (=2) if he can be moved, but not made commander
        """
        if draggedGuy.__guid__ not in uiutil.AllUserEntries() + ['TextLink']:
            return CONNOT_BE_MOVED_INCOMPATIBLE
        if draggedGuy.Get('__guid__', None) == 'TextLink':
            charID = GetCharIDFromTextLink(draggedGuy)
            if not charID:
                return CONNOT_BE_MOVED_INCOMPATIBLE
            draggedGuy.charID = charID
        if not util.IsEvePlayerCharacter(draggedGuy.charID):
            return CONNOT_BE_MOVED_INCOMPATIBLE
        members = self.GetMembers()
        myMemberInfo = members[session.charid]
        canMoveAll = myMemberInfo.role == const.fleetRoleLeader or myMemberInfo.job & const.fleetJobCreator
        shiftDown = uicore.uilib.Key(uiconst.VK_SHIFT)
        isFreeMove = False
        if self.GetOptions().isFreeMove and draggedGuy.charID == session.charid:
            isFreeMove = True
        if groupType == 'fleet':
            if not canMoveAll:
                return CANNOT_BE_MOVED
            fleetCommander = self.GetFleetCommander()
            if fleetCommander or isMultiMove or shiftDown:
                return CAN_ONLY_BE_MEMBER
            return CAN_BE_COMMANDER
        if groupType == 'wing':
            newWingID = groupID
            wingCommander = self.GetWingCommander(newWingID)
            if wingCommander or isMultiMove or shiftDown:
                return CAN_ONLY_BE_MEMBER
            if canMoveAll:
                return CAN_BE_COMMANDER
        elif groupType in ('squad', 'fleetMember'):
            return self.CanMoveToSquad(canMoveAll, draggedGuy, groupType, isFreeMove, myMemberInfo, receivingNode, isMultiMove)
        return CANNOT_BE_MOVED

    def GetFleetCommander(self):
        members = self.GetMembers()
        for eachMember in members.itervalues():
            if eachMember.role == const.fleetRoleLeader:
                return eachMember

    def GetWingCommander(self, wingID):
        members = self.GetMembers()
        for eachGuy in members.itervalues():
            if eachGuy.wingID == wingID and eachGuy.role == const.fleetRoleWingCmdr:
                return eachGuy

    def GetSquadCommander(self, squadID):
        """ returns the squad commander of this squad if one exists """
        members = self.GetMembers()
        for eachGuy in members.itervalues():
            if eachGuy.squadID == squadID and eachGuy.role == const.fleetRoleSquadCmdr:
                return eachGuy

    def GetDraggedGuysMemberInfo(self, draggedGuy):
        members = self.GetMembers()
        if draggedGuy.charID in members:
            return members[draggedGuy.charID]

    def ValidateWingsHaveValidNames(self):
        wingNames = set()
        for wing in self.GetWings().itervalues():
            wingName = wing.name.lower().strip()
            if not wingName or wingName in wingNames:
                raise UserError('GiveWingsUniqueNames')
            wingNames.add(wingName)

    def StoreSetup(self):
        if self.fleet is None:
            return
        self.ValidateWingsHaveValidNames()
        name = self.lastLoadedSetup or ''
        wnd = StoreFleetSetupWnd(oldSetupName=self.lastLoadedSetup)
        if wnd.ShowModal() != 1:
            return
        if wnd.result is not None:
            self.StoreFleetSetup(wnd.result)

    def GetSetups(self):
        m = []
        fleetSetupsByName = self.GetFleetSetups()
        for eachSetupName, setupInfo in fleetSetupsByName.iteritems():
            m.append((eachSetupName, [setupInfo['setupName'], self.LoadSetup, (eachSetupName,)]))

        m = uiutil.SortListOfTuples(m)
        return m

    def StoreFleetSetup(self, storeOptions):
        wingsInfo = {}
        wings = self.GetWings().values()
        wings = sorted(wings, key=lambda x: x.get('wingID', None))
        for wingIdx, wing in enumerate(wings):
            wingSquads = []
            for squad in wing.squads.itervalues():
                wingSquads.append(squad.name)

            wingsInfo[wing.name.lower()] = {'wingName': wing.name,
             'squadNames': wingSquads,
             'wingIdx': wingIdx}

        setupName = storeOptions['setupName']
        fleetSetupsByName = self.GetFleetSetups()
        fleetInfo = fleetSetupsByName.get(setupName, {})
        fleetInfo['setupName'] = setupName
        fleetInfo['wingsInfo'] = wingsInfo
        if storeOptions.get('storeMotd', False):
            fleetInfo['motd'] = self.GetMotd()
        if storeOptions.get('storeVoiceSettings', False):
            fleetInfo['isVoiceEnabled'] = self.options.isVoiceEnabled
        if storeOptions.get('storeFreeMove', False):
            fleetInfo['isFreeMove'] = self.options.isFreeMove
        fleetSetupsByName[setupName.lower()] = fleetInfo
        self.SaveSetupOnServer()

    def SaveSetupOnServer(self):
        fleetSetupsByName = self.GetFleetSetups()
        yamlFilters = yaml.safe_dump(fleetSetupsByName.values())
        self.characterSettings.Save('fleetSetups', yamlFilters)
        sm.ScatterEvent('OnFleetSetupChanged')

    def DeleteFleetSetup(self, setupName):
        fleetSetupsByName = self.GetFleetSetups()
        setupRemoved = fleetSetupsByName.pop(setupName, None)
        if setupRemoved:
            self.SaveSetupOnServer()

    def LoadSetup(self, setupName):
        eve.Message('AttemptingToLoadFleet')
        self.lastLoadedSetup = setupName
        self.fleet.LoadFleetSetup(setupName)

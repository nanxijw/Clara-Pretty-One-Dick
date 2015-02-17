#Embedded file name: eve/client/script/ui/station/agents\agents.py
import uicontrols
import uix
import uthread
import blue
import util
import triui
import form
import copy
import moniker
import weakref
import service
import types
import uicls
import carbonui.const as uiconst
import uiutil
import localization
import log
import agentDialogueUtil
import telemetry
from service import ROLE_SERVICE, ROLE_IGB
from eve.common.script.sys.rowset import Rowset
globals().update(service.consts)

class Agents(service.Service):
    __exportedcalls__ = {'InteractWith': [],
     'RemoteNamePopup': [ROLE_SERVICE],
     'GetQuantity': [ROLE_SERVICE],
     'PopupSelect': [ROLE_SERVICE],
     'YesNo': [ROLE_SERVICE],
     'MessageBox': [ROLE_SERVICE],
     'SingleChoiceBox': [ROLE_SERVICE],
     'CheckCargoCapacity': [ROLE_SERVICE],
     'GetAgentByID': [],
     'GetAgentsByID': [],
     'GetAgentsByStationID': [],
     'GetAgentsByCorpID': [],
     'IsAgent': [],
     'GetDivisions': [],
     'GetTutorialAgentIDs': [],
     'DoAction': [ROLE_IGB],
     'PopupMissionJournal': [ROLE_IGB | ROLE_SERVICE],
     'RemoveOfferFromJournal': [],
     'ShowMissionObjectives': [ROLE_IGB | ROLE_SERVICE],
     'PopupDungeonShipRestrictionList': [ROLE_IGB | ROLE_SERVICE]}
    __configvalues__ = {'printHTML': 0}
    __guid__ = 'svc.agents'
    __servicename__ = 'agents'
    __displayname__ = 'Agent Service'
    __dependencies__ = ['map']
    __notifyevents__ = ['OnAgentMissionChange',
     'OnSessionChanged',
     'OnInteractWith',
     'ProcessUIRefresh',
     'OnDatacoreBought']

    def __GetAllAgents(self):
        if self.allAgents is None:
            t = sm.RemoteSvc('agentMgr').GetAgents()
            agentsInSpace = sm.RemoteSvc('agentMgr').GetAgentsInSpace()
            newRowSet = Rowset(t.columns)
            for r in t:
                newRowSet.lines.append(list(r))

            newRowSet.AddField('factionID', None)
            newRowSet.AddField('solarsystemID', None)
            for each in newRowSet:
                if each.stationID:
                    station = sm.GetService('ui').GetStation(each.stationID)
                    each.corporationID = each.corporationID or station.ownerID
                    each.solarsystemID = station.solarSystemID
                else:
                    each.solarsystemID = agentsInSpace.get(each.agentID)
                each.factionID = sm.GetService('faction').GetFaction(each.corporationID)

            self.allAgentsByID = newRowSet.Index('agentID')
            self.allAgentsByStationID = newRowSet.Filter('stationID')
            self.allAgentsByCorpID = newRowSet.Filter('corporationID')
            self.allAgentsByType = newRowSet.Filter('agentTypeID')
            self.allAgents = newRowSet

    def GetAgentByID(self, agentID):
        self.__GetAllAgents()
        if agentID in self.allAgentsByID:
            return self.allAgentsByID[agentID]

    def GetAgentsByID(self):
        self.__GetAllAgents()
        return self.allAgentsByID

    def GetAgentsByStationID(self):
        self.__GetAllAgents()
        return self.allAgentsByStationID

    def GetAgentsByCorpID(self, corpID):
        self.__GetAllAgents()
        return self.allAgentsByCorpID[corpID]

    def GetAgentsByType(self, agentTypeID):
        self.__GetAllAgents()
        return self.allAgentsByType[agentTypeID]

    def IsAgent(self, agentID):
        self.__GetAllAgents()
        return agentID in self.allAgentsByID

    def GetDivisions(self):
        if self.divisions is None:
            self.divisions = sm.RemoteSvc('corporationSvc').GetNPCDivisions().Index('divisionID')
            for row in self.divisions.values():
                row.divisionName = localization.GetByMessageID(row.divisionNameID)
                row.leaderType = localization.GetByMessageID(row.leaderTypeID)

        return self.divisions

    def __init__(self):
        service.Service.__init__(self)
        self.windows = weakref.WeakValueDictionary()
        self.allAgents = None
        self.divisions = None
        self.agentMonikers = {}
        self.agentArgs = {}
        self.missionArgs = {}
        self.lastMonikerAccess = blue.os.GetWallclockTime()
        uthread.worker('agents::ClearMonikers', self.__ClearAgentMonikers)

    def GetAgentMoniker(self, agentID):
        if agentID not in self.agentMonikers:
            if getattr(self, 'allAgentsByID', False) and agentID in self.allAgentsByID and self.allAgentsByID[agentID].stationID:
                self.agentMonikers[agentID] = moniker.GetAgent(agentID, self.allAgentsByID[agentID].stationID)
            else:
                self.agentMonikers[agentID] = moniker.GetAgent(agentID)
        self.lastMonikerAccess = blue.os.GetWallclockTime()
        return self.agentMonikers[agentID]

    def __ClearAgentMonikers(self):
        while self.state == service.SERVICE_RUNNING:
            blue.pyos.synchro.SleepWallclock(300000)
            if blue.os.GetWallclockTime() > self.lastMonikerAccess + 30 * const.MIN:
                self.agentMonikers.clear()

    def Run(self, memStream = None):
        self.LogInfo('Agent Service')
        self.processing = 0
        self.reentrancyGuard1 = 0
        self.reentrancyGuard2 = 0
        self.journalwindows = weakref.WeakValueDictionary()
        self.agentSolarSystems = {}

    def CheckCargoCapacity(self, cargoUnits, mandatoryCargoUnits, extraFlagsToCheck):
        activeShipID = util.GetActiveShip()
        if activeShipID is None:
            capacity, used = (0, 0)
        else:
            capacity, used = sm.GetService('invCache').GetInventoryFromId(activeShipID).GetCapacity(const.flagCargo)
            for flag in extraFlagsToCheck:
                flagCapacity, flagUsed = sm.GetService('invCache').GetInventoryFromId(activeShipID).GetCapacity(flag)
                capacity += flagCapacity
                used += flagUsed

        if session.stationid2 is None and capacity - (used + mandatoryCargoUnits) < 0:
            rejectMessage = localization.GetByLabel('UI/Agents/StandardMissionCargoCapWarning', cargoUnits=mandatoryCargoUnits)
            self.MessageBox(localization.GetByLabel('UI/Agents/CannotAcceptMission'), rejectMessage)
            return ('mission.offeredinsufficientcargospace', rejectMessage)
        if capacity - (used + cargoUnits) < 0:
            if capacity - (used + cargoUnits) < 1:
                c1 = cargoUnits
                c2 = capacity - used
            else:
                c1 = cargoUnits
                c2 = capacity - used
            if not self.YesNo(localization.GetByLabel('UI/Agents/CargoCapacityWarning'), localization.GetByLabel('UI/Agents/StandardMissionAcceptCargoCapWarning', requiredUnits=c1, availableUnits=c2), 'AgtMissionAcceptBigCargo'):
                return 'mission.offered'

    def YesNo(self, title, body, agentID = None, contentID = None, suppressID = None):
        if isinstance(title, basestring):
            titleText = title
        else:
            titleText = self.ProcessMessage((title, contentID), agentID)
        if isinstance(body, basestring):
            bodyText = body
        else:
            bodyText = self.ProcessMessage((body, contentID), agentID)
        options = {'text': bodyText,
         'title': titleText,
         'buttons': uiconst.YESNO,
         'icon': uiconst.QUESTION}
        ret = self.ShowMessageWindow(options, suppressID)
        return ret == uiconst.ID_YES

    def MessageBox(self, title, body, agentID = None, contentID = None, suppressID = None):
        if isinstance(title, basestring):
            titleText = title
        else:
            titleText = self.ProcessMessage((title, contentID), agentID)
        if isinstance(body, basestring):
            bodyText = body
        else:
            bodyText = self.ProcessMessage((body, contentID), agentID)
        options = {'text': bodyText,
         'title': titleText,
         'buttons': triui.OK,
         'icon': triui.INFO}
        self.ShowMessageWindow(options, suppressID)

    def ShowMessageWindow(self, options, suppressID = None):
        if suppressID:
            supp = settings.user.suppress.Get('suppress.' + suppressID, None)
            if supp is not None:
                return supp
            options['suppText'] = localization.GetByLabel('UI/Common/SuppressionShowMessage')
        ret, block = sm.StartService('gameui').MessageBox(**options)
        if suppressID and block and ret not in [uiconst.ID_NO]:
            settings.user.suppress.Set('suppress.' + suppressID, ret)
        return ret

    def SingleChoiceBox(self, title, body, choices, agentID = None, contentID = None, suppressID = None):
        if isinstance(title, basestring):
            titleText = title
        else:
            titleText = self.ProcessMessage((title, contentID), agentID)
        if isinstance(body, basestring):
            bodyText = body
        else:
            bodyText = self.ProcessMessage((body, contentID), agentID)
        choicesText = []
        for choice in choices:
            if type(choice) is tuple:
                choicesText.append(localization.GetByLabel(choice[0], **choice[1]))
            else:
                choicesText.append(choice)

        options = {'text': bodyText,
         'title': titleText,
         'icon': triui.QUESTION,
         'buttons': uiconst.OKCANCEL,
         'radioOptions': choicesText}
        if suppressID:
            supp = settings.user.suppress.Get('suppress.' + suppressID, None)
            if supp is not None:
                return supp
            options['suppText'] = localization.GetByLabel('UI/Common/SuppressionShowMessageRemember')
        ret, block = sm.StartService('gameui').RadioButtonMessageBox(**options)
        if suppressID and block:
            settings.user.suppress.Set('suppress.' + suppressID, ret)
        return (ret[0] == uiconst.ID_OK, ret[1])

    def GetQuantity(self, **keywords):
        for k in ('caption', 'label'):
            if k in keywords and not isinstance(keywords[k], basestring):
                keywords[k] = self.ProcessMessage((keywords[k], None), keywords.get('agentID', None))

        ret = uix.QtyPopup(**keywords)
        if not ret:
            return
        return ret.get('qty', None)

    def RemoteNamePopup(self, caption, label, agentID):
        """
            Intended to be called from the server. Only used by locator agents.
        """
        if isinstance(caption, basestring):
            captionText = caption
        else:
            captionText = self.ProcessMessage((caption, None), agentID)
        if isinstance(label, basestring):
            labelText = label
        else:
            labelText = self.ProcessMessage((label, None), agentID)
        return uiutil.NamePopup(captionText, labelText)

    def PopupSelect(self, title, explanation, agentID, **keywords):
        if isinstance(title, basestring):
            titleText = title
        else:
            titleText = self.ProcessMessage((title, None), agentID)
        if isinstance(explanation, basestring):
            explanationText = explanation
        else:
            explanationText = self.ProcessMessage((explanation, None), agentID)
        if 'typeIDs' in keywords:
            displayList = []
            for typeID in keywords['typeIDs']:
                displayList.append([cfg.invtypes.Get(typeID).name, typeID, typeID])

            ret = uix.ListWnd(displayList, 'type', titleText, explanationText, 0, 300)
        else:
            return
        if ret:
            return ret[2]
        else:
            return

    def Stop(self, memStream = None):
        self.LogInfo('Stopping Agent Services')
        service.Service.Stop(self)

    rookieAgentDict = {}

    def GetTutorialAgentIDs(self):
        """
        This function previously had a hardcoded dict of agentID:True
        written out for every tutorial agentID.  This gives the same return
        value, but this function still seems ill-advised.  :P
        """
        if self.rookieAgentDict == {}:
            for agentID in const.rookieAgentList:
                self.rookieAgentDict[agentID] = True

        return copy.copy(self.rookieAgentDict)

    def GetAuraAgentID(self):
        """
        Gets the aura agent assigned to the current character.
        Note: Returns None if aura is not found.
        """
        charinfo = sm.RemoteSvc('charMgr').GetPublicInfo(eve.session.charid)
        schoolinfo = sm.GetService('cc').GetData('schools', ['schoolID', charinfo.schoolID])
        corpinfo = sm.GetService('corp').GetCorporation(schoolinfo.corporationID)
        agents = self.allAgentsByStationID[corpinfo.stationID]
        for agent in agents:
            if agent.agentTypeID == const.agentTypeAura:
                return agent.agentID

    def OnInteractWith(self, agentID):
        self.InteractWith(agentID)

    @telemetry.ZONE_METHOD
    def InteractWith(self, agentID, maximize = True):
        """
        Interact with the given agent.  Also used to update the agent dialogue window.
        If maximize is set to False then
         - if the window is minimized, update it but leave it minimized
         - if the window does not exist, create it as normal
        If maximize is set to True then
         - if the window is minimized, maximize it and update it
         - if the window does not exist, create it as normal        
        """
        agentDialogueWindow = None
        if agentID in self.windows:
            agentDialogueWindow = self.windows[agentID]
            if agentDialogueWindow.destroyed:
                agentDialogueWindow = None
            if agentDialogueWindow is not None and not agentDialogueWindow.destroyed:
                if maximize:
                    agentDialogueWindow.Maximize()
        if agentDialogueWindow is None:
            agentDialogueWindow = self.OpenAgentDialogueWindow(windowName='agentinteraction_%s' % agentID, agentID=agentID)
            self.windows[agentID] = agentDialogueWindow
            agentDialogueWindow.sr.main.opacity = 0.0
            agentInfo = sm.GetService('agents').GetAgentByID(agentID)
            if agentID not in self.GetTutorialAgentIDs() and agentInfo is not None and agentInfo.agentTypeID != const.agentTypeAura:
                uthread.pool('agents::confirm', eve.Message, 'AgtMissionOfferWarning')
        self.__Interact(agentDialogueWindow)
        if not agentDialogueWindow.destroyed:
            agentDialogueWindow.sr.main.opacity = 1.0
        if not agentDialogueWindow.destroyed and hasattr(agentDialogueWindow.sr, 'stack') and agentDialogueWindow.sr.stack:
            agentDialogueWindow.RefreshBrowsers()

    def ProcessUIRefresh(self):
        if not getattr(self, 'divisions', None):
            return
        for row in self.divisions.values():
            row.divisionName = localization.GetByMessageID(row.divisionNameID)
            row.leaderType = localization.GetByMessageID(row.leaderTypeID)

        for agentID in self.windows:
            state = self.windows[agentID].state
            self.windows[agentID].Close()
            self.InteractWith(agentID)
            self.windows[agentID].SetState(state)

    def __GetConversation(self, wnd, actionID):
        if wnd is None or wnd.destroyed or wnd.sr is None:
            return (None, None, None)
        tmp = wnd.sr.agentMoniker.DoAction(actionID)
        if wnd is None or wnd.destroyed or wnd.sr is None:
            return (None, None, None)
        ret, wnd.sr.oob = tmp
        agentSays, wnd.sr.dialogue = ret
        if actionID is None and len(wnd.sr.dialogue):
            self.LogInfo('Agent Service: Started a new conversation with an agent and successfully retrieved dialogue options.')
            firstActionID = wnd.sr.dialogue[0][0]
            firstActionDialogue = wnd.sr.dialogue[0][1]
            agentHasLocatorService = False
            for id, dlg in wnd.sr.dialogue:
                if dlg == const.agentDialogueButtonLocateCharacter:
                    agentHasLocatorService = True

            isResearchAgent = False
            if self.GetAgentByID(wnd.sr.agentID).agentTypeID == const.agentTypeResearchAgent:
                isResearchAgent = True
            if firstActionDialogue in (const.agentDialogueButtonRequestMission, const.agentDialogueButtonViewMission) and (len(wnd.sr.dialogue) == 1 or not agentHasLocatorService and not isResearchAgent):
                self.LogInfo("Agent Service: Automatically executing the 'Ask' dialogue action for the player.")
                tmp = wnd.sr.agentMoniker.DoAction(firstActionID)
                if wnd is None or wnd.destroyed or wnd.sr is None:
                    return (None, None, None)
                ret, wnd.sr.oob = tmp
                agentSays, wnd.sr.dialogue = ret
        wnd.sr.agentSays = self.ProcessMessage(agentSays, wnd.sr.agentID)
        return (wnd.sr.agentSays, wnd.sr.dialogue, wnd.sr.oob)

    def GetAgentArgs(self, agentID):
        agentInfo = self.GetAgentByID(agentID)
        if not agentInfo:
            return {}
        agentArgs = {'agentID': agentInfo.agentID}
        agentArgs['agentCorpID'] = agentInfo.corporationID
        agentArgs['agentFactionID'] = agentInfo.factionID
        agentArgs['agentSolarSystemID'] = agentInfo.solarsystemID
        agentArgs['agentLocation'] = agentInfo.solarsystemID
        if getattr(agentInfo, 'stationID', None):
            agentArgs['agentStationID'] = agentInfo.stationID
            agentArgs['agentLocation'] = agentInfo.stationID
        agentArgs['agentConstellationID'] = self.map.GetConstellationForSolarSystem(agentInfo.solarsystemID)
        agentArgs['agentRegionID'] = self.map.GetRegionForSolarSystem(agentInfo.solarsystemID)
        return agentArgs

    def PrimeMessageArguments(self, agentID, contentID):
        """
            Fetch all keywords for this mission and agentID now, to avoid potential locking conflicts when the agent
            service triggers a message box being opened by the client.
        """
        if contentID is not None:
            if agentID is None:
                raise RuntimeError('Agent message received a content ID without an agent ID. Something is wrong!')
            if (agentID, contentID) not in self.missionArgs:
                self.missionArgs[agentID, contentID] = self.GetAgentMoniker(agentID).GetMissionKeywords(contentID)
        if agentID is not None:
            if agentID not in self.agentArgs:
                self.agentArgs[agentID] = self.GetAgentArgs(agentID)

    def ProcessMessage(self, msg, agentID = None):
        """
            Processes a message which comes from the agent system. Messages can come in two types:
            (string, ...) -- This is a plaintext string, stored in the old-style agent memory. Kept for backwards-compatibility
            (msgID, contentID) -- This is an authored content message from the current mission or the agent itself
            ((msgLabel, extraArgs), contentID) -- This is a default message from agentMessageUtil (or other location in agent logic
                                                which use message labels rather than IDs). Note that the extraArgs dictionary can
                                                itself contain message ID's (which are processed with the same msgArgs arguments)
        """
        if isinstance(msg, types.TupleType):
            msgInfo, contentID = msg
            if isinstance(msgInfo, basestring):
                return msgInfo
            msgArgs = {}
            self.PrimeMessageArguments(agentID, contentID)
            if contentID is not None:
                msgArgs.update(self.missionArgs[agentID, contentID])
            if agentID is not None:
                msgArgs.update(self.agentArgs[agentID])
            if isinstance(msgInfo, tuple):
                for k in msgInfo[1]:
                    if k in ('missionCompletionText', 'missionOfferText', 'missionBriefingText', 'declineMessageText', 'locationString') or isinstance(msgInfo[1][k], tuple):
                        msgInfo[1][k] = self.ProcessMessage((msgInfo[1][k], contentID), agentID)

                msgArgs.update(msgInfo[1])
                try:
                    return localization.GetByLabel(msgInfo[0], **msgArgs)
                except:
                    log.LogException('Error parsing message with label %s' % msgInfo[0])
                    return localization.GetByLabel('UI/Agents/Dialogue/StandardMission/CorruptBriefing')

            else:
                try:
                    return localization.GetByMessageID(msgInfo, **msgArgs)
                except:
                    log.LogException('Error parsing agent message with ID %s' % msgInfo)
                    return localization.GetByLabel('UI/Agents/Dialogue/StandardMission/CorruptBriefing') + '<br>----------------------<br>' + localization._GetRawByMessageID(msgInfo)

        else:
            return msg

    def DoAction(self, agentID, actionID = None, closeWindowOnClick = False):
        if self.reentrancyGuard1:
            return
        self.reentrancyGuard1 = 1
        try:
            if agentID in self.windows:
                self.__Interact(self.windows[agentID], actionID, closeWindowAfterInteraction=closeWindowOnClick)
        finally:
            self.reentrancyGuard1 = 0

    def OnAgentMissionChange(self, what, agentID, tutorialID = None):
        if tutorialID:
            sm.GetService('tutorial').OpenTutorialSequence_Check(tutorialID)
        if (agentID, 'offer') in self.journalwindows:
            window = self.journalwindows[agentID, 'offer']
            if window is not None and not window.destroyed:
                if what in (const.agentMissionReset,
                 const.agentMissionOfferRemoved,
                 const.agentMissionOfferExpired,
                 const.agentMissionOfferDeclined,
                 const.agentMissionOfferAccepted):
                    window.Close()
                else:
                    self.PopupOfferJournal(agentID)
        elif (agentID, 'mission') in self.journalwindows:
            window = self.journalwindows[agentID, 'mission']
            if window is not None and not window.destroyed:
                if what in (const.agentMissionReset,
                 const.agentMissionDeclined,
                 const.agentMissionCompleted,
                 const.agentMissionQuit,
                 const.agentMissionFailed,
                 const.agentMissionOffered,
                 const.agentMissionOfferRemoved):
                    window.Close()
                else:
                    self.PopupMissionJournal(agentID)
        if agentID in self.windows:
            agentDialogueWindow = self.windows[agentID]
            if what in (const.agentMissionDeclined, const.agentMissionQuit) and 'objectiveBrowser' in agentDialogueWindow.htmlCache:
                del agentDialogueWindow.htmlCache['objectiveBrowser']
            if what in (const.agentMissionOfferRemoved, const.agentMissionReset, const.agentTalkToMissionCompleted):
                if not agentDialogueWindow.destroyed:
                    agentDialogueWindow.CloseByUser()
                del self.windows[agentID]
        if what in (const.agentMissionOffered, const.agentMissionReset):
            keys = [ x for x in self.missionArgs.keys() if x[0] == agentID ]
            for key in keys:
                del self.missionArgs[key]

        if what in const.agentMissionCompleted:
            sm.GetService('audio').SendUIEvent(u'ui_notify_mission_rewards_play')

    def OnDatacoreBought(self, characterID, agentID, balance):
        self.LogInfo('OnDatacoreBought', characterID, agentID, balance)
        sm.ScatterEvent('OnAgentMissionChange', const.agentMissionResearchUpdatePPD, agentID)
        sm.ScatterEvent('OnAccountChange', 'cash', characterID, balance)

    def OnSessionChanged(self, isRemote, sess, change):
        """
        The agent dialogue window and the mission briefing window both refresh themselves
        when the player docks/undocks, to update the status of location-specific mission
        objectives.  This handles the mission briefing window.
        """
        if 'stationid2' in change:
            for key, window in self.journalwindows.iteritems():
                agentID, missionState = key
                if window is not None and not window.destroyed:
                    self.UpdateMissionJournal(agentID, popup=False)

    def PopupMissionJournal(self, agentID, charID = None, contentID = None):
        self.UpdateMissionJournal(agentID, charID, contentID)

    def UpdateMissionJournal(self, agentID, charID = None, contentID = None, popup = True):
        if self.reentrancyGuard2:
            return
        self.reentrancyGuard2 = 1
        try:
            ret = self.GetAgentMoniker(agentID).GetMissionJournalInfo(charID, contentID)
            if ret:
                html = self.BuildJournalHTML(ret, agentID)
                if (agentID, 'mission') not in self.journalwindows or self.journalwindows[agentID, 'mission'].destroyed:
                    browser = form.AgentBrowser.Open(caption=localization.GetByLabel('UI/Agents/MissionJournalWithAgent', agentID=agentID))
                    self.journalwindows[agentID, 'mission'] = browser
                else:
                    browser = self.journalwindows[agentID, 'mission']
                browser.SetMinSize([420, 400])
                uthread.new(self.LoadPage, browser, html, popup)
        finally:
            self.reentrancyGuard2 = 0

    def CheckCourierCargo(self, agentID, stationID, contentID):
        missionInfo = self.GetAgentMoniker(agentID).GetMissionJournalInfo()
        if missionInfo:
            for objType, objData in missionInfo['objectives']['objectives']:
                if objType == 'transport':
                    pickupOwnerID, pickupLocation, dropoffOwnerID, dropoffLocation, cargo = objData
                    return cargo['hasCargo']

        return False

    def BuildJournalHTML(self, missionInfo, agentID):
        missionName = self.ProcessMessage((missionInfo['missionNameID'], missionInfo['contentID']), agentID)
        html = '\n            <html>\n            <head>\n                <LINK REL="stylesheet" TYPE="text/css" HREF="res:/ui/css/missionjournal.css">\n            </head>\n            <body>\n        '
        if 'iconID' in missionInfo:
            missionGraphic = util.IconFile(missionInfo['iconID'])
            if missionGraphic:
                html += '<p><img src="icon:%s" width=64 height=64 align=left hspace=4 vspace=4><br>' % missionGraphic
        html += '\n            <span id=mainheader>%(missionName)s</span><br>\n            <hr>\n            <center><span id=ip>%(missionImage)s</span></center><br>\n            </p>\n            <span id=subheader>%(briefingTitle)s</span>\n            <div id=basetext>%(missionBriefing)s</div>\n            <br>\n        ' % {'missionName': missionName,
         'missionImage': missionInfo['missionImage'],
         'briefingTitle': localization.GetByLabel('UI/Agents/StandardMission/MissionBriefing'),
         'missionBriefing': self.ProcessMessage((missionInfo['briefingTextID'], missionInfo['contentID']), agentID)}
        expirationTime = missionInfo['expirationTime']
        if expirationTime is not None:
            if missionInfo['missionState'] in (const.agentMissionStateAllocated, const.agentMissionStateOffered):
                expirationMessage = localization.GetByLabel('UI/Agents/Dialogue/ThisOfferExpiresAt', expireTime=expirationTime)
            else:
                expirationMessage = localization.GetByLabel('UI/Agents/Dialogue/ThisMissionExpiresAt', expireTime=expirationTime)
            html += '<span id=ip>%s</span><br><br>' % expirationMessage
        html += agentDialogueUtil.BuildObjectiveHTML(agentID, missionInfo['objectives'])
        html += '</body></html>'
        return html

    def PopupDungeonShipRestrictionList(self, agentID, charID = None, dungeonID = None):
        restrictions = self.GetAgentMoniker(agentID).GetDungeonShipRestrictions(dungeonID)
        title = localization.GetByLabel('UI/Agents/Dialogue/DungeonShipRestrictionsHeader')
        ship = None
        shipID = util.GetActiveShip()
        if shipID is not None:
            ship = sm.GetService('clientDogmaIM').GetDogmaLocation().GetDogmaItem(shipID)
        shipGroupID = shipTypeID = None
        body = ''
        if ship:
            shipGroupID = getattr(ship, 'groupID', None)
            shipTypeID = ship.typeID
        if shipGroupID:
            if shipGroupID in restrictions.restrictedShipTypes:
                msgPath = 'UI/Agents/Dialogue/DungeonShipRestrictionsListShipIsRestricted'
            elif shipGroupID in restrictions.allowedShipTypes:
                if len(restrictions.allowedShipTypes) > 1:
                    msgPath = 'UI/Agents/Dialogue/DungeonShipRestrictionsListShipIsNotRestricted'
                else:
                    restrictions.allowedShipTypes.remove(shipGroupID)
                    body = localization.GetByLabel('UI/Agents/Dialogue/DungeonShipRestrictionShipIsNotRestricted', groupName=cfg.invgroups.Get(shipGroupID).groupName, typeID=shipTypeID)
        else:
            msgPath = 'UI/Agents/Dialogue/DungeonShipRestrictionsShowList'
        if len(restrictions.allowedShipTypes) > 0:
            permittedShipGroupList = []
            for shipGroupID in restrictions.allowedShipTypes:
                permittedShipGroupList.append(cfg.invgroups.Get(shipGroupID).groupName)

            localization.util.Sort(permittedShipGroupList)
            shipList = ''
            for each in permittedShipGroupList:
                shipList += u'  \u2022' + each + '<br>'

            body = localization.GetByLabel(msgPath, shipTypeID=shipTypeID, shipList=shipList)
        options = {'text': body,
         'title': title,
         'buttons': triui.OK,
         'icon': triui.INFO}
        self.ShowMessageWindow(options)

    def RemoveOfferFromJournal(self, agentID):
        self.GetAgentMoniker(agentID).RemoveOfferFromJournal()

    def OpenAgentDialogueWindow(self, windowName = 'agentDialogueWindow', agentID = None):
        window = form.AgentDialogueWindow.Open(windowID=windowName, agentID=agentID)
        return window

    @telemetry.ZONE_METHOD
    def LoadPage(self, browser, html, popup):
        if browser.state != uiconst.UI_NORMAL and popup:
            browser.Maximize()
        if browser.state in (uiconst.UI_NORMAL, uiconst.UI_PICKCHILDREN):
            blue.pyos.synchro.Yield()
            browser.sr.browser.LoadHTML(html)

    def PopupOfferJournal(self, agentID):
        if self.reentrancyGuard2:
            return
        self.reentrancyGuard2 = 1
        try:
            html = self.GetAgentMoniker(agentID).GetOfferJournalInfo()
            if html:
                if self.printHTML:
                    print '-----------------------------------------------------------------------------------'
                    print html
                    print '-----------------------------------------------------------------------------------'
                if (agentID, 'offer') not in self.journalwindows or self.journalwindows[agentID, 'offer'].destroyed:
                    browser = form.AgentBrowser(caption=localization.GetByLabel('UI/Agents/MissionJournalWithAgent', agentID=agentID))
                    self.journalwindows[agentID, 'offer'] = browser
                else:
                    browser = self.journalwindows[agentID, 'offer']
                browser.SetMinSize([420, 400])
                browser.sr.browser.LoadHTML(html)
        finally:
            self.reentrancyGuard2 = 0

    def ShowMissionObjectives(self, agentID, charID = None, contentID = None, briefingTitleID = None):
        """
        This method is meant purely to display the mission objective details of an arbitrary
        mission while leaving the agent dialogue pane untouched, when selecting an option in
        an Agent Interaction mission.  Fallback code exists to handle errors, but is not meant
        to allow this method to be called in a general way. 
        """
        if agentID not in self.windows:
            self.InteractWith(agentID)
            return
        if self.reentrancyGuard2:
            return
        self.reentrancyGuard2 = 1
        try:
            agentDialogueWindow = self.windows[agentID]
            ret = self.GetAgentMoniker(agentID).GetMissionObjectiveInfo(charID, contentID)
            if not agentDialogueWindow.destroyed:
                if ret:
                    objectiveHtml = '\n                        <html>\n                        <head>\n                            <link rel="stylesheet" type="text/css" href="res:/ui/css/missionobjectives.css">\n                        </head>\n                        <body>\n                    '
                    objectiveHtml += agentDialogueUtil.BuildObjectiveHTML(agentDialogueWindow.sr.agentID, ret)
                    objectiveHtml += '</body></html>'
                    agentDialogueWindow.SetDoublePaneView(objectiveHtml=objectiveHtml)
                else:
                    agentDialogueWindow.SetSinglePaneView()
        finally:
            self.reentrancyGuard2 = 0

    def GetSecurityWarning(self, locations):
        routeStart = eve.session.solarsystemid2
        charSecStatus = sm.GetService('crimewatchSvc').GetMySecurityStatus()
        secWarning = ''
        for each in locations:
            if len(secWarning) > 0:
                break
            if routeStart == eve.session.solarsystemid2 and each == eve.session.solarsystemid2:
                continue
            else:
                route = sm.GetService('clientPathfinderService').GetAutopilotPathBetween(routeStart, each)
            if route is None:
                secWarning = localization.GetByLabel('UI/Agents/Dialogue/AutopilotRouteNotFound')
                break
            elif len(route) > 0:
                routeStart = route[len(route) - 1]
                for solarsystem in route:
                    if charSecStatus > -5.0 and sm.StartService('map').GetSecurityClass(solarsystem) <= const.securityClassLowSec:
                        secWarning = localization.GetByLabel('UI/Agents/Dialogue/AutopilotRouteLowSecWarning')
                        break
                    elif charSecStatus < -5.0 and sm.StartService('map').GetSecurityClass(solarsystem) == const.securityClassHighSec:
                        secWarning = localization.GetByLabel('UI/Agents/Dialogue/AutopilotRouteHighSecWarning')
                        break

        return secWarning

    def GetMissionBriefingInformation(self, wnd):
        if wnd is None or wnd.destroyed or wnd.sr is None:
            return
        return wnd.sr.agentMoniker.GetMissionBriefingInfo()

    _buttonLabelMapping = {const.agentDialogueButtonViewMission: 'UI/Agents/Dialogue/Buttons/ViewMission',
     const.agentDialogueButtonRequestMission: 'UI/Agents/Dialogue/Buttons/RequestMission',
     const.agentDialogueButtonAccept: 'UI/Agents/Dialogue/Buttons/AcceptMission',
     const.agentDialogueButtonAcceptChoice: 'UI/Agents/Dialogue/Buttons/AcceptThisChoice',
     const.agentDialogueButtonAcceptRemotely: 'UI/Agents/Dialogue/Buttons/AcceptRemotely',
     const.agentDialogueButtonComplete: 'UI/Agents/Dialogue/Buttons/CompleteMission',
     const.agentDialogueButtonCompleteRemotely: 'UI/Agents/Dialogue/Buttons/CompleteRemotely',
     const.agentDialogueButtonContinue: 'UI/Agents/Dialogue/Buttons/Continue',
     const.agentDialogueButtonDecline: 'UI/Agents/Dialogue/Buttons/DeclineMission',
     const.agentDialogueButtonDefer: 'UI/Agents/Dialogue/Buttons/DeferMission',
     const.agentDialogueButtonQuit: 'UI/Agents/Dialogue/Buttons/QuitMission',
     const.agentDialogueButtonStartResearch: 'UI/Agents/Dialogue/Buttons/StartResearch',
     const.agentDialogueButtonCancelResearch: 'UI/Agents/Dialogue/Buttons/CancelResearch',
     const.agentDialogueButtonBuyDatacores: 'UI/Agents/Dialogue/Buttons/BuyDatacores',
     const.agentDialogueButtonLocateCharacter: 'UI/Agents/Dialogue/Buttons/LocateCharacter',
     const.agentDialogueButtonLocateAccept: 'UI/Agents/Dialogue/Buttons/LocateCharacterAccept',
     const.agentDialogueButtonLocateReject: 'UI/Agents/Dialogue/Buttons/LocateCharacterReject',
     const.agentDialogueButtonYes: 'UI/Common/Buttons/Yes',
     const.agentDialogueButtonNo: 'UI/Common/Buttons/No'}

    def GetLabelForButtonID(self, buttonID):
        """
            Converts the buttonID from the server to the corresponding localization string label.
        """
        return self._buttonLabelMapping.get(buttonID, '')

    @telemetry.ZONE_METHOD
    def __Interact(self, agentDialogueWindow, actionID = None, closeWindowAfterInteraction = False):
        if actionID:
            agentDialogueWindow.DisableButtons()
        agentSays, dialogue, extraInfo = self.__GetConversation(agentDialogueWindow, actionID)
        briefingInformation = self.GetMissionBriefingInformation(agentDialogueWindow)
        if briefingInformation and briefingInformation['ContentID']:
            self.missionArgs[agentDialogueWindow.sr.agentID, briefingInformation['ContentID']] = briefingInformation['Mission Keywords']
        initialContentID = None
        if agentSays is None:
            return
        if closeWindowAfterInteraction:
            agentDialogueWindow.CloseByUser()
            return
        if extraInfo.get('missionQuit', None):
            agentDialogueWindow.CloseByUser()
            return
        customAgentButtons = {'okLabel': [],
         'okFunc': [],
         'args': []}
        disabledButtons = []
        charSays = ''
        extraMissionInfo = ''
        numDialogChoices = 0
        isAgentInteractionMission = False
        appendCloseButton = False
        adminBlock = ''
        if dialogue:
            adminOptions = []
            for each in dialogue:
                if not agentDialogueWindow or agentDialogueWindow.destroyed:
                    return
                if type(each[1]) == dict:
                    if not isAgentInteractionMission:
                        initialContentID = each[1]['ContentID']
                        extraMissionInfo += '<br>'
                    self.missionArgs[agentDialogueWindow.sr.agentID, each[1]['ContentID']] = each[1]['Mission Keywords']
                    isAgentInteractionMission = True
                    missionTitle = self.ProcessMessage((each[1]['Mission Title ID'], each[1]['ContentID']), agentDialogueWindow.sr.agentID)
                    extraMissionInfo += '\n                        <span id=subheader><a href="localsvc:service=agents&method=DoAction&agentID=%d&actionID=%d">%s</a> &gt;&gt;</span><br>\n                    ' % (agentDialogueWindow.sr.agentID, each[0], missionTitle)
                    if each[1]['Mission Briefing ID'] is not None:
                        if isinstance(each[1]['Mission Briefing ID'], basestring) or each[1]['Mission Briefing ID'] > 0:
                            briefingText = self.ProcessMessage((each[1]['Mission Briefing ID'], each[1]['ContentID']), agentDialogueWindow.sr.agentID)
                        else:
                            briefingText = localization.GetByLabel('UI/Agents/Dialogue/StandardMission/CorruptBriefing')
                        extraMissionInfo += '\n                            <div id=basetext>%s</div>\n                            <br>\n                        ' % briefingText
                    numDialogChoices += 1
                elif type(each[1]) is int:
                    labelPath = self.GetLabelForButtonID(each[1])
                    if labelPath:
                        label = localization.GetByLabel(labelPath)
                    else:
                        self.LogError('Unknown button ID for agent action, id =', each[1])
                        label = 'Unknown ID ' + str(each[1])
                    closeWindowOnClick = each[1] == const.agentDialogueButtonDefer
                    if each[1] in (const.agentDialogueButtonRequestMission,
                     const.agentDialogueButtonContinue,
                     const.agentDialogueButtonQuit,
                     const.agentDialogueButtonCancelResearch):
                        appendCloseButton = True
                    customAgentButtons['okLabel'].append(label)
                    customAgentButtons['okFunc'].append(self.DoAction)
                    customAgentButtons['args'].append((agentDialogueWindow.sr.agentID, each[0], closeWindowOnClick))
                else:
                    adminOptions.append('<a href="localsvc:service=agents&method=DoAction&agentID=%d&actionID=%d">%s</a>' % (agentDialogueWindow.sr.agentID, each[0], each[1]))

            if adminOptions:
                if len(adminOptions) == 1:
                    adminBlock = '<br>'
                    adminBlock += adminOptions[0]
                else:
                    adminBlock = '<ol>'
                    adminBlock += ''.join([ '<br><li>%s</li>' % x for x in adminOptions ])
                    adminBlock += '</ol>'
        a = self.GetAgentByID(agentDialogueWindow.sr.agentID)
        agentCorpID = a.corporationID
        agentDivisionID = a.divisionID
        lp = getattr(agentDialogueWindow.sr, 'oob', {}).get('loyaltyPoints', 0)
        if isAgentInteractionMission or briefingInformation:
            extraMissionInfo += '<br>'
            if briefingInformation['Decline Time'] is not None:
                if briefingInformation['Decline Time'] == -1:
                    extraMissionInfo += localization.GetByLabel('UI/Agents/StandardMission/DeclineMessageGeneric')
                else:
                    timeRemaining = briefingInformation['Decline Time']
                    timeBreakAt = 'min' if timeRemaining > const.MIN else 'sec'
                    extraMissionInfo += localization.GetByLabel('UI/Agents/StandardMission/DeclineMessageTimeLeft', timeRemaining=util.FmtTimeInterval(timeRemaining, breakAt=timeBreakAt))
            elif briefingInformation['Expiration Time'] is not None:
                extraMissionInfo += localization.GetByLabel('UI/Agents/Dialogue/ThisMissionExpiresAt', expireTime=briefingInformation['Expiration Time'])
            if not isAgentInteractionMission:
                extraMissionInfo += '<br><center>%s</center>' % briefingInformation['Mission Image']
        if not len(customAgentButtons['okLabel']) and not isAgentInteractionMission:
            extraMissionInfo = ''
        missionTitle = ''
        if briefingInformation:
            missionTitle = '<br><span id=subheader>' + self.ProcessMessage((briefingInformation['Mission Title ID'], briefingInformation['ContentID']), agentDialogueWindow.sr.agentID) + '</span><br>'
        if self.GetAgentByID(agentDialogueWindow.sr.agentID).agentTypeID == const.agentTypeAura:
            agentInfoIcon = ''
            blurbEffectiveStanding = ''
            blurbDivision = ''
        else:
            agentInfoIcon = '<a href=showinfo:%d//%d><img src=icon:38_208 size=16 alt="%s"></a>' % (self.GetAgentInventoryTypeByBloodline(a.bloodlineID), a.agentID, uiutil.StripTags(localization.GetByLabel('UI/Commands/ShowInfo'), stripOnly=['localized']))
            divisions = self.GetDivisions()
            blurbDivision = localization.GetByLabel('UI/Agents/Dialogue/Division', divisionName=divisions[agentDivisionID].divisionName)
        agentLocationWrap = self.GetAgentMoniker(agentDialogueWindow.sr.agentID).GetAgentLocationWrap()
        html = '\n            <html>\n            <head>\n                <link rel="stylesheet" type="text/css" href="res:/ui/css/agentconvo.css">\n            </head>\n                <body background-color=#00000000 link=#ffa800>\n                    %(agentHeader)s\n                    <br>\n                    %(missionTitle)s\n                    <br>\n                    %(agentSays)s\n                    <br>    \n                    %(extraMissionInfo)s\n                    <br>\n                    %(adminBlock)s\n                </body>\n            </html>\n        ' % {'agentHeader': agentDialogueUtil.GetAgentLocationHeader(a, agentLocationWrap, lp),
         'missionTitle': missionTitle,
         'agentSays': agentSays,
         'extraMissionInfo': extraMissionInfo,
         'adminBlock': adminBlock}
        if self.printHTML:
            print '-----------------------------------------------------------------------------------'
            print html
            print '-----------------------------------------------------------------------------------'
        numButtons = len(customAgentButtons['okLabel'])
        if appendCloseButton and numButtons < 3:
            customAgentButtons['okLabel'].append(localization.GetByLabel('UI/Common/Buttons/Close'))
            customAgentButtons['okFunc'].append(agentDialogueWindow.CloseByUser)
            customAgentButtons['args'].append('self')
        if numButtons:
            agentDialogueWindow.DefineButtons('Agent Interaction Buttons', **customAgentButtons)
            for each in disabledButtons:
                agentDialogueWindow.DisableButton(each)

        else:
            agentDialogueWindow.DefineButtons(uiconst.CLOSE)
        ret = self.GetAgentMoniker(agentDialogueWindow.sr.agentID).GetMissionObjectiveInfo()
        if agentDialogueWindow and not agentDialogueWindow.destroyed:
            agentDialogueWindow.SetHTML(html, where='briefingBrowser')
            objectiveHtml = None
            if ret and not (extraInfo['missionCompleted'] or extraInfo['missionDeclined'] or extraInfo['missionQuit']):
                objectiveHtml = '\n                    <html>\n                    <head>\n                        <link rel="stylesheet" type="text/css" href="res:/ui/css/missionobjectives.css">\n                    </head>\n                    <body>\n                '
                objectiveHtml += agentDialogueUtil.BuildObjectiveHTML(agentDialogueWindow.sr.agentID, ret)
                objectiveHtml += '</body></html>'
                agentDialogueWindow.SetHTML(objectiveHtml, where='objectiveBrowser')
            if objectiveHtml or extraInfo.get('missionCompleted'):
                agentDialogueWindow.SetDoublePaneView(briefingHtml=html, objectiveHtml=objectiveHtml)
            else:
                agentDialogueWindow.SetSinglePaneView(briefingHtml=html)

    def GetAgentInventoryTypeByBloodline(self, bloodlineID):
        """
        This function originally existed only in agentMgr.py on the server; however,
        we don't care to make a call to the server just to get this const mapping, so
        I have made it present here on the client side in agents.py as well.
        
        These should be consolidated into a common util location.
        """
        return {const.bloodlineAmarr: const.typeCharacterAmarr,
         const.bloodlineNiKunni: const.typeCharacterNiKunni,
         const.bloodlineCivire: const.typeCharacterCivire,
         const.bloodlineDeteis: const.typeCharacterDeteis,
         const.bloodlineGallente: const.typeCharacterGallente,
         const.bloodlineIntaki: const.typeCharacterIntaki,
         const.bloodlineSebiestor: const.typeCharacterSebiestor,
         const.bloodlineBrutor: const.typeCharacterBrutor,
         const.bloodlineStatic: const.typeCharacterStatic,
         const.bloodlineModifier: const.typeCharacterModifier,
         const.bloodlineAchura: const.typeCharacterAchura,
         const.bloodlineJinMei: const.typeCharacterJinMei,
         const.bloodlineKhanid: const.typeCharacterKhanid,
         const.bloodlineVherokior: const.typeCharacterVherokior}[bloodlineID]

    def GetSolarSystemOfAgent(self, agentID):
        if agentID not in self.agentSolarSystems:
            self.agentSolarSystems[agentID] = sm.RemoteSvc('agentMgr').GetSolarSystemOfAgent(agentID)
        return self.agentSolarSystems[agentID]

    def ProcessAgentInfoKeyVal(self, data):
        infoFunc = {'research': self._ProcessResearchServiceInfo,
         'locate': self._ProcessLocateServiceInfo,
         'mission': self._ProcessMissionServiceInfo}.get(data.agentServiceType, None)
        if infoFunc:
            return infoFunc(data)
        else:
            return []

    def _ProcessResearchServiceInfo(self, data):
        header = localization.GetByLabel('UI/Agents/Research/ResearchServices', session.languageID)
        skillList = []
        for skillTypeID, skillLevel in data.skills:
            skillList.append(localization.GetByLabel('UI/Agents/Research/SkillListing', session.languageID, skillID=skillTypeID, skillLevel=skillLevel))

        if not skillList:
            skills = localization.GetByLabel('UI/Agents/Research/ErrorNoRelevantResearchSkills', session.languageID)
        else:
            skillList = localization.util.Sort(skillList)
            skills = localization.formatters.FormatGenericList(skillList)
        details = [(localization.GetByLabel('UI/Agents/Research/RelevantSkills', session.languageID), skills)]
        status = []
        if data.researchData:
            researchData = data.researchData
            researchStuff = [(localization.GetByLabel('UI/Agents/Research/ResearchField', session.languageID), cfg.invtypes.Get(researchData['skillTypeID']).name), (localization.GetByLabel('UI/Agents/Research/CurrentStatus', session.languageID), localization.GetByLabel('UI/Agents/Research/CurrentStatusRP', session.languageID, rpAmount=researchData['points'])), (localization.GetByLabel('UI/Agents/Research/ResearchRate', session.languageID), localization.GetByLabel('UI/Agents/Research/ResearchRateRPDay', session.languageID, rpAmount=researchData['pointsPerDay']))]
            status = [(localization.GetByLabel('UI/Agents/Research/YourResearch', session.languageID), researchStuff)]
        return [(header, details)] + status

    def _ProcessLocateServiceInfo(self, data):
        header = localization.GetByLabel('UI/Agents/Locator/LocationServices', session.languageID)
        if data.frequency:
            details = [(localization.GetByLabel('UI/Agents/Locator/MaxFrequency', session.languageID), localization.GetByLabel('UI/Agents/Locator/EveryInterval', session.languageID, interval=data.frequency))]
        else:
            details = [(localization.GetByLabel('UI/Agents/Locator/MaxFrequency', session.languageID), localization.GetByLabel('UI/Generic/NotAvailableShort', session.languageID))]
        for delayRange, delay, cost in data.delays:
            rangeText = [localization.GetByLabel('UI/Agents/Locator/SameSolarSystem', session.languageID),
             localization.GetByLabel('UI/Agents/Locator/SameConstellation', session.languageID),
             localization.GetByLabel('UI/Agents/Locator/SameRegion', session.languageID),
             localization.GetByLabel('UI/Agents/Locator/DifferentRegion', session.languageID)][delayRange]
            if not delay:
                delay = localization.GetByLabel('UI/Agents/Locator/ResultsInstantaneous', session.languageID)
            else:
                delay = util.FmtTimeInterval(delay * const.SEC)
            details.append((rangeText, localization.formatters.FormatGenericList((util.FmtISK(cost), delay))))

        if data.callbackID:
            details.append((localization.GetByLabel('UI/Agents/Locator/Availability', session.languageID), localization.GetByLabel('UI/Agents/Locator/NotAvailableInProgress', session.languageID)))
        elif data.lastUsed and blue.os.GetWallclockTime() - data.lastUsed < data.frequency:
            details.append((localization.GetByLabel('UI/Agents/Locator/AvailableAgain', session.languageID), util.FmtDate(data.lastUsed + data.frequency)))
        return [(header, details)]

    def _ProcessMissionServiceInfo(self, data):
        if data.available:
            return [(localization.GetByLabel('UI/Agents/MissionServices', session.languageID), [(localization.GetByLabel('UI/Agents/MissionAvailability', session.languageID), localization.GetByLabel('UI/Agents/MissionAvailabilityStandard', session.languageID))])]
        else:
            return [(localization.GetByLabel('UI/Agents/MissionServices', session.languageID), [(localization.GetByLabel('UI/Agents/MissionAvailability', session.languageID), localization.GetByLabel('UI/Agents/MissionAvailabilityNone', session.languageID))])]


class AgentBrowser(uicontrols.Window):
    """
        This class is a stripped-down version of the old IGB, which is used in 3 places by
        the agent system.
    """
    __guid__ = 'form.AgentBrowser'
    __notifyevents__ = []
    default_windowID = 'AgentBrowser'

    def ApplyAttributes(self, attributes):
        uicontrols.Window.ApplyAttributes(self, attributes)
        self.scope = 'all'
        self.loadupdates = 0
        self.statustext = ''
        self.views = []
        self.activeView = 0
        self.SetCaption('')
        self.SetWndIcon(None)
        self.SetTopparentHeight(0)
        self.sr.browser = uicontrols.Edit(parent=self.sr.main, padding=(const.defaultPadding,
         const.defaultPadding,
         const.defaultPadding,
         const.defaultPadding), readonly=1)
        self.sr.browser.AllowResizeUpdates(0)
        self.sr.browser.sr.window = self

    def LoadHTML(self, html, hideBackground = 0, newThread = 1):
        self.sr.browser.sr.hideBackground = hideBackground
        self.sr.browser.LoadHTML(html, newThread=newThread)

    def OnEndScale_(self, *args):
        self.reloadedScaleSize = (self.width, self.height)
        uthread.new(self.Reload, 0)

    def Reload(self, forced = 1, *args):
        if not self or self.destroyed:
            return
        url = self.sr.browser.sr.currentURL
        if url and forced:
            uthread.new(self.GoTo, url, self.sr.browser.sr.currentData, scrollTo=self.sr.browser.GetScrollProportion())
        else:
            uthread.new(self.sr.browser.LoadHTML, None, scrollTo=self.sr.browser.GetScrollProportion())

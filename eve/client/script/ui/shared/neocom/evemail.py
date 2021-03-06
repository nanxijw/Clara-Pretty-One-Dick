#Embedded file name: eve/client/script/ui/shared/neocom\evemail.py
"""
This file contains the UI for the mail system
"""
from carbonui.primitives.containerAutoSize import ContainerAutoSize
from eve.client.script.ui.control.divider import Divider
from eve.client.script.ui.control.colorpicker import ColorSwatch
from eve.client.script.ui.shared.neocom.characterSearchWindow import CharacterSearchWindow
from eve.client.script.ui.control.listgroup import ListGroup as Group
from eve.client.script.ui.shared.userentry import User
from eve.client.script.ui.control.eveBaseLink import GetCharIDFromTextLink
from carbonui.control.dragResizeCont import DragResizeCont
import blue
import uiprimitives
import uicontrols
import uthread
import uix
import uiutil
import util
from eve.client.script.ui.control import entries as listentry
import carbonui.const as uiconst
import math
import base
import types
import uicls
import log
import localization
import searchUtil
import copy
from eve.common.script.util.notificationconst import groupNamePaths as notificationGroupNamePaths, GetTypeGroup, IsTypeInCommunications
import characterSettingsStorage.characterSettingsConsts as cSettings
GROUP_CHAR = 1
GROUP_LIST = 2
GROUP_CORP = 3
MAILLABELTRASH = -1
CORPTEXT = 'corp'
ALLIANCTEXT = 'alliance'
DEFAULTNUMMAILS = 30
MAXNUMMAILS = 100
MINNUMMAILS = 20
SAVE_INTERVAL = 120 * 1000
DELETE_INTERVAL = 0.3 * const.SEC
WHITE = (1.0, 1.0, 1.0)

class MailWindow(uicontrols.Window):
    __guid__ = 'form.MailWindow'
    __notifyevents__ = ['OnNewMailReceived', 'OnMailStartStopBlinkingTab']
    default_width = 600
    default_height = 450
    default_windowID = 'mail'
    default_captionLabelPath = 'Tooltips/Neocom/Mail'
    default_descriptionLabelPath = 'Tooltips/Neocom/Mail_description'
    default_iconNum = 'res:/ui/Texture/WindowIcons/evemail.png'

    def ApplyAttributes(self, attributes):
        uicontrols.Window.ApplyAttributes(self, attributes)
        if sm.GetService('mailSvc').IsFileCacheCorrupted():
            self.Close()
            raise UserError('MailCacheFileError')
        sm.GetService('mailSvc').SetBlinkNeocomState(False)
        self.SetHeaderIcon()
        settingsIcon = self.sr.headerIcon
        settingsIcon.state = uiconst.UI_NORMAL
        settingsIcon.GetMenu = self.GetArrowMenu
        settingsIcon.expandOnLeft = 1
        settingsIcon.hint = localization.GetByLabel('UI/Common/Settings')
        self.SetScope('station_inflight')
        self.SetMinSize([500, 350])
        self.SetTopparentHeight(0)
        self.mailInited = 0
        self.sr.mail = MailForm(name='mailform', parent=self.sr.main, pos=(0, 0, 0, 0))
        from eve.client.script.ui.shared.neocom.notifications import NotificationForm
        self.sr.notifications = NotificationForm(name='notificationform', parent=self.sr.main, pos=(0, 0, 0, 0))
        self.sr.tabs = uicontrols.TabGroup(name='tabs', parent=self.sr.main, tabs=[[localization.GetByLabel('UI/Mail/EveMail'),
          self.sr.mail,
          self,
          'mail'], [localization.GetByLabel('UI/Mail/Notifications/Notifications'),
          self.sr.notifications,
          self,
          'notifications']], groupID='tabs', autoselecttab=1, idx=0)
        shouldBlink = sm.GetService('mailSvc').ShouldTabBlink()
        if shouldBlink:
            uthread.new(self.OnNewMailReceived)

    def SelectMailTab(self):
        self.sr.tabs.SelectByIdx(0)

    def SelectNotificationTab(self):
        self.sr.tabs.SelectByIdx(1)

    def Load(self, key):
        if key == 'mail':
            self.LoadMail()
        elif key == 'notifications':
            self.LoadNotifications()

    def LoadMail(self):
        if getattr(self, 'mailIniting', 0):
            return
        if not getattr(self, 'mailInited', 0):
            self.mailIniting = 1
            self.sr.mail.Setup()
            if not self or self.destroyed:
                return
            self.mailInited = 1
            self.mailIniting = 0
        sm.GetService('mailSvc').SetBlinkTabState(False)
        self.sr.mail.LoadMailForm()

    def LoadNotifications(self):
        if not getattr(self, 'notificationsInited', 0):
            self.sr.notifications.Setup()
            self.notificationsInited = 1
        self.sr.notifications.LoadNotificationForm()

    def _OnClose(self, *args):
        if getattr(self, 'mailInited', 0):
            self.sr.mail._OnClose()
        uicontrols.Window._OnClose(self, *args)

    def OnNewMailReceived(self, *args):
        self.OnMailStartStopBlinkingTab('mail', blink=1)

    def OnMailStartStopBlinkingTab(self, configname, blink = 1):
        if self.sr.tabs.destroyed:
            return
        mailSettings = sm.GetService('mailSvc').GetMailSettings()
        if configname == 'mail':
            doBlinkTab = mailSettings.GetSingleValue(cSettings.MAIL_BLINK_TAB, True)
            if blink == 0 or doBlinkTab:
                self.sr.tabs.BlinkPanelByName(localization.GetByLabel('UI/Mail/EveMail'), blink)

    def GetArrowMenu(self, *args):
        m = [(uiutil.MenuLabel('UI/Common/Settings'), self.OpenMailSettings, ())]
        return m

    def OpenMailSettings(self, *args):
        if getattr(self, 'mailIniting', 0):
            raise UserError('CustomNotify', {'notify': localization.GetByLabel('UI/Mail/SystemLoading')})
        MailSettings.Open()


class MailForm(uiprimitives.Container):
    __guid__ = 'form.MailForm'
    __notifyevents__ = ['OnMyMaillistChanged',
     'OnMyLabelsChanged',
     'OnNewMailReceived',
     'OnMailTrashedDeleted',
     'OnMailSettingsChanged',
     'OnMailStatusUpdate',
     'OnMailCountersUpdate']

    def Setup(self):
        sm.RegisterNotify(self)
        self.viewing = None
        self.readTimer = 0
        self.startPos = 0
        self.scrollHeight = 0
        self.readingPaneVisible = settings.user.ui.Get('mail_readingPaneVisible', True)
        self.lastDeleted = 0
        self.inited = 0
        sortBy = settings.user.ui.Get('evemail_sortBy', localization.GetByLabel('UI/Mail/Received'))
        if sortBy in [localization.GetByLabel('UI/Mail/Status'),
         localization.GetByLabel('UI/Mail/Sender'),
         localization.GetByLabel('UI/Mail/Subject'),
         localization.GetByLabel('UI/Mail/Received')]:
            self.sortBy = sortBy
        else:
            self.sortBy = localization.GetByLabel('UI/Mail/Received')
        self.sortOrder = settings.user.ui.Get('evemail_sortOrder', True)
        self.sr.main = self
        self.DrawStuff()
        sm.GetService('mailSvc').TrySyncMail()
        if self and not self.destroyed:
            self.worker = uthread.new(self.SaveChangesWorker)
            self.inited = 1

    def CheckInited(self):
        if not self.inited:
            raise UserError('CustomNotify', {'notify': localization.GetByLabel('UI/Mail/SystemLoading')})

    def DrawStuff(self, *args):
        self.sr.toolbarCont = uiprimitives.Container(name='toolbarCont', parent=self.sr.main, align=uiconst.TOTOP, pos=(0, 0, 0, 50))
        leftContWidth = settings.user.ui.Get('evemail_leftContWidth', 200)
        self.sr.leftCont = uiprimitives.Container(name='leftCont', parent=self.sr.main, align=uiconst.TOLEFT, pos=(const.defaultPadding,
         0,
         leftContWidth,
         0))
        self.sr.btns = uicontrols.ButtonGroup(btns=[[localization.GetByLabel('UI/Mail/AddMailingList'),
          self.GetMailingListWnd,
          'self',
          None]], parent=self.sr.leftCont, line=0)
        self.sr.leftScroll = uicontrols.Scroll(name='leftScroll', parent=self.sr.leftCont)
        self.sr.leftScroll.multiSelect = 0
        self.sr.leftScroll.allowBrowsing = 0
        divider = Divider(name='divider', align=uiconst.TOLEFT, width=const.defaultPadding, parent=self.sr.main, state=uiconst.UI_NORMAL)
        divider.Startup(self.sr.leftCont, 'width', 'x', 180, 275)
        self.sr.bottomCont = uiprimitives.Container(name='bottomCont', parent=self.sr.main, align=uiconst.TOBOTTOM, pos=(0, 0, 0, 22))
        self.sr.expanderCont = uiprimitives.Container(name='expanderCont', parent=self.sr.bottomCont, align=uiconst.CENTER, pos=(0, 0, 16, 16))
        expander = uiprimitives.Sprite(parent=self.sr.expanderCont, pos=(5, 2, 11, 11), name='expandericon', state=uiconst.UI_NORMAL, texturePath='res:/UI/Texture/Shared/expanderDown.png', align=uiconst.TOPRIGHT)
        expander.OnClick = self.ChangeReadingPaneVisiblity
        self.sr.expander = expander
        self.sr.readingPaneCont = DragResizeCont(name='rightCont', parent=self.sr.main, align=uiconst.TOBOTTOM_PROP, settingsID='evemail_readingContProporations', minSize=0.1, maxSize=0.7)
        self.sr.readingPane = uicls.EditPlainText(setvalue='', parent=self.sr.readingPaneCont, align=uiconst.TOALL, readonly=1)
        self.sr.msgScroll = uicontrols.Scroll(name='msgScroll', parent=self.sr.main)
        self.sr.msgScroll.sr.id = 'mail_msgs'
        self.sr.msgScroll.sr.fixedColumns = {localization.GetByLabel('UI/Mail/Status'): 52}
        self.sr.msgScroll.sr.maxDefaultColumns = {localization.GetByLabel('UI/Mail/Subject'): 250}
        self.sr.msgScroll.Sort = self.SortMail
        self.sr.msgScroll.OnDelete = self.DeleteFromKeyboard
        self.sr.msgScroll.OnSelectionChange = self.MsgScrollSelectionChange
        self.sr.msgScroll.DrawHeaders = self.RefreshMsgScrollHeaders
        self.sr.msgScroll.Load(contentList=[], noContentHint=localization.GetByLabel('UI/Mail/FetchingMails'), ignoreSort=1)
        self.inited = True
        self.DrawToolbar()
        self.viewingLabel = 1
        self.viewingList = None

    def DrawToolbar(self, *args):
        actions = util.KeyVal()
        actions.composeClicked = self.ComposeClicked
        actions.replyClicked = self.ReplyClicked
        actions.replyAllClicked = self.ReplyAllClicked
        actions.forwardClicked = self.ForwardClicked
        actions.trashClicked = self.TrashClicked
        actions.deleteClicked = self.DeleteClicked
        self.sr.mailActions = MailActionPanel(name='mailActionCont', parent=self.sr.toolbarCont, align=uiconst.TOPLEFT, pos=(0, 0, 250, 50))
        self.sr.mailActions.Startup(actions)
        labelBtn = uix.GetBigButton(size=32, where=None, left=0, top=0, hint=localization.GetByLabel('UI/Mail/ManageLabels'), align=uiconst.RELATIVE)
        uiutil.MapIcon(labelBtn.sr.icon, 'res:/ui/Texture/WindowIcons/evemailtag.png', ignoreSize=True)
        labelBtn.OnClick = self.ManageLabels
        self.sr.mailActions.AddExtraButton(labelBtn, withSpace=1, size=32, hint=localization.GetByLabel('UI/Mail/ManageLabels'))
        self.sr.browseCont = uiprimitives.Container(name='browseCont', parent=self.sr.toolbarCont, align=uiconst.BOTTOMRIGHT, pos=(8, 0, 48, 40))
        self.sr.pageCount = uicontrols.EveLabelMedium(text='', parent=self.sr.browseCont, left=0, top=26, state=uiconst.UI_DISABLED, align=uiconst.CENTERTOP)
        btn = uix.GetBigButton(24, self.sr.browseCont, 0, 0)
        btn.OnClick = (self.BrowseMail, -1)
        btn.hint = localization.GetByLabel('UI/Common/Previous')
        btn.state = uiconst.UI_HIDDEN
        btn.sr.icon.LoadIcon('ui_23_64_1')
        self.sr.mailBackBtn = btn
        btn = uix.GetBigButton(24, self.sr.browseCont, 24, 0)
        btn.OnClick = (self.BrowseMail, 1)
        btn.hint = localization.GetByLabel('UI/Common/Next')
        btn.state = uiconst.UI_HIDDEN
        btn.sr.icon.LoadIcon('ui_23_64_2')
        self.sr.mailFwdBtn = btn
        self.SetReadingPaneVisibility(self.readingPaneVisible)

    def _OnClose(self, *args):
        if self.sr.leftCont:
            settings.user.ui.Set('evemail_leftContWidth', self.sr.leftCont.width)
        sm.UnregisterNotify(self)
        sm.GetService('mailSvc').SaveChangesToDisk()

    def SaveChangesWorker(self):
        while self and not self.destroyed:
            blue.pyos.synchro.SleepWallclock(SAVE_INTERVAL)
            try:
                sm.GetService('mailSvc').SaveChangesToDisk()
            except Exception:
                log.LogTraceback('SaveChangesWorker', 'Error while saving to disk...', severity=log.LGERR)
                sys.exc_clear()

    def LoadMailForm(self):
        self.ReloadAll()
        self.MsgScrollSelectionChange()

    def LoadLeftSide(self, *args):
        scrolllist = []
        groups = self.GetStaticLabelsGroups()
        scrolllist += groups
        scrolllist.insert(1, listentry.Get('Space', {'height': 16}))
        scrolllist.append(listentry.Get('Space', {'height': 16}))
        data = {'GetSubContent': self.GetLabelsSubContent,
         'MenuFunction': self.LabelGroupMenu,
         'label': localization.GetByLabel('UI/Mail/Labels'),
         'cleanLabel': localization.GetByLabel('UI/Mail/Labels'),
         'id': ('evemail', 'Labels', localization.GetByLabel('UI/Mail/Labels')),
         'state': 'locked',
         'BlockOpenWindow': 1,
         'showicon': 'ui_73_16_9',
         'showlen': 0,
         'groupName': 'labels',
         'groupItems': [],
         'updateOnToggle': 0}
        scrolllist.append(listentry.Get('Group', data))
        scrolllist.append(listentry.Get('Space', {'height': 16}))
        data = {'GetSubContent': self.GetMaillistSubContent,
         'label': localization.GetByLabel('UI/Mail/MailingLists'),
         'cleanLabel': localization.GetByLabel('UI/Mail/MailingLists'),
         'id': ('evemail', 'maillists', localization.GetByLabel('UI/Mail/MailingLists')),
         'state': 'locked',
         'BlockOpenWindow': 1,
         'showicon': 'ui_38_16_190',
         'showlen': 0,
         'groupName': 'mailinglists',
         'groupItems': [],
         'updateOnToggle': 0}
        scrolllist.append(listentry.Get('Group', data))
        self.sr.leftScroll.Load(contentList=scrolllist)
        self.UpdateCounters()

    def UpdateCounters(self):
        """
            Updates the 'new mail' counter for all the labels (not All Mails and mailing lists)
        """
        newMailsInGroups = {'labels': False,
         'mailinglists': False}
        static = [None,
         const.mailLabelInbox,
         const.mailLabelSent,
         const.mailLabelCorporation,
         const.mailLabelAlliance,
         MAILLABELTRASH]
        unreadCountsForLabels = sm.GetService('mailSvc').GetUnreadCounts().labels
        for key in unreadCountsForLabels.iterkeys():
            if unreadCountsForLabels.get(key, 0) > 0 and key not in static:
                newMailsInGroups['labels'] = True
                break

        myLists = sm.GetService('mailinglists').GetMyMailingLists()
        unreadCountsForLists = sm.GetService('mailSvc').GetUnreadCounts().lists
        for key in unreadCountsForLists.iterkeys():
            if unreadCountsForLists.get(key, 0) > 0 and key in myLists:
                newMailsInGroups['mailinglists'] = True
                break

        for each in self.sr.leftScroll.GetNodes():
            if each.get('currentView', -1) not in [-1, const.mailLabelSent]:
                count = unreadCountsForLabels.get(each.currentView, 0)
                self.TryChangePanelLabel(each, count)
            elif each.listID is not None:
                count = unreadCountsForLists.get(each.listID, 0)
                self.TryChangePanelLabel(each, count)
            elif each.groupName is not None:
                new = newMailsInGroups.get(each.groupName, False)
                self.TryChangePanelLabel(each, None, forceBold=new)

    def GetStaticLabelsGroups(self):
        """
            Gets the groups for the static labels
        """
        myLabels = sm.GetService('mailSvc').GetAllLabels()
        swatchColors = sm.GetService('mailSvc').GetSwatchColors()
        if self.viewingList is not None:
            viewingLabel = -100
        else:
            viewingLabel = self.viewingLabel
        scrolllist = []
        for label, id, icon in [(localization.GetByLabel('UI/Mail/LabelAllMails'), None, 'ui_73_16_5'),
         (localization.GetByLabel('UI/Mail/LabelInbox'), const.mailLabelInbox, 'ui_73_16_6'),
         (localization.GetByLabel('UI/Mail/LabelSent'), const.mailLabelSent, 'ui_73_16_7'),
         (localization.GetByLabel('UI/Common/Corp'), const.mailLabelCorporation, 'ui_73_16_32'),
         (localization.GetByLabel('UI/Common/Groups/Alliance'), const.mailLabelAlliance, 'ui_73_16_31'),
         (localization.GetByLabel('UI/Mail/LabelTrash'), MAILLABELTRASH, 'ui_73_16_11')]:
            labelInfo = myLabels.get(id, None)
            colorID = None
            color = 'ffffff'
            if labelInfo:
                colorID = labelInfo.get('color', None)
                color = swatchColors.get(colorID, (None, None))
                color = color[0]
            if id == MAILLABELTRASH:
                onClickFunction = self.LoadTrashGroup
            else:
                onClickFunction = self.LoadLabelGroup
            data = {'GetSubContent': self.GetLeftGroups,
             'label': label,
             'cleanLabel': label,
             'id': ('evemail', id, label),
             'state': 'locked',
             'BlockOpenWindow': 1,
             'disableToggle': 1,
             'expandable': 0,
             'showicon': icon,
             'colorID': colorID,
             'color': color,
             'showlen': 0,
             'groupItems': [],
             'hideNoItem': 1,
             'hideExpander': 1,
             'hideExpanderLine': 1,
             'selectGroup': 1,
             'OnClick': onClickFunction,
             'MenuFunction': self.StaticMenu,
             'isSelected': viewingLabel == id,
             'currentView': id,
             'DropData': self.OnGroupDropData}
            scrolllist.append(listentry.Get('MailGroup', data))

        return scrolllist

    def GetLeftGroups(self, items, *args):
        """
            gets the subcontent for the static gropus - they do not have sub content
        """
        return []

    def GetLabelsSubContent(self, items):
        """
            gets the subcontent for label group, the player defined labels
        """
        scrolllist = []
        myLabels = sm.GetService('mailSvc').GetAllLabels().values()
        unreadCounts = sm.GetService('mailSvc').GetUnreadCounts().labels
        swatchColors = sm.GetService('mailSvc').GetSwatchColors()
        if self.viewingList is not None:
            viewingLabel = -100
        else:
            viewingLabel = self.viewingLabel
        for each in myLabels:
            if getattr(each, 'static', 0):
                continue
            count = unreadCounts.get(each.labelID, 0)
            label = self.GetPanelLabel(each.name, count)
            colorID = each.color or 0
            color = swatchColors.get(colorID, (None, None))[0]
            data = util.KeyVal()
            data.cleanLabel = each.name
            data.label = label
            data.sublevel = 1
            data.currentView = each.labelID
            data.OnClick = self.LoadLabelGroup
            data.GetMenu = self.GetLabelMenu
            data.isSelected = viewingLabel == each.labelID
            data.OnDropData = self.OnGroupDropData
            data.color = color
            data.colorID = colorID
            scrolllist.append((each.name.lower(), listentry.Get('MailLabelEntry', data=data)))

        scrolllist = uiutil.SortListOfTuples(scrolllist)
        return scrolllist

    def GetMaillistSubContent(self, *args):
        """
            gets the subcontent for the mailinglists group, the mailinglists
        """
        scrolllist = []
        myLists = sm.GetService('mailinglists').GetMyMailingLists()
        unreadCounts = sm.GetService('mailSvc').GetUnreadCounts().lists
        for key, value in myLists.iteritems():
            count = unreadCounts.get(key, 0)
            label = self.GetPanelLabel(value.displayName, count)
            data = util.KeyVal()
            data.cleanLabel = value.displayName
            data.label = label
            data.sublevel = 1
            data.GetMenu = self.MaillistMenu
            data.isSelected = key == self.viewingList
            data.listID = key
            data.OnClick = self.LoadMailinglistMails
            data.listData = value
            scrolllist.append((value.displayName.lower(), listentry.Get('Generic', data=data)))

        scrolllist = uiutil.SortListOfTuples(scrolllist)
        return scrolllist

    def GetMailingListWnd(self, *args):
        MailinglistWnd.Open()

    def LeaveMaillist(self, listID, *args):
        sm.GetService('mailinglists').LeaveMaillist(listID)

    def DeleteMaillist(self, listID, *args):
        mailinglistName = sm.GetService('mailinglists').GetDisplayName(listID)
        if eve.Message('DeleteMailingList', {'mailinglistName': mailinglistName}, uiconst.YESNO) == uiconst.ID_YES:
            sm.GetService('mailinglists').DeleteMaillist(listID)

    def OpenMaillistSetup(self, listID, *args):
        windowID = 'MaillistSetupWindow_%s' % listID
        from eve.client.script.ui.shared.neocom.evemailingListConfig import MaillistSetupWindow
        MaillistSetupWindow.Open(windowID=windowID, mailingListID=listID)

    def SendMailToList(self, listID, *args):
        sm.GetService('mailSvc').SendMsgDlg(toListID=listID)

    def SendMailToCorp(self, corpID, *args):
        sm.GetService('mailSvc').SendMsgDlg(toCorpOrAllianceID=[corpID])

    def SendMailToAlliance(self, allianceID, *args):
        sm.GetService('mailSvc').SendMsgDlg(toCorpOrAllianceID=[allianceID])

    def LoadMailinglistMails(self, entry, *args):
        """
            load the mailinglist specified in the entry
        """
        self.startPos = 0
        self.viewingList = entry.sr.node.listID
        self.viewingLabel = None
        self.LoadFromLabelIDOrLabelID(listID=entry.sr.node.listID)

    def MaillistMenu(self, entry):
        m = []
        listID = entry.sr.node.listID
        data = entry.sr.node.listData
        if not data.isMuted:
            m.append((uiutil.MenuLabel('UI/Mail/SendMailToList'), self.SendMailToList, (listID,)))
        if data.isOperator or data.isOwner:
            m.append((uiutil.MenuLabel('UI/Mail/OpenMailingListMgmt'), self.OpenMaillistSetup, (listID,)))
        m.append(None)
        name = entry.sr.node.cleanLabel
        text = uiutil.MenuLabel('UI/Mail/MarkAllAsReadWithFolderName', {'folderName': name})
        m.append((text, self.MarkAsReadByList, (listID, name)))
        text = uiutil.MenuLabel('UI/Mail/TrashAllWithFolderName', {'folderName': name})
        m.append((text, self.MoveToTrashByList, (listID, name)))
        m.append(None)
        if data.isOwner:
            m.append((uiutil.MenuLabel('UI/Mail/DeleteMailingList'), self.DeleteMaillist, (listID,)))
        else:
            m.append((uiutil.MenuLabel('UI/Mail/LeaveMailingList'), self.LeaveMaillist, (listID,)))
        return m

    def GetLabelMenu(self, entry):
        labelID = entry.sr.node.currentView
        m = []
        m.append((uiutil.MenuLabel('UI/Mail/AssignColor'), self.GetAssignColorWnd, (labelID,)))
        m.append((uiutil.MenuLabel('UI/Mail/LabelRename'), sm.GetService('mailSvc').RenameLabelFromUI, (labelID,)))
        m.append(None)
        text = uiutil.MenuLabel('UI/Mail/MarkAllAsReadWithFolderName', {'folderName': entry.sr.node.cleanLabel})
        m.append((text, self.MarkAsReadByLabel, (labelID, entry.sr.node.cleanLabel)))
        text = uiutil.MenuLabel('UI/Mail/TrashAllWithFolderName', {'folderName': entry.sr.node.cleanLabel})
        m.append((text, self.MoveToTrashByLabel, (labelID, entry.sr.node.cleanLabel)))
        m.append(None)
        m.append((uiutil.MenuLabel('UI/Common/Delete'), sm.GetService('mailSvc').DeleteLabelFromUI, (labelID, entry.sr.node.label)))
        return m

    def GetAssignColorWnd(self, labelID):
        blue.pyos.synchro.Yield()
        doneCallBack = sm.StartService('mailSvc').ChangeLabelColorFromUI
        doneArgs = (labelID,)
        sm.GetService('mailSvc').GetAssignColorWnd(labelID, doneCallBack=doneCallBack, doneArgs=doneArgs)

    def CheckLabelName(self, dict, *args):
        name = dict.get('name', '').strip()
        myLabelNames = [ label.name for label in sm.GetService('mailSvc').GetAllLabels(assignable=0).values() ]
        if name in myLabelNames:
            return localization.GetByLabel('UI/Mail/LabelNameTaken')

    def LoadLabelGroup(self, entry):
        """
            load the label group specified in the entry
        """
        self.startPos = 0
        self.viewingLabel = entry.sr.node.currentView
        self.viewingList = None
        entry.label = entry.sr.node.label
        self.LoadFromLabelIDOrLabelID(labelID=entry.sr.node.currentView)

    def LoadTrashGroup(self, entry):
        """
            Loads the trash mails
        """
        self.startPos = 0
        self.viewingLabel = entry.sr.node.currentView
        self.viewingList = None
        self.LoadFromLabelIDOrLabelID(labelID=MAILLABELTRASH)

    def ReloadAll(self, *args):
        self.LoadLeftSide()
        self.ReloadMails()

    def ReloadMails(self, refreshing = 0):
        """
            Reloads the message scroll with the label/list that is currently being viewed
        """
        labelID = self.viewingLabel
        listID = self.viewingList
        self.LoadFromLabelIDOrLabelID(labelID=labelID, listID=listID, refreshing=refreshing)

    def LoadFromLabelIDOrLabelID(self, labelID = None, listID = None, refreshing = 0):
        mailInfo = self.GetMailInfo(labelID, listID)
        self.LoadMails(mails=mailInfo.sorted, labelID=labelID, refreshing=refreshing, totalNum=mailInfo.totalNum)
        self.UpdateCounters()

    def GetMailInfo(self, labelID = None, listID = None):
        mailSettings = sm.GetService('mailSvc').GetMailSettings()
        numMails = max(1, mailSettings.GetSingleValue(cSettings.MAILS_PER_PAGE, DEFAULTNUMMAILS))
        if labelID == MAILLABELTRASH:
            mailInfo = sm.GetService('mailSvc').GetTrashedMails(orderBy=self.sortBy, ascending=self.sortOrder, pos=self.startPos, count=numMails)
        elif listID is not None:
            mailInfo = sm.GetService('mailSvc').GetMailsByLabelOrListID(listID=listID, orderBy=self.sortBy, ascending=self.sortOrder, pos=self.startPos, count=numMails)
        else:
            mailInfo = sm.GetService('mailSvc').GetMailsByLabelOrListID(labelID=labelID, orderBy=self.sortBy, ascending=self.sortOrder, pos=self.startPos, count=numMails)
        return mailInfo

    def LoadMails(self, mails = [], labelID = None, refreshing = 0, totalNum = None):
        """
            load the message scroll
        
            ARGUMENTS:
                mails       a list of keyvals with info about each mail
        
                labelID     int (if specified). The ID of the label group
                            that is being loaded
                            
                refreshing  0 or 1 depending on whether the scroll is being
                            reloaded or just loaded for the first time
        
                totalNum    the total number of mails that belong to the list/label
                            that is being loaded
                           
        """
        sel = self.sr.msgScroll.GetSelected()
        selIDs = [ msg.messageID for msg in sel ]
        pos = self.sr.msgScroll.GetScrollProportion()
        scrolllist = []
        myLabels = sm.GetService('mailSvc').GetAllLabels(assignable=0)
        for info in mails:
            entry = self.GetMsgEntry(info, labelID, selIDs, myLabels, refreshing)
            scrolllist.append(entry)

        self.sr.msgScroll.labelID = labelID
        scrollHeaders = [localization.GetByLabel('UI/Mail/Status'),
         localization.GetByLabel('UI/Mail/Sender'),
         localization.GetByLabel('UI/Mail/Subject'),
         localization.GetByLabel('UI/Mail/Received'),
         localization.GetByLabel('UI/Mail/Labels')]
        self.sr.msgScroll.Load(contentList=scrolllist, headers=scrollHeaders, noContentHint=localization.GetByLabel('UI/Mail/NoMailsFound'), ignoreSort=1, reversesort=self.sortOrder, sortby=self.sortBy)
        if not refreshing:
            self.ClearReadingPane()
        else:
            self.sr.msgScroll.ScrollToProportion(pos)
        if totalNum is not None:
            self.ShowHideBrowse(totalNum)
        self.ShowHideToolbarButtons()

    def RefreshMsgScrollHeaders(self, headers, tabs = []):
        uicontrols.Scroll.DrawHeaders(self.sr.msgScroll, headers, tabs)
        labelID = getattr(self.sr.msgScroll, 'labelID', None)
        senderColumn = uiutil.FindChild(self.sr.msgScroll, localization.GetByLabel('UI/Mail/Sender'))
        if senderColumn is not None:
            if labelID == const.mailLabelSent:
                text = localization.GetByLabel('UI/Mail/Recipient')
            else:
                text = localization.GetByLabel('UI/Mail/Sender')
            senderColumn.sr.label.text = text
        dateColumn = uiutil.FindChild(self.sr.msgScroll, localization.GetByLabel('UI/Mail/Received'))
        if dateColumn is not None:
            if labelID == const.mailLabelSent:
                text = localization.GetByLabel('UI/Mail/DateSent')
            else:
                text = localization.GetByLabel('UI/Mail/Received')
            dateColumn.sr.label.text = text

    def GetMsgEntry(self, info, labelID, selIDs, myLabels, refreshing = 0):
        labels = self.GetLabelText(info.labels, myLabels)
        data = util.KeyVal()
        data.messageID = info.messageID
        data.data = info.copy()
        data.currentView = labelID
        data.OnClick = self.LoadReadingPaneFromEntry
        data.OnDblClick = self.DblMailClickEntry
        data.GetMenu = self.GetMsgMenu
        data.ignoreRightClick = 1
        data.isSelected = refreshing and info.messageID in selIDs
        date = util.FmtDate(info.sentDate, 'ls')
        data.id = info.messageID
        if labelID == const.mailLabelSent:
            name = sm.GetService('mailSvc').GetRecipient(info, getName=1)
        else:
            name = info.senderName
        data.name = name
        data.label = '<t>'.join(('',
         name,
         info.subject,
         date,
         labels))
        data.cleanLabel = data.label
        entry = listentry.Get('MailEntry', data=data)
        return entry

    def GetLabelText(self, labels, myLabels):
        """
            finds what label text should be on this mail entry
        """
        labelText = ''
        labelNames = []
        swatchColors = sm.GetService('mailSvc').GetSwatchColors()
        for labelID in labels:
            label = myLabels.get(labelID, None)
            if label is not None:
                labelNames.append((label.name, label.color))

        labelNames.sort()
        for each, colorID in labelNames:
            if colorID is None or colorID not in swatchColors:
                colorID = 0
            color = swatchColors.get(colorID)[0]
            labelText += '<color=0xBF%s>%s</color>, ' % (color, each)

        labelText = labelText[:-2]
        return labelText

    def ShowHideBrowse(self, totalNum):
        """
            figuring out if the browse buttons are needed
        """
        btnDisplayed = 0
        if self.startPos == 0:
            self.sr.mailBackBtn.state = uiconst.UI_HIDDEN
        else:
            self.sr.mailBackBtn.state = uiconst.UI_NORMAL
            btnDisplayed = 1
        mailSettings = sm.GetService('mailSvc').GetMailSettings()
        numMails = max(1, mailSettings.GetSingleValue(cSettings.MAILS_PER_PAGE, DEFAULTNUMMAILS))
        if self.startPos + numMails >= totalNum:
            self.sr.mailFwdBtn.state = uiconst.UI_HIDDEN
        else:
            self.sr.mailFwdBtn.state = uiconst.UI_NORMAL
            btnDisplayed = 1
        if btnDisplayed:
            numPages = int(math.ceil(totalNum / float(numMails)))
            currentPage = self.startPos / numMails + 1
            self.sr.pageCount.text = '%s/%s' % (currentPage, numPages)
        else:
            self.sr.pageCount.text = ''

    def ClearReadingPane(self):
        self.sr.readingPane.SetText('')
        self.viewing = None

    def ChangeReadingPaneVisiblity(self, *args):
        if self.readingPaneVisible is True:
            self.SetReadingPaneVisibility(on=False)
        else:
            self.SetReadingPaneVisibility(on=True)
        settings.user.ui.Set('mail_readingPaneVisible', self.readingPaneVisible)

    def SetReadingPaneVisibility(self, on = True):
        if on:
            self.readingPaneVisible = True
            self.sr.expander.hint = localization.GetByLabel('UI/Mail/HideReadingPane')
            self.sr.expander.texturePath = 'res:/UI/Texture/Shared/expanderDown.png'
            sel = self.sr.msgScroll.GetSelected()
            if len(sel) > 0:
                self.viewing = sel[0]
            self.ShowHideReadingPane(show=1)
            if self.viewing is not None:
                self.LoadReadingPane(self.viewing)
        else:
            self.readingPaneVisible = False
            self.sr.expander.hint = localization.GetByLabel('UI/Mail/ShowReadingPane')
            self.sr.expander.texturePath = 'res:/UI/Texture/Shared/expanderUp.png'
            self.ShowHideReadingPane(show=0)

    def ShowHideReadingPane(self, show):
        if show:
            self.sr.readingPaneCont.state = uiconst.UI_PICKCHILDREN
            self.sr.readingPane._OnResize()
        else:
            self.sr.readingPaneCont.state = uiconst.UI_HIDDEN

    def OpenMailSettings(self, *args):
        MailSettings.Open()

    def DblMailClickEntry(self, entry):
        if not entry or entry.destroyed:
            return
        node = entry.sr.node
        sm.GetService('mailSvc').OnOpenPopupMail(node.data)
        mail = sm.GetService('mailSvc').GetMailByID(node.messageID)
        if self and not self.destroyed:
            self.TryReloadNode(node, mail)

    def LoadReadingPaneFromEntry(self, entry):
        """
            displays the mail in the clicked entry of the scroll
        """
        self.ShowHideReadingPane(show=self.readingPaneVisible)
        uthread.new(self.LoadReadingPaneFromNode, entry.sr.node)

    def LoadReadingPaneFromNode(self, node):
        shift = uicore.uilib.Key(uiconst.VK_SHIFT)
        if not shift:
            self.LoadReadingPane(node)

    def LoadReadingPane(self, node):
        self.readTimer = 0
        if node not in self.sr.msgScroll.GetNodes():
            return
        if self.sr.readingPaneCont.state != uiconst.UI_HIDDEN:
            txt = sm.GetService('mailSvc').GetMailText(node.data)
            self.sr.readingPane.SetText(txt)
            self.viewing = node.messageID
            if not node.data.read:
                mail = sm.GetService('mailSvc').GetMailByID(node.messageID)
                if self and not self.destroyed:
                    self.TryReloadNode(node, mail)

    def OnMailStatusUpdate(self, replyTo, forwardedFrom, forcedIDs = []):
        if not self.inited:
            return
        mailList = forcedIDs[:]
        if replyTo:
            mailList.append(replyTo)
        if forwardedFrom:
            mailList.append(forwardedFrom)
        self.RefreshEntriesFromIDs(mailList)

    def RefreshEntriesFromIDs(self, mailIDs):
        nodes = []
        for node in self.sr.msgScroll.GetNodes():
            if node.messageID in mailIDs:
                nodes.append(node)

        self.RefreshEntries(mailIDs, nodes)

    def RefreshEntries(self, mailIDs, nodes):
        mails = sm.GetService('mailSvc').GetMailsByIDs(mailIDs)
        for node in nodes:
            mailData = mails.get(node.messageID, None)
            if mailData is not None:
                self.TryReloadNode(node, mailData)

    def TryReloadNode(self, node, data):
        node.data = data.copy()
        panel = node.Get('panel', None)
        if panel is None:
            return
        panel.LoadMailEntry(node)

    def RefreshLabels(self, nodes, mailIDs):
        myLabels = sm.GetService('mailSvc').GetAllLabels(assignable=0)
        mails = sm.GetService('mailSvc').GetMailsByIDs(mailIDs)
        nodesToRemove = {}
        for node in nodes:
            mailData = mails.get(node.messageID, None)
            if mailData is not None:
                shouldRemove = self.RefreshLabel(node, mailData, myLabels)
                if shouldRemove:
                    nodesToRemove[node.messageID] = node

        if len(nodesToRemove) > 0:
            self.GoRemoveEntries(nodesToRemove.values(), nodesToRemove.keys())

    def RefreshLabel(self, node, data, myLabels):
        """
            The labels of this mail have changed but we dont want to reload all the scroll
            Returns True if the node should be removed from the scroll but False if it shouldnt be
        """
        if node.currentView is not None and node.currentView not in data.labels + [MAILLABELTRASH]:
            return True
        node.data = data.copy()
        labelText = self.GetLabelText(data.labels, myLabels)
        date = util.FmtDate(node.data.sentDate, 'ls')
        node.cleanLabel = '<t>'.join(('',
         node.name,
         node.data.subject,
         date,
         labelText))
        panel = node.Get('panel', None)
        if panel is None:
            return
        panel.UpdateLabel(data)
        return False

    def MsgScrollSelectionChange(self, sel = [], *args):
        """
            when what is selected in the message scroll has changed, we need to
            figure out what toolbar buttons should be visible
        """
        self.ShowHideToolbarButtons(sel=sel)
        if len(sel) == 0:
            return
        node = sel[0]
        if self.viewing != node.messageID:
            self.readTimer = base.AutoTimer(1000, self.LoadReadingPane, node)

    def ShowHideToolbarButtons(self, sel = []):
        """
            figuring out what buttons should be visible based on how many messages
            are selected in the message scroll
        """
        if len(sel) < 1:
            sel = self.sr.msgScroll.GetSelected()
        numSelected = len(sel)
        showDelete = self.viewingLabel == MAILLABELTRASH
        if numSelected == 0:
            self.sr.mailActions.SetDeleteVisibility(disabled=1, showDelete=showDelete)
        else:
            self.sr.mailActions.SetDeleteVisibility(disabled=0, showDelete=showDelete)
        if numSelected == 1:
            if sel[0].data.statusMask & const.mailStatusMaskAutomated == const.mailStatusMaskAutomated:
                self.sr.mailActions.SingleMsgBtnStateAllowFwd()
            else:
                self.sr.mailActions.SingleMsgBtnsState(disabled=0)
        else:
            self.sr.mailActions.SingleMsgBtnsState(disabled=1)

    def SortMail(self, by = None, reversesort = 0, forceHilite = 0):
        """
            overwriting the Sort() method in the scroll
        """
        scroll = self.sr.msgScroll
        if by == localization.GetByLabel('UI/Mail/Labels'):
            return
        self.sortBy = by
        self.sortOrder = reversesort
        settings.user.ui.Set('evemail_sortBy', by)
        settings.user.ui.Set('evemail_sortOrder', reversesort)
        self.startPos = 0
        self.ReloadMails()
        if scroll.sr.sortBy != by or forceHilite:
            scroll.HiliteSorted(by, reversesort)
            scroll.sr.sortBy = by

    def GetMsgMenu(self, entry, *args):
        """
            get the menu for the entries in the message scroll
            some of the can be read and others are unread, so there is number
            after each menu options if it applies to more than 1 entry
        """
        trashed = entry.sr.node.data.trashed
        sel = self.sr.msgScroll.GetSelected()
        selIDs = [ x.id for x in sel ]
        msgID = entry.sr.node.messageID
        if msgID not in selIDs:
            selIDs = [msgID]
            sel = [entry.sr.node]
        m = []
        readMails = {}
        unreadMails = {}
        for mail in sel:
            if mail.data.read:
                readMails[mail.id] = mail
            else:
                unreadMails[mail.id] = mail

        if len(readMails) > 0:
            m.append((uiutil.MenuLabel('UI/Mail/MarkAsUnread'), self.MarkAsUnread, (readMails.keys(), readMails.values())))
        if len(unreadMails) > 0:
            m.append((uiutil.MenuLabel('UI/Mail/MarkAsRead'), self.MarkAsRead, (unreadMails.keys(), unreadMails.values())))
        if trashed:
            m.append(None)
            m.append((uiutil.MenuLabel('UI/Mail/Restore'), self.RestoreMail, (sel, selIDs)))
            m.append(None)
            if len(sel) == 1:
                m += self.GetSenderMenu(sel[0])
            m.append((uiutil.MenuLabel('UI/Mail/Delete'), self.DeleteMail, (sel, selIDs)))
        else:
            assignLabelMenu = self.GetAssignLabelMenu(sel, selIDs)
            if len(assignLabelMenu) > 0:
                m.append((uiutil.MenuLabel('UI/Mail/AssignLabel'), assignLabelMenu))
            removeLabelMenu = self.GetRemoveLabelMenu(sel, selIDs)
            if len(removeLabelMenu) > 0:
                m.append((uiutil.MenuLabel('UI/Mail/LabelRemove'), removeLabelMenu))
            m.append(None)
            if len(sel) == 1:
                m += self.GetSenderMenu(sel[0])
            m.append((uiutil.MenuLabel('UI/Mail/Trash'), self.TrashMail, (sel, selIDs)))
        return m

    def GetSenderMenu(self, node):
        charMenu = []
        m = []
        itemID = None
        typeID = None
        text = localization.GetByLabel('UI/Common/Character')
        if node.data.statusMask & const.mailStatusMaskAutomated == const.mailStatusMaskAutomated:
            return m
        if node.currentView == const.mailLabelSent:
            recipient = sm.GetService('mailSvc').GetRecipient(node.data, getName=0)
            if recipient > 0:
                itemID = recipient
                if util.IsCharacter(itemID):
                    typeID = const.typeCharacterAmarr
                elif util.IsCorporation(itemID):
                    typeID = const.typeCorporation
                    text = localization.GetByLabel('UI/Common/Corporation')
                elif util.IsAlliance(itemID):
                    typeID = const.typeAlliance
                    text = localization.GetByLabel('UI/Common/Alliance')
        else:
            itemID = node.data.senderID
            typeID = const.typeCharacterAmarr
        if itemID:
            charMenu = sm.GetService('menu').GetMenuFormItemIDTypeID(itemID, typeID)
        if len(charMenu):
            m.append((text, charMenu))
            m.append(None)
        return m

    def GetAssignLabelMenu(self, sel, selIDs, *args):
        m = []
        myLabels = sm.GetService('mailSvc').GetAllLabels(assignable=1).values()
        labelMask = const.maxInt
        for node in sel:
            labelMask = labelMask & node.data.labelMask

        for each in myLabels:
            labelID = each.labelID
            if labelMask & labelID == labelID:
                continue
            label = each.name
            static = getattr(each, 'static', 0)
            if static:
                label = '  %s' % each.labelID
            m.append((label, (each.name, self.AssignLabelFromMenu, (sel,
               selIDs,
               each.labelID,
               each.name))))

        m = uiutil.SortListOfTuples(m)
        return m

    def GetRemoveLabelMenu(self, sel, selIDs, *args):
        m = []
        myLabels = sm.GetService('mailSvc').GetAllLabels(assignable=1).values()
        labelMask = 0
        for node in sel:
            labelMask = labelMask | node.data.labelMask

        for each in myLabels:
            labelID = each.labelID
            if labelMask & labelID != labelID:
                continue
            label = each.name
            static = getattr(each, 'static', 0)
            if static:
                label = '  %s' % labelID
            m.append((label, (each.name.lower(), self.RemoveLabelFromMenu, (sel,
               selIDs,
               each.labelID,
               each.name))))

        m = uiutil.SortListOfTuples(m)
        return m

    def AssignLabelFromMenu(self, sel, selIDs, labelID, labelName):
        self.AssignLabelFromMailWnd(sel, selIDs, labelID)
        text = localization.GetByLabel('UI/Mail/LabelAssigned', labelName=labelName, numMails=len(selIDs))
        eve.Message('CustomNotify', {'notify': text})

    def AssignLabelFromMailWnd(self, sel, selIDs, labelID):
        sm.StartService('mailSvc').AssignLabels(selIDs, labelID)
        self.RefreshLabels(sel, selIDs)

    def RemoveLabelFromMenu(self, sel, selIDs, labelID, labelName):
        sm.StartService('mailSvc').RemoveLabels(selIDs, labelID)
        text = localization.GetByLabel('UI/Mail/LabelRemoved', labelName=labelName, numMails=len(selIDs))
        eve.Message('CustomNotify', {'notify': text})
        self.RefreshLabels(sel, selIDs)

    def TrashMail(self, mails, mailIDs):
        sm.GetService('mailSvc').MoveMessagesToTrash(mailIDs)
        self.GoRemoveEntries(mails, mailIDs)
        sm.ScatterEvent('OnMessageChanged', const.mailTypeMail, mailIDs, 'trashed')
        self.UpdateCounters()

    def DeleteMail(self, mails, mailIDs):
        sm.GetService('mailSvc').DeleteMails(mailIDs)
        self.GoRemoveEntries(mails, mailIDs)
        sm.ScatterEvent('OnMessageChanged', const.mailTypeMail, mailIDs, 'deleted')

    def RestoreMail(self, mails, mailIDs):
        sm.GetService('mailSvc').MoveMessagesFromTrash(mailIDs)
        self.GoRemoveEntries(mails, mailIDs)

    def MarkAsUnread(self, mailIDs, mails):
        sm.GetService('mailSvc').MarkMessagesAsUnread(mailIDs)
        self.RefreshEntries(mailIDs, mails)

    def MarkAsRead(self, mailIDs, mails, *args):
        sm.GetService('mailSvc').MarkMessagesAsRead(mailIDs)
        self.RefreshEntries(mailIDs, mails)

    def LabelGroupMenu(self, entry, *args):
        m = []
        m.append((uiutil.MenuLabel('UI/Mail/ManageLabels'), self.ManageLabels))
        return m

    def StaticMenu(self, entry, *args):
        currentView = entry.currentView
        m = []
        if currentView == const.mailLabelCorporation and not util.IsNPC(session.corpid):
            m.append((uiutil.MenuLabel('UI/Mail/SendMailToCorp'), self.SendMailToCorp, (session.corpid,)))
        elif currentView == const.mailLabelAlliance and session.allianceid is not None and session.corprole & const.corpRoleChatManager == const.corpRoleChatManager:
            m.append((uiutil.MenuLabel('UI/Mail/SendMailToAlliance'), self.SendMailToAlliance, (session.allianceid,)))
        if currentView is None:
            text = uiutil.MenuLabel('UI/Mail/MarkAllAsReadWithFolderName', {'folderName': localization.GetByLabel('UI/Common/All')})
            m.append((text, self.MarkAllAsRead, ()))
            text = uiutil.MenuLabel('UI/Mail/TrashAllWithFolderName', {'folderName': localization.GetByLabel('UI/Common/All')})
            m.append((text, self.MoveAllToTrash, ()))
        elif currentView == MAILLABELTRASH:
            m.append((uiutil.MenuLabel('UI/Mail/RestoreAll'), self.MoveAllFromTrash, ()))
            m.append((uiutil.MenuLabel('UI/Mail/EmptyTrash'), self.EmptyTrash, ()))
        else:
            m.append((uiutil.MenuLabel('UI/Mail/AssignColor'), self.GetAssignColorWnd, (entry.currentView,)))
            m.append(None)
            text = uiutil.MenuLabel('UI/Mail/MarkAllAsReadWithFolderName', {'folderName': entry.cleanLabel})
            m.append((text, self.MarkAsReadByLabel, (entry.currentView, entry.cleanLabel)))
            text = uiutil.MenuLabel('UI/Mail/TrashAllWithFolderName', {'folderName': entry.cleanLabel})
            m.append((text, self.MoveToTrashByLabel, (entry.currentView, entry.cleanLabel)))
        return m

    def MarkAllAsRead(self, *args):
        if eve.Message('EvemailMailMarkAllRead', {}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
            sm.GetService('mailSvc').MarkAllAsRead()
            self.ReloadAll()

    def MoveAllToTrash(self, *args):
        if eve.Message('EvemailMailTrashAll', {}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
            sm.GetService('mailSvc').MoveAllToTrash()
            self.ReloadAll()

    def MoveAllFromTrash(self, *args):
        if eve.Message('EvemailMailRestoreAll', {}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
            sm.GetService('mailSvc').MoveAllFromTrash()
            self.ReloadAll()

    def EmptyTrash(self, *args):
        if eve.Message('EvemailMaillDeleteAll', {}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
            sm.GetService('mailSvc').EmptyTrash()
            self.ReloadAll()

    def MarkAsReadByLabel(self, labelID, name, *args):
        if eve.Message('EvemailMailReadLabelGroup', {'labelName': name}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
            sm.GetService('mailSvc').MarkAsReadByLabel(labelID)
            self.ReloadAll()

    def MarkAsReadByList(self, listID, name, *args):
        if eve.Message('EvemailMailReadMailinglistGroup', {'listName': name}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
            sm.GetService('mailSvc').MarkAsReadByList(listID)
            self.ReloadAll()

    def MoveToTrashByLabel(self, labelID, name, *args):
        if eve.Message('EvemailMailTrashLabelGroup', {'labelName': name}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
            sm.GetService('mailSvc').MoveToTrashByLabel(labelID)
            self.ReloadAll()

    def MoveToTrashByList(self, listID, name, *args):
        if eve.Message('EvemailMailTrashMailinglistGroup', {'listName': name}, uiconst.YESNO, suppress=uiconst.ID_YES) == uiconst.ID_YES:
            sm.GetService('mailSvc').MoveToTrashByList(listID)
            self.ReloadAll()

    def GoRemoveEntries(self, nodes, mailIDs):
        if getattr(self, 'removingEntries', 0):
            return
        self.removingEntries = 1
        pos = self.sr.msgScroll.GetScrollProportion()
        self.sr.msgScroll.RemoveEntries(nodes)
        if self.viewing in mailIDs:
            self.ClearReadingPane()
        mailInfo = self.GetMailInfo(labelID=self.viewingLabel, listID=self.viewingList)
        mails = mailInfo.sorted
        mailsInScroll = [ msg.id for msg in self.sr.msgScroll.GetNodes() ]
        mailsToAdd = []
        for info in mails:
            if info.messageID not in mailsInScroll:
                mailsToAdd.append(info)

        if len(mailsToAdd) < 1:
            self.removingEntries = 0
            if len(self.sr.msgScroll.GetNodes()) < 1:
                self.BrowseMail(-1)
            return
        myLabels = sm.GetService('mailSvc').GetAllLabels(assignable=0)
        entriesToAdd = []
        for each in mailsToAdd:
            entry = self.GetMsgEntry(each, self.viewingLabel, [], myLabels, 0)
            entriesToAdd.append(entry)

        self.sr.msgScroll.AddEntries(-1, entriesToAdd, ignoreSort=1)
        self.sr.msgScroll.ScrollToProportion(pos)
        self.ShowHideBrowse(mailInfo.totalNum)
        self.removingEntries = 0

    def ComposeClicked(self, *args):
        self.CheckInited()
        sm.GetService('mailSvc').SendMsgDlg()

    def ReplyClicked(self, *args):
        self.CheckInited()
        self.Reply(all=0)

    def ForwardClicked(self, *args):
        """
            forwards the e-mail that is currently selected
        """
        self.CheckInited()
        sel = self.sr.msgScroll.GetSelected()
        if len(sel) < 1:
            return
        msg = sel[0]
        sm.GetService('mailSvc').GetForwardWnd(msg.data)

    def ReplyAllClicked(self, *args):
        self.CheckInited()
        self.Reply(all=1)

    def DeleteFromKeyboard(self, *args):
        self.CheckInited()
        delete = self.viewingLabel == MAILLABELTRASH
        if blue.os.GetWallclockTime() - self.lastDeleted < DELETE_INTERVAL:
            eve.Message('uiwarning03')
            return
        if delete:
            self.DeleteClicked()
        else:
            self.TrashClicked()
        self.UpdateCounters()
        self.lastDeleted = blue.os.GetWallclockTime()

    def TrashClicked(self, *args):
        self.CheckInited()
        self.TrashDeleteFunctionality('trashed')

    def DeleteClicked(self, *args):
        self.CheckInited()
        self.TrashDeleteFunctionality('deleted')

    def TrashDeleteFunctionality(self, what):
        selected = self.sr.msgScroll.GetSelected()
        if len(selected) < 1:
            return
        idx = selected[0].idx
        messageIDs = [ mail.messageID for mail in selected ]
        if what == 'trashed':
            self.TrashMail(selected, messageIDs)
        elif what == 'deleted':
            self.DeleteMail(selected, messageIDs)
        numChildren = len(self.sr.msgScroll.GetNodes())
        newIdx = min(idx, numChildren - 1)
        newSelectedNode = self.sr.msgScroll.GetNode(newIdx)
        if newSelectedNode is not None:
            self.sr.msgScroll.SelectNode(newSelectedNode)

    def ManageLabels(self, *args):
        self.CheckInited()
        ManageLabelsExistingMails.Open()

    def BrowseMail(self, backforth, *args):
        """
            called when one of the browse window is clicked
        """
        mailSettings = sm.GetService('mailSvc').GetMailSettings()
        numMails = max(1, mailSettings.GetSingleValue(cSettings.MAILS_PER_PAGE, DEFAULTNUMMAILS))
        pos = max(0, self.startPos + numMails * backforth)
        self.startPos = pos
        self.ReloadMails()

    def Reply(self, all = 0):
        """
            currently the mail replied to is the one that was last displayed
        """
        sel = self.sr.msgScroll.GetSelected()
        if len(sel) < 1:
            return
        msg = sel[0]
        if msg is None:
            return
        sm.GetService('mailSvc').GetReplyWnd(msg.data, all)

    def OnMyMaillistChanged(self, *args):
        if not self.inited:
            return
        self.LoadLeftSide()

    def OnMyLabelsChanged(self, labelType, created = None, *args):
        if labelType == 'mail_labels':
            if not self.inited:
                return
            self.ReloadAll()

    def OnMailSettingsChanged(self, *args):
        if not self.inited:
            return
        self.startPos = 0
        self.ReloadMails()

    def OnNewMailReceived(self, *args):
        if not self.inited:
            return
        self.UpdateCounters()

    def OnMailCountersUpdate(self, *args):
        if not self.inited:
            return
        self.UpdateCounters()

    def OnMailTrashedDeleted(self, mail, force = 0):
        """
            This event is scattered when a mail is deleted from outside the window, either
            player action (force=0) or GM (force=1)
            Figure out if the message scroll needs to be reloaded
        """
        if not self.inited:
            return
        reload = force
        if not force:
            if self.viewingLabel == MAILLABELTRASH:
                reload = 1
            elif not mail.trashed:
                if self.viewingList is not None:
                    if self.viewingList == mail.toListID:
                        reload = 1
                elif self.viewingLabel is None:
                    reload = 1
                elif self.viewingLabel in mail.labels:
                    reload = 1
        if reload:
            self.ReloadMails(refreshing=1)
        self.UpdateCounters()

    def TryChangePanelLabel(self, node, count, forceBold = False):
        panel = node.Get('panel', None)
        label = self.GetPanelLabel(node.cleanLabel, count, forceBold)
        node.label = label
        if panel is None:
            return
        panelLabel = label
        panel.sr.label.text = panelLabel
        if hasattr(panel, 'UpdateHint'):
            panel.UpdateHint()

    def GetPanelLabel(self, label, count, forceBold = False):
        if count > 0:
            return '<b>' + localization.GetByLabel('UI/Mail/FolderLabelWithCount', folderName=label, unreadCount=count) + '</b>'
        elif forceBold:
            return '<b>' + label + '</b>'
        else:
            return label

    def OnGroupDropData(self, groupID, nodes, *args):
        what, labelID, labelName = groupID
        shift = uicore.uilib.Key(uiconst.VK_SHIFT)
        if len(nodes) < 1 or nodes[0].__guid__ != 'listentry.MailEntry':
            return
        if labelID is None or labelID == const.mailLabelSent:
            uicore.Message('CustomNotify', {'notify': localization.GetByLabel('UI/Mail/CannotAssignLabel')})
            return
        currentView = nodes[0].currentView
        allLabels = sm.GetService('mailSvc').GetAllLabels(assignable=0)
        currentName = allLabels.get(currentView, None)
        if currentName is not None:
            currentName = currentName.name
        messageIDs = [ node.messageID for node in nodes ]
        removeText = ''
        if labelID == MAILLABELTRASH:
            if currentView == labelID:
                return
            self.TrashMail(nodes, messageIDs)
        else:
            if currentView == MAILLABELTRASH:
                self.RestoreMail(nodes, messageIDs)
            if not shift and currentView:
                if currentView == labelID:
                    return
                if currentView not in [MAILLABELTRASH, const.mailLabelSent]:
                    sm.StartService('mailSvc').RemoveLabels(messageIDs, currentView)
                    removeText = localization.GetByLabel('UI/Mail/LabelRemoved', labelName=currentName, numMails=len(messageIDs))
            self.AssignLabelFromMailWnd(nodes, messageIDs, labelID)
            text = localization.GetByLabel('UI/Mail/LabelAssigned', labelName=labelName, numMails=len(messageIDs))
            if removeText:
                text += '<br>%s' % removeText
            eve.Message('CustomNotify', {'notify': text})


class MailGroup(Group):
    __guid__ = 'listentry.MailGroup'

    def Startup(self, *args):
        Group.Startup(self, args)
        self.sr.colorTag = uiprimitives.Container(name='colorTag', parent=self, align=uiconst.CENTERRIGHT, pos=(4, 0, 8, 8), idx=0)

    def Load(self, node):
        Group.Load(self, node)
        if node.Get('colorID', None) is not None and node.Get('color', None) is not None:
            import colorsys
            rgb = colorsys.hex_to_rgb(node.color)
            if rgb == WHITE:
                return
            f = uiprimitives.Fill(parent=self.sr.colorTag, color=rgb)
            f.color.a = 0.75


class MailEntry(listentry.Generic):
    __guid__ = 'listentry.MailEntry'
    isDragObject = True

    def Startup(self, *args):
        listentry.Generic.Startup(self, args)
        self.sr.statusIcon = uiprimitives.Container(name='statusIcon', parent=self, align=uiconst.TOLEFT, pos=(0, 0, 52, 0))

    def Load(self, node):
        self.sr.node = node
        listentry.Generic.Load(self, node)
        self.LoadMailEntry(node)

    def LoadMailEntry(self, node):
        uiutil.Flush(self.sr.statusIcon)
        iconPath = 'ui_73_16_15'
        hint = localization.GetByLabel('UI/Mail/Read')
        data = node.data
        self.UpdateLabel(data)
        if not data.read:
            iconPath = 'ui_73_16_14'
            hint = localization.GetByLabel('UI/Mail/Unread')
        elif node.Get('showAllStatus', 1):
            if data.Get('replied', 0):
                iconPath = 'ui_73_16_12'
                hint = localization.GetByLabel('UI/Mail/Replied')
            elif data.Get('forwarded', 0):
                iconPath = 'ui_73_16_13'
                hint = localization.GetByLabel('UI/Mail/Forwarded')
        icon = uicontrols.Icon(icon=iconPath, parent=self.sr.statusIcon, align=uiconst.CENTER, pos=(0, 0, 16, 16), state=uiconst.UI_PICKCHILDREN)
        icon.hint = hint

    def GetDragData(self, *args):
        return self.sr.node.scroll.GetSelectedNodes(self.sr.node)

    def OnDropData(self, dragObj, nodes):
        pass

    def UpdateLabel(self, data):
        label = self.sr.node.cleanLabel
        if not data.read:
            label = '<b>' + label + '</b>'
        self.sr.label.text = label
        self.sr.node.label = label
        self.sr.label.Update()


class MailLabelEntry(listentry.Generic):
    __guid__ = 'listentry.MailLabelEntry'

    def Startup(self, *args):
        listentry.Generic.Startup(self, args)
        self.sr.colorTag = uiprimitives.Container(name='colorTag', parent=self, align=uiconst.CENTERRIGHT, pos=(4, 0, 8, 8), idx=0)

    def Load(self, node):
        listentry.Generic.Load(self, node)
        self.labelID = self.sr.node.currentView
        uiutil.Flush(self.sr.colorTag)
        if node.Get('color', None) is not None:
            import colorsys
            rgb = colorsys.hex_to_rgb(node.color)
            if rgb == WHITE:
                return
            f = uiprimitives.Fill(parent=self.sr.colorTag, color=rgb)
            f.color.a = 0.75

    def OnDropData(self, dragObj, nodes):
        data = self.sr.node
        currentView = data.currentView
        if data.OnDropData:
            data.OnDropData(('MailLabelEntry', currentView, data.cleanLabel), nodes)


class ManageLabelsBase(uicontrols.Window):
    """
    window to assign/remove labels, need 2 window that are the same but behave a bit different
    """
    __guid__ = 'form.ManageLabelsBase'
    __notifyevents__ = ['OnMyLabelsChanged']
    default_iconNum = 'res:/ui/Texture/WindowIcons/evemailtag.png'

    def ApplyAttributes(self, attributes):
        uicontrols.Window.ApplyAttributes(self, attributes)
        labelType = self.labelType = attributes.labelType
        self.loadingShowcontent = 0
        self.SetScope('all')
        self.SetWndIcon(self.iconNum)
        self.SetMinSize([250, 250])
        caption = localization.GetByLabel('UI/Mail/ManageLabels')
        if labelType == 'contact':
            caption = localization.GetByLabel('UI/Mail/ManageLabelsWithType', labelType=localization.GetByLabel('UI/Mail/Contacts'))
        elif labelType == 'corpcontact':
            caption = localization.GetByLabel('UI/Mail/ManageLabelsWithType', labelType=localization.GetByLabel('UI/Mail/CorpContacts'))
        elif labelType == 'alliancecontact':
            caption = localization.GetByLabel('UI/Mail/ManageLabelsWithType', labelType=localization.GetByLabel('UI/Mail/AllianceContacts'))
        self.SetCaption(caption)
        self.SetTopparentHeight(60)
        self.sr.bottom = uiprimitives.Container(name='bottom', parent=self.sr.main, align=uiconst.TOBOTTOM, pos=(0, 0, 0, 26))
        self.sr.inpt = inpt = uicontrols.SinglelineEdit(name='input', parent=self.sr.topParent, maxLength=const.mailMaxLabelSize, pos=(74, 20, 86, 0), label=localization.GetByLabel('UI/Mail/LabelName'))
        createBtn = uicontrols.Button(parent=self.sr.topParent, label=localization.GetByLabel('UI/Mail/Create'), pos=(inpt.left + inpt.width + 4,
         inpt.top,
         0,
         0), func=self.CreateLabel, btn_default=1)
        self.sr.textCont = uiprimitives.Container(name='textCont', parent=self.sr.main, align=uiconst.TOTOP, pos=(0, 0, 0, 42), state=uiconst.UI_HIDDEN)
        self.sr.textCont2 = uiprimitives.Container(name='textCont', parent=self.sr.main, align=uiconst.TOBOTTOM, pos=(0, 0, 0, 18), state=uiconst.UI_HIDDEN)
        self.sr.selectedText = uicontrols.EveLabelMedium(text='', parent=self.sr.textCont2, left=0, top=0, state=uiconst.UI_DISABLED, align=uiconst.CENTERTOP)
        self.sr.labelScroll = uicontrols.Scroll(name='labelScroll', parent=self.sr.main, padding=(const.defaultPadding,
         0,
         const.defaultPadding,
         const.defaultPadding))
        self.sr.labelScroll.sr.id = labelType

    def FindLabelsChecked(self, *args):
        labelsChecked = []
        for each in self.sr.labelScroll.GetNodes():
            if each.checked == 1:
                labelsChecked.append(each.retval)

        return labelsChecked

    def CreateLabel(self, *args):
        labelName = self.sr.inpt.GetValue()
        labelName = labelName.strip()
        existingLabels = []
        for each in self.sr.labelScroll.GetNodes():
            existingLabels.append(each.label.lower())

        if labelName.lower() in existingLabels:
            raise UserError('MailLabelNameExists')
        if len(labelName) < 1:
            eve.Message('LookupStringMinimum', {'minimum': 1})
            return
        if len(labelName) > const.mailMaxLabelSize:
            raise UserError('CustomNotify', {'notify': localization.GetByLabel('UI/Mail/LabelTooLong')})
        if self.labelType == 'mail_labels':
            wasCreated = sm.GetService('mailSvc').CreateLabel(labelName)
        else:
            sm.GetService('addressbook').CreateContactLabel(labelName)

    def LoadScroll(self, *args):
        if self.labelType == 'mail_labels':
            labels = sm.GetService('mailSvc').GetAllLabels(assignable=1).values()
        else:
            labels = sm.GetService('addressbook').GetContactLabels(self.labelType).values()
        scrolllist = []
        for each in labels:
            data = util.KeyVal()
            data.label = each.name
            data.cfgname = each.name
            data.retval = each.labelID
            data.checked = each.labelID in self.storedSelection
            data.OnChange = self.ShowTextHint
            data.GetMenu = self.GetLabelMenu
            data.ignoreRightClick = 1
            label = each.name
            static = getattr(each, 'static', 0)
            if static:
                label = '  %s' % each.labelID
            scrolllist.append((label, listentry.Get('Checkbox', data=data)))

        scrolllist = uiutil.SortListOfTuples(scrolllist)
        self.sr.labelScroll.Load(contentList=scrolllist)
        self.ShowTextHint()

    def OnMyLabelsChanged(self, labelType, created = None, *args):
        """
            listen to notify event and update scroll
        """
        if labelType == self.labelType:
            self.UpdateLabelsList(created)

    def UpdateLabelsList(self, created = None, *args):
        """
            listen to notify event and update scroll
        """
        self.storedSelection = self.FindLabelsChecked()
        if created is not None:
            self.storedSelection.append(created)
        self.LoadScroll()
        self.storedSelection = []

    def ShowTextHint(self, *args):
        labelsChecked = self.FindLabelsChecked()
        numLabels = len(labelsChecked)
        if numLabels > 0:
            self.sr.selectedText.text = localization.GetByLabel('UI/Mail/LabelsSelected', numSelected=numLabels)
            self.sr.textCont2.state = uiconst.UI_DISABLED
        else:
            self.sr.textCont2.state = uiconst.UI_HIDDEN

    def GetLabelMenu(self, entry):
        labelID = entry.sr.node.retval
        m = []
        if self.labelType == 'mail_labels':
            m.append((uiutil.MenuLabel('UI/Mail/AssignColor'), self.GetAssignColorWnd, (labelID,)))
            if const.mailLabelsSystem & labelID == 0:
                m.append((uiutil.MenuLabel('UI/Mail/LabelRename'), sm.GetService('mailSvc').RenameLabelFromUI, (labelID,)))
                m.append(None)
                m.append((uiutil.MenuLabel('UI/Mail/Delete'), sm.GetService('mailSvc').DeleteLabelFromUI, (labelID, entry.sr.node.label)))
        else:
            m.append((uiutil.MenuLabel('UI/Mail/LabelRename'), sm.GetService('addressbook').RenameContactLabelFromUI, (labelID,)))
            m.append(None)
            m.append((uiutil.MenuLabel('UI/Mail/Delete'), sm.GetService('addressbook').DeleteContactLabelFromUI, (labelID, entry.sr.node.label)))
        return m

    def GetAssignColorWnd(self, labelID):
        blue.pyos.synchro.Yield()
        doneCallBack = sm.StartService('mailSvc').ChangeLabelColorFromUI
        doneArgs = (labelID,)
        sm.GetService('mailSvc').GetAssignColorWnd(labelID, doneCallBack=doneCallBack, doneArgs=doneArgs)


class ManageLabelsExistingMails(ManageLabelsBase):
    __guid__ = 'form.ManageLabelsExistingMails'
    default_windowID = 'ManageLabelsExistingMails'

    def ApplyAttributes(self, attributes):
        attributes.labelType = 'mail_labels'
        ManageLabelsBase.ApplyAttributes(self, attributes)
        self.storedSelection = []
        self.sr.textCont.state = uiconst.UI_DISABLED
        text = uicontrols.EveLabelMedium(text=localization.GetByLabel('UI/Mail/LabelText'), parent=self.sr.textCont, left=10, top=0, state=uiconst.UI_DISABLED, align=uiconst.TOALL)
        btns = uicontrols.ButtonGroup(btns=[[localization.GetByLabel('UI/Mail/AssignLabel'),
          self.AssignLabelFromBtn,
          None,
          81], [localization.GetByLabel('UI/Mail/LabelRemove'),
          self.RemoveLabelFromBtn,
          None,
          81]], parent=self.sr.bottom, idx=0, line=1)
        self.LoadScroll()

    def AssignLabelFromBtn(self, *args):
        self.ManageLabel(assign=1)

    def RemoveLabelFromBtn(self, *args):
        self.ManageLabel(assign=0)

    def ManageLabel(self, assign = 1):
        labelsChecked = self.FindLabelsChecked()
        numLabels = len(labelsChecked)
        if numLabels < 1:
            raise UserError('CustomNotify', {'notify': localization.GetByLabel('UI/PeopleAndPlaces/NoLabelsSelected')})
        wnd = MailWindow.GetIfOpen()
        if not wnd:
            raise UserError('CustomNotify', {'notify': localization.GetByLabel('UI/Mail/NoMailsSelected')})
        scroll = uiutil.FindChild(wnd, 'msgScroll')
        if scroll is None:
            selectedMails = []
        else:
            selectedMails = scroll.GetSelected()
        mailIDs = [ mail.messageID for mail in selectedMails ]
        sum = 0
        for labelID in labelsChecked:
            sum = sum + labelID

        if assign == 1:
            sm.StartService('mailSvc').AssignLabels(mailIDs, sum)
        else:
            sm.StartService('mailSvc').RemoveLabels(mailIDs, sum)
        numLabels = len(labelsChecked)
        numMails = len(mailIDs)
        if numMails > 0:
            if assign:
                text = localization.GetByLabel('UI/Mail/LabelsAssignedToMails', numLabels=numLabels, numMails=numMails)
            else:
                text = localization.GetByLabel('UI/Mail/LabelsRemovedFromMails', numLabels=numLabels, numMails=numMails)
            eve.Message('CustomNotify', {'notify': text})
            wnd.sr.mail.RefreshLabels(selectedMails, mailIDs)
        else:
            raise UserError('CustomNotify', {'notify': localization.GetByLabel('UI/Mail/NoMailsSelected')})


class ManageLabelsNewMails(ManageLabelsBase):
    __guid__ = 'form.ManageLabelsNewMails'
    default_windowID = 'ManageLabelsNewMails'

    def ApplyAttributes(self, attributes):
        self.result = None
        attributes.labelType = 'mail_labels'
        ManageLabelsBase.ApplyAttributes(self, attributes)
        labels = attributes.labels
        btns = uicontrols.ButtonGroup(btns=[[localization.GetByLabel('UI/Mail/Apply'),
          self.Apply,
          None,
          81]], parent=self.sr.bottom, idx=0, line=1)
        self.storedSelection = labels
        self.LoadScroll()

    def Apply(self, *args):
        labelsChecked = self.FindLabelsChecked()
        if labelsChecked is None or labelsChecked == []:
            if eve.Message('NoLabelApplied', {}, uiconst.YESNO, suppress=uiconst.ID_YES) != uiconst.ID_YES:
                return
        self.result = labelsChecked
        if getattr(self, 'isModal', None):
            self.SetModalResult(1)


class NewNewMessage(uicontrols.Window):
    """ This is a new message window"""
    __guid__ = 'form.NewNewMessage'
    __nonpersistvars__ = ['messageedit',
     'buddy',
     'input',
     'receivers']
    default_toCharacterIDs = []
    default_toListID = None
    default_toCorpOrAllianceID = None
    default_isForwardedFrom = False
    default_isReplyTo = False
    default_subject = None
    default_body = None
    default_width = 300
    default_height = 350
    default_iconNum = 'res:/ui/Texture/WindowIcons/evemailcompose.png'

    def ApplyAttributes(self, attributes):
        uicontrols.Window.ApplyAttributes(self, attributes)
        toCharacterIDs = attributes.toCharacterIDs or self.default_toCharacterIDs
        toListID = attributes.toListID
        toCorpOrAllianceID = attributes.toCorpOrAllianceID
        isForwardedFrom = attributes.isForwardedFrom or self.default_isForwardedFrom
        isReplyTo = attributes.isReplyTo or self.default_isReplyTo
        subject = attributes.subject
        body = attributes.body
        self.messageedit = None
        self.scope = 'station_inflight'
        self.parsingReceivers = 0
        self.labels = []
        self.toChars = {}
        self.toCorpAlliance = {}
        self.toListID = None
        self.isForwardedFrom = 0
        self.isReplyTo = 0
        self.buddies = []
        self.isForwardedFrom = isForwardedFrom
        self.isReplyTo = isReplyTo
        self.SetMinSize([250, 250])
        self.SetWndIcon(self.iconNum, hidden=True)
        self.SetCaption(localization.GetByLabel('UI/Mail/NewMessage'))
        self.SetTopparentHeight(64)
        main = uiutil.GetChild(self, 'main')
        self.configname = self.__hash__()
        self.buddies = [ buddy for buddy in sm.GetService('addressbook').GetAddressBook() if util.IsNPC(buddy) == False and util.IsCharacter(buddy) ]
        self.name = 'newmessage'
        sendCont = uiprimitives.Container(name='sendCont', parent=self.sr.topParent, align=uiconst.TOLEFT, pos=(0, 0, 64, 0))
        labelCont = uiprimitives.Container(name='labelCont', parent=self.sr.topParent, align=uiconst.TOLEFT, pos=(0, 0, 50, 0))
        editCont = uiprimitives.Container(name='editCont', parent=self.sr.topParent, align=uiconst.TOALL, pos=(0, 0, 0, 0))
        uiprimitives.Container(name='push', parent=editCont, align=uiconst.TORIGHT, pos=(0, 0, 5, 0))
        self.sr.sendBtn = sendBtn = uix.GetBigButton(size=48, where=sendCont, left=8, top=8, hint=localization.GetByLabel('UI/Mail/SendMail'), align=uiconst.RELATIVE)
        uiutil.MapIcon(sendBtn.sr.icon, 'res:/ui/Texture/WindowIcons/evemail.png', ignoreSize=True)
        sendBtn.OnClick = self.ClickSend
        sendBtn.isTabStop = 1
        sendBtn.Confirm = self.ClickSend
        sendBtn.setfocus = 1
        sendBtn.killfocus = 1
        uiprimitives.Container(name='push', parent=self.sr.topParent, align=uiconst.TORIGHT, pos=(0, 0, 4, 0))
        uiprimitives.Container(name='push', parent=self.sr.topParent, align=uiconst.TOTOP, pos=(0, 0, 0, 4))
        toBtn = uicontrols.Button(parent=labelCont, label=localization.GetByLabel('UI/Mail/To'), pos=(0, 7, 0, 0), func=self.OpenReceiverSearch)
        toBtn.height = 23
        self.sr.receiver = receiver = self.GetReceiverEdit('toField', editCont, maxLength=const.mailMaxRecipients * 24, left=0, top=10, label='', align=uiconst.TOTOP)
        self.sr.subjecField = subjecField = uicontrols.SinglelineEdit(name='subjecField', parent=editCont, maxLength=const.mailMaxSubjectSize, pos=(0, 10, 0, 0), label='', align=uiconst.TOTOP)
        subjectLabel = uicontrols.EveLabelSmall(text=localization.GetByLabel('UI/Mail/Subject'), parent=labelCont, top=40, left=10, state=uiconst.UI_NORMAL)
        labelCont.width = max(subjectLabel.textwidth + 15, toBtn.width + 5)
        receiver.blockSetValue = 1
        receiver.registerHistory = 0
        receiver.GetAll = self.GetAllOptions
        receiver.OnHistoryClick = self.OnReceiverHistoryClick
        receiver.OnDropData = self.OnDropReceiver
        receiver.OnInsert = self.ValidateReceiver
        receiver.OnFocusLost = self.ValidateReceivers
        receiver.receiverText = ''
        self.messageedit = uicls.EditPlainText(parent=main, pos=(0, 0, 0, 0), padding=(const.defaultPadding,
         const.defaultPadding,
         const.defaultPadding,
         const.defaultPadding), align=uiconst.TOALL, maxLength=const.mailMaxBodySize, showattributepanel=1)
        buttonCont = self.messageedit.sr.attribPanel
        if buttonCont is not None:
            btn = uicontrols.Icon(name='channelWndIcon', icon='ui_73_16_9', parent=buttonCont, pos=(144, 0, 16, 16), align=uiconst.TOPLEFT, hint=localization.GetByLabel('UI/Mail/LabelMail'), ignoreSize=True)
            btn.OnClick = self.Label
        if subject is not None:
            subjecField.SetValue(subject)
        if body is not None:
            self.messageedit.SetValue(body)
        fontCombo = uiutil.FindChild(self.messageedit, 'fontsize')
        if fontCombo:
            fontCombo.isTabStop = 0
        if toCharacterIDs:
            sm.GetService('mailSvc').PrimeOwners(toCharacterIDs)
            for each in toCharacterIDs:
                if each is not None:
                    self.AddCharacterReceiver(each)

        if toCorpOrAllianceID:
            for each in toCorpOrAllianceID:
                if each is not None:
                    self.AddCorpAllianceReciver(each)

        if toListID is not None:
            myLists = sm.GetService('mailinglists').GetMyMailingLists()
            if toListID in myLists:
                list = myLists.get(toListID)
                name = list.displayName
                self.AddList(toListID, name)
        if isReplyTo:
            uicore.registry.SetFocus(self.messageedit)
        else:
            uicore.registry.SetFocus(receiver)
        self.ValidateReceivers()

    def GetReceiverEdit(self, configname, where, setvalue = None, left = 0, width = 80, ints = None, top = 2, height = 18, floats = None, callback = None, label = None, maxLength = None, passwordChar = None, align = 0, readonly = 0, adjustWidth = False):
        """
            Simple version of uicontrols.SinglelineEdit where I removed everything I didn't need
        """
        edit = uicls.ReceiverEdit(name=configname, parent=where, height=height, width=width, left=left, top=top, align=align)
        edit.SetMaxLength(maxLength)
        if setvalue is not None:
            edit.SetValue(setvalue)
        if label:
            _label = uicontrols.EveHeaderSmall(text=label, parent=edit, align=uiconst.TOPLEFT, width=1000, height=13, left=0, top=-13)
            edit.sr.label = _label
        return edit

    def _OnClose(self, *args):
        self.messageedit = None
        self.parsingReceivers = 0
        from eve.client.script.ui.shared.neocom.characterSearchWindow import CharacterSearchWindow
        wnd = CharacterSearchWindow.GetIfOpen()
        if wnd and wnd.configname == self.configname:
            wnd.CloseByUser()

    def AddCharacterReceiver(self, id, partly = 0):
        """
            Checks if this character can be added to the receiver list and then adds it if everything is OK
            Returns True if he could be added, False, if not
        """
        if not util.IsCharacter(id):
            return self.AddCorpAllianceReciver(id)
        name = cfg.eveowners.Get(id).name
        if len(self.toChars) >= const.mailMaxRecipients:
            eve.Message('EvemailMaxRecipients', {'max': const.mailMaxRecipients,
             'name': name})
            return False
        self.toChars[name] = id
        if partly:
            return True
        self.AddReceiver(id, name)
        sm.ScatterEvent('OnSearcedUserAdded', id, self.configname)
        return True

    def ValidateCorpOrAlliance(self, id):
        if util.IsCorporation(id):
            if id != session.corpid:
                eve.Message('EvemailCantSendToOtherCorp', {})
                return False
            if util.IsNPC(id):
                eve.Message('EvemailCantSendToNPCCorp', {})
                return False
        elif util.IsAlliance(id):
            if id != session.allianceid:
                eve.Message('EvemailCantSendToOtherAlliance', {})
                return False
            if not const.corpRoleChatManager & session.corprole == const.corpRoleChatManager:
                eve.Message('EvemailCantSendToAllianceNoRole', {})
                return False
        else:
            return False
        return True

    def AddCorpAllianceReciver(self, id, partly = 0):
        """
            Checks if this corp or alliance can be added to the receiver list and then adds it if everything is OK
            Returns True if it could be added, False, if not
        """
        if not self.ValidateCorpOrAlliance(id):
            return False
        name = cfg.eveowners.Get(id).name
        if self.TotalNumberOfGroups() >= const.mailMaxGroups:
            self.GetMaxGroupText(name)
            return False
        self.toCorpAlliance[name] = id
        if partly:
            return True
        self.AddReceiver(id, name)
        return True

    def AddList(self, id, name, partly = 0):
        """
            Checks if this mailing list can be added to the receiver list and then adds it if everything is OK
            Returns True if it could be added, False, if not
        """
        if self.TotalNumberOfGroups() >= const.mailMaxGroups:
            self.GetMaxGroupText(name)
            return False
        self.toListID = id
        if partly:
            return True
        name = localization.GetByLabel('UI/Mail/MailEntry', entryName=name, entryType=localization.GetByLabel('UI/Mail/ML'))
        self.AddReceiver(id, name, checkNPC=False)
        return True

    def AddReceiver(self, id, name, checkNPC = True):
        """
            you can only send to player made entities.
        """
        if checkNPC and util.IsNPC(id):
            return
        c = self.sr.receiver.GetValue()
        if c:
            c += ', '
        if self.name == localization.GetByLabel('UI/Common/Unknown'):
            self.name = name
        c += name
        self.sr.receiver.SetValue(c)
        self.ValidateReceivers()

    def NewParseReceiver(self, name, *args):
        """
            find a new receiver
            if the receiver is found, it's added to the appropriate receiver dictionary and
            a keyval with its name, id and the group it belongs to is returned
            if the receiver is not found, None is returned
            if the recipient cannot be added because there are too many recipients, None is returned
        
            ARGUMENTS:
                name    name of the entity you want to send to
        """
        listReceiver = self.GetMailinglistReceiver(name.strip())
        if listReceiver is not None:
            if self.TotalNumberOfGroups() >= const.mailMaxGroups:
                self.GetMaxGroupText(name)
                return
            self.toListID = listReceiver
            ret = util.KeyVal(name=name, group=GROUP_LIST, id=listReceiver)
            return ret
        name = name.strip()
        if name.lower() in [cfg.eveowners.Get(session.corpid).ownerName.lower(), CORPTEXT]:
            valid = self.ValidateCorpOrAlliance(session.corpid)
            if not valid:
                return
            name = cfg.eveowners.Get(session.corpid).ownerName
            if self.TotalNumberOfGroups() >= const.mailMaxGroups:
                self.GetMaxGroupText(name)
                return
            self.toCorpAlliance[name] = session.corpid
            ret = util.KeyVal(name=name, group=GROUP_CORP, id=listReceiver)
            return ret
        if session.allianceid:
            if name.lower() in [cfg.eveowners.Get(session.allianceid).ownerName.lower(), ALLIANCTEXT]:
                valid = self.ValidateCorpOrAlliance(session.allianceid)
                if not valid:
                    return
                name = cfg.eveowners.Get(session.allianceid).ownerName
                if self.TotalNumberOfGroups() >= const.mailMaxGroups:
                    self.GetMaxGroupText(name)
                    return
                self.toCorpAlliance[name] = session.allianceid
                ret = util.KeyVal(name=name, group=GROUP_CORP, id=listReceiver)
                return ret
        nme, id = self.GetReceiver(name)
        if nme and id:
            if len(self.toChars) >= const.mailMaxRecipients:
                eve.Message('EvemailMaxRecipients', {'max': const.mailMaxRecipients,
                 'name': nme})
                return
            self.toChars[nme] = id
            sm.ScatterEvent('OnSearcedUserAdded', id, self.configname)
            ret = util.KeyVal(name=nme, group=GROUP_CHAR, id=id)
            return ret

    def GetMailinglistReceiver(self, name):
        """
            finding a mailinglist from a name
            if the mailing list is found, you are asked if you are sending to a mailing list, and if you
            accept the mailing list name is returned
            if you are not sending to a mailinglist, None is returned 
        """
        lists = sm.GetService('mailinglists').GetMyMailingLists()
        for key, value in lists.iteritems():
            if name == value.displayName:
                if eve.Message('CustomQuestion', {'header': localization.GetByLabel('UI/Mail/SendToMailingListQ'),
                 'question': localization.GetByLabel('UI/Mail/SendToMailingListQ2', listName=name)}, uiconst.YESNO) == uiconst.ID_YES:
                    return key

    def GetReceiver(self, string):
        """
            Searching for a character receiver, this is exact search, and only if no character is found that matches the 
            string a search window is popped up
        """
        if string in self.toChars:
            id = self.toChars[string]
            if id:
                return (string, id)
        ownerID = uix.Search(string, const.groupCharacter, hideNPC=1, exact=const.searchByExactPhrase, searchWndName='newMessageReceiverSearch', getError=1)
        if ownerID:
            if type(ownerID) in [types.StringType, types.UnicodeType]:
                mailSettings = sm.GetService('mailSvc').GetMailSettings()
                if mailSettings.GetSingleValue(cSettings.MAIL_GET_SEARCH_WND, True):
                    self.GetSearchWnd(input=string)
                else:
                    eve.Message('EveMailNoCharFound', {'name': string})
                return (string, None)
            return (cfg.eveowners.Get(ownerID).name, ownerID)
        return (string, None)

    def GetAllOptions(self):
        """
            Gets all the buddies, your mailinglists and corp to display them in the typeahaed
        """
        buddies = self.buddies
        mailingLists = sm.GetService('mailinglists').GetMyMailingLists()
        myCorpAndAllicane = [session.corpid]
        if session.allianceid:
            myCorpAndAllicane.append(session.allianceid)
        ret = util.KeyVal()
        ret.buddies = buddies
        ret.mailingLists = mailingLists
        ret.corpAll = myCorpAndAllicane
        return ret

    def OnReceiverHistoryClick(self, rest, string, info, *args):
        """
            This is called when something is selected from the typeahead
        """
        if info:
            string = string.strip()
            group, id = info
            canAdd = False
            if group == GROUP_CHAR:
                canAdd = self.AddCharacterReceiver(id, partly=1)
            elif group == GROUP_LIST:
                canAdd = self.AddList(id, string, partly=1)
                if canAdd:
                    string = localization.GetByLabel('UI/Mail/MailEntry', entryName=string, entryType=localization.GetByLabel('UI/Mail/ML'))
            elif group == GROUP_CORP:
                canAdd = self.AddCorpAllianceReciver(id, partly=1)
            if canAdd:
                if rest:
                    rest += ' '
                self.sr.receiver.SetValue(rest + string, updateIndex=1)
            else:
                self.sr.receiver.SetValue(rest, updateIndex=1)

    def OnDropReceiver(self, dragObj, nodes):
        """
            when an entity is dragged to the TO field, add it as a receiver
        """
        for node in nodes:
            charID = GetCharIDFromTextLink(node)
            if charID and util.IsCharacter(charID):
                self.AddCharacterReceiver(charID)
            elif node.__guid__ in uiutil.AllUserEntries():
                self.AddCharacterReceiver(node.charID)
            elif node.__guid__ == 'listentry.CorpAllianceEntry':
                itemID = getattr(node, 'itemID', None)
                if itemID is None:
                    mailingListID = util.GetAttrs(node, 'sr', 'node', 'mailingListID')
                    if mailingListID is not None:
                        self.AddList(mailingListID, node.Get('name', ''))
                else:
                    self.AddCorpAllianceReciver(node.itemID)

    def TotalNumberOfGroups(self):
        return len(self.toCorpAlliance) + int(self.toListID is not None)

    def GetMaxGroupText(self, name, corpNamesUsed = None, listNamesUsed = None):
        if corpNamesUsed is None:
            corpNamesUsed = self.toCorpAlliance
        if listNamesUsed is None and self.toListID is not None:
            listNamesUsed = sm.GetService('mailinglists').GetMyMailingLists()[self.toListID]
        groupName = localization.GetByLabel('UI/Common/Unknown')
        groups = corpNamesUsed.keys()
        if listNamesUsed is not None:
            groups.append(listNamesUsed.displayName)
        if len(groups) >= const.mailMaxGroups:
            groupName = groups[0]
        return eve.Message('EvemailMaxListOrCorp', {'name': name,
         'groupName': groupName})

    def OnDropData(self, dragObj, nodes):
        pass

    def ValidateReceiver(self, char, *args):
        """
            Called when a character is inserted
            if the inserted character was comma, then the receivers are validated
            we also want to validate if the user has deleted everything
        """
        text = unichr(char)
        if text != ',' and self.sr.receiver.GetValue().strip() != '':
            return None
        if not self or self.destroyed:
            return None
        uthread.new(self.ValidateReceivers)

    def ValidateReceivers(self, *args):
        """
            the recievers are validated here
            if the receivers have been validated before they are in the self.toX dicts
            if they are not, AddUnknownToValidate is called to find the receivers
            when the validation is done, the textfield displays the validated entities
            
            Everything is more complicated because mailinglists can have the same name as some
            character/corp/alliance. So even though the name is for example in self.toChars, the user might have entered
            the name again, now as list.
            So if there is a name that is in self.toX dict and it has no suffix (no [ML] in the end), we need to check 
            if the user is entering a new recipient.
        
            In the end, the self.toX dicts are checked to see if there is something in them
            that is not in the 'to' field, which will happen when entities have been eveluated
            but then removed. All those entities are removed from the self.toX dicts, and there
            for are no longer listed as receivers of the mail
            
        """
        if not self or self.destroyed or getattr(self, 'parsingReceivers', 0):
            return
        self.parsingReceivers = 1
        inp = self.sr.receiver.GetValue()
        all = inp.split(',')
        charNamesUsed = {}
        corpNamesUsed = {}
        listNamesUsed = {}
        allReceivers = self.toChars.keys() + self.toCorpAlliance.keys()
        myLists = sm.GetService('mailinglists').GetMyMailingLists()
        myListsNames = [ each.displayName.lower() for each in myLists.itervalues() ]
        if self.toListID in myLists:
            allReceivers.append(myLists[self.toListID].displayName)
        finalString = ''
        for name in all:
            name = name.strip()
            if not name:
                continue
            cleanNameAndGroup = self.GetCleanNameAndGroup(name)
            cleanName = cleanNameAndGroup.name
            group = cleanNameAndGroup.group
            if cleanName not in allReceivers:
                add = self.AddUnknownToValidate(cleanName, listNamesUsed, corpNamesUsed, charNamesUsed)
                if add is None:
                    eve.Message('EvemailCantFindRecipient', {'name': cleanName})
                    continue
                else:
                    group = add.group
                    cleanName = add.name
            elif group == GROUP_LIST:
                if cleanName.lower() in myListsNames:
                    if cleanName not in listNamesUsed:
                        listNamesUsed[cleanName] = True
                    else:
                        continue
            elif cleanName in self.toChars and cleanName not in charNamesUsed:
                charNamesUsed[cleanName] = True
            elif cleanName in self.toCorpAlliance and cleanName not in corpNamesUsed:
                corpNamesUsed[cleanName] = True
            else:
                add = self.AddUnknownToValidate(cleanName, listNamesUsed, corpNamesUsed, charNamesUsed)
                if add is None:
                    continue
                else:
                    group = add.group
                    cleanName = add.name
            nameToAdd = cleanName
            if group == GROUP_LIST:
                nameToAdd = localization.GetByLabel('UI/Mail/MailEntry', entryName=nameToAdd, entryType=localization.GetByLabel('UI/Mail/ML'))
            finalString += '%s, ' % nameToAdd

        if not self or self.destroyed:
            self.parsingReceivers = 0
            return
        self.sr.receiver.SetValue(finalString)
        toChars = self.toChars.copy()
        toCorpAlliance = self.toCorpAlliance.copy()
        charsPopped = []
        for each in toChars:
            if each not in charNamesUsed:
                charsPopped.append(self.toChars.get(each, None))
                self.toChars.pop(each, None)

        sm.ScatterEvent('OnSearcedUserRemoved', charsPopped, self.configname)
        for each in toCorpAlliance:
            if each not in corpNamesUsed:
                self.toCorpAlliance.pop(each, None)

        if self.toListID is not None:
            myLists = sm.GetService('mailinglists').GetMyMailingLists()
            if self.toListID not in myLists or len(listNamesUsed) < 1:
                self.toListID = None
        self.parsingReceivers = 0

    def GetCleanNameAndGroup(self, name):
        """
            This function strips [ML] from recipient name and returns the clean name
            along with the group (which is GROUP_LIST if the name ended with [ML] but otherwise
            it is None).
            
        """
        name = name.strip()
        ret = util.KeyVal(name=name, group=None)
        strippedMaillistLabel = uiutil.StripTags(localization.GetByLabel('UI/Mail/ML'))
        if name.endswith(strippedMaillistLabel):
            ret.name = name.replace(strippedMaillistLabel, '')
            if ret.name[-1] == ' ':
                ret.name = ret.name[:-1]
            ret.group = GROUP_LIST
        return ret

    def AddUnknownToValidate(self, name, listNamesUsed, corpNamesUsed, charNamesUsed):
        """
            This functions tries to add recipient based on a name that was entered in
            the recipient edit field.
            
            If a recipient is not added, this function returns None
            If a recipient is added, this function will add it to the xNamesUsed lists
            passed in to indicate that the name is about to be/has been added to the recipient
            field, and returns a keyVal with the name and group of the recipient.
            
            listNamesUsed, corpNamesUsed and charNamesUsed are lists that are passed
            by reference, so when I add to them, I add to the original list that were passed in
        """
        keyVal = self.NewParseReceiver(name)
        if keyVal is None:
            return
        name = keyVal.name
        group = keyVal.group
        corpAndListsNum = len(corpNamesUsed) + len(listNamesUsed)
        ret = keyVal.copy()
        if group == GROUP_LIST:
            if corpAndListsNum >= const.mailMaxGroups:
                self.GetMaxGroupText(name, corpNamesUsed, listNamesUsed)
            elif name not in listNamesUsed:
                listNamesUsed[name] = True
                return ret
        elif group == GROUP_CORP:
            if corpAndListsNum >= const.mailMaxGroups:
                self.GetMaxGroupText(name, corpNamesUsed, listNamesUsed)
            elif name not in corpNamesUsed:
                corpNamesUsed[name] = True
                return ret
        elif group == GROUP_CHAR:
            if len(charNamesUsed) >= const.mailMaxRecipients:
                eve.Message('EvemailMaxRecipients', {'max': const.mailMaxRecipients,
                 'name': name})
            elif name not in charNamesUsed:
                charNamesUsed[name] = True
                return ret

    def ClickSend(self, *args):
        self.SetSendBtnState(disable=1)
        self.ValidateReceivers()
        allReceivers = self.toChars.keys() + self.toCorpAlliance.keys()
        if self.toListID is not None:
            myLists = sm.GetService('mailinglists').GetMyMailingLists()
            if self.toListID in myLists:
                allReceivers.append(myLists[self.toListID])
        if len(allReceivers) < 1:
            eve.Message('CustomInfo', {'info': localization.GetByLabel('UI/Mail/NoRecipientForMessage')})
            self.SetSendBtnState(disable=0)
            return
        if len(allReceivers) > const.mailMaxRecipients + 1:
            info = localization.GetByLabel('UI/Mail/TooManyRecipients', max=const.mailMaxRecipients)
            eve.Message('CustomInfo', {'info': info})
            self.SetSendBtnState(disable=0)
            return
        subject = self.sr.subjecField.GetValue()
        if subject.strip() == '':
            self.SetSendBtnState(disable=0)
            raise UserError('NoSubject')
        elif len(subject) > const.mailMaxSubjectSize:
            self.SetSendBtnState(disable=0)
            raise UserError('CustomNotify', {'notify': localization.GetByLabel('UI/Mail/NameIsTooLong')})
        body = self.messageedit.GetValue()
        values = self.toCorpAlliance.values()
        corpAlliance = None
        if values:
            corpAlliance = values[0]
            if not self.ValidateCorpOrAlliance(corpAlliance):
                self.SetSendBtnState(disable=0)
                raise UserError('EvemailSendingFailed')
        labels = self.labels
        try:
            messageID = sm.GetService('mailSvc').SendMail(toCharacterIDs=self.toChars.values(), toListID=self.toListID, toCorpOrAllianceID=corpAlliance, title=subject, body=body, isReplyTo=self.isReplyTo, isForwardedFrom=self.isForwardedFrom)
        except:
            self.SetSendBtnState(disable=0)
            raise

        if messageID is None:
            self.SetSendBtnState(disable=0)
            return
        sum = 0
        for labelID in labels:
            sum = sum + labelID

        sm.GetService('mailSvc').AssignLabels([messageID], sum)
        setattr(sm.StartService('mailSvc'), 'lastMessageTime', blue.os.GetWallclockTime())
        if self and not self.destroyed:
            self.Close()

    def SetSendBtnState(self, disable = 0):
        if disable:
            self.sr.sendBtn.state = uiconst.UI_DISABLED
            self.sr.sendBtn.opacity = 0.3
        else:
            self.sr.sendBtn.state = uiconst.UI_NORMAL
            self.sr.sendBtn.opacity = 1.0

    def Label(self, *args):
        wnd = ManageLabelsNewMails.Open(labels=self.labels)
        if wnd.ShowModal() == 1:
            self.labels = wnd.result

    def OpenReceiverSearch(self, *args):
        self.GetSearchWnd()

    def AddReceiverFromSearch(self, func, *args):
        sel = apply(func)
        for each in sel:
            if not self or self.destroyed:
                return
            itemID = getattr(each, 'itemID', None)
            guid = getattr(each, '__guid__', None)
            if guid in uiutil.AllUserEntries():
                self.AddCharacterReceiver(itemID)
            elif guid == 'listentry.CorpAllianceEntry':
                if itemID is None:
                    if getattr(each, 'mailingListID', None) is not None:
                        self.AddList(each.mailingListID, getattr(each, 'name', ''))
                else:
                    self.AddCorpAllianceReciver(itemID)

    def GetSearchWnd(self, input = ''):
        """
            Gets a search window to search for receivers. This is done either when pressing the "TO" button, or when 
            the entity you typed in wasnt found
            Input is a string that is to be searched for
        """
        actionBtn = [(localization.GetByLabel('UI/Mail/Add'), self.AddReceiverFromSearch, 1)]
        caption = localization.GetByLabel('UI/Mail/SearchForRecipients')
        wnd = CharacterSearchWindow.GetIfOpen()
        if wnd:
            wnd.CloseByUser()
        extraIconHintFlag = ['ui_73_16_13', localization.GetByLabel('UI/Mail/CharacterAdded'), False]
        wnd = CharacterSearchWindowMail.Open(actionBtns=actionBtn, caption=caption, input=input, showContactList=True, extraIconHintFlag=extraIconHintFlag, configname=self.configname)
        if wnd is not None:
            wnd.IsAdded = self.IsAddedToMail
            wnd.Maximize()
            searchBtn = util.GetAttrs(wnd, 'sr', 'searchBtn')
            if searchBtn is not None and input:
                wnd.Search()
                uicore.registry.SetFocus(searchBtn)

    def IsAddedToMail(self, charID, *args):
        if not self or self.destroyed:
            return False
        return charID in self.toChars.values()


class ReceiverEdit(uicontrols.SinglelineEdit):
    """ This class is a special cased SingleLineEdit which allows for typeahead in the to field in the mail"""
    __guid__ = 'uicls.ReceiverEdit'

    def ApplyAttributes(self, attributes):
        uicontrols.SinglelineEdit.ApplyAttributes(self, attributes)
        self.blockSetValue = 1

    def RegisterHistory(self, value = None):
        pass

    def ClearHistory(self, *args):
        pass

    def GetValid(self):
        """
            Gets the list of the entities that match what has been typed in the field
        """
        current = self.GetValue(registerHistory=0)
        rest = ''
        lastComma = current.rfind(',')
        if lastComma > -1:
            rest = current[:lastComma + 1]
            current = current[lastComma + 1:]
            current.strip()
        self.current = current
        self.rest = rest
        id, mine = self.GetHistory()
        buddies = mine.buddies
        lists = mine.mailingLists
        corpAll = mine.corpAll
        valid = []
        sm.GetService('mailSvc').PrimeOwners(buddies)
        for each in buddies:
            name = cfg.eveowners.Get(each).ownerName
            if name.lower().startswith(current.lower().strip()) and name != current:
                valid.append((GROUP_CHAR,
                 name,
                 name,
                 each))

        for key, value in lists.iteritems():
            if value.displayName.lower().startswith(current.lower().strip()) and value.displayName != current:
                valid.append((GROUP_LIST,
                 localization.GetByLabel('UI/Mail/MailEntry', entryName=value.displayName, entryType=localization.GetByLabel('UI/Mail/ML')),
                 value.displayName,
                 key))

        for each in corpAll:
            if util.IsNPC(each):
                continue
            if util.IsAlliance(each) and session.corprole & const.corpRoleChatManager != const.corpRoleChatManager:
                continue
            name = cfg.eveowners.Get(each).ownerName
            if name.lower().startswith(current.lower().strip()) and name != current:
                text = ''
                if each == session.corpid:
                    text = localization.GetByLabel('UI/Mail/LabelCorp')
                elif each == session.allianceid:
                    text = localization.GetByLabel('UI/Mail/LabelAlliance')
                valid.append((GROUP_CORP,
                 localization.GetByLabel('UI/Mail/MailEntry', entryName=name, entryType=text),
                 name,
                 each))

        valid = uiutil.SortListOfTuples([ (len(name), (group,
          displayName,
          name,
          (group, id))) for group, displayName, name, id in valid ])
        return valid

    def HEMouseDown(self, entry, *args):
        """
            selecting one of the entities in the typeahead list
        """
        rest = getattr(self, 'rest', '')
        info = getattr(entry, 'info', None)
        self.OnHistoryClick(rest, entry.string, info)

    def GetHistory(self, getAll = 0):
        id = 0
        all = self.GetAll()
        if getAll:
            return (id, all, all)
        return (id, all)

    def GetAll(self, *args):
        """
            Overwritable
        
        """
        return []

    def PopulateHistoryMenu(self, menuSub, mp, history):
        valid = history
        ep = None
        for g, d, h, info in valid:
            self.GetHistoryMenuEntry(d, h, menuSub, mp, info=info)

        if ep:
            ep.children.remove(ep.children[0])

    def Confirm(self, *args):
        """
            Get what was selected and act like it was clicked
            TODO: I think there is a different way to do this, check on that
        """
        if getattr(self, 'historyMenu', None) is None:
            return
        hm = self.historyMenu()
        entry = getattr(self, 'active', None)
        if entry:
            rest = getattr(self, 'rest', '')
            self.OnHistoryClick(rest, entry.string, entry.info)
        self.CloseHistoryMenu()
        return False


class MailReadingWnd(uicontrols.Window):
    __guid__ = 'form.MailReadingWnd'
    __notifyevents__ = ['OnMessageChanged']
    default_mail = None
    default_msgID = None
    default_txt = ''
    default_toolbar = True
    default_trashed = False
    default_type = None
    detault_windowID = 'mailReadingWnd'

    def ApplyAttributes(self, attributes):
        uicontrols.Window.ApplyAttributes(self, attributes)
        mail = attributes.mail
        msgID = attributes.msgID
        txt = attributes.get('txt', self.default_txt)
        toolbar = attributes.get('toolbar', self.default_toolbar)
        trashed = attributes.get('trashed', self.default_trashed)
        type = attributes.type
        self.messageedit = None
        self.scope = 'station_inflight'
        sm.RegisterNotify(self)
        self.SetMinSize([250, 250])
        self.SetWndIcon()
        self.SetCaption(localization.GetByLabel('UI/Mail/Message'))
        self.SetTopparentHeight(0)
        main = self.sr.main
        self.mail = mail
        self.type = type
        self.messageID = msgID
        actions = util.KeyVal()
        actions.replyClicked = self.ReplyClicked
        actions.replyAllClicked = self.ReplyAllClicked
        actions.forwardClicked = self.ForwardClicked
        actions.trashClicked = self.TrashClicked
        actions.deleteClicked = self.DeleteClicked
        if toolbar:
            self.sr.toolbarCont = uiprimitives.Container(name='rightCont', parent=main, align=uiconst.TOTOP, pos=(0, 0, 0, 50))
            self.sr.mailActions = MailActionPanel(name='mailActionCont', parent=self.sr.toolbarCont, align=uiconst.TOPLEFT, pos=(10, 0, 250, 50))
            self.sr.mailActions.Startup(actions, showCompose=0)
            self.sr.mailActions.SetDeleteVisibility(disabled=0, showDelete=trashed)
            if mail.statusMask & const.mailStatusMaskAutomated == const.mailStatusMaskAutomated:
                self.sr.mailActions.SingleMsgBtnStateAllowFwd()
            else:
                self.sr.mailActions.SingleMsgBtnsState(disabled=0)
        self.sr.rightCont = uiprimitives.Container(name='rightCont', parent=main, align=uiconst.TOALL, pos=(const.defaultPadding,
         const.defaultPadding,
         const.defaultPadding,
         const.defaultPadding))
        self.sr.readingPane = uicls.EditPlainText(setvalue=txt, parent=self.sr.rightCont, align=uiconst.TOALL, readonly=1)

    def SetText(self, text):
        self.sr.readingPane.SetValue(text)

    def _OnClose(self, *args):
        sm.UnregisterNotify(self)
        uicontrols.Window._OnClose(self, *args)

    def ReplyClicked(self, *args):
        sm.GetService('mailSvc').GetReplyWnd(self.mail, all=0)

    def ReplyAllClicked(self, *args):
        sm.GetService('mailSvc').GetReplyWnd(self.mail, all=1)

    def ForwardClicked(self, *args):
        sm.GetService('mailSvc').GetForwardWnd(self.mail)

    def TrashClicked(self, *arsg):
        if self.type == const.mailTypeMail:
            mailCopy = self.mail.copy()
            sm.GetService('mailSvc').MoveMessagesToTrash([self.mail.messageID])
            self.sr.mailActions.SetDeleteVisibility(disabled=0, showDelete=1)
            sm.ScatterEvent('OnMailTrashedDeleted', mailCopy)

    def DeleteClicked(self, *args):
        if self.type == const.mailTypeMail:
            mailCopy = self.mail.copy()
            sm.GetService('mailSvc').DeleteMails([self.mail.messageID])
            sm.ScatterEvent('OnMailTrashedDeleted', mailCopy)
            self.CloseByUser()

    def OnMessageChanged(self, type, messageIDs, what):
        """
            this event is scattered when message is deleted or trashed from outside this
            window
        """
        if type == self.type and self.messageID in messageIDs:
            if type == const.mailTypeMail:
                if what == 'trashed':
                    self.sr.mailActions.SetDeleteVisibility(disabled=0, showDelete=1)
                elif what == 'deleted':
                    self.CloseByUser()
            elif type == const.mailTypeNotifications:
                if what == 'deleted':
                    self.CloseByUser()


class MailActionPanel(uiprimitives.Container):
    __guid__ = 'xtriui.MailActionPanel'

    def ApplyAttributes(self, attributes):
        uiprimitives.Container.ApplyAttributes(self, attributes)
        self.sr.data = None
        self.topOffset = top = 10
        self.size = size = 32
        self.leftOffset = left = 10
        self.space = 35
        self.extraSpace = 15
        composeCont = uiprimitives.Container(name='composeCont', parent=self, align=uiconst.TOPLEFT, pos=(left,
         top,
         size,
         size), hint=localization.GetByLabel('UI/Mail/Compose'))
        self.sr.composeBtn = a = uix.GetBigButton(size=size, where=composeCont, left=0, top=0, menu=0, hint=localization.GetByLabel('UI/Mail/Compose'))
        uiutil.MapIcon(a.sr.icon, 'res:/ui/Texture/WindowIcons/evemailcompose.png', ignoreSize=True)
        left += self.space + self.extraSpace
        replyCont = uiprimitives.Container(name='replyCont', parent=self, align=uiconst.TOPLEFT, pos=(left,
         top,
         size,
         size), hint=localization.GetByLabel('UI/Mail/Reply'))
        self.sr.replyBtn = b = uix.GetBigButton(size=size, where=replyCont, left=0, top=0, menu=0, hint=localization.GetByLabel('UI/Mail/Reply'))
        uiutil.MapIcon(b.sr.icon, 'ui_94_64_2', ignoreSize=True)
        left += self.space
        replyAllCont = uiprimitives.Container(name='replyAllCont', parent=self, align=uiconst.TOPLEFT, pos=(left,
         top,
         size,
         size), hint=localization.GetByLabel('UI/Mail/ReplyAll'))
        self.sr.replyAllBtn = c = uix.GetBigButton(size=size, where=replyAllCont, left=0, top=0, menu=0, hint=localization.GetByLabel('UI/Mail/ReplyAll'))
        uiutil.MapIcon(c.sr.icon, 'ui_94_64_3', ignoreSize=True)
        left += self.space
        forwardCont = uiprimitives.Container(name='forwardCont', parent=self, align=uiconst.TOPLEFT, pos=(left,
         top,
         size,
         size), hint=localization.GetByLabel('UI/Mail/Forward'))
        self.sr.forwardBtn = d = uix.GetBigButton(size=size, where=forwardCont, left=0, top=0, menu=0, hint=localization.GetByLabel('UI/Mail/Forward'))
        uiutil.MapIcon(d.sr.icon, 'ui_94_64_4', ignoreSize=True)
        left += self.space + self.extraSpace
        trashCont = uiprimitives.Container(name='deleteCont', parent=self, align=uiconst.TOPLEFT, pos=(left,
         top,
         size,
         size), hint=localization.GetByLabel('UI/Mail/Trash'))
        self.sr.trashBtn = e = uix.GetBigButton(size=size, where=trashCont, left=0, top=0, menu=0, hint=localization.GetByLabel('UI/Mail/Trash'))
        uiutil.MapIcon(e.sr.icon, 'ui_94_64_5', ignoreSize=True)
        deleteCont = uiprimitives.Container(name='deleteCont', parent=self, align=uiconst.TOPLEFT, pos=(left,
         top,
         size,
         size), hint=localization.GetByLabel('UI/Mail/Delete'))
        self.sr.deleteBtn = f = uix.GetBigButton(size=size, where=deleteCont, left=0, top=0, menu=0, hint=localization.GetByLabel('UI/Mail/Delete'))
        uiutil.MapIcon(f.sr.icon, 'res:/UI/Texture/WindowIcons/terminate.png', ignoreSize=True)
        left += self.space + self.extraSpace
        self.sr.singleMsgBtn = [b, c, d]
        self.width = left

    def Startup(self, data, showCompose = 1):
        self.sr.data = data
        self.sr.composeBtn.OnClick = data.Get('composeClicked', self.ComposeClicked)
        self.sr.replyBtn.OnClick = data.Get('replyClicked', self.ReplyClicked)
        self.sr.replyAllBtn.OnClick = data.Get('replyAllClicked', self.ReplyAllClicked)
        self.sr.forwardBtn.OnClick = data.Get('forwardClicked', self.ForwardClicked)
        self.sr.trashBtn.OnClick = data.Get('trashClicked', self.TrashClicked)
        self.sr.deleteBtn.OnClick = data.Get('deleteClicked', self.DeleteClicked)
        if not showCompose:
            self.sr.composeBtn.state = uiconst.UI_HIDDEN
            self.left -= self.space + self.leftOffset + self.extraSpace

    def DisableWhenManySelected(self, *args):
        pass

    def DisableDelete(self, *args):
        pass

    def ComposeClicked(self, *args):
        pass

    def ReplyClicked(self, *args):
        pass

    def ReplyAllClicked(self, *args):
        pass

    def ForwardClicked(self, *args):
        pass

    def TrashClicked(self, *args):
        pass

    def DeleteClicked(self, *args):
        pass

    def SetDeleteVisibility(self, disabled = 0, showDelete = 0):
        if showDelete:
            hiddenParent = self.sr.trashBtn.parent
            visibleBtn = self.sr.deleteBtn
        else:
            hiddenParent = self.sr.deleteBtn.parent
            visibleBtn = self.sr.trashBtn
        if hiddenParent is not None:
            self.SetDeleteState(disabled, hiddenParent, visibleBtn)

    def SetDeleteState(self, disabled, hiddenParent, visibleBtn):
        btnState = [uiconst.UI_NORMAL, uiconst.UI_DISABLED][disabled]
        opacity = [1.0, 0.3][disabled]
        parentState = [uiconst.UI_PICKCHILDREN, uiconst.UI_NORMAL][disabled]
        hiddenParent.state = uiconst.UI_HIDDEN
        visibleBtn.state = btnState
        visibleBtn.opacity = opacity
        visibleBtn.parent.state = parentState

    def SingleMsgBtnsState(self, disabled = 0, btns = None):
        if disabled:
            state = uiconst.UI_DISABLED
            alpha = 0.3
            parentState = uiconst.UI_NORMAL
        else:
            state = uiconst.UI_NORMAL
            alpha = 1.0
            parentState = uiconst.UI_PICKCHILDREN
        if btns is None:
            btns = self.sr.singleMsgBtn
        for btn in btns:
            if btn.parent is None:
                return
            btn.state = state
            btn.opacity = alpha
            btn.parent.state = parentState

    def SingleMsgBtnStateAllowFwd(self, *args):
        btns = self.sr.singleMsgBtn[:]
        btns.remove(self.sr.forwardBtn)
        self.SingleMsgBtnsState(disabled=1, btns=btns)
        self.SingleMsgBtnsState(disabled=0, btns=[self.sr.forwardBtn])

    def AddExtraButton(self, btn, withSpace = 1, size = None, hint = ''):
        left = self.width
        if withSpace:
            left += self.extraSpace
        if size is None:
            size = self.size
        cont = uiprimitives.Container(name='cont', parent=self, align=uiconst.TOPLEFT, pos=(left,
         self.topOffset,
         size,
         size), hint=hint)
        cont.children.append(btn)
        self.width = left + self.space


class MailSettings(uicontrols.Window):
    __guid__ = 'form.MailSettings'
    default_windowID = 'mailSettings'
    CHECKBOX_ACTIVE_ICON = 'res:/UI/Texture/classes/UtilMenu/checkBoxActive.png'
    CHECKBOX_INACTIVE_ICON = 'res:/UI/Texture/classes/UtilMenu/checkBoxInactive.png'
    mainCont = None
    default_iconNum = MailWindow.default_iconNum

    def ApplyAttributes(self, attributes):
        uicontrols.Window.ApplyAttributes(self, attributes)
        self.mailSettingObjectCopy = copy.deepcopy(sm.GetService('mailSvc').GetMailSettings())
        self.SetScope('all')
        self.SetTopparentHeight(0)
        self.SetCaption(localization.GetByLabel('UI/Mail/CommunicationSettings'))
        self.SetMinSize([350, 375], refresh=True)
        self.SetWndIcon(self.iconNum)
        self.sr.standardBtns = uicontrols.ButtonGroup(btns=[[localization.GetByLabel('UI/Mail/Apply'),
          self.OnApply,
          (),
          81], [localization.GetByLabel('UI/Commands/Cancel'),
          self.CloseByUser,
          (),
          81]])
        self.sr.main.children.insert(0, self.sr.standardBtns)
        mainCont = ContainerAutoSize(parent=self.sr.main, align=uiconst.TOTOP, alignMode=uiconst.TOTOP, padding=const.defaultPadding, callback=self.OnMainSizeChanged)
        self.mainCont = mainCont
        cost = sm.GetService('account').GetDefaultContactCost()
        uix.GetContainerHeader(localization.GetByLabel('UI/Mail/IncomingCommunications'), mainCont, bothlines=0)
        self.sr.accessCb1 = uicontrols.Checkbox(text=localization.GetByLabel('UI/Mail/RequireCSPNFromUnknown'), parent=mainCont, configName='accessCb1', retval=0, checked=cost != -1, groupname='communications', callback=self.OnCheckboxChange, padding=(6, 6, 6, 0), align=uiconst.TOTOP, hint=localization.GetByLabel('UI/Mail/CSPAHint'))
        self.sr.accessCb2 = uicontrols.Checkbox(text=localization.GetByLabel('UI/Mail/BlockUnknown'), parent=mainCont, configName='accessCb1', retval=1, checked=cost == -1, groupname='communications', callback=self.OnCheckboxChange, padding=(6, 0, 6, 6), align=uiconst.TOTOP, hint=localization.GetByLabel('UI/Mail/CSPAHint2'))
        self.sr.chargeCont = uiprimitives.Container(name='chargeCont', parent=mainCont, align=uiconst.TOTOP, pos=(0, 0, 0, 20), padding=(0, 0, 0, 6))
        if cost == -1:
            self.sr.chargeCont.state = uiconst.UI_HIDDEN
            cost = 0
        self.sr.chargeEdit = uicontrols.SinglelineEdit(name='chargeField', parent=self.sr.chargeCont, setvalue=cost, maxLength=32, pos=(150, 0, 60, 0), label='', align=uiconst.TOPLEFT, ints=[0, 1000000])
        label = uicontrols.EveLabelSmall(text=localization.GetByLabel('UI/Mail/CSPACharge'), parent=self.sr.chargeCont, align=uiconst.CENTERLEFT, width=150, left=8)
        uix.GetContainerHeader(localization.GetByLabel('UI/Mail/MailSettings'), mainCont)
        perPageCont = uiprimitives.Container(name='perPageCont', parent=mainCont, align=uiconst.TOTOP, pos=(0, 0, 0, 20), padding=(0, 0, 0, 6))
        perPageNumer = self.mailSettingObjectCopy.GetSingleValue(cSettings.MAILS_PER_PAGE, DEFAULTNUMMAILS)
        self.sr.perPageEdit = uicontrols.SinglelineEdit(name='perPageEdit', parent=perPageCont, setvalue=perPageNumer, maxLength=32, pos=(150, 4, 60, 0), label='', align=uiconst.TOPLEFT, ints=[MINNUMMAILS, MAXNUMMAILS])
        label = uicontrols.EveLabelSmall(text=localization.GetByLabel('UI/Mail/MailsPerPage'), parent=perPageCont, align=uiconst.CENTERLEFT, width=150, left=8)
        getSearchWnd = self.mailSettingObjectCopy.GetSingleValue(cSettings.MAIL_GET_SEARCH_WND, True)
        self.sr.getSearchWnd = uicontrols.Checkbox(text=localization.GetByLabel('UI/Mail/ShowSearch'), parent=mainCont, configName='getSearchWnd', retval=0, checked=getSearchWnd, align=uiconst.TOTOP, padding=(6, 0, 0, 0))
        t = uicontrols.EveLabelSmall(text=localization.GetByLabel('UI/Mail/WhenReceived'), parent=mainCont, align=uiconst.TOTOP, padding=(8, 10, 8, 0), state=uiconst.UI_DISABLED)
        isNeocomBlinkOnForMail = self.mailSettingObjectCopy.GetSingleValue(cSettings.MAIL_BLINK_NEOCOM, True)
        isTabBlinkOnForMail = self.mailSettingObjectCopy.GetSingleValue(cSettings.MAIL_BLINK_TAB, True)
        isPopupOnForMail = self.mailSettingObjectCopy.GetSingleValue(cSettings.MAIL_SHOW_POPUP, True)
        self.sr.mailBlinkNeocomCB = uicontrols.Checkbox(text=localization.GetByLabel('UI/Mail/BlinkMailNeoComButton'), parent=mainCont, configName='mailBlinkNeocomCB', retval=0, checked=bool(isNeocomBlinkOnForMail), align=uiconst.TOTOP, padding=(16, 0, 0, 0))
        self.sr.mailBlinkTabCB = uicontrols.Checkbox(text=localization.GetByLabel('UI/Mail/BlinkTab'), parent=mainCont, configName='mailBlinkTabCB', retval=0, checked=bool(isTabBlinkOnForMail), align=uiconst.TOTOP, padding=(16, 0, 0, 0))
        self.sr.mailNotificationCB = uicontrols.Checkbox(text=localization.GetByLabel('UI/Mail/ShowNotification'), parent=mainCont, configName='mailNotificationCB', retval=0, checked=bool(isPopupOnForMail), align=uiconst.TOTOP, padding=(16, 0, 0, 0))
        self.settingCb = {}

    def OnMainSizeChanged(self, *args, **kwds):
        if self.mainCont:
            self.SetMinSize([350, max(375, self.mainCont.height + 50)])

    def OpenMenuFunc(self, menuParent, settingKey, *args):
        disabledGroups = self.mailSettingObjectCopy.GetListForSettingKey(settingKey)
        headerChecked = not bool(disabledGroups)
        if headerChecked:
            icon = self.CHECKBOX_ACTIVE_ICON
        else:
            icon = self.CHECKBOX_INACTIVE_ICON
        menuParent.AddHeader(text=localization.GetByLabel('UI/Common/All'), callback=(self.ToggleAll, settingKey), icon=icon)
        menuParent.AddSpace()
        checkboxes = []
        for groupID, labelPath in notificationGroupNamePaths.iteritems():
            checked = groupID not in disabledGroups
            groupName = localization.GetByLabel(labelPath)
            checkboxes.append((groupName, groupID, checked))

        checkboxes.sort()
        for groupName, groupID, checked in checkboxes:
            menuParent.AddCheckBox(text=groupName, checked=checked, callback=(self.ToggleGroup, groupID, settingKey), indentation=10)

        menuParent.AddSpace()
        self.RefreshIcon(settingKey)

    def RefreshIcon(self, settingKey):
        iconOwner = self.settingCb.get(settingKey)
        if not iconOwner:
            return
        numGroups = len(notificationGroupNamePaths)
        disabledGroups = self.mailSettingObjectCopy.GetListForSettingKey(settingKey)
        if not disabledGroups:
            path = 'res:/UI/Texture/Shared/checkboxChecked.png'
        elif len(disabledGroups) < numGroups:
            path = 'res:/UI/Texture/Shared/checkboxMinus.png'
        else:
            iconOwner.iconCheckmark.display = False
            return
        iconOwner.iconCheckmark.SetTexturePath(path)
        iconOwner.iconCheckmark.display = True

    def ToggleAll(self, settingKey):
        disabledGroups = self.mailSettingObjectCopy.GetListForSettingKey(settingKey)
        if disabledGroups:
            newGroupList = []
        else:
            newGroupList = [ groupID for groupID in notificationGroupNamePaths.iterkeys() ]
        self.mailSettingObjectCopy.UpdateSettingListWithNewValues(settingKey, newGroupList)

    def ToggleGroup(self, groupID, settingKey):
        if groupID in self.mailSettingObjectCopy.GetListForSettingKey(settingKey):
            self.mailSettingObjectCopy.RemoveValueFromListSetting(settingKey, groupID)
        else:
            self.mailSettingObjectCopy.AddValueToListSetting(settingKey, groupID)

    def OnCheckboxChange(self, checkbox):
        config = checkbox.data.get('config', None)
        if config == None:
            return
        value = checkbox.data.get('value', None)
        if value is None:
            return
        if value == 1:
            self.sr.chargeCont.state = uiconst.UI_HIDDEN
        else:
            self.sr.chargeCont.state = uiconst.UI_PICKCHILDREN
        settings.char.ui.Set('mail_accessCombo', value)

    def OnApply(self, *args):
        oldCost = sm.GetService('account').GetDefaultContactCost()
        if self.sr.accessCb1.checked:
            cost = self.sr.chargeEdit.GetValue()
            if cost != oldCost:
                sm.GetService('account').SetDefaultContactCost(self.sr.chargeEdit.GetValue())
        elif oldCost != -1:
            sm.GetService('account').BlockAll()
        mailBlinkNeocom = self.sr.mailBlinkNeocomCB.GetValue()
        mailBlinkTab = self.sr.mailBlinkTabCB.GetValue()
        mailNotification = self.sr.mailNotificationCB.GetValue()
        getSearchWnd = self.sr.getSearchWnd.GetValue()
        self.mailSettingObjectCopy.SetSingleValue(cSettings.MAIL_BLINK_NEOCOM, mailBlinkNeocom)
        self.mailSettingObjectCopy.SetSingleValue(cSettings.MAIL_BLINK_TAB, mailBlinkTab)
        self.mailSettingObjectCopy.SetSingleValue(cSettings.MAIL_SHOW_POPUP, mailNotification)
        self.mailSettingObjectCopy.SetSingleValue(cSettings.MAIL_GET_SEARCH_WND, getSearchWnd)
        perPage = self.sr.perPageEdit.GetValue()
        oldPerPage = self.mailSettingObjectCopy.GetSingleValue(cSettings.MAILS_PER_PAGE, DEFAULTNUMMAILS)
        self.mailSettingObjectCopy.SetSingleValue(cSettings.MAILS_PER_PAGE, perPage)
        sm.GetService('mailSvc').SaveMailSettingsOnServer(self.mailSettingObjectCopy)
        if perPage != oldPerPage:
            sm.ScatterEvent('OnMailSettingsChanged')
        self.CloseByUser()


class MailinglistWnd(uicontrols.Window):
    __guid__ = 'form.MailinglistWnd'
    default_windowID = 'MailinglistWnd'
    default_iconNum = MailWindow.default_iconNum

    def ApplyAttributes(self, attributes):
        uicontrols.Window.ApplyAttributes(self, attributes)
        self.scope = 'station_inflight'
        self.SetMinSize([240, 100], refresh=True)
        self.MakeUnResizeable()
        self.SetCaption(localization.GetByLabel('UI/Mail/CreateOrJoinML'))
        self.SetWndIcon(self.iconNum)
        self.SetTopparentHeight(70)
        self.sr.inpt = inpt = uicontrols.SinglelineEdit(name='input', parent=self.sr.topParent, maxLength=const.mailingListMaxNameSize, pos=(74, 20, 86, 0), label=localization.GetByLabel('UI/Mail/MailingListName'))
        joinBtn = uicontrols.Button(parent=self.sr.topParent, label=localization.GetByLabel('UI/Mail/Join'), pos=(inpt.left,
         inpt.top + inpt.height + 4,
         0,
         0), func=self.JoinMaillist, args=(0,), btn_default=1)
        createBtn = uicontrols.Button(parent=self.sr.topParent, label=localization.GetByLabel('UI/Mail/Create'), pos=(joinBtn.left + joinBtn.width + 2,
         joinBtn.top,
         0,
         0), func=self.CreateMaillist, args=(1,))
        self.sr.inpt.width = max(100, joinBtn.left + joinBtn.width - inpt.left)

    def CreateMaillist(self, *args):
        """
            when the player clicks the CREATE button, this function is entered.
        """
        name = self.sr.inpt.GetValue()
        if name.strip() == '':
            eve.Message('LookupStringMinimum', {'minimum': 1})
            return
        if len(name) > const.mailingListMaxNameSize:
            raise UserError('CustomNotify', {'notify': localization.GetByLabel('UI/Mail/NameIsTooLong')})
        ret = sm.GetService('mailinglists').CreateMailingList(name)
        if ret is not None:
            self.CloseByUser()

    def JoinMaillist(self, *args):
        """
            when the player clicks the JOIN button, this function is entered.
        """
        name = self.sr.inpt.GetValue()
        if name.strip() == '':
            eve.Message('LookupStringMinimum', {'minimum': 1})
            return
        ret = sm.GetService('mailinglists').JoinMailingList(name)
        if ret is not None:
            self.CloseByUser()


class CharacterSearchWindowMail(CharacterSearchWindow):
    """
        A special search window which includes mailing lists and the player's corporation / alliance when appropriate.
    """
    __guid__ = 'form.CharacterSearchWindowMail'
    default_windowID = 'searchWindow_mail'

    def GetExtraSearchEntries(self, searchTerm, searchBy):
        extraEntries = []
        myLists = sm.GetService('mailinglists').GetMyMailingLists()
        for key, value in myLists.iteritems():
            if searchUtil.IsMatch(searchTerm, value.displayName, searchBy):
                entry = self.GetCorpAllianceMailingListEntry(None, 1, key, value.displayName)
                extraEntries.append((value.displayName.lower(), entry))

        extraEntries = uiutil.SortListOfTuples(extraEntries)
        if session.allianceid and session.corprole & const.corpRoleChatManager == const.corpRoleChatManager:
            allianceName = cfg.eveowners.Get(session.allianceid).ownerName
            if searchUtil.IsMatch(searchTerm, allianceName, searchBy):
                entry = self.GetCorpAllianceMailingListEntry(const.typeAlliance, 0, session.allianceid, allianceName)
                extraEntries.insert(0, entry)
        if not util.IsNPC(session.corpid):
            corpName = cfg.eveowners.Get(session.corpid).ownerName
            if searchUtil.IsMatch(searchTerm, corpName, searchBy):
                entry = self.GetCorpAllianceMailingListEntry(const.typeCorporation, 0, session.corpid, corpName)
                extraEntries.insert(0, entry)
        return extraEntries

    def GetCorpAllianceMailingListEntry(self, type, mailingList, id, name):
        data = util.KeyVal()
        data.confirmOnDblClick = 1
        if type is None:
            if mailingList:
                data.label = localization.GetByLabel('UI/Mail/MailEntry', entryName=name, entryType=localization.GetByLabel('UI/Mail/ML'))
                data.itemID = None
                data.typeID = None
                data.mailingListID = id
                data.name = name
            else:
                return
        else:
            if type == const.typeCorporation:
                data.label = localization.GetByLabel('UI/Mail/MailEntry', entryName=name, entryType=localization.GetByLabel('UI/Mail/LabelCorp'))
            elif type == const.typeAlliance:
                data.label = localization.GetByLabel('UI/Mail/MailEntry', entryName=name, entryType=localization.GetByLabel('UI/Mail/LabelAlliance'))
            data.itemID = id
            data.typeID = type
            data.name = name
        data.OnClick = self.ClickEntry
        data.OnDblClick = self.DblClickEntry
        entry = listentry.Get('CorpAllianceEntry', data=data)
        return entry


class MailAssignColorWnd(uiprimitives.Container):
    __guid__ = 'xtriui.MailAssignColorWnd'

    def Startup(self, labelID, doneCallback = None, doneArgs = (), *args):
        container = uiprimitives.Container(name='headercontainer', parent=self, align=uiconst.TOTOP, pos=(0, 0, 0, 18), idx=0)
        t = uicontrols.EveHeaderSmall(text=localization.GetByLabel('UI/Mail/Select Color'), parent=container, left=8, align=uiconst.TOALL, top=5, state=uiconst.UI_DISABLED)
        uiprimitives.Line(parent=container, align=uiconst.TOBOTTOM, top=-1)
        colorCont = uiprimitives.Container(name='colorCont', parent=self, align=uiconst.TOALL, padding=(const.defaultPadding,
         const.defaultPadding,
         const.defaultPadding,
         const.defaultPadding))
        self.sr.underlay = uicontrols.WindowUnderlay(parent=self)
        self.sr.underlay.padding = (0, -18, 0, -2)
        self.labelID = labelID
        colorSwatch = ColorSwatch(name='colorSwatch', parent=colorCont, align=uiconst.TOALL, pos=(0, 0, 0, 0))
        colorSwatch.OnPickColor = self.PickCol
        colorSwatch.swatches = sm.StartService('mailSvc').GetSwatchColors().values()
        colorSwatch.Startup(frameColor=(0.0, 0.0, 0.0, 0.0), padding=1)
        self.top = uicore.uilib.y - 35
        self.left = uicore.uilib.x - 20
        self.doneCallback = doneCallback
        self.doneArgs = doneArgs

    def PickCol(self, obj, *args):
        if getattr(obj, 'swatchID', None) is not None:
            if self.doneCallback is not None:
                args = tuple([obj.swatchID]) + self.doneArgs
                apply(self.doneCallback, args)
            self.Close()


class SearchedUser(User):
    __guid__ = 'listentry.SearchedUser'
    __notifyevents__ = ['OnContactLoggedOn',
     'OnContactLoggedOff',
     'OnClientContactChangeOnPortraitCreated',
     'OnContactNoLongerContact',
     'OnStateSetupChance',
     'ProcessSessionChange',
     'OnFleetJoin',
     'OnFleetLeave',
     'ProcessOnUIAllianceRelationshipChanged',
     'OnContactChange',
     'OnBlockContacts',
     'OnUnblockContacts']

    def Startup(self, *args):
        self.pictureLeft = 14
        self.labelLeft = 52
        User.Startup(self, *args)
        self.sr.picture.left = self.pictureLeft
        self.sr.namelabel.left = self.labelLeft

    def PreLoad(node):
        User.PreLoad(node)
        node.isAdded = False
        node.extraIcon = None
        node.hint = ''
        if node.Get('extraInfo', None) is not None:
            extraIconHintFlag = getattr(node.extraInfo, 'extraIconHintFlag', None)
            if extraIconHintFlag:
                extraIcon, hint, isAdded = extraIconHintFlag
                node.isAdded = isAdded
                node.extraIcon = extraIcon
                node.hint = ''

    def Load(self, node, *args):
        User.Load(self, node, *args)
        self.sr.picture.left = self.pictureLeft
        self.sr.namelabel.left = self.labelLeft
        self.extraInfo = self.sr.node.Get('extraInfo', None)
        self.configname = util.GetAttrs(self, 'extraInfo', 'wndConfigname')
        self.extraIconHintFlag = None
        if self.extraInfo is not None:
            if node.extraIcon:
                uix.Flush(self.sr.extraIconCont)
                icon = uicontrols.Icon(parent=self.sr.extraIconCont, icon=node.extraIcon, pos=(0, 0, 0, 0), hint=node.hint)
                self.sr.extraIconCont.SetAlign(uiconst.CENTERLEFT)
        self.SearcedUserAddedOrRemoved(node.isAdded)

    def SearcedUserAddedOrRemoved(self, wasAdded = 0):
        if wasAdded:
            self.sr.extraIconCont.state = uiconst.UI_PICKCHILDREN
        else:
            self.sr.extraIconCont.state = uiconst.UI_HIDDEN

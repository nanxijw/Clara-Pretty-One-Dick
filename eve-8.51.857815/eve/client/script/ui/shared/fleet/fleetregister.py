#Embedded file name: eve/client/script/ui/shared/fleet\fleetregister.py
import uiprimitives
import uicontrols
import util
import carbonui.const as uiconst
import uicls
import localization
from fleetcommon import *
WINDOW_WIDTH = 300

class RegisterFleetWindow(uicontrols.Window):
    __guid__ = 'form.RegisterFleetWindow'
    default_windowID = 'RegisterFleetWindow'

    def ApplyAttributes(self, attributes):
        uicontrols.Window.ApplyAttributes(self, attributes)
        fleetInfo = attributes.fleetInfo
        self.SetTopparentHeight(0)
        self.SetCaption(localization.GetByLabel('UI/Fleet/CreateAdvert'))
        self.SetWndIcon(None)
        self.MakeUnResizeable()
        self.sr.scopeRadioButtons = []
        self.SetupStuff(fleetInfo)

    def SetupStuff(self, fleetInfo = None):
        publicIsGood = False
        publicIsHigh = False
        localIsGood = False
        localIsHigh = False
        if not fleetInfo:
            fleetInfo = settings.user.ui.Get('fleetAdvert_lastAdvert', util.KeyVal())
        fleetName = fleetInfo.get('fleetName', localization.GetByLabel('UI/Fleet/DefaultFleetName', char=session.charid))
        description = fleetInfo.get('description', '')
        needsApproval = fleetInfo.get('joinNeedsApproval', False)
        hideInfo = fleetInfo.get('hideInfo', False)
        localMinStanding = fleetInfo.get('local_minStanding', None)
        localMinSecurity = fleetInfo.get('local_minSecurity', None)
        publicMinStanding = fleetInfo.get('public_minStanding', None)
        publicMinSecurity = fleetInfo.get('public_minSecurity', None)
        myCorp = IsOpenToCorp(fleetInfo)
        myAlliance = IsOpenToAlliance(fleetInfo)
        myMilitia = IsOpenToMilitia(fleetInfo)
        isPublic = IsOpenToPublic(fleetInfo)
        if publicMinStanding == const.contactGoodStanding:
            publicIsGood = True
        elif publicMinStanding == const.contactHighStanding:
            publicIsHigh = True
        if localMinStanding == const.contactGoodStanding:
            localIsGood = True
        elif localMinStanding == const.contactHighStanding:
            localIsHigh = True
        self.sr.main.Flush()
        self.sr.main.padding = 6
        uicontrols.EveLabelSmall(text=localization.GetByLabel('UI/Fleet/NameOfFleet'), parent=self.sr.main, padTop=6, align=uiconst.TOTOP)
        self.sr.fleetName = uicontrols.SinglelineEdit(name='fleetName', parent=self.sr.main, align=uiconst.TOTOP, maxLength=FLEETNAME_MAXLENGTH, setvalue=fleetName)
        uicontrols.EveLabelSmall(text=localization.GetByLabel('UI/Fleet/Description'), parent=self.sr.main, padTop=6, align=uiconst.TOTOP)
        self.sr.description = uicls.EditPlainText(setvalue=description, parent=self.sr.main, align=uiconst.TOTOP, height=64, maxLength=FLEETDESC_MAXLENGTH)
        openFleetText = uicontrols.EveLabelSmall(text=localization.GetByLabel('UI/Fleet/FleetRegistry/OpenFleetTo'), parent=self.sr.main, align=uiconst.TOTOP, state=uiconst.UI_NORMAL, padTop=6)
        self.sr.myCorpButton = uicontrols.Checkbox(text=localization.GetByLabel('UI/Fleet/FleetRegistry/MyCorporation'), parent=self.sr.main, configName='corp', retval='1', checked=myCorp, hint=localization.GetByLabel('UI/Fleet/FleetRegistry/CorpOnlyHint'))
        if session.allianceid is not None:
            self.sr.myAllianceButton = uicontrols.Checkbox(text=localization.GetByLabel('UI/Fleet/FleetRegistry/MyAlliance'), parent=self.sr.main, configName='alliance', retval='1', checked=myAlliance, hint=localization.GetByLabel('UI/Fleet/FleetRegistry/AllianceOnlyHint'), align=uiconst.TOTOP)
        if session.warfactionid is not None:
            self.sr.myMilitiaButton = uicontrols.Checkbox(text=localization.GetByLabel('UI/Fleet/FleetRegistry/MyMilitia'), parent=self.sr.main, configName='militia', retval='1', checked=myMilitia, hint=localization.GetByLabel('UI/Fleet/FleetRegistry/MyMilitiahint'), align=uiconst.TOTOP)
        self.sr.requireLocalStandingButton = uicontrols.Checkbox(text=localization.GetByLabel('UI/Fleet/FleetRegistry/RequireStanding'), parent=self.sr.main, configName='requireLocalStanding', retval='1', checked=bool(localMinStanding), align=uiconst.TOTOP, hint=localization.GetByLabel('UI/Fleet/FleetRegistry/RequireStandingHint'), padLeft=18)
        self.sr.localGoodStandingCB = uicontrols.Checkbox(text=localization.GetByLabel('UI/Standings/Good'), parent=self.sr.main, configName='localgood', retval=const.contactGoodStanding, checked=localIsGood, groupname='localStanding', align=uiconst.TOTOP, padLeft=36)
        self.sr.localHighStandingCB = uicontrols.Checkbox(text=localization.GetByLabel('UI/Standings/Excellent'), parent=self.sr.main, configName='localhigh', retval=const.contactHighStanding, checked=localIsHigh, groupname='localStanding', align=uiconst.TOTOP, padLeft=36)
        startVal = 0.5
        if localMinSecurity is not None:
            startVal = localMinSecurity / 20.0 + 0.5
        self.sr.requireLocalSecurityButton = uicontrols.Checkbox(text=localization.GetByLabel('UI/Fleet/FleetRegistry/RequireSecurity', securityLevel=startVal), parent=self.sr.main, configName='requireLocalSecurity', retval='1', checked=localMinSecurity is not None, align=uiconst.TOTOP, padLeft=18, hint=localization.GetByLabel('UI/Fleet/FleetRegistry/RequireSecurityHint'))
        self.sr.localSecuritySlider = self.AddSlider(self.sr.main, 'localSecurity', -10, 10.0, '', startVal=startVal, padLeft=18)
        self.sr.localSecuritySlider.SetValue(startVal)
        self.sr.publicButton = uicontrols.Checkbox(text=localization.GetByLabel('UI/Fleet/FleetRegistry/BasedOnStandings'), parent=self.sr.main, configName='public', retval='1', checked=isPublic, align=uiconst.TOTOP, hint=localization.GetByLabel('UI/Fleet/FleetRegistry/AddPilots'))
        standingText = uicontrols.EveLabelSmall(text=localization.GetByLabel('UI/Fleet/FleetRegistry/RequireStanding'), parent=self.sr.main, align=uiconst.TOTOP, state=uiconst.UI_NORMAL, padLeft=18)
        self.sr.publicGoodStandingCB = uicontrols.Checkbox(text=localization.GetByLabel('UI/Standings/Good'), parent=self.sr.main, configName='publicgood', retval=const.contactGoodStanding, checked=publicIsGood, groupname='publicStanding', align=uiconst.TOTOP, padLeft=18)
        self.sr.publicHighStandingCB = uicontrols.Checkbox(text=localization.GetByLabel('UI/Standings/Excellent'), parent=self.sr.main, configName='publichigh', retval=const.contactHighStanding, checked=publicIsHigh, groupname='publicStanding', align=uiconst.TOTOP, padLeft=18)
        startVal = 0.5
        if publicMinSecurity is not None:
            startVal = publicMinSecurity / 20.0 + 0.5
        self.sr.requirePublicSecurityButton = uicontrols.Checkbox(text=localization.GetByLabel('UI/Fleet/FleetRegistry/RequireSecurity', securityLevel=startVal), parent=self.sr.main, configName='requirePublicSecurity', retval='1', checked=publicMinSecurity is not None, hint=localization.GetByLabel('UI/Fleet/FleetRegistry/RequireSecurityHint'), padLeft=18)
        self.sr.publicSecuritySlider = self.AddSlider(self.sr.main, 'publicSecurity', -10, 10.0, '', startVal=startVal, padLeft=18)
        self.sr.publicSecuritySlider.SetValue(startVal)
        uiprimitives.Line(parent=self.sr.main, align=uiconst.TOTOP, padLeft=-self.sr.main.padLeft, padRight=-self.sr.main.padRight, padTop=6, padBottom=3)
        self.sr.needsApprovalButton = uicontrols.Checkbox(text=localization.GetByLabel('UI/Fleet/FleetRegistry/RequireApproval'), parent=self.sr.main, configName='needsApproval', retval='1', checked=needsApproval, hint=localization.GetByLabel('UI/Fleet/FleetRegistry/RequireApprovalHint'))
        self.sr.hideInfoButton = uicontrols.Checkbox(text=localization.GetByLabel('UI/Fleet/FleetRegistry/HideInfo'), parent=self.sr.main, configName='hideInfo', retval='1', checked=hideInfo, hint=localization.GetByLabel('UI/Fleet/FleetRegistry/HideInfoHint'), padBottom=6)
        self.sr.submitButtons = uicontrols.ButtonGroup(btns=[[localization.GetByLabel('UI/Common/Buttons/Submit'), self.Submit, ()], [localization.GetByLabel('UI/Common/Buttons/Cancel'), self.CloseByUser, ()]], parent=self.sr.main, idx=0, padLeft=-self.sr.main.padLeft, padRight=-self.sr.main.padRight)
        windowHeight = sum([ each.height + each.padTop + each.padBottom for each in self.sr.main.children ]) + self.GetHeaderHeight() + self.sr.main.padTop + self.sr.main.padBottom
        self.SetMinSize([WINDOW_WIDTH, windowHeight], refresh=True)

    def SlideIt(self, startVal):
        self.sr.slider.SlideTo(startVal, 1)

    def AddSlider(self, where, config, minval, maxval, header, hint = '', startVal = 0, padLeft = 0):
        h = 10
        _par = uiprimitives.Container(name=config + '_slider', parent=where, align=uiconst.TOTOP, padLeft=padLeft, height=10)
        par = uiprimitives.Container(name=config + '_slider_sub', parent=_par, align=uiconst.TOPLEFT, pos=(18, 0, 180, 10))
        slider = uicontrols.Slider(parent=par)
        lbl = uicontrols.EveLabelSmall(text='bla', parent=par, width=200, left=-34, top=0, state=uiconst.UI_NORMAL)
        setattr(self.sr, '%sLabel' % config, lbl)
        lbl.name = 'label'
        slider.SetSliderLabel = getattr(self, 'SetSliderLabel_%s' % config)
        lbl.state = uiconst.UI_HIDDEN
        slider.Startup(config, minval, maxval, None, header, startVal=startVal)
        if startVal < minval:
            startVal = minval
        slider.value = startVal
        slider.name = config
        slider.hint = hint
        slider.OnSetValue = getattr(self, 'OnSetValue_%s' % config)
        return slider

    def SetSliderLabel_localSecurity(self, label, idname, dname, value):
        self.sr.localSecurityLabel.text = '%.1f' % value

    def SetSliderLabel_publicSecurity(self, label, idname, dname, value):
        self.sr.publicSecurityLabel.text = '%.1f' % value

    def OnSetValue_localSecurity(self, *args):
        self.sr.requireLocalSecurityButton.SetLabelText(localization.GetByLabel('UI/Fleet/FleetRegistry/RequireSecurity', securityLevel=float(self.sr.localSecurityLabel.text)))

    def OnSetValue_publicSecurity(self, *args):
        self.sr.requirePublicSecurityButton.SetLabelText(localization.GetByLabel('UI/Fleet/FleetRegistry/RequireSecurity', securityLevel=float(self.sr.publicSecurityLabel.text)))

    def Submit(self):
        fleetSvc = sm.GetService('fleet')
        info = util.KeyVal()
        info.fleetName = self.sr.fleetName.GetValue()
        info.description = self.sr.description.GetValue()
        info.inviteScope = INVITE_CLOSED
        info.public_minStanding = None
        info.public_minSecurity = None
        info.public_allowedEntities = set()
        info.local_minStanding = None
        info.local_minSecurity = None
        info.local_allowedEntities = set()
        if self.sr.myCorpButton.checked:
            info.inviteScope += INVITE_CORP
        if session.allianceid is not None:
            if self.sr.myAllianceButton.checked:
                info.inviteScope += INVITE_ALLIANCE
        if session.warfactionid is not None:
            if self.sr.myMilitiaButton.checked:
                info.inviteScope += INVITE_MILITIA
        if self.sr.publicButton.checked:
            info.inviteScope += INVITE_PUBLIC
            if self.sr.publicGoodStandingCB.checked:
                info.public_minStanding = const.contactGoodStanding
            elif self.sr.publicHighStandingCB.checked:
                info.public_minStanding = const.contactHighStanding
            else:
                raise UserError('FleetInviteAllWithoutStanding')
            info.public_allowedEntities = self.GetAllowedEntities(info.public_minStanding)
            if self.sr.requirePublicSecurityButton.checked:
                info.public_minSecurity = self.sr.publicSecuritySlider.value
        noAccess = False
        if IsOpenToCorp(info) or IsOpenToAlliance(info) or IsOpenToMilitia(info):
            if self.sr.requireLocalStandingButton.checked:
                if self.sr.localGoodStandingCB.checked:
                    info.local_minStanding = const.contactGoodStanding
                elif self.sr.localHighStandingCB.checked:
                    info.local_minStanding = const.contactHighStanding
                else:
                    raise UserError('FleetInviteAllWithoutStanding')
                info.local_allowedEntities = self.GetAllowedEntities(info.local_minStanding)
            else:
                if IsOpenToCorp(info):
                    info.local_allowedEntities.add(session.corpid)
                if session.allianceid is not None and IsOpenToAlliance(info):
                    info.local_allowedEntities.add(session.allianceid)
                if session.warfactionid is not None and IsOpenToMilitia(info):
                    info.local_allowedEntities.add(session.warfactionid)
            if self.sr.requireLocalSecurityButton.checked:
                info.local_minSecurity = self.sr.localSecuritySlider.value
        elif not IsOpenToPublic(info):
            noAccess = True
        if IsOpenToPublic(info) and info.public_minStanding is not None:
            if len(info.public_allowedEntities) + len(info.local_allowedEntities) == 0:
                noAccess = True
        if noAccess:
            if eve.Message('FleetNobodyHasAccess', {}, uiconst.YESNO, suppress=uiconst.ID_YES) != uiconst.ID_YES:
                return
        info.joinNeedsApproval = not not self.sr.needsApprovalButton.checked
        info.hideInfo = not not self.sr.hideInfoButton.checked
        fleetSvc.RegisterFleet(info)
        settings.user.ui.Set('fleetAdvert_lastAdvert', info)
        self.CloseByUser()

    def GetAllowedEntities(self, minRelationship):
        """
        gets all entities statisfying standing requirements
        """
        return sm.GetService('addressbook').GetContactsByMinRelationship(minRelationship)

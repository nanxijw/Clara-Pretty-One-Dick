#Embedded file name: eve/client/script/ui/shared/neocom\compare.py
import blue
from inventorycommon.const import compareCategories
import uiprimitives
import uicontrols
import uiutil
from dogma.attributes.format import FormatUnit, GetFormatAndValue
from eve.client.script.ui.control import entries as listentry
import util
import carbon.client.script.util.lg as lg
import carbonui.const as uiconst
import localization
from eve.client.script.ui.control.divider import Divider
from collections import OrderedDict

class TypeCompare(uicontrols.Window):
    __guid__ = 'form.TypeCompare'
    default_windowID = 'typecompare'
    default_iconNum = 'res:/ui/Texture/WindowIcons/comparetool.png'
    default_captionLabelPath = 'Tooltips/Neocom/CompareTool'
    default_descriptionLabelPath = 'Tooltips/Neocom/CompareTool_description'

    def ApplyAttributes(self, attributes):
        uicontrols.Window.ApplyAttributes(self, attributes)
        self.dogmaLocation = sm.GetService('clientDogmaIM').GetDogmaLocation()
        self.typeIDs = []
        self.attrDictChecked = []
        self.banAttrs = [const.attributeTechLevel] + sm.GetService('info').GetSkillAttrs()
        self.attributeLimit = 10
        self.typeLimit = 40
        self.settingsinited = 0
        self.graphinited = 0
        self.compareinited = 0
        self.topLevelMarketGroup = None
        self.attrDictIDs = []
        self.allowedGuids = ['xtriui.InvItem',
         'xtriui.FittingSlot',
         'listentry.InvItem',
         'listentry.GenericMarketItem',
         'listentry.QuickbarItem',
         'listentry.InvAssetItem',
         'xtriui.ShipUIModule',
         'uicls.GenericDraggableForTypeID',
         'listentry.Item',
         'listentry.KillItems']
        self.SetWndIcon()
        self.SetTopparentHeight(0)
        self.SetMinSize([350, 400])
        self.LoadPanels()
        self.LoadCompare()

    def LoadPanels(self):
        bottomparent = uiprimitives.Container(name='bottomparent', parent=self.sr.main, align=uiconst.TOBOTTOM, height=25)
        uiprimitives.Line(parent=bottomparent, align=uiconst.TOTOP)
        self.sr.bottomparent = bottomparent
        panel = uiprimitives.Container(name='panel', parent=self.sr.main, left=const.defaultPadding, top=const.defaultPadding, width=const.defaultPadding, height=const.defaultPadding)
        self.sr.panel = panel

    def LogInfo(self, *args):
        lg.Info(self.__guid__, *args)

    def LoadCompare(self):
        if not self.compareinited:
            subpanel = uiprimitives.Container(name='subpanel', parent=self.sr.panel, align=uiconst.TOALL, pos=(0, 0, 0, 0))
            self.sr.subpanel = subpanel
            bottomclear = uiprimitives.Container(name='typecompare_bottomclear', parent=self.sr.subpanel, height=60, align=uiconst.TOBOTTOM)
            uicontrols.EveLabelMedium(text=localization.GetByLabel('UI/Compare/CompareTypeAttributeLimit', attributeLimit=self.attributeLimit, typeLimit=self.typeLimit), parent=bottomclear, align=uiconst.TOALL, width=const.defaultPadding, height=const.defaultPadding, state=uiconst.UI_NORMAL)
            attributescroll = uiprimitives.Container(name='typecompare_attributescroll', parent=self.sr.subpanel, align=uiconst.TOLEFT, left=0, width=settings.user.ui.Get('charsheetleftwidth', 125), idx=0)
            self.sr.attributescroll = uicontrols.Scroll(name='attributescroll', parent=attributescroll, padding=(0,
             const.defaultPadding,
             0,
             const.defaultPadding))
            self.sr.attributescroll.sr.id = 'typecompare_attributescroll'
            self.sr.attributescroll.hiliteSorted = 0
            self.sr.attributescroll.ShowHint(localization.GetByLabel('UI/Compare/NothingToCompare'))
            typescroll = uiprimitives.Container(name='typecompare_typescroll', parent=self.sr.subpanel, align=uiconst.TOALL, pos=(0, 0, 0, 0))
            self.sr.typescroll = uicontrols.Scroll(name='typescroll', parent=typescroll, left=0, top=const.defaultPadding, width=2, height=const.defaultPadding)
            self.sr.typescroll.ShowHint(localization.GetByLabel('UI/Compare/CompareToolHint'))
            divider = Divider(name='divider', align=uiconst.TOLEFT, idx=1, width=const.defaultPadding, parent=self.sr.subpanel, state=uiconst.UI_NORMAL)
            divider.Startup(attributescroll, 'width', 'x', 160, 200)
            self.sr.typescroll.sr.id = 'typecompare_typescroll'
            btns = uicontrols.ButtonGroup(btns=[[localization.GetByLabel('UI/Commands/UncheckAll'),
              self.SelectAll,
              (0,),
              None], [localization.GetByLabel('UI/Commands/ResetAll'),
              self.RemoveAllEntries,
              (),
              None]], parent=self.sr.bottomparent, idx=0, unisize=0)
            self.sr.typescroll.sr.content.OnDropData = self.OnDropData
            self.compareinited = 1

    def RemoveAllEntries(self, *args):
        self.typeIDs = []
        self.topLevelMarketGroup = None
        self.SelectAll()

    def SelectAll(self, onOff = 0):
        if onOff:
            return
        self.attrDictChecked = []
        self.OnColumnChanged()

    def AddTypeID(self, typeID):
        self.AddEntry(cfg.invtypes.Get(typeID))

    def AddEntry(self, nodes):
        if self.compareinited:
            if type(nodes) != type([]):
                nodes = [nodes]
            current = [ node.typeID for node in self.typeIDs ]
            valid = [ node for node in nodes if node.typeID not in current ]
            hasNew = False
            i = 0
            for typeRow in valid:
                topLevelMarketGroupID = self.GetTopLevelMarketGroupID(typeRow)
                if topLevelMarketGroupID == -1:
                    eve.Message('CannotCompareNoneItem')
                    break
                invgroup = typeRow.Group()
                invgroup.categoryID
                if invgroup.categoryID not in compareCategories:
                    eve.Message('CannotCompareFromCategory', {'category': cfg.invcategories.Get(invgroup.categoryID).categoryName})
                    break
                if hasattr(self, 'topLevelMarketGroup') and self.topLevelMarketGroup != topLevelMarketGroupID:
                    self.CompareErrorMessage(topLevelMarketGroupID)
                    break
                else:
                    typeRow = self.GetPreparedTypeData(typeRow)
                    if typeRow not in self.typeIDs:
                        hasNew = True
                        self.typeIDs.append(typeRow)

            if hasNew:
                self.OnColumnChanged()

    def RemoveEntry(self, item):
        sel = self.sr.typescroll.GetSelected() or [item]
        rem = [ node.typeID for node in sel ]
        self.typeIDs = [ compareData for compareData in self.typeIDs if compareData.typeID not in rem ]
        if not self.typeIDs:
            self.attrDictChecked = []
            self.topLevelMarketGroup = None
        self.OnColumnChanged()

    def OnColumnChanged(self, force = 1, *args):
        self.GetCombinedDogmaAttributes()
        if force:
            self.GetAttributeScroll()
        self.GetTypeCompareScroll()

    def GetTopLevelMarketGroupID(self, data):
        marketGroupIDFromType = None
        if data.marketGroupID is None:
            typeID = sm.GetService('info').GetMetaParentTypeID(data.typeID)
            if typeID is not None:
                marketGroupIDFromType = cfg.invtypes.Get(sm.GetService('info').GetMetaParentTypeID(data.typeID)).marketGroupID
                topLevelMarketGroupID = self.GetTopLevelMarketGroupIDEx(marketGroupIDFromType)
            else:
                return -1
        else:
            topLevelMarketGroupID = self.GetTopLevelMarketGroupIDEx(data.marketGroupID)
        if not self.topLevelMarketGroup:
            if marketGroupIDFromType:
                self.topLevelMarketGroup = self.GetTopLevelMarketGroupIDEx(marketGroupIDFromType)
            else:
                self.topLevelMarketGroup = self.GetTopLevelMarketGroupIDEx(data.marketGroupID)
        return topLevelMarketGroupID

    def GetTopLevelMarketGroupIDEx(self, marketGroupID):
        mg = sm.GetService('marketutils').GetMarketGroup(marketGroupID)
        if mg:
            parentGroupID = mg.parentGroupID
            while parentGroupID:
                mg = sm.GetService('marketutils').GetMarketGroup(parentGroupID)
                parentGroupID = mg.parentGroupID

            return mg.marketGroupID
        else:
            return None

    def CompareErrorMessage(self, topLevelMarketGroupID):
        currentMarketGroup = sm.GetService('marketutils').GetMarketGroup(self.topLevelMarketGroup)
        tryfailMarketGroup = sm.GetService('marketutils').GetMarketGroup(topLevelMarketGroupID)
        eve.Message('CannotCompareFromItemToItem', {'currentMarketGroup': currentMarketGroup.marketGroupName,
         'tryfailMarketGroup': tryfailMarketGroup.marketGroupName})

    def GetCombinedDogmaAttributes(self):
        attrIDDict = []
        attrDict = []
        for typeRow in self.typeIDs:
            ad = sm.GetService('info').GetAttributeDictForType(typeRow.invtype.typeID)
            for attributeID, value in ad.iteritems():
                if attributeID not in self.banAttrs and attributeID not in attrIDDict:
                    attrIDDict.append(attributeID)
                    dgmAttribs = cfg.dgmattribs.Get(attributeID)
                    if dgmAttribs.published or dgmAttribs.attributeID == const.attributeHp:
                        attrDict.append(dgmAttribs)

        attributesToRemove = []
        for attribute in attrDict:
            removeIt = True
            for typeRow in self.typeIDs:
                taa, value = self.GetAttributeValue(attribute, typeRow.invtype.typeID)
                if taa:
                    removeIt = False
                    break

            if removeIt:
                attributesToRemove.append(attribute)

        self.attrDict = attrDict

    def GetAttributeScroll(self):
        scrolllist = self.GetAttributeContentList()
        self.sr.attributescroll.Load(contentList=scrolllist, noContentHint=localization.GetByLabel('UI/Compare/NothingToCompare'))

    def GetAttributeContentList(self):
        scrolllist = []
        if self.attrDict:
            self.attrDictIDs = []
            info = sm.GetService('godma').GetStateManager().GetShipType(const.typeApocalypse)
            tid = self.typeIDs[0]
            attrAndFittings = OrderedDict()
            attrAndFittings.update(sm.GetService('info').GetShipAndDroneAttributes())
            attrAndFittings.update(self.GetFittings())
            categoryID = cfg.invtypes.Get(tid.typeID).Group().Category().categoryID
            if categoryID in (const.categoryShip, const.categoryDrone):
                for caption, attrs in attrAndFittings.iteritems():
                    normalAttributes = attrs['normalAttributes']
                    groupedAttributes = [ x[1] for x in attrs.get('groupedAttributes', []) ]
                    allAttributes = normalAttributes + groupedAttributes
                    shipAttr = [ each for each in self.attrDict if each.attributeID in allAttributes ]
                    if shipAttr:
                        scrolllist.append(listentry.Get('Header', {'label': caption}))
                        for attr in shipAttr:
                            scrolllist.append(self.ScrollEntry(attr))
                            self.attrDictIDs.append(attr.attributeID)

                        if categoryID == const.categoryShip and caption == localization.GetByLabel('UI/Compare/Propulsion'):
                            entry = self.ScrollEntry(cfg.dgmattribs.Get(const.attributeBaseWarpSpeed))
                            scrolllist.append(entry)
                            self.attrDictIDs.append(const.attributeBaseWarpSpeed)

                if categoryID == const.categoryDrone:
                    otherAttributes = [ x for x in self.attrDict if x.attributeID not in self.attrDictIDs ]
                    if otherAttributes:
                        scrolllist.append(listentry.Get('Header', {'label': localization.GetByLabel('UI/InfoWindow/Miscellaneous')}))
                        for each in otherAttributes:
                            scrolllist.append(self.ScrollEntry(each))
                            self.attrDictIDs.append(each.attributeID)

            else:
                for each in self.attrDict:
                    scrolllist.append(self.ScrollEntry(each))
                    self.attrDictIDs.append(each.attributeID)

        return scrolllist

    def GetFittings(self):
        fittingDict = {localization.GetByLabel('UI/Fitting/FittingWindow/Fitting'): {'normalAttributes': [const.attributeCpuOutput,
                                                                                            const.attributePowerOutput,
                                                                                            const.attributeUpgradeCapacity,
                                                                                            const.attributeHiSlots,
                                                                                            const.attributeMedSlots,
                                                                                            const.attributeLowSlots,
                                                                                            const.attributeTurretSlotsLeft,
                                                                                            const.attributeUpgradeSlotsLeft,
                                                                                            const.attributeLauncherSlotsLeft]}}
        return fittingDict

    def ScrollEntry(self, entry):
        sentry = listentry.Get('AttributeCheckbox', {'line': 1,
         'info': entry,
         'label': entry.displayName,
         'iconID': entry.iconID,
         'item': entry,
         'text': FormatUnit(entry.unitID) or ' ',
         'hint': entry.displayName,
         'checked': False if entry.attributeID not in self.attrDictChecked else True,
         'cfgname': entry.attributeID,
         'retval': entry.attributeID,
         'OnChange': self.OnAttributeSelectedChanged})
        return sentry

    def OnAttributeSelectedChanged(self, checkbox):
        attributeID = checkbox.data['retval']
        if checkbox.GetValue():
            if len(self.attrDictChecked) < self.attributeLimit:
                if attributeID not in self.attrDictChecked:
                    self.attrDictChecked.append(attributeID)
                self.LogInfo(attributeID, 'CHECKED')
                self.OnColumnChanged(force=0)
            else:
                checkbox.SetValue(False)
                message = localization.GetByLabel('UI/Compare/CanOnlyCompareAmountAttributes', amount=self.attributeLimit)
                eve.Message('CustomInfo', {'info': message})
        else:
            if attributeID in self.attrDictChecked:
                self.attrDictChecked.remove(attributeID)
            self.LogInfo(attributeID, 'UNCHECKED')
            self.OnColumnChanged(force=0)

    def GetTypeCompareScroll(self):
        scrolllist, headers = self.GetCompareTypeInfoContentList()
        self.sr.typescroll.Load(contentList=scrolllist, headers=headers, noContentHint=localization.GetByLabel('UI/Compare/CompareToolHint'))

    def GetAttributeValue(self, attribute, typeID):
        ta = sm.GetService('info').GetAttributeDictForType(typeID)
        text = None
        value = None
        if attribute.attributeID in ta or attribute.attributeCategory == 9:
            text = ta.get(attribute.attributeID)
            value = self.dogmaLocation.GetAttributesForType(typeID).get(attribute.attributeID, None)
        return (text, value)

    def GetCompareTypeInfoContentList(self):
        scrolllist = []
        headers, uniqueHeaders, treatedHeaders, initialHeaders = ([],
         [],
         [],
         [])
        if self.typeIDs:
            headers = [localization.GetByLabel('/Carbon/UI/Common/TypeName'), localization.GetByLabel('UI/Compare/MetaGroup')]
            for typeRow in self.typeIDs:
                data = typeRow.copy()
                metaGroup = sm.GetService('info').GetMetaTypesFromTypeID(typeRow.invtype.typeID, groupOnly=1)
                text = '%s<t>%s' % (typeRow.invtype.typeName, metaGroup.metaGroupName)
                data.Set('sort_%s' % headers[0], typeRow.invtype.typeName)
                data.Set('sort_%s' % headers[1], metaGroup.metaGroupID)
                attributeLoop = {}
                for each in self.attrDict:
                    if each.attributeID in self.attrDictChecked:
                        attributeLoop[each.attributeID] = each

                for each in self.attrDictIDs:
                    attribute = attributeLoop.get(each, None)
                    if not attribute:
                        continue
                    displayName = uiutil.ReplaceStringWithTags(attribute.displayName)
                    value = None
                    if (displayName, attribute.attributeID) not in uniqueHeaders:
                        uniqueHeaders.append((displayName, attribute.attributeID))
                    if attribute.attributeID == const.attributeBaseWarpSpeed:
                        GTA = sm.GetService('godma').GetTypeAttribute
                        typeID = typeRow.invtype.typeID
                        cmp = max(GTA(typeID, const.attributeBaseWarpSpeed, defaultValue=1), 1.0)
                        cmp *= GTA(typeID, const.attributeWarpSpeedMultiplier, defaultValue=1)
                        cmp *= const.AU
                        value = cmp
                        taa = sm.GetService('info').GetBaseWarpSpeed(typeRow.invtype.typeID)
                    else:
                        taa, value = self.GetAttributeValue(attribute, typeRow.invtype.typeID)
                    if typeRow.invtype.Group().Category().categoryID == const.categoryCharge:
                        bsd, bad = sm.GetService('info').GetBaseDamageValue(typeRow.invtype.typeID)
                        if attribute.displayName == localization.GetByLabel('UI/Compare/BaseShieldDamage'):
                            value = bsd[0]
                        elif attribute.displayName == localization.GetByLabel('UI/Compare/BaseArmorDamage'):
                            value = bad[0]
                    if value is not None:
                        data.Set('sort_%s' % displayName, value)
                    else:
                        data.Set('sort_%s' % displayName, taa)
                    if taa is None:
                        taa = localization.GetByLabel('UI/Generic/NotAvailableShort')
                    else:
                        taa = GetFormatAndValue(attribute, taa)
                    text += '<t>%s' % taa

                data.label = text
                data.getIcon = 1
                data.GetMenu = self.GetEntryMenu
                data.viewMode = 'details'
                data.item = data.invtype
                data.ignoreRightClick = 1
                scrolllist.append(listentry.Get('Item', data=data))

            for header, attributeID in uniqueHeaders:
                if header in headers:
                    header = header + ' '
                headers.append(header)

            initialHeaders = headers
            treatedHeaders = []
            for each in initialHeaders:
                treatedHeaders.append(each.replace(' ', '<br>'))

        return (scrolllist, initialHeaders)

    def GetEntryMenu(self, item):
        m = sm.GetService('menu').GetMenuFormItemIDTypeID(None, item.typeID, ignoreMarketDetails=0)
        item.DoSelectNode()
        sel = self.sr.typescroll.GetSelected()
        text = localization.GetByLabel('UI/Commands/Remove')
        if len(sel) > 1:
            text = localization.GetByLabel('UI/Commands/RemoveMultiple', itemcount=len(sel))
        m += [(text, self.RemoveEntry, (item,))]
        return m

    def OnDropData(self, dragObj, nodes):
        for node in nodes:
            if node.__guid__ in self.allowedGuids:
                invType = self.GetInvType(node)
                if invType:
                    self.AddEntry([invType])

    def GetInvType(self, node):
        invType = node.get('invtype')
        if invType:
            return invType
        typeID = node.get('typeID')
        if typeID:
            return cfg.invtypes.Get(typeID)

    def GetPreparedTypeData(self, rec):
        attribs = {}
        for attribute in sm.GetService('godma').GetType(rec.typeID).displayAttributes:
            attribs[attribute.attributeID] = attribute.value

        data = util.KeyVal()
        data.godmaattribs = attribs
        data.invtype = cfg.invtypes.Get(rec.typeID)
        data.itemID = None
        data.typeID = rec.typeID
        return data


class AttributeCheckbox(listentry.LabelTextTop):
    __guid__ = 'listentry.AttributeCheckbox'

    def Startup(self, *args):
        listentry.LabelTextTop.Startup(self, args)
        cbox = uicontrols.Checkbox(align=uiconst.TOPLEFT, callback=self.CheckBoxChange, pos=(4, 4, 0, 0))
        cbox.data = {}
        self.children.insert(0, cbox)
        self.sr.checkbox = cbox
        self.sr.checkbox.state = uiconst.UI_DISABLED

    def Load(self, args):
        listentry.LabelTextTop.Load(self, args)
        data = self.sr.node
        self.sr.checkbox.SetGroup(data.group)
        self.sr.checkbox.SetChecked(data.checked, 0)
        self.sr.checkbox.data = {'key': data.cfgname,
         'retval': data.retval}
        self.sr.icon.left = 20
        self.sr.label.left = self.sr.icon.left + self.sr.icon.width + 2
        self.sr.text.left = self.sr.icon.left + self.sr.icon.width + 2

    def CheckBoxChange(self, *args):
        self.sr.node.checked = self.sr.checkbox.checked
        self.sr.node.OnChange(*args)

    def OnClick(self, *args):
        if self.sr.checkbox.checked:
            eve.Message('DiodeDeselect')
        else:
            eve.Message('DiodeClick')
        if self.sr.checkbox.groupName is None:
            self.sr.checkbox.SetChecked(not self.sr.checkbox.checked)
            return
        if self.sr.checkbox.diode is None:
            self.sr.checkbox.Prepare_Diode_()
        for node in self.sr.node.scroll.GetNodes():
            if node.Get('__guid__', None) == 'listentry.Checkbox' and node.Get('group', None) == self.sr.checkbox.groupName:
                if node.panel:
                    node.panel.sr.checkbox.SetChecked(0, 0)
                    node.checked = 0
                else:
                    node.checked = 0

        if not self.destroyed:
            self.sr.checkbox.SetChecked(1)

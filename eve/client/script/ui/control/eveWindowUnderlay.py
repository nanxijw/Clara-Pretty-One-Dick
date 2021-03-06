#Embedded file name: eve/client/script/ui/control\eveWindowUnderlay.py
from carbonui.primitives.container import Container
from carbonui.util.various_unsorted import GetWindowAbove
import carbonui.const as uiconst
from eve.client.script.ui.control.themeColored import SpriteThemeColored, FrameThemeColored, FillThemeColored, StretchSpriteVerticalThemeColored
import trinity
import telemetry

class WindowUnderlay(Container):
    default_name = 'underlay'
    default_state = uiconst.UI_PICKCHILDREN
    default_padLeft = 1
    default_padTop = 1
    default_padRight = 1
    default_padBottom = 1
    __notifyevents__ = ['OnCameraDragStart', 'OnCameraDragEnd']

    def ApplyAttributes(self, attributes):
        Container.ApplyAttributes(self, attributes)
        sm.RegisterNotify(self)
        self.isCameraDragging = False
        self.frame = FrameThemeColored(name='bgFrame', colorType=uiconst.COLORTYPE_UIHILIGHTGLOW, bgParent=self, texturePath='res:/UI/Texture/Shared/windowFrame.png', cornerSize=10, fillCenter=False, opacity=0.5)
        FrameThemeColored(bgParent=self, colorType=uiconst.COLORTYPE_UIHILIGHTGLOW, opacity=0.1)
        self.outerGlow = FrameThemeColored(name='outerGlow', bgParent=self, colorType=uiconst.COLORTYPE_UIHILIGHT, texturePath='res:/UI/Texture/Shared/boxGlow.png', cornerSize=5, offset=-2, opacity=0.0)
        self.blurredUnderlay = BlurredSceneUnderlay(bgParent=self, effectOpacity=0.5, saturation=0.5)

    def AnimEntry(self):
        self.blurredUnderlay.AnimEntry()
        uicore.animations.FadeTo(self.outerGlow, self.outerGlow.opacity, 0.25, duration=0.4, curveType=uiconst.ANIM_OVERSHOT2)
        uicore.animations.FadeTo(self.frame, self.frame.opacity, 1.0, duration=0.4, curveType=uiconst.ANIM_OVERSHOT3)

    def AnimExit(self):
        self.blurredUnderlay.AnimExit()
        uicore.animations.FadeTo(self.outerGlow, self.outerGlow.opacity, 0.0, duration=0.6)
        uicore.animations.FadeTo(self.frame, self.frame.opacity, 0.5, duration=0.6)

    def OnCameraDragStart(self):
        self.blurredUnderlay.isCameraDragging = True
        self.blurredUnderlay.UpdateState()

    def OnCameraDragEnd(self):
        self.blurredUnderlay.isCameraDragging = False
        self.blurredUnderlay.UpdateState()

    def Pin(self):
        self.blurredUnderlay.Pin()

    def UnPin(self):
        self.blurredUnderlay.UnPin()


class BlurredSceneUnderlay(SpriteThemeColored):
    default_name = 'BlurredSceneUnderlay'
    default_colorType = uiconst.COLORTYPE_UIBASE
    __notifyevents__ = ['OnBlurredBufferCreated', 'OnGraphicSettingsChanged', 'OnUIColorsChanged']
    default_effectOpacity = 0.5
    default_saturation = 0.5
    default_opacity = 0.98
    default_state = uiconst.UI_DISABLED
    default_spriteEffect = trinity.TR2_SFX_BLURBACKGROUNDCOLORED
    default_isPinned = False
    default_isInFocus = False

    @telemetry.ZONE_METHOD
    def ApplyAttributes(self, attributes):
        SpriteThemeColored.ApplyAttributes(self, attributes)
        sm.RegisterNotify(self)
        self.isInFocus = attributes.Get('isInFocus', self.default_isInFocus)
        self.isPinned = attributes.Get('isPinned', self.default_isPinned)
        self.isCameraDragging = False
        if uicore.uilib.blurredBackBufferAtlas:
            self.texture.atlasTexture = uicore.uilib.blurredBackBufferAtlas
        trinity.device.RegisterResource(self)
        self.UpdateState()

    def OnCreate(self, *args):
        """
        Device reset handler
        """
        pass

    def OnGraphicSettingsChanged(self, *args):
        self.UpdateState()

    def OnUIColorsChanged(self, *args):
        self.UpdateState()

    def OnBlurredBufferCreated(self, *args):
        if not self.destroyed:
            self.texture.atlasTexture = uicore.uilib.blurredBackBufferAtlas

    def AnimateEffectTo(self, value):
        uicore.animations.MorphScalar(self, 'effectOpacity', self.effectOpacity, value, curveType=uiconst.ANIM_LINEAR, duration=0.3)

    def AnimateBrightnessTo(self, value):
        uicore.animations.MorphScalar(self, 'saturation', self.saturation, value, curveType=uiconst.ANIM_LINEAR, duration=0.3)

    def AnimEntry(self):
        self.isInFocus = True
        self.UpdateState()

    def AnimExit(self):
        self.isInFocus = False
        self.UpdateState()

    def GetTransparencySetting(self):
        return settings.user.ui.Get('windowTransparency', 1.0)

    def UpdateStateBlurEnabled(self):
        self.SetFixedColor(None)
        self.opacity = self.default_opacity
        if self.isPinned:
            self.spriteEffect = trinity.TR2_SFX_BLURBACKGROUND
        else:
            self.spriteEffect = trinity.TR2_SFX_BLURBACKGROUNDCOLORED
        if self.isInFocus:
            effectOpacity = 1.2
        elif self.isPinned:
            effectOpacity = 1.0
        else:
            effectOpacity = 0.75
        if self.isPinned:
            if self.isInFocus:
                brightness = 0.6
            elif self.isCameraDragging:
                brightness = 1.0
            else:
                brightness = 0.95
            brightness *= self.GetTransparencySetting()
            brightness = max(brightness, 0.5)
        else:
            if self.isInFocus:
                brightness = 0.5
            elif self.isCameraDragging:
                brightness = 0.7
            else:
                brightness = 0.6
            brightness *= self.GetTransparencySetting()
        self.AnimateEffectTo(effectOpacity)
        self.AnimateBrightnessTo(brightness)

    def UpdateStateBlurDisabled(self):
        if self.isPinned:
            self.opacity = 0.5 - 0.3 * self.GetTransparencySetting()
        else:
            self.SetFixedColor(None)
            self.opacity = 0.5 * (2.0 - self.GetTransparencySetting())
        self.spriteEffect = trinity.TR2_SFX_FILL

    @telemetry.ZONE_METHOD
    def UpdateState(self):
        if settings.char.windows.Get('enableWindowBlur', True):
            self.UpdateStateBlurEnabled()
        else:
            self.UpdateStateBlurDisabled()

    def Pin(self):
        self.isPinned = True
        self.UpdateState()

    def UnPin(self):
        self.isPinned = False
        self.UpdateState()


class BumpedUnderlay(Container):
    """ A bumped underlay Frame used by various UI controls. Color is affected by "base color" setting """
    __guid__ = 'uicontrols.BumpedUnderlay'
    __notifyevents__ = ['OnCameraDragStart',
     'OnCameraDragEnd',
     'OnWindowSetActive',
     'OnWindowSetInctive']
    default_isInFocus = False
    default_showFill = False

    def ApplyAttributes(self, attributes):
        Container.ApplyAttributes(self, attributes)
        sm.RegisterNotify(self)
        self.isInFocus = attributes.Get('isInFocus', self.default_isInFocus)
        showFill = attributes.get('showFill', self.default_showFill)
        self.isWindowActive = True
        self.isCameraDragging = False
        self.edgeGlow = StretchSpriteVerticalThemeColored(name='edgeGlow', bgParent=self, texturePath='res:/UI/Texture/shared/buttonEdgeGlowFrameBottom.png', colorType=uiconst.COLORTYPE_UIHILIGHTGLOW, blendMode=trinity.TR2_SBM_ADD, opacity=0.1, topEdgeSize=2, bottomEdgeSize=2)
        self.frame = FrameThemeColored(bgParent=self, colorType=uiconst.COLORTYPE_UIHILIGHTGLOW, texturePath='res:/UI/Texture/Shared/underlayBumped.png', cornerSize=6)
        if showFill:
            FillThemeColored(name='hoverFill', bgParent=self, colorType=uiconst.COLORTYPE_UIHILIGHT, opacity=0.2)
        self.fillUnderlay = FillThemeColored(bgParent=self, colorType=uiconst.COLORTYPE_UIBASECONTRAST)
        self.UpdateIsActive()
        self.UpdateState(animate=False)

    def OnCameraDragStart(self):
        self.isCameraDragging = True
        self.UpdateState()

    def OnCameraDragEnd(self):
        self.isCameraDragging = False
        self.UpdateState()

    def AnimEntry(self):
        self.isInFocus = True
        self.UpdateState()

    def AnimExit(self):
        self.isInFocus = False
        self.UpdateState()

    def UpdateIsActive(self):
        activeWnd = uicore.registry.GetActive()
        if activeWnd and activeWnd == GetWindowAbove(self):
            self.isWindowActive = True
        else:
            self.isWindowActive = False

    def OnWindowSetActive(self, wnd):
        self.UpdateIsActive()
        self.UpdateState()

    def OnWindowSetInctive(self, wnd):
        self.UpdateIsActive()
        self.UpdateState()

    def UpdateState(self, animate = True):
        if self.isCameraDragging:
            opacity = 0.0
        elif self.isWindowActive:
            if self.isInFocus:
                opacity = 0.7
            else:
                opacity = 0.5
        else:
            opacity = 0.2
        if self.isInFocus:
            frameOpacity = 0.5
        else:
            frameOpacity = 1.0
        if self.isInFocus:
            edgeOpacity = 0.35
        else:
            edgeOpacity = 0.1
        if animate:
            uicore.animations.FadeTo(self.fillUnderlay, self.fillUnderlay.opacity, opacity, duration=0.3)
            uicore.animations.FadeTo(self.frame, self.frame.opacity, frameOpacity, duration=0.1)
            uicore.animations.FadeTo(self.edgeGlow, self.edgeGlow.opacity, edgeOpacity, duration=0.6)
        else:
            self.fillUnderlay.opacity = opacity
            self.frame.opacity = frameOpacity
            self.edgeGlow.opacity = edgeOpacity


class RaisedUnderlay(Container):
    """ A raised underlay Frame used by various UI controls. Color is affected by "Background color" setting """
    __guid__ = 'uicontrols.RaisedUnderlay'
    default_fixedColor = None
    default_isGlowEdgeRotated = False
    default_clipChildren = True
    default_hideFrame = False
    OPACITY_DISABLED = 0.2
    OPACITY_IDLE = 0.4
    OPACITY_HOVER = 0.7
    OPACITY_SELECTED = 1.0
    OPACITY_MOUSEDOWN = 1.1

    def ApplyAttributes(self, attributes):
        Container.ApplyAttributes(self, attributes)
        self.fixedColor = attributes.Get('color', self.default_fixedColor)
        self.isGlowEdgeRotated = attributes.Get('isGlowEdgeRotated', self.default_isGlowEdgeRotated)
        hideFrame = attributes.get('hideFrame', self.default_hideFrame)
        self.isSelected = False
        self.isDisabled = False
        self.ConstructLayout()
        if hideFrame:
            self.frame.Hide()

    def ConstructLayout(self):
        self.frame = FrameThemeColored(name='frame', bgParent=self, colorType=uiconst.COLORTYPE_UIHILIGHT, color=self.fixedColor, blendMode=trinity.TR2_SBM_ADD, texturePath='res:/UI/Texture/Classes/Button/frame.png', opacity=0.2)
        self.innerGlow = FrameThemeColored(name='innerGlow', bgParent=self, cornerSize=10, texturePath='res:/UI/Texture/Classes/Button/innerGlow.png', colorType=uiconst.COLORTYPE_UIHILIGHT, color=self.fixedColor, opacity=0.2)
        self.hoverFill = FillThemeColored(name='hoverFill', bgParent=self, colorType=uiconst.COLORTYPE_UIHILIGHT, opacity=self.OPACITY_IDLE, color=self.fixedColor)
        FillThemeColored(name='backgroundColorFill', bgParent=self, opacity=0.45)

    def SetFixedColor(self, fixedColor):
        self.fixedColor = fixedColor
        self.innerGlow.SetFixedColor(fixedColor)
        self.hoverFill.SetFixedColor(fixedColor)

    def OnMouseEnter(self, *args):
        self.ShowHilite()

    def OnMouseExit(self, *args):
        self.HideHilite()

    def GetColor(self):
        return self.fixedColor or sm.GetService('uiColor').GetUIColor(uiconst.COLORTYPE_UIHILIGHT)

    def ShowHilite(self, animate = True):
        if self.isSelected or self.isDisabled:
            return
        color = self.GetColor()
        if animate:
            uicore.animations.FadeTo(self.hoverFill, self.hoverFill.opacity, self.OPACITY_HOVER, duration=uiconst.TIME_ENTRY)
            uicore.animations.SpColorMorphTo(self.frame, self.frame.GetRGBA(), color, includeAlpha=False, duration=uiconst.TIME_ENTRY)
        else:
            self.hoverFill.opacity = OPACITY_HOVER
            color = color[:3] + (self.frame.opacity,)
            self.frame.SetRGB(*color)

    def HideHilite(self, animate = True):
        if self.isSelected or self.isDisabled:
            return
        color = self.GetColor()
        if animate:
            uicore.animations.FadeTo(self.hoverFill, self.hoverFill.opacity, self.OPACITY_IDLE, duration=uiconst.TIME_EXIT)
            uicore.animations.SpColorMorphTo(self.frame, self.frame.GetRGBA(), color, includeAlpha=False, duration=uiconst.TIME_ENTRY)
        else:
            self.hoverFill.opacity = OPACITY_IDLE
            color = color[:3] + (self.frame.opacity,)
            self.frame.SetRGB(*color)

    def OnMouseDown(self, *args):
        if self.isSelected or self.isDisabled:
            return
        uicore.animations.FadeTo(self.hoverFill, self.hoverFill.opacity, self.OPACITY_MOUSEDOWN, duration=0.1)

    def OnMouseUp(self, *args):
        if self.isSelected or self.isDisabled:
            return
        uicore.animations.FadeTo(self.hoverFill, self.hoverFill.opacity, self.OPACITY_HOVER, duration=0.3)

    def Blink(self, loops = 1):
        uicore.animations.FadeTo(self.hoverFill, self.OPACITY_MOUSEDOWN, self.OPACITY_IDLE, curveType=uiconst.ANIM_WAVE, duration=0.6, loops=loops)

    def StopBlink(self):
        uicore.animations.FadeTo(self.hoverFill, self.hoverFill.opacity, self.OPACITY_IDLE, duration=0.3)

    def Select(self, animate = True):
        if self.isSelected:
            return
        self.innerGlow.StopAnimations()
        if self.fixedColor:
            self.innerGlow.SetFixedColor(self.fixedColor)
        else:
            self.innerGlow.SetColorType(uiconst.COLORTYPE_UIHILIGHT)
        if animate:
            uicore.animations.FadeTo(self.hoverFill, self.hoverFill.opacity, self.OPACITY_SELECTED, duration=0.15)
        else:
            self.hoverFill.opacity = self.OPACITY_SELECTED
        self.isSelected = True

    def Deselect(self, animate = True):
        if not self.isSelected:
            return
        self.isSelected = False
        self.HideHilite(animate=animate)

    def SetDisabled(self):
        self.isDisabled = True
        self.hoverFill.opacity = self.OPACITY_DISABLED

    def SetEnabled(self):
        self.isDisabled = False
        self.hoverFill.opacity = self.OPACITY_IDLE


class CheckboxUnderlay(RaisedUnderlay):
    OPACITY_IDLE = 0.15
    OPACITY_HOVER = 0.4
    OPACITY_SELECTED = 0.8


class RadioButtonUnderlay(RaisedUnderlay):
    OPACITY_IDLE = 0.15
    OPACITY_HOVER = 0.4
    OPACITY_SELECTED = 1.0

    def ConstructLayout(self):
        self.frame = FrameThemeColored(name='frame', bgParent=self, colorType=uiconst.COLORTYPE_UIHILIGHT, color=self.fixedColor, blendMode=trinity.TR2_SBM_ADD, texturePath='res:/UI/Texture/Classes/RadioButton/frame.png', opacity=self.OPACITY_IDLE)
        self.innerGlow = FrameThemeColored(name='innerGlow', bgParent=self, cornerSize=10, texturePath='res:/UI/Texture/Classes/RadioButton/innerGlow.png', colorType=uiconst.COLORTYPE_UIHILIGHT, color=self.fixedColor, opacity=self.OPACITY_IDLE)
        self.hoverFill = SpriteThemeColored(name='hoverFill', bgParent=self, texturePath='res:/UI/Texture/Classes/RadioButton/frame.png', colorType=uiconst.COLORTYPE_UIHILIGHT, opacity=self.OPACITY_IDLE, color=self.fixedColor)
        SpriteThemeColored(name='backgroundColorFill', bgParent=self, texturePath='res:/UI/Texture/Classes/RadioButton/innerGlow.png', colorType=uiconst.COLORTYPE_UIBASE, opacity=0.45)


class TabUnderlay(Container):
    """ Underlay used for tab group buttons. Color is affected by "Background color" setting """
    default_fixedColor = None
    default_isSelected = False
    default_clipChildren = True
    OPACITY_IDLE = 0.0
    OPACITY_HOVER = 2.0
    OPACITY_MOUSEDOWN = 3.0
    OPACITY_BLINK = 6.0
    OPACITY_SELECTED = 2.0

    def ApplyAttributes(self, attributes):
        Container.ApplyAttributes(self, attributes)
        self.fixedColor = attributes.Get('color', self.default_fixedColor)
        self.isSelected = attributes.get('isSelected', self.default_isSelected)
        self.bgCont = Container(name='bgCont', bgParent=self, opacity=self.OPACITY_IDLE, state=uiconst.UI_DISABLED, idx=0)
        StretchSpriteVerticalThemeColored(name='edgeGlow', bgParent=self.bgCont, texturePath='res:/UI/Texture/shared/buttonEdgeGlowFrameBottom.png', colorType=uiconst.COLORTYPE_UIHILIGHT, blendMode=trinity.TR2_SBM_ADD, opacity=0.5, color=self.fixedColor, topEdgeSize=1, bottomEdgeSize=1)
        SpriteThemeColored(name='buttonGlow', bgParent=self.bgCont, texturePath='res:/UI/Texture/shared/buttonGlow.png', colorType=uiconst.COLORTYPE_UIHILIGHT, padding=-14, opacity=0.15, color=self.fixedColor)
        colorType = uiconst.COLORTYPE_UIBASECONTRAST if self.isSelected else uiconst.COLORTYPE_UIBASE
        self.underlay = FillThemeColored(bgParent=self, name='tabBackground', colorType=colorType, opacity=0.7)

    def SetFixedColor(self, fixedColor):
        self.fixedColor = fixedColor
        self.frame.SetFixedColor(fixedColor)

    def GetHoverColor(self):
        if self.fixedColor:
            return self.fixedColor
        return sm.GetService('uiColor').GetUIColor(uiconst.COLORTYPE_UIBASECONTRAST)

    def OnMouseEnter(self, *args):
        if self.isSelected:
            return
        color = self.GetHoverColor()
        self.underlay.colorType = uiconst.COLORTYPE_UIBASECONTRAST
        uicore.animations.SpColorMorphTo(self.underlay, endColor=color, duration=0.15, includeAlpha=False)
        uicore.animations.FadeTo(self.bgCont, self.bgCont.opacity, self.OPACITY_HOVER, duration=0.15)

    def OnMouseExit(self, *args):
        if self.isSelected:
            uicore.animations.FadeTo(self.bgCont, self.bgCont.opacity, self.OPACITY_SELECTED, duration=0.5)
        else:
            uicore.animations.FadeTo(self.bgCont, self.bgCont.opacity, self.OPACITY_IDLE, duration=0.5)
            color = sm.GetService('uiColor').GetUIColor(uiconst.COLORTYPE_UIBASE)
            self.underlay.colorType = uiconst.COLORTYPE_UIBASE
            self.underlay.fixedColor = None
            uicore.animations.SpColorMorphTo(self.underlay, endColor=color, duration=0.5, includeAlpha=False)

    def OnMouseDown(self, *args):
        if not self.isSelected:
            uicore.animations.FadeTo(self.bgCont, self.bgCont.opacity, self.OPACITY_MOUSEDOWN, duration=0.1)
        else:
            uicore.animations.FadeTo(self.bgCont, self.bgCont.opacity, self.OPACITY_SELECTED, duration=0.1)

    def OnMouseUp(self, *args):
        uicore.animations.FadeTo(self.bgCont, self.bgCont.opacity, self.OPACITY_HOVER, duration=0.3)

    def Blink(self, loops = 1):
        uicore.animations.FadeTo(self.bgCont, self.OPACITY_BLINK, self.OPACITY_IDLE, curveType=uiconst.ANIM_WAVE, duration=0.8, loops=loops)

    def StopBlink(self):
        uicore.animations.FadeTo(self.bgCont, self.bgCont.opacity, self.OPACITY_IDLE, duration=0.3)

    def Select(self):
        if self.isSelected:
            return
        self.underlay.StopAnimations()
        if self.fixedColor:
            self.underlay.SetFixedColor(self.fixedColor)
        else:
            self.underlay.SetColorType(uiconst.COLORTYPE_UIBASECONTRAST)
        uicore.animations.FadeTo(self.bgCont, self.bgCont.opacity, self.OPACITY_SELECTED, duration=0.15)
        self.underlay.opacity = 0.7
        self.isSelected = True

    def Deselect(self):
        if not self.isSelected:
            return
        self.underlay.opacity = 0.4
        self.isSelected = False
        self.OnMouseExit()


class EntryUnderlay(FrameThemeColored):
    default_align = uiconst.TOALL
    default_colorType = uiconst.COLORTYPE_UIHILIGHT
    default_opacity = 0.0
    default_texturePath = 'res:/UI/Texture/Shared/underlayRaised.png'
    default_padLeft = default_padTop = default_padRight = default_padBottom = -2
    OPACITY_IDLE = 0.0
    OPACITY_HOVER = 1.0
    OPACITY_MOUSEDOWN = 1.5
    OPACITY_SELECTED = 1.0
    isSelected = False

    def OnMouseEnter(self, *args):
        uicore.animations.FadeTo(self, self.opacity, self.OPACITY_HOVER, duration=0.3)

    def OnMouseExit(self, *args):
        if self.isSelected:
            uicore.animations.FadeTo(self, self.opacity, self.OPACITY_SELECTED, duration=0.3)
        else:
            uicore.animations.FadeTo(self, self.opacity, self.OPACITY_IDLE, duration=0.3)

    def OnMouseDown(self, *args):
        uicore.animations.FadeTo(self, self.opacity, self.OPACITY_MOUSEDOWN, duration=0.3)

    def OnMouseUp(self, *args):
        uicore.animations.FadeTo(self, self.opacity, self.OPACITY_HOVER, duration=0.3)

    def Select(self):
        self.isSelected = True
        uicore.animations.FadeTo(self, self.opacity, self.OPACITY_SELECTED, duration=0.3)

    def Deselect(self):
        self.isSelected = False
        uicore.animations.FadeTo(self, self.opacity, self.OPACITY_IDLE, duration=0.3)


class MenuUnderlay(Container):
    default_name = 'MenuUnderlay'

    def ApplyAttributes(self, attributes):
        Container.ApplyAttributes(self, attributes)
        FrameThemeColored(bgParent=self, colorType=uiconst.COLORTYPE_UIHILIGHT, opacity=0.35)
        FillThemeColored(bgParent=self, opacity=0.93)


OPACITY_IDLE = 0.0
OPACITY_HOVER = 0.25
OPACITY_MOUSEDOWN = 0.35
OPACITY_SELECTED = 0.5

class ListEntryUnderlay(FillThemeColored):
    default_name = 'ListEntryUnderlay'
    default_colorType = uiconst.COLORTYPE_UIHILIGHT
    default_opacity = OPACITY_IDLE
    default_padBottom = 1

    def ShowHilite(self, animate = True):
        if animate:
            uicore.animations.FadeTo(self, self.opacity, OPACITY_HOVER, duration=uiconst.TIME_ENTRY)
        else:
            self.opacity = OPACITY_HOVER

    def HideHilite(self, animate = True):
        if animate:
            uicore.animations.FadeTo(self, self.opacity, OPACITY_IDLE, duration=uiconst.TIME_EXIT)
        else:
            self.opacity = OPACITY_IDLE

    def Select(self, animate = True):
        if animate:
            uicore.animations.FadeTo(self, self.opacity, OPACITY_SELECTED, duration=0.4, curveType=uiconst.ANIM_OVERSHOT5)
        else:
            self.opacity = OPACITY_SELECTED

    def Deselect(self, animate = True):
        if animate:
            uicore.animations.FadeTo(self, max(0.1, self.opacity), OPACITY_IDLE, duration=0.6)
        else:
            self.opacity = OPACITY_IDLE

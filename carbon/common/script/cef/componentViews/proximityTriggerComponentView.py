#Embedded file name: carbon/common/script/cef/componentViews\proximityTriggerComponentView.py
from carbon.common.script.cef.baseComponentView import BaseComponentView

class ProximityTriggerComponentView(BaseComponentView):
    __guid__ = 'cef.ProximityTriggerComponentView'
    __COMPONENT_ID__ = const.cef.PROXIMITY_TRIGGER_COMPONENT_ID
    __COMPONENT_DISPLAY_NAME__ = 'Proximity Trigger'
    __COMPONENT_CODE_NAME__ = 'proximityTrigger'
    RADIUS = 'radius'
    DIMENSIONS = 'dimensions'

    @classmethod
    def SetupInputs(cls):
        cls.RegisterComponent(cls)
        cls._AddInput(cls.RADIUS, 0.0, cls.RECIPE, const.cef.COMPONENTDATA_FLOAT_TYPE, displayName='Radius')
        cls._AddInput(cls.DIMENSIONS, None, cls.RUNTIME, const.cef.COMPONENTDATA_NON_PRIMITIVE_TYPE, displayName='Dimensions')


ProximityTriggerComponentView.SetupInputs()

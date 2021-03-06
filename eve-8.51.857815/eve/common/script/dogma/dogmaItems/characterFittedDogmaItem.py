#Embedded file name: eve/common/script/dogma/dogmaItems\characterFittedDogmaItem.py
from eve.common.script.dogma.dogmaItems.fittableDogmaItem import FittableDogmaItem
import util
import weakref

class CharacterFittedDogmaItem(FittableDogmaItem):
    __guid__ = 'dogmax.CharacterFittedDogmaItem'

    def GetShipID(self):
        if self.location is None:
            self.dogmaLocation.LogWarn('CharacterFittedDogmaItem::GetShipID - item not fitted to location', self.itemID)
            return
        return self.location.GetShipID()

    def SetLocation(self, locationID, locationDogmaItem, flagID):
        self.flagID = flagID
        if locationDogmaItem is None:
            self.dogmaLocation.LogError('CharacterFittedDogmaItem::SetLocation, locationDogmaItem is None')
            return
        oldData = self.GetLocationInfo()
        self.location = weakref.proxy(locationDogmaItem)
        self.ownerID = self.location.itemID
        locationDogmaItem.RegisterFittedItem(self, flagID)
        return oldData

    def UnsetLocation(self, locationDogmaItem):
        locationDogmaItem.UnregisterFittedItem(self)
        self.ownerID = self.location = None

    def GetEnvironmentInfo(self):
        return util.KeyVal(itemID=self.itemID, shipID=self.GetShipID(), charID=self.GetPilot(), otherID=None, targetID=None, effectID=None)

    def GetPilot(self):
        return self.locationID

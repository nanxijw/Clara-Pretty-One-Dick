#Embedded file name: eve/common/script/dogma/dogmaItems\structureDogmaItem.py
from eve.common.script.dogma.dogmaItems.locationDogmaItem import LocationDogmaItem
import util

class StructureDogmaItem(LocationDogmaItem):
    __guid__ = 'dogmax.StructureDogmaItem'

    def GetEnvironmentInfo(self):
        otherID = self.subLocations.get(const.flagHiSlot0, None)
        if otherID is None:
            other = self.dogmaLocation.GetChargeNonDB(self.itemID, const.flagHiSlot0)
            if other is not None:
                otherID = other.itemID
        return util.KeyVal(itemID=self.itemID, shipID=self.locationID, charID=None, otherID=otherID, targetID=None, effectID=None)

    def CanFitItem(self, dogmaItem, flagID):
        if dogmaItem.itemID == self.itemID:
            return True
        if flagID == const.flagHiSlot0:
            return True
        return False

    def IsOnline(self):
        return const.effectOnlineForStructures in self.activeEffects

    def IsActive(self):
        for effectID in self.activeEffects:
            if effectID == const.effectOnlineForStructures:
                continue
            effect = self.dogmaLocation.GetEffect(effectID)
            if effect.effectCategory in (const.dgmEffActivation, const.dgmEffTarget):
                return True

        return False

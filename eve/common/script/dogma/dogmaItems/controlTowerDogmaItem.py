#Embedded file name: eve/common/script/dogma/dogmaItems\controlTowerDogmaItem.py
from eve.common.script.dogma.dogmaItems.locationDogmaItem import LocationDogmaItem
import util

class ControlTowerDogmaItem(LocationDogmaItem):
    __guid__ = 'dogmax.ControlTowerDogmaItem'

    def OnItemLoaded(self):
        self.dogmaLocation.FitItemToLocation(self.itemID, self.itemID, 0)
        super(ControlTowerDogmaItem, self).OnItemLoaded()

    def CanFitItem(self, dogmaItem, flagID):
        if dogmaItem.itemID == self.itemID:
            return True
        if dogmaItem.categoryID == const.categoryStructure and dogmaItem.groupID != const.groupControlTower:
            return True
        return False

    def GetEnvironmentInfo(self):
        return util.KeyVal(itemID=self.itemID, shipID=self.itemID, charID=None, otherID=None, targetID=None, effectID=None)

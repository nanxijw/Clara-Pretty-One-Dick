#Embedded file name: carbon/common/script/entities\ActionObject.py
import service
import geo2
import GameWorld
import cef
from carbon.common.script.zaction.zactionCommon import ProcPropertyTypeDef, ProcTypeDef

class ActionObjectSvc(service.Service):
    __guid__ = 'svc.actionObjectSvc'
    __machoresolve__ = 'location'
    __componentTypes__ = ['actionObject']
    __notifyevents__ = ['OnEntityDeleted']

    def __init__(self):
        self.manager = GameWorld.ActionObjectManager()
        self.manager.loadActionObjectDataFunc = self._LoadActionObjectData
        self.manager.loadActionStationGlobalDataFunc = self._LoadActionStationGlobalData
        self.preservedStates = {}
        service.Service.__init__(self)

    def Run(self, *args):
        service.Service.Run(self, *args)

    def CreateComponent(self, name, state):
        actionObjectID = state.get(cef.ActionObjectComponentView.ACTIONOBJECT_ID, None)
        if actionObjectID is None or actionObjectID == 0:
            recipeID = state.get('_recipeID', '<UNKNOWN>')
            spawnID = state.get('_spawnID', '<UNKNOWN>')
            self.LogError('ActionObject component ignored for recipeID=%s/spawnID=%s: no actionObjectID was set for it' % (recipeID, spawnID))
            return
        actionObj = GameWorld.ActionObject()
        self.preservedStates[actionObj] = state
        return actionObj

    def PrepareComponent(self, sceneID, entityID, component):
        """
            Gets called in order to prepare a component. No other components can be referred to
        """
        actionObjID = self.preservedStates[component].get('actionObjectUID', None)
        if actionObjID is None:
            self.LogError('Missing ActionObject ID for entity ', entityID, ', expect missing assets!')
            del self.preservedStates[component]
        elif self.InitActionObject(component, int(actionObjID), entityID) is None:
            self.LogError('Error initializing ActionObject for entity ', entityID, ', expect missing assets!')
            del self.preservedStates[component]

    def SetupComponent(self, entity, component):
        """
            Gets called in order to setup a component. All other components can be referred to
        """
        if component in self.preservedStates:
            actionStationOccupants = self.preservedStates[component].get('actionStationOccupants', None)
            if actionStationOccupants:
                for key, val in actionStationOccupants.iteritems():
                    self.manager.SetActionStationInUse(component, component.actionStations[key], val)

            del self.preservedStates[component]

    def RegisterComponent(self, entity, component):
        """
            Gets called in order to register a component. The component can be searched for prior to this point.
        """
        pass

    def PackUpForSceneTransfer(self, component, destinationSceneID):
        return None

    def PackUpForClientTransfer(self, component):
        state = {}
        state['actionObjectUID'] = int(component.actionObjectData.UID)
        occupantDict = {}
        for index, value in enumerate(component.actionStations):
            occupantDict[index] = value.occupant

        state['actionStationOccupants'] = occupantDict
        return state

    def ReportState(self, component, entity):
        state = self.PackUpForClientTransfer(component)
        return state

    def UnRegisterComponent(self, entity, component):
        self.manager.RemoveActionObject(component)

    def OnEntityDeleted(self, entityID, sceneID):
        self.manager.StopUsingActionObject(entityID)

    def InitActionObject(self, actionObject, actionObjectUID, entID):
        """
            Creates an ActionObject based on the data referred to by the UID.
            
            In:     actionObjectUID - The UID of the action object data to use.
            Return: ao - The ActionObject we've created. None if failure occurs.
        """
        aoData = self.manager.GetActionObjectData(actionObjectUID)
        if aoData is None:
            self.LogError('Could not look up ActionObjectData for ActionObject with UID %d.' % actionObjectUID)
            return
        actionObject.Init(aoData, entID)
        self.manager.AddActionObject(actionObject)
        return actionObject

    def _LoadActionObjectData(self, actionObjectUID):
        """
            Loads ActionObject object-level data with the given UID.
            
            In:     actionObjectUID - The UID of the action object to load
            Out:    aoData - Appended to self.actionObjectDatas
            Return: aoData - The action object data just loaded and stored 
        """
        aoDbData = self.GetActionObjectRecord(actionObjectUID)
        if aoDbData is None:
            self.LogError('Error getting ActionObject record with UID %d.' % actionObjectUID)
            return
        aoData = GameWorld.ActionObjectData(actionObjectUID, str(aoDbData['Name']))
        if self._LoadExitPoints(aoData) is False:
            self.LogError('Error loading exit points for ActionObject data with UID %d.' % actionObjectUID)
            return
        if self._LoadActionStationLocalData(aoData) is False:
            self.LogError('Error loading action stations for ActionObject data with UID %d.' % actionObjectUID)
            return
        self.manager.AddActionObjectData(aoData)
        return aoData

    def _LoadExitPointsToList(self, rows, destList):
        """
            Loads the exit points in the specified rows and stores them in the specified list.
            
            In:     rows - The DB rows we're loading from
                    destList - The list we're storing to
            Out:    destList - All exit points are stored here
            Return: True if successful, False otherwise
        """
        if rows is None:
            return True
        for row in rows:
            exitPoint = GameWorld.ActionExitPoint(row['pos'], row['rot'])
            destList.append(exitPoint)

        return True

    def _LoadExitPoints(self, aoData):
        """
            Loads the global exit points for the specified ActionObject.
            
            In:     aoData - The ActionObjectData we're loading to
            Out:    aoData.exitPoints - Stores the exit points in the AO
            Return: True if successful, False otherwise
        """
        globalExitRows = self.GetActionObjectExits(aoData.UID, 0)
        return self._LoadExitPointsToList(globalExitRows, aoData.exitPoints)

    def _LoadActionStationLocalData(self, aoData):
        """
            Loads the ActionStations for this ActionObject.
            
            In:     aoData - The ActionObjectData we're loading to
            Out:    aoData.actionStationDatas - Stores the ActionStations in the AO
            Return: True if successful, False otherwise
        """
        asMappingRows = self.GetActionObjectStations(aoData.UID)
        for asMapping in asMappingRows:
            asGlobalData = self.manager.GetActionStationGlobalData(asMapping['StationID'])
            asLocalData = GameWorld.ActionStationLocalData(asGlobalData, asMapping['pos'], asMapping['rot'])
            if self._LoadActionStationExitPoints(asLocalData, aoData.UID, asMapping['InstID']) is False:
                self.LogError('Error loading exit points on action station with ID %d for ActionObject data with UID %d.' % (asMapping['StationID'], aoData.UID))
                return False
            aoData.actionStationLocalDatas.append(asLocalData)

        return True

    def _LoadActionStationExitPoints(self, asLocalData, aoUID, asInstanceID):
        """
            Loads the ActionStation's exit points for the specified ActionStation.
            
            In:     asLocalData - The "local data" for this ActionStation.
                    aoUID - The UID of the ActionObject that this ActionStation belongs to.
                    index - The index of this ActionStation within the ActionObject.
            Out:    The exit points are written to the list within the asLocalData structure.
            Return: True if successful, False otherwise.
        """
        asExitPointRows = self.GetActionObjectExits(aoUID, asInstanceID)
        return self._LoadExitPointsToList(asExitPointRows, asLocalData.exitPoints)

    def _LoadActionStationGlobalData(self, asUID):
        """
            Load the ActionStation "global data" for the specified UID.
            
            In:     asUID - The UID of the ActionStation we're loading.
            Out:    Stores the loaded ActionStation "global data" to the internal list.
            Return: The global data just loaded.
        """
        asDbData = self.GetActionStationRecord(asUID)
        if asDbData is None:
            return
        asGlobalData = GameWorld.ActionStationGlobalData(asUID)
        if self._LoadActionEntries(asGlobalData) is False:
            return
        self.manager.AddActionStationGlobalData(asGlobalData)
        return asGlobalData

    def _LoadActionEntries(self, asGlobalData):
        """
            Load the ActionEntried for the ActionStation specified.
            
            In:     asGlobalData - The "global data" for the ActionStation we're loading.
            Out:    The ActionEntry list within the ActionStation global data.
            Return: True if successful, False otherwise.
        """
        actionMappingRows = self.GetActionStationActions(asGlobalData.UID)
        for action in actionMappingRows:
            tagList = ''
            entry = None
            for potentialMatch in asGlobalData.actionEntries:
                if potentialMatch.MatchEntTags(tagList):
                    entry = potentialMatch
                    break

            if entry is None:
                entry = GameWorld.ActionEntry(tagList)
                asGlobalData.actionEntries.append(entry)
            entry.AddAction(action)

        return True

    def _PrepareActionObject(self, ent, staticObject, position, rotation):
        pass

    def GetActionObjectRecord(self, actionObjectID):
        if actionObjectID is not None:
            aoRow = cfg.actionObjects.Get(actionObjectID)
            if aoRow is not None:
                return {'ID': aoRow.actionObjectID,
                 'Name': aoRow.actionObjectName}

    def GetActionStationRecord(self, actionStationTypeID):
        if actionStationTypeID is not None:
            asRow = cfg.actionStations.Get(actionStationTypeID)
            if asRow is not None:
                return {'ID': asRow.actionStationTypeID,
                 'Name': asRow.actionStationTypeName}

    def GetActionStationActions(self, actionStationTypeID):
        rows = cfg.actionStationActions.get(actionStationTypeID)
        actions = []
        if rows is not None:
            for row in rows:
                actions.append(row.actionID)

        return actions

    def GetActionObjectStations(self, actionObjectID):
        rows = cfg.actionObjectStations.get(actionObjectID)
        stations = []
        if rows is not None:
            for row in rows:
                quat = geo2.QuaternionRotationSetYawPitchRoll(row.rotY, row.rotX, row.rotZ)
                pos = (row.posX, row.posY, row.posZ)
                stations.append({'StationID': row.actionStationTypeID,
                 'InstID': row.actionStationInstanceID,
                 'pos': pos,
                 'rot': quat})

        return stations

    def GetActionObjectExits(self, actionObjectID, actionStationInstanceID):
        exits = []
        aoRows = cfg.actionObjectExits.get(actionObjectID)
        if aoRows is not None:
            rows = aoRows.get(actionStationInstanceID)
            if rows is not None:
                for row in rows:
                    quat = geo2.QuaternionRotationSetYawPitchRoll(row.rotY, row.rotX, row.rotZ)
                    pos = (row.posX, row.posY, row.posZ)
                    exits.append({'pos': pos,
                     'rot': quat})

        return exits


UseActionObject = ProcTypeDef(isMaster=True, procCategory='ActionObject', properties=[ProcPropertyTypeDef('Distance', 'F', userDataType=None, isPrivate=False)], description='Set the ActionObject in use by the requesting entity.')
StopUsingActionObject = ProcTypeDef(isMaster=True, procCategory='ActionObject', description='Set the ActionObject as no longer in use by the requesting entity.')
IsActionObjectActionAvailable = ProcTypeDef(isMaster=True, isConditional=True, procCategory='ActionObject', properties=[ProcPropertyTypeDef('Distance', 'F', userDataType=None, isPrivate=False)], description='Prereq to determine if the Action is available on the target object.')
ExclusiveIsActionObjectActionAvailable = ProcTypeDef(isMaster=True, isConditional=True, procCategory='ActionObject', properties=[ProcPropertyTypeDef('Distance', 'F', userDataType=None, isPrivate=False)], description='Prereq to determine if the Action is available on the target object. (Requires the reqesting entity not be involved in an ActionObject elsewhere.)')
SetActionObjectEntry = ProcTypeDef(isMaster=False, procCategory='ActionObject', description='Finds the closest action entry and sets its position and rotation in the ALIGN_POS and ALIGN_ROT properties.')
GetActionStationPosRot = ProcTypeDef(isMaster=False, procCategory='ActionObject', description='Finds the closest action station and sets its position and rotation in the ALIGN_POS and ALIGN_ROT properties.')
IsEntityOnActionObject = ProcTypeDef(isMaster=True, isConditional=True, procCategory='ActionObject', description='Returns true if the requesting entity is currently using an Action Object.')
exports = {'actionProcTypes.UseActionObject': UseActionObject,
 'actionProcTypes.StopUsingActionObject': StopUsingActionObject,
 'actionProcTypes.IsActionObjectActionAvailable': IsActionObjectActionAvailable,
 'actionProcTypes.ExclusiveIsActionObjectActionAvailable': ExclusiveIsActionObjectActionAvailable,
 'actionProcTypes.SetActionObjectEntry': SetActionObjectEntry,
 'actionProcTypes.GetActionStationPosRot': GetActionStationPosRot,
 'actionProcTypes.IsEntityOnActionObject': IsEntityOnActionObject}

#Embedded file name: carbon/common/script/world\GameWorldService.py
import service
import GameWorld
import locks
import geo2
import uthread

class GameWorldService(service.Service):
    __guid__ = 'GameWorld.GameWorldService'
    __displayname__ = 'GameWorld Service'

    def Run(self, *etc):
        service.Service.Run(self)
        GameWorld.Manager.Init()
        self.gameWorldManager = GameWorld.Manager
        useRemoteDebugger = False
        GameWorld.InitKynapse(useRemoteDebugger)
        self.gameworlds = {}
        self.waitingForGameWorlds = {}

    def OnLoadEntityScene(self, sceneID):
        self.LogInfo('Registering a new gameworld scene for', sceneID)
        gw = self.GetGameWorldType()()
        gw.instanceID = long(sceneID)
        gw.InitWorld('GameWorld_%s' % sceneID, const.GAMEWORLD_INIT_DATA, False)
        GameWorld.Manager.AddGameWorld(gw)
        self.gameworlds[sceneID] = gw
        if sceneID in self.waitingForGameWorlds:
            self.LogInfo('notifying gameworld waiters for', sceneID)
            self.waitingForGameWorlds.pop(sceneID).set()
        self.LogInfo('Done loading up gameworld scene', sceneID)
        return gw

    def OnEntitySceneLoaded(self, sceneID):
        """
        Starts ticking game world once start up entities have been created.
        """
        uthread.worker('gameWorldService::OnEntitySceneLoaded', self._OnEntitySceneLoaded, sceneID)

    def _OnEntitySceneLoaded(self, sceneID):
        """
        Starts ticking game world once start up entities have been created.
        """
        self.entityService.WaitForEntityScene(sceneID)
        entityScene = self.entityService.GetEntityScene(sceneID)
        entityScene.WaitOnStartupEntities()
        gw = self.gameworlds[sceneID]
        gw.StartTicking()

    def OnUnloadEntityScene(self, sceneID):
        pass

    def OnEntitySceneUnloaded(self, sceneID):
        self.LogInfo('Unloading the gameworld scene for', sceneID)
        if sceneID in self.gameworlds:
            gw = self.gameworlds[sceneID]
            del self.gameworlds[sceneID]
            GameWorld.Manager.DeleteGameWorld(gw.instanceID)
        if sceneID in self.waitingForGameWorlds:
            self.waitingForGameWorlds.pop(sceneID).set()
        self.LogInfo('Done Unloading the gameworld scene for', sceneID)

    def GetGameWorld(self, gameWorldID):
        """
        Returns the gameworld tree for the scene. Will block if we don't have one yet
        """
        gw = self.gameworlds.get(gameWorldID, None)
        if gw:
            return gw
        if gameWorldID not in self.waitingForGameWorlds:
            self.waitingForGameWorlds[gameWorldID] = locks.Event('GameWorldLoad_%s' % gameWorldID)
        self.LogInfo('Waiting for gameworld instance', gameWorldID)
        self.waitingForGameWorlds[gameWorldID].wait()
        self.LogInfo('Done Waiting for gameworld instance', gameWorldID)
        gw = self.gameworlds.get(gameWorldID, None)
        return gw

    def HasGameWorld(self, gameworldID):
        return gameworldID in self.gameworlds

    def GetGameWorldManager(self):
        return self.gameWorldManager

    def GetFloorHeight(self, pos, instanceID, upLength = 30.0, downLength = 10.0):
        """ Get Floor height code, useing havok for tests.
        Takes the pos given, finds the FloorMap collision point,
        and returns the y position of the ground at the point you're trying to walk to. """
        floorHeight = pos.y
        gameWorld = self.GetGameWorld(instanceID)
        if gameWorld == None:
            return pos.y
        floorHit = gameWorld.GetHeightAtPoint(pos, upLength, downLength)
        if floorHit != None:
            floorHeight = floorHit[0][1]
            if pos.y < floorHeight - const.FLOAT_TOLERANCE:
                return pos.y
        return floorHeight

    def GetHeightAtPoint(self, position, instanceID, upLength = 100.0, downLength = 100.0):
        gameWorld = self.GetGameWorld(instanceID)
        if gameWorld:
            floorHit = gameWorld.GetHeightAtPoint(position, upLength, downLength)
            return floorHit

    def GetFloorInfo(self, position, worldSpaceID):
        """ Return a point on the ground, and a poly reference, for the given position. """
        position.y = self.GetFloorHeight(position, worldSpaceID)
        return position

    def EntityLOS(self, startEntity, endPosition, offset = 1.8):
        """ Returns True if the entity is within line of sight of the location. """
        vStart = geo2.Vector(*startEntity.GetComponent('position').position)
        vEnd = geo2.Vector(endPosition[0], endPosition[1], endPosition[2])
        gameWorld = self.GetGameWorld(startEntity.scene.sceneID)
        if not gameWorld:
            return False
        vStart.y += offset
        vEnd.y += offset
        tRes = gameWorld.LineTest(vStart, vEnd)
        return tRes == None

#Embedded file name: talecommon\const.py
"""
A common module to provide constants for the tale system
"""
import collections
import utillib as util
from dogma.const import attributeScanGravimetricStrength
from inventorycommon.const import ownerUnknown
from eve.common.lib.appConst import securityClassZeroSec, securityClassLowSec, securityClassHighSec
templates = util.KeyVal(incursion=2, knownSpace=3, solarSystem=4)
actionClass = util.KeyVal(spawnOneDungeonAtEachCelestial=1, spawnManyDungeonsAtLocation=2, disableDjinns=3, addDjinnCommand=4, addSystemEffectBeacon=5, addSystemInfluenceTrigger=6, initializeInfluence=7, setBountySurcharge=8, endTale=9, spawnDungeonAtDeterministicLocation=10, spawnNPCsAtLocation=11)
conditionClass = util.KeyVal(checkSolarSystemSecurity=1)
systemInfluenceAny = 0
systemInfluenceDecline = 1
systemInfluenceRising = 2
Parameter = collections.namedtuple('Parameter', 'name parameterType defaultValue prettyName description')
parameterByID = {1: Parameter('dungeonID', int, 0, 'Dungeon ID', 'The ID of the dungeon to spawn'),
 2: Parameter('dungeonListID', int, None, 'Dungeon list ID', 'The ID of the list of dungeons to spawn'),
 3: Parameter('dungeonRespawnTime', int, 1, 'Dungeon respawn time', 'Dungeon respawn time in minutes'),
 4: Parameter('dungeonScanStrength', int, 100, 'Dungeon scan strength', 'Dungeon scan strength for scanning down the dungeon'),
 5: Parameter('dungeonSignatureRadius', float, 100.0, 'Dungeon signature radius', 'Dungeon signature radius used for scanning down the dungeon'),
 6: Parameter('dungeonScanStrengthAttrib', float, attributeScanGravimetricStrength, 'Dungeon scan attribute', 'Dungeon scan attribute'),
 7: Parameter('dungeonSpawnLocation', float, None, 'Dungeon spawn location', 'The locations in space where the dungeon is going to respawn'),
 8: Parameter('dungeonSpawnQuantity', int, 1, 'Number of Dungeons', 'The number of dungeons which have to be spawned'),
 9: Parameter('triggeredScene', int, None, 'Triggered Scene', 'The scene which is added to the trigger location when activated'),
 10: Parameter('triggeredSceneLocation', int, None, 'Trigger Location', 'The location the triggered scene is added when the trigger is activated'),
 11: Parameter('solarSystemSecurityMin', float, 1.0, 'Security minimum', 'The security level of the solar system has to be above this before the condition is true'),
 12: Parameter('solarSystemSecurityMax', float, 0.0, 'Security maximum', 'The security level of the solar system has to be below this before the condition is true'),
 13: Parameter('solarSystemSecurityMinInclusive', bool, True, 'Security minimum inclusive', 'This is whether the minimum should be inclusive or exclusive'),
 14: Parameter('solarSystemSecurityMaxInclusive', bool, False, 'Security maximum inclusive', 'This is whether the maximum should be inclusive or exclusive'),
 15: Parameter('disableConvoyDjinn', bool, False, 'Disable convoy djinn', 'Disables the convoy djinn during the tale'),
 16: Parameter('disableCustomsPoliceDjinn', bool, False, 'Disable custom police djinn', 'Disables the custom police during the tale'),
 17: Parameter('disableEmpirePoliceDjinn', bool, False, 'Disable empire police djinn', 'Disables the empire police during the tale'),
 18: Parameter('disableMilitaryFactionDjinn', bool, False, 'Disable military faction djinn', 'Disables the military faction djinn during the tale'),
 19: Parameter('disablePirateDjinn', bool, False, 'Disable pirate djinn', 'Disables the pirate djinn during the tale'),
 20: Parameter('disablePirateAutoDjinn', bool, False, 'Disable pirate auto djinn', 'Disables the pirate auto djinn during the tale'),
 21: Parameter('disablePirateStargateDjinn', bool, False, 'Disable pirate stargate djinn', 'Disables the pirate Stargate djinn during the tale'),
 22: Parameter('djinnCommandID', int, 0, 'Djinn command ID', 'The djinn command ID in this is added to solar system the scene is running in'),
 23: Parameter('systemEffectBeaconTypeID', int, 0, 'System effect beacon type ID', 'The type ID of the systems effect beacon'),
 24: Parameter('systemEffectBeaconBlockCynosural', bool, False, 'System effect beacon blocks cyno', 'The system effect beacon will also block cynosural jump'),
 25: Parameter('systemInfluenceTriggerDirection', int, systemInfluenceAny, 'Trigger direction', 'What direction the influence should change before the trigger is triggered'),
 26: Parameter('systemInfluenceTriggerValue', float, 0.0, 'Trigger value', 'The value around which the trigger should be triggered'),
 27: Parameter('dummyParameter', float, 0.0, 'Dummy Parameter', 'This is a dummy parameter for actions that take no parameters'),
 28: Parameter('surchargeRate', float, 0.2, 'Surcharge Rate', 'This is the surcharge rate that will be applied to this system'),
 29: Parameter('ownerID', int, ownerUnknown, 'Owner ID', 'Specifies the owner for items deployed through the scene.'),
 30: Parameter('entityTypeID', int, 0, 'Entity TypeID', 'The typeID for NPC to spawn.'),
 31: Parameter('entityAmountMin', int, 1, 'Minimum Entity Spawn Amount', 'The minimum amount of NPCs that should spawn.'),
 32: Parameter('entityAmountMax', int, 1, 'Maximum Entity Spawn Amount', 'The maximum amount of NPCs that should spawn.'),
 33: Parameter('entityGroupRespawnTimer', int, 30, 'Group Respawn Timer', 'The time (in minutes) it will take for the whole group to respawn if killed.'),
 34: Parameter('entityReinforcementAmountMin', int, 0, 'Minimum Reinforcement Size', 'The minimum size for the NPC group with reinforcements spawning for their aid.'),
 35: Parameter('entityReinforcementAmountMax', int, 0, 'Maximum Reinforcement Size', 'The maximum size for the NPC group with reinforcements spawning for their aid.'),
 36: Parameter('entityReinforcementCooldownTimer', int, 0, 'Reinforcement Cooldown Timer', 'The time (in seconds) that can pass between the NPC group asking for reinforcements.')}
parameter = util.KeyVal()
for _parameterID, _parameterLine in parameterByID.iteritems():
    setattr(parameter, _parameterLine.name, _parameterID)

sceneTypeMinConditional = 1000001
sceneTypeMinSystem = 5000001
scenesTypes = util.KeyVal()
conditionalScenesTypes = util.KeyVal()
sceneTypesByID = {1: util.KeyVal(name='headquarters', display='Headquarters'),
 2: util.KeyVal(name='assault', display='Assault'),
 3: util.KeyVal(name='vanguard', display='Vanguard'),
 4: util.KeyVal(name='staging', display='Staging'),
 5: util.KeyVal(name='testscene', display='Test Scene'),
 6: util.KeyVal(name='system', display='Solar System'),
 1000001: util.KeyVal(name='boss', display='Boss Spawn'),
 1000002: util.KeyVal(name='endTale', display='End Tale'),
 2000001: util.KeyVal(name='testscene1', display='Conditional Test Scene 1'),
 2000002: util.KeyVal(name='testscene2', display='Conditional Test Scene 2'),
 2000003: util.KeyVal(name='testscene3', display='Conditional Test Scene 3'),
 2000004: util.KeyVal(name='testscene4', display='Conditional Test Scene 4'),
 2000005: util.KeyVal(name='testscene5', display='Conditional Test Scene 5'),
 5000001: util.KeyVal(name='managerInit', display='Initialize Manager ')}
for _constID, _constNames in sceneTypesByID.iteritems():
    setattr(scenesTypes, _constNames.name, _constID)

distributionStatus = util.KeyVal(success=1, locationAlreadyUsed=2, failedRequirementFromTemplate=3, exception=4, hardKilled=5)
securityClassToParameterString = {securityClassZeroSec: 'DistributeNullSec',
 securityClassLowSec: 'DistributeLowSec',
 securityClassHighSec: 'DistributeHighSec'}
KNOWN_SPACE_RANDOM_SEED = 42
BLACKLIST_GENERIC = 1
BLACKLIST_INCURSIONS = 3
BLACKLIST_SLEEPER_SCOUTS = 4
DETERMINISTIC_PLACEMENT_AU_DISTANCE = 0.2

#Embedded file name: encounter.py
"""
Constants for the Encounter System
"""
ENCOUNTER_SCHEMA = 'zencounter'
_ENCOUNTER_PREFIX = ENCOUNTER_SCHEMA + '.'
ENCOUNTER_TABLE_FULL_NAME = _ENCOUNTER_PREFIX + 'encounters'
COORDINATE_SET_TABLE_FULL_NAME = _ENCOUNTER_PREFIX + 'coordinateSets'
COORDINATE_TABLE_FULL_NAME = _ENCOUNTER_PREFIX + 'coordinates'
ENCOUNTER_TYPE_IMMEDIATE = 0
ENCOUNTER_TYPE_TRIGGERED = 1
ENCOUNTER_TYPE_NAMES = {ENCOUNTER_TYPE_IMMEDIATE: 'Immediate',
 ENCOUNTER_TYPE_TRIGGERED: 'Triggered'}
#Embedded file name: workers/staticdata\__init__.py
from eve.common.lib.appConst import factionAmarrEmpire, factionAngelCartel, factionCaldariState, factionGallenteFederation, factionGuristasPirates, factionMinmatarRepublic, factionSanshasNation, factionSerpentis
from industry.const import MANUFACTURING, RESEARCH_TIME, COPYING, RESEARCH_MATERIAL
factionByRegionID = {10000020: factionAmarrEmpire,
 10000036: factionAmarrEmpire,
 10000038: factionAmarrEmpire,
 10000043: factionAmarrEmpire,
 10000052: factionAmarrEmpire,
 10000054: factionAmarrEmpire,
 10000065: factionAmarrEmpire,
 10000067: factionAmarrEmpire,
 10000001: factionAmarrEmpire,
 10000049: factionAmarrEmpire,
 10000012: factionAngelCartel,
 10000011: factionAngelCartel,
 10000005: factionAngelCartel,
 10000006: factionAngelCartel,
 10000007: factionAngelCartel,
 10000008: factionAngelCartel,
 10000009: factionAngelCartel,
 10000025: factionAngelCartel,
 10000061: factionAngelCartel,
 10000062: factionAngelCartel,
 10000002: factionCaldariState,
 10000016: factionCaldariState,
 10000033: factionCaldariState,
 10000069: factionCaldariState,
 10000032: factionGallenteFederation,
 10000037: factionGallenteFederation,
 10000044: factionGallenteFederation,
 10000048: factionGallenteFederation,
 10000064: factionGallenteFederation,
 10000068: factionGallenteFederation,
 10000015: factionGuristasPirates,
 10000003: factionGuristasPirates,
 10000010: factionGuristasPirates,
 10000029: factionGuristasPirates,
 10000035: factionGuristasPirates,
 10000045: factionGuristasPirates,
 10000055: factionGuristasPirates,
 10000028: factionMinmatarRepublic,
 10000030: factionMinmatarRepublic,
 10000042: factionMinmatarRepublic,
 10000022: factionSanshasNation,
 10000014: factionSanshasNation,
 10000031: factionSanshasNation,
 10000039: factionSanshasNation,
 10000047: factionSanshasNation,
 10000050: factionSanshasNation,
 10000056: factionSanshasNation,
 10000059: factionSanshasNation,
 10000060: factionSanshasNation,
 10000063: factionSanshasNation,
 10000057: factionSerpentis,
 10000041: factionSerpentis,
 10000023: factionSerpentis,
 10000046: factionSerpentis,
 10000051: factionSerpentis,
 10000058: factionSerpentis}
import inventorycommon.const as invconst
corpIDByFactionAndActivity = {MANUFACTURING: {factionAmarrEmpire: invconst.ownerAmarrConstructions,
                 factionCaldariState: invconst.ownerCaldariSteel,
                 factionGallenteFederation: invconst.ownerRodenShipyards,
                 factionMinmatarRepublic: invconst.ownerCoreComplexionInc,
                 factionAngelCartel: invconst.ownerSalvationAngels,
                 factionGuristasPirates: invconst.ownerGuristasProduction,
                 factionSanshasNation: invconst.ownerTrueCreations,
                 factionSerpentis: invconst.ownerSerpentisInquest},
 RESEARCH_MATERIAL: {factionAmarrEmpire: invconst.ownerCarthumConglomorate,
                     factionCaldariState: invconst.ownerZeroGResearchFirm,
                     factionGallenteFederation: invconst.ownerAllotekIndustries,
                     factionMinmatarRepublic: invconst.ownerSixKinDevelopment,
                     factionAngelCartel: invconst.ownerSalvationAngels,
                     factionGuristasPirates: invconst.ownerGuristasProduction,
                     factionSanshasNation: invconst.ownerTrueCreations,
                     factionSerpentis: invconst.ownerSerpentisInquest},
 RESEARCH_TIME: {factionAmarrEmpire: invconst.ownerNobleAppliances,
                 factionCaldariState: invconst.ownerPropelDynamics,
                 factionGallenteFederation: invconst.ownerChemalTech,
                 factionMinmatarRepublic: invconst.ownerEifyrAndCo,
                 factionAngelCartel: invconst.ownerSalvationAngels,
                 factionGuristasPirates: invconst.ownerGuristasProduction,
                 factionSanshasNation: invconst.ownerTrueCreations,
                 factionSerpentis: invconst.ownerSerpentisInquest},
 COPYING: {factionAmarrEmpire: invconst.ownerViziam,
           factionCaldariState: invconst.ownerRapidAssembly,
           factionGallenteFederation: invconst.ownerCreoDron,
           factionMinmatarRepublic: invconst.ownerThukkerMix,
           factionAngelCartel: invconst.ownerSalvationAngels,
           factionGuristasPirates: invconst.ownerGuristasProduction,
           factionSanshasNation: invconst.ownerTrueCreations,
           factionSerpentis: invconst.ownerSerpentisInquest}}
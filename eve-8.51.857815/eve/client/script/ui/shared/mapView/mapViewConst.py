#Embedded file name: eve/client/script/ui/shared/mapView\mapViewConst.py
from eve.client.script.ui.shared.maps.mapcommon import STARMODE_SECURITY
SETTING_PREFIX = 'mapviewX'
VIEWMODE_GROUP_SETTINGS = SETTING_PREFIX + '_grouping'
VIEWMODE_GROUP_SOLARSYSTEM = 0
VIEWMODE_GROUP_CONSTELLATIONS = 1
VIEWMODE_GROUP_REGIONS = 2
VIEWMODE_GROUP_DEFAULT = VIEWMODE_GROUP_SOLARSYSTEM
VIEWMODE_LINES_SETTINGS = SETTING_PREFIX + '_lines'
VIEWMODE_LINES_NONE = 3
VIEWMODE_LINES_ALL = 4
VIEWMODE_LINES_SELECTION = 5
VIEWMODE_LINES_SELECTION_REGION = 6
VIEWMODE_LINES_SELECTION_REGION_NEIGHBOURS = 7
VIEWMODE_LINES_DEFAULT = VIEWMODE_LINES_ALL
VIEWMODE_LINES_SHOW_ALLIANCE_SETTINGS = SETTING_PREFIX + '_show_alliance_lines'
VIEWMODE_LINES_SHOW_ALLIANCE_DEFAULT = True
VIEWMODE_LAYOUT_SHOW_ABSTRACT_SETTINGS = SETTING_PREFIX + '_layout'
VIEWMODE_LAYOUT_SHOW_ABSTRACT_DEFAULT = False
VIEWMODE_COLOR_SETTINGS = SETTING_PREFIX + '_colormode'
VIEWMODE_COLOR_DEFAULT = STARMODE_SECURITY
VIEWMODE_MARKERS_SETTINGS = SETTING_PREFIX + '_systemmap_markers'
VIEWMODE_MARKERS_OPTIONS = [const.groupPlanet,
 const.groupMoon,
 const.groupStation,
 const.groupAsteroidBelt,
 const.groupBeacon,
 const.groupSatellite,
 const.groupStargate,
 const.groupSovereigntyClaimMarkers,
 const.groupSovereigntyDisruptionStructures]
VIEWMODE_MARKERS_DEFAULT = VIEWMODE_MARKERS_OPTIONS[:]
DEFAULT_MAPVIEW_SETTINGS = {VIEWMODE_GROUP_SETTINGS: VIEWMODE_GROUP_DEFAULT,
 VIEWMODE_COLOR_SETTINGS: VIEWMODE_COLOR_DEFAULT,
 VIEWMODE_LAYOUT_SHOW_ABSTRACT_SETTINGS: VIEWMODE_LAYOUT_SHOW_ABSTRACT_DEFAULT,
 VIEWMODE_LINES_SETTINGS: VIEWMODE_LINES_DEFAULT,
 VIEWMODE_LINES_SHOW_ALLIANCE_SETTINGS: VIEWMODE_LINES_SHOW_ALLIANCE_DEFAULT,
 VIEWMODE_MARKERS_SETTINGS: VIEWMODE_MARKERS_DEFAULT}
VIEWMODE_FOCUS_SELF = 'focus_self'
MARKERID_MYPOS = 1
MARKERID_BOOKMARK = 2
MARKERID_ROUTE = 3
MARKERID_SOLARSYSTEM_CELESTIAL = 4
MARKERID_MYHOME = 5
MARKER_TYPES = (MARKERID_MYPOS,
 MARKERID_BOOKMARK,
 MARKERID_ROUTE,
 MARKERID_SOLARSYSTEM_CELESTIAL,
 MARKERID_MYHOME)
PRIMARY_MARKER_TYPES = [MARKERID_MYPOS, MARKERID_MYHOME]
MARKER_POINT_LEFT = 0
MARKER_POINT_TOP = 1
MARKER_POINT_RIGHT = 2
MARKER_POINT_BOTTOM = 3
JUMPBRIDGE_COLOR = (0.0, 1.0, 0.0, 1.0)
JUMPBRIDGE_CURVE_SCALE = 0.5
MAPVIEW_OVERLAY_PADDING_FULLSCREEN = (150, 12, 150, 200)
MAPVIEW_OVERLAY_PADDING_NONFULLSCREEN = (6, 12, 6, 6)

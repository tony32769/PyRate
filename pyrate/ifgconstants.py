'''
Collection of constants for elements in ROI_PAC headers (*.rsc)
Created on 14/09/2012
@author: Ben Davies
'''

# lookup keys for the fields in PyRate's custom GeoTIFF files
PYRATE_NCOLS = 'NCOLS'
PYRATE_NROWS = 'NROWS'
PYRATE_X_STEP = 'X_STEP'
PYRATE_Y_STEP = 'Y_STEP'
PYRATE_LAT = 'LAT'
PYRATE_LONG = 'LONG'
PYRATE_DATE = 'DATE'
PYRATE_DATE2 = 'DATE2'
#PYRATE_
PYRATE_DATUM = 'DATUM'
PYRATE_TIME_SPAN = 'TIME_SPAN_YEAR'
PYRATE_WAVELENGTH_METRES = 'WAVELENGTH_METRES'



# ROIPAC RSC header file constants
WIDTH = "WIDTH"
FILE_LENGTH = "FILE_LENGTH"
XMIN = "XMIN"
XMAX = "XMAX"
YMIN = "YMIN"
YMAX = "YMAX"
RLOOKS = "RLOOKS"
ALOOKS = "ALOOKS"
X_FIRST = "X_FIRST"
X_STEP = "X_STEP"
X_UNIT = "X_UNIT"
Y_FIRST = "Y_FIRST"
Y_STEP = "Y_STEP"
Y_UNIT = "Y_UNIT"
TIME_SPAN_YEAR = "TIME_SPAN_YEAR"
COR_THRESHOLD = "COR_THRESHOLD"
ORBIT_NUMBER = "ORBIT_NUMBER"
VELOCITY = "VELOCITY"
HEIGHT = "HEIGHT"
EARTH_RADIUS = "EARTH_RADIUS"
WAVELENGTH = "WAVELENGTH"
DATE = "DATE"
DATE12 = "DATE12"
HEADING_DEG = "HEADING_DEG"
RGE_REF1 = "RGE_REF1"
LOOK_REF1 = "LOOK_REF1"
LAT_REF1 = "LAT_REF1"
LON_REF1 = "LON_REF1"
RGE_REF2 = "RGE_REF2"
LOOK_REF2 = "LOOK_REF2"
LAT_REF2 = "LAT_REF2"
LON_REF2 = "LON_REF2"
RGE_REF3 = "RGE_REF3"
LOOK_REF3 = "LOOK_REF3"
LAT_REF3 = "LAT_REF3"
LON_REF3 = "LON_REF3"
RGE_REF4 = "RGE_REF4"
LOOK_REF4 = "LOOK_REF4"
LAT_REF4 = "LAT_REF4"
LON_REF4 = "LON_REF4"

# DEM specific
Z_OFFSET = "Z_OFFSET"
Z_SCALE = "Z_SCALE"
PROJECTION = "PROJECTION"
DATUM = "DATUM"

# custom header aliases
MASTER = "MASTER"
SLAVE = "SLAVE"
X_LAST = "X_LAST"
Y_LAST = "Y_LAST"


# store type for each of the header items
INT_HEADERS = [WIDTH, FILE_LENGTH, XMIN, XMAX, YMIN, YMAX, RLOOKS, ALOOKS,
							Z_OFFSET, Z_SCALE ]
STR_HEADERS = [X_UNIT, Y_UNIT, ORBIT_NUMBER, DATUM, PROJECTION ]
FLOAT_HEADERS = [X_FIRST, X_STEP, Y_FIRST, Y_STEP, TIME_SPAN_YEAR, COR_THRESHOLD,
								VELOCITY, HEIGHT, EARTH_RADIUS, WAVELENGTH, HEADING_DEG,
								RGE_REF1, RGE_REF2, RGE_REF3, RGE_REF4,
								LOOK_REF1, LOOK_REF2, LOOK_REF3, LOOK_REF4,
								LAT_REF1, LAT_REF2, LAT_REF3, LAT_REF4,
								LON_REF1, LON_REF2, LON_REF3, LON_REF4]
DATE_HEADERS = [DATE, DATE12]



ROI_PAC_HEADER_FILE_EXT = "rsc"

'''
Collection of constants for elements in ROI_PAC headers (\*.rsc)
+
Collection of constants used at different stages of ifg processing

Created on 14/09/2012

.. codeauthor:: Ben Davies
.. Sudipta Basak, GA
'''

# lookup keys for the fields in PyRate's custom GeoTIFF files
PYRATE_NCOLS = 'NCOLS'
PYRATE_NROWS = 'NROWS'
PYRATE_X_STEP = 'X_STEP'
PYRATE_Y_STEP = 'Y_STEP'
PYRATE_LAT = 'LAT'
PYRATE_LONG = 'LONG'
MASTER_DATE = 'MASTER_DATE'
MASTER_TIME = 'MASTER_TIME'
SLAVE_DATE = 'SLAVE_DATE'
SLAVE_TIME = 'SLAVE_TIME'
EPOCH_DATE = 'EPOCH_DATE'
PYRATE_DATUM = 'DATUM'
PYRATE_TIME_SPAN = 'TIME_SPAN_YEAR'
PYRATE_WAVELENGTH_METRES = 'WAVELENGTH_METRES'
PYRATE_INCIDENCE_DEGREES = 'INCIDENCE_DEGREES'

PYRATE_INSAR_PROCESSOR = 'INSAR_PROCESSOR'
PYRATE_APS_ERROR = 'APS_ERROR'
#PROCESS_STEP = 'PR_TYPE'
#GEOTIFF = 'GEOTIFF'
MULTILOOKED = 'MULTILOOKED_IFG'
ORIG = 'ORIGINAL_IFG'
DEM = 'DEM'
INCR = 'INCREMENTAL_TIME_SLICE'
CUML = 'CUMULATIVE_TIME_SLICE'
LINRATE = 'LINEAR_RATE_MAP'
LINERROR = 'LINEAR_RATE_ERROR_MAP'
PYRATE_ORBITAL_ERROR = 'ORBITAL_ERROR'
ORB_REMOVED = 'REMOVED'
REF_PHASE = 'REFERENCE_PHASE'
REF_PHASE_REMOVED = 'REMOVED'
NAN_STATUS = 'NAN_STATUS'
NAN_CONVERTED = 'CONVERTED'
DATA_TYPE = 'DATA_TYPE'
DATA_UNITS = 'DATA_UNITS'

DAYS_PER_YEAR = 365.25  # span of year, not a calendar year
SPEED_OF_LIGHT_METRES_PER_SECOND = 3e8
MM_PER_METRE = 1000

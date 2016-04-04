'''
Tests for the GAMMA file format interface.

Created on 29/05/2014

.. codeauthor:: Ben Davies
'''

import os, sys, unittest
from osgeo import gdal
from os.path import join
from datetime import date
from numpy.testing import assert_array_almost_equal
import uuid
import shutil
import numpy as np
import glob

from pyrate.scripts.converttogtif import main as gammaMain
from pyrate import gamma
from pyrate.tasks.utils import DUMMY_SECTION_NAME
import pyrate.ifgconstants as ifc
from pyrate.config import (
    DEM_HEADER_FILE,
    NO_DATA_VALUE,
    OBS_DIR,
    IFG_FILE_LIST,
    PROCESSOR,
    OUT_DIR,
    LUIGI,
    IFG_LKSX,
    IFG_LKSY,
    IFG_CROP_OPT,
    NO_DATA_AVERAGING_THRESHOLD)

from pyrate.tests.common import GAMMA_TEST_DIR
from pyrate.tests import common
from pyrate.tests.common import SYD_TEST_DIR, TEMPDIR
from pyrate.tests.common import sydney_data_setup
from pyrate import config as cf
from pyrate.scripts import run_pyrate, run_prepifg

gdal.UseExceptions()

LIGHTSPEED = 3e8  # approx


class GammaCommandLineTests(unittest.TestCase):

    def setUp(self):
        self.base = join(os.environ['PYRATEPATH'], 'tests', 'gamma')
        self.hdr = join(self.base, 'dem16x20raw.dem.par')
        temp_text = uuid.uuid4().hex
        self.confFile = os.path.join(
            TEMPDIR,
            '{}/gamma_test.cfg'.format(temp_text)
        )
        self.ifgListFile = os.path.join(
            TEMPDIR,
            '{}/gamma_ifg.list'.format(temp_text))
        self.base_dir = os.path.dirname(self.confFile)
        common.mkdir_p(self.base_dir)

    def tearDown(self):
        try:
            os.remove(self.exp_path)
        except:
            pass
        shutil.rmtree(self.base_dir)

    def makeInputFiles(self, data):
        with open(self.confFile, 'w') as conf:
            conf.write('[{}]\n'.format(DUMMY_SECTION_NAME))
            conf.write('{}: {}\n'.format(DEM_HEADER_FILE, self.hdr))
            conf.write('{}: {}\n'.format(NO_DATA_VALUE, '0.0'))
            conf.write('{}: {}\n'.format(OBS_DIR, self.base_dir))
            conf.write('{}: {}\n'.format(IFG_FILE_LIST, self.ifgListFile))
            conf.write('{}: {}\n'.format(PROCESSOR, '1'))
            conf.write('{}: {}\n'.format(OUT_DIR, self.base_dir))
        with open(self.ifgListFile, 'w') as ifgl:
            ifgl.write(data)

    def test_cmd_ifg(self):
        data = join(self.base, '16x20_20090713-20090817_VV_4rlks_utm.unw')
        self.exp_path = os.path.join(
            self.base_dir, '16x20_20090713-20090817_VV_4rlks_utm.tif')
        self.common_check(data)

    def test_cmd_dem(self):
        data = join(self.base, 'dem16x20raw.dem')
        self.exp_path = os.path.join(self.base_dir, 'dem16x20raw.tif')
        self.common_check(data)

    def common_check(self, data):
        self.makeInputFiles(data)
        sys.argv = ['gamma.py', self.confFile]
        gammaMain()
        self.assertTrue(os.path.exists(self.exp_path))


class GammaToGeoTiffTests(unittest.TestCase):
    'Tests conversion of GAMMA rasters to custom PyRate GeoTIFF'

    @classmethod
    def setUpClass(cls):
        # create common combined header obj so the headers are only read once
        # tricker: needs both ifg headers, and DEM one for the extents
        filenames = ['r20090713_VV.slc.par', 'r20090817_VV.slc.par']
        hdr_paths = [join(GAMMA_TEST_DIR, f) for f in filenames]
        hdrs = [gamma.parse_epoch_header(p) for p in hdr_paths]
        dem_hdr_path = join(GAMMA_TEST_DIR, 'dem16x20raw.dem.par')

        cls.DEM_HDR = gamma.parse_dem_header(dem_hdr_path)
        cls.COMBINED = gamma.combine_headers(*hdrs, dem_hdr=cls.DEM_HDR)

    def tearDown(self):
        if os.path.exists(self.dest):
            os.remove(self.dest)

    def test_to_geotiff_dem(self):
        hdr_path = join(GAMMA_TEST_DIR, 'dem16x20raw.dem.par')
        hdr = gamma.parse_dem_header(hdr_path)
        data_path = join(GAMMA_TEST_DIR, 'dem16x20raw.dem')
        self.dest = os.path.join(TEMPDIR, "tmp_gamma_dem.tif")

        gamma.to_geotiff(hdr, data_path, self.dest, nodata=0)
        exp_path = join(GAMMA_TEST_DIR, 'dem16x20_subset_from_gamma.tif')
        exp_ds = gdal.Open(exp_path)
        ds = gdal.Open(self.dest)

        # compare data and geographic headers
        assert_array_almost_equal(exp_ds.ReadAsArray(), ds.ReadAsArray())
        self.compare_rasters(ds, exp_ds)
        md = ds.GetMetadata()
        self.assertTrue(md['AREA_OR_POINT'] == 'Area')

    def test_to_geotiff_ifg(self):
        self.dest = os.path.join(TEMPDIR, 'tmp_gamma_ifg.tif')
        data_path = join(GAMMA_TEST_DIR, '16x20_20090713-20090817_VV_4rlks_utm.unw')
        gamma.to_geotiff(self.COMBINED, data_path, self.dest, nodata=0)

        ds = gdal.Open(self.dest)
        exp_path = join(GAMMA_TEST_DIR, '16x20_20090713-20090817_VV_4rlks_utm.tif')
        exp_ds = gdal.Open(exp_path)

        # compare data and geographic headers
        assert_array_almost_equal(exp_ds.ReadAsArray(), ds.ReadAsArray())
        self.compare_rasters(ds, exp_ds)

        md = ds.GetMetadata()
        self.assertEqual(len(md), 5)
        self.assertTrue(md[ifc.PYRATE_DATE] == str(date(2009, 7, 13)))
        self.assertTrue(md[ifc.PYRATE_DATE2] == str(date(2009, 8, 17)))
        self.assertTrue(md[ifc.PYRATE_TIME_SPAN] == str(35 / ifc.DAYS_PER_YEAR))

        wavelen = float(md[ifc.PYRATE_WAVELENGTH_METRES])
        self.assertAlmostEqual(wavelen, 0.05627457792190739)

    def test_to_geotiff_wrong_input_data(self):
        # use TIF, not UNW for data
        self.dest = os.path.join(TEMPDIR, 'tmp_gamma_ifg.tif')
        data_path = join(GAMMA_TEST_DIR,
                         '16x20_20090713-20090817_VV_4rlks_utm.tif')
        self.assertRaises(gamma.GammaException, gamma.to_geotiff,
                            self.COMBINED, data_path, self.dest, nodata=0)

    def test_mismatching_cell_resolution(self):
        hdrs = self.DEM_HDR.copy()
        hdrs[ifc.PYRATE_X_STEP] = 0.1 # fake a mismatch
        data_path = join(GAMMA_TEST_DIR, '16x20_20090713-20090817_VV_4rlks_utm.unw')
        self.dest = os.path.join(TEMPDIR, 'fake')

        self.assertRaises(gamma.GammaException, gamma.to_geotiff, hdrs,
                            data_path, self.dest, 0)

    def compare_rasters(self, ds, exp_ds):
        band = ds.GetRasterBand(1)
        exp_band = exp_ds.GetRasterBand(1)

        nodata = band.GetNoDataValue()
        self.assertFalse(nodata is None)
        self.assertEqual(exp_band.GetNoDataValue(), nodata)

        pj = ds.GetProjection()
        self.assertTrue('WGS 84' in pj)
        self.assertEqual(exp_ds.GetProjection(), pj)
        for exp, act in zip(exp_ds.GetGeoTransform(), ds.GetGeoTransform()):
            self.assertAlmostEqual(exp, act, places=4)

    def test_bad_projection(self):
        hdr = self.DEM_HDR.copy()
        hdr[ifc.PYRATE_DATUM] = 'nonexistent projection'
        data_path = join(GAMMA_TEST_DIR, 'dem16x20raw.dem')
        self.dest = os.path.join(TEMPDIR, 'tmp_gamma_dem2.tif')
        self.assertRaises(gamma.GammaException, gamma.to_geotiff, hdr,
                            data_path, self.dest, nodata=0)


class GammaHeaderParsingTests(unittest.TestCase):
    'Tests conversion of GAMMA headers to Py dicts'

    def test_parse_gamma_epoch_header(self):
        # minimal required headers are:
        # date:      2009  7 13
        # radar_frequency:        5.3310040e+09   Hz
        path = join(GAMMA_TEST_DIR, 'r20090713_VV.slc.par')
        hdrs = gamma.parse_epoch_header(path)

        exp_date = date(2009, 7, 13)
        self.assertEqual(hdrs[ifc.PYRATE_DATE], exp_date)

        exp_wavelen = LIGHTSPEED / 5.3310040e+09
        self.assertEqual(hdrs[ifc.PYRATE_WAVELENGTH_METRES], exp_wavelen)


    def test_parse_gamma_dem_header(self):
        path = join(GAMMA_TEST_DIR, 'dem16x20raw.dem.par')
        hdrs = gamma.parse_dem_header(path)

        self.assertEqual(hdrs[ifc.PYRATE_NCOLS], 16)
        self.assertEqual(hdrs[ifc.PYRATE_NROWS], 20)
        self.assertEqual(hdrs[ifc.PYRATE_LAT], -33.3831945)
        self.assertEqual(hdrs[ifc.PYRATE_LONG], 150.3870833)
        self.assertEqual(hdrs[ifc.PYRATE_X_STEP], 6.9444445e-05)
        self.assertEqual(hdrs[ifc.PYRATE_Y_STEP], -6.9444445e-05)


# Test data for the epoch header combination
H0 = { ifc.PYRATE_DATE : date(2009, 7, 13),
        ifc.PYRATE_WAVELENGTH_METRES : 1.8,
    }

H1 = { ifc.PYRATE_DATE : date(2009, 8, 17),
        ifc.PYRATE_WAVELENGTH_METRES : 1.8,
    }

H1_ERR = { ifc.PYRATE_DATE : date(2009, 8, 17),
            ifc.PYRATE_WAVELENGTH_METRES : 2.4,
    }


class HeaderCombinationTests(unittest.TestCase):
    'Tests GAMMA epoch and DEM headers can be combined into a single Py dict'

    def setUp(self):
        self.err = gamma.GammaException
        dem_hdr_path = join(GAMMA_TEST_DIR, 'dem16x20raw.dem.par')
        self.dh = gamma.parse_dem_header(dem_hdr_path)

    def test_combine_headers(self):
        filenames = ['r20090713_VV.slc.par', 'r20090817_VV.slc.par']
        paths = [join(GAMMA_TEST_DIR, p) for p in filenames]
        hdr0, hdr1 = [gamma.parse_epoch_header(p) for p in paths]

        chdr = gamma.combine_headers(hdr0, hdr1, self.dh)

        exp_timespan = (18 + 17) / ifc.DAYS_PER_YEAR
        self.assertEqual(chdr[ifc.PYRATE_TIME_SPAN], exp_timespan)

        exp_date = date(2009, 7, 13)
        self.assertEqual(chdr[ifc.PYRATE_DATE], exp_date)
        exp_date2 = date(2009, 8, 17)
        self.assertEqual(chdr[ifc.PYRATE_DATE2], exp_date2)

        exp_wavelen = LIGHTSPEED / 5.3310040e+09
        self.assertEqual(chdr[ifc.PYRATE_WAVELENGTH_METRES], exp_wavelen)


    def test_fail_non_dict_header(self):
        self.assertRaises(self.err, gamma.combine_headers, H0, '', self.dh)
        self.assertRaises(self.err, gamma.combine_headers, '', H0, self.dh)
        self.assertRaises(self.err, gamma.combine_headers, H0, H1, None)
        self.assertRaises(self.err, gamma.combine_headers, H0, H1, '')


    def test_fail_mismatching_wavelength(self):
        self.assertRaises(self.err, gamma.combine_headers, H0, H1_ERR, self.dh)


    def test_fail_same_date(self):
        self.assertRaises(self.err, gamma.combine_headers, H0, H0, self.dh)


    def test_fail_bad_date_order(self):
        self.assertRaises(self.err, gamma.combine_headers, H1, H0, self.dh)


class TestGammaLuigiEquality(unittest.TestCase):

    SYDNEY_GAMMA_TEST = os.path.join(SYD_TEST_DIR, 'gamma_sydney_test')
    @classmethod
    def setUpClass(cls):

        luigi_dir = uuid.uuid4().hex
        non_luigi_dir = uuid.uuid4().hex
        cls.luigi_confFile = os.path.join(
            TEMPDIR,
            '{}/gamma_test.conf'.format(luigi_dir)
        )
        cls.luigi_ifgListFile = os.path.join(
            TEMPDIR,
            '{}/gamma_ifg.list'.format(luigi_dir)
        )
        cls.non_luigi_confFile = os.path.join(
            TEMPDIR,
            '{}/gamma_test.conf'.format(non_luigi_dir)
        )
        cls.non_luigi_ifgListFile = os.path.join(
            TEMPDIR,
            '{}/gamma_ifg.list'.format(non_luigi_dir)
        )

        cls.luigi_base_dir = os.path.dirname(cls.luigi_confFile)
        cls.non_luigi_base_dir = os.path.dirname(cls.non_luigi_confFile)
        common.mkdir_p(cls.luigi_base_dir)
        common.mkdir_p(cls.non_luigi_base_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.luigi_base_dir)
        shutil.rmtree(cls.non_luigi_base_dir)

    def make_input_files(self, data):
        with open(self.conf_file, 'w') as conf:
            conf.write('[{}]\n'.format(DUMMY_SECTION_NAME))
            conf.write('{}: {}\n'.format(NO_DATA_VALUE, '0.0'))
            conf.write('{}: {}\n'.format(OBS_DIR, self.base_dir))
            conf.write('{}: {}\n'.format(OUT_DIR, self.base_dir))
            conf.write('{}: {}\n'.format(IFG_FILE_LIST, self.ifgListFile))
            conf.write('{}: {}\n'.format(PROCESSOR, '1'))
            conf.write('{}: {}\n'.format(LUIGI, self.LUIGI))
            conf.write('{}: {}\n'.format(
                DEM_HEADER_FILE, os.path.join(
                    self.SYDNEY_GAMMA_TEST, '20060619_utm_dem.par')))
            conf.write('{}: {}\n'.format(IFG_LKSX, '1'))
            conf.write('{}: {}\n'.format(IFG_LKSY, '1'))
            conf.write('{}: {}\n'.format(IFG_CROP_OPT, '1'))
            conf.write('{}: {}\n'.format(NO_DATA_AVERAGING_THRESHOLD, '0.5'))
        with open(self.ifgListFile, 'w') as ifgl:
            ifgl.write('\n'.join(data))

    def test_cmd_ifg_luigi_files_created(self):

        self.LUIGI = '1'  # luigi or no luigi
        self.conf_file = self.luigi_confFile
        self.base_dir = self.luigi_base_dir
        self.ifgListFile = self.luigi_ifgListFile
        self.common_check(self.luigi_confFile)

    def test_cmd_ifg_no_luigi_files_created(self):
        self.LUIGI = '0'  # luigi or no luigi
        self.conf_file = self.non_luigi_confFile
        self.base_dir = self.non_luigi_base_dir
        self.ifgListFile = self.non_luigi_ifgListFile
        self.common_check(self.non_luigi_confFile)

    def common_check(self, conf_file):
        data_paths = glob.glob(
            os.path.join(self.SYDNEY_GAMMA_TEST, "*_utm.unw"))

        self.make_input_files(data_paths)
        sys.argv = ['run_pyrate.py', conf_file]

        base_ifg_paths, dest_paths, params = run_pyrate.get_ifg_paths()
        dest_base_ifgs = [os.path.join(
            params[cf.OUT_DIR], os.path.basename(q).split('.')[0] + '.tif')
            for q in base_ifg_paths]
        sys.argv = ['run_prepifg.py', conf_file]
        run_prepifg.main()

        for p, q in zip(dest_base_ifgs, dest_paths):
            self.assertTrue(os.path.exists(p),
                            '{} does not exist'.format(p))
            self.assertTrue(os.path.exists(q),
                            '{} does not exist'.format(q))

    def test_equality_of_luigi_and_no_luigi_phase_data(self):

        all_luigi_ifgs = sydney_data_setup(
            glob.glob(os.path.join(self.luigi_base_dir, "*.tif")))
        all_non_luigi_ifgs = sydney_data_setup(
            glob.glob(os.path.join(self.non_luigi_base_dir, "*.tif")))

        self.assertEquals(len(all_luigi_ifgs), len(all_non_luigi_ifgs))
        c = 0
        for c, (i, j) in enumerate(zip(all_luigi_ifgs, all_non_luigi_ifgs)):
            np.testing.assert_array_equal(i.phase_data, j.phase_data)
        self.assertEquals(c + 1, len(all_luigi_ifgs))

    def test_eqality_of_meta_data(self):
        all_luigi_ifgs = sydney_data_setup(
            glob.glob(os.path.join(self.luigi_base_dir, "*.tif")))
        all_non_luigi_ifgs = sydney_data_setup(
            glob.glob(os.path.join(self.non_luigi_base_dir, "*.tif")))

        c = 0
        for c, (i, j) in enumerate(zip(all_luigi_ifgs, all_non_luigi_ifgs)):
            mdi = i.meta_data
            mdj = j.meta_data
            for k in mdi:  # all key vaues equal
                self.assertEquals(mdj[k], mdi[k])

        self.assertEquals(c + 1, len(all_luigi_ifgs))

if __name__ == "__main__":
    unittest.main()
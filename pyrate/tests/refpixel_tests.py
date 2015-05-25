'''
Collection of tests for validating PyRate's reference pixel code.

.. codeauthor:: Ben Davies
'''

import unittest
from numpy import nan, mean, std, isnan

from common import sydney_data_setup, MockIfg
from pyrate.refpixel import ref_pixel, RefPixelError, _step
from pyrate.config import ConfigException


# default testing values
REFNX = 5
REFNY = 7
MIN_FRAC = 0.7
CHIPSIZE = 3


class ReferencePixelInputTests(unittest.TestCase):
    '''
    Verifies error checking capabilities of the reference pixel function
    '''

    def setUp(self):
        self.ifgs = sydney_data_setup()

    def test_missing_chipsize(self):
        args = (REFNX, REFNY, None, MIN_FRAC)
        self.assertRaises(ConfigException, ref_pixel, self.ifgs, *args)


    def test_chipsize_valid(self):
        for illegal in [0, -1, -15, 1, 2, self.ifgs[0].ncols+1, 4, 6, 10, 20]:
            args = (REFNX, REFNY, illegal, MIN_FRAC)
            self.assertRaises(ValueError, ref_pixel, self.ifgs, *args)


    def test_minimum_fraction_missing(self):
        args = (REFNX, REFNY, CHIPSIZE, None)
        self.assertRaises(ConfigException, ref_pixel, self.ifgs, *args)


    def test_minimum_fraction_threshold(self):
        for illegal in [-0.1, 1.1, 1.000001, -0.0000001]:
            args = (REFNX, REFNY, CHIPSIZE, illegal)
            self.assertRaises(ValueError, ref_pixel, self.ifgs, *args)


    def test_search_windows(self):
        # 45 is max # cells a width 3 sliding window can iterate over
        for illegal in [-5, -1, 0, 46, 50, 100]:
            args = (illegal, REFNY, CHIPSIZE, MIN_FRAC)
            self.assertRaises(ValueError, ref_pixel, self.ifgs, *args)

        # 40 is max # cells a width 3 sliding window can iterate over
        for illegal in [-5, -1, 0, 71, 85, 100]:
            args = (REFNX, illegal, CHIPSIZE, MIN_FRAC)
            self.assertRaises(ValueError, ref_pixel, self.ifgs, *args)


    def test_missing_search_windows(self):
        args = (None, REFNY, CHIPSIZE, MIN_FRAC)
        self.assertRaises(ConfigException, ref_pixel, self.ifgs, *args)

        args = (REFNX, None, CHIPSIZE, MIN_FRAC)
        self.assertRaises(ConfigException, ref_pixel, self.ifgs, *args)



class ReferencePixelTests(unittest.TestCase):
    """
    Tests reference pixel search
    """

    def setUp(self):
        self.ifgs = sydney_data_setup()

    def test_all_below_threshold_exception(self):
        # test failure when no valid stacks in dataset

        # rig mock data to be below threshold
        mock_ifgs = [MockIfg(i, 6, 7) for i in self.ifgs]
        for m in mock_ifgs:
            m.phase_data[:1] = nan
            m.phase_data[1:5] = 0.1
            m.phase_data[5:] = nan

        args = (2, 2, 3, 0.7)
        self.assertRaises(RefPixelError, ref_pixel, mock_ifgs, *args)


    def test_refnxy_step_1(self):
        # test step of 1 for refnx|y gets the reference pixel for axis centre
        mock_ifgs = [MockIfg(i, 47, 72) for i in self.ifgs]
        for m in mock_ifgs:
            m.phase_data[:1] = 0.2
            m.phase_data[1:5] = 0.1
            m.phase_data[5:] = 0.3

        exp_refpx = (36,23)
        res = ref_pixel(mock_ifgs, refnx=1, refny=1, chipsize=3, min_frac=0.7)
        self.assertEqual(exp_refpx, res)


    def test_large_window(self):
        # 5x5 view over a 5x5 ifg with 1 window/ref pix search
        chps = 5
        mockifgs = [MockIfg(i, chps, chps) for i in self.ifgs]
        res = ref_pixel(mockifgs, refnx=1, refny=1, chipsize=chps, min_frac=0.7)
        self.assertEqual((2,2), res)


    def test_step(self):
        # test different search windows to verify x/y step calculation

        # convenience testing function
        def assert_equal(actual, expected):
            for a, e in zip(actual, expected):
                self.assertEqual(a, e)

        # start with simple corner only test
        width = 47
        radius = 2
        refnx = 2
        exp = [2, 44]
        act = _step(width, refnx, radius)
        assert_equal(act, exp)

        # test with 3 windows
        refnx = 3
        exp = [2, 23, 44]
        act = _step(width, refnx, radius)
        assert_equal(act, exp)

        # test 4 search windows
        refnx = 4
        exp = [2, 16, 30, 44]
        act = _step(width, refnx, radius)
        assert_equal(act, exp)


    def test_ref_pixel(self):
        exp_refpx = (2,2) # calculated manually from _expected_ref_pixel()
        res = ref_pixel(self.ifgs, 2, 2, 5, 0.7)
        self.assertEqual(res, exp_refpx)

        # Invalidate first data stack, get new refpix coods & retest
        for i in self.ifgs:
            i.phase_data[:3,:5] = nan

        exp_refpx = (2,44) # calculated manually from _expected_ref_pixel()
        res = ref_pixel(self.ifgs, 2, 2, 5, 0.7)
        self.assertEqual(res, exp_refpx)


def _expected_ref_pixel(ifgs, cs):
    '''Helper function for finding reference pixel when refnx/y=2'''

    # calculate expected data
    data = [i.phase_data for i in ifgs] # len 17 list of arrays
    ul = [ i[:cs,:cs] for i in data] # upper left corner stack
    ur = [ i[:cs,-cs:] for i in data]
    ll = [ i[-cs:,:cs] for i in data]
    lr = [ i[-cs:,-cs:] for i in data]

    ulm = mean([std(i[~isnan(i)]) for i in ul]) # mean std of all the layers
    urm = mean([std(i[~isnan(i)]) for i in ur])
    llm = mean([std(i[~isnan(i)]) for i in ll])
    lrm = mean([std(i[~isnan(i)]) for i in lr])
    assert isnan([ulm, urm, llm, lrm]).any() == False

    # coords of the smallest mean is the result
    mn = [ulm, urm, llm, lrm]
    print mn, min(mn), mn.index(min(mn))



if __name__ == "__main__":
    unittest.main()

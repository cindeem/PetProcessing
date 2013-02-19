# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
""" test nicm """

import os
from os.path import abspath, join, dirname, exists

import numpy as np
import nibabel as ni

from numpy.testing import (assert_raises, assert_equal,
                           assert_almost_equal, assert_array_less)

from unittest import TestCase, skipIf, skipUnless
from .. import seg_em


class TestSegEM(TestCase):

    def get_data_dir(self):
        pth, _  = os.path.split(abspath(__file__))
        return join(pth, 'data')

    def setUp(self):
        
        self.template = join(self.get_data_dir(),  'test_template.nii.gz')
        dat = ni.load(self.template).get_data()
        dat = np.nan_to_num(dat)
        dat[dat < 0] = 0
        self.flat = dat.flatten()
        self.seq = range(10)

    def test_load_img(self):
        # make sure the shuffled sequence does not lose any elements
        dat = ni.load(self.template).get_data()

        # flat sets negative values to zero
        assert_array_less(dat.flatten()[2], self.flat[2])
        assert_equal(dat.flatten()[0], self.flat[0])

    def test_calc_mus_sigma(self):
        pass 

if __name__ == '__main__':
    unittest.main()

# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
""" test nicm """

import os
from os.path import abspath, join, dirname, exists

import numpy as np
import nibabel as ni

from numpy.testing import (assert_raises, assert_equal,
                           assert_almost_equal, assert_array_less,
                           assert_array_equal)

from unittest import TestCase, skipIf, skipUnless
from .. import preprocessing
import tempfile


class TestROIStatsNibabel(TestCase):
    def get_data_dir(self):
        pth, _  = os.path.split(abspath(__file__))
        return join(pth, 'data')

    def setUp(self):
        """ create small tmp data and write to tmp directory"""
        self.template = join(self.get_data_dir(),  'test_template.nii.gz')
        data = np.random.random((10,10,2))

        mask = np.zeros((10,10,2))
        mask[5:,5:,:] = 1
        gm = np.zeros((10,10,2))
        gm[6:, 6:,:] = 1
        label = np.zeros((10,10,2))
        label[5:5,5:6,:] = 1
        label[6:, 6:,:] = 2
        aff = np.eye(4) # identitiy matrix
        datad = dict(zip(['data', 'mask', 'gm', 'label'],
                         [data, mask, gm, label])) 
        filemap = {}
        tmpdir = tempfile.mkdtemp()
        print tmpdir
        for nme, tmpdat in datad.items():
            newimg = ni.Nifti1Image(tmpdat, aff)
            newfile = join(tmpdir, '%s.nii.gz'%(nme))
            newimg.to_filename(newfile)
            filemap.update({nme:newfile})
        bigmask = np.zeros((20,20,2))
        bigmask[6:,6:,:] = 1
        bigaff = np.eye(4) * .5
        bigaff[-1,-1] = 1
        newimg = ni.Nifti1Image(bigmask, bigaff)
        newfile = join(tmpdir, 'bigmask.nii.gz')
        newimg.to_filename(newfile)
        filemap.update({'bigmask': newfile})
        self.filemap = filemap
        self.tmpdir = tmpdir

    def tearDown(self):
        """get rid of tmp files and directory"""
        cmd = 'rm -rf %s'%(self.tmpdir)
        print cmd

        os.system(cmd)

    def test_reslice_data(self):
        mask = self.filemap['mask']
        bigmask = self.filemap['bigmask']
        data = self.filemap['data']
        print ni.load(data).get_affine()
        img, newdat = preprocessing.reslice_data(data, mask)
        # test item not needing reslicing doesnt change
        assert_array_equal(newdat, ni.load(mask).get_data())
        assert_raises(RuntimeError, 
                      preprocessing.reslice_data, mask, self.template)
        # test label image not cast to float 
        label = self.filemap['label']
        img, newdat = preprocessing.reslice_data(data, label)
        assert_equal(newdat.shape, ni.load(data).get_shape())
        assert_equal(set(newdat.flatten()), set([0.0,2.0]))
        # test label is cast to float
        img, newdatf = preprocessing.reslice_data(data, label, order=3)
        assert_almost_equal(newdatf[9,9,:], newdat[9,9,:])


    """
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

    def test_calc_mu_sigma(self):
        m1,m2,m3,std1, std2 = seg_em.calc_mu_sigma(self.flat)
        assert_equal(m1, 0.0)
        assert_almost_equal(m2,0.61140956)
        assert_almost_equal(std1, 0.185017225388)         
    """

if __name__ == '__main__':

    unittest.main()


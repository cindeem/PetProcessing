import os
import tempfile
import warnings
from unittest import TestCase, skipIf, skipUnless
import numpy as np
from numpy.testing import (assert_raises, assert_equal, 
                           assert_almost_equal, assert_warns)
from os.path import exists, join, split, abspath
import py_logan


def test_parse_file():
    tmpd = tempfile.mkdtemp()
    jnk = np.empty((10,4))
    jnk[:,0] = np.arange(10)
    jnk[:,1] = np.arange(0,50,5)
    jnk[:,-1] = np.ones(10) * 5
    jnk[:,-2] = jnk[:,1] + jnk[:,-1]
    csvf = os.path.join(tmpd,'csv.csv')
    tabf = os.path.join(tmpd, 'tab.csv')
    with open (csvf, 'w+') as fid:
        fid.write('frame,start,stop,dur,\n')
        for line in jnk:
            fid.write(','.join(['%s'%x for x in line]) + ',\n')
    with open (tabf, 'w+') as fid:
        fid.write('frame\tstart\tstop\tdur\t\n')
        for line in jnk:
            fid.write('\t'.join(['%s'%x for x in line]) + '\t\n')
    jnk_csv = py_logan.parse_file(csvf)
    assert_warns(UserWarning, py_logan.parse_file, tabf)
    # note will not raise warning second time
    jnk_tab = py_logan.parse_file(tabf)
    assert_equal(jnk_csv, jnk_tab)
    
    ## cleanup
    os.system('rm -rf %s'%(tmpd))

def test_label_mask():
    tmpdir = tempfile.mkdtemp()
    jnk = np.zeros((10,10,10))
    


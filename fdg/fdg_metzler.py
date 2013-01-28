# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
import base_gui as bg
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing/pvc')
import metzler
import logging, logging.config
from time import asctime

if __name__ == '__main__':
    """Uses specified subject dir
    finds dvr dir
    find aparc_aseg in pet space
    makes brainmask
    runs ecat_smooth
    creates pvc directory with pvc corrected data
    """
    # start wx gui app
    app = wx.App()

    roifile = '/home/jagust/cindeem/CODE/PetProcessing/pib/fsrois_pibindex.csv'

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose FDG data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(__file__, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    tracer = 'FDG'
    user = os.environ['USER']
    _, fname = os.path.split(__file__)
    logging.info('###START %s :::'%(fname))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    for sub in subs:
        
        _, fullsubid = os.path.split(sub)
        try:
            m = pp.re.search('B[0-9]{2}-[0-9]{3}',fullsubid)
            subid = m.group()
        except:
            logging.error('cant find ID in %s'%fullsubid)
            continue
        logging.info('%s'%subid)
        # make filepath to tracer dir
        pth = os.path.join(sub, tracer.lower())
        if not os.path.exists(pth):
            logging.error('SKIP: missing %s'%pth)
            continue
        pvcdir, exists = utils.make_dir(pth, 'pvc_metzler')
        if exists:
            logging.error('%s exists, remove to re-run'%(pvcdir))
            continue
        # get ponsnormd
        globstr = '%s/nonan-ponsnormed_%s*nii*'%(pth,subid)                  
        ponsnormd = pp.find_single_file(globstr)
        if ponsnormd is None:
            logging.error('%s missing, skipping'%(globstr))
            continue
        # copy ponsnormd to pvc directory
        cponsnormd = utils.copy_file(ponsnormd, pvcdir)
        # get raparc
        corgdir = os.path.join(pth, 'coreg_mri2fdg')
        globstr = '%s/rB*aparc_aseg.nii'%(corgdir)
        raparc = pp.find_single_file(globstr)
        if raparc is None:
            logging.error('%s missing, skipping '%(globstr))
            continue
        #copy raparc_aseg to pvd dir
        craparc = utils.copy_file(raparc, pvcdir)
        # make brainamsk
        bmask = metzler.make_aseg_brainmask(craparc)
        os.unlink(craparc)
        smooth_bmask = pp.fname_presuffix(bmask, prefix='s')
        _ = metzler.smooth_mask_nipy(bmask, smooth_bmask)
        ero_bmask = metzler.fsl_erode2d(bmask)
        pvcpet = metzler.calc_pvc(cponsnormd, ero_bmask, smooth_bmask)
        os.unlink(cponsnormd)
        logging.info('Created %s'%(pvcpet))
        

# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
import base_gui as bg
import fs_tools as fst
import logging, logging.config
from time import asctime

if __name__ == '__main__':
    """sets up subject directory structure
    Select subs from ARDA,
    1. creates output dirs
    2. copies pet data to Raw
    3. converts
    """

    # start wx gui app
    app = wx.App()

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose project data dir',
                              indir = '/home/jagust')

    mridir = bg.SimpleDirDialog(prompt='Choose Freesurfer data dir',
                                indir = '/home/jagust')
    cleantime = asctime().replace(' ','-').replace(':', '-')
    _, scriptnme = os.path.split(__file__)
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(scriptnme, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START Setup Directory :::')
    logging.info('###TRACER Setup %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    
    for s in subs:
        _, subid = os.path.split(s)
        # mk tracer directory  in freesurfer
        fsdir = os.path.join(mridir, subid)
        if not os.path.isdir(fsdir):
             logging.warning('%s missing, skipping'%fsdir)
             continue
        petdir, exists = bg.make_dir(fsdir, dirname = 'pib')
        if exists:
            logging.warning('%s exists, skipping'%(petdir))
            continue
        globstr = os.path.join(s, 'pib','dvr','DVR*nii*')
        dvr = pp.find_single_file(globstr)
        if dvr is None:
            logging.warning('%s missing, skipping'%(globstr))
            continue
        coregdir,exists = bg.make_dir('%s/pib'%s, 'pet2mri')
        if exists:
            logging.warning('remove %s to rerun?'%coregdir)
            continue
        ## find brainmask
        globstr = os.path.join(s, 'anatomy','brainmask.nii')
        brainmask = pp.find_single_file(globstr)
        ## find sum
        globstr = os.path.join(s, 'pib','realign_QA','mean20min*.nii')
        sum = pp.find_single_file(globstr)

        if brainmask is None or sum is None:
            logging.error('pet2mri sum: %s brainmask: %s'%(sum, brainmask))
            continue
        # move dvr and sum to coregdir, unzip if necessary
        cdvr = bg.copy_file(dvr, coregdir)
        csum = bg.copy_file(sum, coregdir)
        cdvr = bg.unzip_file(cdvr)
        csum = bg.unzip_file(csum)
        ## coreg pet 2 brainmask
        corg_out = pp.simple_coregister(str(brainmask),
                                        str(csum),
                                        other=str(cdvr))
        if not corg_out.runtime.returncode == 0:
            logging.error(corg_out.runtime.traceback)
            continue
        rdvr = corg_out.outputs.coregistered_files
        # copy dvr to freesurfer subjects petdir
        cdvr = bg.copy_file(rdvr, petdir)
        globstr = os.path.join(fsdir, 'mri', 'T1.mgz')
        t1 = pp.find_single_file(globstr)
        if t1 is None:
            logging.error('%s not found'%globstr)
            continue           
        xfm = fst.fs_generate_dat(cdvr, t1, subid)
        outfiles = fst.pet_2_surf(cdvr, xfm, mridir)
        # zip files in coregdir
        allf = glob('%s/*'%coregdir)
        bg.zip_files(allf)

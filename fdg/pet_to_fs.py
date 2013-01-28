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

    
    tracer = 'FDG'
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
        petdir, exists = utils.make_dir(fsdir, dirname = 'fdg')
        if exists:
            logging.warning('%s exists, skipping'%(petdir))
            continue
        globstr = os.path.join(s, 'fdg','nonan*pons*nii*')
        ponsnormed = pp.find_single_file(globstr)
        if ponsnormed is None:
            logging.warning('%s missing, skipping'%(globstr))
            continue
        coregdir,exists = utils.make_dir('%s/fdg'%s, 'pet2mri')
        if exists:
            continue
        ## find brainmask
        globstr = os.path.join(s, 'anatomy','brainmask.nii')
        brainmask = pp.find_single_file(globstr)
        ## find sum
        globstr = os.path.join(s, 'fdg','sum_r*.nii')
        sum = pp.find_single_file(globstr)

        if brainmask is None or sum is None:
            logging.error('pet2mri sum: %s brainmask: %s'%(sum, brainmask))
            continue
        ## coreg pet 2 brainmask
        cpons = pp.copy_file(ponsnormed, coregdir)
        csum = pp.copy_file(sum, coregdir)
        
        corg_out = pp.simple_coregister(str(brainmask),
                                        str(csum),
                                        other=str(cpons))
        if not corg_out.runtime.returncode == 0:
            logging.error(corg_out.runtime.stderr)
            continue
        rpons = corg_out.outputs.coregistered_files
        # copy ponsnormed to freesurfer subjects petdir
        cponsnormed = pp.copy_file(rpons, petdir)
        globstr = os.path.join(fsdir, 'mri', 'T1.mgz')
        t1 = pp.find_single_file(globstr)
        if t1 is None:
            logging.error('%s not found'%globstr)
            continue           
        xfm = fst.fs_generate_dat(cponsnormed, t1, subid)
        outfiles = fst.pet_2_surf(cponsnormed, xfm, mridir)

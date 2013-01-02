# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
import base_gui as bg
import qa 
import logging, logging.config
from time import asctime

if __name__ == '__main__':
    """
    Uses specified PIB directory
    finds pib nifti files
    check number of files
    realigned 6-end to frame 17
    sum 1-5
    coreg summed 1-5 to mean from realign, and apply to each frame
    run qa on scans
    """
    # start wx gui app
    app = wx.App()

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs','%s_%s.log'%(__file__, cleantime))
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START %s :::'%(__file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)

    # choose template
    template = bg.FilesDialog(prompt='Choose template',
                           indir='/home/jagust/cindeem/TEMPLATES')
    logging.info('Template: %s'%(template[0]))
    template = str(template[0])
    _, tname, _ = pp.split_filename(template)
                 

    for sub in subs:
        if '_v2' in sub:
            logging.info('skipping visit2 %s'%(sub))
            continue
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        anatdir = os.path.join(sub, 'anatomy')
        if not os.path.isdir(anatdir):
            logging.error('%s doesnt exist,skipping'%(anatdir))
            continue
        dvrdir = os.path.join(sub,'pib','dvr')
        if not os.path.isdir(dvrdir):
            logging.error('%s doesnt exist,skipping'%(dvrdir))
            continue
        # make/check warp dir
        warpdir, exists = bg.make_dir(dvrdir, 'warp_%s'%tname)
        if exists:
            logging.warning('%s exists, remove to rerun'%(warpdir))
            continue
        #get brainmask
        globstr = os.path.join(dvrdir, 'DVR-%s*.nii*'%subid)
        dvr = pp.find_single_file(globstr)
        if dvr is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        dvr = bg.unzip_file(dvr)
        # get mean 20 minute pib
        globstr = os.path.join(sub,'pib','realign_QA', 'mean20min*.nii*')
        mean20 = pp.find_single_file(globstr)
        if mean20 is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        mean20 = bg.unzip_file(mean20)        
        # brainmask
        globstr = os.path.join(anatdir, 'brainmask.nii*')
        brainmask = pp.find_single_file(globstr)
        if brainmask is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        brainmask = bg.unzip_file(brainmask)
        # copy to warp dir
        cmean20 = bg.copy_file(mean20, warpdir)
        cdvr = bg.copy_file(dvr, warpdir)
        cbm = bg.copy_file(brainmask, warpdir)
        # coreg pet to brainmask
        logging.info('Run coreg')
        # cast everything to string
        cbm = str(cbm)
        cmean20 = str(cmean20)
        cdvr = str(cdvr)
        corgout = pp.simple_coregister(cbm, cmean20, other=cdvr)
        if not corgout.runtime.returncode == 0:
            logging.error('coreg pet to mri failed %s'%subid)
            shutil.rmtree(warpdir)
            continue
        rcmean20 = corgout.outputs.coregistered_source
        rdvr = corgout.outputs.coregistered_files
        # warp brainmask to template, apply to dvr
        logging.info('Run warp')
        wout = pp.simple_warp(template, cbm, other=rdvr)
        if not wout.runtime.returncode == 0:
            logging.error('warp to template failed %s'%subid)
            shutil.rmtree(warpdir)
            continue            
        logging.info('Finished warping %s'%subid)
        

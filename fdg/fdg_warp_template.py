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
    Uses specified FDG directory
    finds fdg nifti files
    check number of files
    realigned 6-end to frame 17
    sum 1-5
    coreg summed 1-5 to mean from realign, and apply to each frame
    run qa on scans
    """
    # start wx gui app
    app = wx.App()

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose FDG data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs','%s_%s.log'%(__file__, cleantime))
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'FDG'
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
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        anatdir = os.path.join(sub, 'anatomy')
        if not os.path.isdir(anatdir):
            logging.error('%s doesnt exist,skipping'%(anatdir))
            continue
        tracerdir = os.path.join(sub,'fdg')
        if not os.path.isdir(tracerdir):
            logging.error('%s doesnt exist,skipping'%(tracerdir))
            continue
        # make/check warp dir
        warpdir, exists = utils.make_dir(tracerdir, 'warp_%s'%tname)
        if exists:
            logging.warning('%s exists, remove to rerun'%(warpdir))
            continue
        #get ponsnormed
        globstr = os.path.join(tracerdir, 'ponsnormed_%s*.nii*'%subid)
        pnfdg = pp.find_single_file(globstr)
        if pnfdg is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        pnfdg = pp.unzip_file(pnfdg)
        # get summed fdg
        globstr = os.path.join(tracerdir,  'sum_rB*.nii*')
        sumfdg = pp.find_single_file(globstr)
        if sumfdg is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        sumfdg = pp.unzip_file(sumfdg)        
        # brainmask
        globstr = os.path.join(anatdir, 'brainmask.nii*')
        brainmask = pp.find_single_file(globstr)
        if brainmask is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        brainmask = pp.unzip_file(brainmask)
        # copy to warp dir
        csumfdg = pp.copy_file(sumfdg, warpdir)
        cpnfdg = pp.copy_file(pnfdg, warpdir)
        cbm = pp.copy_file(brainmask, warpdir)
        # coreg pet to brainmask
        logging.info('Run coreg')
        # cast everything to string
        cbm = str(cbm)
        csumfdg = str(csumfdg)
        cpnfdg = str(cpnfdg)
        corgout = pp.simple_coregister(cbm, csumfdg, other=cpnfdg)
        if not corgout.runtime.returncode == 0:
            logging.error('coreg pet to mri failed %s'%subid)
            shutil.rmtree(warpdir)
            continue
        rcsumfdg = corgout.outputs.coregistered_source
        rpnfdg = corgout.outputs.coregistered_files
        # warp brainmask to template, apply to pnfdg
        logging.info('Run warp')
        wout = pp.simple_warp(template, cbm, other=rpnfdg)
        if not wout.runtime.returncode == 0:
            logging.error('warp to template failed %s'%subid)
            shutil.rmtree(warpdir)
            continue            
        logging.info('Finished warping %s'%subid)
        

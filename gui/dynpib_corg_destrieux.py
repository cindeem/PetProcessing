#!/usr/bin/env python
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import preprocessing as pp
import base_gui as bg
import utils
import spm_tools
import logging, logging.config
from time import asctime


def apply_coreg(target, source, xfm):
    apply_out = spm_tools.apply_transform_onefile(xfm, source)
    if not apply_out.runtime.returncode == 0:
        logging.error(apply_out.runtime.stderr)
        return None
    rout_aparc = spm_tools.reslice(target, source)
    if not rout_aparc.runtime.returncode == 0:
        logging.error(rout_aparc.runtime.stderr)
        return None
    else:
        rsource = pp.fname_presuffix(source, prefix='r')
        utils.remove_files([source])
        utils.zip_files([rsource])
        rsource = rsource + '.gz'
        return rsource
    

if __name__ == '__main__':
    """
    finds realigned scans and aligns freesurfer aprac2009aseg (Destrieux
    atlas parcellations) to mean20
    """
    # start wx gui app
    app = wx.App()

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose data dir',
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
    logging.info('###START %s :::'%(__file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)

    subs.sort()
    for sub in subs:
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        # get tracer dir
        tracerdir, exists = utils.make_dir(sub, tracer.lower())
        if not exists:
            logging.error('%s does not exist, skipping'%tracerdir)
            continue
        # find mean and summed
        globstr = os.path.join(tracerdir, 'mean20min_r%s*nii*'%(subid))
        mean = utils.find_single_file(globstr)
        if mean is None:
            globstr = os.path.join(tracerdir,
                                   'realign_QA',
                                   'mean20min_r%s*nii*'%(subid))
            mean = utils.find_single_file(globstr)
 
    
        if mean is None:
            logging.error('%s missing mean20:%s'%(globstr, mean))
            continue
        

        # find aparc.a2009s+aseg (Destrieux atlas)
        ################
        searchstring = os.path.join(mridir,
                                    subid,'mri',
                                    'aparc.a2009s+aseg.mgz')
        aparc = utils.find_single_file(searchstring)
        if aparc is None:
            logging.error('%s not found'%(searchstring))
            continue
        # copy converted parcellation

        pet = utils.unzip_files([mean])
        pet = pet[0]
        _, petnme, _ = utils.split_filename(pet)
        logging.info('coreg ref region to %s'%pet)
        coreg_dir,exists = utils.make_dir(tracerdir,
                                          dirname='coreg_mri2%s'%petnme)
        
        if not exists:
            os.system('rm -rf %s'%coreg_dir) # remove unneeded dir
            coreg_dir, exists = utils.make_dir(tracerdir,
                                               dirname = 'coreg')
        
        if not exists:
            logging.error('no coreg dir found, %s'%coreg_dir)
            continue
        # anatomy
        caparc = pp.move_and_convert(aparc, coreg_dir, 
                                     '%s_destrieux_aparc.nii.gz'%subid)
        caparc = utils.unzip_files([caparc])
        caparc = caparc[0]
        globstr = os.path.join(coreg_dir, '*.mat')
        xfm_file = utils.find_single_file(globstr)
        if xfm_file is None:
            logging.error('%s not found'%globstr)
            continue
        ## Apply transform 
        rcaparc = apply_coreg(pet, caparc, xfm_file)
        utils.zip_files([ pet])

        logging.info( '%s finished coreg destrieux' % subid)

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
import nibabel as ni
  

if __name__ == '__main__':
    """
    50-70 minute SUVR using brainstem, whole and grey cerebellum

    if nframes == 34, use frames[29:33]
    if nframes == 35, use frames[29:33]
    """
    # start wx gui app
    app = wx.App()

    root = bg.SimpleDirDialog(prompt='Choose data dir',
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

        globstr = os.path.join(tracerdir,
                               'realign_QA',
                               'r%s*nii*'%(subid))
        frames = utils.find_files(globstr, 33)

        if frames is None: 
            logging.error('%s missing realigned:%s'%(subid,globstr))
            continue

        # find aparc_aseg in coreg dir
        ###############################
        searchstring = os.path.join(tracerdir,
                                    'coreg*',
                                    'r%s*aparc_aseg.nii*'%(subid))
        aparc = utils.find_files(searchstring, 1)
        if aparc is None:
            logging.error('%s not found'%(searchstring))
            continue
        aparc = aparc[0]
        
        ##### Make Summed
        m50_70 = pp.make_mean_50_70(frames)

        # make SUVR dir
        suvrdir, exists = utils.make_dir(tracerdir, 'SUVR')

        regions = {'grey_cerebellum':[8, 47],
                'whole_cerebellum':[7,8,46,47],
                'brainstem':[16]}
        img50_70 = ni.load(m50_70)
        # ref region norm
        region_vals = pp.mean_from_labels(regions, aparc, img50_70.get_data())
        for ref, mean_val in region_vals.items():
            outfname = os.path.join(suvrdir,
                                    '%s_normed50_70SUVR_%s.nii.gz'%(ref,
                                    subid))
            newvals = img50_70.get_data() / mean_val[0].item() 
            newimg = ni.Nifti1Image(newvals, img50_70.get_affine())
            newimg.to_filename(outfname)
            logging.info('saved %s'%(outfname))

        logging.info( '%s finished suvr norm' % subid)

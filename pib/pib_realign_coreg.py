# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os
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
    logfile = os.path.join(root,'logs',
                           'pib_realign_coreg_%s.log'%(cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START Setup Directory :::')
    logging.info('###TRACER Setup %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    for sub in subs:
        _, subid = os.path.split(sub)

        nifti = glob('%s/pib/%s_PIB*.nii'%(sub, subid))
        nifti.sort()
        if len(nifti) < 34:
            logging.error('%s only has %d frames, RUNBYHAND'%(subid,
                                                              len(nifti)))
            continue

        pth, _ = os.path.split(nifti[0])
        realigndir = os.path.join(pth, 'realign_QA')
        if os.path.isdir(realigndir):
            logging.error('%s exists, remove to rerun'%(realigndir))
            continue
        rlgnout, newnifti = pp.realigntoframe17(nifti)
        tmpparameterfile = rlgnout.outputs.realignment_parameters
        realigndir, _ = os.path.split(tmpparameterfile)
        sum1_5 = pp.make_summed_image(newnifti[:5],
                                      prefix='sum1_5_')
        mean_img = rlgnout.outputs.mean_image
        #coregister 1-5 to mean
        crg_out = pp.simple_coregister(mean_img, sum1_5, newnifti[:5])
        if crg_out.runtime.returncode is not 0:
            logging.error('Failed to coreg 1-5 to mean for  %s' % subid)
            continue
        # grab all realigned files
        allrealigned = crg_out.outputs.coregistered_files + \
                       rlgnout.outputs.realigned_files
        # make new mean files(s) based on fully realigned files
        # 1. first 20 mins for coreg (frames 1-23)
        # 2. 40-60 mins for possible SUVR (frames 28-31)
        mean_20min = pp.make_mean_20min(allrealigned)
        mean_40_60min = pp.make_mean_40_60(allrealigned)

        # QA
        # make 4d for QA
        qadir, exists = qa.make_qa_dir(realigndir, name='data_QA')
        data4d = qa.make_4d_nibabel(allrealigned, outdir=qadir)
        snrimg = qa.gen_sig2noise_img(data4d,qadir)
        artout = qa.run_artdetect(data4d,tmpparameterfile)
        #qa.screen_data_dirnme(data4d, qadir)
        qa.plot_movement(tmpparameterfile, subid)
        qa.calc_robust_median_diff(data4d)

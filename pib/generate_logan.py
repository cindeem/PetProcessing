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
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing/pyga')
import frametimes as ft
import py_logan as pyl
import logging, logging.config
from time import asctime

if __name__ == '__main__':
    """
    Uses specified PIB directory
    finds realigned pib nifti files (realign_QA dir)
    check number of files
    finds coregistered brainmask, and cerebellum (coreg directory)
    generates frametimes from raw pet
    calcs dvr
    
    """
    # start wx gui app
    app = wx.App()

    roifile = '/home/jagust/cindeem/CODE/PetProcessing/pib/fsrois_pibindex.csv'

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs',
                           'pib_%s_%s.log'%(__file__, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START pib generate DVR :::')
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    for sub in subs:
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        pth = os.path.join(sub, tracer.lower())
        # get realigned
        realigndir = os.path.join(pth, 'realign_QA')        
        nifti = glob('%s/r%s_PIB*.nii'%(realigndir, subid))
        nifti.sort()
        if len(nifti) < 34:
            logging.error('%s only has %d frames, RUNBYHAND'%(subid,
                                                              len(nifti)))
            continue
        # get ref and brainmask
        corgdir = os.path.join(pth, 'coreg')
        globstr = '%s/rbrainmask.nii'%(corgdir)
        rbrainmask = pp.find_single_file(globstr)
        if rbrainmask is None:
            logging.error('%s missing, skipping'%(globstr))
            continue
        globstr = '%s/rgrey_cerebellum.nii'%(corgdir)                  
        rcere = pp.find_single_file(globstr)
        if rcere is None:
            logging.error('%s missing, skipping'%(globstr))
            continue
        # get raw
        globstr = os.path.join(sub, 'raw', '*.v')
        ecats = glob(globstr)
        if len(ecats) < 1:
            globstr = os.path.join(sub, 'RawData', tracer, '*.v')
            ecats = glob(globstr)
        if len(ecats) < 1:       
            logging.error('%s missing, skipping'%(globstr))
            continue
        ftimes = ft.frametimes_from_ecats(ecats)
        ftimes = ft.frametimes_to_seconds(ftimes)
        timingf = ft.make_outfile(ecats[0])
        ft.write_frametimes(ftimes, timingf)
        k2ref = 0.15
        range = (35,90)
        logging.info('Running Logan')
        dvrdir, exists = qa.make_qa_dir(pth, name='dvr')
        if exists:
            logging.warning('%s exists, remove to re-run'%(pth + '/dvr'))
            continue
        
        midtimes, durs = pyl.midframes_from_file(timingf)
        data4d = pyl.get_data_nibabel(nifti)
        ref = pyl.get_ref(rcere, data4d)
        ref_fig = pyl.save_inputplot(ref, (midtimes + durs/2.), dvrdir)
        masked_data, mask_roi = pyl.mask_data(rbrainmask, data4d)
        x,y  = pyl.calc_xy(ref, masked_data, midtimes)
        allki, residuals = pyl.calc_ki(x, y, timingf, range=range)
        dvr = pyl.results_to_array(allki, mask_roi)
        resid = pyl.results_to_array(residuals, mask_roi)
    
        outf = pyl.save_data2nii(dvr, rbrainmask,
                                 filename='DVR-%s'%subid, outdir=dvrdir)
        _ = pyl.save_data2nii(resid, rbrainmask,
                              filename = 'RESID-%s'%subid,
                              outdir = dvrdir)
        logging.info('%s Finished Logan: %s'%(subid, outf))
        roid = pp.roilabels_fromcsv(roifile)
        logging.info('PIBINDEX ROI file: %s'%(roifile))
        
        # get raparc
        corgdir = os.path.join(pth, 'coreg')
        globstr = '%s/rB*aparc_aseg.nii'%(corgdir)
        raparc = pp.find_single_file(globstr)
        if raparc is None:
            logging.error('%s missing, unable to get pibindex '%(globstr))
            continue
        meand = pp.mean_from_labels(roid, raparc, dvr)
        csvfile = os.path.join(dvrdir, 'PIBINDEX_%s_%s.csv'%(subid,cleantime))
        pp.meand_to_file(meand, csvfile)

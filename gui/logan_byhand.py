#!/usr/bin/env python
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


import sys, os, shutil
import wx
from glob import glob
import logging, logging.config
from time import asctime
# non standard imports
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import preprocessing as pp
import base_gui as bg
import utils
from fs_tools import (desikan_pibindex_regions, roilabels_fromcsv)
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/pyga')
import py_logan as pyl
import frametimes as ft

def check_selection(inlist, n=1):
    """ given list returned by gui, make sure it has at least n, items
    and if n==1, return just that item"""
    if n is 1: # expecting one file
        try:
            return inlist[0]
        except:
            raise IOError('%s missing, skipping'%(inlist))
    else:
        if  len(inlist) == n:
            return inlist
        else:
            raise IOError('%s only has %d items, some missing'%(inlist,
                                                                len(inlist)))


    
if __name__ == '__main__':

    # start wx gui app
    app = wx.App()
    
    root = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    _, scriptnme = os.path.split(__file__)
    logfile = os.path.join(root,'logs',
                           'pib_%s%s.log'%(scriptnme, cleantime))
    
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START %s :::'%__file__)
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))

    roifile = bg.FilesDialog(prompt='Choose roifile',
                           indir='/home/jagust/cindeem/CODE/PetProcessing/pib')
    nifti = bg.FilesDialog(prompt='Choose realigned ',
                           indir='%s/'%root)
    tracerdir, _ = os.path.split(os.path.split(nifti[0])[0])
    rbrainmask = bg.FilesDialog(prompt = 'Choose rbrainmask',
                                indir = tracerdir)
    raparc =  bg.FilesDialog(prompt = 'Choose raparc',
                             indir = tracerdir)

    timingf = bg.FilesDialog('Choose timing file',
                              indir = tracerdir)
    ref_region = bg.FilesDialog('Choose rRefRegion',
                                indir = tracerdir)

    ## add more data to log
    logging.info('Root Directory : %s'%root)
    logging.info('NIFTIS : %s'%nifti)
    logging.info('ROI file (csv) : %s'%roifile)
    logging.info('Brainmask : %s'%rbrainmask)
    logging.info('APARC file : %s'%raparc)
    logging.info('Timing File : %s'%timingf)
    logging.info('Reference Region : %s'%ref_region)
    
    try: 
        m = pp.re.search('B[0-9]{2}-[0-9]{3}', nifti[0])
        subid = m.group()
    except:
        logging.error('cant find ID in %s'%(nifti[0]))
        raise IOError('cant find ID in %s'%(nifti[0]))
    
    rbrainmask = check_selection(rbrainmask)
    raparc = check_selection(raparc)
    timingf = check_selection(timingf)
    ref_region = check_selection(ref_region)
    ## get frametimes (coerce into sec format)
    ft_sec = ft.read_frametimes(timingf)
    if not ft_sec[-1,1] >  1000.: # times in minutes
        ft_sec = ft_sec.copy() *  60.
    ## get start and end time
    start = bg.singlechoice(['%d'%int(x/60.) for x in ft_sec[:,1]], 
                            text='Start Time (eg 35)')
    # durs stored in -1 start stop duration
    end = bg.singlechoice(['%d'%int(x/60.) for x in ft_sec[:,-1]], 
                             text='End Time (eg 90)')
 
    
    k2ref = 0.15
    range = (int(start),int(end))
    logging.info('Running Logan')
    _, refnme, _ = utils.split_filename(ref_region)
    dvrdir, exists = utils.make_dir(tracerdir, dirname = 'dvr_%s'%refnme)
    if exists:
        logging.warning('%s exists, remove to re-run'%(dvrdir))
        raise IOError('%s exists, remove to re-run'%(dvrdir))

    midtimes, durs = pyl.midframes_from_file(timingf)
    data4d = pyl.get_data_nibabel(nifti)
    ref = pyl.get_ref(ref_region, data4d)
    ref_fig = pyl.save_inputplot(ref, (midtimes + durs/2.), dvrdir)
    masked_data, mask_roi = pyl.mask_data(rbrainmask, data4d)
    x,y  = pyl.calc_xy(ref, masked_data, midtimes)
    allki, allvd, residuals = pyl.calc_ki(x, y, timingf, range=range)
    dvr = pyl.results_to_array(allki, mask_roi)
    resid = pyl.results_to_array(residuals, mask_roi)
    outf = pyl.save_data2nii(dvr, rbrainmask,
                             filename='DVR-%s'%subid, outdir=dvrdir)
    _ = pyl.save_data2nii(resid, rbrainmask,
                          filename = 'RESID-%s'%subid,
                          outdir = dvrdir)    
    
    ## calc logan plot
    labels = desikan_pibindex_regions()
    region = pyl.get_labelroi_data(data4d, raparc, labels)
    pyl.loganplot( ref, region, timingf, dvrdir)
    logging.info('%s Finished Logan: %s'%(subid, outf))
    roid = roilabels_fromcsv(roifile[0])
    

    ## Calc pibindex
    logging.info('PIBINDEX ROI file: %s'%(roifile[0]))
    meand = pp.mean_from_labels(roid, raparc, dvr)
    csvfile = os.path.join(dvrdir, 'PIBINDEX_%s_%s.csv'%(subid,cleantime))
    pp.meand_to_file(meand, csvfile)
     

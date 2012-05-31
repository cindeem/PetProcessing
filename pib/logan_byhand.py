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
import logging, logging.config
from time import asctime
import py_logan as pyl


def singlechoice(options, text='Start Time'):
    dlg = wx.SingleChoiceDialog(None,text, text, options, wx.CHOICEDLG_STYLE)
    if dlg.ShowModal() == wx.ID_OK:
        choice = dlg.GetStringSelection()
    else:
        choice = None
    dlg.Destroy()
    return choice

    
if __name__ == '__main__':

    # start wx gui app
    app = wx.App()
    
    root = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs',
                           'pib_%s%s.log'%(__file__,cleantime))
    
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START pib %s :::'%__file__)
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    
    roifile = bg.FilesDialog(prompt='Choose roifile',
                           indir='/home/jagust/cindeem/CODE/PetProcessing/pib')
    nifti = bg.FilesDialog(prompt='Choose realigned ',
                           indir='%s/'%root)
    try: 
        m = pp.re.search('B[0-9]{2}-[0-9]{3}', nifti[0])
        subid = m.group()
    except:
        logging.error('cant find ID in %s'%(nifti[0]))
        raise IOError('cant find ID in %s'%(nifti[0]))

    realigned_dir , _ = os.path.split(nifti[0])
    pth, _ = os.path.split(realigned_dir)
    # get ref and brainmask
    corgdir = os.path.join(pth, 'coreg')
    globstr = '%s/rbrainmask.nii'%(corgdir)
    rbrainmask = pp.find_single_file(globstr)
    if rbrainmask is None:
        logging.error('%s missing, skipping'%(globstr))
        raise IOError('%s missing, skipping'%(globstr))
    globstr = '%s/rgrey_cerebellum.nii'%(corgdir)                  
    rcere = pp.find_single_file(globstr)
    if rcere is None:
        logging.error('%s missing, skipping'%(globstr))     
    # get timing file
    sub, _ = os.path.split(pth)
    globstr = os.path.join(sub, 'raw', 'frametimes-*.csv')
    timingf = glob(globstr)
    if len(timingf) < 1:
        globstr = os.path.join(sub, 'RawData', tracer, 'frametimes-*.csv')
        timingf = glob(globstr)
    if len(timingf) < 1:       
        logging.error('%s missing, skipping'%(globstr))
        raise IOError('%s missing, skipping'%(globstr))
    timingf = timingf[0]
    ft = ft.read_frametimes(timingf)
    ft_sec = ft.copy() / 60.
    start = singlechoice(['%d'%x for x in ft_sec[:,1]], text='Start Time')
    end = singlechoice(['%d'%x for x in ft_sec[:,-1]], text='End Time')
    k2ref = 0.15
    range = (int(start),int(end))
    logging.info('Running Logan')
    dvrdir, exists = qa.make_qa_dir(pth, name='dvr')
    if exists:
        logging.warning('%s exists, remove to re-run'%(pth + '/dvr'))
        raise IOError('%s exists, remove to re-run'%(pth + '/dvr'))
    midtimes, durs = pyl.midframes_from_file(timingf)
    data4d = pyl.get_data_nibabel(nifti)
    ref = pyl.get_ref(rcere, data4d)
    ref_fig = pyl.save_inputplot(ref, (midtimes + durs/2.), dvrdir)
    masked_data, mask_roi = pyl.mask_data(rbrainmask, data4d)
    x,y  = pyl.calc_xy(ref, masked_data, midtimes)
    allki, residuals = pyl.calc_ki(x, y, timingf, range=range)
    dvr = pyl.results_to_array(allki, mask_roi)

    outf = pyl.save_data2nii(dvr, rbrainmask,
                             filename='DVR-%s'%subid, outdir=dvrdir)
    logging.info('%s Finished Logan: %s'%(subid, outf))
    roid = pp.roilabels_fromcsv(roifile[0])
    logging.info('PIBINDEX ROI file: %s'%(roifile[0]))

    # get raparc
    corgdir = os.path.join(pth, 'coreg')
    globstr = '%s/rB*aparc_aseg.nii'%(corgdir)
    raparc = pp.find_single_file(globstr)
    if raparc is None:
        logging.error('%s missing, unable to get pibindex '%(globstr))
        raise IOError('%s missing, unable to get pibindex '%(globstr))
    meand = pp.mean_from_labels(roid, raparc, dvr)
    csvfile = os.path.join(dvrdir, 'PIBINDEX_%s_%s.csv'%(subid,cleantime))
    pp.meand_to_file(meand, csvfile)
     

# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
import base_gui as bg
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing/pvc')
import metzler
import logging, logging.config
from time import asctime

if __name__ == '__main__':
    """Uses specified subject dir
    finds dvr dir
    find aparc_aseg in pet space
    makes brainmask
    runs ecat_smooth
    creates pvc directory with pvc corrected data
    """
    # start wx gui app
    app = wx.App()

    roifile = bg.FileDialog(prompt='Choose fsroi csv file',
                            indir ='/home/jagust/cindeem/CODE/PetProcessing')

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(__file__, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START %s %s :::'%(tracer, __file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    roid = pp.roilabels_fromcsv(roifile)
    alld = {}
    for sub in subs:
        if 'v2' in sub:
            logging.info('Skipping visit 2 %s'%(sub))
            continue
        _, fullsubid = os.path.split(sub)
        try:
            m = pp.re.search('B[0-9]{2}-[0-9]{3}_v[0-9]',fullsubid)
            subid = m.group()
        except:
            logging.error('cant find ID in %s'%fullsubid)
            continue
        logging.info('%s'%subid)
        pth = os.path.join(sub, tracer.lower())
        dvrdir  = os.path.join(pth, 'dvr')
        if not os.path.isdir(dvrdir):
            logging.error('%s missing. skipping'%(dvrdir))
            continue
        pvcdir, exists = bg.make_dir(dvrdir, 'pvc_metzler')
        if not exists:
            logging.error('%s missing, skipping'%(pvcdir))
            continue
        # get pvc dvr
        globstr = '%s/pvcfs_DVR-%s*nii*'%(pvcdir,subid)                  
        dvr = pp.find_single_file(globstr)
        if dvr is None:
            logging.error('%s missing, skipping'%(globstr))
            continue
        # get raparc
        corgdir = os.path.join(pth, 'coreg')
        globstr = '%s/rB*aparc_aseg.nii'%(corgdir)
        raparc = pp.find_single_file(globstr)
        if raparc is None:
            logging.error('%s missing, skipping '%(globstr))
            continue
        dvr_data = pp.nibabel.load(dvr).get_data()
        meand = pp.mean_from_labels(roid, raparc, dvr_data)
        #csvfile = os.path.join(dvrdir, 'PIBINDEX_%s_%s.csv'%(subid,cleantime))
        #pp.meand_to_file(meand, csvfile)
        alld[subid] = meand

    ###write to file
    fid =open('pvc_metzler_OLD_PIBINDEX_%s'%(cleantime), 'w+')
    fid.write('SUBID,')
    rois = sorted(meand.keys())
    roiss = ','.join(rois)
    fid.write(roiss)
    fid.write(',\n')
    for subid in sorted(alld.keys()):
        fid.write('%s,'%(subid))
        for r in rois:
            fid.write('%f,'%(alld[subid][r][0]))
        fid.write(',\n')
    fid.close()
                      


        

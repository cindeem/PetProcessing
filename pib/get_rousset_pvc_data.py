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
import rousset
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
    logging.info('###START %s :::'%(__file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)

    datad = {}
    for sub in subs:
        
        _, fullsubid = os.path.split(sub)
        try:
            m = pp.re.search('B[0-9]{2}-[0-9]{3}',fullsubid)
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
        pvcdir, exists = utils.make_dir(dvrdir, 'pvc_rousset')
        if not exists:
            logging.error('%s does not exist, skipping'%(pvcdir))
            continue
        globstr = '%s/rB*aparc_aseg.nii'%(pvcdir)
        craparc = pp.find_single_file(globstr)
        if craparc is None:
            logging.error('%s missing, skipping '%(globstr))
            continue
        
        transferf = os.path.join(pvcdir, 'transfer_matrix.npy')
        try:
            transfer_mtx = rousset.np.load(transferf)
        except:
            logging.error('%s missing, skipping'%(transferf))
            continue
        obsf = os.path.join(pvcdir, 'observed.npy')
        try:
            obs = rousset.np.load(obsf)
        except:
            logging.error('%s missing, skipping'%(obsf))
            continue
        logging.info('Finished %s'%(subid))
        correct = rousset.calc_pvc_values(transfer_mtx,obs)
        datad[subid] = correct

    #write to file
    outfile = os.path.join(root, 'pvc_rousset_%s.csv'%(cleantime))
    with open(outfile, 'w+') as fid:
        fid.write('SUBID, GM, WM, PIBINDEX,\n')
        for subid in sorted(datad.keys()):
            gm,wm,pi = datad[subid]
            fid.write('%s,'%(subid))
            fid.write('%f,'%(gm))
            fid.write('%f,'%(wm))
            fid.write('%f,'%(pi))
            fid.write('\n')
    logging.info('wrote %s'%(outfile))

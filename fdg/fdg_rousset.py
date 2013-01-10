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
    root = bg.SimpleDirDialog(prompt='Choose FDG data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(__file__, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    tracer = 'FDG'
    user = os.environ['USER']
    logging.info('###START %s :::'%(__file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    for sub in subs:
        if '_v2' in sub:
            logging.info('skipping visit2 %s'%(sub))
            continue
        
        _, fullsubid = os.path.split(sub)
        try:
            m = pp.re.search('B[0-9]{2}-[0-9]{3}',fullsubid)
            subid = m.group()
        except:
            logging.error('cant find ID in %s'%fullsubid)
            continue
        logging.info('%s'%subid)
        # subjects tracer specific path
        pth = os.path.join(sub, tracer.lower())
        
        pvcdir, exists = pp.make_dir(dvrdir, 'pvc_rousset')
        if exists:
            logging.error('%s exists, remove to re-run'%(pvcdir))
            continue
        # get pons normed
        globstr = '%s/nonan-ponsnormed_%s*nii*'%(pth,subid)                  
        ponsnormd = pp.find_single_file(globstr)
        if ponsnormd is None:
            logging.error('%s missing, skipping'%(globstr))
            continue
        # copy ponsnormd to pvc directory
        cponsnormd = pp.copy_file(ponsnormd, pvcdir)
        # get raparc
        corgdir = os.path.join(pth, 'coreg_mri2fdg')
        globstr = '%s/rB*aparc_aseg.nii'%(corgdir)
        raparc = pp.find_single_file(globstr)
        if raparc is None:
            logging.error('%s missing, skipping '%(globstr))
            continue
        #copy raparc_aseg to pvd dir
        craparc = pp.copy_file(raparc, pvcdir)
        # make brainamsk
        wm,gm,pibi = rousset.generate_pibindex_rois_fs(craparc)
        wmf = pp.fname_presuffix(craparc, prefix='wm_')
        gmf = pp.fname_presuffix(craparc, prefix='gm_')
        pibif = pp.fname_presuffix(craparc, prefix='pibindex_')
        aff = rousset.ni.load(craparc).get_affine()
        rousset.to_file(wm, aff, wmf)
        rousset.to_file(gm, aff, gmf)
        rousset.to_file(pibi, aff, pibif)
        rois = [gmf, wmf, pibif]
        rsfs = rousset.compute_rsf(rois)
        transfer_mtx = rousset.gen_transfer_matrix(rsfs, rois)
        obs = rousset.get_observed_conc(cponsnormd, rois)
        transferf = os.path.join(pvcdir, 'transfer_matrix')
        rousset.np.save(transferf, transfer_mtx)
        obsf = os.path.join(pvcdir, 'observed')
        rousset.np.save(obsf, obs)
        logging.info('Created %s'%(pvcdir))
        

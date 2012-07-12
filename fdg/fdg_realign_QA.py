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
    realignes to first
    sum 1-5
    run qa on scans
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

    subs.sort()
    for sub in subs:
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        # find fdg nifti files
        globstr = os.path.join(sub, tracer.lower(), '%s_%s*'%(subid, tracer))
        nifti = bg.glob(globstr)
        
        if len(nifti) < 5:
            logging.warning('fdg frames not found or too few for %s  skipping'%(subid))
            continue
        nifti.sort()
        
        rlgnout, newnifti = pp.realigntoframe1(nifti)
        if rlgnout is None and newnifti is None:
            logging.warning('existing realign_QA dir for %s remove to re-run'%(subid))
            continue
        if rlgnout.runtime.returncode is not 0:
            logging.warning('Failed to realign %s' % subid)
            continue
        tmprealigned = rlgnout.outputs.realigned_files
        tmpmean = rlgnout.outputs.mean_image
        tmpparameterfile = rlgnout.outputs.realignment_parameters

        logging.info( 'realigned %s' % subid)

        # make final mean image
        meanimg = pp.make_summed_image(tmprealigned)
            
        # move data back to main directory
        nifti_dir,_ = os.path.split(nifti[0])
        movedmean = bg.copy_file(meanimg, nifti_dir)

        #QA
        logging.info( 'qa %s' % subid)
        qa.plot_movement(tmpparameterfile,subid)
        # get rid of NAN in files
        no_nanfiles = pp.clean_nan(tmprealigned)
        #make 4d volume to visualize movement
        img4d = qa.make_4d_nibabel(no_nanfiles)
            
        #save qa image
        #qa.save_qa_img(img4d)
        qa.plot_movement(tmpparameterfile, subid)
        qa.calc_robust_median_diff(img4d)
        qa.screen_pet(img4d) 
        #remove tmpfiles
        
        bg.remove_files(no_nanfiles)
        bg.remove_files(newnifti)
            

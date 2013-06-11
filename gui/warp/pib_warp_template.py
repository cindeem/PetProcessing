# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import preprocessing as pp
import base_gui as bg
import utils
import fsl_tools
import spm_tools
import logging, logging.config
from time import asctime

if __name__ == '__main__':
    """
    warp aprarc masked brain tospecified template
    apply to pet

    """
    # start wx gui app
    app = wx.App()

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs','%s_%s.log'%(__file__, cleantime))
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START %s :::'%(__file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)

    # choose template
    template = bg.FilesDialog(prompt='Choose template',
                           indir='/home/jagust/cindeem/TEMPLATES')
    logging.info('Template: %s'%(template[0]))
    template = str(template[0])
    _, tname, _ = pp.split_filename(template)
                 
    # text dialog to get the mean20minute pib and dvr 
    mean20_glob = bg.TextEntry(message='Glob for mean20minute pseudo anat file',
                                 default = 'mean20min*')
    logging.info(mean20_glob)

    dvrdir_glob = bg.TextEntry(message='Glob for dvr dirrectory',
                               default = 'dvr_rgrey_cerebellum')
    logging.info(dvrdir_glob)


    for sub in subs:
        if '_v2' in sub:
            logging.info('skipping visit2 %s'%(sub))
            continue
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        anatdir = os.path.join(sub, 'anatomy')
        if not os.path.isdir(anatdir):
            logging.error('%s doesnt exist,skipping'%(anatdir))
            continue
        dvrdir = os.path.join(sub,'pib',dvrdir_glob)
        dvrdir = glob(dvrdir)
        
        if len(dvrdir) < 1:
            logging.error('%s doesnt exist,skipping'%(dvrdir))
            continue
        dvrdir = dvrdir[0]
        # make/check warp dir
        warpdir, exists = utils.make_dir(dvrdir, 'warp_%s'%tname)
        if exists:
            logging.warning('%s exists, remove to rerun'%(warpdir))
            continue
        #get dvr, brainmask
        globstr = os.path.join(dvrdir, 'DVR-%s*.nii*'%subid)
        dvr = utils.find_single_file(globstr)
        if dvr is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        dvr = utils.unzip_file(dvr)
        # get mean 20 minute pib
        globstr = os.path.join(sub,'pib', 'realign_QA', mean20_glob)
        mean20 = utils.find_single_file(globstr)
        if mean20 is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        mean20 = utils.unzip_file(mean20)        
        # brainmask
        globstr = os.path.join(anatdir, 'brainmask.nii*')
        brainmask = utils.find_single_file(globstr)
        if brainmask is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        # copy to warp dir
        cmean20 = utils.copy_file(mean20, warpdir)
        cdvr = utils.copy_file(dvr, warpdir)
        cbm = utils.copy_file(brainmask, warpdir)
        # Mask brainmask with aparc to remove skull
        globstr = os.path.join(anatdir, '%s*aparc_aseg.nii*'%subid)
        aparc = utils.find_single_file(globstr)
        sscbm = fsl_tools.fsl_mask(cbm, aparc,
                                    outname = 'aparcmasked_brainmask.nii.gz')
        sscbm = utils.unzip_file(sscbm)
        # coreg pet to brainmask
        logging.info('Run coreg')
        # cast everything to string
        sscbm = str(sscbm)
        cmean20 = str(cmean20)
        cdvr = str(cdvr)
        corgout = spm_tools.simple_coregister(sscbm, cmean20, other=[cdvr])
        if not corgout.runtime.returncode == 0:
            logging.error('coreg pet to mri failed %s'%subid)
            shutil.rmtree(warpdir)
            continue
        rcmean20 = corgout.outputs.coregistered_source
        rdvr = corgout.outputs.coregistered_files
        # warp brainmask to template, apply to dvr
        logging.info('Run warp')
        wout = spm_tools.simple_warp(template, sscbm, other=[rdvr])
        if not wout.runtime.returncode == 0:
            logging.error('warp to template failed %s'%subid)
            shutil.rmtree(warpdir)
            continue            
        logging.info('Finished warping %s'%subid)
        

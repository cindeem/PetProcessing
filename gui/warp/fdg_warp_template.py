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
    root = bg.SimpleDirDialog(prompt='Choose FDG data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    _, scriptnme = os.path.split(__file__)
    logfile = os.path.join(root,'logs','%s_%s.log'%(scriptnme, cleantime))
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'FDG'
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
                 

    # text dialog to get normed FDG file and coreg directory
    norm_fdg_glob = bg.TextEntry(message='Enter Ref-normed FDG glob',
                                 default = 'rpons_tunormed_mean*')
    logging.info(norm_fdg_glob)



    for sub in subs:
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        anatdir = os.path.join(sub, 'anatomy')
        if not os.path.isdir(anatdir):
            logging.error('%s doesnt exist,skipping'%(anatdir))
            continue
        tracerdir = os.path.join(sub,'fdg')
        if not os.path.isdir(tracerdir):
            logging.error('%s doesnt exist,skipping'%(tracerdir))
            continue
        #get ponsnormed
        globstr = os.path.join(tracerdir, norm_fdg_glob)
        pnfdg = utils.find_single_file(globstr)
        if pnfdg is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        pnfdg = utils.unzip_file(pnfdg)
        # get summed fdg
        if 'mean' in norm_fdg_glob:
            tmp_glob = 'mean_rB*.nii*'
        else:
            tmp_glob = 'sum_rB*.nii*'
        globstr = os.path.join(tracerdir,  tmp_glob)
        sumfdg = utils.find_single_file(globstr)
        if sumfdg is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        sumfdg = utils.unzip_file(sumfdg)        
        # make/check warp dir
        (warpdir,
         exists) = utils.make_dir(tracerdir,
                                  'warp_%s_%s'%(norm_fdg_glob.replace('*',''),
                                                tname))
        if exists:
            logging.warning('%s exists, remove to rerun'%(warpdir))
            continue

        # brainmask
        globstr = os.path.join(anatdir, 'brainmask.nii*')
        brainmask = utils.find_single_file(globstr)
        if brainmask is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue
        brainmask = utils.unzip_file(brainmask)
        ## aparc
        globstr = os.path.join(anatdir, 'B*aparc_aseg.nii*')
        aparc = utils.find_single_file(globstr)
        if aparc is None:
            logging.error('%s not found. skipping'%globstr)
            shutil.rmtree(warpdir)
            continue

        # copy to warp dir
        csumfdg = utils.copy_file(sumfdg, warpdir)
        cpnfdg = utils.copy_file(pnfdg, warpdir)
        cbm = utils.copy_file(brainmask, warpdir)
        caparc = utils.copy_file(aparc, warpdir)

        # Mask brainmask with aparc to remove skull
        globstr = os.path.join(anatdir, '%s*aparc_aseg.nii*'%subid)
        aparc = utils.find_single_file(globstr)
        sscbm = fsl_tools.fsl_mask(cbm, aparc,
                            outname = 'aparcmasked_brainmask.nii.gz')
        sscbm = utils.unzip_file(sscbm)

        # coreg pet to masked brainmask
        logging.info('Run coreg')
        # cast everything to string
        sscbm = str(sscbm)
        csumfdg = str(csumfdg)
        cpnfdg = str(cpnfdg)
        corgout = spm_tools.simple_coregister(sscbm, csumfdg, other=[cpnfdg])
        if not corgout.runtime.returncode == 0:
            logging.error('coreg pet to mri failed %s'%subid)
            shutil.rmtree(warpdir)
            continue
        rcsumfdg = corgout.outputs.coregistered_source
        rpnfdg = corgout.outputs.coregistered_files
        # warp brainmask to template, apply to pnfdg
        logging.info('Run warp')
        wout = spm_tools.simple_warp(template, sscbm, other= [rpnfdg])
        if not wout.runtime.returncode == 0:
            logging.error('warp to template failed %s'%subid)
            shutil.rmtree(warpdir)
            continue            
        ## zip files
        cmd = 'gzip %s/*.nii'%warpdir
        out = utils.CommandLine(cmd).run()
        if out.runtime.returncode == 0:
            logging.info('zipped files in %s'%warpdir)
        else:
            logging.warn('zipping failed for files in %s'%warpdir)
        logging.info('Finished warping %s'%subid)
               

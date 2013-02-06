# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-refactor/preprocessing')
import preprocessing as pp
import base_gui as bg
import utils
import qa
import spm_tools
import fsl_tools
import logging, logging.config
from time import asctime

    
if __name__ == '__main__':
    """
    AV45
    align 4 frames (only if not done)
    segments pet
    applies inverse warp to ref region
    
    """
    # start wx gui app
    app = wx.App()
    
    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose data dir',
                              indir = '/home/jagust/cindeem/CODE')

    template = bg.FileDialog(prompt = 'Choose Template',
                             indir = '/home/jagust/cindeem/CODE/ucsf')
    template_pth, _ = os.path.split(template)
    ref = bg.FileDialog(prompt = 'Choose Ref Region',
                        indir = template_pth)
    _, ref_name, _ = utils.split_filename(ref)
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(__file__, cleantime))
    
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    tracer = bg.MyTracerDialog()
    
    user = os.environ['USER']
    logging.info('###START %s :::'%(__file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###Template %s :::'%(template))
    logging.info('###USER : %s'%(user))


    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='/home/jagust/cindeem/CODE/test_preproc')
    #os.path.abspath(root))
    

    fsl_info = fsl_tools.fsl.Info()
    fsl_ext = fsl_info.output_type_to_ext(fsl_info.output_type())
    for sub in subs:
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        tracerdir = os.path.join(sub, tracer.lower())
        globstr = os.path.join(tracerdir, 'sum*%s*%s*.nii*'%(subid,
                                                             tracer))
        sum = utils.find_single_file(globstr)
        if sum is None:
            logging.error('%s not found'%globstr)
            continue
        sum = utils.unzip_file(sum)
        
        ### COREG TO TEMPLATE  ###
        corgdir, exists = utils.make_dir(tracerdir, 'petonly_pet2mri')
        if exists:
            logging.info('%s exists, remove to re-run'%(corgdir))
            continue
        csum = utils.copy_file(sum, corgdir)
        utils.zip_files([sum])

        xfm = spm_tools.make_transform_name( template, csum, inverse=False)
        corgout = spm_tools.forward_coreg(template, csum, xfm)
        if not corgout.runtime.returncode == 0:
            logging.info('COREG FAIL: %s'%(corgout.runtime.stderr))
            continue            
        reslice_out = spm_tools.reslice(template, csum)
        if not reslice_out.runtime.returncode == 0:
            logging.info('COREG FAIL: %s'%(reslice_out.runtime.stderr))
            continue
        corgsum = utils.fname_presuffix(csum, prefix = 'r')
        ###  SEGMENT coregistered sum ####
        segdir, exists = utils.make_dir(tracerdir, 'petonly_segment')
        if exists:
            logging.info('%s exists, remove to re-run'%(segdir))
            continue        
        ccorgsum = utils.copy_file(corgsum, segdir)
        
        ### Make mask using coreg petfile
        petmaskf = os.path.join(segdir, 'petmask' + fsl_ext)
        petmaskf = fsl_tools.fsl_maths(ccorgsum, opstr = '-thr 100',
                                       outfile = petmaskf)
        petmask = utils.unzip_file(petmaskf)
        segout = spm_tools.seg_pet(ccorgsum, petmask)
        if not segout.runtime.returncode == 0:
            logging.info('SEG FAIL: %s'%(corgout.runtime.stderr))
            continue              
        gm = segout.outputs.native_gm_image
        wm = segout.outputs.native_wm_image
        inv_xfm = segout.outputs.inverse_transformation_mat
        ### Warp Ref Region to PET
        refdir, exists = utils.make_dir(tracerdir, 'petonly_ref')
        if exists:
            logging.info('%s exists, remove to re-run'%(segdir))
            continue        
        cref = utils.copy_file(ref, refdir)
        cref = utils.unzip_file(cref)
        wout = spm_tools.apply_warp_fromseg([cref], inv_xfm)
        if not wout.runtime.returncode == 0:
            logging.info(wout.runtime.returncode)
            continue
        wref = wout.outputs.normalized_files
        binwref = utils.fname_presuffix(wref, prefix='bin_',
                                        suffix = fsl_ext,
                                        use_ext = False)
                                        
        binwref = fsl_tools.fsl_maths(wref, opstr = '-nan -thr .1 -bin',
                                       outfile = binwref)
        binwref = utils.unzip_file(binwref)
        
        outf = os.path.join(tracerdir, '%s_%s_%s_normed.nii'%(subid,
                                                              tracer,
                                                              ref_name))
        pp.make_pons_normed(corgsum, binwref, outf)
        logging.info('wrote %s'%outf)
        ## Cleanup
        utils.remove_files([csum, ccorgsum,
                            segout.outputs.modulated_input_image,
                            cref, wref])
                            
        utils.zip_files([corgsum, petmask, gm, wm, binwref])  

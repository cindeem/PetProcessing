# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preprocessing')
import preprocessing as pp
import base_gui as bg
import utils
import qa
import spm_tools
import fsl_tools
import seg_em
import logging, logging.config
from time import asctime

def get_mean(subid, tracerdir, tracer):
    globstr = os.path.join(tracerdir, 'mean*%s*%s*.nii*'%(subid,
                                                         tracer))
    sum = utils.find_single_file(globstr)
    if sum is None:
        logging.error('%s not found'%globstr)
        return None
    sum = utils.unzip_file(sum)
    return sum


def corg_2_template(sum, corgdir):
    csum = utils.copy_file(sum, corgdir)
    utils.zip_files([sum])

    xfm = spm_tools.make_transform_name( template, csum, inverse=False)
    corgout = spm_tools.forward_coreg(template, csum, xfm)
    if not corgout.runtime.returncode == 0:
        logging.info('COREG FAIL: %s'%(corgout.runtime.stderr))
        return None
    reslice_out = spm_tools.reslice(template, csum, interp=1)
    if not reslice_out.runtime.returncode == 0:
        logging.info('Reslice FAIL: %s'%(reslice_out.runtime.stderr))
        return None
    utils.remove_files([csum])
    corgsum = utils.fname_presuffix(csum, prefix = 'r')
    return corgsum

def warp(corgsum, template, warpdir):
    ccorgsum = utils.copy_file(corgsum, warpdir)
        
    ### Make mask using coreg petfile
    petmaskf = os.path.join(warpdir, 'petmask' + fsl_ext)
    petmaskf = fsl_tools.fsl_maths(ccorgsum, opstr = '-thr 100 -bin',
                                   outfile = petmaskf)
    petmask = utils.unzip_file(petmaskf)
    warpout = spm_tools.simple_warp(template, ccorgsum, source_weight=petmask)
    utils.zip_files([petmask])
    utils.remove_files([ccorgsum])
    if not warpout.runtime.returncode == 0:
        logging.info('WARP FAIL: %s'%(corgout.runtime.stderr))
        return None    
    return warpout

def warp_ref(ref, refdir, pet, snmat):
    cref = utils.copy_file(ref, refdir)
    cref = utils.unzip_file(cref)

    out = spm_tools.invert_warp(pet, snmat, cref)
    if not out.runtme.returncode == 0:
        logging.error(out.runtime.stderr)
        return None
    wref = utils.fname_presuffix(cref, prefix = 'w')
    utils.remove_files([cref])
    utils.zip_files([wref])
    return wref + '.gz'


def segment_pet(corgmean, segdir):
    ccorgmean = utils.copy_file(corgmean, segdir)
    segfile = seg_em.main(ccorgmean)
    # create mask
    img = ni.load(segfile)
    dat = img.get_data()
    newdat = np.zeros(dat.shape)
    newdat[dat == 2] = 1
    newimg = ni.Nifti1Image(newdat, img.get_affine(), ni.Nifti1Header())
    outf = utils.fname_presuffix(ccorgmean, prefix = 'c1_')
    newimg.to_filename(outf)
    return outf

def mask_ref(wref, gm):
    refd = ni.load(wref).get_data()
    gmd = ni.load(gm).get_data()
    if not refd.shape == gmd.shape:
        logging.error('Shape mismatch in mask, ref: %s , mask%s'%(refd.shape,
                                                                  gmd.shape))
        return None
    newmask = np.zeros(refd.shape)
    newmask[np.logical_and(refd>0, gmd>0)] = 1
    newimg = ni.Nifti1Image(newmask, ni.load(wref).get_affine())
    fname = utils.fname_presuffix(wref, prefix='mask_')
    newimg.to_filename(fname)
    return fname
    
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
                              indir = '/home/jagust')

    template = bg.FileDialog(prompt = 'Choose Template',
                             indir = '/home/jagust/cindeem/TEMPLATES')
    template_pth, template_nme, _  = utils.split_filename(template)
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
                         indir=root)
    #os.path.abspath(root))
    

    fsl_info = fsl_tools.fsl.Info()
    fsl_ext = fsl_info.output_type_to_ext(fsl_info.output_type())
    for sub in subs:
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        tracerdir = os.path.join(sub, tracer.lower())
        mean = get_mean(subid, tracerdir, tracer)
        if mean is None:
            continue
        ### COREG TO TEMPLATE  ###
        corgdir, exists = utils.make_dir(tracerdir,
                                         'petonly_coreg2_%s'%template_nme)
        if exists:
            logging.info('%s exists, remove to re-run'%(corgdir))
            continue
        corgmean  = corg_2_template(mean, corgdir)
        if corgmean is None:
            continue
        ###  warp coregistered mean ####
        warpdir, exists = utils.make_dir(tracerdir,
                                        'petonly_%s_warp'%template_nme)
        if exists:
            logging.info('%s exists, remove to re-run'%(warpdir))
            continue        
        warpout = warp(corgmean, template, warpdir)
        if warpout is None:
            continue
        snmat = warpout.outputs.normalization_parameters
        wcorgmean = warpout.outputs.normalized_source

        ### Warp Ref Region to PET
        refdir, exists = utils.make_dir(tracerdir,
                                        'petonly_%s_ref'%template_nme)
        if exists:
            logging.info('%s exists, remove to re-run'%(refdir))
            continue        
        wref = warp_ref(ref, refdir, corgmean, snmat)
        if wref is None:
            continue

        ## EM segmentation
        segdir, exists = utils.make_dir(tracerdir,
                                        'petonly_%s_EMsegment'%template_nme)
        if exists:
            logging.info('%s exists, remove to re-run'%(segdir))
            continue
        gm = segment_pet(corgmean, segdir)
        ### Create ref normalized Image
        binwref = mask_ref(wref, gm)
        outf = os.path.join(tracerdir, '%s_%s_%s_%s_normed.nii'%(subid,
                                                                 tracer,
                                                                 template_nme,
                                                                 ref_name))
        pp.make_pons_normed(corgmean, binwref, outf)
        logging.info('wrote %s'%outf)

        ## Cleanup
        utils.zip_files([corgmean, gm, wm, binwref, outf])  

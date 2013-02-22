# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os, sys
import preprocessing as pp
import utils
from nipype.interfaces.base import  CommandLine
import nipype.interfaces.fsl as fsl
from nipype.utils.filemanip import split_filename


def remove_nan(files):
    """ FSL maths to remove nan form files"""
    outfiles = []
    for file in files:
        imaths = fsl.ImageMaths()
        imaths.inputs.in_file = file
        imaths.inputs.op_string = '-nan'
        imaths.inputs.suffix = 'nan'
        iout = imaths.run()
        if iout.runtime.returncode == 0:
            outfiles.append(iout.outputs.out_file)
        else:
            print iout.runtime.stderr
    if len(outfiles) == len(files):
        return outfiles
    else:
        return None

def skull_strip(infile, frac = 0.7, grad = -0.5):
    """ BET to skull strip
    frac default(.7) [ 0 (big outline -> 1 (small outline)]
    vertical_gradient default(-0.5) [ -1 large top, small bottom -> 
                                       1 small top, large bottom]
    """
    ss = fsl.BET()
    ss.inputs.in_file = infile
    ss.inputs.frac =frac
    ss.inputs.vertical_gradient = grad
    ssout = ss.run()
    if ssout.runtime.returncode == 0:
        return ssout.outputs.out_file
    else:
        print ssout.runtime.stderr
        return None

def flirt_coreg(infile, target):
    """Flirt generate xfm and move infile -> target"""
    flrt = fsl.FLIRT()
    pth, nme, ext = split_filename(infile)
    _, tnme, ext = split_filename(target)
    xfm = os.path.join(pth, nme + '_TO_' + tnme + '.xfm')
    flrt.inputs.in_file = infile
    flrt.inputs.reference = target
    flrt.out_matrix_file = xfm
    fout = flrt.run()
    if fout.runtime.returncode == 0:
        return fout.outputs.out_matrix_file, fout.outputs.out_file
    else:
        print fout.runtime.stderr
        return None

def fsl_maths(infile, opstr, suffix='fslmaths', outfile = None):
    """ Run fslmaths on infile
    specify optional outfile
    returns outfile"""
    
    imaths = fsl.ImageMaths()
    imaths.inputs.in_file = infile
    imaths.inputs.op_string = opstr
    if suffix is not None:
        imaths.inputs.suffix = suffix
    if outfile is not None:
        imaths.inputs.out_file = outfile
    iout = imaths.run()
    if iout.runtime.returncode == 0:
        return iout.outputs.out_file
    else:
        print iout.runtime.stderr
        return None


def fsl_warp(infile, reference,mask ):
    """ Fnirt for nonlinear warp
    infile = moving volume
    reference = target
    mask = mask to restrict missing data etc
    Returns
    -------
    warpd : image that has been warped
    warp_file:  warp coefficients file

    Notes
    -----
    assumes mri is in register with reference"""
    
    pth, nme, ext = split_filename(infile)
    aff_file = '/home/jagust/UCSF/Templates/eye.mat'
    fnrt = fsl.FNIRT()
    fnrt.inputs.in_file = infile
    fnrt.inputs.ref_file = reference
    fnrt.inputs.inmask_file = mask
    fnrt.inputs.ref_fwhm = [8,4,0]
    fnrt.inputs.affine_file = aff_file
    fnrt.inputs.subsampling_scheme = [8,4,2]
    fnrt.inputs.max_nonlin_iter = [5,5,10]
    fnrt.inputs.ref_fwhm = [8,4,0]
    fnrt.inputs.in_fwhm = [10,6,2]
    fnrt.inputs.args = '--estint=1,1,0'
    fnrt.inputs.apply_inmask = [0,1,1]
    fnrt.inputs.apply_refmask = [0,0,0]
    fout = fnrt.run()
    if fout.runtime.returncode == 0:
        warpd = pp.glob('%s/*warped*'%(pth))[0]
        warp_file = pp.glob('%s/*warpcoef*'%(pth))[0]
        return warpd, warp_file
    else:
        print fout.runtime.stderr
        return None, None


def invert_warp(warpvol, reference):
    """ inverts warp field
    returns file holding result
    """
    
    pth, nme, ext = split_filename(warpvol)
    outfile = os.path.join(pth, 'INV-'+ nme + ext)
    cmd = 'invwarp -w %s -o %s -r %s'%(warpvol,
                                       outfile,
                                       reference)
    out = CommandLine(cmd).run()
    if out.runtime.returncode == 0:
        return outfile
    else:
        print out.runtime.stderr
        return None


def apply_warp(infile, reference, warpfile, outfile):
    """ apply warpfile, to infile relsicing to refence and saving as
    outfile"""
    
    cmd = 'applywarp -i %s -o %s -r %s -w %s'%(infile,
                                               outfile,
                                               reference,
                                               warpfile)
    out = CommandLine(cmd).run()
    if out.runtime.returncode == 0:
        return outfile
    else:
        print out.runtime.stderr
        return None


def invert_xfm(xfm):
    """ invert transform"""
    inv = fsl.ConvertXFM()
    inv.inputs.in_file = xfm
    inv.inputs.invert_xfm = True
    out = inv.run()
    if out.runtime.returncode == 0:
        return out.outputs.out_file
    else:
        print out.runtime.stderr
        return None

def apply_xfm(infile, reference, xfm):
    """apply transform to infile writing like reference"""
    axfm = fsl.ApplyXfm()
    axfm.inputs.in_file = infile
    axfm.inputs.reference = reference
    axfm.inputs.in_matrix_file = xfm
    axfm.inputs.apply_xfm = True
    out = axfm.run()
    if out.runtime.returncode == 0:
        return out.outputs.out_file
    else:
        print out.runtime.stderr
        return None
   
def erode(infile, niter=1):
    """ fslmaths to erode an image"""
    pth, nme, ext = split_filename(infile)
    outfile = os.path.join(pth, 'ero'+nme+ext)
    cmd = 'fslmaths %s -ero %s'%(infile, outfile)
    out = CommandLine(cmd).run()
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return None
    if niter > 1:
        for i in range(niter-1):
            cmd = 'fslmaths %s -ero %s'%(outfile, outfile)            
            out = CommandLine(cmd).run()
            if not out.runtime.returncode == 0:
                print out.runtime.stderr
                return None
    return outfile

def fsl_split4d(in4d, basenme = None):
    cwd = os.getcwd()
    pth, nme, ext = split_filename(in4d)
    if basenme is None:
        basenme = nme
    os.chdir(pth)
    split = fsl_split()
    split.inputs.in_file = in4d
    split.inputs.dimension = 't'
    split.inputs.out_base_name = basenme
    split_out = split.run()
    os.chdir(cwd)
    if not split_out.runtime.returncode == 0:
        logging.error('Failed to split 4d file %s'%in4d)
        return None
    else:
        return split_out.outputs.out_files
    
    return pth   


def extract_stats_fsl(data, mask, gmmask, threshold=0.3):
    """ uses fsl tools to extract data values in mask,
    masks 'mask' with gmmask thresholded at 'threshold' (default 0.3)
    returns mean, std, nvoxels
    NOTE: generates some tmp files in tempdir, but also removes them"""
    tmpdir = tempfile.mkdtemp()
    startdir = os.getcwd()
    os.chdir(tmpdir)
    # first mask mask with thresholded gmmask
    pth, nme = os.path.split(mask)
    outfile = fname_presuffix(mask, prefix = 'gmask_', newpath=tmpdir )
    c1 = CommandLine('fslmaths %s -thr %2.2f -nan -mul %s %s'%(gmmask,
                                                               threshold,
                                                               mask,
                                                               outfile)
                     ).run()
    if not c1.runtime.returncode == 0:
        print 'gm masking of mask failed for %s'%(mask)
        print 'tmp dir', tmpdir
        print c1.runtime.stderr
        return None   
    #first mask data
    cmd = 'fslmaths %s -nan -mas %s masked_data'%(data, outfile)
    mask_out = CommandLine(cmd).run()
    if not mask_out.runtime.returncode == 0:
        print 'masking failed for %s'%(data)
        return None, None, None
    masked = utils.find_single_file('masked*')
    # get stats
    mean_out = CommandLine('fslstats %s -M'%(masked)).run()
    mean = mean_out.runtime.stdout.strip('\n').strip()
    std_out = CommandLine('fslstats %s -S'%(masked)).run()
    std = std_out.runtime.stdout.strip('\n').strip()
    vox_out = CommandLine('fslstats %s -V'%(masked)).run()
    vox = vox_out.runtime.stdout.split()[0]
    os.chdir(startdir)
    rmtree(tmpdir)
    return mean, std, vox


def fsl_mask(infile, mask, outname='grey_cerebellum_tu.nii'):
    """use fslmaths to mask img with mask"""

    pth, nme = os.path.split(infile)
    outfile = os.path.join(pth, outname)
    c1 = CommandLine('fslmaths %s -mas %s %s'%(infile, mask, outfile))
    out = c1.run()
    
    if not out.runtime.returncode == 0:
        print 'failed to mask %s'%(infile)
        print out.runtime.stderr
        return None
    else:
        return outfile

def fsl_theshold_mask(infile, gmmask, threshold, outname='gmaskd_mask.nii.gz'):
    """ use fslmaths to mask infile with gmmask which will be thresholded
    at threshold and saved into outname"""
    pth, nme = os.path.split(infile)
    outfile = os.path.join(pth, outname)
    c1 = CommandLine('fslmaths %s -thr %2.2f -mul %s %s'%(gmmask,
                                                          threshold,
                                                          infile,
                                                          outnfile)
                     )
    if not c1.runtime.returncode == 0:
        print 'gm masking of mask failed for %s'%(infile)
        return None
    return outfile
    

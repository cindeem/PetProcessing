# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import os, sys, re
from glob import glob
import tempfile

import nipype.interfaces.spm as spm
from nipype.interfaces.base import CommandLine
import nipype.interfaces.matlab as mlab
from nipype.utils.filemanip import split_filename, fname_presuffix
from utils import (make_rec_dir,make_dir, copy_file,
                   copy_files, tar_cmd, copy_tmpdir)

def spm_smooth(infiles, fwhm=8):
    startdir = os.getcwd()
    basedir = os.path.split(infiles[0])[0]
    os.chdir(basedir)
    smth = spm.Smooth(matlab_cmd='matlab-spm8')
    smth.inputs.in_files = infiles
    smth.inputs.fwhm = fwhm
    #smth.inputs.ignore_exception = True
    sout = smth.run()
    os.chdir(startdir)
    return sout


def realigntoframe1(niftilist, copied = False):
    """given list of nifti files
    if copied is False
          copies relevent files to realign_QA
    else:
          works on input files
    realigns to the 1st frame
    """
    startdir = os.getcwd()
    niftilist.sort()
    if not copied:
        basepth, _ = os.path.split(niftilist[0])
        tmpdir, exists = make_dir(basepth, 'realign_QA')
        if exists:
            return None, None
        # copy files to tmp dir
        copiednifti = []
        for f in niftilist:
            newf = copy_file(f, tmpdir)
            copiednifti.append(str(newf))
            print 'copied nifti', copiednifti
    else:
        tmpdir, _ = os.path.split(niftilist[0])
        copiednifti = [str(x) for x in niftilist]
    # realign to frame1
    os.chdir(tmpdir)
    rlgn = spm.Realign()
    rlgn.inputs.matlab_cmd = 'matlab-spm8'
    rlgn.inputs.in_files = copiednifti
    rlgn.inputs.ignore_exception = True
    #print rlgn.mlab.cmdline
    rlgnout = rlgn.run()
    os.chdir(startdir)
    return rlgnout, copiednifti    

def realigntoframe17(niftilist, copied = False):
    """given list of nifti files
    copies/creates realign_QA
    removes first 5 frames
    realignes rest to the 17th frame
    """
    startdir = os.getcwd()
    niftilist.sort()
    basepth, _ = os.path.split(niftilist[0])
    if not copied:
        tmpdir, exists = make_dir(basepth, 'realign_QA')
        if exists:
            return None, None    
        # copy files to tmp dir
        copiednifti = []
        for f in niftilist:
            newf = copy_file(f, tmpdir)
            copiednifti.append(str(newf))
    else:
        tmpdir, _ = os.path.split(niftilist[0])
        copiednifti = [str(x) for x in niftilist]
        
    # put files in correct order
    os.chdir(tmpdir)
    alteredlist =[x for x in  copiednifti]
    frame17 = alteredlist[16]
    alteredlist.remove(frame17)
    alteredlist = alteredlist[5:]
    alteredlist.insert(0, frame17)
    # realign
    rlgn = spm.Realign(matlab_cmd='matlab-spm8')
    rlgn.inputs.in_files = alteredlist
    rlgn.inputs.ignore_exception = True
    rlgnout = rlgn.run()
    os.chdir(startdir)
    return rlgnout, copiednifti


def simple_coregister(target, moving, other=None):
    """ uses the basic spm Coregister functionality to move the
    moving image to target, and applies to others is any"""
    startdir = os.getcwd()
    pth, _ = os.path.split(moving)
    os.chdir(pth)
    corg = spm.Coregister(matlab_cmd = 'matlab-spm8')
    corg.inputs.target = str(target)
    corg.inputs.source = str(moving)
    corg.inputs.ignore_exception = True
    if other is not None:
        corg.inputs.apply_to_files = [str(x) for x in other]
    corg_out = corg.run()
    os.chdir(startdir)
    return corg_out

def simple_warp(template, warped, other=None):
    """ uses basic spm Normalize to warp warped to template
    applies parameters to other if specified"""
    startdir = os.getcwd()
    pth, _ = os.path.split(warped)
    os.chdir(pth)
    warp = spm.Normalize(matlab_cmd = 'matlab-spm8')
    warp.inputs.template = template
    warp.inputs.source = warped
    warp.inputs.ignore_exception = True
    if other is not None:
        warp.inputs.apply_to_files = other
    warp_out = warp.run()
    os.chdir(startdir)
    return warp_out

def simple_segment(mri):
    """uses spm to segment an mri in native space"""
    startdir = os.getcwd()
    pth, _ = os.path.split(mri)
    os.chdir(pth)
    seg = spm.Segment(matlab_cmd = 'matlab-spm8')
    seg.inputs.data = mri
    seg.inputs.gm_output_type = [False, False, True]
    seg.inputs.wm_output_type = [False, False, True]
    seg.inputs.csf_output_type = [False, False, True]
    seg.inputs.ignore_exception = True
    segout = seg.run()
    os.chdir(startdir)
    return segout


def make_transform_name(inpet, inmri, inverse = True):
    """ given pet filename and mrifilename,
    if inverse, makes
    the MRI_2_PET transform name
    else
    makes PET_2_MRI transform name"""

    petpth, petnme, petext = split_filename(inpet)
    mripth, mrinme, ext  = split_filename(inmri)

    if inverse:
        newnme = '%s_TO_%s.mat'%(mrinme, petnme)
        newfile = os.path.join(petpth, newnme)
    else:
        newnme = '%s_TO_%s.mat'%(petnme, mrinme)
        newfile = os.path.join(mripth, newnme)
    return newfile

def invert_coreg(mri, pet, transform):
    """ coregisters pet to mri, inverts parameters
    and applies to mri"""
    startdir = os.getcwd()
    pth, _ = os.path.split(pet)
    os.chdir(pth)
    mlab_cmd = mlab.MatlabCommand(matlab_cmd='matlab-spm8')
    mlab_cmd.inputs.nodesktop = True
    mlab_cmd.inputs.nosplash = True
    mlab_cmd.inputs.mfile = True
    mlab_cmd.inputs.script_file = 'pyspm8_invert_coreg.m'
    script = """
    pet = \'%s\';
    mri = \'%s\';
    petv = spm_vol(pet);
    mriv = spm_vol(mri);
    x = spm_coreg(petv, mriv);
    M = inv(spm_matrix(x(:)'));
    save( \'%s\' , \'M\' );
    mrispace = spm_get_space(mri);
    spm_get_space(mri, M*mrispace);
    """%(pet,
         mri,
         transform)
    mlab_cmd.inputs.script = script
    mout = mlab_cmd.run()
    os.chdir(startdir)
    return mout


def forward_coreg(mri, pet, transform):
    """ coregisters pet to mri and applies to pet,
    saves parameters in transform """
    startdir = os.getcwd()
    pth, _ = os.path.split(pet)
    os.chdir(pth)
    mlab_cmd = mlab.MatlabCommand(matlab_cmd='matlab-spm8')
    mlab_cmd.inputs.nodesktop = True
    mlab_cmd.inputs.nosplash = True
    mlab_cmd.inputs.mfile = True
    mlab_cmd.inputs.script_file = 'pyspm8_forward_coreg.m'
    script = """
    pet = \'%s\';
    mri = \'%s\';
    petv = spm_vol(pet);
    mriv = spm_vol(mri);
    x = spm_coreg(petv, mriv);
    M = spm_matrix(x(:)');
    save( \'%s\' , \'M\' );
    petspace = spm_get_space(pet);
    spm_get_space(pet, M * petspace);
    """%(pet,
         mri,
         transform)
    mlab_cmd.inputs.script = script
    mout = mlab_cmd.run()
    os.chdir(startdir)
    return mout
    
def apply_transform_onefile(transform,file):
    """ applies transform to files using spm """
    startdir = os.getcwd()
    pth, _ = os.path.split(file)
    os.chdir(pth)
    mlab_cmd = mlab.MatlabCommand(matlab_cmd = 'matlab-spm8')
    mlab_cmd.inputs.nodesktop = True
    mlab_cmd.inputs.nosplash = True
    mlab_cmd.inputs.ignore_exception = True
    mlab_cmd.inputs.mfile = True
    mlab_cmd.inputs.script_file = 'pyspm8_apply_transform.m'
    script = """
    infile = \'%s\';
    transform = load(\'%s\');
    imgspace = spm_get_space(infile);
    spm_get_space(infile ,transform.M*imgspace);
    """%(file, transform)
    mlab_cmd.inputs.script = script
    mout = mlab_cmd.run()
    os.chdir(startdir)
    return mout
    
def reslice(space_define, infile, interp=0):
    """ uses spm_reslice to resample infile into the space
    of space_define, assumes they are already in register
    interp = 0, nearest neighbor, 1=trilinear"""
    startdir = os.getcwd()
    pth, _ = os.path.split(infile)
    os.chdir(pth)
    mlab_cmd = mlab.MatlabCommand(matlab_cmd = 'matlab-spm8')
    mlab_cmd.inputs.nodesktop = True
    mlab_cmd.inputs.nosplash = True
    mlab_cmd.inputs.mfile = True
    mlab_cmd.inputs.ignore_exception = True
    mlab_cmd.inputs.script_file = 'pyspm8_reslice.m'
    script = """
    flags.mean = 0;
    flags.which = 1;
    flags.mask = 1;
    flags.interp = %d;
    infiles = strvcat(\'%s\', \'%s\');
    invols = spm_vol(infiles);
    spm_reslice(invols, flags);
    """%(interp, space_define, infile)
    mlab_cmd.inputs.script = script
    mout = mlab_cmd.run()
    os.chdir(startdir)
    return mout

def seg_pet(meanimg, mask):
    """ align PET to template,(no reslice)
    and segment, this will create both direction
    warps for moving ref region and then warping to template space
    """
    startdir = os.getcwd()
    pth, _ = os.path.split(meanimg)
    os.chdir(pth)
    seg = spm.Segment(matlab_cmd = 'matlab-spm8')
    seg.inputs.data = str(meanimg)
    seg.inputs.affine_regularization = "none"
    seg.inputs.clean_masks ='no'
    seg.inputs.csf_output_type = [False, False, False]
    seg.inputs.gm_output_type = [False, False, True]
    seg.inputs.wm_output_type = [False, False, True]
    seg.inputs.mask_image = str(mask)
    #seg.inputs.save_bias_corrected = False
    segout = seg.run()
    os.chdir(startdir)
    return segout
    

def apply_warp_fromseg(infiles, param_file):
    """ applys a warp param file generated from segmentation
    to infiles, (infiles should be a list of file names"""
    startdir = os.getcwd()
    pth, _ = os.path.split(infiles[0])
    os.chdir(pth)
    warp = spm.Normalize(matlab_cmd = 'matlab-spm8')
    warp.inputs.parameter_file = param_file
    warp.inputs.jobtype = 'write'
    warp.inputs.apply_to_files = [str(x) for x in infiles]
    warp.inputs.write_bounding_box = [[-90, -126, -72],
                                     [90, 90, 108]]
    warp.inputs.write_voxel_sizes = [2.0, 2.0, 2.0]
    warpout = warp.run()
    os.chdir(startdir)
    return warpout


def invert_warp(infile, snmat, pons):
    """ updates mfile with correct info
    calcs inverse of snmat, in space of infile and
    applies to pons"""
    
    mfile_dir,_ = os.path.split(os.path.abspath(__file__))
    mfile = os.path.join(mfile_dir, 'inv_warp_job.m')
    startdir = os.getcwd()
    pth, _ , _ = split_filename(infile)
    os.chdir(pth)
    
    lines = open(mfile).read()
    for tag, item in zip(['INFILE', 'SNMAT','PONS'],
                         [infile, snmat, pons]):
        lines = lines.replace(tag, item)
    newmfile = os.path.join(pth, 'inv_warp_job.m')
    with open(newmfile, 'w+') as fid:
        fid.write(lines)
       
    mlab_cmd = mlab.MatlabCommand(matlab_cmd = 'matlab-spm8')
    mlab_cmd.inputs.nodesktop = True
    mlab_cmd.inputs.nosplash = True
    mlab_cmd.inputs.mfile = True
    mlab_cmd.inputs.ignore_exception = True
    mlab_cmd.inputs.script_file = 'pyspm8_invwarp.m'
    script = """
    eval('inv_warp_job');
    spm_jobman('initcfg');
    spm('defaults','PET');
    spm_jobman(\'run\', matlabbatch);
    """
    mlab_cmd.inputs.script = script
    mout = mlab_cmd.run()
    os.chdir(startdir)
    return mout


    
    

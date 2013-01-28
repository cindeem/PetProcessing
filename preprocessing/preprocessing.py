# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import os, sys, re
from glob import glob
import tempfile
import logging
from shutil import rmtree
sys.path.insert(0,'/home/jagust/cindeem/CODE/PetProcessing')

import nipype.interfaces.spm as spm
from nipype.interfaces.base import CommandLine
import nipype.interfaces.matlab as mlab
from nipype.utils.filemanip import split_filename, fname_presuffix
import base_gui as bg
import nibabel
from numpy import zeros, nan_to_num, mean, logical_and, eye, dot
from scipy.ndimage import affine_transform
import numpy as np

sys.path.insert(0, '/home/jagust/cindeem/CODE/GraphicalAnalysis/pyGA')
import pyGraphicalAnalysis as pyga

import csv
from utils import make_rec_dir
#made non writeable by lab

def make_cerebellum_nibabel(aseg):
      """ use nibabel to make cerebellum"""
      #cwd = os.getcwd()
      pth, nme = os.path.split(aseg)
      #os.chdir(pth)
      img = ni.load(aseg)
      newdat = np.zeros(img.get_shape())
      dat = img.get_data()
      newdat[dat == 8] = 1
      newdat[dat == 47] = 1
      newimg = ni.Nifti1Image(newdat, img.get_affine())
      newfile = os.path.join(pth, 'grey_cerebellum.nii')
      newimg.to_filename(newfile)
      return newfile

def make_cerebellum(aseg):
      cwd = os.getcwd()
      pth, nme = os.path.split(aseg)
      os.chdir(pth)
      cl = CommandLine('fslmaths %s -thr 47 -uthr 47 right_cerebellum'% (aseg))
      cout = cl.run()
      
      if not cout.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  right cerebellum for %s'%(aseg)
            return None

      cl2 = CommandLine('fslmaths %s -thr 8 -uthr 8 left_cerebellum'% (aseg))
      cout2 = cl2.run()

      if not cout2.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  left cerebellum for %s'%(aseg)
            return None

      cl3 = CommandLine('fslmaths left_cerebellum -add right_cerebellum -bin grey_cerebellum')
      cout3 = cl3.run()
      if not cout3.runtime.returncode == 0:
            print 'Unable to create whole cerebellum for %s'%(aseg)
            print cout3.runtime.stderr
            print cout3.runtime.stdout
            return None
      
      cmd = 'rm right_cerebellum.* left_cerebellum.*'
      cl4 = CommandLine(cmd)
      cout4 = cl4.run()
      os.chdir(cwd)
      cerebellum = glob('%s/grey_cerebellum.*'%(pth))
      return cerebellum[0]

def make_whole_cerebellume(aseg):
      """
      os.system('fslmaths rad_aseg -thr 46 -uthr 47 whole_right_cerebellum')
      os.system('fslmaths rad_aseg -thr 7 -uthr 8 whole_left_cerebellum')
      os.system('fslmaths whole_left_cerebellum -add whole_right_cerebellum -bin whole_cerebellum')
      """
      cwd = os.getcwd()
      pth, nme = os.path.split(aseg)
      os.chdir(pth)
      cmd = 'fslmaths %s -thr 46 -uthr 47 whole_right_cerebellum'%(aseg)
      cl = CommandLine(cmd)
      cout = cl.run()
      if not cout.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  right whole cerebellum for %s'%(aseg)
            return None
      
      cmd = 'fslmaths %s -thr 7 -uthr 8 whole_left_cerebellum'%(aseg)
      cl2 = CommandLine(cmd)
      cout2 = cl2.run()
      if not cout2.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  whole left cerebellum for %s'%(aseg)
            return None     

      cmd = 'fslmaths whole_left_cerebellum -add whole_right_cerebellum' + \
            ' -bin whole_cerebellum'
      cl3 = CommandLine(cmd)
      cout3 = cl3.run()
      if not cout3.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  whole cerebellum for %s'%(aseg)
            print cout3.runtime.stderr
            print cout3.runtime.stdout
            return None     
      cmd = 'rm whole_right_cerebellum.* whole_left_cerebellum.*'
      cl4 = CommandLine(cmd)
      cout4 = cl4.run()      
      whole_cerebellum = glob('%s/whole_cerebellum.*'%(pth))
      os.chdir(cwd)
      return whole_cerebellum[0]


def make_brainstem(aseg):

      cwd = os.getcwd()
      pth, nme = os.path.split(aseg)
      os.chdir(pth)
      cl = CommandLine('fslmaths %s -thr 16 -uthr 16 brainstem'% (aseg))
      cout = cl.run()
      os.chdir(cwd)
      if not cout.runtime.returncode == 0:
            print 'Unable to create brainstem for %s'%(aseg)
            return None
      else:
            os.remove(aseg)
            return 'brainstem'


def move_and_convert(mgz, dest, newname):
      """takes a mgz file, moves it,
      converts it to nifti and then removes
      the original mgz file"""
      cwd = os.getcwd()
      new_mgz = copy_file(mgz, dest)
      os.chdir(dest)
      nii = convert(new_mgz, newname)
      os.chdir(cwd)
      os.remove(new_mgz)
      return nii

def biograph_dicom_convert(input, dest, subid, tracer):
    """ given a tgz file holding dicoms,
    expands in temdir, uses mri_convert to convert
    file to nifti (4D) in tmpdir
    copies single frames to dest"""
    newfile = copy_tmpdir(input)
    pth = tar_cmd(newfile)
    results = find_dicoms(pth)
    all4d = []
    for val, (name, files) in enumerate(sorted(results.items())):
        dcm0 = files[0]
        #if not tracer.upper() in name.upper():
        #    fname = os.path.join(pth,
        #                         '%s_%s%d'%(subid, tracer,val) + '.nii.gz')
        #else:
        #    fname = os.path.join(pth, name + '.nii.gz')
        #tmp4d = convert_dicom(dcm0, fname)
        tmp4d = biograph_to_nifti(dcm0)
        all4d.append(tmp4d)

    if len(all4d) > 1:
        final4d = concat_images(all4d)
    else:
        final4d = all4d[0]
    basename = '%s_%s_frame'%(subid, tracer.upper())    
    tmpsplit = fsl_split4d(final4d, basenme = basename)    
    newfiles = copy_files(tmpsplit, dest)
    pth, _ = os.path.split(final4d)
    os.system('rm -rf %s'%(pth)) 
    return newfiles
    

def concat_images(img_list):
    alldat = np.concatenate([ni.load(x).get_data() for x in img_list],
                            axis=3)
    pth, _ = os.path.split(img_list[0])
    newf = os.path.join(pth, 'full4d.nii.gz')
    allimg = ni.Nifti1Image(alldat, ni.load(img_list[0]).get_affine())
    allimg.to_filename(newf)
    for item in img_list[1:]:
        # clean tmp directories
        pth, _ = os.path.split(item)
        os.system('rm -rf %s'%pth)
    return newf

def copy_tmpdir(infile):
    """copies file to tempdir, returns path
    to file copied into tmpdir"""
    tmpdir = tempfile.mkdtemp()
    newfile = copy_file(infile, tmpdir)
    return newfile


def fsl_split4d(in4d, basenme = None):
    cwd = os.getcwd()
    pth, nme, ext = nipype.utils.filemanip.split_filename(in4d)
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


def biograph_to_nifti(dicomf):
    """ given a dicom file <dicomf> in a directory of dicoms
    , use dcm2nii to convert
    to a 4d.nii.gz file in a tempdir"""
    tmp, _ = os.path.split(os.path.abspath(__file__))
    default_file = os.path.join(tmp,
                                'dcm2nii.ini')
    tmpdir = tempfile.mkdtemp()
    convert = dcm2nii.Dcm2nii()
    convert.inputs.source_names = dicomf
    convert.inputs.output_dir = tmpdir
    convert.inputs.config_file = default_file
    cout = convert.run()
    if not cout.runtime.returncode == 0:
        logging.error(cout.runtime.stderr)
        return None
    else:
        ext = ''
        if 'GZip' in cout.runtime.stdout:
            ext = '.gz'
        outf = cout.runtime.stdout.split('->')[-1].split('\n')[0]
        return os.path.join(tmpdir,outf + ext)
    


def convert_dicom(dcm0, fname):
    """given first dicom and fname uses mri_convert to convert
    to a 4d nii.gz file"""
    

    cmd = '/usr/local/freesurfer_x86_64-5.1.0/bin/mri_convert '
    cmd = cmd + ' --out_orientation LAS %s %s'%(dcm0, fname)
    cl = CommandLine(cmd)
    cout = cl.run()
    if not cout.runtime.returncode == 0:
        logging.error('DICOM Failed to convert %s'%(dcm0))
        return None
    else:
        return fname

def clean_dicom_filenames(dcms):
    """remove parenthesis from all dicom filenames"""
    newfiles = []
    for dcm  in dcms:
        # hanlde unix issue
        tmpdcm = dcm.replace('(', '\(').replace(')', '\)')
        # get rid of meaningless scans
        if '._B' in dcm or '.tgz' in dcm:
            continue
        newname = dcm.replace('(','').replace(')','')
        if not newname == tmpdcm:
            cmd = 'mv %s %s'%(tmpdcm, newname)
            out = CommandLine(cmd).run()
        newfiles.append(newname)
            
    return newfiles

def find_dicoms(pth):
    """looks in pth to find files, sorts and returns list
    of lists (to handle multiple directories)"""
    toplevel = [os.path.join(pth, x) for x in os.listdir(pth)]
    alldir = [x for x in toplevel if os.path.isdir(x)]

    if len(alldir) < 1:
        alldir = [pth]
    results = {}
    for item in alldir:
        if '.tgz' in item:
            continue
        tmpfiles = glob('%s/*'%(item))
        tmpfiles.sort()
        cleanfiles = clean_dicom_filenames(tmpfiles)
        results.update({item:cleanfiles})
    return results





def convertallecat(ecats, newname):
      """ converts all ecat files and removes .v files"""
      for f in ecats:
            ecat2nifti(f, newname)
            os.remove(f)



def copy_dir(dir, dest, pattern='*'):
      """copies files matching pattern in dir to dest
      returns list of abspath to new copied items """
      items = glob('%s/%s'%(dir,pattern))
      newitems = []
      for item in items:
            newitem = copy_file(item, dest)
            newitems.append(newitem)
      return newitems


def ecat2nifti(ecat, newname):
    """run ecat_convert_nibabel.py"""
    cmd = 'ecat_convert_nibabel.py'
    format = '-format NIFTI'
    outname = '-newname %s'%(newname)
    cmdstr = ' '.join([cmd, format, outname,ecat])    
    cl = CommandLine(cmdstr)
    out = cl.run()
    if not out.runtime.returncode == 0:
        return False
    else:
        return True


def convert(infile, outfile):
    """converts freesurfer .mgz format to nifti
    """
    c1 = CommandLine('mri_convert --out_orientation LAS %s %s'%(infile,
                                                                outfile))
    out = c1.run()
    if not out.runtime.returncode == 0:
        #failed
        print 'did not convert %s from .mgz to .nii'%(infile)
    else:
        path = os.path.split(infile)[0]
        niifile = os.path.join(path,outfile)
        return niifile



def make_subject_dict(dirs, outdict):
      """given a set of directories
      initialize a dictionary to hold
      names
      directories
      diagnoses
      """
      
      for item in dirs:
          scanid = item.strip('/home/jagust/arda/lblid')
          outdict.update({scanid:[item,None]})
      

def get_logging_configdict(logfile):
        log_settings = {
                'version': 1,
                'root': {
                    'level': 'NOTSET',
                    'handlers': ['console', 'file'],
                },
                'handlers': {
                    'file': {
                        'class': 'logging.handlers.RotatingFileHandler',
                        'level': 'INFO',
                        'formatter': 'detailed',
                        'filename': logfile,
                        'mode': 'w',
                        'maxBytes': 10485760,
                        },
                    'console': {
                        'class': 'logging.StreamHandler',
                        'level': 'INFO',
                        'formatter': 'detailed',
                        'stream': 'ext://sys.stdout',
                }},
                'formatters': {
                    'detailed': {
                        'format': '%(asctime)s %(module)-17s line:%(lineno)-4d ' \
                        '%(levelname)-8s %(message)s',
                        }
                    }}       
        return log_settings


def set_up_dir(root, subid, tracer):
    """ check for and Make Subjects Target Directories
    Returns Dict of final directories and if they exist"""
    outdirs = {}
        
    subdir, exists = make_dir(root, dirname=subid)
    outdirs.update(dict(subdir=[subdir, exists]))
    tracerdir,exists = make_dir(subdir,
                                dirname = '%s' % (tracer.lower()) )
    outdirs.update(dict(tracerdir=[tracerdir, exists]))
    
    rawdatadir, exists  = make_dir(subdir, dirname = 'RawData')
    outdirs.update(dict(rawdatadir=[rawdatadir, exists]))
    
    rawtracer, exists  = make_dir(rawdatadir, dirname = tracer)
    outdirs.update(dict(rawtracer=[rawtracer, exists]))
    
    anatomydir, exists  = make_dir(subdir,dirname='anatomy')
    outdirs.update(dict(anatomydir=[anatomydir, exists]))
    
    refdir, exists = make_rec_dir(tracerdir,dirname='ref_region')
    outdirs.update(dict(refdir=[refdir, exists]))
    
    #print 'directories created for %s' % subid
    logging.info('directories created for %s'%(subid))
    for k, v in sorted(outdirs.values()):
        logging.info('%s : previously existed = %s'%(k,v))
    return outdirs


def setup_dir(root, subid, tracer):
    """ check for and Make Subjects Target Directories
    Returns Dict of final directories and if they exist"""
    outdirs = {}
        
    subdir, exists = make_dir(root, dirname=subid)
    outdirs.update(dict(subdir=[subdir, exists]))
    tracerdir,exists = make_dir(subdir,
                                dirname = '%s' % (tracer.lower()) )
    outdirs.update(dict(tracerdir=[tracerdir, exists]))
    
    rawdatadir, exists  = make_dir(subdir, dirname = 'raw')
    outdirs.update(dict(rawdatadir=[rawdatadir, exists]))
    
    rawtracer, exists  = make_dir(rawdatadir, dirname = tracer)
    outdirs.update(dict(rawtracer=[rawtracer, exists]))
    
    anatomydir, exists  = make_dir(subdir,dirname='anatomy')
    outdirs.update(dict(anatomydir=[anatomydir, exists]))
    
    refdir, exists = make_rec_dir(tracerdir,dirname='ref_region')
    outdirs.update(dict(refdir=[refdir, exists]))
    
    #print 'directories created for %s' % subid
    logging.info('directories created for %s'%(subid))
    for k, v in sorted(outdirs.values()):
        logging.info('%s : previously existed = %s'%(k,v))
    return outdirs

def check_subject(subject_directory):
    """checks to make sure this is a valid subject
    directory by looking at subject ID
    BXX-XXX
    """
    pth, subid = os.path.split(subject_directory)
    if len(subid) < 7:
        print 'bad directory ', subject_directory
        return False, None
    
    elif subid[0] == 'B':
        return True, subid
    else:
        print 'bad directory ', subject_directory
        return False, None
        

def reslice_data(space_define_file, resample_file):
    """ reslices data in space_define_file to matrix of
    resample_file
    Parameters
    ----------
    space_define_file :  filename of space defining image
    resample_file : filename of image be resampled

    Returns
    -------
    img : space_define_file as nibabel image
    data : ndarray of data in resample_file sliced to
           shape of space_define_file
    """
    space_define_file = str(space_define_file)
    resample_file = str(resample_file)
    img = nibabel.load(space_define_file)
    change_img = nibabel.load(resample_file)
    T = eye(4)
    
    Tv = dot(np.linalg.inv(change_img.get_affine()), 
             dot(T, img.get_affine()))
    data = affine_transform(change_img.get_data().squeeze(), 
                            Tv[0:3,0:3], 
                            offset=Tv[0:3,3], 
                            output_shape = img.get_shape()[:3],
                            order=0,mode = 'nearest')

    return img, data


def roi_stats_nibabel(data, mask, gm=None,gmthresh=0.3):
    """ uses nibabel to pull mean, std, nvox from
    data <file>  using mask <file>  and gm <file>(if defined )
    to define region of interest
    """
    img, newmask=  reslice_data(data, mask)
    if gm is not None:
        gmdat = nibabel.load(gm).get_data()
        if not gmdat.shape == newmask.shape:
            raise IOError('matrix dims not matched %s %s'%(gm,data))
        fullmask = np.logical_and(gmdat>gmthresh, newmask>0)
    else:
        fullmask = newmask
    dat = img.get_data()
    allmask = np.logical_and(fullmask, dat>0)
    roidat = dat[allmask]
    return roidat.mean(), roidat.std(), roidat.shape[0]
    


def labelroi_stats_nibabel(data, mask,label, othermask=None):
    """ uses nibabel to pull stats form roi defined by
    a labelled image (mask)
    othermask can be used to mask the labelled mask (eg stroke)
    returns mean, std, nvox
    """
    dat = nibabel.load(data).get_data()
    roi = nibabel.load(mask).get_data()
    if not dat.shape == roi.shape:
        raise IOError('shape mismatch of DATA and ROI')
    if othermask is not None:
        msk = nibabel.load(othermask).get_data()
        if not msk.shape == dat.shape:
            raise IOError('shape mismatch of DATA and othermask')
    fullmask = roi == label
    allmask = np.logical_and(fullmask, dat>0)
    if othermask is not None:
        allmask = np.logical_and(fullmask, msk > 0)
    roidat = dat[allmask]
    if roidat.shape[0] < 2:
        return 0,0,0
    return np.mean(roidat).item(), np.std(roidat).item(), roidat.shape[0]

def roi_stats_nibabel_noreslice(data, mask, gm=None,gmthresh=0.3):
    """ uses nibabel to pull roi values (mean, std, nvox) from
    file data, roi is mask, gm is a gm mask
    """
    dat = nibabel.load(data).get_data()
    roi = nibabel.load(mask).get_data()
    if not dat.shape == roi.shape:
        raise IOError('shape mismatch of DATA and ROI')
    if gm is not None:
        gmdat = nibabel.load(gm).get_data()
        if not gmdat.shape == dat.shape:
            raise IOError('shape mismatch of DATA and ROI')
        fullmask = np.logical_and(gmdat>gmthresh, roi>0)
    else:
        fullmask = roi
    allmask = np.logical_and(fullmask, dat>0)
    roidat = dat[allmask]
    return roidat.mean(), roidat.std(), roidat.shape[0]



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
    
def realigntoframe1(niftilist):
    """given list of nifti files
    copies relevent files to realign_QA
    realigns to the 1st frame
    """
    startdir = os.getcwd()
    niftilist.sort()
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



def realigntoframe17(niftilist):
    """given list of nifti files
    copies/creates realign_QA
    removes first 5 frames
    realignes rest to the 17th frame
    """
    startdir = os.getcwd()
    niftilist.sort()
    basepth, _ = os.path.split(niftilist[0])
    tmpdir, exists = make_dir(basepth, 'realign_QA')
    if exists:
        return None, None    
    # copy files to tmp dir
    copiednifti = []
    for f in niftilist:
        newf = copy_file(f, tmpdir)
        copiednifti.append(str(newf))
    # put files in correct order
    os.chdir(tmpdir)
    alteredlist =[x for x in  copiednifti]
    frame17 = alteredlist[16]
    alteredlist.remove(frame17)
    alteredlist = alteredlist[5:]
    alteredlist.insert(0, frame17)
    #print 'alteredlist', alteredlist
    # realign
    rlgn = spm.Realign(matlab_cmd='matlab-spm8')
    rlgn.inputs.in_files = alteredlist
    rlgn.inputs.ignore_exception = True
    #rlgn.inputs.write_which = [2,0]
    #rlgn.register_to_mean = True
    rlgnout = rlgn.run()
    os.chdir(startdir)
    return rlgnout, copiednifti

def prefix_filename(infile, prefix=''):
    """prefixes a file and returns full path/newfilename
    """
    pth, nme = os.path.split(infile)
    newfile = os.path.join(pth, '%s%s'%(prefix,nme))
    return newfile



def clean_nan(niftilist):
    """replaces nan in a file with zeros"""
    newfiles = []
    for item in niftilist:
        newitem = prefix_filename(item, prefix='nonan-')
        dat = nibabel.load(item).get_data().copy()
        affine = nibabel.load(item).get_affine()
        newdat = nan_to_num(dat)
        hdr = nibabel.Nifti1Header()
        newimg = nibabel.Nifti1Image(newdat, affine,hdr)
        newimg.to_filename(newitem)
        newfiles.append(newitem)
    return newfiles


def make_summed_image(niftilist, prefix='sum_'):
    """given a list of nifti files
    generates a summed image"""
    newfile = prefix_filename(niftilist[0], prefix=prefix)
    affine = nibabel.load(niftilist[0]).get_affine()
    shape =  nibabel.load(niftilist[0]).get_shape()
    newdat = zeros(shape)
    for item in niftilist:
        newdat += nibabel.load(item).get_data().copy()
    newimg = nibabel.Nifti1Image(newdat, affine)
    newimg.to_filename(newfile)
    return newfile

def make_pons_normed(petf, maskf, outfile):
    """given petf and maskf , normalize by mean of values
    in mask and save to outfile"""
    affine = nibabel.load(petf).get_affine()
    pet = nibabel.load(petf).get_data().squeeze()
    mask = nibabel.load(maskf).get_data().squeeze()
    if not pet.shape == mask.shape:
        raise AssertionError, 'pet and mask are different dimensions'
    allmask = logical_and(pet> 0, mask> 0)
    meanval = mean(pet[allmask])
    normpet = pet / meanval
    newimg = nibabel.Nifti1Image(normpet, affine)
    newimg.to_filename(outfile)


def simple_coregister(target, moving, other=None):
    """ uses the basic spm Coregister functionality to move the
    moving image to target, and applies to others is any"""
    startdir = os.getcwd()
    pth, _ = os.path.split(moving)
    os.chdir(pth)
    corg = spm.Coregister(matlab_cmd = 'matlab-spm8')
    corg.inputs.target = target
    corg.inputs.source = moving
    corg.inputs.ignore_exception = True
    if other is not None:
        corg.inputs.apply_to_files = other
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


def make_transform_name(inpet, inmri):
    """ given pet filename and mrifilename, makes
    the MRI_2_PET transform name"""
    pth, petnme = os.path.split(inpet)
    _, mrinme = os.path.split(inmri)

    mribase = mrinme.split('.')[0]
    petbase = petnme.split('.')[0]
    newnme = '%s_TO_%s.mat'%(mribase, petbase)
    newfile = os.path.join(pth, newnme)
    return newfile

def make_mean_20min(niftilist):
    """given list of niftis, grab frame 1-23
    generate mean image"""
    first_23 = niftilist[:23]
    first_23.sort()
    if not '23' in first_23[-1]:
        print "badframe numbers, unable to generate 20min mean"
        print 'frames', first_23
        return None
    newfile = make_mean(first_23, prefix='mean20min_')
    return newfile

def make_mean_40_60(niftilist):
    """given list of niftis, grab frame 28-31
    generate mean image"""
    #framen = [28,29,30,31]
    try:
        frames_28_31 = niftilist[27:31] #note frames start counting from 1
    except:
        print 'incorrect number of frames for making sum_40_60'
        return None
    m = re.search('frame0*28.nii',frames_28_31[0])
    if m is None:
        print 'bad frame numbers, unable to generate 40-60 mean'
        print 'frames', frames_28_31
        return None
    newfile = make_mean(frames_28_31, prefix='mean40_60min_')
    return newfile


def make_mean_usrdefined(niftilist, start, end):
    """ given nifti list generate mean image from
    start frame<start> to end frame<end>  inclusive
    name based on start and end frame numbers
    error raise if frame numbers not found in niftilist
    no check for missing frames between start and end"""
    niftilist.sort()
    # find indicies for the start and end frames in list
    for val, item in enumerate(niftilist):
        if 'frame' + repr(start).zfill(2) in item:
            start_frame = val
        if 'frame' + repr(end).zfill(2) in item:
            end_frame = val + 1 #add one to make sure we include frame
    frames = niftilist[start_frame:end_frame]
    prefix = 'mean_frame' + repr(start).zfill(2) + \
             '_to_frame' +repr(end).zfill(2) + '_'
    newfile = make_mean(frames, prefix = prefix)
    return newfile


def make_mean(niftilist, prefix='mean_'):
    """given a list of nifti files
    generates a mean image"""
    n_images = len(niftilist)
    newfile = prefix_filename(niftilist[0], prefix=prefix)
    affine = nibabel.load(niftilist[0]).get_affine()
    shape =  nibabel.load(niftilist[0]).get_shape()
    newdat = zeros(shape)
    for item in niftilist:
        newdat += nibabel.load(item).get_data().copy()
    newdat = newdat / n_images
    newimg = nibabel.Nifti1Image(newdat, affine)
    newimg.to_filename(newfile)
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
    mlab_cmd.inputs.script_file = 'pyspm8_invert_coreg.m'
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
    

def reslice(space_define, infile):
    """ uses spm_reslice to resample infile into the space
    of space_define, assumes they are already in register"""
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
    flags.interp = 0;
    infiles = strvcat(\'%s\', \'%s\');
    invols = spm_vol(infiles);
    spm_reslice(invols, flags);
    """%(space_define, infile)
    mlab_cmd.inputs.script = script
    mout = mlab_cmd.run()
    os.chdir(startdir)
    return mout


def find_single_file(searchstring):
    """ glob for single file using searchstring
    if found returns full file path """
    file = glob(searchstring)
    if len(file) < 1:
        print '%s not found' % searchstring
        return None
    else:
        outfile = file[0]
        return outfile


def run_logan(subid, nifti, ecat, refroi, outdir):
    """run pyGraphicalAnalysis Logan Plotting on PIB frames
    """
    midframes,frametimes = pyga.get_midframes_fromecat(ecat, units='sec')
    data = pyga.get_data(nifti)
    ref = pyga.get_ref(refroi, data)
    int_ref = pyga.integrate_reference(ref,midframes)
    #Make DVR
    ki, vd, resids = pyga.integrate_data_genki(data,ref,
                                               int_ref,
                                               midframes,
                                               0.15, (35,90))
    pth, _ = os.path.split(nifti[0])
    _, refnme = os.path.split(refroi)
    refbase = refnme.split('.')[0]
    ref_plot = os.path.join(outdir, '%s_REF_TAC.png'%(refbase))
    pyga.save_inputplot(ref_plot, ref, midframes)
    pyga.pylab.clf()
    pyga.save_data2nii(ki, nifti[0],
                       '%s_dvr_%s'%(subid, refbase), outdir)
    pyga.save_data2nii(resids, nifti[0],
                       filename='resid_%s'%(refbase),
                       outdir=outdir)
    outfile = os.path.join(outdir, '%s_dvr.nii'%(refbase))
    data.close()
    return outfile

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
    masked = find_single_file('masked*')
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


def fs_generate_dat(pet, subdir):
    """ use freesurfer tkregister to generate a dat file used in
    extracting PET counts with a labelled mri mask in freesurfer

    Parameters
    ----------
    pet : pet file that is registered to the subjects mri

    subdir : subjects freesurfer directory

    Returns
    -------
    dat : dat file generated , or None if failes
    you can check dat with ...
               'tkmedit %s T1.mgz -overlay %s -overlay-reg %s
               -fthresh 0.5 -fmid1'%(subject, pet, dat)
                 
    """
    pth, nme, ext = split_filename(pet)
    dat = os.path.join(pth, '%s_2_FS.dat'%(nme))
    cmd = 'tkregister2 --mov %s --s %s --regheader --reg %s --noedit'%(pet,
                                                                       subdir,
                                                                       dat)
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print 'tkregister failed for %s'%(pet)
        return None
    return dat

def fs_extract_label_rois(subdir, pet, dat, labels):
    """
    Uses freesurfer tools to extract

    Parameters
    -----------
    subdir : subjects freesurfer directory

    pet : filename of subjects PET volume coreg'd to mri space

    dat : filename of dat generated by tkregister mapping pet to mri

    labels : filename of subjects aparc+aseg.mgz

    Returns
    -------
    stats_file: file  that contains roi stats

    label_file : file of volume with label rois in pet space
               you can check dat with ...
               'tkmedit %s T1.mgz -overlay %s -overlay-reg %s
               -fthresh 0.5 -fmid1'%(subject, pet, dat)
                 
    """
    pth, nme, ext = split_filename(pet)
    pth_lbl, nme_lbl, ext_lbl = split_filename(labels)
    
    stats_file = os.path.join(pth, '%s_%s_stats'%(nme, nme_lbl))
    label_file = os.path.join(pth, '%s_%s_.nii.gz'%(nme, nme_lbl))

    # Gen label file
    cmd = ['mri_label2vol',
           '--seg %s/mri/%s'%(subdir, labels),
           '--temp %s'%(pet),
           '--reg'%(dat),
           '--o %s'%(label_file)]
    cmd = ' '.join(cmd)
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print 'mri_label2vol failed for %s'%(pet)
        return None, None
    ## Get stats
    cmd = ['mri_segstats',
           '--seg %s'%(label_file),
           '--sum %s'%(stats_file),
           '--in %s'%(pet),
           '--nonempty --ctab',
           '/usr/local/freesurfer_x86_64-4.5.0/FreeSurferColorLUT.txt']
    cmd = ' '.join(cmd)
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print 'mri_segstats failed for %s'%(pet)
        return None, None
    return stats_file, label_file

    
def parse_fs_statsfile(statsfile):
    """opens a fs generated stats file and returns
    a dict of roi keys with [mean, std, nvox], for
    each roi
    """
    roidict = {}
    for line in open(statsfile):
        if line[0] == '#':
            continue
        tmp = line.split()
        roi = tmp[4]
        mean = eval(tmp[5])
        std = eval(tmp[6])
        nvox = eval(tmp[2])
        roidict.update({roi:[mean, std, nvox]})
    return roidict

def parse_fs_statsfile_vert(statsfile):
    """opens a fs generated stats file and returns
    a dict of roi keys with [mean, std, nvert], for
    each roi
    """
    roidict = {}
    for line in open(statsfile):
        if line[0] == '#':
            continue
        tmp = line.split()
        roi = tmp[0]
        mean = eval(tmp[4])
        std = eval(tmp[5])
        nvox = eval(tmp[1])
        roidict.update({roi:[mean, std, nvox]})
    return roidict



def aseg_label_dict(lut, type='ctx'):
    """ Given a color LUT (look up table)
    return a dict of label : region
    (eg, {17:  'Left-Hippocampus'} )

    Inputs
    ------

    lut : file storing label to region look up table
          /usr/local/freesurfer_x86_64-4.5.0/ASegStatsLUT.txt

    type : string ('ctx', None)
           if ctx, only returns cortex regions
	   else returns all in file

    Returns
    -------

    dict : dictionary mapping label -> region
	   
    """
    outd = {}
    for line in open(lut):
        if '#' in line or 'G_' in line or 'S_' in line:
	    continue
        if type is 'ctx':
            if not type in line:
	        continue
        parts = line.split()
	if len(parts) < 2:
	    continue
        name_as_int = int(parts[0])
        valrange = np.vstack((np.arange(1002, 1036),np.arange(2002, 2036)))
        if type is 'ctx' and name_as_int not in valrange:
            # label is not a cortical label we care about
            continue
        outd[parts[0]] = parts[1]
    return outd
	
def roilabels_fromcsv(infile):
    """ given a csv file with fields
    'pibindex_Ltemporal', '1009', '1015', '1030', '', '', '', '', '', ''
    parses into roi name and array of label values and returns dict"""
    spam = csv.reader(open(infile, 'rb'),
                      delimiter=',', quotechar='"')
    roid = {}
    for item in spam:
        roi = item[0]
        labels = [x for x in item[1:] if not x == '']
        roid[roi] = np.array(labels, dtype=int)
    return roid

def mean_from_labels(roid, labelimg, data, othermask = None):
    meand = {}
    labels = nibabel.load(labelimg).get_data()
    if not labels.shape == data.shape:
        return None
    allmask = np.zeros(labels.shape, dtype=bool)
    for roi, mask in roid.items():
        fullmask = np.zeros(labels.shape, dtype=bool)
        for label_id in mask:
            fullmask = np.logical_or(fullmask, labels == label_id)
            data_mask = np.logical_and(data>0, np.isfinite(data))
            fullmask = np.logical_and(fullmask, data_mask)
            if othermask is not None:
                maskdat = nibabel.load(othermask).get_data()
                fullmask = np.logical_and(fullmask, maskdat > 0)
            # update allmask
            allmask = np.logical_or(allmask, fullmask)
            roimean = data[fullmask].mean()
            roinvox = data[fullmask].shape[0]
            meand[roi] = [roimean, roinvox]
    # get values of all regions
    meand['ALL'] = [data[allmask].mean(), data[allmask].shape[0]]
    return meand

def mean_from_labels_percent(roid, labelimg, data, percent = .50):
    meand = {}
    labels = nibabel.load(labelimg).get_data()
    if not labels.shape == data.shape:
        return None
    allmask = np.zeros(labels.shape, dtype=bool)
    for roi, mask in roid.items():
        fullmask = np.zeros(labels.shape, dtype=bool)
        for label_id in mask:
            fullmask = np.logical_or(fullmask, labels == label_id)
            data_mask = np.logical_and(data>0, np.isfinite(data))
            fullmask = np.logical_and(fullmask, data_mask)
            # update allmask
            allmask = np.logical_or(allmask, fullmask)
            roidat = data[fullmask]
            roidat.sort()
            topindx = int(roidat.shape[0] * percent)
            roimean = roidat[topindx:].mean()
            roinvox = roidat[topindx:].shape[0]
            meand[roi] = [roimean, roinvox]
    # get values of all regions
    meand['ALL'] = [data[allmask].mean(), data[allmask].shape[0]]
    return meand    
    

def meand_to_file(meand, csvfile):
    """given a dict of roi->[mean, nvox]
    unpack to array
    output to file
    """
    fid = open(csvfile, 'w+')
    csv_writer = csv.writer(fid)
    csv_writer.writerow(['SUBID', 'mean','nvox'])
    for k, (mean, nvox) in sorted(meand.items()):
        row = ['%s'%k,'%f'%mean,'%d'%nvox]
        csv_writer.writerow(row)
    fid.close()
    
    
if __name__ == '__main__':

	## test generateing freesurfer label dictionaries
	lut = '/usr/local/freesurfer_x86_64-4.5.0/ASegStatsLUT.txt'
	outd = aseg_label_dict(lut)
	assert outd == {}
	outd = aseg_label_dict(lut,type=None)
	assert outd['50'] == 'Right-Caudate'
	lut = '/usr/local/freesurfer_x86_64-4.5.0/FreeSurferColorLUT.txt'
	outd = aseg_label_dict(lut, type='ctx')
	## all values should have ctx in them
	assert 'ctx' in  outd.values()[0]
	

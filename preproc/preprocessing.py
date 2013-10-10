# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import os, sys, re
from glob import glob
import tempfile
import logging
from shutil import rmtree

import nipype.interfaces.spm as spm
from nipype.interfaces.base import CommandLine
import nipype.interfaces.matlab as mlab
from nipype.utils.filemanip import split_filename, fname_presuffix
import base_gui as bg
import nibabel
from numpy import zeros, nan_to_num, mean, logical_and, eye, dot
from scipy.ndimage import affine_transform
import numpy as np
import csv
from utils import (make_rec_dir,make_dir, copy_file,
                   copy_files, tar_cmd, copy_tmpdir)
import utils
#made non writeable by lab

def make_cerebellum_nibabel(aseg):
    """ use nibabel to make cerebellum"""
    #cwd = os.getcwd()
    pth, nme = os.path.split(aseg)
    #os.chdir(pth)
    img = nibabel.load(aseg)
    newdat = np.zeros(img.get_shape())
    dat = img.get_data()
    newdat[dat == 8] = 1
    newdat[dat == 47] = 1
    newimg = nibabel.Nifti1Image(newdat, img.get_affine())
    newfile = os.path.join(pth, 'grey_cerebellum.nii.gz')
    newimg.to_filename(newfile)
    return newfile


def make_whole_cerebellum(aseg):
    pth, nme = os.path.split(aseg)
    img = nibabel.load(aseg)
    newdat = np.zeros(img.get_shape())
    dat = img.get_data()
    regions = [7,8,46,47]
    for reg in regions:
        newdat[dat == reg] = 1
    newimg = nibabel.Nifti1Image(newdat, img.get_affine())
    newfile = os.path.join(pth, 'grey_cerebellum.nii.gz')
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
    cmdout2 = cl2.run()
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
            logging.error('Unable to create brainstem for %s'%(aseg))
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




def convertallecat(ecats, newname):
    """ converts all ecat files and removes .v files"""
    allresult = []
    for f in ecats:
        result = ecat2nifti(f, newname)
        os.remove(f)
        allresult.append(result)
    if all(allresult):
        return True
    else:
        return False

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
        logging.error(out.runtime.stderr)
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
    
    rawdatadir, exists  = make_dir(subdir, dirname = 'raw')
    outdirs.update(dict(rawdatadir=[rawdatadir, exists]))
        
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
        

def reslice_data(space_define_file, resample_file, order = 0):
    """ reslices data in space_define_file to matrix of
    resample_file
    Parameters
    ----------
    space_define_file :  filename of space defining image
    resample_file : filename of image be resampled
    order : int 
        order of spline used for reslicing 0=nearest, 3 = trilinear

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
    transform = eye(4) # identity transform
    newtransform = dot(np.linalg.inv(change_img.get_affine()),
                       dot(transform, img.get_affine()))
    data = affine_transform(change_img.get_data().squeeze(),
                            newtransform[:3, :3],
                            offset = newtransform[:3,3],
                            output_shape = img.get_shape()[:3],
                            order = order)
    return img, data

def roi_stats_nibabel(data, mask, gm=None, gmthresh=0.3):
    """ Uses nibabel to pull mean, std, nvox from 
    data <file> using mask <file> and gm <file> (if
    provided) """
    img, newmask = reslice_data(data, mask)
    if gm is not None:
        gmat = nibabel.load(gm).get_data()
        if not gmdat.shape == newmask.shape:
            raise IOError('matrix dim mismatch %s %s'%(gm,data))
        fullmask = np.logical_and(gmat > gmthresh, newmask > 0)
    else:
        fullmask = newmask > 0
    dat = img.get_data()
    allmask = np.logical_and(fullmask, dat > 0)
    roidat = dat[allmask]
    return roidat.mean(), roidat.std(), roidat.shape[0]




def make_summed_image(niftilist, prefix='sum_'):
    """given a list of nifti files
    generates a summed image"""
    newfile = fname_presuffix(niftilist[0], prefix=prefix)
    affine = nibabel.load(niftilist[0]).get_affine()
    shape =  nibabel.load(niftilist[0]).get_shape()
    newdat = zeros(shape)
    for item in niftilist:
        tmpdat = np.nan_to_num(nibabel.load(item).get_data().copy())
        newdat += tmpdat
    newimg = nibabel.Nifti1Image(newdat, affine)
    newimg.to_filename(newfile)
    return newfile



def make_mean_40_60(niftilist):
    """given list of niftis, grab frame 28-31
    generate mean image"""
    #framen = [28,29,30,31]
    try:
        frames_28_31 = niftilist[27:31] #note frames start counting from 1 or 0
    except:
        print 'incorrect number of frames for making sum_40_60'
        return None
    
    m = re.search('frame0*28',frames_28_31[0])
    if m is None:
        m = re.search('frame0*27', frames_28_31[0])
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

def make_mean_20min(niftilist):
    """ given list of nifti files, grab frames 1-23
    to generate a mean image (good pseudo-anatomical for PIB"""
    first_23 = niftilist[:23]
    first_23.sort()
    if not any(['23' in first_23[-1], '22' in first_23[-1]]):
        logging.error("frame 22 not in first 23, meake mean20 by hand")
        return None
    newfile = make_mean(first_23, prefix = 'mean20min_')
    return newfile

def make_mean(niftilist, prefix='mean_'):
    """given a list of nifti files
    generates a mean image"""
    n_images = len(niftilist)
    newfile = fname_presuffix(niftilist[0], prefix=prefix)
    affine = nibabel.load(niftilist[0]).get_affine()
    shape =  nibabel.load(niftilist[0]).get_shape()
    newdat = zeros(shape)
    for item in niftilist:
        newdat += nibabel.load(item).get_data().copy()
    newdat = newdat / n_images
    newdat = np.nan_to_num(newdat)
    newimg = nibabel.Nifti1Image(newdat, affine)
    newimg.to_filename(newfile)
    return newfile


def make_pons_normed(petf, maskf, outfile):
    """given petf and maskf (aligned and in same dims
    normalize entire volume by mean of values in maskf
    save to outfile"""
    affine = nibabel.load(petf).get_affine()
    pet = nibabel.load(petf).get_data().squeeze()
    mask = nibabel.load(maskf).get_data().squeeze()
    pet = np.nan_to_num(pet)
    mask = np.nan_to_num(mask)
    if not pet.shape == mask.shape:
        raise AssertionError, 'pet and mask have different dims'
    allmask = logical_and( pet > 0, mask > 0)
    meanval = pet[allmask].mean()
    normpet = pet / meanval
    newimg = nibabel.Nifti1Image(normpet, affine)
    newimg.to_filename(outfile)

    pass

def run_logan(subid, nifti, ecat, refroi, outdir):
    """run pyGraphicalAnalysis Logan Plotting on PIB frames
    """
    raise IOError('Not Implemented')
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

    print 'preprocessing module'




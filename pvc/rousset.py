# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python
import sys,os
import numpy as np
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing/pvc')
import ecat_smooth as es
import metzler as metzler
import nibabel as ni
import nipype.interfaces.freesurfer as freesurfer
import nipy
import nipy.algorithms


def check_roi_shape(rois):
    shapes = [ni.load(x).get_shape() for x in rois]
    sameshape = np.all([x == shapes[0] for x in shapes])
    if sameshape:
        return True, shapes[0]
    else:
        return False, None
    

def compute_rsf(rois):
    """ computes an RSF for each roi in input argument and returns an array with same size as input """
    sameshape, shape = check_roi_shape(rois)
    if not sameshape:
        raise AssertionError('ROIs do NOT have same shape, exiting program,'\
                             'check your ROIS dimensions')
    startdir = os.getcwd()
    
    fullshape = tuple([len(rois)] + list(shape))
    rsfs = np.zeros(fullshape)
    for ind, roi in enumerate(rois):
        
        petpsf = es.PetPsf(roi)
        xyresult = petpsf.convolve_xy()
        zresult = petpsf.convolve_z()
        file = petpsf.save_result()
        sfile = pp.fname_presuffix(file, prefix='s')
        smfile = metzler.smooth_mask_nipy(file,sfile,fwhm=7)
        smdata = smfile.get_data()
        rsfs[ind,:,:,:]  = smdata
    
    return rsfs


def mask_from_aseg(aparc_aseg, labels):
    """ generate binary mask based on labels from aparc aseg
    returns binary array"""
    
    labeldat = ni.load(aparc_aseg).get_data()
    binary = np.zeros(labeldat.shape)
    for label in labels:
        binary[labeldat == label] = 1
    
    return binary

def wm_aseg():
    """ labels to get wm in aparc_aseg"""
    return (2,7,41, 46,77,78,79,86)

def gm_aseg():
    """ labels to get gm in aparc_aseg"""
    ctx = range(1000,1036)+ range(2000,2036)
    sub_ctx = [3,8,9,10,11,12,13,16,17,18,19,20,26,27,#left subcort
               42,47,48,49,50,51,52,53,54,55,56,58,59]# right subcort
    return tuple(ctx + sub_ctx)

def pibindex_aseg():
    """ labels for pibindex"""
    return tuple([1003,1012,1014,1018,1019,1020,1027,1028,1032,1008,
                 1025,1029,1031,1002,1023,1010,1026,2003,2012,2014,
                 2018,2019,2020,2027,2028,2032,2008,2025,2029,2031,
                 2002,2023,2010,2026,1015,1030,2015,2030,2009,1009])

def to_file(dat, affine, fname):
    newimg = ni.Nifti1Image(dat, affine,
                            ni.Nifti1Header())
    newimg.to_filename(fname)
    
def generate_pibindex_rois_fs(aparc_aseg):
    """ given an aparc aseg in pet space:
    generate wm, gm and pibindex rois
    make sure they are non-overlapping
    return 3 rois"""
    wm = mask_from_aseg(aparc_aseg, wm_aseg())
    gm = mask_from_aseg(aparc_aseg,  gm_aseg())
    pibi = mask_from_aseg(aparc_aseg, pibindex_aseg())
    # make non-overlapping
    wm[pibi==1] = 0
    gm[pibi ==1] = 0
    gm[wm==1] = 0
    return wm, gm, pibi
    
def gen_transfer_matrix(rsfs, rois):
    transfer_matrix = np.zeros((len(rsfs),len(rsfs))) #initialize TM

    for jval, roi in enumerate(rois):
        roidat = ni.load(roi).get_data()
        roidat = np.nan_to_num(roidat)
        npix = np.prod(roidat[roidat >0].shape)
        # determine number of pixels in ROI
        for ival, rsf in enumerate(rsfs):
            # effect of one rsf on one ROI
            transfer_matrix[jval,ival] = np.nansum(np.multiply(roidat,rsf))/npix
    return transfer_matrix

def get_observed_conc(pet, rois):
    petdat = ni.load(pet).get_data()
    obs_conc = np.zeros(len(rois))
    for jval, roi in enumerate(rois):
        roidat = ni.load(roi).get_data()
        roidat = np.nan_to_num(roidat)
        mask = np.logical_and(roidat > 0, petdat > 0)
        obs_conc[jval] = petdat[mask].mean()
    return obs_conc

def calc_pvc_values(transfer_mtx, observed):
    corrected = np.matrix(np.linalg.inv(transfer_mtx))* \
                np.transpose(np.matrix(observed))
    return corrected

if __name__ == '__main__':

    testdir = os.path.abspath('../test')
    aparc_aseg = os.path.join(testdir, 'rB09-230_v1_aparc_aseg.nii')
    dvr = os.path.join(testdir,'DVR-B09-230_v1_2012-06-08-15-07.nii.gz')
    wm = mask_from_aseg(aparc_aseg, wm_aseg())
    gm = mask_from_aseg(aparc_aseg,  gm_aseg())
    pibi = mask_from_aseg(aparc_aseg, pibindex_aseg())
    wm,gm,pibi = generate_pibindex_rois_fs(aparc_aseg)
    wmf = pp.fname_presuffix(aparc_aseg, prefix='wm_')
    gmf = pp.fname_presuffix(aparc_aseg, prefix='gm_')
    pibif = pp.fname_presuffix(aparc_aseg, prefix='pibindex_')
    aff = ni.load(aparc_aseg).get_affine()
    to_file(wm, aff, wmf)
    to_file(gm, aff, gmf)
    to_file(pibi, aff, pibif)
    rois = [gmf, wmf, pibif]
    rsfs = compute_rsf(rois)
    transfer_mtx = gen_transfer_matrix(rsfs, rois)
    obs = get_observed_conc(dvr, rois)
    correct = calc_pvc_values(transfer_mtx, obs)

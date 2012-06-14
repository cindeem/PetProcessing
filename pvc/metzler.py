# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python
import sys
import numpy as np
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing/pvc')
import ecat_smooth as es
import nibabel as ni
import nipype.interfaces.freesurfer as freesurfer
import nipy
import nipy.algorithms

def make_pvc(pet, psf_brainmask, brainmask, prefix = 'pvc_'):
    """ uses the given per psf brain mask to correct the data in pet
    """
    pimg = ni.load(pet)
    psfdat = ni.load(psf_brainmask).get_data()
    bmaskdat = ni.load(brainmask).get_data()
    
    pdat = pimg.get_data().copy()
    pvc_pdat = pdat / psfdat
    pdat[bmaskdat > 0] = pvc_pdat[bmaskdat > 0]
    newimg = ni.Nifti1Image(pdat, pimg.get_affine(), ni.Nifti1Header())
    outfile = pp.prefix_filename(pet, prefix=prefix)
    newimg.to_filename(outfile)
    return outfile


def binarize_erode_mask(infile, min = 0.05, erode = 1):
    """ use freesurfer to binarize and erode a mask"""
    outfile = pp.prefix_filename(infile,
                                 prefix='ero%d_%2.2fbin_'%(erode, min))
                                 
    bin = freesurfer.Binarize()
    bin.inputs.in_file = infile
    bin.inputs.min = min
    bin.inputs.binary_file = outfile
    bin.inputs.erode = erode
    binout = bin.run()
    return binout


def make_aseg_brainmask(infile):
    """ uses a subject aseg.nii to generate a brainmask that
    does not contain ventricles etc
    <infile>  is the subjects aseg.nii
    creates a new file aseg_brainmask.nii in same directory
    as the original aseg.nii file"""
    maskint = ((2,3), (7,13), (16, 20), (26,28),(41,42), (46,56),
               (58,60),(77,77),(251,255))
    aseg = ni.load(infile)
    asegd = aseg.get_data()

    newdat = np.zeros(aseg.get_shape())
    for low, high in maskint:
        tmp = np.logical_and(asegd>= low, asegd<=high)
        newdat[tmp] = 1

    newimg = ni.Nifti1Image(newdat, aseg.get_affine())
    outfile = infile.replace('aseg', 'aseg_brainmask')
    newimg.to_filename(outfile)
    return outfile

def smooth_mask_spm(mask, fwhm = 7):
    sout = pp.spm_smooth([mask] , fwhm=fwhm)
    
    if not sout.runtime.returncode ==0:
        print sout.runtime.stderr # changed from sout.runtime.stderr

        return None
    else:
        return sout.outputs.smoothed_files    


def smooth_mask_nipy(infile, outfile, fwhm=14):
    """uses nipy to smooth an image using gaussian filter of fwhm"""
    img = nipy.load_image(infile)
    lf = nipy.algorithms.kernel_smooth.LinearFilter(img.coordmap,
                                                    img.shape,
                                                    fwhm)
    simg = lf.smooth(img)
    outimg = nipy.save_image(simg, outfile)
    return outimg

def calc_pvc(pet, mask, smask):
    petpsf = es.PetPsf(smask)
    xyresult = petpsf.convolve_xy()
    zresult = petpsf.convolve_z()
    petpsf_brainmask  = petpsf.save_result()
    pvcpet = make_pvc(pet, petpsf_brainmask,
                      mask, prefix='pvcfs_')
    return pvcpet
    

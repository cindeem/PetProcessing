
"""
using freesurfer parcellations
1. gen GM, WM (CSF,dilate aparc mask mri_binarize by 5, mask with aparc mask)
2. smooth using 7mm fwhm (and later PET psf)
3. write to new directory so I can pull ROI based estimates of signal


"""
import sys, os
import numpy as np

import pandas
import nibabel as ni
import nipy
from nipy.algorithms.kernel_smooth import LinearFilter
from nipype.interfaces.freesurfer import Binarize

sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import utils



fwhm = 7


def mask_from_aseg(aparc_aseg, labels, outfile):
    """ generate binary mask based on labels from aparc aseg
    returns binary array"""
    aff = ni.load(aparc_aseg).get_affine() 
    labeldat = ni.load(aparc_aseg).get_data()
    binary = np.zeros(labeldat.shape)
    for label in labels:
        binary[labeldat == label] = 1
    newimage = ni.Nifti1Image(binary, aff)
    newimage.to_filename(outfile)
    return outfile

try:
    datadir = sys.argv[1]
    csvf = sys.argv[2]
except:
    datadir = '/home/jagust/cindeem/wonky_ecats' 
    csvf = 'fs_desikan_GM.csv'

globstr = os.path.join(datadir, 'B*')
allsub = sorted(utils.glob(globstr))
if len(allsub) < 1:
    raise IOError('no subjects found in %s'%datadir)

for sub in allsub:
    _, subid = os.path.split(sub)
    globstr = os.path.join(datadir, subid, 'pib', 'coreg*')
    coregdir = utils.find_single_file(globstr)
    if coregdir is None:
        print 'SKIP: %s: %s not found'%(subid, globstr)
        continue 
    """ go in coreg and find raparc
    use csv file to make mask
    if ventricle in csv file, also dialte to get outter pial csf
    make , directory in coreg pvc_fwhmXX
    """
    pvcdir, exists = utils.make_dir(coregdir, 'PVC_fwhm%02d'%fwhm)
    # look for exisiting file
    _, nme, _ = utils.split_filename(csvf)
    globstr = os.path.join(pvcdir,'%s*'%nme)
    pvcfile = utils.find_single_file(globstr)
    if pvcfile is not None:
        print 'SKIP: %s : %s found'%(subid, pvcfile)
        continue
    ### find raparc
    globstr = os.path.join(coregdir, 'rB*aparc_aseg.nii*')
    aparc = utils.find_single_file(globstr)
    if aparc is  None:
        print 'SKIP: %s : %s NOT found'%(subid, globstr)
    roid = pandas.read_csv(csvf, header = None, sep=None, index_col = 0)
    outf = os.path.join(pvcdir, '%s.nii.gz'%nme)
    outf = mask_from_aseg(aparc, [x[0] for x in roid.values], outf)
    if 'ventricle' in csvf:
        ## make outer CSF
        outcsff = outf.replace('ventricle', 'outer_CSF') 
        mybin = Binarize()
        mybin.inputs.min = 1
        mybin.inputs.in_file = aparc
        mybin.inputs.dilate = 5
        mybin.inputs.binary_file = outcsff
        res = mybin.run()
        # mask with bin aparc
        img = ni.load(outcsff)
        dat = img.get_data()
        aparc_dat = ni.load(aparc).get_data()
        dat[aparc_dat > 0] = 0
        ## add ventricles
        ventdat = ni.load(outf).get_data()
        dat[ventdat == 1] = 1
        outf = outcsff.replace('outer_CSF', 'CSF')
        newimg = ni.Nifti1Image(dat, img.get_affine())
        newimg.to_filename(outf)
        

    img = nipy.load_image(outf)
    lf = LinearFilter(img.coordmap,
                      img.shape,                                                                      fwhm)
    simg = lf.smooth(img)
    smoothfile = utils.fname_presuffix(outf, prefix='s%02d_'%fwhm)
    smoothfile = nipy.save_image(simg, smoothfile)
    print '%s: wrote %s'%(subid, smoothfile)
         









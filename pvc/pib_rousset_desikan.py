

"""
for each subject (young)
find raparc
generate pvc_rousset_desikan
(tho only fixed number of regions)
subcortical + cortical
WM
CSF
GM

smooth (this time only 7mm fwhm)

find true concentration and write to csv file
"""
import os, sys
import numpy as np
from glob import glob

import pandas
import nibabel as ni
import nipy
from nipy.algorithms.kernel_smooth import LinearFilter
from nipype.interfaces.freesurfer import Binarize

sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import utils

import rousset as rpvc

def smooth_roi(roif, fwhm=7):
    """ uses nipy to smooth binary image using fwhm kernel"""
    img = nipy.load_image(roif)
    smoothfile = utils.fname_presuffix(roif, prefix='s%02d_'%(fwhm))
    lf = LinearFilter(img.coordmap, img.shape, fwhm)
    simg = lf.smooth(img)
    smoothf = nipy.save_image(simg, smoothfile)
    return smoothfile


def make_brainmask(aparc, outdir):
    img = ni.load(aparc)
    dat = img.get_data()
    mask = dat > 0
    newimg = ni.Nifti1Image(mask.astype(int), img.get_affine())
    newf = os.path.join(outdir, 'aparc_mask.nii.gz')
    newimg.to_filename(newf)
    return newf


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


def make_csf(aparc, labels, outdir):
    """ given a labelled image (aparc) and relevent labels
    make a dilated mask, mask with original, and add ventricle regions
    """
    outercsf_file = os.path.join(outdir, 'outer_csf.nii.gz')
    ## make outer
    mybin = Binarize()
    mybin.inputs.min = 1
    mybin.inputs.in_file = aparc
    mybin.inputs.dilate = 5
    mybin.inputs.binary_file = outercsf_file
    res = mybin.run()
    # mask with bin apparc
    img = ni.load(outercsf_file)
    dat = img.get_data()
    aparc_dat = ni.load(aparc).get_data()
    dat[aparc_dat > 0] = 0
    ventricles = os.path.join(outdir, 'ventricles.nii.gz')
    ventricles = mask_from_aseg(aparc, labels, ventricles) 
    ventdat = ni.load(ventricles).get_data()
    dat[ventdat == 1] = 1
    final_csf = os.path.join(outdir, 'CSF.nii.gz')
    newimg = ni.Nifti1Image(dat, img.get_affine())
    newimg.to_filename(final_csf)
    return final_csf


if __name__ == '__main__':
    fwhm = 7
    try:
        datadir = sys.argv[1]
    except:
        datadir = '/home/jagust/cindeem/wonky_ecats'

    wm_file = 'fs_desikan_WM.csv'
    ventfile = 'fs_desikan_ventricle.csv'
    gm_regions = 'fs_desikan_cortical_GM_regions.csv'
    dvr_type = 'dvr_rwhole*'

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
        dvrdirglob = os.path.join(sub, 'pib',dvr_type)
        ## used this when I wanted grey_cere only, comment out for whole
        ##dvrdir = [x for x in glob(dvrdirglob) if not 'whole' in x]
        dvrdir = glob(dvrdirglob)
        try:
            dvrdir = dvrdir[0]
        except:
            print '%s: no %s'%(subid, dvrdirglob)
            continue
        ## get raparc
        globstr = os.path.join(datadir, subid, 'pib', 'coreg*')
        coregdir = utils.find_single_file(globstr)
        if coregdir is None:
            print 'SKIP: %s: %s not found'%(subid, globstr)
            continue
        globstr = os.path.join(coregdir, 'rB*aparc_aseg.nii*')
        aparc = utils.find_single_file(globstr)
        if aparc is  None:
            print 'SKIP: %s : %s NOT found'%(subid, globstr)
            continue

        ### make new pvc directory
        pvcdir, exists = utils.make_dir(dvrdir, 'rousset_desikan_fwhm%02d'%fwhm)
        if exists:
            print '%s: EXISTS: %s'%(subid, pvcdir)
            continue
        ##
        ## make rois
        fullbrain = make_brainmask(aparc, pvcdir)        
        ## CSF
        csfd = pandas.read_csv(ventfile, header=None, 
                sep=None, index_col=0)
        csf = make_csf(aparc, [x[0] for x in csfd.values], pvcdir)
        ## WM
        wmd = pandas.read_csv(wm_file, header=None,sep=None, index_col=0)
        wm = os.path.join(pvcdir, 'wm.nii.gz')
        wm  = mask_from_aseg(aparc, [x[0] for x in wmd.values], wm)
        ## make cortical regions
        allgm = []
        allgmdat = ni.load(fullbrain).get_data()
        gmd = pandas.read_csv(gm_regions, header=None,sep=None, index_col=0)
        for item in gmd.iterrows():
            name = item[0]
            label = item[1][1]
            tmpf = os.path.join(pvcdir, '%s.nii.gz'%name)
            tmpf = mask_from_aseg(aparc, [label], tmpf)
            allgm.append(tmpf)
            tmpdat = ni.load(tmpf).get_data()
            allgmdat[tmpdat > 0] = 0
        ## write last gm mask (all but regions defined)
        for item in [wm, csf]:
            tmpdat = ni.load(item)
            allgmdat[tmpdat > 0] = 0
        leftovergm = ni.Nifti1Image(allgmdat, ni.load(wm).get_affine())
        gm = os.path.join(pvcdir, 'leftovergm.nii.gz')
        leftovergm.to_filename(gm)
        ## smooth everything and make rsfs
        allsmooth = []
        allrois = allgm + [ wm, csf]
        shape = ni.load(wm).get_shape()
        fullshape = tuple([len(allrois)] + list(shape))
        rsfs = np.zeros(fullshape)
        for val, roi in enumerate(allrois):
            sroi = smooth_roi(roi, fwhm=7)
            allsmooth.append(sroi)
            rsfs[val, :,:,:] = ni.load(sroi).get_data()

        transfer_matrix = rpvc.gen_transfer_matrix(rsfs, allrois)
        # get dvr
        dvrglob = os.path.join(dvrdir, 'DVR*.nii*')
        dvr = utils.find_single_file(dvrglob)
        if dvr is None:
            print '%s: no DVR %s'%(subid, dvrglob)
            continue
        observed = rpvc.get_observed_conc(dvr, allrois)
        corrected = rpvc.calc_pvc_values(transfer_matrix, observed)
        np.save(os.path.join(pvcdir, 'corrected.npy'), corrected)
        roinames = [os.path.split(x)[1].replace('.nii.gz','') for x in allrois]
        df = pandas.DataFrame(corrected, 
                index=roinames, columns=['corrected',])
        df['observed'] = observed
        dfile = os.path.join(pvcdir, '%s_rousset_corrected.csv'%subid)
        df.to_csv(dfile)
        print 'saved %s'%dfile



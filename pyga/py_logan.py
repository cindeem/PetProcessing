# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import os
from glob import glob
import time
import tempfile
import numpy as np
import nibabel as ni
import scipy.integrate
import matplotlib.pyplot as plt

 
def get_ref(refroi, dat):
    """given region of interest, extracts mean for each frame
    in dat, returns vector of means across time
    """
    refdat = ni.load(refroi).get_data().squeeze()
    if not refdat.shape == dat.shape[:-1]:
        raise IOError('%s has shape %s, not %s'%(refroi, refdat.shape, 
                                                 dat.shape[1:]))
    means = np.zeros(dat.shape[-1])
    refdat = np.nan_to_num(refdat)
    for val,slice in enumerate(dat.T):
        ind = np.logical_and(slice > 0,
                             refdat.T > 0)
        means[val] = slice[ind].mean()
    return means


def midframes_from_file(infile, units='sec'):
    """infile is a frametimes file each row has
    [frame number, start dur, stop] in seconds

    Returns
    -------
    midframes: vector of start-dur/2
    starttimes: vector of durations
    """
    ft = np.loadtxt(infile, delimiter = ',',
                    usecols = (1,2,3), skiprows = 1)
    midframes = ft[:,0] + ft[:,1] / 2
    return midframes, ft[:,1]

def frametimes_from_file(infile):
    """infile is a frametimes file each row has
    [frame number, start dur, stop] in seconds

    Returns
    -------
    ft: array [start, duration, stop] in seconds for each frame
    """
    ft = np.loadtxt(infile, delimiter = ',',
                    usecols = (1,2,3), skiprows = 1)
    return ft

def is_iterable(input):
    """checks if object can be iterated"""
    if hasattr(input, '__iter__'):
        return True
    else:
        return False

def load_3d(infiles):
    """given a list of 3d frames, load into 4D array
    retun array of shape (frame, x, y, z) with nan removed"""
    tmp = ni.concat_images(infiles)
    return np.nan_to_num(tmp.get_data())

def get_data_nibabel(infiles):
    """ uses nibabel to open nifti file
    and return a 4d array of data"""
    if is_iterable(infiles):
        # set of 3D frames
        dat4d = load_3d(infiles)
        return dat4d
    else:
        print '4d files not supported yet'
        return None

def mask_data(mask, dat4d):
    """given a mask file and a 4d array
    mask data with data in maskfile
    return maksed_data and mask_bool"""
    nframes = dat4d.shape[-1]
    maskdat = ni.load(mask).get_data().squeeze()
    if not maskdat.shape == dat4d.shape[:-1]:
        raise IOError('shape mismatch, %s: %s and dat4d: %s'%(mask,
                                                              maskdat.shape,
                                                              dat4d.shape[:-1]))
    # mask for both anatomical and PET data (logical_and mask
    data_mask = dat4d.all(axis=-1) > 0
    fullmask = np.logical_and(maskdat>0, data_mask)
                             
    new = np.empty((fullmask[fullmask].size,nframes))
    for i in np.arange(nframes):
        new[:,i] = dat4d[:,:,:,i][fullmask].flatten()
    new.shape = (fullmask[fullmask].size, nframes)
    return new, fullmask

def get_ki_vd_lstsq(x,y):
    """solves best fitting line using np.linalg.lstsq
    """
    x = np.vstack([x,np.ones(x.shape[0])]).T
    results = np.linalg.lstsq(x,y)
    ki, vd = results[0]
    residues = results[1]
    return ki,vd,residues

def get_ki_vd_polyfit(x,y):
    """ solves using np.polyfit
    """
    output = np.polyfit(x,y,1,full=True)
    ki,vd = output[0]
    resids = output[1]
    return ki, vd, resids



def integrate_reference(reference_data, delta_time):
    """
    returns a cumulative integration of reference_data with delta_time
    uses np.cumtrapz"""
    int_ref = np.zeros(reference_data.shape)
    int_ref[1:] = scipy.integrate.cumtrapz(reference_data, delta_time)
    return int_ref

    
def save_inputplot(ref, midframes, outdir):
    """saves input TAC to png figure
    """
    fig = plt.figure()
    fig.set_label('Reference TAC')
    ax1 = fig.add_subplot(111)
    ax1.plot(midframes,ref, 'ko-')
    ax2 = ax1.twiny()
    ax1.set_xlabel('midframe times (sec)')
    ax1.set_ylabel('counts bq/ml')
    ax2.set_xlabel('midframe times (min)')
    xticks_minutes = (ax1.get_xticks() / 60.).round()
    ax2.set_xticks(xticks_minutes)
    ax1.grid()
    basename = 'REF_TAC_%s'%(time.strftime('%Y-%m-%d-%H-%M'))
    figname = os.path.join(outdir, '%s.png'%(basename))
    plt.savefig(figname, format='png') 
    fig.clf()
    return figname
  
def save_data2nii(data, reference_img, filename='generic_file',outdir='.'):
    """saves data to nifti file given affine info in reference_img
    and data array"""
    img = ni.load(reference_img)
    data = np.reshape(data, img.get_shape())
    out_img = ni.Nifti1Image(data, img.get_affine())
    outfile = os.path.join(outdir, '%s_%s.nii.gz'%(filename,time.strftime('%Y-%m-%d-%H-%M')))
    out_img.to_filename(outfile)
    return outfile
    

def repmat_1d(x, n):
    """ make new matrix of n copies of x
    resulting array has shape (n, x.shape)"""
    newx = np.tile(x, n)
    newx.shape = tuple([n] + [i for i in x.shape])
    return newx

def calc_xy(ref, masked_dat,midtimes, k2ref=.15):
    """calculates the x and y terms used in Logan Graphical Analysis
    y = integrated_data / data
    x = integrated_reference / data + (1 / k2ref) * reference / data
    """
    big_durs = repmat_1d(midtimes,masked_dat.shape[0])
    int_dat = scipy.integrate.cumtrapz(masked_dat.T,big_durs.T,axis=0)
    big_ref = repmat_1d(ref,masked_dat.shape[0])
    int_ref = scipy.integrate.cumtrapz(big_ref.T,big_durs.T, axis=0)
    y = (int_dat.T)  / masked_dat[:,1:]# 33, nvox in mask
    x = (int_ref.T / masked_dat[:,1:]) + ( 1 / k2ref) *(big_ref[:,1:] / masked_dat[:,1:]) 
    return x,y



    

def get_lstsq(x,y):
    """solves best fitting line using np.linalg.lstsq
    """
    if np.all(x == 0) or np.all(y == 0):
        return 0.,0.,0.
    newx = np.ones((x.shape[0],2))
    newx[:,0] = x
    results = np.linalg.lstsq(newx,y)
    ki, vd = results[0]
    residues = results[1]
    return ki,vd,residues

def calc_ki(x,y, timing_file, range=(35,90)):
    """ calculates ki of data given reference, timing file,
    and range of steady state data (in minutes)"""
    ft = frametimes_from_file(timing_file)
    start_end = np.logical_and(ft[1:,0] / 60. >= range[0],
                               ft[1:,2] / 60. <= range[1])
    if len(x.shape) == len(y.shape) == 1:
        ## regional ki
        allki, allvd, residues = get_lstsq(x[start_end],y[start_end])
        return allki, allvd, residues
    else:    
        allki = np.zeros(x.shape[0])
        resids = np.zeros(x.shape[0])
        for val, (tmpx, tmpy) in enumerate(zip(x,y)):
            ki,vd,residues = get_lstsq(tmpx[start_end],tmpy[start_end])
            allki[val] = ki
            resids[val] = residues
            allvd = None
    return allki, allvd, resids

def results_to_array(results, mask):
    """ puts values in results back in fill data array
    of size shape using values in boolean mask"""
    dat = np.zeros(mask.shape)
    dat[mask] = results
    return dat

def loganplot(ref,region, timingf, outdir):
    """given (ref), and  (region)
    calculate best fit line"""
    midtimes, durs = midframes_from_file(timingf)
    refx, refy = region_xy(ref, ref, midtimes)
    rx,ry = region_xy(ref, region, midtimes)
    slope, intercept, err = calc_ki(rx,ry, timingf)
    refslope, refintercept, referr = calc_ki(refx, refy, timingf)
    fity = rx * slope + intercept
    fitrefy = refx * refslope + refintercept
    fig = plt.figure() 
    fig.set_label('Logan Plot')
    ax1 = fig.add_subplot(111)

    ax1.plot(rx, ry, 'ro', label = 'pibindex')
    ax1.plot(refx, refy, 'bo', label = 'ref region')
    ax1.plot(rx, fity, 'k-', label = 'region slope : %2.2f'%slope)
    ax1.plot(refx, fitrefy, 'b-', label='ref slope : %2.2f'%refslope)
    ax1.legend(loc='lower right')
    ax1.set_ylabel('$\int data / data$')
    ax1.set_xlabel('$(\int ref / data) + (1 / k2rf) * t / data$')
    outfile = os.path.join(outdir, 'loganplot.png')
    plt.savefig(outfile)
    plt.clf()


def region_xy(ref, region, midtimes, k2ref = .15):
    """ used to calc cumulative integral
    for one dimensional region"""
    int_dat = scipy.integrate.cumtrapz(region,midtimes,axis=0) 
    int_ref = scipy.integrate.cumtrapz(ref.squeeze(), midtimes, axis=0)
    y = int_dat / region[1:]
    x = (int_ref / region[1:]) + ( 1 / k2ref) *(midtimes[1:] / region[1:])
    return x, y


def get_labelroi_data(data, labelf, labels):
    """ given a 4d volume of data (array), a 3d file with label rois
    and a set of labels, extract mean of data (made from combining
    labels)
    """
    labeldat = label_mask(labelf, labels)
    assert data.shape[:3] == labeldat.shape
    means = np.zeros(data.shape[3])
    for val,slice in enumerate(data.T):
        ind = np.logical_and(slice > 0,
                             labeldat.T > 0)
        means[val] = slice[ind].mean()
    return means

def label_mask(labelf, labels):
    """ given a label image and a set of labels
    return the combined label mask"""
    dat = ni.load(labelf).get_data()
    new = np.zeros(dat.shape)
    for label in labels:
        new[dat == label] = 1
    return new



def generate_region(data, labels):
    """given a data file with labels, generate
    a new binary mask made up of labels"""
    tmpdir = tempfile.mkdtemp()
    img = ni.load(data)
    newdat = np.zeros(img.get_shape())
    for label in labels:
        newdat[data == label ] = 1
    newimg = ni.Nifti1Image(newdat, img.get_affine())
    outf = os.path.join(tmpdir, 'labelmask.nii.gz')
    newimg.to_filename(outf)
    return outf


if __name__ == '__main__':

    root = '/home/jagust/cindeem/CODE/GraphicalAnalysis/pyGA_refactor/test/pib2'
    k2ref = 0.15
    range = (35,90)
    frames = glob(root + '/rB*PIB*.nii*')
    frames.sort()
    refroifile = '%s/rgrey_cerebellum.nii.gz'%root
    mask = '%s/rbrainmask.nii.gz'%root
    timing_file = '%s/frametimes.csv'%root
    aparc = '%s/rB09-210_v1_aparc_aseg.nii.gz'%root
    midtimes, durs = midframes_from_file(timing_file)
    data4d = get_data_nibabel(frames)
    
    ref = get_ref(refroifile, data4d)
    ref_fig = save_inputplot(ref, (midtimes + durs/2.), root)
    masked_data, mask_roi = mask_data(mask, data4d)
    x,y  = calc_xy(ref,masked_data, midtimes)
    allki,allvd, residuals = calc_ki(x, y, timing_file, range=range)
    dvr = results_to_array(allki, mask_roi)
    # logan plot
    labels = [1003,
              1012,1014,1018,1019,1020,1027,1028,1032,1008,
              1025,1029,1031,1002,1023,1010,1026,2003,
              2012,2014,2018,2019,2020,2027,2028,2032,2008,
              2025,2029,2031,2002,2023,2010,2026,1015,1030,
              2015,2030,2009,1009]

    region_x =  get_labelroi_data(data4d, aparc, labels)
    
    loganplot(ref,region_x, timing_file, root)
    save_data2nii(dvr, mask, filename='DVR', outdir=root)
    
    


            
    
            
            
        
        

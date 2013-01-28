from os.path import (abspath, join, split)
import sys, re
import dicom
from dicom.dataset import Dataset, FileDataset
import nibabel as ni
from glob import glob
from utils import get_subid

def get_dicoms(indir):
    """ given an indir (dicomdirectory)
    finds all dicoms and removes any nifti files"""
    
    result = glob(join(indir, '*'))
    result = [x for x in result if not '.nii' in x] # remove niftis
    result.sort()
    dmap, nslices = get_slicenumber_dict(result)
    return  get_vol_slicefiles(dmap, nslices)

def get_slicenumber_dict(dicoms):
    """ given set of dicom files, creates map
    verifying slice number and filename
    returns dict mapping slicen->file, and nslices
    """
    dmap = {}
    for d in dicoms:
        plan = dicom.read_file(d)
        slicen = plan.ImageIndex
        dmap.update({slicen:d})
    nslices = plan.NumberOfSlices
    return dmap, nslices

def get_vol_slicefiles(dmap, nslices):
    """for a dict of slicen->file
    returns list of files sorted in order of slicen"""
    skeys = sorted(dmap.keys())
    volume_keys = skeys[:nslices]
    return [dmap[k] for k in volume_keys]

def raw_dicom():
    """ Set up a raw dicom data dict"""
    file_meta = Dataset()
    return file_meta

    
    
def label_fromdata_dict(img):
    """ grabs meta data from original dicom"""
    rows, columns, slices = img.get_shape()
    hdr = img.get_header()
    zooms = hdr.get_zooms()
    raw_data = hdr.raw_data_from_fileobj(img.get_filename()) #unscaled data
    max = raw_data.max()
    min = raw_data.min()
    slope, inter = hdr.get_slope_inter()
    d = {'Rows': rows,
         'Columns':columns,
         'Pixel Spacing': zooms[0],
         'Bits Allocated': 16,
         'Bits Stored': 16,
         'Largest Image Pixel Value' : max.item(),
         'Smallest Image Pixel Value': min.item(),
         'Rescale Intercept': inter,
         'Rescale Slope': slope,
         'Slice Thickness' : zooms[-1],
         }
    if d['Smallest Image Pixel Value'] < 0:
        d['Smallest Image Pixel Value'] = 0
    return d, raw_data


def update_plan(plan, imgd):
    """ given an existing dicom plan, updates for new data"""
    for item in plan:
        if item.name in imgd.keys():
            if item.name in  ['Slice Thickness',
                              'Pixel Spacing',
                              'Rescale Slope',
                              'Rescale Intercept']:
                plan[item.tag].VR = 'FL'
            plan[item.tag].value = imgd[item.name]

def nifti_to_dicom(nifti, dicomdir, outdir):
    """ converts nifti to dicom file using pre-existing dicom
    meta-data"""
    # load processsed data
    img = ni.load(nifti)
    (x,y,z) = img.get_shape()[:3]
    subid = get_subid(nifti)
    # get original dicoms only for slices in first frame
    frame_files = get_dicoms(dicomdir)

    #raise error if number of slices in volume doesnt match dicoms
    assert( len(frame_files) == z)

    dicom_mapping, raw_data = label_fromdata_dict(img)

    for slicen, tmpfile in enumerate(frame_files):
        data_slice = raw_data[:,:,::-1][:,:,slicen]
        plan = dicom.read_file(tmpfile)
        plan.NumberOfTimeSlices = 1
        # causes unreadable update_plan(plan, dicom_mapping)
        
        plan.PixelData = data_slice.transpose()
        newfile = join(outdir, '%s_%s_5.%d.dcm'%(subid,
                                                 plan.ProtocolName,
                                                 plan.ImageIndex)
                       )
        print newfile
        plan.save_as(newfile)
        

from os.path import (abspath, join, split)
import sys, re
import dicom
from dicom.dataset import Dataset, FileDataset
import nibabel as ni
from glob import glob
from utils import (get_subid, make_rec_dir,make_dir, copy_file,
                   copy_files, tar_cmd, copy_tmpdir)

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
        
### DICOM TO NIFTI

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

import os, sys
import numpy as np
import nibabel as ni
import nipype.algorithms.rapidart as rapidart
from glob import glob
import nipype.interfaces.fsl as fsl
import nipype.algorithms.misc as misc
import json
import nipy
import nipy.algorithms.diagnostics as diag
from nipype.utils.filemanip import fname_presuffix
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import base_gui as bg
import argparse

def make_4d_nibabel(infiles,outdir=None):
    shape = ni.load(infiles[0]).get_shape()
    finalshape = tuple([x for x in shape]+[len(infiles)])
    dat4d = np.empty(finalshape)
    for val, f in enumerate(infiles):
        tmpdat = ni.load(f).get_data()
        tmpdat[np.isnan(tmpdat)] =  0
        dat4d[:,:,:,val] = tmpdat
    newimg = ni.Nifti1Image(dat4d, ni.load(infiles[0]).get_affine())
    if outdir is None:
        outf = fname_presuffix(infiles[0], prefix='data4d_')
    else:
        outf = fname_presuffix(infiles[0], prefix='data4d_',newpath = outdir)
    newimg.to_filename(outf)
    return outf

        
def make_4d(infiles):
    merge = fsl.utils.Merge()
    merge.inputs.in_files = infiles
    merge.inputs.dimension = 't'
    mrgout = merge.run()
    return mrgout.outputs.merged_file
    
def outlier_vol_fromfile(mean, outliers, fname = None):
    _, filename = os.path.split(mean)
    vox = np.loadtxt(outliers).astype(int)
    img = ni.load(mean)
    newdat = np.zeros(img.get_shape()).flatten()
    newdat[vox] = 100
    newdat.shape = img.get_shape()
    newimg = ni.Nifti1Image(newdat, img.get_affine())
    if fname is None:
        newfile = filename.replace('mean', 'outliers')
    newfile = fname
    newimg.to_filename(newfile)
    print os.path.abspath(newfile)

def gen_sig2noise_img(in4d, outdir):
    startdir = os.getcwd()
    os.chdir(outdir)
    tsnr = misc.TSNR()
    tsnr.inputs.in_file = in4d
    tsnrout = tsnr.run()
    ## there is no valid return code for tsnr 
    #if tsnrout.runtime.returncode == 0:
    #    return tsnrout.outputs.tsnr_file
    #else:
    #    print tsnrout.runtime.stderr
    #    return None
    os.chdir(startdir)
    return tsnrout.outputs.tsnr_file

def make_qa_dir(inroot, name='data_QA'):
    qadir = os.path.join(inroot, name)
    if os.path.isdir(qadir):
        return qadir, True
    else:
        os.mkdir(qadir)
        return qadir, False

def run_artdetect(file4d, param_file, thresh = 4, param_source='SPM'):
    startdir = os.getcwd()
    pth, _ = os.path.split(param_file)
    os.chdir(pth)
    ad = rapidart.ArtifactDetect()
    ad.inputs.realigned_files = file4d
    ad.inputs.realignment_parameters = param_file
    ad.inputs.parameter_source = param_source
    ad.inputs.norm_threshold = 1
    ad.inputs.mask_type = 'spm_global'
    ad.inputs.use_differences = [True, False]
    ad.inputs.zintensity_threshold = thresh
    adout = ad.run()
    os.chdir(startdir)
    return adout

def screen_data_dirnme(in4d, outdir):
    """uses nipy diagnostic code to screen the data for
    outlier values and saves results to three images
    mean, std, pca, in same dir as original file(s)"""
    img = nipy.load_image(in4d)
    result = diag.screen(img)
    # save mean, std, pca
    pth, nme = os.path.split(in4d)
    stripnme = nme.split('.')[0]
    
    pcafile = os.path.join(outdir,
                           'QA-PCA_%s.nii.gz'%(nme))
    meanfile = os.path.join(outdir,
                            'QA-MEAN_%s.nii.gz'%(nme))
    stdfile = os.path.join(outdir,
                           'QA-STD_%s.nii.gz'%(nme))
    nipy.save_image(result['mean'], meanfile)
    nipy.save_image(result['std'], stdfile)
    nipy.save_image(result['pca'], pcafile)
    print 'saved: %s\n \t%s\n \t%s\n'%(pcafile, meanfile, stdfile)

def save_qa_img_dirnme(in4d, outdir):
    pth, nme = os.path.split(in4d)
    img = nipy.load_image(in4d)
    diag.plot_tsdiffs(diag.time_slice_diffs(img))
    cleantime = time.asctime().replace(' ','-').replace(':', '_')
    figfile = os.path.join(outdir, 'QA_%s_%s.png'%(nme, cleantime))
    pylab.savefig(figfile)


def main(infile, param_file, param_source, thresh, outdir=None):

    
    if len(infile) > 1:
        # input is list, need to merge
        if outdir is None:
            outdir, _ = os.path.split(infile[0])
        qadir, exists = make_qa_dir(outdir)
        if exists:
            print '%s exists, remove to re-run'%qadir
            return None
        merged = make_4d_nibabel(infile,outdir=qadir)
    else:
        merged = infile[0]
        if outdir is None:
            outdir, _ = os.path.split(merged)
        qadir, exists = make_qa_dir(outdir)
        if exists:
            print '%s exists, remove to re-run'%qadir
            return None
    param_file = utils.copy_file(param_file, qadir)
    artout = run_artdetect(merged, param_file, thresh, param_source)

    vox_outliers =  artout.outputs.outlier_files

    statd = json.load(open(artout.outputs.statistic_files))
    mot = statd[1]['motion_outliers']
    intensity = statd[1]['intensity_outliers']
    if mot > 0:
        try:
            tmp = np.loadtxt(artout.outputs.outlier_files)[:mot]
        except:
            tmp = np.loadtxt(artout.outputs.outlier_files)
	tmp.tofile(os.path.join(qadir,'bad_movement_frames.txt'), 
                   sep='\n')
    np.array([mot,intensity]).tofile(os.path.join(qadir,
                                                  'motion_intensity_outliers'),
                                     sep = '\n')
    print 'QA written to %s'%(qadir)
        

if __name__ == '__main__':

    # create the parser
    parser = argparse.ArgumentParser(
        description='Artifact Detection on fMRI ')

    # add the arguments
    parser.add_argument(
        'infiles',
        type = str,
        nargs = '+', # one or more items
        help = 'file(s) 4d or multiple 3d of fMRI series')
    parser.add_argument(
        '-params',
        dest = 'params',
        help = 'Movement parameters txt file')
    parser.add_argument(
        '-params_source',
        dest = 'params_source',
        default = 'SPM',
        help = 'Params are from SPM or FSL (defualt SPM), specify which')
    parser.add_argument(
        '-thresh',
        type = int,
        dest = 'thresh',
        default = 4,
        help = 'Intensity threshold (default 4)')
    parser.add_argument(
        '-outdir',        
        dest = 'outdir',
        help = """Optional output directory (QA_data folder will be created
        in this base direcoty if sepcified,
        otherwise in directory of infiles""")
    
    if len(sys.argv) ==1:
        parser.print_help()
    else:
        args = parser.parse_args()
        print args
        main(args.infiles,
             args.params,
             args.params_source,
             args.thresh,
             args.outdir)
        
  

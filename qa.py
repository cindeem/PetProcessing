import os
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
import statsmodels.robust.scale as scale
import matplotlib.pyplot as plt
import time


def plot_movement(infile, subid):
    """given a file from spm with movement parameters
    plots a figure with 2 subplots
    plot1: movement in x, y, z
    plot2, rotational movement
    """
    dat = np.loadtxt(infile)
    plt.figure(figsize=(12,6))
    plt.subplot(211)
    plt.plot(dat[:,0], 'ro-', label='x')
    plt.plot(dat[:,1], 'go-', label='y')
    plt.plot(dat[:,2], 'bo-', label='z')
    plt.legend(loc='upper left')
    plt.title('%s Translations' % subid)
    plt.subplot(212)
    plt.plot(dat[:,3], 'ro-', label='pitch')
    plt.plot(dat[:,4], 'go-', label='yaw')
    plt.plot(dat[:,5], 'bo-', label='roll')
    plt.legend(loc='upper left')
    plt.title('%s Rotations' % subid)
    figfile = infile.replace('.txt', '.png')
    plt.savefig(figfile)
    print 'saved %s'%(figfile)
    plt.close()
    


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

def run_artdetect(file4d, param_file):
    startdir = os.getcwd()
    pth, _ = os.path.split(file4d)
    os.chdir(pth)
    ad = rapidart.ArtifactDetect()
    ad.inputs.realigned_files = file4d
    ad.inputs.realignment_parameters = param_file
    ad.inputs.parameter_source = 'SPM'
    ad.inputs.norm_threshold = 3
    ad.inputs.use_differences = [True, False]
    ad.inputs.zintensity_threshold = 5
    ad.inputs.mask_type = 'thresh'
    ad.inputs.mask_threshold = -100 
    ad.inputs.save_plot = False
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
    plt.savefig(figfile)

def calc_robust_median_diff(in4d):
    """Calculates the robust median fo slice to slice diffs"""
    img = ni.load(in4d)
    dat = img.get_data()
    shape = dat.shape
    tdat = dat.T
    tdat.shape = (shape[-1], np.prod(shape[:-1]))
    dat_diff = tdat[1:,:] - tdat[:-1,:]
    mad = scale.mad(dat_diff, axis=1)
    mad_std = (mad - mad.mean())/ mad.std()
    plt.plot(mad_std, 'ro-')
    plt.title('Robust Frame difference median')
    plt.grid()
    outfile = fname_presuffix(in4d, prefix='Robust_framediff_median',
                              suffix = '.png', use_ext=False)
    plt.savefig(outfile)
    print 'Saved ', outfile
    plt.close()
    

def screen_pet(in4d):
    dat = ni.load(in4d).get_data()
    shape = dat.shape
    tdat = dat.T
    tdat.shape = (shape[-1],shape[-2], np.prod(shape[:-2]))
    slice_var = tdat.var(axis=2)
    slice_var = (slice_var - slice_var.mean()) / slice_var.std()
    tdat.shape = (shape[-1], np.prod(shape[:-1]))
    frame_vars = tdat.var(axis=1)
    frame_vars = (frame_vars - frame_vars.mean()) / frame_vars.std()
    frame_means = tdat.mean(axis=1)
    plt.subplot(411)
    plt.plot(slice_var, 'o-')
    plt.subplot(412)
    plt.plot(frame_vars, 'o-')
    plt.subplot(413)
    plt.plot(frame_means, 'o-')
    plt.subplot(414)
    plt.plot(slice_var.max(axis=1), 'ro-', label='max')
    plt.plot(slice_var.min(axis=1), 'go-', label='min')
    plt.plot(slice_var.mean(axis=1), 'ko-', label='mean')
    plt.legend()
    outfile = fname_presuffix(in4d, prefix='QA_frames',
                              suffix = '.png', use_ext=False)    
    plt.savefig(outfile)
    print 'Saved ', outfile
    plt.close()    
    

if __name__ == '__main__':

    """
    maybe add tool to calculate std for the unwarped_realigned run?)
    """

    startdir = os.getcwd()

    mean = '/home/jagust/pib_bac/ica/data/templates/MNI152_T1_2mm_brain.nii.gz'
    allsubids = glob('/home/jagust/graph/data/spm_220/B*')
    allsubids.sort()
    for sub in allsubids[:]:
        _, subid = os.path.split(sub)
        # get slicetimes make 4d
        globstr = os.path.join(sub, 'func', 'slicetime', 'auB*.nii')
        frames = glob(globstr)
        frames.sort()
        
        qadir, exists = make_qa_dir(sub)
        if exists:
            print qadir, 'exists, skipping'
            continue
        merged = make_4d_nibabel(frames, outdir = qadir)
        param_file = '%s/func/realign_unwarp/rp_%s0000.txt'%(sub, subid)
        
        os.chdir(qadir)
        artout = run_artdetect(merged, param_file)
        vox_outliers =  artout.outputs.outlier_files
        tsnr_file = gen_sig2noise_img(merged, qadir)
        outlier_vol_fromfile(mean, vox_outliers,
                             fname='%s_outliers.nii.gz'%(subid))
        statd = json.load(open(artout.outputs.statistic_files))
        mot = statd[1]['motion_outliers']
        intensity = statd[1]['intensity_outliers']
        if mot > 0:
            tmp = np.loadtxt(artout.outputs.outlier_files)[:mot]
            tmp.tofile('bad_frames.txt', sep='\n')
        np.array([mot,intensity]).tofile('motion_intensity_outliers',
                                         sep = '\n')
        

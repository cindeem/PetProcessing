# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
import base_gui as bg
import qa 
import logging, logging.config
from time import asctime

def find_realigned(pth):
    """ finds realigned files in realign_QA directory"""
    realigndir = 'realign_QA'
    globstr = os.path.join(pth, realigndir, 'rB*_FDG_*nii*')
    tmprealigned = glob(globstr)
    if len(tmprealigned)< 1:
        tmprealigned = None
    tmprealigned.sort()
    globstr = os.path.join(pth, realigndir, 'rp_B*.txt*')
    tmpparameterfile = pp.find_single_file(globstr)
    return tmprealigned, tmpparameterfile 
        
    tmpparameterfile = rlgnout.outputs.realignment_parameters
    

if __name__ == '__main__':
    """
    Uses specified FDG directory
    finds fdg nifti files
    check number of files
    realignes to first
    sum 1-5
    run qa on scans
    """
    # start wx gui app
    app = wx.App()

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose FDG data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    _, scriptnme = os.path.split(__file__)
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(scriptnme, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'FDG'
    user = os.environ['USER']
    logging.info('###START %s :::'%(__file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)

    subs.sort()
    for sub in subs:
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        # find fdg nifti files
        tracerdir = os.path.join(sub, tracer.lower())
        globstr = os.path.join(sub, tracer.lower(), '%s_%s*'%(subid, tracer))
        nifti = bg.glob(globstr)
        
        if len(nifti) < 5:
            logging.warning('fdg frames not found or too few for %s  skipping'%(subid))
            continue
        nifti.sort()
        nifti = pp.unzip_files(nifti)
        hasqa = False
        rlgnout, newnifti = pp.realigntoframe1(nifti)
        if rlgnout is None and newnifti is None:
            logging.warning('%s :existing realign_QA '%(subid))
            tmprealigned, tmpparameterfile = find_realigned(tracerdir)
            if tmprealigned is None or tmpparameterfile is None:
                logging.warning('%s :missing realigned, skipping '%(subid))
                continue
            logging.info('found %s %s'%(tmprealigned, tmpparameterfile))
            tmpparameterfile = pp.unzip_file(tmpparameterfile)
            tmprealigned = [pp.unzip_file(x) for x in tmprealigned]
            hasqa = True
                         
        elif rlgnout.runtime.returncode is not 0:
            logging.warning('Failed to realign %s' % subid)
            continue
        else:
            tmprealigned = rlgnout.outputs.realigned_files
            tmpmean = rlgnout.outputs.mean_image
            tmpparameterfile = rlgnout.outputs.realignment_parameters

            logging.info( 'realigned %s' % subid)

        # make final mean image
        meanimg = pp.make_summed_image(tmprealigned)
            
        # move data back to main directory
        nifti_dir,_ = os.path.split(nifti[0])
        movedmean = pp.copy_file(meanimg, nifti_dir)

        #QA
        if not hasqa:
            logging.info( 'qa %s' % subid)
            qa.plot_movement(tmpparameterfile,subid)
            # get rid of NAN in files
            no_nanfiles = pp.clean_nan(tmprealigned)
            #make 4d volume to visualize movement
            img4d = qa.make_4d_nibabel(no_nanfiles)
            bg.zip_files(tmprealigned)
            #save qa image
            #qa.save_qa_img(img4d)
            qa.plot_movement(tmpparameterfile, subid)
            qa.calc_robust_median_diff(img4d)
            qa.screen_pet(img4d) 
            #remove tmpfiles

            pp.remove_files(no_nanfiles)
            pp.remove_files(newnifti)

        # coreg pons to pet
        # find PONS
        pons_searchstr = '%s/ref_region/pons_tu.nii*' % tracerdir
        pons =  pp.find_single_file(pons_searchstr)
        if 'gz' in pons:
            pons = pp.unzip_file(pons)
        if pons is None:
            logging.warning('no pons_tu found for %s'%(subid))
            continue
        # find MRI
        searchstring = '%s/anatomy/brainmask.nii' % sub
        mri = pp.find_single_file(searchstring)
        if mri is None:
            logging.warning('no brainmask found for %s'%(subid))
            continue
        # find aparc_aseg
        searchstring = '%s/anatomy/B*aparc_aseg.nii*' % sub
        aparc = pp.find_single_file(searchstring)
        if aparc is None:
            logging.warning('%s not found'%(searchstring))
            continue
        aparc = pp.unzip_file(aparc)
        
        # find PET
        pet = movedmean # use previously made summed image
        # copy files to tmp dir
        logging.info('coreg ref region to %s'%pet)
        coreg_dir,exists = pp.make_dir(tracerdir, dirname='coreg_mri2fdg')
        if exists:
            logging.warning('existing dir %s remove to re-run'%(coreg_dir))
            continue
        cmri = pp.copy_file(mri, coreg_dir)
        cpons = pp.copy_file(pons, coreg_dir)
        cpet = pp.copy_file(pet, coreg_dir)
        caparc = pp.copy_file(aparc, coreg_dir)
        xfm_file = pp.make_transform_name(cpet, cmri)
        logging.info( 'coreg %s'%(subid))
        corg_out = pp.invert_coreg(cmri, cpet, xfm_file)
        if not corg_out.runtime.returncode == 0:
            logging.warning(corg_out.runtime.stderr)
            continue
        apply_out = pp.apply_transform_onefile(xfm_file,cpons)
        if not apply_out.runtime.returncode == 0:
            logging.warning(apply_out.runtime.stderr)
            continue
        apply_out = pp.apply_transform_onefile(xfm_file,caparc)
        if not apply_out.runtime.returncode == 0:
            logging.warning(apply_out.runtime.stderr)
            continue
        rout_mri = pp.reslice(cpet, cmri)
        if not rout_mri.runtime.returncode == 0:
            logging.warning(rout_mri.runtime.stderr)
        else:
            rmri = pp.prefix_filename(cmri, prefix='r')
            _, rmri_nme = os.path.split(rmri)
            new_rmri = rmri_nme.replace('rbr', 'rfdg_br')
            newmri = pp.copy_file(rmri, '%s/anatomy/%s'%(sub,new_rmri))
            if newmri:
                pp.remove_files([cmri,rmri])
        rout_pons = pp.reslice(cpet, cpons)
        if not rout_pons.runtime.returncode == 0:
            logging.warning(rout_pons.runtime.stderr)
        else:
            rpons = pp.prefix_filename(cpons, prefix='r')
            newpons = pp.copy_file(rpons, '%s/ref_region'%(tracerdir))
            if newpons:
                pp.remove_files([cpons,rpons])
        rout_aparc = pp.reslice(cpet, caparc)
        if not rout_aparc.runtime.returncode == 0:
            logging.warning(rout_aparc.runtime.stderr)
        pp.remove_files(cpet)
        pp.remove_files(caparc)
        bg.zip_files(aparc)
        bg.zip_files(nifti)

        # pons norm
        outfname = os.path.join(tracerdir,
                                'ponsnormed_%s_%s.nii'%(subid,
                                                        tracer.lower()))
        # generate pons normed image
        pp.make_pons_normed(pet, newpons, outfname)
        no_nanfiles = pp.clean_nan([outfname])
        logging.info('saved %s'%(outfname))


        
        logging.info( '%s finished realign QA coreg ponsnorm' % subid)

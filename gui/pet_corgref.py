#!/usr/bin/env python
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import preprocessing as pp
import base_gui as bg
import utils
import spm_tools
import logging, logging.config
from time import asctime


def apply_coreg(target, source, xfm):
    apply_out = spm_tools.apply_transform_onefile(xfm, source)
    if not apply_out.runtime.returncode == 0:
        logging.error(apply_out.runtime.stderr)
        return None
    rout_aparc = spm_tools.reslice(target, source)
    if not rout_aparc.runtime.returncode == 0:
        logging.error(rout_aparc.runtime.stderr)
        return None
    else:
        rsource = pp.fname_presuffix(source, prefix='r')
        utils.remove_files([source])
        utils.zip_files([rsource])
        rsource = rsource + '.gz'
        return rsource
    

if __name__ == '__main__':
    """
    for fdg, av45, 4frame pib
    find mean and sum
    finds reference_regions
    registers ref_regions to pet via mri
    creates reference normalized volumes
    """
    # start wx gui app
    app = wx.App()

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose Project dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    _, scriptnme = os.path.split(__file__)
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(scriptnme, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    tracer = bg.MyTracerDialog()
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
        # get tracer dir
        tracerdir, exists = utils.make_dir(sub, tracer.lower())
        if not exists:
            logging.error('%s does not exist, skipping'%tracerdir)
            continue
        # find mean and summed
        globstr = os.path.join(tracerdir, 'mean_r%s*nii*'%(subid))
        mean = utils.find_single_file(globstr)

        globstr = os.path.join(tracerdir, 'sum_r%s*nii*'%(subid))
        sum = utils.find_single_file(globstr)

        
        # coreg ref region(s) to pet
        # find ref regions
        globstr = os.path.join(tracerdir, 'ref_region', '*.nii*' )
        ref_regions = glob(globstr)
        if len (ref_regions) < 1:
            logging.error('no ref regions, skipping : %s'%globstr)
            continue
        ref_regions = [utils.unzip_file(x) for x in ref_regions]
        # find MRI
        globstr = os.path.join(sub, 'anatomy','brainmask.nii*')
        mri = utils.find_single_file(globstr)
        if mri is None:
            logging.error('no brainmask found for %s'%(subid))
            continue
        # find aparc_aseg
        searchstring = os.path.join(sub, 'anatomy', '%s*aparc_aseg.nii*'%(subid))
        aparc = utils.find_single_file(searchstring)
        if aparc is None:
            logging.error('%s not found'%(searchstring))
            continue
        
        for pet in [mean, sum]:
            _, petnme, _ = utils.split_filename(pet)
            logging.info('coreg ref region to %s'%pet)
            coreg_dir,exists = utils.make_dir(tracerdir, dirname='coreg_mri2%s'%petnme)
            if exists:
                logging.warning('existing dir %s remove to re-run'%(coreg_dir))
                continue
            # anatomy
            cpet, cmri, caparc = utils.copy_files([pet, mri, aparc], coreg_dir)
            cpet, cmri, caparc = utils.unzip_files([cpet, cmri, caparc])
            # ref regions
            cref_regions = utils.copy_files(ref_regions, coreg_dir)
            cref_regions = utils.unzip_files(cref_regions)
            xfm_file = spm_tools.make_transform_name(cpet, cmri)
            logging.info( 'coreg %s to %s'%(cpet, cmri))
            # invert corg mri
            corg_out = spm_tools.invert_coreg(cmri, cpet, xfm_file)
            if not corg_out.runtime.returncode == 0:
                logging.error(corg_out.runtime.stderr)
                continue
            rout_mri = spm_tools.reslice(cpet, cmri)
            if not rout_mri.runtime.returncode == 0:
                logging.error(rout_mri.runtime.stderr)
            else:
                rmri = pp.fname_presuffix(cmri, prefix='r')
                utils.remove_files([cmri])
                utils.zip_files([rmri])
            ## Apply transform to rest
            rcaparc = apply_coreg(cpet, caparc, xfm_file)
            rcref_regions = []
            for source in cref_regions:
                tmpr = apply_coreg(cpet, source, xfm_file)
                rcref_regions.append(tmpr)
            utils.zip_files([cpet])
        
            # ref region norm
            for ref in rcref_regions:
                _, refname, _ = utils.split_filename(ref)
                outfname = os.path.join(tracerdir,
                                        '%snormed_%s.nii.gz'%(refname,
                                                              petnme))
                # generate ref  normed image
                pp.make_pons_normed(pet, ref, outfname)
                logging.info('saved %s'%(outfname))

        logging.info( '%s finished coreg norm' % subid)

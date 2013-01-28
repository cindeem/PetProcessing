# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
import base_gui as bg
sys.path.insert(0, '/home/jagust/cindeem/src/nicm/nicm')
import nicm

import logging, logging.config
from time import asctime

if __name__ == '__main__':
    """sets up subject directory structure
    Select subs from ARDA,
    1. creates output dirs
    2. copies pet data to Raw
    3. converts
    """

    # start wx gui app
    app = wx.App()

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose project data dir',
                              indir = '/home/jagust')

    mridir = bg.SimpleDirDialog(prompt='Choose Freesurfer data dir',
                                indir = '/home/jagust')
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs',
                           'setup_pibdirectory_%s.log'%(cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START Setup Directory :::')
    logging.info('###TRACER Setup %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    
    
    outdict = {}
    for s in subs:
        _, subid = os.path.split(s)
        globstr = '%s/raw/*.tgz'%(s)
        
        rawpibs = glob(globstr)
        if len(rawpibs) < 1:
            outdict.update({subid:[None]})
        else:
            outdict.update({subid:rawpibs})
            
    for item in sorted(outdict):
        if outdict[item][0] is None:
            logging.info('skipping %s, no PIB found' %(item))
            continue
        else:
            tgz = outdict[item]
        subid = item
        logging.info(subid)
        ### XXXXXXXXXXXXXXXXX
        ##  set_up_dir
        outdirs = pp.setup_dir(root, subid, tracer)

        ## set up MRI
        brainmask = os.path.join(outdirs['anatomydir'][0],
                                 'brainmask.nii')
        fsmri = pp.find_single_file(os.path.join(mridir,
                                                 subid,
                                                 'mri/brainmask.mgz'))
        if os.path.isfile(brainmask):
            logging.warning('%s has existing anatomy,'\
                            'skipping'%(brainmask))
        elif fsmri is None:
            logging.error('%s NO MRI: %s'%(subid,fsmri)) 
            
        else:
            fsmri = utils.copy_file(fsmri, outdirs['anatomydir'][0])
            brainmask = pp.convert(fsmri, brainmask)
            utils.remove_files([fsmri])
            # copy aseg+aparc
        aparcnii = os.path.join(outdirs['anatomydir'][0],
                                '%s_aparc_aseg.nii.gz'%subid) 
        aparc = pp.find_single_file(os.path.join(mridir,
                                                 subid,
                                                 'mri/aparc+aseg.mgz'))
        if os.path.isfile(aparcnii):
            logging.warning('%s has existing anatomy,'\
                            'skipping'%(aparcnii))
        elif aparc is None:
            logging.error('%s NO APARC ASEG: %s'%(subid, aparc))

        else:
            aparc = utils.copy_file(aparc, outdirs['anatomydir'][0])
            aparcnii = pp.convert(aparc, aparcnii)     
            utils.remove_files([aparc])
        # make cerebellum
        refdir,_ = outdirs['refdir']
        cerebellum = os.path.join(refdir, 'grey_cerebellum.nii')
        if os.path.isfile(cerebellum):
            logging.warning('cerebellum %s exists, skipping'%(cerebellum))
            
        else:
            # copy aseg+aparc to refdir
            try:
                caparcnii = utils.copy_file(aparcnii, refdir)                        
                bg.make_cerebellum_nibabel(caparcnii)
                utils.remove_files([caparcnii])
            except:
                logging.warning('Fail: unable to make %s'%(cerebellum))
        
        rawtracer, exists = outdirs['rawtracer']
        os.system('rm %s'%rawtracer)
        tracerdir, _ = outdirs['tracerdir']
        
        newname = '%s_%s' % (subid, tracer)
        niftis = dicom_tools.biograph_dicom_convert(tgz[0], tracerdir, subid, tracer)
        ## center new nifti files
        orig_dir, _ = utils.make_dir(tracerdir, dirname='orig')
        copied_orig = utils.copy_files(niftis, orig_dir)
        utils.remove_files(niftis)
        for f,nf  in zip(copied_orig, niftis):
            print f, nf
            nicm.CMTransform(f).fix(new_file = nf)
        logging.info('biograph dicoms converted for %s ' % (subid))                
            

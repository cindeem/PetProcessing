# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import preprocessing as pp
import base_gui as bg
import utils
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
    _, scriptnme = os.path.split(__file__)
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(scriptnme, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    tracer = bg.MyTracerDialog()
    user = os.environ['USER']
    logging.info('###START Setup Directory :::')
    logging.info('###TRACER Setup %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    
    
    outdict = {}
    for s in subs:
        _, subid = os.path.split(s)
        globstr = '%s/raw/*.v'%(s)
        
        rawpet = glob(globstr)
        if len(rawpet) < 1:
            outdict.update({subid:[None]})
        else:
            outdict.update({subid:rawpet})
            
    for item in sorted(outdict):
        if outdict[item][0] is None:
            logging.info('skipping %s, no %s found' %(item, tracer))
            continue
        else:
            ecats = outdict[item]
        subid = item
        logging.info(subid)
        ### XXXXXXXXXXXXXXXXX
        ##  set_up_dir
        outdirs = pp.set_up_dir(root, subid, tracer)

        ## set up MRI
        brainmask = os.path.join(outdirs['anatomydir'][0],
                                 'brainmask.nii.gz')
        fsmri = utils.find_single_file(os.path.join(mridir,
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
        aparc = utils.find_single_file(os.path.join(mridir,
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
        # make pons
        refdir,_ = outdirs['refdir']
        brainstem = os.path.join(refdir, 'brainstem.nii.gz')
        if os.path.isfile(brainstem):
            logging.warning('brainstem %s exists, skipping'%(brainstem))
            
        else:
            # copy aseg+aparc to refdir
            try:
                caparcnii = utils.copy_file(aparcnii, refdir)                  
                pp.make_brainstem(caparcnii)
            except:
                logging.warning('Check  %s'%(brainstem))
        # make cerebellum
        cerebellum = os.path.join(refdir, 'grey_cerebellum.nii.gz')
        if os.path.isfile(cerebellum):
            logging.warning('%s exists, skipping'%(cerebellum))            
        else:            
            try:
                caparcnii = utils.copy_file(aparcnii, refdir)                  
                pp.make_cerebellum_nibabel(caparcnii)
                utils.remove_files([caparcnii])
            except:
                logging.warning('Check  %s'%(cerebellum))
        # convert PET
        tracerdir, _ = outdirs['tracerdir']
        
        newname = '%s_%s' % (subid, tracer)
        globstr = os.path.join(tracerdir, '%s*.nii*'%newname)
        converted = glob(globstr)
        if len(converted) > 1:
            logging.warning('%s already converted, remove to redo'%(converted))
            continue
        copied_ecats = utils.copy_files(ecats, tracerdir)
        all_converted = pp.convertallecat(copied_ecats, newname)
        if all_converted:
            converted = glob(globstr)
            utils.zip_files(converted)
            converted = glob(globstr)
            logging.info('ecats converted to  %s ' % (converted))                
        else:
            logging.error('failed to convert ecats for %s'%(ecats))
        
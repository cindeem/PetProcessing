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
        # check is ponsnormed exists
        searchstring = '%s/fdg/nonan-ponsnormed_*.nii*'%sub
        pn = pp.find_single_file(searchstring)
        if pn is not None:
            logging.info('%s exists, skipping'%(pn))
            continue
        # find sum
        searchstring = '%s/fdg/sum_rB*.nii*' % sub
        sum = pp.find_single_file(searchstring)
        if sum is None:
            logging.error('%s not found'%(searchstring))
            continue
        searchstr = '%s/fdg/ref_region/rpons_tu.nii*' % sub
        pons = pp.find_single_file(searchstr)
        if pons is None:
            logging.error('%s not found'%(searchstring))
            continue
        outfname = os.path.join(sub, 'fdg', 
                                'ponsnormed_%s_%s.nii'%(subid,
                                                        tracer.lower()))
        pp.make_pons_normed(pet, newpons, outfname)
        no_nanfiles = pp.clean_nan([outfname])
        logging.info('saved %s'%(outfname))


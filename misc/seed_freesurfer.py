# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
import base_gui as bg
import logging, logging.config
from time import asctime
import tempfile

if __name__ == '__main__':

    # start wx gui app
    app = wx.App()
    
    fsdir = bg.SimpleDirDialog(prompt='Choose Freesurfer DIR',
                               indir = '/home/jagust')
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(fsdir,'seedfs_logs',
                           '%s%s.log'%(__file__,cleantime))
    
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    user = os.environ['USER']
    logging.info('###START  %s :::'%__file__)
    logging.info('###USER : %s'%(user))

    tgz = bg.FilesDialog(prompt='Choose mri .tgz file',
                         indir='/home/jagust/arda/lblid')
    try:
        m = pp.re.search('B[0-9]{2}-[0-9]{3}', tgz[0])
        subid = m.group()
    except:
        logging.error('cant find ID in %s'%(tgz[0]))
        raise IOError('cant find ID in %s'%(tgz[0]))

    # create temp dir and untar/unzip dicom files into it
    startdir = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)
    tgz = tgz[0]
    cmd = 'tar xfvz %s '%(tgz)
    os.system(cmd)
    # find first dicom
    dcm0 = glob('%s/*0001.dcm'%(tmpdir))
    if not len(dcm0) > 0:
        os.chdir(startdir)
        logging.error('%s first dicom not found in %s'%(subid,tmpdir))
        raise IOError('first dicom not found in %s'%(tmpdir))
    dcm0 = dcm0[0]
    
    # seed freesurfer
    cmd = 'recon-all -i %s -sd %s -subjid %s'%(dcm0, fsdir, subid)
    os.system(cmd)
    logging.info(cmd)
    os.chdir(startdir)
    shutil.rmtree(tmpdir)
    logging.info('Finished %s'%(subid))
    

    
    
    
    

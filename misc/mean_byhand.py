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


if __name__ == '__main__':

    # start wx gui app
    app = wx.App()
    
    root = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs',
                           'pib_%s%s.log'%(__file__,cleantime))
    
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START pib %s :::'%__file__)
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))

    nifti = bg.FilesDialog(prompt='Choose realigned ',
                           indir='%s/'%root)
    try:
        m = pp.re.search('B[0-9]{2}-[0-9]{3}', nifti[0])
        subid = m.group()
    except:
        logging.error('cant find ID in %s'%(nifti[0]))
        raise IOError('cant find ID in %s'%(nifti[0]))
    
    realigned_dir , _ = os.path.split(nifti[0])
    pth, _ = os.path.split(realigned_dir)
    meanfile = pp.make_mean(nifti)
    logging.info('created %s'%(meanfile))
    
    

#!/usr/bin/env python
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import preprocessing as pp
import base_gui as bg
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/pyga')
import frametimes as ft
import logging, logging.config
from time import asctime

if __name__ == '__main__':

    # start wx gui app
    app = wx.App()

    root = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    _, scriptnme = os.path.split(__file__)
    logfile = os.path.join(root,'logs',
                           'pib_%s%s.log'%(scriptnme, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START pib %s :::'%__file__)
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    for sub in subs:
        print sub
        globstr = os.path.join(sub, 'raw', '*.v')
        ecats = glob(globstr)
        if len(ecats) < 1:
            globstr = os.path.join(sub, 'RawData', tracer, '*.v')
            ecats = glob(globstr)
        if len(ecats) < 1:       
            logging.error('%s missing, skipping'%(globstr))
            continue
        raw_ftimes = ft.frametimes_from_ecats(ecats)
        ftimes = ft.frametimes_to_seconds(raw_ftimes)
        timingf = ft.make_outfile(ecats[0])
        ft.write_frametimes(ftimes, timingf)
        logging.info('wrote %s'%(timingf))
        ft_minutes = ft.frametimes_to_seconds(raw_ftimes, type='min')
        sectimingf = ft.make_outfile(ecats[0], name = 'frametimes_in_minutes')
        ft.write_frametimes(ft_minutes, sectimingf)
        logging.info('wrote %s'%(sectimingf))

# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preprocessing')
import preprocessing as pp
import base_gui as bg
import utils
import qa
import spm_tools
import logging, logging.config
from time import asctime
import nicm.nicm as nicm


def realign(frames, realigndir):
    # center frames if necessary
    cframes = []
    for frame in frames:
        cm, dist, warn = nicm.CenterMass(frame).run()
        if dist > 40:
            cmtrans = nicm.CMTransform(frame)
            cframe = utils.fname_presuffix(frame, newpath = realigndir)
            cmtrans.fix(new_file = cframe)
            logging.info('Centering %s'%cframe)
        else:
            cframe = utils.copy_file(frame, realigndir)
        cframes.append(cframe)
    cframes = utils.unzip_files(cframes)
    
    rlgnout, newnifti = spm_tools.realigntoframe17(cframes, copied=True)
    if not rlgnout.runtime.returncode == 0:
        logging.error(rlgnout.runtime.stderr)
        return None, None
    tmpparameterfile = rlgnout.outputs.realignment_parameters
    rmean = rlgnout.outputs.mean_image
    ## sum first 5 frames
    sum1_5 = pp.make_summed_image(cframes[:5])
    crg_out = spm_tools.simple_coregister(rmean, sum1_5, cframes[:5])
    if crg_out.runtime.returncode is not 0:
        logging.error('Failed to coreg 1-5 to mean for  %s' % subid)
        return None, None
    rframes1_5 = crg_out.outputs.coregistered_files
    rframes = rframes1_5 + rlgnout.outputs.realigned_files
    rframes.sort()
    utils.remove_files(cframes)
    utils.remove_files([rmean, sum1_5, crg_out.outputs.coregistered_source])
    return rframes, tmpparameterfile

def run_qa(rframes, qadir, subid, tmpparameterfile):
    data4d = qa.make_4d_nibabel(rframes, outdir=qadir)
    qa.plot_movement(tmpparameterfile, subid)
    qa.calc_robust_median_diff(data4d)
    qa.screen_pet(data4d)
    utils.zip_files([data4d])
    
def make_means(rframes, tracerdir):
    mean20 = pp.make_mean_20min(rframes)
    cmean20 = utils.copy_file(mean20, tracerdir)
    suvr = pp.make_mean_40_60(rframes)
    utils.zip_files([suvr])
    utils.remove_files([mean20])
    return cmean20

if __name__ == '__main__':
    
    # start wx gui app
    app = wx.App()
    root = bg.SimpleDirDialog(prompt='Choose data dir',
                              indir = '/home/jagust')
    
    cleantime = asctime().replace(' ','-').replace(':', '-')
    _, scriptnme = os.path.split(__file__)
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(scriptnme, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'PIB'
    min_frames = 34 # dynamic scan has 34 or 35 frames
    user = os.environ['USER']
    logging.info('###START %s :::'%(__file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.DirsDialog(prompt='Choose Subjects ',
                         indir=root)
    
    for sub in subs:
        _, subid = os.path.split(sub)
        logging.info('%s'%subid)
        tracerdir = os.path.join(sub, tracer.lower())
        globstr = os.path.join(tracerdir, '%s*%s*.nii*'%(subid, tracer))
        frames = utils.find_files(globstr, n=min_frames)
        if frames is None:
            #logging error handled in find_files
            continue
        frames = utils.unzip_files(frames)
        ###  REALIGN allow for using existing data ###
        realigndir, exists = utils.make_dir(tracerdir, 'realign_QA')
        if exists:
            logging.error('%s exists, using, remove to rerun'%(realigndir))
            continue
        rframes, tmpparameterfile = realign(frames, realigndir)
        if rframes is None:
            continue
        # QA
        # make 4d for QA
        qadir, exists = qa.make_qa_dir(realigndir, name='data_QA')
        run_qa(rframes, qadir, subid, tmpparameterfile)

        # make mean20min
        csum = make_means(rframes, tracerdir)
        #clean up
        utils.zip_files([csum])
        utils.zip_files( rframes)
        utils.zip_files(frames)
        

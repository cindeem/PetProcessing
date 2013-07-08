# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import preprocessing as pp
import base_gui as bg
import utils
import qa
import spm_tools
import logging, logging.config
from time import asctime
import nicm.nicm as nicm


def realign(frames, realigndir):
    cframes = utils.copy_files(frames, realigndir)
    cframes = utils.unzip_files(cframes)
    rlgnout, newnifti = spm_tools.realigntoframe1(cframes, copied=True)
    if not rlgnout.runtime.returncode == 0:
        logging.error(rlgnout.runtime.stderr)
        return None, None
    tmpparameterfile = rlgnout.outputs.realignment_parameters
    rframes = rlgnout.outputs.realigned_files
    rmean = rlgnout.outputs.mean_image
    utils.remove_files(cframes)
    utils.remove_files([rmean])
    return rframes, tmpparameterfile

def run_qa(rframes, qadir, subid, tmpparameterfile):
    data4d = qa.make_4d_nibabel(rframes, outdir=qadir)
    qa.plot_movement(tmpparameterfile, subid)
    qa.calc_robust_median_diff(data4d)
    qa.screen_pet(data4d)
    utils.zip_files([data4d])
    
def make_centered_sum(rframes, tracerdir):
    sum = pp.make_summed_image(rframes)
    # check center of mass of SUM
    cm, dist, warn = nicm.CenterMass(sum).run()
    if dist > 40:
        cmtrans = nicm.CMTransform(sum)
        csum = utils.fname_presuffix(sum, newpath = tracerdir)
        cmtrans.fix(new_file = csum)
    else:
        csum = utils.copy_file(sum, tracerdir)
    utils.remove_files([sum])
    return csum

def make_centered_mean(rframes, tracerdir):
    mean = pp.make_mean(rframes)
    # check center of mass of SUM
    cm, dist, warn = nicm.CenterMass(mean).run()
    if dist > 40:
        cmtrans = nicm.CMTransform(mean)
        cmean = utils.fname_presuffix(mean, newpath = tracerdir)
        cmtrans.fix(new_file = cmean)
    else:
        cmean = utils.copy_file(mean, tracerdir)
    utils.remove_files([mean])
    return cmean
    

if __name__ == '__main__':

    try:
        min_frames = int(sys.argv[1])
        print min_frames
    except:
        min_frames = None
    
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

    
    tracer = bg.MyTracerDialog()
    tracerd = {'FDG':5, # min expected frames each tracer
               'PIB': 4,
               'AV45':4}
    if min_frames is None:
        min_frames = tracerd[tracer]
    logging.info('Minimum Frames is %d'%min_frames)
    user = os.environ['USER']
    logging.info('###START %s :::'%(__file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
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

        # make sum
        csum = make_centered_sum(rframes, tracerdir)
        cmean = make_centered_mean(rframes, tracerdir)
        #clean up
        utils.zip_files([csum, cmean])
        utils.zip_files(rframes)
        

        

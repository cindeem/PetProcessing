
""" quickly 
1. make whole cerelbellum from aparc
2. move to ref_region
3. use the coreg params used for grey_cerebellum to put in pet space
4. create whole_cerebellum dvr directory
5. attempt to run logan ga to get
 (log error if failed so users can easily re-do by hand)

"""

import os, sys
from glob import glob
import logging, logging.config
from time import asctime

sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/preproc')
import preprocessing as pp
import utils
import spm_tools as spm
from fs_tools import (desikan_pibindex_regions, roilabels_fromcsv)


sys.path.insert(0, '/home/jagust/cindeem/CODE/petproc-stable/pyga')
import py_logan as pyl
import frametimes as ft

def find_raw(subdir):
    """ looks for raw or RawData/PIB directory for subject"""
    raw = os.path.join(subdir, 'raw')
    if not os.path.isdir(raw):
        raw = os.path.join(subdir, 'RawData', 'PIB')
    if not os.path.isdir(raw):
        return None
    return raw

def is_biograph(rawdir):
    """ checks if subject has biograph or ecat files"""
    # check for biograph
    bio = glob(os.path.join(rawdir, 'B*.tgz'))
    if len(bio) > 0:
        return True, []
    ecat = sorted(glob(os.path.join(rawdir, 'B*.v*')))
    if len(ecat) < 1:
        return False, None
    # if zipped, unzip ecats
    ecats = [utils.unzip_file(x) for x in ecat]
    return False, ecats

    

def get_ecat_timing(ecats):
    """ given unzipped ecats extracts timing info and writes to file
    rezips ecats"""
    raw_ftimes = ft.frametimes_from_ecats(ecats)
    ftimes = ft.frametimes_to_seconds(raw_ftimes)
    timingf = ft.make_outfile(ecats[0])
    ft.write_frametimes(ftimes, timingf)
    logging.info('wrote %s'%(timingf))
    utils.zip_files(ecats)
    return timingf


def get_biograph_timing(rawdir):
    """ trys to grab Timing file for Biograph data"""
    globstr = os.path.join(rawdir, 'PIBtiming*.csv*')
    timing_file = utils.find_single_file(globstr)
    if timing_file is None:
        return None
    # unzip if necessary
    return utils.unzip_file(timing_file)


try:
    datadir = sys.argv[1]
except:
    datadir = '/home/jagust/bacs_pet/PIB/old/biograph'

cleantime = asctime().replace(' ','-').replace(':', '-')
_, scriptnme = os.path.split(__file__)
logfile = os.path.join(datadir,'logs',
    'pib_%s%s.log'%(scriptnme, cleantime))

        
log_settings = pp.get_logging_configdict(logfile)
logging.config.dictConfig(log_settings)
                
                    
tracer = 'pib'
user = os.environ['USER']
logging.info('###START %s :::'%__file__)
logging.info('###TRACER  %s  :::'%(tracer))
logging.info('###USER : %s'%(user))

allsub = glob(os.path.join(datadir, 'B*'))

for sub in allsub:
    _, sid = os.path.split(sub)
    ## check for whole cerebellum dvr dir, skip if exists
    dvrdir, exists = utils.make_dir(os.path.join(sub, tracer), 'dvr_rwhole_cerebellum')
    if exists:
        logging.warning('%s: dvr_rwhole_cerebellum exists, remove ro re-run'%sid)
        continue
    """
    # get aparc, make whole cerebellum
    globstr = os.path.join(sub,'anatomy', 'B*_aparc_aseg.nii*')
    aparc = utils.find_single_file(globstr)
    if aparc is None:
        logging.error('%s: has no %s'%(sid, globstr))
        continue
    # make whole cerebellum
    wcere = pp.make_whole_cerebellum(aparc)
    if wcere is None:
        logging.error('no wcere for %s'%sid)
    # move to ref_region directory
    refdir = os.path.join(sub,tracer, 'ref_region') 
    if not os.path.isdir(refdir):
        logging.error('%s: %s does not exist, skipping'%(sid, refdir))
        continue
    # put one copy in ref regions
    wcere = utils.copy_file(wcere, refdir)
    """
    # put copy we use in coreg directory
    globstr = os.path.join(sub, tracer, 'coreg*')
    allcoreg = sorted(glob((globstr)))
    if len(allcoreg) < 1:
        logging.error('%s: not found: %s'%(sid, globstr))
        continue
    # remove symbolic links
    allcoreg = [ x for x in allcoreg if not os.path.islink(x)]
    coregdir = allcoreg[0]
    # raparc
    globstr = os.path.join(coregdir, 'rB*aparc_aseg.nii*')
    aparc = utils.find_single_file(globstr)
    if aparc is None:
        logging.error('%s: no %s'%(sid, globstr))
        continue
    wcere = pp.make_whole_cerebellum(aparc, 'rwhole_cerebellum.nii.gz')
    """
    wcere = utils.copy_file(wcere, coregdir)
    # find transform in coreg directory
    globstr = os.path.join(coregdir, '*.mat*')
    xfm = glob(globstr)
    if len(xfm) < 1:
        logging.error('%s: not found: %s'%(sid, xfm))
        continue
    xfm = xfm[0]
    # find mean image
    globstr = os.path.join(coregdir, 'mean20min*.nii*')
    mean = utils.find_single_file(globstr)
    if mean is None:
        ## look in realign directory
        globstr = os.path.join(sub, tracer, 'realign_QA', 'mean20min*.nii*')
        mean = utils.find_single_file(globstr)
        if mean is None:
            logging.error('%s: no mean %s'%(sid, globstr))
            continue
    # unzip files if necessary
    # cere
    wcere = utils.unzip_file(wcere)
    xfm = utils.unzip_file(xfm)
    mean = utils.unzip_file(mean)
    
    # apply transform
    ret = spm.apply_transform_onefile(xfm[0], wcere)
    if not ret.runtime.returncode == 0:
        logging.error('%s: apply xfm failed'%(sid))
        continue
    # reslice to pet space
    ret = spm.reslice(mean, wcere)
    if not ret.runtime.returncode == 0:
        logging.error('%s: reslice failed'%(sid))
        logging.error('%s: %s'%(sid, ret.runtime.stderr))
        continue
    # get reslice wcere
    rwcere = wcere.replace('whole', 'rwhole')
    """
    # get realigned
    realign_dir = os.path.join(sub, tracer, 'realign_QA')
    if not os.path.isdir(realign_dir):
        logging.error('%s: no realign dir'%sid)
        continue
    
    ## find realigned, require at least 34 frames
    globstr = os.path.join(realign_dir, 'rB*.nii*')
    frames = utils.find_files(globstr, n=34)
    if frames is None:
        logging.error('%s: realigned not sufficient'%sid)
        continue
    # find raw directory
    rawdir = find_raw(sub)
    if rawdir is None:
        logging.error('%s: no raw dir'%sid)
        continue
    isbio, files = is_biograph(rawdir)
    if not isbio and files is None:
        logging.error('%s: not biograph, no ecats'%sid)
        continue
    # if biograph, grab timing file
    if isbio:
        timing_file = get_biograph_timing(rawdir)
        if timing_file is None:
            logging.error('%s: no biograph timing file'%sid)
            continue
    else:
        timing_file = get_ecat_timing(files)
        # if ecat, generate timing file from ecats
    ## get files needed
    # rbrainmask
    globstr = os.path.join(coregdir, 'rbrainmask.nii*')
    brainmask = utils.find_single_file(globstr)
    if brainmask is None:
        logging.error('%s: no brainmask %s'%(sid, globstr))
        continue
    # set defaults
    roifile = 'fsrois_pibindex.csv'
    ki = 0.15
    start = 35
    stop = 90
    logging.info('%s: Running Logan'%sid)
    midtimes, durs = pyl.midframes_from_file(timing_file)
    data4d = pyl.get_data_nibabel(frames)
    ref = pyl.get_ref(wcere, data4d)
    ref_fig = pyl.save_inputplot(ref, (midtimes + durs/2.), dvrdir)
    masked_data, mask_roi = pyl.mask_data(brainmask, data4d)
    x,y  = pyl.calc_xy(ref, masked_data, midtimes)
    allki, allvd, residuals = pyl.calc_ki(x, y, timing_file, trange=(start,stop))
    dvr = pyl.results_to_array(allki, mask_roi)
    resid = pyl.results_to_array(residuals, mask_roi)
    outf = pyl.save_data2nii(dvr, brainmask,
            filename='DVR-%s'%sid, outdir=dvrdir)
    _ = pyl.save_data2nii(resid, brainmask,
            filename = 'RESID-%s'%sid,outdir = dvrdir)

    ## calc logan plot
    labels = desikan_pibindex_regions()
    region = pyl.get_labelroi_data(data4d, aparc, labels)
    pyl.loganplot( ref, region, timing_file, dvrdir)
    logging.info('%s Finished Logan: %s'%(sid, outf))
    roid = roilabels_fromcsv(roifile)

    ## Calc pibindex
    logging.info('PIBINDEX ROI file: %s'%(roifile))
    meand = pp.mean_from_labels(roid, aparc, dvr)
    csvfile = os.path.join(dvrdir, 'PIBINDEX_%s_%s.csv'%(sid,cleantime))
    pp.meand_to_file(meand, csvfile)

















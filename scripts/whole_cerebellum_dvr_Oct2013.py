
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
    """ finds ecats, unzips, extracts timing info and writes to file?"""
    pass

def get_biograph_timing(rawdir):
    """ trys to grab Timing file for Biograph data"""
    globstr = os.path.join(rawdir, 'PIBtiming_*.csv*')
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
    # get aparc, make whole cerebellum
    globstr = os.path.join(sub,'anatomy', 'B*_aparc_aseg.nii*')
    aparc = utils.find_single_file(globstr)
    if aparc is None:
        logging.error('%s: has no %s'%(sid, globstr))
        continue
    # make whole cerebellum
    wcere = pp.make_whole_cerebellume(aparc)
    if wcere is None:
        logging.error('no wcere for %s'%sid)
    # move to ref_region directory
    refdir = os.path.join(sub,tracer, 'ref_region') 
    if not os.path.isdir(refdir):
        logging.error('%s: %s does not exist, skipping'%(sid, refdir))
        continue
    # put one copy in ref regions
    wcere = utils.copy_file(wcere, refdir)
    # put copy we use in coreg directory
    globstr = os.path.join(sub, tracer, 'coreg*')
    allcoreg = sorted(glob((globstr)))
    if len(allcoreg) < 1:
        logging.error('%s: not found: %s'%(sid, globstr))
        continue
    # remove symbolic links
    allcoreg = [ x for x in allcoreg if not os.path.islink(x)]
    coregdir = allcoreg[0]
    wcere = utils.copy_file(wcere, coregdir)
    # find transform in coreg directory
    globstr = os.path.join(coregdir, '*.mat*')
    xfm = glob(globstr)
    if len(xfm) < 1:
        logging.error('%s: not found: %s'%(sid, xfm))
        continue
    # find mean image
    globstr = os.path.join(coregdir, 'mean20min*.nii*')
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
        
    # if ecat, generate timing file form ecats
    
    dvrdir =  
















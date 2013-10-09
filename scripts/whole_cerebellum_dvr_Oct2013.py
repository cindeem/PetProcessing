
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
    
    dvrdir =  
















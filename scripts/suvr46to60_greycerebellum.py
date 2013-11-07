
""" quickly 
1. find mean40_60 in the realign_QA directory
2. find rgrey_cere in the coreg directory
3. calc 40_60 SUVR with grey ref region
4. save named file to SUVR directory

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

try:
    datadir = sys.argv[1]
except:
    datadir = '/home/jagust/bacs_pet/PIB/old/ecat'

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

allsub = sorted(glob(os.path.join(datadir, 'B*')))

for sub in allsub:
    ## skip second visit subjects
    if '_v2' in sub:
        continue
    _, sid = os.path.split(sub)
    ## check for whole cerebellum dvr dir, skip if exists
    try:
        suvrdir, exists = utils.make_dir(os.path.join(sub, tracer), 'SUVR')
    except:
        logging.error('%s: pib not worked up'%sid)
        continue
    ## find mean40_60 in realign_QA dir
    globstr = os.path.join(sub, tracer, 'realign_QA', 'mean40_60min*.nii*')
    mean4060 = utils.find_single_file(globstr)
    if mean4060 is None:
        logging.error('%s: not found: %s'%(sid, globstr))
        continue
    # find rgrey_cere
    globstr = os.path.join(sub, tracer,'coreg*', 'rgrey_cerebellum.nii*')
    gcere = utils.find_single_file(globstr)
    if gcere is None:
        logging.error('%s: not found: %s'%(sid, globstr))
        continue
    
    outfile = os.path.join(suvrdir, '%s_mean40_60min_rgreycerebellum.nii.gz'%sid)
    pp.make_pons_normed(mean4060, gcere, outfile)
    logging.info('%s: made SUVR %s'%(sid, outfile))






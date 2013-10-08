
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
        logging.error('%s has no %s'%(sid, globstr))
        continue
    # make whole cerebellum
    wcere = pp.make_whole_cerebellume(aparc)
    if wcere is None:
        logging.error('no wcere for %s'%sid)
    # move to ref_region directory
    refdir = os.path.join(sub,tracer, 'ref_region') 







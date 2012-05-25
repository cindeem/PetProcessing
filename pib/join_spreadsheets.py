import os, re
from glob import glob
import csv
from datetime import datetime



def parse_subid(infile):
    m = re.search('B[0-9]{2}-[0-9]{3}', infile)
    try:
        return m.group()
    except:
        print 'missing subid in %s'%infile
        return 'NA'

    
def get_data(dict, infile):
    subid = parse_subid(infile)
    if subid == 'NA':
        return
    roid = {}
    for row in csv.reader(open(infile)):
        if 'SUBID' in row:
            continue
        roid[row[0]] = row[1:]
    dict[subid]  = roid

data_dir ='/home/jagust/UCD_Project/pet'
globstr = os.path.join(data_dir, 'B*/pib/dvr/PIB*')
allpi = glob(globstr)
allpi.sort()

allsd = {}
for f in allpi:
    get_data(allsd, f)

newname = 'ALL_PIBINDEX' + datetime.now().strftime('-%Y-%m-%d_%H-%M') + '.csv'
outfile = os.path.join(data_dir, newname)
fid = open(outfile, 'w+')
csv_writer = csv.writer(fid)

subjects = sorted(allsd.keys())
headers = ['SUBID']
for item in sorted(allsd[subjects[0]]):
    if 'SUBID' in item:
        continue
    else:
        headers += ['%s_mean'%item, '%s_std'%item]
csv_writer.writerow(headers)
# write headers

for subid in subjects:
    row = [subid]
    data = allsd[subid]
    for mean, std in sorted(data.values()):
        row+= [mean, std]
    csv_writer.writerow(row)
fid.close()
    
"""
csv_writer = csv.writer(open(outfile, 'w+'))
csv_writer.writerow(['frame', 'start', 'duration','stop'])
csv_writer.writerow(row)
jnk = csv.reader(open(infile),delimiter=',' )
"""

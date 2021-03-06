import os, re,sys
from glob import glob
import csv
from datetime import datetime
import wx
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import base_gui as bg


def parse_subid(infile, visit=False):
    if visit:
        m = re.search('B[0-9]{2}-[0-9]{3}_v[0-9]', infile)
    else:
        m = re.search('B[0-9]{2}-[0-9]{3}', infile)
    try:
        return m.group()
    except:
        print 'missing subid in %s'%infile
        return 'NA'

    
def get_data(dict, infile, visit=False):
    subid = parse_subid(infile, visit=visit)
    if subid == 'NA':
        return
    roid = {}
    for row in csv.reader(open(infile)):
        if 'SUBID' in row:
            continue
        roid[row[0]] = row[1:]
    if dict.has_key(subid):
        print 'duplicate for %s'%subid
    else:
        dict[subid]  = roid

if __name__ == '__main__':
    # specify if subjects will have more than one visit
    
    app = wx.App()
    data_dir = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                                  indir='/home/jagust')
    
    if 'UCD_Project' in data_dir:
        visit = False
    else:
        visit = True
    _, datadir_nme = os.path.split(data_dir)
    #data_dir ='/home/jagust/UCD_Project/pet'
    #data_dir = '/home/jagust/bacs_pet/PIB'
    globstr = os.path.join(data_dir, 'B*/pib/dvr/PIB*')
    allpi = glob(globstr)
    allpi.sort()

    allsd = {}
    for f in allpi:
        get_data(allsd, f, visit=visit)

    newname = 'ALL_PIBINDEX-' + datadir_nme + datetime.now().strftime('-%Y-%m-%d_%H-%M') + '.csv'
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

    keys = sorted(allsd[subjects[0]])
    for subid in subjects:
        row = [subid]
        data = allsd[subid]
        for k in keys:
            try:
                mean, std = data[k]
            except:
                mean= 'NA'
                std = 'NA'
            row+= [mean, std]
        csv_writer.writerow(row)
    fid.close()
    print 'Created %s'%(outfile)

    """
    csv_writer = csv.writer(open(outfile, 'w+'))
    csv_writer.writerow(['frame', 'start', 'duration','stop'])
    csv_writer.writerow(row)
    jnk = csv.reader(open(infile),delimiter=',' )
    """

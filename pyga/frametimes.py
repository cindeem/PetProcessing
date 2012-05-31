# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import sys, os
import nibabel.ecat as ecat
sys.path.insert(0, '/home/jagust/cindeem/src/pydicom-0.9.7')
import dicom
import numpy as np
from datetime import datetime
import csv
from glob import glob

def get_series_iter(infile):
    """ based on structure of current dicoms
    returns iterator for files to junm between
    frames"""
    plan = dicom.read_file(infile)
    ns = plan.NumberOfSlices
    nts = plan.NumberOfTimeSlices
    ii = plan.ImageIndex
    return np.arange(0,nts*ns, ns)


def sort_series(infiles):
    nfiles = len(infiles)
    out = np.recarray((nfiles), dtype=[('x', int), ('file', 'S250')])
    for val, f in enumerate(infiles):
        plan = dicom.read_file(f)
        ii = plan.ImageIndex
        out.x[val] = ii
        out.file[val] = f
    sort_mask = out.argsort(axis=0)    
    out = out[sort_mask]# sort to correct order
    return out


def frametime_from_dicoms(infiles):
    """ given a dicom series,
    find timing info for each frame
    """
    frametimes = []
    files = []
    sorted = sort_series(infiles)
    fiter = get_series_iter(infiles[0])
    for f in sorted.file[fiter]:
        plan = dicom.read_file(f)
        st = datetime.fromtimestamp(float(plan.StudyTime))
        at = datetime.fromtimestamp(float(plan.AcquisitionTime))
        dur = float(plan.ActualFrameDuration)
        start = (at -st).microseconds * 1000
        frt = datetime.fromtimestamp(float(plan.FrameReferenceTime))
        end = start + dur
        frametimes.append([frt.microsecond * 1000, at.microsecond * 1000, dur, st.microsecond * 1000])
        files.append(f)
    return frametimes, files
        

        
def frametime_from_ecat(ecatf):
    """given an ecat file , finds timing info for each frame
    
    Returns
    -------
    out : array
          array holding framenumber, starttime, duration, endtime
          in milliseconds
    """
    img = ecat.load(ecatf)
    shdrs = img.get_subheaders()
    mlist = img.get_mlist()
    framenumbers = mlist.get_series_framenumbers()
    out = np.zeros((len(framenumbers), 4))
    if shdrs.subheaders[0]['frame_start_time']== 16:
        adj = 16
    else:
        adj = 0
    for i, fn in framenumbers.items():
        startt = shdrs.subheaders[i]['frame_start_time']
        dur = shdrs.subheaders[i]['frame_duration']
        out[i,0] = fn 
        out[i,1] = startt - adj
        # fix adj, divide by 60000 to get minutes
        out[i,2] = dur
        out[i,3] = startt - adj + dur
    out = out[out[:,0].argsort(),]
    return out


def frametimes_from_ecats(filelist):
    """
    for each ecat file in filelist
    gets the frame number, start, duration info
    combines
    sorts and retruns

    Returns
    -------
    out : array
          array holding framenumber, starttime, duration, endtime
          in milliseconds
          
    """
    if not hasattr(filelist, '__iter__'):
        filelist = [filelist]
    for f in filelist:
        tmp = frametime_from_ecat(f)
        try:
            out = np.vstack((out, tmp))
        except:
            out = tmp
    out = out[out[:,0].argsort(),]
    return out


def frametimes_to_seconds(frametimes, type = 'sec'):
    """ assumes a frametimes array
    type = 'sec', or 'min'
    [frame, start, duration, stop]
    converts to type (default sec (seconds))
    """
    
    newframetimes = frametimes.copy()
    newframetimes[:,1:] = frametimes[:,1:] / 1000.
    if type == 'min':
        newframetimes[:,1:] = newframetimes[:,1:]  / 60.
    return newframetimes




def make_outfile(infile, name = 'frametimes'):
    pth, _ = os.path.split(infile)
    newname = name + datetime.now().strftime('-%Y-%m-%d_%H-%M') + '.csv'
    newfile = os.path.join(pth, newname)
    return newfile

def write_frametimes(inarray, outfile):
    csv_writer = csv.writer(open(outfile, 'w+'))
    csv_writer.writerow(['frame', 'start', 'duration','stop'])
    for row in inarray:
        csv_writer.writerow(row)

def read_frametimes(infile):
    outarray = []
    jnk = csv.reader(open(infile),delimiter=',' )
    for row in jnk:
        if not 'frame' in row[0]:
            outarray.append(row)
    return np.asarray(outarray, dtype=float)





if __name__ == '__main__':
    #run tests
    infile = '../test/B09_237-42A890F600004FB4-de.v'
    ft = frametime_from_ecat(infile)
    np.testing.assert_equal(ft[0,0], 23.)
    np.testing.assert_equal(ft[0,1] , 1020016.0)
    np.testing.assert_equal(ft[0,2] , 180000.0)
    np.testing.assert_equal(ft[0,3] , 1200016.0)

    # test multiple and sorting
    allv  = glob('../test/*.v')
    ft_all = frametimes_from_ecats(allv)
    np.testing.assert_equal(ft_all[0,0],17.0)
    # test naming
    outf = make_outfile(infile)
    np.testing.assert_equal('../test/frametimes' in outf, True)
    

    # test writing
    ft_sec = ft_all[0,:].copy()
    ft_sec.shape = (1,4)
    ft_sec[:,1:] = ft_sec[:,1:] / 1000.
    
    write_frametimes(ft, outf)
    outf_sec = make_outfile(infile, name = 'frametimes_sec')
    write_frametimes(ft_sec, outf_sec)

    # roundtrip
    ft = read_frametimes(outf)
    np.testing.assert_equal(ft[0,0], 23.)
    np.testing.assert_equal(ft[0,1] , 1020016.0)
    np.testing.assert_equal(ft[0,2] , 180000.0)
    np.testing.assert_equal(ft[0,3] , 1200016.0)
    eft = read_frametimes(outf)
    # roundtrip seconds
    ft = read_frametimes(outf_sec)
    np.testing.assert_almost_equal(ft[0,1], 540.016)
    os.unlink(outf_sec)
    os.unlink(outf)

    ## dicom
    inglob = '../../biograph_dicom/B12-219PIBFR1TO18/*'
    alldicoms = glob(inglob)
    ft, files = frametime_from_dicoms(alldicoms)

    inglob = '../../biograph_dicom/B12-209FDG/*'
    alldicoms = glob(inglob)
    ft2, files2 = frametime_from_dicoms(alldicoms)

    

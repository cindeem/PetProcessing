import os, sys
from glob import glob
import dicom
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import base_gui as bg
import argparse

#  pth = bg.tar_cmd(intgz)
#  dcms = bg.find_dicoms(pth)


# for each dicom in unzipped untarr'd archive

# replace PatientID with new ID

# write new file

# retar and zip to new directory

def main(tgz, newid, outdir=None):
    """ untars tgz, replaces PatientID PatientName
    with new id, and save to outdir (default origdir/newtgz"""
    # mv dicom to tmp directory
    tgz = os.path.abspath(tgz)
    origdir, orignme = os.path.split(tgz)
    tmptgz = bg.copy_tmpdir(tgz)
    # un-archive
    pth = bg.tar_cmd(tmptgz)
    newdir, exists = pp.make_dir(pth, dirname='dicomfiles')
    startdir = os.getcwd()
    os.chdir(pth)
    dcms = bg.find_dicoms(pth)
    keys = dcms.keys()
    keys = [x for x in keys if not newdir in x]
    for k in keys:
        for dcm in dcms[k]:
            plan = dicom.read_file(dcm)
            plan.PatientID = newid
            plan.PatientName = newid
            _, dcm_name = os.path.split(dcm)
            newdcm = os.path.join(newdir, dcm_name)
            dicom.write_file(newdcm, plan)
    # create tar archive of updated dicoms
    if outdir is None:
        outdir, _ = pp.make_dir(origdir, dirname="newtgz")
    newtgz = os.path.join(outdir, orignme)
    cmd = 'tar cfvz %s  dicomfiles'%(newtgz)
    os.system(cmd)
    os.chdir(startdir)
    print 'removing %s'%pth
    os.system('rm -rf %s'%(pth))
    print 'wrote ', newtgz
    return newtgz
    


    
if __name__ == '__main__':

    # create the parser
    parser = argparse.ArgumentParser(
        description="""untar <file>tgz dicom archive and replace
        PatientName, PatientID with new ID""")

    # add the arguments
    parser.add_argument(
        'infile', type=str, nargs=1,
        help='Filename fullpath to <file>tgz archive')

    parser.add_argument(
        'newid', type=str,
        default='', 
        help='newid to put in dicom')
    

    parser.add_argument(
        '-outdir', dest='outdir', default=None,
        help='Directory to save new tararchive file')
    
        
    if len(sys.argv) ==1:
        parser.print_help()
    else:
        args = parser.parse_args()
        print args.infile
        print args.outdir
        print args.newid
        main(args.infile[0], args.newid, args.outdir)

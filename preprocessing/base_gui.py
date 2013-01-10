# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import wx
import sys, os
import tempfile
sys.path.insert(0, '/home/jagust/cindeem/CODE/ruffus')
import MultiDirDialog as mdd
from glob import glob
import nibabel as ni
import nipype
from nipype.interfaces.base import CommandLine
from nipype.interfaces.fsl import Split as fsl_split
import nipype.interfaces.dcm2nii as dcm2nii
import numpy as np
import logging

def MyDirsDialog(prompt='Choose Subject Dirs',indir='',title='Choose Subject Dirs'):
      """
      Advanced  directory dialog and returns selected directories
      """
      dlg = mdd.MultiDirDialog(None,
                               message=prompt,
                               title=title,
                               defaultPath=indir)
      if dlg.ShowModal() == wx.ID_OK:
          tmpdir = dlg.GetPaths()
      else:
          tmpdir = []
      dlg.Destroy()
      return tmpdir


def FileDialog(prompt='ChooseFile', indir=''):
    """
    opens a wx dialog that allows you to select a single
    file, and returns the full path/name of that file """
    dlg = wx.FileDialog(None,
                        message = prompt,
                        defaultDir = indir)
                        
    if dlg.ShowModal() == wx.ID_OK:
          outfile = dlg.GetPath()
    else:
          outfile = None
    dlg.Destroy()
    return outfile

def FilesDialog(prompt = 'Choose Files', indir = ''):
      """
      opens a wx Dialog that allows you to select multiple files within
      a single directory and returns full path/names of those files"""
      fdlg = wx.FileDialog(None,
                           message=prompt,
                           defaultDir = indir,
                           style = wx.FD_MULTIPLE)
      if fdlg.ShowModal() == wx.ID_OK:
            outfiles = fdlg.GetPaths()
      else:
            outfiles = None
      fdlg.Destroy()
      return outfiles

def SimpleDirDialog(prompt='Choose Directory', indir=''):
    """
    opens a directory dialog and returns selected directory
    """
    sdlg = wx.DirDialog(None,
                        message = prompt,
                        defaultPath = indir)
    if sdlg.ShowModal() == wx.ID_OK:
          tmpdir = sdlg.GetPath()
    else:
          tmpdir = []
    sdlg.Destroy()
    return tmpdir
    
def MyVisitDialog():
    choices = ['v1', 'v2', 'v3', 'v4', 'v5']
    dialog = wx.SingleChoiceDialog(None,
                                   'Choose a Timepoint',
                                   'VISIT TIMEPOINT',
                                   choices)
    if dialog.ShowModal() == wx.ID_OK:
        visit = dialog.GetStringSelection()
    dialog.Destroy()
    return visit
    
def MyTracerDialog():
    choices = ['FDG', 'PIB']
    dialog = wx.SingleChoiceDialog(None,
                                   'Choose a Tracer',
                                   'TRACERS',
                                   choices)
    if dialog.ShowModal() == wx.ID_OK:
        tracer = dialog.GetStringSelection()
    dialog.Destroy()
    return tracer

def MyScanChoices(choices,message = 'Choose directories'):
    sdialog = wx.MultiChoiceDialog(None,
                                  message = message,
                                  caption='Choices',
                                  choices=choices)
    if sdialog.ShowModal() == wx.ID_OK:
        dirs = sdialog.GetSelections()
    sdialog.Destroy()
    return [choices[x] for x in dirs]


def MyRadioSelect(outdict):
      mrc = MyRadioChoices(outdict)
      mrc_retval = mrc.ShowModal()
      if mrc_retval == wx.ID_OK:
            outdict = mrc.GetValue()
      mrc.Destroy()
      return outdict

def MriDialog(subid):
      qdlg = wx.MessageDialog(None,
                              message = 'No Freesurfer MRI for ' + \
                              '%s, skip subject?'%(subid),
                              caption = 'MRI Message',
                              style=wx.YES_NO)
     
      if qdlg.ShowModal() == wx.ID_YES:
            resp = True

      else:
            resp = False
      
      qdlg.Destroy()
      return resp

class MyRadioChoices(wx.Dialog):
      
      def __init__(self, outdict):
            #global outdict
            self.outdict = outdict
            nchoices = len(outdict)
            wx.Dialog.__init__(self, None, -1, 'Radio select', size=(800,800),
                               )
            panel = wx.Panel(self,-1)
            self.button = wx.Button(panel, wx.ID_OK, 'Finished',
                                    pos = (10,10))
            self.Bind(wx.EVT_CLOSE, self.DialogClose)
            #self.scroll = wx.ScrolledWindow(panel, -1)
            #self.scroll.SetScrollbars( 100, 100, 600, nchoices*100) 
            dirlist = ['Controls', 'AD', 'LPA', 'PCA', 'FTLD', 'CBS',
                       'Others', 'NIFD-LBL', 'NIFD-ADNI', 'MCI']
            self.rb = {}
            for val, item in enumerate(sorted(outdict.keys())):
                  self.rb.update({item:wx.RadioBox(panel, -1, item, (10, 50+val*40),
                                                   (550,40), dirlist,
                                                   1, wx.RA_SPECIFY_ROWS)})

      def DialogClose(self, event):
            self.EndModal(wx.ID_OK)
      def GetValue(self):
            for key in self.rb:
                  self.outdict[key][1] = self.rb[key].GetStringSelection()
            #print self.outdict
            return self.outdict
                  
            
            
#### END WX ###










def convert_dicom(dcm0, fname):
    """given first dicom and fname uses mri_convert to convert
    to a 4d nii.gz file"""
    

    cmd = '/usr/local/freesurfer_x86_64-5.1.0/bin/mri_convert '
    cmd = cmd + ' --out_orientation LAS %s %s'%(dcm0, fname)
    cl = CommandLine(cmd)
    cout = cl.run()
    if not cout.runtime.returncode == 0:
        logging.error('DICOM Failed to convert %s'%(dcm0))
        return None
    else:
        return fname

def biograph_to_nifti(dicomf):
    """ given a dicom file <dicomf> in a directory of dicoms
    , use dcm2nii to convert
    to a 4d.nii.gz file in a tempdir"""
    tmp, _ = os.path.split(os.path.abspath(__file__))
    default_file = os.path.join(tmp,
                                'dcm2nii.ini')
    tmpdir = tempfile.mkdtemp()
    convert = dcm2nii.Dcm2nii()
    convert.inputs.source_names = dicomf
    convert.inputs.output_dir = tmpdir
    convert.inputs.config_file = default_file
    cout = convert.run()
    if not cout.runtime.returncode == 0:
        logging.error(cout.runtime.stderr)
        return None
    else:
        ext = ''
        if 'GZip' in cout.runtime.stdout:
            ext = '.gz'
        outf = cout.runtime.stdout.split('->')[-1].split('\n')[0]
        return os.path.join(tmpdir,outf + ext)
    

def fsl_split4d(in4d, basenme = None):
    cwd = os.getcwd()
    pth, nme, ext = nipype.utils.filemanip.split_filename(in4d)
    if basenme is None:
        basenme = nme
    os.chdir(pth)
    split = fsl_split()
    split.inputs.in_file = in4d
    split.inputs.dimension = 't'
    split.inputs.out_base_name = basenme
    split_out = split.run()
    os.chdir(cwd)
    if not split_out.runtime.returncode == 0:
        logging.error('Failed to split 4d file %s'%in4d)
        return None
    else:
        return split_out.outputs.out_files
    
    return pth   


def copy_tmpdir(infile):
    """copies file to tempdir, returns path
    to file copied into tmpdir"""
    tmpdir = tempfile.mkdtemp()
    newfile = copy_file(infile, tmpdir)
    return newfile

def concat_images(img_list):
    alldat = np.concatenate([ni.load(x).get_data() for x in img_list],
                            axis=3)
    pth, _ = os.path.split(img_list[0])
    newf = os.path.join(pth, 'full4d.nii.gz')
    allimg = ni.Nifti1Image(alldat, ni.load(img_list[0]).get_affine())
    allimg.to_filename(newf)
    for item in img_list[1:]:
        # clean tmp directories
        pth, _ = os.path.split(item)
        os.system('rm -rf %s'%pth)
    return newf

def biograph_dicom_convert(input, dest, subid, tracer):
    """ given a tgz file holding dicoms,
    expands in temdir, uses mri_convert to convert
    file to nifti (4D) in tmpdir
    copies single frames to dest"""
    newfile = copy_tmpdir(input)
    pth = tar_cmd(newfile)
    results = find_dicoms(pth)
    all4d = []
    for val, (name, files) in enumerate(sorted(results.items())):
        dcm0 = files[0]
        #if not tracer.upper() in name.upper():
        #    fname = os.path.join(pth,
        #                         '%s_%s%d'%(subid, tracer,val) + '.nii.gz')
        #else:
        #    fname = os.path.join(pth, name + '.nii.gz')
        #tmp4d = convert_dicom(dcm0, fname)
        tmp4d = biograph_to_nifti(dcm0)
        all4d.append(tmp4d)

    if len(all4d) > 1:
        final4d = concat_images(all4d)
    else:
        final4d = all4d[0]
    basename = '%s_%s_frame'%(subid, tracer.upper())    
    tmpsplit = fsl_split4d(final4d, basenme = basename)    
    newfiles = copy_files(tmpsplit, dest)
    pth, _ = os.path.split(final4d)
    os.system('rm -rf %s'%(pth)) 
    return newfiles
    
    

def move_and_convert(mgz, dest, newname):
      """takes a mgz file, moves it,
      converts it to nifti and then removes
      the original mgz file"""
      cwd = os.getcwd()
      new_mgz = copy_file(mgz, dest)
      os.chdir(dest)
      nii = convert(new_mgz, newname)
      os.chdir(cwd)
      os.remove(new_mgz)
      return nii

def make_brainstem(aseg):

      cwd = os.getcwd()
      pth, nme = os.path.split(aseg)
      os.chdir(pth)
      cl = CommandLine('fslmaths %s -thr 16 -uthr 16 brainstem'% (aseg))
      cout = cl.run()
      os.chdir(cwd)
      if not cout.runtime.returncode == 0:
            print 'Unable to create brainstem for %s'%(aseg)
            return None
      else:
            os.remove(aseg)
            return 'brainstem'

      
def make_whole_cerebellume(aseg):
      """
      os.system('fslmaths rad_aseg -thr 46 -uthr 47 whole_right_cerebellum')
      os.system('fslmaths rad_aseg -thr 7 -uthr 8 whole_left_cerebellum')
      os.system('fslmaths whole_left_cerebellum -add whole_right_cerebellum -bin whole_cerebellum')
      """
      cwd = os.getcwd()
      pth, nme = os.path.split(aseg)
      os.chdir(pth)
      cmd = 'fslmaths %s -thr 46 -uthr 47 whole_right_cerebellum'%(aseg)
      cl = CommandLine(cmd)
      cout = cl.run()
      if not cout.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  right whole cerebellum for %s'%(aseg)
            return None
      
      cmd = 'fslmaths %s -thr 7 -uthr 8 whole_left_cerebellum'%(aseg)
      cl2 = CommandLine(cmd)
      cout2 = cl2.run()
      if not cout2.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  whole left cerebellum for %s'%(aseg)
            return None     

      cmd = 'fslmaths whole_left_cerebellum -add whole_right_cerebellum' + \
            ' -bin whole_cerebellum'
      cl3 = CommandLine(cmd)
      cout3 = cl3.run()
      if not cout3.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  whole cerebellum for %s'%(aseg)
            print cout3.runtime.stderr
            print cout3.runtime.stdout
            return None     
      cmd = 'rm whole_right_cerebellum.* whole_left_cerebellum.*'
      cl4 = CommandLine(cmd)
      cout4 = cl4.run()      
      whole_cerebellum = glob('%s/whole_cerebellum.*'%(pth))
      os.chdir(cwd)
      return whole_cerebellum[0]
      
def make_cerebellum(aseg):
      cwd = os.getcwd()
      pth, nme = os.path.split(aseg)
      os.chdir(pth)
      cl = CommandLine('fslmaths %s -thr 47 -uthr 47 right_cerebellum'% (aseg))
      cout = cl.run()
      
      if not cout.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  right cerebellum for %s'%(aseg)
            return None

      cl2 = CommandLine('fslmaths %s -thr 8 -uthr 8 left_cerebellum'% (aseg))
      cout2 = cl2.run()

      if not cout2.runtime.returncode == 0:
            os.chdir(cwd)
            print 'Unable to create  left cerebellum for %s'%(aseg)
            return None

      cl3 = CommandLine('fslmaths left_cerebellum -add right_cerebellum -bin grey_cerebellum')
      cout3 = cl3.run()
      if not cout3.runtime.returncode == 0:
            print 'Unable to create whole cerebellum for %s'%(aseg)
            print cout3.runtime.stderr
            print cout3.runtime.stdout
            return None
      
      cmd = 'rm right_cerebellum.* left_cerebellum.*'
      cl4 = CommandLine(cmd)
      cout4 = cl4.run()
      os.chdir(cwd)
      cerebellum = glob('%s/grey_cerebellum.*'%(pth))
      return cerebellum[0]

def make_cerebellum_nibabel(aseg):
      """ use nibabel to make cerebellum"""
      #cwd = os.getcwd()
      pth, nme = os.path.split(aseg)
      #os.chdir(pth)
      img = ni.load(aseg)
      newdat = np.zeros(img.get_shape())
      dat = img.get_data()
      newdat[dat == 8] = 1
      newdat[dat == 47] = 1
      newimg = ni.Nifti1Image(newdat, img.get_affine())
      newfile = os.path.join(pth, 'grey_cerebellum.nii')
      newimg.to_filename(newfile)
      return newfile
      
if __name__ == '__main__':

    root = '/home/jagust/cindeem/tmpucsf'
    mridir = '/home/jagust/UCSF/freesurfer'
    app = wx.App()
    
    tracer = MyTracerDialog()
    print tracer
    subs = MyDirsDialog(prompt='Choose Subjectss ',
                        indir='/home/jagust/arda/lblid')
    alldirs = []
    for s in subs:
        dirs = glob('%s/%s*'%(s,tracer))
        alldirs.extend(dirs)
    
    finalchoice = MyScanChoices(alldirs)
    #global outdict
    outdict = {}
    make_subject_dict(finalchoice,outdict) 
    MyRadioChoices(outdict).Show()
    app.MainLoop()
    """
    for item in outdict:
        if outdict[item][1] is None:
              continue
        else:
              petdir, dx = outdict[item]
        subid, _ = os.path.split(item)
        print subid
        # check for and Make Target Directories
        basedir = os.path.join(root, '%s-spm8'%(dx))
        subdir, _ = make_dir(basedir, dirname=subid)
        tracerdir, already_exists = make_dir(subdir, dirname = '%s_nifti' % (tracer.lower()) )
        if already_exists:
              print '%s already has %s dir, remove all related dirs if you want to redo' % (subid, tracer)
              print 'skipping %s' %(subid)
              continue
        rawdatadir, _  = make_dir(subdir, dirname = 'RawData')
        rawtracer, _  = make_dir(rawdatadir, dirname = tracer)
        anatomydir, anat_exists  = make_dir(subdir,dirname='fs_anatomy')
        masksdir, _  = make_dir(tracerdir,dirname='ref_region')
        print 'directories created for %s' % subid
        
        # Copy PET data, convert to nifti
        newraw = copy_dir(petdir, rawtracer)
        ecats = copy_dir(rawtracer, tracerdir, pattern='*.v')
        newname = '%s_%s' % (subid, tracer)
        convertallecat(ecats, newname)
        print 'ecats converted for %s ' % subid

        # Get MRI, convert
        if not anat_exists:
              mri = os.path.join(mridir, subid, 'mri', 'nu.mgz')
              mri_nii = move_and_convert(mri, anatomydir, 'rad_nu_mri.nii')
              print 'mri converted'
        # Get aseg, convert
        aseg = os.path.join(mridir, subid, 'mri', 'aseg.mgz')
        aseg_nii = move_and_convert(aseg, masksdir, 'rad_aseg.nii')
        
        # Generate reference Region
        if tracer == 'FDG':
            make_brainstem(aseg_nii)
            print 'brainstem created for %s' % subid
        else:
            make_cerebellum(aseg_nii)
            print 'cerebellum created for %s ' % subid
    """

# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import os, sys
import re
from glob import glob
import tempfile
from nipype.interfaces.base import CommandLine
from nipype.utils.filemanip import split_filename, fname_presuffix
import logging

def tar_cmd(infile):
    """ given a ipped tar archive, untars"""
    cwd = os.getcwd()
    pth, nme = os.path.split(infile)
    os.chdir(pth)
    cl = CommandLine('tar xfvz %s'%(infile))
    cout = cl.run()
    os.chdir(cwd)
    return pth

def zip_files(files):
    if not hasattr(files, '__iter__'):
        files = [files]
    for f in files:
        base, ext = os.path.splitext(f)
        if 'gz' in ext:
            # file already gzipped
            continue
        cmd = CommandLine('gzip %s' % f)
        cout = cmd.run()
        if not cout.runtime.returncode == 0:
            logging.error('Failed to zip %s'%(f))

def unzip_file(infile):
    """ looks for gz  at end of file,
    unzips and returns unzipped filename"""
    base, ext = os.path.splitext(infile)
    if not ext == '.gz':
        return infile
    else:
        cmd = CommandLine('gunzip %s' % infile)
        cout = cmd.run()
        if not cout.runtime.returncode == 0:
            print 'Failed to unzip %s'%(infile)
            return None
        else:
            return base

def unzip_files(inlist):
    result = []
    for f in inlist:
        unzipped = unzip_file(f)
        result.append(unzipped)
    return result

def copy_files(infiles, newdir):
    """wraps copy file to run across multiple files
    returns list"""
    newfiles = []
    for f in infiles:
        newf = copy_file(f, newdir)
        newfiles.append(newf)
    return newfiles

def copy_file(infile, newdir):
    """ copy infile to new directory
    return full path of new file
    """
    cl = CommandLine('cp %s %s'%(infile, newdir))
    out = cl.run()
    if not out.runtime.returncode == 0:
        print 'failed to copy %s' % infile
        print out.runtime.stderr
        return None
    else:
        basenme = os.path.split(infile)[1]
        newfile = os.path.join(newdir, basenme)
        return newfile

    
def remove_files(files):
    """removes files """
    if not hasattr(files, '__iter__'):
        cl = CommandLine('rm %s'% files)
        out = cl.run()
        if not out.runtime.returncode == 0:
            print 'failed to delete %s' % files
            print out.runtime.stderr
        return
    for f in files:
        cl = CommandLine('rm %s'% f)
        out = cl.run()
        if not out.runtime.returncode == 0:
            print 'failed to delete %s' % f
            print out.runtime.stderr

            
def make_dir(base_dir, dirname='fdg_nifti'):
    """ makes a new directory if it doesnt alread exist
    returns full path
    
    Parameters
    ----------
    base_dir : str
    the root directory
    dirname  : str (default pib_nifti)
    new directory name
    
    Returns
    -------
    newdir  : str
    full path of new directory
    """
    newdir = os.path.join(base_dir,dirname)
    if not os.path.isdir(base_dir):
        raise IOError('ERROR: base dir %s DOES NOT EXIST'%(base_dir))
    directory_exists = os.path.isdir(newdir)
    if not directory_exists:
        os.mkdir(newdir)
    return newdir, directory_exists

def make_rec_dir(base_dir, dirname='fdg_nifti'):
    """ makes a new directories recursively if it doesnt already exist
    returns full path
    
    Parameters
    ----------
    base_dir : str
    the root directory
    dirname  : str (default pib_nifti)
    new directory name
    
    Returns
    -------
    newdir  : str
    full path of new directory
    """
    newdir = os.path.join(base_dir,dirname)
    directory_exists = os.path.isdir(newdir)
    if not directory_exists:
        os.makedirs(newdir)
    return newdir, directory_exists



def get_subid(instr, pattern='B[0-9]{2}-[0-9]{3}'):
    """ given input string searches for lblid pattern
    Bxx-xxx and returns if found, otherwise raises exception"""
    m = re.search(pattern, instr)
    try:
        return m.group()
    except:
        raise IOError('no valid ID found in %s'%(instr))


def touch_file(file):
    """ uses CommandLine to 'touch' a file,
    creating an empty exsisting file"""
    cmd = CommandLine('touch %s' % file)
    cout = cmd.run()
    return cout


def copy_tmpdir(infile):
    """copies file to tempdir, returns path
    to file copied into tmpdir"""
    tmpdir = tempfile.mkdtemp()
    newfile = copy_file(infile, tmpdir)
    return newfile


def copy_dir(dir, dest, pattern='*'):
      """copies files matching pattern in dir to dest
      returns list of abspath to new copied items """
      items = glob('%s/%s'%(dir,pattern))
      newitems = []
      for item in items:
            newitem = copy_file(item, dest)
            newitems.append(newitem)
      return newitems


def find_single_file(searchstring):
    """ glob for single file using searchstring
    if found returns full file path """
    file = glob(searchstring)
    if len(file) < 1:
        print '%s not found' % searchstring
        return None
    else:
        outfile = file[0]
        return outfile

def remove_dir(dir):
    """removes direcotry and contents"""
    cmd = 'rm -rf %s'%(dir)
    out = CommandLine(cmd).run()
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return False
    else:
        return True

def find_files(globstr, n=1):
    """globs for globstr
    if number of files is less than n
    return None
    else
    return frames"""
    
    frames = glob(globstr)
    frames.sort()
    if len(frames) < n:
        logging.error('%s only has %d frames, RUNBYHAND'%(globstr,
                                                          len(frames)))
        return None
    else:
        return frames

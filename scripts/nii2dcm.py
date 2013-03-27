# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys
import argparse
sys.path.insert(0,'/home/jagust/cindeem/CODE/petproc-stable/preproc')
import dicom_tools 

if __name__ == '__main__':


    # create the parser
    parser = argparse.ArgumentParser(
        description='Convert nifti mean image to dicoms')

    # add the arguments
    parser.add_argument(
        'nifti', type=str, nargs=1,
        help='nifti Filename')

    parser.add_argument(
        'dicomdir', type=str, nargs=1,
        help='Directory containing original dicoms')
    

    parser.add_argument(
        'outdir', type=str, nargs=1,
        help='Directory to save new dicoms')
    
        
    if len(sys.argv) ==1:
        parser.print_help()
    else:
        args = parser.parse_args()
        
        dicom_tools.nifti_to_dicom(args.nifti[0],
                                   args.dicomdir[0],
                                   args.outdir[0])

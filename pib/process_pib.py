# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
PIB preprocessing

1. find mri aseg (generated with freesurfer)
2. find frames (34 or 35 pib frames nifti format)
3. realign_QA: 
   a. make realign_QA directory
   b. copy frames to directory
   c. realign frames 6-end to frame 17 (2-pass spm realign)
   d. sum frames 1-5
   e. register summed-1-5 to mean from step c, apply to each frame
   f. QA on realigned frames
4. make coreg_mri2pet directory
   a. copy brainmask and aseg to coreg dir
   b. make grey-matter cerebellum from aseg
   c. coreg and reslice mri to pet, apply transform to cerebellum mask
5. logan graphical analysis
   a. make dvr directory
   b. using cerebellum and realigned frames, run pyga_logan
   c. (make sure to generate timing file and TAC)
6. stats in dvr directory
   a. use reslice aseg+aparc to pull PIB INDEX regions 
      (separate and as one mask)
   b. write pibindex to dvr directory
"""
import ../preprocessing as pp
import ../base_gui as bg




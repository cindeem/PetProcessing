# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python
import os
import nibabel
import numpy as np

import scipy.weave as weave
from scipy.weave import converters
import numpy


class PetPsf():

    # resolution determined for out Pet scanner
    _ecat_resolution = {'radial' : [3.64, 4.10, 7.40 ],
                        'tangential' : [3.64, 4.05, 4.46 ],
                        'axial' : [3.97, 5.36, 6.75 ] }
    _halfwidth = 7; # predefined by previous testing on scanner
    _base_divisor = 2.35482  #standard constant
    
    def __init__(self, infile):
        """this class loads in am image, and applies the point spread
        function specific to the PET scanner up at LBL to the image

        Parameters
        ----------
        infile : file of image to apply pet scanner specific psf
        """

        self.img = nibabel.load(infile)
        dat =  self.img.get_data().squeeze()
        self.dat = np.nan_to_num(dat) #deal with NAN in matrix
        self.matrix_dim = self.dat.shape
        ndim = len(self.dat.shape)
        self.voxel_res = self.img.get_header().get_zooms()[:ndim]
        rad = [x /self._base_divisor for x in self._ecat_resolution['radial'] ]
        tan = [x / self._base_divisor for x in self._ecat_resolution['tangential'] ]
        axial = [x / self._base_divisor for x in self._ecat_resolution['axial'] ]

        self.radial = np.array(rad) 
        self.tan = np.array(tan)
        self.axial = np.array(axial)
        

        # find minimum value across 3 arrays
        self.minres =  min(rad + tan + axial)
        self.uniform_sm = self.minres
        self.uniform_sm_sq = self.minres**2
        # size of the data array
        self.average_pixel_size = (self.voxel_res[1] + self.voxel_res[0]) / 2.0

        self.deltarad = (self.radial[1:] - self.radial[:-2]) / 100.0
        self.deltatan = (self.tan[1:] - self.tan[:-2]) / 100.0
        self.deltaaxial = (self.axial[1:] - self.axial[:-2]) / 100.0


    def _calc_sigma(self, insigma, norm):
        """calculates true sigma based on constraints
        and converts to pixel widths using norm

        Parameters
        ----------
        insigma : the sigma calculated for a specific region

        norm : pixel dim, or avg pixel dim for direction in which
               sigma is being calculated
        """
        sigma_sq = insigma**2
        sigma_sq = sigma_sq - self.uniform_sm_sq
        if  sigma_sq > 0.0:
            out = np.sqrt(sigma_sq)
        else:
            out = 0.0
        return out / norm

    
    def compute_xy_kernel(self,x,y):
        """Find the smoothing kernel specific to a given x,y coordinate

        Parameters
        ----------
        x : x voxel
        y : x voxel
        
        """
        
        center_pixel = np.array(self.matrix_dim[:2]) / 2.0 # center voxel in a slice
        xydim = np.prod(self.matrix_dim[:2]) #number of voxels in a slice

        dx = (x - center_pixel[0]) * self.voxel_res[0]
        dy = (center_pixel[1] - y) * self.voxel_res[1]

        radius = np.sqrt(dx**2 + dy**2 )# in mm
        print radius
        if radius > 0.0:
            angle = np.arctan2(dy,dx)
        else:
            angle = 0.0
        if radius < 100.0:
            sigma_radial = self.radial[0] + self.deltarad[0] * radius
            sigma_tan = self.tan[0] + self.deltatan[0] * radius
        else:
            sigma_radial = self.radial[1] + self.deltarad[1] * (radius - 100.0)
            sigma_tan = self.tan[1] + self.deltatan[1] * (radius - 100.0)

        sigma_radial = self._calc_sigma(sigma_radial,self.average_pixel_size)
        sigma_tan = self._calc_sigma(sigma_tan, self.average_pixel_size)
        kern = self._calc_gauss2d_kernel(sigma_radial, sigma_tan, angle)
        return kern

    def _calc_gauss2d_kernel(self, sigma_rad, sigma_tan, angle):
        """
        returns N X N gaussian kernel N = halfwidth * 2 + 1
        sigmas are in matrix dim widths, NOT mm

        angle : float
            rotation value
        
        """

        length = self._halfwidth * 2 +1
        length_sq = length**2
        kern = np.zeros(length_sq)
        halfwidth = self._halfwidth

        # if either sigma is zero, return a delta function
        # or dont alter the data
        if (sigma_rad <= 0.0) or (sigma_tan <= 0.0):
            kern[length * length / 2] = 1.0
            print 'returning delta'
            return kern
        cos_theta = np.cos(angle)
        sin_theta = np.sin(angle)
        sigma_rad_sq = sigma_rad**2
        sigma_tan_sq = sigma_tan**2

        tmpjnk = np.zeros((length, length))
        indx, indy = np.nonzero(tmpjnk == 0)
        u = (indx - halfwidth)* cos_theta - (indy - halfwidth) * sin_theta
        v = (indx - halfwidth) * sin_theta + (indy - halfwidth) * cos_theta
        
        val = np.exp(-.5 * u * u / sigma_rad_sq)
        val = val * np.exp(-.5 * v * v / sigma_tan_sq)
        val = val / np.sum(val)
        return val
    
        

    def convolve_xy(self):
        """ convolve the xy specific 2D kernel with points in
        the data slices in the x-y plane
        returns result as an array in case you want
        to save it or check it out
        """

        xmax, ymax, zmax = self.matrix_dim

        psfdat = np.zeros(self.matrix_dim)
        xrange = np.arange(self._halfwidth, xmax - self._halfwidth)
        yrange = np.arange(self._halfwidth, ymax - self._halfwidth)

        for x in xrange:
            for y in yrange:
                kern = self.compute_xy_kernel(x,y)
                half_kern = kern.shape[0]/2
                for z in np.arange(zmax):
                    tmp = self.dat[x-self._halfwidth:x+self._halfwidth+1,
                                   y-self._halfwidth:y+self._halfwidth+1,
                                   z].ravel()
                    psfdat[x,y,z] = np.sum(tmp * kern)
        self.xy_psf = psfdat
        return psfdat


    def wconvolve_xy(self):
        """convolve the xy specific 2D kernel with points in
        the data slices in the x-y plane
        returns result as an array in case you want
        to save it or check it out
        USES WEAVE for SPEED
        """
        xmax, ymax, zmax = self.matrix_dim
        mysum = 0.0
        psfdat = np.zeros(self.matrix_dim)
        xrange = np.arange(self._halfwidth, xmax - self._halfwidth)
        yrange = np.arange(self._halfwidth, ymax - self._halfwidth)
        dat = self.dat
        code = \
        """
        int xind, yind;
        fprintf("%d,%d",(x,y));
        for (int z = 0; z< zmax; z++){
           for (int i = 0; i<15; i++){
               xind = x - i;
               xind -= 7;
               yind = y - i;
               yind -= 7;
               fprintf("%d,%d",(x,y));
               fprintf("dat = %f",dat(xind, yind,z));
               fprintf("\\n");
               fprintf("kernel = %f", kernel(i));
               fprintf("\\n");
               }
               }
        """
        for x in xrange:
            for y in yrange:
                kernel = self.compute_xy_kernel(x,y)
                weave.inline(code, ['x','y','zmax','mysum','psfdat','kernel','dat'],
                             type_converters=converters.blitz,
                             compiler='gcc')
        self.xy_psf = psfdat
        return psfdat
        
                            
        #tmp =  dat(x-(i-7), y-(i-7),z)
        #psfdat(x,y,z) = mysum;
    def compute_z_kernel(self, x, y):
        """
        compute z location specific kernel

        Parameters
        ----------
        x : x coordinate of voxel
        y : y coordinate of voxel

        """

        halfwidth = self._halfwidth
        center_pixel = np.array(self.matrix_dim[:2]) / 2.0 # center voxel in a slice
        dx = (x - center_pixel[0]) * self.voxel_res[0]
        dy = (center_pixel[1] - y) * self.voxel_res[1]

        radius = np.sqrt( dx**2 + dy**2)

        if radius < 100 :
            sigma_axial = self.axial[0] + self.deltaaxial[0] * radius
        else:
            sigma_axial = self.axial[1] + self.deltaaxial[1] * (radius - 100.0)

        sigma_axial = self._calc_sigma(sigma_axial, self.voxel_res[2])
        kern = self._calc_gauss1d_kernel(sigma_axial)
        return kern

    def _calc_gauss1d_kernel(self, sigma):
        """calculates a 1D gaussian kernel based on a given sigma
        normalizes result
        """

        fwhm = self._halfwidth
        len = fwhm * 2 + 1
        kern = np.zeros(len)

        if sigma < 0.0:
            kern[fwhm] = 1.0
            return kern

        x = np.arange(-fwhm, fwhm+1)
        kern = np.exp(-.5 * x**2 / (sigma**2))
        
        kern = kern / np.sum(kern)
        return kern
        
    def convolve_z(self):
        """ convolve the results of the xy_smooth with
        a new kernel computed in the z direction
        """
        halfwidth = self._halfwidth
        xmax, ymax, zmax = self.matrix_dim

        psfdat = np.zeros(self.matrix_dim)
        xrange = np.arange(halfwidth, xmax - halfwidth)
        yrange = np.arange(halfwidth, ymax - halfwidth)

        finaldat = np.zeros(self.matrix_dim)
        
        for x in xrange:
            for y in yrange:
                kern = self.compute_z_kernel(x,y)
                for z in np.arange(0,
                                   zmax):
                    if (z - halfwidth) <= 0:
                        tmpdat = np.zeros(15)
                        if z == 0:
                            tmpdat[7:] = self.xy_psf[x,y,z:z+halfwidth + 1]
                        else:
                            tmpdat[7 - z :] = self.xy_psf[x,y,0:z+halfwidth + 1]
                    elif (z + halfwidth + 1 > zmax):
                        tmpdat = np.zeros(15)
                        if z == zmax:
                            tmpdat[:7] = self.xy_psf[x,y,z-halfwidth:]
                        else:
                            tmpdat[:15-(8-(zmax-z))] = self.xy_psf[x,y,z-halfwidth:]
                    else:
                        tmpdat = self.xy_psf[x,y, z - halfwidth : z + halfwidth + 1]

                    finaldat[x,y,z] = np.sum(tmpdat * kern)
                                   

        self.finaldat = finaldat
        return finaldat

    def save_result(self, filename=None):
        """ saves the result of smoothing input in xy, and z to a new file

        Parameters
        ----------
        filename : file to save new image

        if None, will create filename from original file and
        save in same directory prepending PET_PSF to filename
        """
        if filename is None:
            basename = os.path.abspath(self.img.get_filename())
            pth, filenme = os.path.split(basename)
            nme, ext = os.path.splitext(filenme)
            filename = os.path.join(pth, 'PET_PSF_%s.nii'%(nme))
        newimg = nibabel.Nifti1Image(self.finaldat,
                                     self.img.get_affine())
        newimg.to_filename(filename)
        return filename

if __name__ == '__main__':


    # this SHOULD be resliced into space of pet image, but we are lazy
    infile = '/home/jagust/cindeem/CODE/pverousset/tmp_atrophy_smooth/rgm_seg_bin.nii'
    
    petpsf = PetPsf(infile)
    xyresult = petpsf.convolve_xy()
    zresult = petpsf.convolve_z()
    newfile = petpsf.save_result()

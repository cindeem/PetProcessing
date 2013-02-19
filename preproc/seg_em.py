import os, sys
import numpy as np
import nibabel as ni
sys.path.insert(0,'/home/jagust/cindeem/local/lib/python2.7/site-packages')
import mixture

def calc_mu_sigma(flat):
    biny, binx = np.histogram(flat)
    max1 = np.where(biny == biny[1:].max())
    max2 = np.where(biny == biny[max1[0]+1:].max())
    m1 = binx[0]
    m2 = binx[max1[0]+1]
    m3 = binx[max2[0] + 2]
    std1 = flat[flat<m2].std()
    std2 = flat[np.logical_and(flat > m1, flat < m3)].std()
    return m1, m2, m3,  std1, std2


def load_data(datf):
    """ loads nifti file
    cleans nan, sets negs to 0
    and flattens,
    Returns
    --------
    img : nifti1 image object
    flat : nparray
        flattened data
    """
    img = ni.load(datf)
    dat = img.get_data()
    dat = np.nan_to_num(dat)
    dat[dat < 0] = 0
    flat = dat.flatten()
    return img, flat

def run_em(flat):
    """ run expectation max on flat data"""
    m1, m2, m3, std1, std2 = calc_mu_sigma(flat)
    flat[flat < m2] = 0
    data = mixture.DataSet()
    data.fromArray(flat)
    
    n1 = mixture.NormalDistribution(m1, std1)
    n2 = mixture.NormalDistribution(m2, std2)
    n3 = mixture.NormalDistribution(m3, std2)
    m = mixture.MixtureModel(3,[0.4,0.3, 0.3], [n1,n2,n3])
    
    m.EM(data,40,0.1)
    newdat = np.zeros(flat.shape)
    clust = m.classify(data)
    return clust

def save_dat(clust, img, datdir):
    newdat = clust + 1
    newdat.shape = img.get_shape()
    newimg = ni.Nifti1Image(newdat, img.get_affine(), ni.Nifti1Header())
    newf = os.path.join(datdir, 'segimg.nii.gz')
    newimg.to_filename(newf)
    return newf

def main(infile):
    img, flat = load_data(infile)
    clust = run_em(flat)
    outdir, _ = os.path.split(infile)
    newf = save_dat(clust, img, outdir)
    print 'saved %s'%newf
    return newf

"""
if __name__ == '__main__':

    try:
        infile = sys.argv[1]
        newf = main(infile)
    except:
    
        
"""

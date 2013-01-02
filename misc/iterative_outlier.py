import pandas
import numpy as np
from scipy.stats import scoreatpercentile


def calc_quartiles(data):
    """returns q1, q3, and iqr (interquartile range) of
    data (note data needs to be sorted)"""
    q1 = scoreatpercentile(data, 25)
    q3 = scoreatpercentile(data, 75)
    iqr = q3 - q1
    return q1, q3, iqr


def find_outliers(data):
    q1, q3, iqr = calc_quartiles(data)
    thr = q3 + 1.5 * iqr
    print thr, q1, q3
    outliers = data[data >= thr]
    if len(outliers) > 0: #no more outliers
        return data[data < thr]
    else:
        return find_outliers(data)


if __name__ == '__main__':

    ifile = '/home/jagust/graph/data/Spreadsheets/data_summary.xls'
    dat = pandas.ExcelFile(ifile)
    sheetnames = dat.sheet_names
    pib = dat.parse('PIB')
    pibdat = np.array(pib.PIBINDEX_noIT.copy())
    pibdat.sort() # sort data
    #q1, q3, iqr = calc_quartiles(pibdat)
    #thr = q3 + 1.5 * (q3 - q1)
    #newdat = pibdat[pibdat < thr]
    nooutlier_data = find_outliers(pibdat)
    q1, q3, iqr = calc_quartiles(nooutlier_data)
    cutoff = q3 + 1.5 * iqr

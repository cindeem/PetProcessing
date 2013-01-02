import sys, os
sys.path.insert(0, '/home/jagust/cindeem/local/lib/python2.7/site-packages/pysurfer-0.3-py2.7.egg')
from surfer import Brain, io
import surfer


def main(subid, overlay):
    _, fname = os.path.split(overlay)
    
    hemi = fname[:2]
    brain = Brain(subid, hemi, "pial",
                  config_opts=dict(cortex="low_contrast"))
    brain.add_overlay(overlay, min=0.4, max=4, sign="pos")
    brain.show_view('m')

if __name__ == '__main__':

    subid = sys.argv[1]
    overlay = sys.argv[2]
    main(subid, overlay)

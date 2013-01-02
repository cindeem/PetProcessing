from distutils.core import setup

setup(
    name='PetProcessing',
    version='0.1.0',
    author='C Madison',
    author_email='cindee at berkeley dot edu',
    packages=['PetProcessing',
              'PetProcessing.pvc',
              'PetProcessing.pyga',
              ],
    scripts=['bin/ex1.py',],
    license='LICENSE.txt',
    description='Tools, Scripts used for PET data',
    long_description=open('README').read(),
    install_requires=[
        "numpy >= 1.6.1",
    ],
)

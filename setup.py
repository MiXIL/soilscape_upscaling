#!/usr/bin/env python
"""
Setup script for SoilSCAPE Upscaling Code
"""

from numpy.distutils.core import setup, Extension

setup(name='soilscape_upscaling',
      version='0.1',
      description='A library to upscale in situ soil moisture estimates'
                  'using Random Forests',
      author='Daniel Clewley and Jane Whitcomb',
      url='http://soilscape.usc.edu/',
      packages=['soilscape_upscaling'])

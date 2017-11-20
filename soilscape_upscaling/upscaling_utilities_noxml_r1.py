#!/usr/bin/env python
"""
SoilSCAPE Random Forests upscaling code.

Dan Clewley & Jane Whitcomb

General purpose utilities

This file is licensed under the GPL v3 License. A copy of this

license is available to download with this file.


"""

import os
import shutil
import tempfile
import collections
import rsgislib
from rsgislib import imagecalc
from rsgislib.imagecalc import BandDefn
from rsgislib import rastergis

def get_gdal_format(file_name):
    """ Get GDAL format, based on filename """
    gdalStr = ''
    extension = os.path.splitext(file_name)[-1].lower()
    if extension in ['.env', '.bil', '.bsq']:
        gdalStr = 'ENVI'
    elif extension == '.kea':
        gdalStr = 'KEA'
    elif extension == '.tif':
        gdalStr = 'GTiff'
    elif extension == '.img':
        gdalStr = 'HFA'
    else:
        raise Exception('Type not recognised')
    
    return gdalStr


def colour_SM_image(inimage, colourimage, max_value=0.5, band=1):
    """
    Colour image 

    """

    if max_value == 0.5:
        
        # Add class field:
        bandDefns = []
        bandDefns.append(BandDefn('SM',inimage,1))

        expression = []
        expression.append('0.00')
        expression.append('(SM > 0.00) && (SM <= 0.05)? 1 : 0')
        expression.append('(SM > 0.05) && (SM <= 0.10)? 2 : 0')
        expression.append('(SM > 0.10) && (SM <= 0.15)? 3 : 0')
        expression.append('(SM > 0.15) && (SM <= 0.20)? 4 : 0')
        expression.append('(SM > 0.20) && (SM <= 0.25)? 5 : 0')
        expression.append('(SM > 0.25) && (SM <= 0.30)? 6 : 0')
        expression.append('(SM > 0.30) && (SM <= 0.35)? 7 : 0')
        expression.append('(SM > 0.35) && (SM <= 0.40)? 8 : 0')
        expression.append('(SM > 0.40) && (SM <= 0.45)? 9 : 0')
        expression.append('(SM > 0.45) && (SM <= 0.50)? 10 : 0')

        gdalformat = get_gdal_format(colourimage)
        datatype = rsgislib.TYPE_8INT

        temp_dir = tempfile.mkdtemp(prefix='soilscape_upscaling')
        colourbase = os.path.basename(colourimage)
        colour = []
        for i in range(11):
            colour.append(os.path.join(temp_dir,colourbase.replace('.kea',str(i)+'.kea')))
            imagecalc.bandMath(colour[i], expression[i], gdalformat, datatype, bandDefns)

        bandDefns = []
        for i in range(11):
            SMclass = 'SM'+str(i)
            bandDefns.append(BandDefn(SMclass,colour[i],1))
            if i == 0: 
                expression = SMclass
            else:
                expression = expression+'+'+SMclass
        print('expression: ',expression)
        imagecalc.bandMath(colourimage, expression, gdalformat, datatype, bandDefns)   
    
        shutil.rmtree(temp_dir)

        # Populate stats (converts to RAT):
        rastergis.populateStats(colourimage,False,False,True,ratband=1)

        # Add class field:
        bandStats = []
        bandStats.append(rastergis.BandAttStats(band=1,maxField="SMclass"))
        rastergis.populateRATWithStats(colourimage,colourimage,bandStats,ratband=1)

        field = 'SMclass'
        classcolours = {}
        colourCat = collections.namedtuple('ColourCat', ['red', 'green', 'blue', 'alpha'])
        for i in range(11):
            classcolours[i] = colourCat(red=0, green=0, blue=0, alpha=255)
        classcolours[0] = colourCat(red=0, green=0, blue=0, alpha=255)
        classcolours[1] = colourCat(red=165, green=0, blue=38, alpha=255)
        classcolours[2] = colourCat(red=215, green=48, blue=39, alpha=255)
        classcolours[3] = colourCat(red=244, green=109, blue=67, alpha=255)
        classcolours[4] = colourCat(red=253, green=174, blue=97, alpha=255)
        classcolours[5] = colourCat(red=254, green=224, blue=144, alpha=255)
        classcolours[6] = colourCat(red=224, green=243, blue=248, alpha=255)
        classcolours[7] = colourCat(red=171, green=217, blue=233, alpha=255)
        classcolours[8] = colourCat(red=116, green=173, blue=209, alpha=255)
        classcolours[9] = colourCat(red=69, green=117, blue=180, alpha=255)
        classcolours[10] = colourCat(red=49, green=54, blue=149, alpha=255)
        rastergis.colourClasses(colourimage,field,classcolours)

    else:
        raise ValueError('Failed to find colours for specified max_value')























#!/usr/bin/env python
"""
SoilSCAPE Random Forests upscaling code.

Dan Clewley & Jane Whitcomb

General purpose utilities

This file is licensed under the GPL v3 Licence. A copy of this
licence is available to download with this file.

"""

import subprocess
import os
import tempfile as tempfile

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

def colour_sm_image(inimage, outimage, max_value=0.5, band=1):
    """
    Colour image using RSGISLib XML interface

    FIXME: This function should be tidied up possibly to use
    """

    gdalFormat = get_gdal_format(outimage)

    if max_value == 0.5:
        out_colour_table = '''
            <rsgis:colour name="class_name_1" id="1"  band="{0}" lower="0" upper="0.05" red="165" green="0" blue="38" />
            <rsgis:colour name="class_name_2" id="2"  band="{0}" lower="0.05" upper="0.10" red="215" green="48" blue="39" />
            <rsgis:colour name="class_name_3" id="3"  band="{0}" lower="0.10" upper="0.15" red="244" green="109" blue="67" />
            <rsgis:colour name="class_name_3" id="4"  band="{0}" lower="0.15" upper="0.20" red="253" green="174" blue="97" />
            <rsgis:colour name="class_name_3" id="5"  band="{0}" lower="0.2" upper="0.25" red="254" green="224" blue="144" />
            <rsgis:colour name="class_name_3" id="6"  band="{0}" lower="0.25" upper="0.30" red="224" green="243" blue="248" />
            <rsgis:colour name="class_name_3" id="7"  band="{0}" lower="0.30" upper="0.35" red="171" green="217" blue="233" />
            <rsgis:colour name="class_name_3" id="8"  band="{0}" lower="0.35" upper="0.40" red="116" green="173" blue="209" />
            <rsgis:colour name="class_name_3" id="9"  band="{0}" lower="0.40" upper="0.45" red="69" green="117" blue="180" />
            <rsgis:colour name="class_name_3" id="10" band="{0}" lower="0.45" upper="0.50" red="49" green="54" blue="149" />
        '''.format(band)
    elif max_value == 0.4:
        out_colour_table = '''
            <rsgis:colour name="class_name_1" id="1"  band="{0}" lower="0" upper="0.04" red="165" green="0" blue="38" />
            <rsgis:colour name="class_name_2" id="2"  band="{0}" lower="0.04" upper="0.08" red="215" green="48" blue="39" />
            <rsgis:colour name="class_name_3" id="3"  band="{0}" lower="0.08" upper="0.12" red="244" green="109" blue="67" />
            <rsgis:colour name="class_name_3" id="4"  band="{0}" lower="0.12" upper="0.16" red="253" green="174" blue="97" />
            <rsgis:colour name="class_name_3" id="5"  band="{0}" lower="0.16" upper="0.20" red="254" green="224" blue="144" />
            <rsgis:colour name="class_name_3" id="6"  band="{0}" lower="0.20" upper="0.24" red="224" green="243" blue="248" />
            <rsgis:colour name="class_name_3" id="7"  band="{0}" lower="0.24" upper="0.28" red="171" green="217" blue="233" />
            <rsgis:colour name="class_name_3" id="8"  band="{0}" lower="0.28" upper="0.32" red="116" green="173" blue="209" />
            <rsgis:colour name="class_name_3" id="9"  band="{0}" lower="0.32" upper="0.36" red="69" green="117" blue="180" />
            <rsgis:colour name="class_name_3" id="10" band="{0}" lower="0.36" upper="0.50" red="49" green="54" blue="149" />
        '''.format(band)
        
    elif max_value == 0.3:
        out_colour_table = '''
            <rsgis:colour name="class_name_1" id="1"  band="{0}" lower="0" upper="0.03" red="165" green="0" blue="38" />
            <rsgis:colour name="class_name_2" id="2"  band="{0}" lower="0.03" upper="0.06" red="215" green="48" blue="39" />
            <rsgis:colour name="class_name_3" id="3"  band="{0}" lower="0.06" upper="0.09" red="244" green="109" blue="67" />
            <rsgis:colour name="class_name_3" id="4"  band="{0}" lower="0.09" upper="0.12" red="253" green="174" blue="97" />
            <rsgis:colour name="class_name_3" id="5"  band="{0}" lower="0.12" upper="0.15" red="254" green="224" blue="144" />
            <rsgis:colour name="class_name_3" id="6"  band="{0}" lower="0.15" upper="0.18" red="224" green="243" blue="248" />
            <rsgis:colour name="class_name_3" id="7"  band="{0}" lower="0.18" upper="0.21" red="171" green="217" blue="233" />
            <rsgis:colour name="class_name_3" id="8"  band="{0}" lower="0.21" upper="0.24" red="116" green="173" blue="209" />
            <rsgis:colour name="class_name_3" id="9"  band="{0}" lower="0.24" upper="0.27" red="69" green="117" blue="180" />
            <rsgis:colour name="class_name_3" id="10" band="{0}" lower="0.27" upper="0.30" red="49" green="54" blue="149" />
        '''.format(band)
    else:
        raise ValueError('Max value must be 0.5 or 0.3')

    outXMLStr = '''<?xml version="1.0" encoding="UTF-8" ?>
    <!--
        Description:
            XML File for execution within RSGISLib
        Created by Dan Clewley on Wed Nov 14 10:04:09 2012.
        Copyright (c) 2012 USC. All rights reserved.
    -->
    
    <!-- Colour up soil moisture surfaces. Colour scheme RdYiBi from http://colorbrewer2.org/ -->
    
    <rsgis:commands xmlns:rsgis="http://www.rsgislib.org/xml/">
    
        <rsgis:command algor="imageutils" option="colourimage" 
            image="{0}" 
            output="{1}" 
            format="{2}" datatype="Byte">
            {3}
        </rsgis:command>
    
    </rsgis:commands>'''.format(inimage, outimage, gdalFormat, out_colour_table)
          
    # Create temp XML File
    (osHandle, outXMLName) = tempfile.mkstemp(suffix='.xml')
    outFile = open(outXMLName, 'w')
  
    # Write out XML
    outFile.write(outXMLStr)
    outFile.close()
   
    print('Colouring image')
    subprocess.check_output(['rsgisexe', '-x', outXMLName])
    os.remove(outXMLName)



#!/usr/bin/env python
"""
Functions to get path to dynamic layers for use
in SoilSCAPE upscaling algorithm

Dan Clewley & Jane Whitcomb

"""

import calendar
import time
import glob
import os
import subprocess

from . import upscaling_common

#: Minimum time difference between date and AirMOSS scene
MIN_TIME_DIFF_AIRBORNE_SAR = 1e10

UPSCALING_PROJ = upscaling_common.UPSCALING_PROJ
UPSCALING_RES = upscaling_common.UPSCALING_RES
GDAL_FORMAT = upscaling_common.UPSCALING_GDAL_FORMAT
GDAL_EXT = "kea"

if GDAL_FORMAT == "ENVI":
    GDAL_EXT = "bsq"
elif GDAL_FORMAT == "GTiff":
    GDAL_EXT = "tif"
else:
    GDAL_EXT = GDAL_FORMAT.lower()

def get_reprojected_dynamic_layer(layer_type, layer_dir, sm_date_ts, temp_dir,
                                  bounding_box=None,
                                  out_res=UPSCALING_RES,
                                  out_proj=UPSCALING_PROJ):
    """
    Gets dynamic layer then subsets and reprojects, optionally cropping to
    bounding box.

    Requires:

    * layer_type - type of layer
    * layer_dir - directory which contains dynamic layers
    * sm_date_ts - date of soil moisture - Python time stamp format
    * temp_dir - directory to save reprojected data to
    * bounding_box - bounding box to subset to

    Returns:

    * Path to reprojected layer and date of dynamic layer (string)

    """
    # Get resampling method for layer type
    if layer_type.startswith('airmoss') or layer_type.startswith('uavsar'):
        resample_method = 'average'
    elif layer_type.startswith('prism'):
        resample_method = 'bilinear'
    # Using ECMWF data which has already been resampled using cubic convolution
    elif layer_type.startswith('ecmwf'):
        resample_method = 'near'

    # Get original file
    orig_layer, file_date = get_dynamic_layer(layer_type, layer_dir, sm_date_ts)

    # Subset using GDAL
    out_layer = os.path.join(temp_dir, '{}_subset.{}'.format(layer_type, GDAL_EXT))
    gdal_warp_cmd = ['gdalwarp',
                     '-r', resample_method,
                     '-of', GDAL_FORMAT]
    if bounding_box is not None:
        gdal_warp_cmd.extend(['-te'])
        gdal_warp_cmd.extend(bounding_box)
    gdal_warp_cmd.extend(['-tr', str(out_res), str(out_res),
                          '-dstnodata', '0',
                          '-t_srs', out_proj,
                          orig_layer, out_layer])
    subprocess.check_call(gdal_warp_cmd)

    return out_layer, file_date

def get_dynamic_layer(layer_type, layer_dir, sm_date_ts):
    """
    Gets path to dynamic layer for a given date.

    Requires:

    * layer_type - type of layer
    * layer_dir - directory which contains dynamic layers
    * sm_date_ts - date of soil moisture - Python time stamp format

    Returns:

    * Path to layer and date of dynamic layer (string)

    """
    # AirMOSS
    if layer_type.startswith('airmoss'):
        polarization = layer_type.split('_')[-1]
        airmoss_files, file_date = get_closest_airmoss(sm_date_ts,
                                                       layer_dir)
        if airmoss_files is None:
            raise Exception('Could not find dynamic layer "{}"'.format(layer_type))
        else:
            return airmoss_files[polarization.upper()], file_date
    # UAVSAR
    elif layer_type.startswith('uavsar'):
        polarization = layer_type.split('_')[-1]
        uavsar_files, file_date = get_closest_uavsar(sm_date_ts,
                                                     layer_dir)
        if uavsar_files is None:
            raise Exception('Could not find dynamic layer "{}"'.format(layer_type))
        else:
            return uavsar_files[polarization.upper()], file_date
    # PRISM
    elif layer_type.startswith('prism'):
        prism_var = layer_type.split('_')[-1]
        prism_file = get_prism_data(sm_date_ts, layer_dir,
                                    prism_var)
        if prism_file is None:
            raise Exception('Could not find dynamic layer "{}"'.format(layer_type))
        else:
            file_date = time.strftime('%Y%m%d', sm_date_ts)
            return prism_file, file_date
    # ECMWF
    elif layer_type.startswith('ecmwf'):
        ecmwf_file = get_ecmwf_data(sm_date_ts, layer_dir)
        if ecmwf_file is None:
            raise Exception('Could not find dynamic layer "{}"'.format(layer_type))
        else:
            file_date = time.strftime('%Y%m%d', sm_date_ts)
            return ecmwf_file, file_date

def get_closest_airmoss(sm_date_ts, airmoss_dir,
                        min_time_diff=MIN_TIME_DIFF_AIRBORNE_SAR):

    """
    Get closest AirMOSS data to date.
    Returns dictionary of files for HH, VV and HV
    data and date.
    """

    # Convert time to s since epoch
    sm_date_epoch = calendar.timegm(sm_date_ts)

    # Get list of AirMOSS files
    airmoss_file_list = sorted(glob.glob(os.path.join(airmoss_dir, '*_hh_*vrt')))

    if len(airmoss_file_list) == 0:
        raise Exception('No AirMOSS files matching "*_hh_*vrt" found'
                        'in {}'.format(airmoss_dir))
    airmoss_date_str = ""
    out_files = None

    for airmoss_file in airmoss_file_list:

        file_name = os.path.split(airmoss_file)[-1]

        elements = file_name.split('_')
        airmoss_date_ts = time.strptime(elements[2], '%y%m%d')

        airmoss_date_epoch = calendar.timegm(airmoss_date_ts)

        time_diff = abs(airmoss_date_epoch - sm_date_epoch)

        if time_diff < min_time_diff:
            min_time_diff = time_diff
            airmoss_date_str = time.strftime('%Y%m%d', airmoss_date_ts)
            out_files = {}
            out_files['HH'] = airmoss_file
            out_files['VV'] = airmoss_file.replace('_hh_', '_vv_')
            out_files['HV'] = airmoss_file.replace('_hh_', '_hv_')

    return out_files, airmoss_date_str

def get_closest_uavsar(sm_date_ts, uavsar_dir,
                       min_time_diff=MIN_TIME_DIFF_AIRBORNE_SAR):

    """
    Get closest UAVSAR data to date.
    Returns dictionary of files for HH, VV and HV
    data and date.
    """
    out_files = None

    # Convert time to s since epoch
    sm_date_epoch = calendar.timegm(sm_date_ts)

    # Get list of uavsar files
    uavsar_file_list = glob.glob(os.path.join(uavsar_dir, '*_HHHH_*kea'))

    if len(uavsar_file_list) == 0:
        raise Exception('No UAVSAR files matching "*_HHHH_*kea" found')
    
    uavsar_date_str = ""
    out_files = None
    
    for uavsar_file in uavsar_file_list:
        
        file_name = os.path.split(uavsar_file)[-1]

        elements = uavsar_file.split('_')
        uavsar_date = elements[1]

        # Not sure why this is here as doesn't do anything if there aren't the expected
        # number of files
        numfilesforDate = len(glob.glob(os.path.join(uavsar_dir, '*{}*kea'.format(uavsar_date))))
        if numfilesforDate < 3:
            continue        

        uavsar_date_ts = time.strptime(uavsar_date, '%y%m%d')
        
        uavsar_date_epoch = calendar.timegm(uavsar_date_ts)

        time_diff = abs(uavsar_date_epoch - sm_date_epoch)

        if time_diff < min_time_diff:
            min_time_diff = time_diff
            uavsar_date_str = time.strftime('%Y%m%d',uavsar_date_ts)
            out_files = {}
            out_files['HH'] = uavsar_file
            out_files['VV'] = uavsar_file.replace('_HHHH_', '_VVVV_')
            out_files['HV'] = uavsar_file.replace('_HHHH_', '_HVHV_')

    return out_files, uavsar_date_str


def get_prism_data(sm_date_ts, prism_dir,
                   prism_var, temporary_dir=None):
    """
    Get PRISM (http://prism.oregonstate.edu/) climate
    data.

    TODO: Download to temp directory if file isn't found
    """
    date_str = time.strftime('%Y%m%d', sm_date_ts)

    prism_search = os.path.join(prism_dir,
                                'PRISM_{0}_*_{1}_bil.bil'.format(prism_var, date_str))
    prism_path = glob.glob(prism_search)
    if len(prism_path) == 0:
        # This is where data could be downloaded
        return None
    else:
        return prism_path[0]


def get_ecmwf_data(sm_date_ts, ecmwf_dir):
    """
    Get ECMWF climate data.

    TODO: Currently relies on having processed data.
    Could be improverd by taking data as it is downloaded.
    """
    date_str = time.strftime('%Y%m%d', sm_date_ts)
    hour_str = time.strftime('%H', sm_date_ts)

    ecmwf_search = os.path.join(ecmwf_dir,
                                '*{0}_{1}_100m.kea'.format(date_str, hour_str))
    ecmwf_path = glob.glob(ecmwf_search)
    if len(ecmwf_path) == 0:
        # This is where data could be downloaded
        return None
    else:
        return ecmwf_path[0]


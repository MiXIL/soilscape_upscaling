#!/usr/bin/env python
"""
SoilSCAPE Random Forests upscaling code.

Dan Clewley & Jane Whitcomb

Functions for stacking bands

"""

import subprocess
import os
from osgeo import gdal
from . import dynamic_layers
from . import upscaling_common

EASE2PROJ4 = upscaling_common.EASE2PROJ4
UPSCALING_RES = upscaling_common.UPSCALING_RES

def set_band_names(input_image, band_names_list, print_names=False):
    """
    A utility function to set band names.
    Taken from RSGISLib (rsgislib.org)

    Requires:

    * input_image
    * band_names_list - list of names for each band

    """
    dataset = gdal.Open(input_image, gdal.GA_Update)

    for i, band_name in enumerate(band_names_list):
        band = i+1
        img_band = dataset.GetRasterBand(band)
        # Check the image band is available
        if img_band is not None:
            if print_names:
                print('Setting Band {0} to "{1}"'.format(band, band_name))
            img_band.SetDescription(band_name)
        else:
            raise Exception("Could not open the image band: {}".format(band))

    dataset = None

def make_stack(data_layers_list, out_dir, sm_date_ts, mask=None, bounding_box=None):
    """
    Makes a stack of all bands to be used in the upscaling.

    Takes a list of DataLayer objects
    """

    out_vrt = os.path.join(out_dir, 'upscaling_layers_stack.vrt')
    out_raster = os.path.join(out_dir, 'upscaling_layers_stack_ease.kea')

    for data_layer in data_layers_list:
        # For dynamic layers check we have the path
        # if we don't find and subset the layer
        if data_layer.layer_type == 'dynamic' and data_layer.layer_path is None:
            dynamic_path, dynamic_date = \
                    dynamic_layers.get_reprojected_dynamic_layer(data_layer.layer_name,
                                                                 data_layer.layer_dir,
                                                                 sm_date_ts,
                                                                 out_dir,
                                                                 bounding_box)
            if dynamic_path is not None:
                data_layer.layer_path = dynamic_path
                data_layer.layer_date = dynamic_date

    # Extract list of band names and layer paths
    band_names = [layer.layer_name for layer in data_layers_list]
    layer_paths = [layer.layer_path for layer in data_layers_list]

    # Create VRT stack of all input layers
    vrt_cmd = ['gdalbuildvrt', '-separate', out_vrt]
    vrt_cmd.extend(layer_paths)

    subprocess.check_call(vrt_cmd)

    # Warp so all layers are the same resolution and data type

    if bounding_box is not None:
        gdalwarp_cmd = ['gdalwarp', '-overwrite',
                        '-ot', 'Float32',
                        '-of', 'KEA']
        gdalwarp_cmd.extend(['-te'])
        gdalwarp_cmd.extend(bounding_box)
        gdalwarp_cmd.extend(['-t_srs', EASE2PROJ4,
                             '-tr', str(UPSCALING_RES), str(UPSCALING_RES),
                             out_vrt, out_raster])
    else:
        gdalwarp_cmd = ['gdalwarp', '-overwrite',
                        '-ot', 'Float32',
                        '-of', 'KEA',
                        '-t_srs', EASE2PROJ4,
                        '-tr', str(UPSCALING_RES), str(UPSCALING_RES),
                        out_vrt, out_raster]
    subprocess.check_call(gdalwarp_cmd)

    set_band_names(out_raster, band_names)

    return out_raster


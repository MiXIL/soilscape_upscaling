#!/usr/bin/env python

"""
Functions to extract stats from image for use
in SoilSCAPE upscaling algorithm.

Dan Clewley & Jane Whitcomb

"""
from __future__ import print_function
import csv
import subprocess
import sys

def extract_stats_for_point(input_stack, point_lat, point_lon):
    """
    Extracts statistics from an image for a point.

    Currently uses 'gdallocationinfo' through subprocess

    Requires:

    * input_stack - stack of all images to extract values from
    * point_lat - lattitude of point
    * point_lon - longitude of point

    Returns:

    * List of extracted values for each band

    """

    gdallocationinfo_cmd = ['gdallocationinfo', '-valonly',
                            '-geoloc', '-wgs84',
                            input_stack, point_lon, point_lat]

    gdal_out = subprocess.check_output(gdallocationinfo_cmd)

    extracted_vals = gdal_out.decode().split()

    if len(extracted_vals) == 0:
        extracted_vals_float = None
    else:
        extracted_vals_float = [float(i) for i in extracted_vals]

    return extracted_vals_float

def extract_layer_stats_csv(input_sensor_locations, output_stats_file,
                            data_layers_list, data_stack):

    """
    Extract statistics for sensor locations

    Input CSV assumed to have the following fields:

    * Sensor Name / ID
    * Latitude
    * Longitude
    * Soil moisture

    Output CSV will contain the same columns + one column for the extracted values
    from each band.

    """

    # Get list of band names
    band_names = [layer.layer_name for layer in data_layers_list]

    in_file_h = open(input_sensor_locations, 'r')
    out_file_h = open(output_stats_file, 'w')

    in_file_csv = csv.reader(in_file_h)
    out_file_csv = csv.writer(out_file_h)

    # Write header
    in_header = next(in_file_csv)
    out_header = in_header
    out_header.extend(band_names)
    out_file_csv.writerow(out_header)

    for line in in_file_csv:
        lattitude = line[1]
        longitude = line[2]

        out_stats = extract_stats_for_point(data_stack, lattitude, longitude)

        if out_stats is not None:
            outline = line
            outline.extend(out_stats)
            out_file_csv.writerow(outline)
        else:
            print('Could not extract stats for sensor {}'.format(line[0]),
                  file=sys.stderr)
    in_file_h.close()
    out_file_h.close()




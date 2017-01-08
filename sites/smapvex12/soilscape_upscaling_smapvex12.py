#!/usr/bin/env python

"""
Script to run the SoilSCAPE upscaling procedure for data from the
SMAPVEX12 network.

Dan Clewley and Jane Whitcomb (2016-12-23)
"""

import argparse
import configparser
import csv
import os
import tempfile
import time
import shutil

from soilscape_upscaling import upscaling_common
from soilscape_upscaling import stack_bands
from soilscape_upscaling import extract_image_stats
from soilscape_upscaling import rf_upscaling
from soilscape_upscaling import upscaling_utilities
from soilscape_upscaling.data_extractors import generic_csv_extractor

MAX_SM_COL = 0.5

def check_create_dir(in_dir_path):
    """
    Check a directory exists and create if it doesn't
    """

    if not os.path.isdir(in_dir_path):
        os.makedirs(in_dir_path)

def run_scaling(config_file, debug_mode=False):   

    """
    Run scaling function for a range of dates
    
    Known issues:

    * Doesn't have checks for most items in the config file so
    will just raise an exception if they are not there.
    
    """

    config = configparser.ConfigParser()
    config.read(config_file)

    create_col_image = True
    
    # Get output directories
    out_dir = config['default']['outdir']
    out_stats_dir = config['default']['out_stats_dir']
    out_csv_dir = config['default']['out_csv_dir']
    out_imge_dir = config['default']['out_images_dir']

    # Check all directories exist
    for script_dir in [out_dir, out_stats_dir, out_csv_dir, out_imge_dir]:
        check_create_dir(script_dir)

    # Get directory containing sensor data
    sensor_data = config['default']['sensor_data']

    # Get a list of nodes.
    # In none are provided use all.
    try:
        sensor_ids_list = config['default']['sensor_ids'].split()
    except KeyError:
        sensor_ids_list = None

    bounding_box = config['default']['bounding_box'].split()

    try:
        upscaling_model = config['default']['upscaling_model']
    except KeyError:
        upscaling_model = "RandomForestRegressor"

    out_stats_file = os.path.join(out_stats_dir, 'scaling_function_stats.csv')
    out_stats_handler = open(out_stats_file, 'w')
    out_stats = csv.writer(out_stats_handler)

    out_var_importance_file = os.path.join(out_stats_dir, 'scaling_function_var_importance.csv')
    out_var_importance_handler = open(out_var_importance_file, 'w')
    out_var_importancee = csv.writer(out_var_importance_handler)
    out_var_importance_header = False

    # Get a list of data layers - to check if using UAVSAR
    data_layers_list = []
    for section in config.sections():
        if section.startswith('layer'):
            data_layer = upscaling_common.DataLayer(config[section])
            if data_layer.use_layer:
                data_layers_list.append(data_layer)

    # Get a list of bandnames
    band_names = [layer.layer_name for layer in data_layers_list]

    # Add mask 
    data_layers_list.append(upscaling_common.DataLayer(config['mask']))

    # Check there aren't any duplicates
    if len(band_names) != len(set(band_names)):
        raise ValueError('Each band must have a unique name:\n'
                         '{}\n were provided'.format(', '.join(band_names)))

    # Write header
    out_stats.writerow(['Date', 'nSamples', 'avgSM_train', 'stdSM_train', 'avgSM_predict',
                        'stdSM_predict', 'RMSE', 'Bias', 'RSq', 'UAVSARDate'])
    
    # Set up data extractor
    csv_extractor = generic_csv_extractor.SoilSCAPECreateCSVGenericStationRowsCSV(sensor_data,
                                                                                  debug_mode=debug_mode)

    # Get list of all available dates in input file
    all_sensor_dates_ts = csv_extractor.get_available_dates()

    # Look through all dates
    for sensor_date_ts in all_sensor_dates_ts:
    
        # Create temp DIR
        temp_dir = tempfile.mkdtemp(prefix='soilscape_upscaling')
        date_str = time.strftime('%Y%m%d', sensor_date_ts)
        out_base_name = date_str
        
        # Extract CSV to use for upscaling from all sensor data.
        sensor_data_csv = os.path.join(temp_dir, "{}_sensor_data.csv".format(out_base_name))

        num_out_records = csv_extractor.create_csv_from_input(sensor_date_ts, sensor_data_csv,
                                                              sensor_ids_list)

        try:
            print("***** {} *****".format(date_str))

            # Create band stack
            data_stack = stack_bands.make_stack(data_layers_list, temp_dir,
                                                sensor_date_ts, bounding_box=bounding_box)

            # Check if using UAVSAR data
            uavsar_date_str = "NA"
            for layer in data_layers_list:
                if layer.layer_name == 'uavsar_hh':
                    uavsar_date_str = time.strftime('%Y%m%d', layer.layer_date)

            # Extract pixel vals
            statscsv = os.path.join(out_csv_dir, out_base_name + '_sensor_data.csv')
            extract_image_stats.extract_layer_stats_csv(sensor_data_csv,
                                                        statscsv,
                                                        data_layers_list, data_stack)
            # Run Random Forests
            out_sm_image = os.path.join(out_imge_dir, out_base_name + '_predict_sm.kea')
            out_sm_col_image = os.path.join(out_imge_dir, out_base_name + '_predict_sm_col.tif')

            rf_par = rf_upscaling.run_random_forests(statscsv, data_stack,
                                                     out_sm_image, data_layers_list,
                                                     upscaling_model=upscaling_model)

            # Write out stats
            out_row = [out_base_name,
                       rf_par['nSamples'],
                       rf_par['averageSMTrain'],
                       rf_par['sdSMTrain'],
                       rf_par['averageSMPredict'],
                       rf_par['sdSMPredict'],
                       rf_par['RMSE'],
                       rf_par['Bias'],
                       rf_par['RSq'],
                       uavsar_date_str]
            out_stats.writerow(out_row)

            # Write header for first record
            if not out_var_importance_header:
                out_var_importancee.writerow(rf_par['varNames'])
                out_var_importance_header = True

            out_var_importancee.writerow(rf_par['varImportance'])

            if create_col_image:
                upscaling_utilities.colour_sm_image(out_sm_image, out_sm_col_image,
                                                    max_value=MAX_SM_COL)

        except Exception as err:
            if debug_mode:
                shutil.rmtree(temp_dir)
                raise
            else:
                print(err)

        # Remove temp files
        shutil.rmtree(temp_dir)

    # Close files
    out_stats_handler.close()

if __name__ == '__main__':

    # Get input parameters
    parser = argparse.ArgumentParser(description="Run SoilSCAPE Scaling function for "
                                                 "the SMAPVEX12 site.")
    parser.add_argument("configfile", 
                        type=str,
                        nargs=1,
                        help="Config file")
    parser.add_argument("--debug", action='store_true',
                        help="Run in debug mode (more error messages; default=False).",
                        default=False, required=False)

    args = parser.parse_args() 

    run_scaling(args.configfile, debug_mode=args.debug)


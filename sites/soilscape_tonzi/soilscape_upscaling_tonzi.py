#!/usr/bin/env python

# soilscape_scaling.py
# A script to extract soil moisture measurements
# from SoilSCAPE database and run Random Forests
# to predict for cells within a 36 km grid
#
# Daniel Clewley (clewley@usc.edu)
# 06/03/2014
#
# Adapted to make use of 'soilscape_upscaling' library
# 11/05/2016

import argparse
import calendar
import configparser
import csv
import os
import sys
import tempfile
import time
import shutil

from soilscape_upscaling import upscaling_common
from soilscape_upscaling import stack_bands
from soilscape_upscaling import extract_image_stats
from soilscape_upscaling import rf_upscaling
from soilscape_upscaling import upscaling_utilities
from soilscape_upscaling.data_extractors import soilscape_db_extractor

MAX_SM_COL = 0.3

def check_create_dir(in_dir_path):
    """
    Check a directory exists and create if it doesn't
    """

    if not os.path.isdir(in_dir_path):
        os.makedirs(in_dir_path)

def py2SQLiteTime(inTimePy):
    """ Converts Python time structure to string in the form:
        YYYY-MM-DD hh:mm:ss
    """
    return time.strftime('%Y-%m-%d %H:%M:%S',inTimePy)

def run_scaling(config_file, debugMode=False):   

    """
    Run scaling function for a range of dates
    
    Known issues:

    * Doesn't have checks for most items in the config file so
    will just raise an exception if they are not there.
    
    """

    config = configparser.ConfigParser()
    config.read(config_file)

    createColImage = True
    
    # Get output directories
    out_dir = config['default']['outdir']
    outputStatsDIR = config['default']['out_stats_dir']
    outputCSVDIR = config['default']['out_csv_dir']
    outputImageDIR = config['default']['out_images_dir']

    # Check all directories exist
    for script_dir in [out_dir, outputStatsDIR, outputCSVDIR, outputImageDIR]:
        check_create_dir(script_dir)

    # Check if an SQLite db has been provided
    # if not use MySQL
    try:
        inSQLite = config['default']['sqlite_db']
    except KeyError:
        inSQLite = None

    # Get start and end time
    starttime_str = config['default']['starttime']
    endtime_str = config['default']['endtime']
    try:
        starttime = time.strptime(starttime_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise ValueError('The "starttime" was not in the required'
                         ' format of YYYY-MM-DD hh:mm:ss')
    try:
        endtime = time.strptime(endtime_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise ValueError('The "endtime" was not in the required'
                         ' format of YYYY-MM-DD hh:mm:ss')

    # Get a list of nodes
    physicalIDsList = config['default']['sensor_ids'].split()

    timeIntervalHours = config['default']['time_interval_hours']
    predictSpacingDays = config['default']['predict_spacing_days']

    sensorNum = int(config['default']['sensor_number']) 

    bounding_box = config['default']['bounding_box'].split()
 

    # Set start and end time
    starttimeEpoch = calendar.timegm(starttime)
    endtimeEpoch = calendar.timegm(endtime)
    
    timeInterval = 3600*float(timeIntervalHours)       # Average over 'timeInterval'
    predictSpacing = 3600*24*float(predictSpacingDays) # Produce predictions with a 'predictSpacing'
    csv_extractor = soilscape_db_extractor.SoilSCAPECreateCSVfromDB(inSQLite,
                                                                    outSensorNum=sensorNum,
                                                                    debugMode=debugMode)
    
    outStatsFile = os.path.join(outputStatsDIR, 'scaling_function_stats.csv')
    outStatsHandler = open(outStatsFile,'w')
    outStats = csv.writer(outStatsHandler)
    
    outVarImportanceFile = os.path.join(outputStatsDIR, 'scaling_function_var_importance.csv')
    outVarImportanceHandler = open(outVarImportanceFile,'w')
    outVarImportance = csv.writer(outVarImportanceHandler)
    outVarImportancHeader = False

    # Get a list of data layers - to check if using AirMOSS
    data_layers_list = []
    for section in config.sections():
        if section.startswith('layer'):
            data_layers_list.append(upscaling_common.DataLayer(config[section]))

    # Get a list of bandnames
    band_names = [layer.layer_name for layer in data_layers_list]

    # If there is a band called 'airmoss_hh' using AirMOSS
    # if there isn't aren't
    useAirMOSS = 'airmoss_hh' in band_names
    
    # Write header
    outStats.writerow(['Date','nSamples','avgSM_train','stdSM_train','avgSM_predict',
                       'stdSM_predict','RMSE','Bias','RSq','AirMOSSDate'])
    
    while starttimeEpoch < endtimeEpoch:
        endIntervalTimeEpoch = starttimeEpoch + timeInterval
    
        startTS = time.gmtime(starttimeEpoch)
        endTS = time.gmtime(endIntervalTimeEpoch)
    
        # Create temp DIR
        tempDIR = tempfile.mkdtemp(prefix='soilscape_upscaling')
        dateStr = time.strftime('%Y%m%d',startTS)
        outBaseName = dateStr
        
        # Extract CSV from dB
        sensorDataCSV = os.path.join(tempDIR, "{}_sensor_data.csv".format(outBaseName))

        nOutRecords = csv_extractor.createCSVFromDB(physicalIDsList, sensorDataCSV,
                                                    py2SQLiteTime(startTS),
                                                    py2SQLiteTime(endTS))
        if nOutRecords > 10:
            try:
                print("***** {} *****".format(dateStr))

                data_layers_list = []
                for section in config.sections():
                    if section.startswith('layer'):
                        data_layers_list.append(upscaling_common.DataLayer(config[section]))
                
                data_layers_list.append(upscaling_common.DataLayer(config['mask']))
                
                # Create band stack 
                data_stack = stack_bands.make_stack(data_layers_list, tempDIR,
                                                    startTS, bounding_box=bounding_box)

                airmossDateStr = "NA"
                for layer in data_layers_list:
                    if layer.layer_name == 'airmoss_hh':
                        airmossDateStr = time.strftime('%Y%m%d', layer.layer_date)

                # Extract pixel vals
                statscsv = os.path.join(outputCSVDIR, outBaseName + '_sensor_data.csv')
                extract_image_stats.extract_layer_stats_csv(sensorDataCSV,
                                                            statscsv,
                                                            data_layers_list, data_stack)
                # Run Random Forests
                outSMimage = os.path.join(outputImageDIR, outBaseName + '_predict_sm.kea')
                outSMColimage = os.path.join(outputImageDIR, outBaseName + '_predict_sm_col.tif')
    
                rfPar = rf_upscaling.run_random_forests(statscsv, data_stack,
                                                        outSMimage, data_layers_list)
        
                # Write out stats
                outRow = [outBaseName,
                          rfPar['nSamples'],
                          rfPar['averageSMTrain'],
                          rfPar['sdSMTrain'],
                          rfPar['averageSMPredict'],
                          rfPar['sdSMPredict'],
                          rfPar['RMSE'],
                          rfPar['Bias'],
                          rfPar['RSq'],
                          airmossDateStr]
                outStats.writerow(outRow)
    
                # Write header for first record
                if not outVarImportancHeader:
                    outVarImportance.writerow(rfPar['varNames'])
                    outVarImportancHeader = True
    
                outVarImportance.writerow(rfPar['varImportance'])
    
                if createColImage:
                    upscaling_utilities.colour_sm_image(outSMimage, outSMColimage,
                                                        max_value=MAX_SM_COL)

            except Exception as err:
                if debugMode:
                    shutil.rmtree(tempDIR)
                    raise
                else:
                    print(err)

        # Remove temp files
        shutil.rmtree(tempDIR)

        # Add spacing to start time.
        starttimeEpoch += predictSpacing

    # Close files
    outStatsHandler.close()

if __name__ == '__main__':

    # Get input parameters
    parser = argparse.ArgumentParser(description="Run SoilSCAPE Scaling function over "
                                                 "a time series of data.")
    parser.add_argument("configfile", 
                        type=str,
                        nargs=1,
                        help="Config file")
    parser.add_argument("--debug", action='store_true',
                        help="Run in debug mode (more error messages; default=False).",
                        default=False, required=False)

    args = parser.parse_args() 

    run_scaling(args.configfile, debugMode=args.debug)


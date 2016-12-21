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
import os.path
import sys
import tempfile
import time
import shutil
import numpy
from numpy import random
from pandas.io.parsers import read_csv

from soilscape_upscaling import upscaling_common
from soilscape_upscaling import stack_bands_bb as stack_bands
from soilscape_upscaling import extract_image_stats
from soilscape_upscaling import rf_upscaling
from soilscape_upscaling import upscaling_utilities
#from soilscape_upscaling.data_extractors import soilscape_db_extractor
from soilscape_upscaling.data_extractors import txson_extractor

MAX_SM_COL = 0.4

def py2SQLiteTime(inTimePy):
    """ Converts Python time structure to string in the form:
        YYYY-MM-DD hh:mm:ss
    """
    return time.strftime('%Y-%m-%d %H:%M:%S',inTimePy)

def run_scaling(outfolder, config_file, debugMode=False):   

    """
    Run scaling function for a range of dates
    
    Known issues:

    * Doesn't have checks for most items in the config file so
    will just raise an exception if they are not there.
    
    """
    config = configparser.ConfigParser()
    config.read(config_file)

    createColImage = True

    outputsdir = '/media/Data/SoilSCAPE/Scaling/Outputs/'
    out_dir = outputsdir+outfolder
    outputStatsDIR = out_dir+'/Stats'
    outputCSVDIR = out_dir+'/CSV'
    outputImageDIR = out_dir+'/Images'
    outputPlotsDIR = out_dir+'/Plots'

    if os.path.isdir(out_dir):
        print('Output directory {0} already exists'.format(out_dir))
    else:
        os.mkdir(out_dir)
        os.mkdir(outputStatsDIR)
        os.mkdir(outputCSVDIR)
        os.mkdir(outputImageDIR)
        os.mkdir(outputPlotsDIR)

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

    timeIntervalHours = config['default']['time_interval_hours']
    predictSpacingDays = config['default']['predict_spacing_days']

    # List of TxSON site IDs:
    siteIDsList = config['default']['site_ids'].split()
    # Number of nodes to use in Random Forests upscaling (others will be used for validation):
    numnodes = int(config['default']['num_nodes'])
    print('numnodes: ',numnodes)

    nodeIDsList = []
    validIDsList = siteIDsList.copy()

    while len(nodeIDsList) < numnodes:
        node = random.choice(siteIDsList)
        if (node not in nodeIDsList):
            nodeIDsList.append(node)
            validIDsList.remove(node)     

    print('len_nodelist: {0}, len_validlist: {1}'.format(len(nodeIDsList),len(validIDsList)))
 
    # Which sensor in the vertical stack of sensors at each site (e.g., sensor 1 is at 5 cm depth):
    sensorNum = int(config['default']['sensor_number']) 

    csv_extractor = txson_extractor.SoilSCAPECreateCSVfromTxSON(nodeIDsList, outSensorNum=sensorNum,
                                                                    debugMode=debugMode)
    valid_extractor = txson_extractor.SoilSCAPECreateCSVfromTxSON(validIDsList, outSensorNum=sensorNum,
                                                                    debugMode=debugMode)

    # Geographic region to be included in the data layer stack:
    bounding_box = config['default']['bounding_box'].split()

    # Resolution defines the pixel size:
    upscaling_res = config['default']['upscaling_res']

    # Dynamic layer resampling method:
    dyn_resampling = config['default']['dyn_resampling']
 
    # Set start and end time
    starttimeEpoch = calendar.timegm(starttime)
    endtimeEpoch = calendar.timegm(endtime)

    timeInterval = 3600*float(timeIntervalHours)       # Average over 'timeInterval'
    predictSpacing = 3600*24*float(predictSpacingDays) # Produce predictions with a 'predictSpacing'

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
    useAirMOSS = 'airmoss_hh' in band_names
    
    # Write header
    outStats.writerow(['Date','nSamples','avgSM_train','stdSM_train','avgSM_predict',
                       'stdSM_predict','RMSE','Bias','RSq','avgSM_valid','stdSM_valid','AirMOSSDate'])
    
    while starttimeEpoch < endtimeEpoch:
        endIntervalTimeEpoch = starttimeEpoch + timeInterval
    
        startTS = time.gmtime(starttimeEpoch)
        endTS = time.gmtime(endIntervalTimeEpoch)
    
        # Create temp DIR
        tempDIR = tempfile.mkdtemp()
        dateStr = time.strftime('%Y%m%d',startTS)
        print('date: ',dateStr)
        outBaseName = dateStr
        
        # Extract CSV from dB
        nodeDataCSV = os.path.join(tempDIR, "{}_node_data.csv".format(outBaseName))

        nOutRecords = csv_extractor.createCSVFromTxSON(nodeDataCSV,startTS,endTS)
        print('noutrec: ',nOutRecords)
        if nOutRecords >= 10:
            try:
                print("***** {} *****".format(dateStr))

                data_layers_list = []
                for section in config.sections():
                    if section.startswith('layer'):
                        data_layers_list.append(upscaling_common.DataLayer(config[section]))
                
                data_layers_list.append(upscaling_common.DataLayer(config['mask']))
                
                # Create band stack 
                data_stack = stack_bands.make_stack(data_layers_list, tempDIR,
                                                    startTS, bounding_box=bounding_box, upscaling_res=upscaling_res, dyn_resampling=dyn_resampling)

                airmossDateStr = "NA"
                for layer in data_layers_list:
                    if layer.layer_name == 'airmoss_hh':
                        airmossDateStr = time.strftime('%Y%m%d', layer.layer_date)

                # Extract pixel vals
                statscsv = os.path.join(outputCSVDIR, outBaseName + '_sensor_data.csv')
                extract_image_stats.extract_layer_stats_csv(nodeDataCSV,
                                                            statscsv,
                                                            data_layers_list, data_stack)
                # Run Random Forests
                outSMimage = os.path.join(outputImageDIR, outBaseName + '_predict_sm.kea')
                outSMColimage = os.path.join(outputImageDIR, outBaseName + '_predict_sm_col.tif')
    
                rfPar = rf_upscaling.run_random_forests(statscsv, data_stack, outSMimage, data_layers_list)

                validDataCSV = os.path.join(outputStatsDIR, "{}_valid_data.csv".format(outBaseName))
                nValidRecords = valid_extractor.createCSVFromTxSON(validDataCSV,startTS,endTS)
                print('nvalidrec: ',nValidRecords)

                validdata = read_csv(validDataCSV)
                validSMs = validdata.sensorData
                if (len(validSMs) == 0):
                    raise Exception('No valid training data found')
                avgSMvalid = numpy.nanmean(validSMs)
                stdSMvalid = numpy.nanstd(validSMs)
        
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
                          avgSMvalid,
                          stdSMvalid,
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

    parser.add_argument("outfolder", 
                        type=str,
                        help="Output folder")
    parser.add_argument("configfile", 
                        type=str,
                        nargs=1,
                        help="Config file")
    parser.add_argument("--debug", action='store_true',
                        help="Run in debug mode (more error messages; default=False).",
                        default=False, required=False)

    args = parser.parse_args() 

    run_scaling(args.outfolder, args.configfile, debugMode=args.debug)


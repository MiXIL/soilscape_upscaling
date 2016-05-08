#!/usr/bin/env python
"""
SoilSCAPE Random Forests upscaling code.

Dan Clewley & Jane Whitcomb

Functions for training Random Forests and applying
to an image.

"""

import pandas
import numpy
from sklearn.ensemble import RandomForestRegressor
from rios import applier
from rios import cuiprogress

def array2table(in_array):
    """
    Takes multi-band image (represented as a 3-dimensional
    array and flattens to a table with bands as separate columns

    To revert use::

        out_table.reshape((num_bands,num_lines, nPixels))

    """
    num_bands = in_array.shape[0]
    num_lines = in_array.shape[1]
    num_pixels = in_array.shape[2]

    # Set up output table
    out_table = numpy.zeros((num_lines*num_pixels, num_bands))

    for j in range(num_lines):
        for i in range(num_pixels):
            out_table[(j*num_pixels) + i] = in_array[:, j, i]

    return out_table

def _rios_apply_rf_image(info, inputs, outputs, otherargs):
    """
    Applies Random Forests to an image (called from RIOS applier)
    """

    # Flatten array to table
    test_data = array2table(inputs.inimage[0:, ...])

    predict_sm = otherargs.rf.predict(test_data[:, :-1])

    # Mask out no data values for each band.
    # last band is mask
    for i, nodata_val in enumerate(otherargs.nodata_vals_list):
        if nodata_val is not None:
            predict_sm = numpy.where(test_data[:, i] == nodata_val,
                                     0, predict_sm)

    # Reshape
    out_predict_sm = predict_sm.reshape((1, inputs.inimage.shape[1], inputs.inimage.shape[2]))

    out_predict_sm = out_predict_sm.astype(numpy.float32)

    # Save back to image
    outputs.outimage = out_predict_sm

    # Save out predicted SM values
    predict_sm = predict_sm.compress(predict_sm != 0) # Remove zero values
    if otherargs.predict_sm is None:
        otherargs.predict_sm = predict_sm
    else:
        otherargs.predict_sm = numpy.append(otherargs.predict_sm, predict_sm)

def run_random_forests(in_train_csv, in_data_stack, out_image, data_layers_list, train_data_col=3):
    """
    Train random forests using a text file and apply to an image.
    
    Requires:
    
    * in_train_csv - CSV containing extracted values for each band
    * in_data_stack - stack of all layers
    * data_layers_list - list of DataLayers objects
    * train_data_col - colum containing training data (default = 3)

    Returns dictionary containing parameters from Random Forests and average
    soil moisture.
    """

    out_parameters_dict = {}

    # Import Data
    data = pandas.read_csv(in_train_csv)

    # Get list of band names
    band_names = [layer.layer_name for layer in data_layers_list]

    # Use all the band names except the last one (mask)
    var_names = band_names[:-1]

    # Last column is training data
    var_names.append(data.columns[train_data_col])

    # Set up array to pass to sk-learn 
    X_train = []

    for var in var_names:
        X_train.append(data[var])

    # Convert to NumPy array
    X_train = numpy.array(X_train)
    X_train = X_train.transpose()
    
    # Remove non-finite values
    X_train = X_train[numpy.isfinite(X_train).all(axis=1)]

    # Remove areas with no training data
    X_train = X_train[X_train[:, -1] != 0]
    
    # Split into variables (X) and class (y)
    y_train = X_train[:, -1]
    X_train = X_train[:,0:-1]

    if y_train.shape[0] == 0:
        raise Exception('No valid training data found')

    # Train Random Forest
    rf = RandomForestRegressor(n_estimators=300, max_features=3, oob_score=True,
                               verbose=0, n_jobs=4, random_state=17)

    # Fit RF
    rf.fit(X_train, y_train)

    r_sqr = rf.score(X_train, y_train)
    rmse = numpy.sqrt(((rf.oob_prediction_ - y_train)**2).mean())
    bias = (rf.oob_prediction_ - y_train).mean()

    # Save random forest variables
    num_samples = y_train.shape[0]
    var_importance = rf.feature_importances_
    average_sm_train = y_train.mean()
    sd_sm_train = y_train.std()

    # Apply to image
    infiles = applier.FilenameAssociations()
    infiles.inimage = in_data_stack
        
    outfiles = applier.FilenameAssociations()
    outfiles.outimage = out_image
    
    otherargs = applier.OtherInputs()
    otherargs.rf = rf
    otherargs.predict_sm = None # Array to store output SM
    # Pass in list of no data values for each layer
    otherargs.nodata_vals_list = [layer.layer_nodata for layer in data_layers_list]
    controls = applier.ApplierControls()
    controls.setOutputDriverName('KEA')
    controls.progress = cuiprogress.CUIProgressBar()
    applier.apply(_rios_apply_rf_image, infiles, outfiles,
                  otherargs, controls=controls)
    
    average_sm_predict = otherargs.predict_sm.mean()
    sd_sm_predict = otherargs.predict_sm.std()

    # Save parameters to output dictionary
    out_parameters_dict['varNames'] = var_names[:-1]
    out_parameters_dict['averageSMTrain'] = average_sm_train
    out_parameters_dict['sdSMTrain'] = sd_sm_train

    out_parameters_dict['nSamples'] = num_samples
    out_parameters_dict['varImportance'] = var_importance
    out_parameters_dict['RMSE'] = rmse
    out_parameters_dict['Bias'] = bias
    out_parameters_dict['RSq'] = r_sqr
    
    out_parameters_dict['averageSMPredict'] = average_sm_predict
    out_parameters_dict['sdSMPredict'] = sd_sm_predict

    return out_parameters_dict


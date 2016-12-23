"""
SoilSCAPE Random Forests upscaling code.

Dan Clewley & Jane Whitcomb

Common functions and constants.

"""

import time
import os

#: Proj4 string for EASE-2 projection
UPSCALING_PROJ = '+proj=cea +lat_0=0 +lon_0=0 +lat_ts=30 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m'

#: Resolution to use for upscaling
UPSCALING_RES = 100

#: GDAL format to use
UPSCALING_GDAL_FORMAT = "KEA"

# go through all variables and check if they should be overwritten
# by an environmental variable of the same name.
for env_var in dir():
    # Only check for all upper case variable names.
    if env_var.upper() == env_var:
        env_var_value = None
        # See if an environmental variable has been set with the same
        # name
        try:
            env_var_value = os.environ[env_var]
        except KeyError:
            pass
        # If environmental variable has been set overwrite default
        # value
        if env_var_value is not None:
            locals()[env_var] = env_var_value

class DataLayer (object):
    """
    Class to store information for each data layer.

    Reads from dictionary - provided by section in config file

    Has the following attributes.

    * layer_type - type of layer (static, dynamic or mask)
    * layer_name - name of layer
    * layer_path - path to layer
    * layer_dir - directory containing layers (for dynamic layers)
    * layer_nodata - no data value
    * layer_date - date for layer
    """
    def __init__(self, layer_dict):

        # Get name of layer - required
        try:
            self.layer_name = layer_dict['name']
        except KeyError:
            raise KeyError('Must provide name')
        # Check if static (default), dynamic or mask
        try:
            self.layer_type = layer_dict['type']
        except KeyError:
            self.layer_type = 'static'
        # Check mask layer is called 'mask'
        if self.layer_type == 'mask' and self.layer_name != 'mask':
            raise Exception('Mask layer must be named "mask"')

         # Get path to layer - required for static layers
        try:
            self.layer_path = layer_dict['path']
        except KeyError:
            if self.layer_type == 'static':
                raise KeyError('Must provide path for static layers')
            else:
                self.layer_path = None
        # Get directory to search for dynamic layers
        try:
            self.layer_dir = layer_dict['dir']
        except KeyError:
            if self.layer_type == 'dynamic' and self.layer_path is None:
                raise KeyError('Must provide dir for dynamic layers if no path is provided')
            else:
                self.layer_dir = None
       # Get nodata value
        try:
            self.layer_nodata = float(layer_dict['nodata'])
        except KeyError:
            self.layer_nodata = None
        except ValueError:
            raise ValueError('Expected float for nodata value '
                             ', got {}'.format(layer_dict['nodata']))
        # Check if we want to use the layer
        try:
            self.use_layer = layer_dict['uselayer']
        except KeyError:
            self.use_layer = True
        # Get date for layer
        try:
            date_str = layer_dict['date']
            try:
                self.layer_date = time.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date was provided for {0} but not in required'
                                 ' format of YYYY-MM-DD'.format(self.layer_name))
        except KeyError:
            self.layer_date = None
        # Check resampling method to use (only for dynamic layers)
        # If not specified will use default for layer type
        try:
            self.resample_method = layer_dict['resample_method']
            if self.layer_type != 'dynamic':
                raise ValueError('Resample method can not be specified for'
                                 ' static layers')
        except KeyError:
            self.resample_method = None


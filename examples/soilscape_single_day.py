#!/bin/env python
"""
Example script to demonstrate upscaling
"""
import configparser
import time
import os
import sys
sys.path.append(os.path.abspath('../'))
from soilscape_upscaling import upscaling_common
from soilscape_upscaling import stack_bands
from soilscape_upscaling import extract_image_stats
from soilscape_upscaling import rf_upscaling

config = configparser.ConfigParser()
config.read('soilscape_config.cfg')

out_dir = config['default']['outdir']
bounding_box = config['default']['bounding_box'].split()
extracted_stats = os.path.join(out_dir, 'sensor_layer_data.csv')
upscaled_image = os.path.join(out_dir, 'upscaled_sm_image.kea')

# 1. Populate list of layers
data_layers_list = []
for section in config.sections():
    if section.startswith('layer'):
        data_layers_list.append(upscaling_common.DataLayer(config[section]))

data_layers_list.append(upscaling_common.DataLayer(config['mask']))

sm_date_ts = time.strptime('2015-07-22', '%Y-%m-%d')

# 2. Create stack
data_stack = stack_bands.make_stack(data_layers_list, out_dir,
                                    sm_date_ts, bounding_box=bounding_box)

# 3. Extract stats
extract_image_stats.extract_layer_stats_csv('soilscape_sensor_data.csv', extracted_stats,
                                        data_layers_list, data_stack)

# 4. Run Random Forests
upscaling_out_dict = rf_upscaling.run_random_forests(extracted_stats, data_stack,
                                                     upscaled_image, data_layers_list)

print('Average SM train: {:.3f}'.format(upscaling_out_dict['averageSMTrain']))
print('Average SM predict: {:.3f}'.format(upscaling_out_dict['averageSMPredict']))

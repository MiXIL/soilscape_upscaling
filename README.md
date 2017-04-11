# SoilSCAPE Upscaling Code #

Code for upscaling soil moisture with Random Forests regression. Implements the method described in the following paper:

Clewley, D., Whitcomb, J., Akbar, R., Silva, Berg, A., Adams, J.R., Caldwell, T., Entekhabi, D., and Moghaddam, M. (2017).  A method for up-scaling _in situ_ soil moisture measurements to satellite footprint scale using random forests. IEEE Journal of Selected Topics in Applied Earth Observation and Remote Sensing. http://doi.org/10.1109/JSTARS.2017.2690220

Developed as part of the SoilSCAPE project and supported by a grant from the National Aeronautics and Space Administration, Earth Science Technology Office, Advanced Information Systems Technologies program.

## Installation ##

### Pre-requisites ###

Requires the following libraries.

* NumPy
* pandas
* scikit-learn
* GDAL
* RIOS

The recommended way of installing these is using miniconda (https://conda.io/miniconda.html). Once this has been set up the packages can be installed using:

```
conda create -n upscaling -c conda-forge numpy pandas scikit-learn gdal rios
. activate upscaling
```

To colour output images currently requires the RSGISLib XML interface (available in version < 3.2).

### Upscaling scripts ###

Download the scripts and install (within the `upscaling` environment if you used conda) using:

```
python setup.py install
```

Test everything has been installed correctly using the following command:
```
python -c "import soilscape_upscaling.rf_upscaling; print('Installed OK')"
```

## Usage ##

### 1. _in situ_ measurements ###

A set of locations for _in situ_ stations with measurements for each is required. In the paper the stations measure soil moisture but the method should apply to other measurements providing appropriate data layers are used. The measurements need to be in the form of a CSV file containing the following:
```
stationID, Latitude, Longitude, measurement
```
See [soilscape_sensor_data.csv](examples/soilscape_sensor_data.csv) for an example of the correct format.


### 2. Data layers ###

A number of data layers in raster (gridded) format with associated geographical information.
Each must be a single band image which can be read using GDAL. If they open in a GIS program such as QGIS or ArcMap and are in the correct location they should be OK to use.

Of particular importance is that the static data layers are in the same projection and gridded to the same pixel size. To achieve this the GDAL utilities are particularly useful, especially [gdalwarp](http://www.gdal.org/gdalwarp.html).

### Running the code ###

The code is designed as a Python library with most parameters passed in via config file.
For an example script see [soilscape_single_day.py](examples/soilscape_single_day.py) and [soilscape_config.cfg](examples/soilscape_config.cfg) for the corresponding config file.

The config file contains a heading for default information, such as output directory and
bounding box:

```
[default]

outdir = /home/danclewley/Documents/Temp/upscaling_test/
bounding_box = -11693000 4520000 -11640000 4577000 
```

Then for each data layer there is a separate section containing the following:
```
[layer1]
name = nlcd
type = static
nodata = 11
path = /media/Data/SoilSCAPE/Scaling/DataLayers/NLCD/nlcd_2011_landcover_2011_edition_2014_03_31_tonzi_ease2_100m.kea
uselayer = true

...

[layer7]
name = prism_ppt
type = dynamic
dir = /media/Data/SoilSCAPE/Scaling/DataLayers/PRISM/ppt
uselayer = true

```
Where:

* **name** - Name of layer
* **type** - static or dynamic. Static layers are the same for all dates. Dynamic layers vary depending on the date. Currently the code only supports a limited number of dynamic layers required for the paper. It is recommended to start with you use only static and have a separate config for each date
* **nodata** - No data value or value to ignore. For example in a classification is certain classes should be ignored (e.g., water) the nodata value can be used.
* **path** - Path to data static data layer
* **uselayer** - If the layer should be included or not
* **dir** - Directory for dynamic layers

## Sites ##

To run for a time series for different sites site-specific scripts have been developed. These provide examples of applying the upscaling to more complicated use cases.
For each site there is the site specific script and config file for each of the scenarios in the paper.

### SoilSCAPE - Tonzi ##

Script and config files for running upscaling for Tonzi Ranch, California.

This version was been designed to run on the SoilSCAPE Data Server (http://soilscape.usc.edu) therefore data are extracted from an SQLite or MySQL version of the SoilSCAPE database.

Versions of the SoilSCAPE data in netCDF format are available to download from https://doi.org/10.3334/ORNLDAAC/1339

### SMAPVEX12 ###

Script and config files for running for the SMAP Validation Experiment 2012 site in Winnipeg, Manitoba, Canada.
The sensor data used are available in `data/smapvex_12_jwhitcomb_subset_with_ll.csv`

### TxSON ###

Script and config files for The Texas Soil Moisture Observation Network (TxSON), Texas.

## Licence ##

This code is made available under the GPLv3 license see [LICENSE](LICENSE) for more details.

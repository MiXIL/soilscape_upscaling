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

The code is designed as a Python library with most parameters passed in via config file.
For an example of applying the method to a single date see [soilscape_single_day.py](examples/soilscape_single_day.py)

Of particular importance is that the static data layers are in the same projection and gridded to the same pixel size. To achieve this the GDAL utilities are particularly useful, especially [gdalwarp](http://www.gdal.org/gdalwarp.html)

## Sites ##

To run for a time series for different sites site-specific scripts have been developed. These provide examples of applying the upscaling to more complicated use cases.
For each site there is the site specific script and config file for each of the scenarios in the paper.

### SoilSCAPE - Tonzi ##

Script and config files for running upscaling for Tonzi Ranch, California.

This version was been designed to run on the SoilSCAPE Data Server (http://soilscape.usc.edu) therefore data are extracted from an SQLite or MySQL version of the SoilSCAPE database.

Versions of the SoilSCAPE data in netCDF format are available to download from https://doi.org/10.3334/ORNLDAAC/1339

### SMAPVEX12 ###

Script and config files for running for the SMAP Validation Experiment 2012 site in Winnipeg, Manitoba, Canada.

### TxSON ###

Script and config files for The Texas Soil Moisture Observation Network (TxSON), Texas.

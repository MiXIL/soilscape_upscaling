# SoilSCAPE Upscaling Code #

Code for upscaling soil moisture using Random Forests.

Developed as part of the SoilSCAPE project.

## Installation ##

Install using:
```
python setup.py install
```

Requires:

* NumPy
* pandas
* scikit-learn
* GDAL

To colour output images currently requires RSGISLib.

## Usage ##

The code is designed as a general purpose library with most parametes passed in via config file.
For an example of applying the method to a single date see [soilscape_single_day.py](examples/soilscape_single_day.py)

## Sites ##

To run for a time series for different sites site-specific scripts have been developed. These provide examples of applying the upscaling to more complicated use cases.

### SoilSCAPE - Tonzi ##

Script and config file for running 

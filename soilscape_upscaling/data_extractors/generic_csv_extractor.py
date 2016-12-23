#!/usr/bin/env python

"""
Classes to extract data from CSV files.

Dan Clewley & Jane Whitcomb

"""

import csv
import time

class SoilSCAPECreateCSVGenericStationRowsCSV(object):
    """
    Class to extract data from a CSV file with a separate row for each station
    and column for each date in the format:

    SensorID,Latitude,Longitude,Date1,Date2,...

    Where Date1 etc., are of the format YYYY-MM-DD.

    """
    def __init__(self, station_sm_file, delimiter=',', debug_mode=False):
        self.debug_mode = debug_mode
        self.station_sm_file = station_sm_file
        self.delimiter = delimiter
        self.dates_ts = None

    def get_available_dates(self):
        """
        Get a list of all available dates from file

        Returns as list of Python time structure objects
        """
        station_sm = open(self.station_sm_file, 'r')
        station_sm_header = station_sm.readline()
        station_sm.close()

        # Remove new line
        station_sm_header = station_sm_header.replace('\n','')
        # Split by delimiter
        header_elements = station_sm_header.split(self.delimiter)
        dates = header_elements[3:]
        self.dates_ts = [time.strptime(d, '%Y-%m-%d') for d in dates]

        return self.dates_ts
 
    def get_column_for_date(self, time_ts):
        """
        Get column number of date matching time_ts

        """

        # If dates haven't already been extracted
        # do so here
        if self.dates_ts is None:
            self.get_available_dates()

        dateidx = None

        for i, station_date_ts in enumerate(self.dates_ts):

            # Check if year month and day are the same
            if station_date_ts.tm_year == time_ts.tm_year and \
               station_date_ts.tm_mon == time_ts.tm_mon and \
               station_date_ts.tm_mday == time_ts.tm_mday:
                dateidx = i+3
                break

        return dateidx

    def create_csv_from_input(self, time_ts, output_csv_file, stations_list=None):
        """
        Create a CSV for use in upscaling code from input sensor data.

        siteID, Latitude, Longitude, sensorData

        Where sensor data is extracted for a specified date
        A list of stations may also be passed in if only certain ones are
        to be used.

        """

        out_f = open(output_csv_file, 'w')
        in_f = open(self.station_sm_file, 'r')

        in_sm_csv = csv.reader(in_f)
        out_csv = csv.writer(out_f)


        out_header = ['siteID', 'Latitude', 'Longitude', 'sensorData']
        out_csv.writerow(out_header)

        # Get the column containing soil moisture for the
        # given date.
        dateidx = self.get_column_for_date(time_ts)

        if dateidx is None:
            raise Exception('No date found for date: '
                            '{}'.format(time.strftime('%Y-%m-%d')))

        num_out_records = 0

        # Skip first row (header)
        next(in_sm_csv)

        for sm_line in in_sm_csv:

            station_id = sm_line[0]
            latitude = sm_line[1]
            longitude = sm_line[2]
            sm_data = sm_line[dateidx]

            write_out = False
            
            # If a list of stations has been provided
            # check it is in this list before writing out
            if stations_list is None:
                write_out = True
            else:
                if station_id in stations_list:
                    write_out = True
            if write_out:
                out_line = [station_id, latitude, longitude, sm_data]
                out_csv.writerow(out_line)
                num_out_records += 1

        in_f.close()
        out_f.close()

        return num_out_records


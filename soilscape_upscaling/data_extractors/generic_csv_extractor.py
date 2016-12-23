#!/usr/bin/env python

"""
Classes to extract data from CSV files.

Dan Clewley & Jane Whitcomb

"""

import csv
import os
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

    def get_column_for_date(self, time_ts):
        """
        Get column number of date matching time_ts

        """
        station_sm = open(self.station_sm_file, 'r')
        station_sm_header = station_sm.readline()
        station_sm.close()

        header_elements = station_sm_header.split(self.delimiter)

        dateidx = None

        for i in range(3, len(header_elements)):
            station_date_ts = time.strptime(header_elements[i], '%Y-%m-%d')

            # Check if year month and day are the same
            if station_date_ts.tm_year == time_ts.tm_year and \
               station_date_ts.tm_mon == time_ts.tm_mon and \
               station_date_ts.tm_mday == time_ts.tm_day:
                dateidx = i
                break

        return dateidx

    def write_out_csv(self, time_ts, output_csv_file, stations_list=None):
        """
        Write out a CSV containing:

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


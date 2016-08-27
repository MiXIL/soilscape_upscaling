#!/usr/bin/env python

################################################################
# Python script to create CSV from soil moisture measurements  #
# Dan Clewley (daniel.clewley@gmail.com), 27/08/2012           #
#                                                              #
# Modified 11/11/2013 to use sqlite                            #
################################################################

import csv
import os
import re
import sqlite3
import numpy

# Check for mysql connector, only needed if connecting
# to MySQL database
havePyMySQL = False
try:
    import mysql.connector
    havePyMySQL = True
except ImportError:
    pass

class SoilSCAPECreateCSVfromDB(object):
    """
    SoilSCAPE Data Base extraction class

    Extracts data from SoilSCAPE data base in SQLite or MySQL format.

    Generally SQLite is used for testing MySQL is used when running
    on the data server.

    """
    def __init__(self, sqliteFile=None, outSensorNum=1, debugMode=False):

        self.outSensorNum = outSensorNum
        # Connect to database
        self.useSQLite = False
        if sqliteFile is not None:
            self.sensordb = sqlite3.connect(sqliteFile)
            self.useSQLite=True
        else:
            if not havePyMySQL:
                raise Exception("Could not import mysql.connector - must install or use SQlite database.")
            else:
                # If SQLite file not provided assume
                mySQLPassFileName = os.path.expanduser('~/.mysql_ip_user_pass.txt')
                mySQLPassFile = open(mySQLPassFileName,'r')
                mysqlip = mySQLPassFile.readline().strip()
                mysqluser = mySQLPassFile.readline().strip()
                mysqlpass = mySQLPassFile.readline().strip()
                mysqldb = mySQLPassFile.readline().strip()
                mySQLPassFile.close()

                print('Using MySQL database')
                self.sensordb = mysql.connector.connect(user=mysqluser, password=mysqlpass, host=mysqlip, database=mysqldb)

        self.debugMode = debugMode
        self.calCoeff = self.setInitialCal()

    def setInitialCal(self):

        """ Set intial calibration to Decagon (mineral soil) """

        calCoeff = {}
        calCoeff['type'] = 'linear'
        calCoeff['s1Coeff0'] = -40.1
        calCoeff['s1Coeff1'] = 0.1279569
        calCoeff['s1Coeff2'] = 0
        calCoeff['s1Coeff3'] = 0
        calCoeff['s2Coeff0'] = -40.1
        calCoeff['s2Coeff1'] = 0.1279569
        calCoeff['s2Coeff2'] = 0
        calCoeff['s2Coeff3'] = 0
        calCoeff['s3Coeff0'] = -40.1
        calCoeff['s3Coeff1'] = 0.1279569
        calCoeff['s3Coeff2'] = 0
        calCoeff['s3Coeff3'] = 0
        calCoeff['s4Coeff0'] = -40.1
        calCoeff['s4Coeff1'] = 0.1279569
        calCoeff['s4Coeff2'] = 0
        calCoeff['s4Coeff3'] = 0

        return calCoeff

    def getCalibration(self, physicalID):

        """ Get node spefific calibration from database.
            returns Decagon calibration if not available.
        """

        foundCal = False

        if self.useSQLite:
            cursor = self.sensordb.cursor()
        else:
            cursor = self.sensordb.cursor(buffered=True)

        # Select calibration coefficients from database
        sqlCommand = '''SELECT s1CalType, s1Coeff0, s1Coeff1,s1Coeff2,s1Coeff3,
                        s2Coeff0, s2Coeff1, s2Coeff2, s2Coeff3,
                        s3Coeff0, s3Coeff1, s3Coeff2, s3Coeff3,
                        s4Coeff0, s4Coeff1, s4Coeff2, s4Coeff3
                         FROM Calibration WHERE PhysicalID = {} ORDER BY Version DESC LIMIT 1;'''.format(physicalID)
        cursor.execute(sqlCommand)

        calData = cursor.fetchall()

        if len(calData) > 0:
            self.calCoeff['type'] = calData[0][0]
            self.calCoeff['s1Coeff0'] = calData[0][1]
            self.calCoeff['s1Coeff1'] = calData[0][2]
            self.calCoeff['s1Coeff2'] = calData[0][3]
            self.calCoeff['s1Coeff3'] = calData[0][4]
            self.calCoeff['s2Coeff0'] = calData[0][5]
            self.calCoeff['s2Coeff1'] = calData[0][6]
            self.calCoeff['s2Coeff2'] = calData[0][7]
            self.calCoeff['s2Coeff3'] = calData[0][8]
            self.calCoeff['s3Coeff0'] = calData[0][9]
            self.calCoeff['s3Coeff1'] = calData[0][10]
            self.calCoeff['s3Coeff2'] = calData[0][11]
            self.calCoeff['s3Coeff3'] = calData[0][12]
            self.calCoeff['s4Coeff0'] = calData[0][13]
            self.calCoeff['s4Coeff1'] = calData[0][14]
            self.calCoeff['s4Coeff2'] = calData[0][15]
            self.calCoeff['s4Coeff3'] = calData[0][16]

            foundCal = True

        return foundCal

    def calData(self, raw1=None, raw2=None, raw3=None, raw4=None):

        """ Calibrate raw data using stored coefficients """

        cal1=None
        cal2=None
        cal3=None
        cal4=None

        # Linear equation
        if self.calCoeff['type'] == 'linear':

            if raw1 is not None:
                cal1 = self.calCoeff['s1Coeff0'] + self.calCoeff['s1Coeff1']*raw1
            if raw2 is not None:
                cal2 = self.calCoeff['s2Coeff0'] + self.calCoeff['s2Coeff1']*raw2
            if raw3 is not None:
                cal3 = self.calCoeff['s3Coeff0'] + self.calCoeff['s3Coeff1']*raw3
            if raw4 is not None:
                cal4 = self.calCoeff['s4Coeff0'] + self.calCoeff['s4Coeff1']*raw4

        # Split linear equation
        elif self.calCoeff['type'].find('split_') > -1:

            rawSplit = int(self.calCoeff['type'].split('_')[1])

            if raw1 is not None:
                cal1 = numpy.where(raw1 < rawSplit,
                                   self.calCoeff['s1Coeff0'] + self.calCoeff['s1Coeff1'] * raw1,
                                   self.calCoeff['s1Coeff2'] + self.calCoeff['s1Coeff3'] * raw1)
            if raw2 is not None:
                cal2 = numpy.where(raw2 < rawSplit,
                                   self.calCoeff['s2Coeff0'] + self.calCoeff['s2Coeff1'] * raw2,
                                   self.calCoeff['s2Coeff2'] + self.calCoeff['s2Coeff3'] * raw2)
            if raw3 is not None:
                cal3 = numpy.where(raw3 < rawSplit,
                                   self.calCoeff['s3Coeff0'] + self.calCoeff['s3Coeff1'] * raw3,
                                   self.calCoeff['s3Coeff2'] + self.calCoeff['s3Coeff3'] * raw3)
            if raw4 is not None:
                cal4 = numpy.where(raw4 < rawSplit,
                                   self.calCoeff['s4Coeff0'] + self.calCoeff['s4Coeff1'] * raw4,
                                   self.calCoeff['s4Coeff2'] + self.calCoeff['s4Coeff3'] * raw4)

        # Second order polynomial
        elif self.calCoeff['type'] == 'poly2':

            if raw1 is not None:
                cal1 = self.calCoeff['s1Coeff0'] + self.calCoeff['s1Coeff1']*raw1 + self.calCoeff['s1Coeff2']*(raw1**2)
            if raw2 is not None:
                cal2 = self.calCoeff['s2Coeff0'] + self.calCoeff['s2Coeff1']*raw2 + self.calCoeff['s2Coeff2']*(raw2**2)
            if raw3 is not None:
                cal3 = self.calCoeff['s3Coeff0'] + self.calCoeff['s3Coeff1']*raw3 + self.calCoeff['s3Coeff2']*(raw3**2)
            if raw4 is not None:
                cal4 = self.calCoeff['s4Coeff0'] + self.calCoeff['s4Coeff1']*raw4 + self.calCoeff['s4Coeff2']*(raw4**2)

        return cal1, cal2, cal3, cal4

    def getOutLine(self, physicalID, startTime, endTime):
        """
        Read and average data from a range of dates and return array,
        to be written out as line to CSV file

        Measurements are extracted for all sensors but only the required
        sensor is returned.
        """

        if self.useSQLite:
            cursor = self.sensordb.cursor()
        else:
            cursor = self.sensordb.cursor(buffered=True)

        smData = {}
        if self.useSQLite:
            startTimeDB = startTime
            endTimeDB = endTime
        else:
            startTimeDB = re.sub('-','',startTime)
            startTimeDB = re.sub(':','',startTimeDB)
            startTimeDB = re.sub(' ','',startTimeDB)
            endTimeDB = re.sub('-','',endTime)
            endTimeDB = re.sub(':','',endTimeDB)
            endTimeDB = re.sub(' ','',endTimeDB)

        # Select data from table
        orderStr = "ORDER BY measTStime ASC"
        sqlCommand = '''SELECT * FROM `Measurements` JOIN `MeasurementControl` ON (Measurements.MeasurementID=MeasurementControl.MeasurementID)
JOIN `LogicalLocation` ON (Measurements.LogicalID=LogicalLocation.LogicalID)
JOIN `PhysicalLocation` ON (Measurements.PhysicalID=PhysicalLocation.PhysicalID)
JOIN `MeasurementScheme` ON (Measurements.MeasurementSchemeID=MeasurementScheme.MeasurementSchemeID)
WHERE Measurements.PhysicalID=%s AND badData = 0 AND measTStime > '%s' AND measTStime < '%s' '''%(physicalID, startTimeDB, endTimeDB) + orderStr + ';'

        cursor.execute(sqlCommand)
        outData = cursor.fetchall()

        if len(outData) == 0:
            raise Exception("No data found for Node#{} for selected dates".format(physicalID))

        # Check for Soil moisture sensors.
        if outData[0][40] == 'EC-5' and outData[0][42] == 'EC-5' and outData[0][44] == 'EC-5':
            smData['hasData'] = True
            smData['sensorType'] = 'EC-5'
            smData['sensorNums'] = [1,2,3]
        else:
            raise Exception("The record for Node #{} does not contain data for three soil moisture sensors".format(physicalID))

        # Convert to numpy array
        dataNP = []

        for line in outData:
            dataNP.append(line)

        dataNP = numpy.array(outData)
        # Get position (common for all nodes)
        latitude = dataNP[0][36]
        longitude = dataNP[0][37]

        # Extract only data with no flags (on sensor basis)
        s1NP = dataNP[dataNP[:,19].astype(int) == 0]
        s2NP = dataNP[dataNP[:,20].astype(int) == 0]
        s3NP = dataNP[dataNP[:,21].astype(int) == 0]

        if (s1NP.shape[0] == 1) and (s2NP.shape[0] == 1) and (s3NP.shape[0] == 1):
            raise Exception("No unmasked data found for {}.".format(physicalID))

        s1NP = s1NP[:,5].astype(float)
        s2NP = s2NP[:,6].astype(float)
        s3NP = s3NP[:,7].astype(float)

        # Get site specific calibration coefficients
        self.getCalibration(physicalID)

        # Apply calibration
        allCalib = self.calData(s1NP, s2NP, s3NP)

        s1Calib = allCalib[0]
        s2Calib = allCalib[1]
        s3Calib = allCalib[2]

        s1Calib = s1Calib[s1Calib > 0]
        s2Calib = s2Calib[s2Calib > 0]
        s3Calib = s3Calib[s3Calib > 0]

        s1Calib = s1Calib[s1Calib < 60]
        s2Calib = s2Calib[s2Calib < 60]
        s3Calib = s3Calib[s3Calib < 60]

        # Check is there are any remaining samples before
        # writing calculating mean.
        # Average of an empty array is NaN anyway but this
        # avoids error message.
        if s1Calib.shape[0] > 0:
            s1CalibAvg = numpy.nanmean(s1Calib)
        else:
            s1CalibAvg = numpy.nan

        if s2Calib.shape[0] > 0:
            s2CalibAvg = numpy.nanmean(s2Calib)
        else:
            s2CalibAvg = numpy.nan

        if s3Calib.shape[0] > 0:
            s3CalibAvg = numpy.nanmean(s3Calib)
        else:
            s3CalibAvg = numpy.nan

        # Only write the required sensor out to CSV file
        # Scale to get in m3/m3
        if self.outSensorNum == 1:
            outSensorCal = s1CalibAvg / 100.0
        elif self.outSensorNum == 2:
            outSensorCal = s2CalibAvg / 100.0
        elif self.outSensorNum == 3:
            outSensorCal = s3CalibAvg / 100.0
        else:
            raise Exception("Sensor number not recognised")

        # Only return outline if there are sensor measurements.
        if numpy.isnan(outSensorCal):
            raise Exception("No valid data found for {}.".format(physicalID))

        outLine = [physicalID, latitude, longitude, outSensorCal]

        return outLine

    def createCSVFromDB(self, physicaIDsList, outDataFile, startDateTimeStr, endDateTimeStr):
        outRecords = 0

        outputText = csv.writer(open(outDataFile,'w'))

        outHeader = ['physicalID', 'Latitude', 'Longitude', 'sensorData']
        outputText.writerow(outHeader)

        for physicalID in physicaIDsList:
            try:
                outLine = self.getOutLine(physicalID, startDateTimeStr, endDateTimeStr)
                outputText.writerow(outLine)
                outRecords += 1
            except Exception as err:
                if self.debugMode:
                    print(err)
                else:
                    pass
        return outRecords


#!/usr/bin/env python
"""
Class to extract data from TxSON network
for use in upscaling algorithm

Dan Clewley & Jane Whitcomb

This file is licensed under the GPL v3 Licence. A copy of this
licence is available to download with this file.

"""

import csv
import calendar
import os
import time
import numpy
import pandas

class SoilSCAPECreateCSVfromTxSON(object):
    """
    TxSON extraction class

    Extracts data from TxSON .dat files.

    """
    def __init__(self, siteIDsList, txsondir, outSensorNum=1, debugMode=False):

        self.siteIDsList = siteIDsList
        self.outSensorNum = outSensorNum
        self.debugMode = debugMode

        self.txsondir = txsondir

        #Set up site information:
        sites = pandas.read_csv(os.path.join(self.txsondir, 'sites_noblanks.csv'))
        allsiteIDs = sites.SiteID

        loggerID = {}
        sitelat = {}
        sitelon = {}

        for i in range(len(siteIDsList)):
            siteIDstr = siteIDsList[i]
            siteID = int(siteIDstr)

            foundsite = 0
            for j in range(len(allsiteIDs)):
                if (siteID == allsiteIDs[j]):
                    loggerID[siteIDstr] = sites.logger_ID[j]        
                    sitelat[siteIDstr] = sites.LAT[j]        
                    sitelon[siteIDstr] = sites.LON[j]
                    foundsite = 1
            if (foundsite == 0):
                print('Cant find siteID '+siteIDstr)       

        self.loggerID = loggerID
        self.sitelat = sitelat
        self.sitelon = sitelon        

    def getOutLine(self, siteIDstr, startsecs, endsecs):
        """
        Read and average data from a range of dates and return array,
        to be written out as line to CSV file

        """

        # Get position (common for all sites)
        latitude = self.sitelat[siteIDstr]
        longitude = self.sitelon[siteIDstr]

        # Select data from file
        sitebase = self.loggerID[siteIDstr].replace('-','_')
        sitefile = self.txsondir+sitebase+'.dat'
        
        sitedata = pandas.read_csv(sitefile,sep=',\s+', engine='python')
        if len(sitedata) == 0:
            raise Exception("No data found for Site {} (at all, any sensors) for selected date".format(loggerID[siteIDstr]))  
  
        SMdate = sitedata.Date

        sensorMeas = []
        for i in range(len(SMdate)):
            filedate = SMdate[i]
            fileTS = time.strptime(filedate, "%m/%d/%y %H:%M")   
            filesecs = calendar.timegm(fileTS)
            if ((filesecs >= startsecs) and (filesecs < endsecs)):    
                if self.outSensorNum == 1:         
                    VWCmeas = sitedata.VWC_5[i]
                elif self.outSensorNum == 2:
                    VWCmeas = sitedata.VWC_10[i]
                elif self.outSensorNum == 3:
                    VWCmeas = sitedata.VWC_20[i]
                else:
                    raise Exception("Sensor number not recognised")
                sensorMeas.append(VWCmeas) 

        if (len(sensorMeas) == 0):
            raise Exception("No data found for Site {}, sensor {} for selected date".format(siteIDstr,self.outSensorNum))

        sensorMeas = numpy.array(sensorMeas)
        sensorMeas = sensorMeas[sensorMeas > 0]
        sensorMeas = sensorMeas[sensorMeas < 0.50]
        sensorAvg = numpy.nanmean(sensorMeas)

        if (numpy.isfinite(sensorAvg) == False):
            raise Exception("Non-finite data found for Site {}, sensor {} for selected date".format(siteIDstr,self.outSensorNum))
        outSensorCal = sensorAvg

        outLine = [ siteIDstr, latitude, longitude, outSensorCal]
        return outLine

    def createCSVFromTxSON(self, outDataFile, startTS, endTS):
        outRecords = 0

        startsecs = calendar.timegm(startTS)
        endsecs = calendar.timegm(endTS)

        outputText = csv.writer(open(outDataFile,'w'))

        outHeader = ['siteID', 'Latitude', 'Longitude', 'sensorData']
        outputText.writerow(outHeader)

        for  siteIDstr in self.siteIDsList:
            try:
                outLine = self.getOutLine( siteIDstr, startsecs, endsecs)
                outputText.writerow(outLine)
                outRecords += 1
            except Exception as err:
                if self.debugMode:
                    print(err)
                else:
                    pass
        return(outRecords)


# -*- coding: utf-8 -*-
import re
import csv
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from osgeo import ogr, osr


class crawler():
    def __init__(self):
        pass

    def crawlering(self):
        crawler.link2web()
        # opencsv
        txt = open("dirpath_2.txt", "r")
        filedir = txt.read()
        file = open(filedir, "w", encoding='ANSI')
        fieldnames = ['County', 'ReefName',
                      'GPSLocation', 'Coordinate', 'Date']
        csvCursor = csv.DictWriter(file, fieldnames=fieldnames, delimiter=',')
        csvCursor.writeheader()

        print('--------------------------人工魚礁、保護礁區資訊--------------------------')
        cty_num = 0
        coordinateList = []
        DdotD_coordinateList = []
        # 將表格撈出
        for idx, (rad, nme) in enumerate(zip(soup.find_all(w='259'), soup.find_all(w='220'))):

            nme_num = int(nme['rowspan'])  # 2
            if(cty_num-nme_num < 0):
                cty_num = int(nme.find_previous_sibling()['rowspan'])  # 4
                cty_num = cty_num-nme_num  # 4-2 = 2
                county = nme.find_previous_sibling().text.strip()
            else:
                cty_num = cty_num-nme_num  # 2-2 = 0

            name = nme.text.strip()
            radius = rad.text.strip().replace(',', '')
            date = rad.find_next_sibling().text.strip()
            coordinate = nme.find_next_sibling().text.strip()
            coordinateList.append(nme.find_next_sibling().text.strip())
            coo_ = nme
            for x in range(nme_num-1):
                coo_ = coo_.find_next('tr').find(w='239')
                coordinateList.append(coo_.text.strip())

            # 換算公尺
            geo_shape = 1
            if(radius.find('圓心') > 0):
                geo_shape = 0  # 'multipoint'
            if(radius.find('浬') > 0):
                radius = re.findall(r"\d+\.?\d*", radius)
                radius = float(radius[0])*1852
            elif(radius.find('公尺') > 0):
                radius = re.findall(r"\d+\.?\d*", radius)
                radius = float(radius[0])
            elif(radius.find('浬') == -1 and radius.find('公尺') == -1):
                print('no buffer')
                radius = 0

            # 處理坐標資料
            for idxx, co in enumerate(coordinateList):
                co = co.replace('\r\n ', '')
                co = co.replace('\'\'', '"')
                co = co.replace('”', '"')
                remove_words = 'ＡＢＣＤ、ABCD點:。'
                for word in remove_words:
                    co = co.replace(word, '')
                coordinateList[idxx] = co

            print(str(idx+1)+'.', county, name, date)
            print('radius: %s公尺' % (radius))

            point = ogr.Geometry(ogr.wkbPoint)
            line = ogr.Geometry(ogr.wkbLineString)
            ring = ogr.Geometry(ogr.wkbLinearRing)
            poly = ogr.Geometry(ogr.wkbPolygon)
            multipoint = ogr.Geometry(ogr.wkbMultiPoint)

            for point_ in coordinateList:
                if(point_[0] == 'N'):

                    lat = re.split(',', point_)[0]
                    lat = lat.replace(' ', '°')
                    lat = re.split('°|\'|\"', lat)
                    lati = float(lat[0].replace('N', '').strip())+float(lat[1]) / \
                        60+float(lat[2])/3600
                    lon = re.split(',', point_)[1]
                    lon = re.split('°|\'|\"', lon)
                    long = float(lon[0].replace('E', ''))+float(lon[1]) / \
                        60+float(lon[2])/3600

                else:
                    lati, long = 0, 0

                if(point_ == coordinateList[0]):
                    Firstlat = lati
                    Firstlon = long

                if(len(coordinateList) == 1):
                    point.AddPoint(long, lati)
                elif(geo_shape is not 0 and len(coordinateList) == 2):
                    line.AddPoint(long, lati)
                elif(geo_shape is not 0 and len(coordinateList) > 2):
                    ring.AddPoint(long, lati)
                elif(geo_shape == 0 and len(coordinateList) > 1):
                    point.AddPoint(long, lati)
                    multipoint.AddGeometry(point)

            # Transform to twd97 and Buffer then Transform back to Wgs84
            if county in ['澎湖縣', '澎湖', '金門縣', '金門', '馬祖縣', '馬祖', '連江縣', '連江']:
                if(len(coordinateList) == 1):
                    point.Transform(crawler.SpatialRefTrans(2))
                    StrictArea = point.Buffer(radius)
                elif(geo_shape is not 0 and len(coordinateList) == 2):
                    line.Transform(crawler.SpatialRefTrans(2))
                    StrictArea = line.Buffer(radius)
                elif(geo_shape is not 0 and len(coordinateList) > 2):
                    ring.AddPoint(Firstlon, Firstlat)
                    poly.AddGeometry(ring)
                    poly = poly.ConvexHull()
                    poly.Transform(crawler.SpatialRefTrans(2))
                    StrictArea = poly.Buffer(radius)
                elif(geo_shape == 0 and len(coordinateList) > 1):
                    multipoint.Transform(crawler.SpatialRefTrans(2))
                    StrictArea = multipoint.Buffer(radius)
                StrictArea.Transform(crawler.SpatialRefTrans(4))
            else:
                if(len(coordinateList) == 1):
                    point.Transform(crawler.SpatialRefTrans(1))
                    StrictArea = point.Buffer(radius)
                elif(geo_shape is not 0 and len(coordinateList) == 2):
                    line.Transform(crawler.SpatialRefTrans(1))
                    StrictArea = line.Buffer(radius)
                elif(geo_shape is not 0 and len(coordinateList) > 2):
                    ring.AddPoint(Firstlon, Firstlat)
                    poly.AddGeometry(ring)
                    poly = poly.ConvexHull()
                    poly.Transform(crawler.SpatialRefTrans(1))
                    StrictArea = poly.Buffer(radius)
                elif(geo_shape == 0 and len(coordinateList) > 1):
                    multipoint.Transform(crawler.SpatialRefTrans(1))
                    StrictArea = multipoint.Buffer(radius)
                StrictArea.Transform(crawler.SpatialRefTrans(3))

            outputcoordinateList = ','.join(coordinateList)
            csvCursor.writerow(
                {'County': county, 'ReefName': name, 'GPSLocation': StrictArea, 'Coordinate': outputcoordinateList, 'Date': date})
            coordinateList = []
            print(' ')
            print(' ')

    def link2web(self):
        ua = UserAgent()
        headers = {'User-Agent': ua.random}

        url = 'https://www.fa.gov.tw/cht/ResourceOtherZones/content.aspx?id=1&chk=8e65c2e0-2071-4da9-aad9-6e892409febc&param=pn%3d1'

        # GET request from url and parse via BeautifulSoup
        resp = requests.get(url, headers=headers)
        resp.encoding = 'utf-8'  # encoded with format utf-8 for chinese character
        global soup
        soup = BeautifulSoup(resp.text, 'lxml')

    # 取得坐標資料N,E出現的位置
    def GetIndex(self, NE, xy):
        NE = str(NE)
        xy = str(xy)
        num = xy.count(NE)
        index = [-2, -2, -2, -2, num]

        index[0] = xy.find(NE)
        if(num > 1):
            for i in range(1, num):
                index[i] = xy.find(NE, index[i-1]+1)
        return index
        ####

    def SpatialRefTrans(self, w):
        inSpatialRef = osr.SpatialReference()
        outSpatialRef = osr.SpatialReference()

        if(w == 1):
            # wgs84->twd97_121
            inputEPSG, outputEPSG = 4326, 3826
        elif(w == 2):
            # wgs84->twd97_119
            inputEPSG, outputEPSG = 4326, 3825
        elif(w == 3):
            # twd97_121->wgs84
            inputEPSG, outputEPSG = 3826, 4326
        elif(w == 4):
            # twd97_119->wgs84
            inputEPSG, outputEPSG = 3825, 4326

        inSpatialRef.ImportFromEPSG(inputEPSG)
        outSpatialRef.ImportFromEPSG(outputEPSG)
        coordTransform = osr.CoordinateTransformation(
            inSpatialRef, outSpatialRef)
        return coordTransform


if __name__ == '__main__':
    crawler = crawler()
    crawler.crawlering()
    print('finish')

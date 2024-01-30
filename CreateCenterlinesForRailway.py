# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import optparse
import numpy
from osgeo import gdal, osr, ogr
import os
import json
from urllib.parse import unquote
import shutil
from os.path import exists
import glob
from math import floor, ceil, sqrt, isnan, modf, trunc, sin, cos, tan
import csv
import re
from numpy import arctan2
from numpy import pi

railwayWidth = 1.8

def azimuth(xi, yi, xj, yj):
    ax = xj - xi
    ay = yj - yi
    value = arctan2(float(ax), ay)
    if value < 0:
        value = value + 2. * pi
    return value


def distance(xi,yi,xj,yj):
    ax=xj-xi
    ay=yj-yi
    value=sqrt(ax**2+ay**2)
    return value


class OptionParser(optparse.OptionParser):
    def check_required(self, opt):
        option = self.get_option(opt)
        # Assumes the option's 'default' is set to None!
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)


class GdalErrorHandler(object):
    def __init__(self):
        self.err_level = gdal.CE_None
        self.err_no = 0
        self.err_msg = ''

    def handler(self, err_level, err_no, err_msg):
        self.err_level = err_level
        self.err_no = err_no
        self.err_msg = err_msg


def is_number(n):
    is_number = True
    try:
        num = float(n)
        # check for "nan" floats
        is_number = num == num  # or use `math.isnan(num)`
    except ValueError:
        is_number = False
    return is_number


def process(input_shapefile,
            input_shapefile_field_idRail,
            input_shapefile_field_idRailway,
            output_shapefile):
    str_error = ''
    str_error = ''
    driver = ogr.GetDriverByName('ESRI Shapefile')
    input_ds = None
    try:
        input_ds = driver.Open(input_shapefile, 0)  # 0 means read-only. 1 means writeable.
    except Exception as e:
        assert err.err_level == gdal.CE_Failure, (
            'The handler error level should now be at failure')
        assert err.err_msg == e.args[0], 'raised exception should contain the message'
        str_error = "Function process"
        str_error = ('Handled warning: level={}, no={}, msg={}'.format(
            err.err_level, err.err_no, err.err_msg))
        return str_error
    layer = input_ds.GetLayer()
    geometry_type = layer.GetGeomType()
    if geometry_type != ogr.wkbLineString \
            and geometry_type != ogr.wkbLineStringM \
            and geometry_type != ogr.wkbLineStringZM \
            and geometry_type != ogr.wkbLineString25D:
        str_error = "Function process"
        str_error += "\nNot LineString geometry type in file:\n{}".format(input_shapefile)
        return str_error
    layer_definition = layer.GetLayerDefn()
    field_idRail_index = layer_definition.GetFieldIndex(input_shapefile_field_idRail)
    if field_idRail_index == -1:
        str_error = "Function process"
        str_error += "\nField: {} not exists in file:\n{}".format(input_shapefile_field_idRail,
                                                                     input_shapefile)
        return str_error
    field_idRail_type = layer_definition.GetFieldDefn(field_idRail_index).GetType()
    if not field_idRail_type == ogr.OFTInteger \
            and not field_idRail_type == ogr.OFTString \
            and not field_idRail_type == ogr.OFTReal:
        str_error = "Function process"
        str_error += "\nField: {} is not valid type in file:\n{}".format(input_shapefile_field_idRail,
                                                                 input_shapefile)
        return str_error
    field_idRailway_index = layer_definition.GetFieldIndex(input_shapefile_field_idRailway)
    if field_idRailway_index == -1:
        str_error = "Function process"
        str_error += "\nField: {} not exists in file:\n{}".format(input_shapefile_field_idRailway,
                                                                     input_shapefile)
        return str_error
    field_idRailway_type = layer_definition.GetFieldDefn(field_idRailway_index).GetType()
    if not field_idRailway_type == ogr.OFTInteger \
            and not field_idRailway_type == ogr.OFTString\
            and not field_idRailway_type == ogr.OFTReal:
        str_error = "Function process"
        str_error += "\nField: {} is not valid type in file:\n{}".format(input_shapefile_field_idRailway,
                                                                 input_shapefile)
        return str_error
    number_of_features = layer.GetFeatureCount()
    input_crs = layer.GetSpatialRef()
    rails = {}
    railways = {}
    for feature in layer:
        geom = feature.GetGeometryRef().Clone()
        str_railId = feature.GetFieldAsString(field_idRail_index).lower()
        if str_railId in rails:
            str_error = "Function process"
            str_error += "\nRepeated rail id: {} in file:\n{}".format(str_railId,
                                                                      input_shapefile)
            return str_error
        str_railwayId = feature.GetFieldAsString(field_idRailway_index).lower()
        rail = {}
        rail['railwayId'] = str_railwayId
        rail['geom'] = geom
        rails[str_railId] = rail
        if not str_railwayId in railways:
            railsInRailway = []
            railways[str_railwayId] = railsInRailway
        if len(railways[str_railwayId]) == 2:
            str_error = "Function process"
            str_error += "\nMore than two rails in railway id: {} in file:\n{}".format(str_railwayId,
                                                                                       input_shapefile)
            return str_error
        if str_railId in railways[str_railwayId]:
            str_error = "Function process"
            str_error += "\nRepeated rail id: {} in railway id: {} file:\n{}".format(str_railId,
                                                                                     str_railwayId,
                                                                                     input_shapefile)
            return str_error
        railways[str_railwayId].append(str_railId)
    # Create the output Layer
    outDriver = ogr.GetDriverByName("ESRI Shapefile")
    # Remove output shapefile if it already exists
    if os.path.exists(output_shapefile):
        outDriver.DeleteDataSource(output_shapefile)
    if os.path.exists(output_shapefile):
        str_error = "Function process"
        str_error += "\nError removing existing output file:\n{}".format(output_shapefile)
        return str_error
    output_ds = outDriver.CreateDataSource(output_shapefile)
    outLayer = output_ds.CreateLayer(output_shapefile.split(".")[0], input_crs, geom_type=ogr.wkbLineString)
    outLayerDefn = outLayer.GetLayerDefn()
    outLayer.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn("railway", ogr.OFTString))
    outLayer.CreateField(ogr.FieldDefn("enabled", ogr.OFTInteger))
    cont_feature = 0
    # geom_boxes = []
    for railwayId in railways.keys():
        geom_centerline = ogr.Geometry(ogr.wkbLineString)
        firstRailId = railways[railwayId][0]
        secondRailId = railways[railwayId][1]
        firstRailGeom = rails[firstRailId]['geom']
        secondRailGeom = rails[secondRailId]['geom']
        firstRailPoints = firstRailGeom.GetPoints()
        secondRailPoints = secondRailGeom.GetPoints()
        for npto in range(len(firstRailPoints)):
            pto_1 = firstRailPoints[npto]
            minDistance = 100000
            secondPoints = {}
            cont = 0
            posMinimumDistance = -1
            for npto2 in range(len(secondRailPoints)):
                pto_2 = secondRailPoints[npto2]
                dis = distance(pto_1[0], pto_1[1], pto_2[0], pto_2[1])
                secondPoint = {}
                secondPoint['distance'] = dis
                secondPoint['x'] = pto_2[0]
                secondPoint['y'] = pto_2[1]
                secondPoints[cont] = secondPoint
                if dis < minDistance:
                    posMinimumDistance = cont
                    minDistance = dis
                cont = cont + 1
            minDistance = 100000
            posSecondMinimumDistance = -1
            for secondPointKey in secondPoints.keys():
                if secondPointKey == posMinimumDistance:
                    continue
                if secondPoints[secondPointKey]['distance'] < minDistance:
                    minDistance = secondPoints[secondPointKey]['distance']
                    posSecondMinimumDistance = secondPointKey
            x = pto_1[0]
            y = pto_1[1]
            x2_1 = secondPoints[posMinimumDistance]['x']
            y2_1 = secondPoints[posMinimumDistance]['y']
            x2_2 = secondPoints[posSecondMinimumDistance]['x']
            y2_2 = secondPoints[posSecondMinimumDistance]['y']
            # y = m x + n
            m2 = tan(pi/2)
            if abs(x2_2-x2_1) > 0.001:
                m2 = (y2_2-y2_1) / (x2_2-x2_1)
            n2 = y2_1 - m2 * x2_1
            m1 = -1.0 / m2
            n1 = y - m1 * x
            # m1 * x + n1 = m2 * x + n2
            # x = (n1 - n2) / (m2 - m1)
            if abs(m2 - m1) > 0.000000000001:
                xI = (n1 - n2) / (m2 - m1)
            else:
                xI = tan(pi/2)
            yI = m1 * xI + n1
            yI_2 = m2 * xI + n2
            x_cl = (x + xI) / 2.
            y_cl = (y + yI) / 2.
            geom_centerline.AddPoint(x_cl, y_cl)

        outFeature = ogr.Feature(outLayerDefn)
        cont_feature = cont_feature + 1
        outFeature.SetField("id", cont_feature)
        outFeature.SetField("railway", railwayId)
        outFeature.SetField("enabled", 1)
        outFeature.SetGeometry(geom_centerline)
        # Add new feature to output Layer
        outLayer.CreateFeature(outFeature)
        outFeature = None
    output_ds = None
    return str_error


def main():
    # ==================
    # parse command line
    # ==================
    usage = "usage: %prog [options] "
    parser = OptionParser(usage=usage)
    parser.add_option("--input_shapefile", dest="input_shapefile", action="store", type="string",
                      help="Input shapefile", default=None)
    parser.add_option("--input_shapefile_field_idRail", dest="input_shapefile_field_idRail", action="store", type="string",
                      help="Identifier rail field name in input shapefile", default=None)
    parser.add_option("--input_shapefile_field_idRailway", dest="input_shapefile_field_idRailway", action="store", type="string",
                      help="Identifier railway field name in input shapefile", default=None)
    parser.add_option("--output_shapefile", dest="output_shapefile", action="store", type="string",
                      help="Output shapefile", default=None)
    (options, args) = parser.parse_args()
    if not options.input_shapefile:
        parser.print_help()
        return
    if not options.input_shapefile_field_idRail:
        parser.print_help()
        return
    if not options.input_shapefile_field_idRailway:
        parser.print_help()
        return
    if not options.output_shapefile:
        parser.print_help()
        return
    input_shapefile = options.input_shapefile
    if not exists(input_shapefile):
        print("Error:\nNot exists input shapefile:\n{}".format(input_shapefile))
        return
    input_shapefile_field_idRail = options.input_shapefile_field_idRail
    input_shapefile_field_idRailway = options.input_shapefile_field_idRailway
    output_shapefile = options.output_shapefile
    # if exists(output_shapefile):
    #     try:
    #         os.remove(output_shapefile)
    #     except FileNotFoundError as e:
    #         print("Removing output shapefile:\n{}".format(output_shapefile))
    #         print("Error\t" + e.strerror)
    #     except OSError as e:
    #         print("Removing output shapefile:\n{}".format(output_shapefile))
    #         print("Error\t" + e.strerror)
    #     return
    str_error = process(input_shapefile,
                        input_shapefile_field_idRail,
                        input_shapefile_field_idRailway,
                        output_shapefile)
    if str_error:
        print("Error:\n{}".format(str_error))
        return
    print("... Process finished")


if __name__ == '__main__':
    # https://gdal.org/api/python_gotchas.html
    err = GdalErrorHandler()
    gdal.PushErrorHandler(err.handler)
    gdal.UseExceptions()  # Exceptions will get raised on anything >= gdal.CE_Failure
    assert err.err_level == gdal.CE_None, 'the error level starts at 0'
    main()

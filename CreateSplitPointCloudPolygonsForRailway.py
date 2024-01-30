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
from math import floor, ceil, sqrt, isnan, modf, trunc, sin, cos
import csv
import re
from numpy import arctan2
from numpy import pi


railwayWidth = 1.8


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
            input_shapefile_field_idRailway,
            output_path,
            railway_buffer):
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
    railways = {}
    cont_feature = 0
    output_shapefile_all = output_path + "/"
    output_shapefile_all += os.path.splitext(os.path.basename(input_shapefile))[0]
    output_shapefile_all += "_Railway_"
    output_shapefile_all += "all"
    output_shapefile_all += ".shp"
    output_shapefile_all = os.path.normpath(output_shapefile_all)
    outDriver_all = ogr.GetDriverByName("ESRI Shapefile")
    # Remove output shapefile if it already exists
    if os.path.exists(output_shapefile_all):
        outDriver_all.DeleteDataSource(output_shapefile_all)
    if os.path.exists(output_shapefile_all):
        str_error = "Function process"
        str_error += "\nError removing existing output file:\n{}".format(output_shapefile_all)
        return str_error
    output_ds_all = outDriver_all.CreateDataSource(output_shapefile_all)
    outLayer_all = output_ds_all.CreateLayer(output_shapefile_all.split(".")[0], input_crs, geom_type=ogr.wkbPolygon)
    outLayerDefn_all = outLayer_all.GetLayerDefn()
    outLayer_all.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
    outLayer_all.CreateField(ogr.FieldDefn("railway", ogr.OFTString))
    outLayer_all.CreateField(ogr.FieldDefn("str_id", ogr.OFTString))
    outLayer_all.CreateField(ogr.FieldDefn("enabled", ogr.OFTInteger))
    for feature in layer:
        geom = feature.GetGeometryRef().Clone()
        railwayId = feature.GetFieldAsString(field_idRailway_index).lower()
        geomBuffer = geom.Buffer(railway_buffer)
        output_shapefile = output_path + "/"
        output_shapefile += os.path.splitext(os.path.basename(input_shapefile))[0]
        output_shapefile += "_Railway_"
        output_shapefile += railwayId
        output_shapefile += ".shp"
        output_shapefile = os.path.normpath(output_shapefile)
        outDriver = ogr.GetDriverByName("ESRI Shapefile")
        # Remove output shapefile if it already exists
        if os.path.exists(output_shapefile):
            outDriver.DeleteDataSource(output_shapefile)
        if os.path.exists(output_shapefile):
            str_error = "Function process"
            str_error += "\nError removing existing output file:\n{}".format(output_shapefile)
            return str_error
        output_ds = outDriver.CreateDataSource(output_shapefile)
        outLayer = output_ds.CreateLayer(output_shapefile.split(".")[0], input_crs, geom_type=ogr.wkbPolygon)
        outLayerDefn = outLayer.GetLayerDefn()
        outLayer.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
        outLayer.CreateField(ogr.FieldDefn("railway", ogr.OFTString))
        outLayer.CreateField(ogr.FieldDefn("str_id", ogr.OFTString))
        outLayer.CreateField(ogr.FieldDefn("enabled", ogr.OFTInteger))
        outFeature = ogr.Feature(outLayerDefn)
        outFeature.SetField("id", cont_feature)
        outFeature.SetField("railway", railwayId)
        str_id = "railway_" + railwayId
        outFeature.SetField("str_id", str_id)
        outFeature.SetField("enabled", 1)
        outFeature.SetGeometry(geomBuffer)
        outLayer.CreateFeature(outFeature)
        outLayer_all.CreateFeature(outFeature)
        cont_feature = cont_feature + 1
        outFeature = None
        output_ds = None
    output_ds_all = None
    return str_error


def main():
    # ==================
    # parse command line
    # ==================
    usage = "usage: %prog [options] "
    parser = OptionParser(usage=usage)
    parser.add_option("--input_shapefile", dest="input_shapefile", action="store", type="string",
                      help="Input shapefile", default=None)
    parser.add_option("--input_shapefile_field_idRailway", dest="input_shapefile_field_idRailway", action="store", type="string",
                      help="Identifier railway field name in input shapefile", default=None)
    parser.add_option("--railway_buffer", dest="railway_buffer", action="store", type="string",
                      help="Rail buffer distance", default=None)
    parser.add_option("--output_path", dest="output_path", action="store", type="string",
                      help="Output path for shapefiles", default=None)
    (options, args) = parser.parse_args()
    if not options.input_shapefile:
        parser.print_help()
        return
    if not options.input_shapefile_field_idRailway:
        parser.print_help()
        return
    if not options.railway_buffer:
        parser.print_help()
        return
    if not options.output_path:
        parser.print_help()
        return
    input_shapefile = options.input_shapefile
    if not exists(input_shapefile):
        print("Error:\nNot exists input shapefile:\n{}".format(input_shapefile))
        return
    input_shapefile_field_idRailway = options.input_shapefile_field_idRailway
    railway_buffer = options.railway_buffer
    if not is_number(railway_buffer):
        print("Error:\nInvalid section length: {}".format(railway_buffer))
        return
    railway_buffer = float(railway_buffer)
    output_path = options.output_path
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    if not os.path.exists(output_path):
        print("Error:\nNot exists output path:\n{}".format(output_path))
        return
    str_error = process(input_shapefile,
                        input_shapefile_field_idRailway,
                        output_path,
                        railway_buffer)
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

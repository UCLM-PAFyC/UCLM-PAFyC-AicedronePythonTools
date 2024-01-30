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
            output_shapefile,
            widthForRailway,
            widthForRail,
            objectTypeRailway,
            objectTypeRail):
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
    outLayer = output_ds.CreateLayer(output_shapefile.split(".")[0], input_crs, geom_type=ogr.wkbPolygon)
    outLayerDefn = outLayer.GetLayerDefn()
    outLayer.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn("railway", ogr.OFTString))
    outLayer.CreateField(ogr.FieldDefn("rail_1", ogr.OFTString))
    outLayer.CreateField(ogr.FieldDefn("rail_2", ogr.OFTString))
    outLayer.CreateField(ogr.FieldDefn("type", ogr.OFTString))
    outLayer.CreateField(ogr.FieldDefn("enabled", ogr.OFTInteger))
    cont_feature = 0
    # geom_boxes = []
    for railwayId in railways.keys():
        firstRailId = railways[railwayId][0]
        secondRailId = railways[railwayId][1]
        firstRailGeom = rails[firstRailId]['geom']
        secondRailGeom = rails[secondRailId]['geom']
        # firstGeomBuffer = firstRailGeom.Buffer(sectionWidth/2.+railwayWidth/4.)
        # secondGeomBuffer = secondRailGeom.Buffer(sectionWidth/2.+railwayWidth/4.)
        # railway
        geom_union = firstRailGeom.Union(secondRailGeom)
        geom_box = geom_union.Buffer(widthForRailway)
        outFeature = ogr.Feature(outLayerDefn)
        cont_feature = cont_feature + 1
        outFeature.SetField("id", cont_feature)
        outFeature.SetField("railway", railwayId)
        outFeature.SetField("rail_1", firstRailId)
        outFeature.SetField("rail_2", secondRailId)
        outFeature.SetField("type", objectTypeRailway)
        outFeature.SetField("enabled", 1)
        outFeature.SetGeometry(geom_box)
        # Add new feature to output Layer
        outLayer.CreateFeature(outFeature)
        # geom_boxes.append(geom_box)
        outFeature = None
        # first rail
        outFeatureFirstRail = ogr.Feature(outLayerDefn)
        geom_boxFirstRail = firstRailGeom.Buffer(widthForRail/2.)
        cont_feature = cont_feature + 1
        outFeatureFirstRail.SetField("id", cont_feature)
        outFeatureFirstRail.SetField("railway", railwayId)
        outFeatureFirstRail.SetField("rail_1", firstRailId)
        outFeatureFirstRail.SetField("rail_2", '')
        outFeatureFirstRail.SetField("type", objectTypeRail)
        outFeatureFirstRail.SetField("enabled", 1)
        outFeatureFirstRail.SetGeometry(geom_boxFirstRail)
        # Add new feature to output Layer
        outLayer.CreateFeature(outFeatureFirstRail)
        # geom_boxes.append(geom_box)
        outFeatureFirstRail = None
        # second rail
        outFeatureSecondRail = ogr.Feature(outLayerDefn)
        geom_boxSecondRail = secondRailGeom.Buffer(widthForRail/2.)
        cont_feature = cont_feature + 1
        outFeatureSecondRail.SetField("id", cont_feature)
        outFeatureSecondRail.SetField("railway", railwayId)
        outFeatureSecondRail.SetField("rail_1", '')
        outFeatureSecondRail.SetField("rail_2", secondRailId)
        outFeatureSecondRail.SetField("type", objectTypeRail)
        outFeatureSecondRail.SetField("enabled", 1)
        outFeatureSecondRail.SetGeometry(geom_boxSecondRail)
        # Add new feature to output Layer
        outLayer.CreateFeature(outFeatureSecondRail)
        # geom_boxes.append(geom_box)
        outFeatureSecondRail = None
        yo = 1
    # input_ds = None
    output_ds = None
    return str_error


def process_segments(input_shapefile,
            input_shapefile_field_idRail,
            input_shapefile_field_idRailway,
            output_shapefile,
            sectionLength,
            sectionWidth,
            sectionsDistance,
            objectType):
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
    outLayer = output_ds.CreateLayer(output_shapefile.split(".")[0], input_crs, geom_type=ogr.wkbPolygon)
    outLayerDefn = outLayer.GetLayerDefn()
    outLayer.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn("railway", ogr.OFTString))
    outLayer.CreateField(ogr.FieldDefn("rail_1", ogr.OFTString))
    outLayer.CreateField(ogr.FieldDefn("rail_2", ogr.OFTString))
    outLayer.CreateField(ogr.FieldDefn("type", ogr.OFTString))
    outLayer.CreateField(ogr.FieldDefn("enabled", ogr.OFTInteger))
    cont_feature = 0
    geom_boxes = []
    for railwayId in railways.keys():
        firstRailId = railways[railwayId][0]
        secondRailId = railways[railwayId][1]
        firstRailGeom = rails[firstRailId]['geom']
        secondRailGeom = rails[secondRailId]['geom']
        # secondGeomBuffer = secondRailGeom.Buffer(sectionWidth/2.+railwayWidth/4.)
        secondGeomBuffer = secondRailGeom.Buffer(railwayWidth/4.)
        firstRailPoints = firstRailGeom.GetPoints()
        # distance_to_origin_next_center = 1.0 + sectionLength / 2.# empizo a 1 m del primer punto
        distance_to_origin_next_center = 1.0 + sectionLength / 2.# empizo a 1 m del primer punto
        distance_to_origin_section_starts = 0
        for npto in range(len(firstRailPoints)-1):
            pto_1 = firstRailPoints[npto]
            pto_2 = firstRailPoints[npto+1]
            azi = azimuth(pto_1[0],pto_1[1],pto_2[0],pto_2[1])
            dis = distance(pto_1[0],pto_1[1],pto_2[0],pto_2[1])
            if (distance_to_origin_section_starts+dis) < distance_to_origin_next_center:
                distance_to_origin_section_starts += dis
                continue
            dis_to_star = distance_to_origin_next_center - distance_to_origin_section_starts
            pto_start_x = pto_1[0] + (dis_to_star - sectionLength/2.) * sin(azi)
            pto_start_y = pto_1[1] + (dis_to_star - sectionLength/2.) * cos(azi)
            pto_box_1_x = pto_start_x + (sectionWidth/2.+railwayWidth/4.) * sin(azi - pi/2.)
            pto_box_1_y = pto_start_y + (sectionWidth/2.+railwayWidth/4.) * cos(azi - pi/2.)
            pto_box_2_x = pto_box_1_x + sectionLength * sin(azi)
            pto_box_2_y = pto_box_1_y + sectionLength * cos(azi)
            pto_box_3_x = pto_box_2_x + (sectionWidth+railwayWidth/2.) * sin(azi + pi/2.)
            pto_box_3_y = pto_box_2_y + (sectionWidth+railwayWidth/2.) * cos(azi + pi/2.)
            pto_box_4_x = pto_box_3_x + sectionLength * sin(azi + pi)
            pto_box_4_y = pto_box_3_y + sectionLength * cos(azi + pi)
            geom_outRing = ogr.Geometry(ogr.wkbLinearRing)
            geom_outRing.AddPoint(pto_box_1_x, pto_box_1_y)
            geom_outRing.AddPoint(pto_box_2_x, pto_box_2_y)
            geom_outRing.AddPoint(pto_box_3_x, pto_box_3_y)
            geom_outRing.AddPoint(pto_box_4_x, pto_box_4_y)
            geom_outRing.AddPoint(pto_box_1_x, pto_box_1_y)
            geom_poly = ogr.Geometry(ogr.wkbPolygon)
            geom_poly.AddGeometry(geom_outRing)
            wkt = geom_poly.ExportToWkt()
            geom_box = geom_poly.Intersection(secondGeomBuffer)
            box_wkt = geom_box.ExportToWkt()
            distance_to_origin_next_center += (sectionLength + sectionsDistance)
            distance_to_origin_section_starts += dis
            geom_box_area = geom_box.GetArea()
            if len(geom_box.GetGeometryRef(0).GetPoints()) > 9:
                continue
            duplicated_box = False
            for nb in range(len(geom_boxes)):
                if geom_box.Intersects(geom_boxes[nb]):
                    geom_int = geom_box.Intersection(geom_boxes[nb])
                    if geom_int.GetArea()/geom_box_area > 0.5:
                        duplicated_box = True
                        break
            if duplicated_box:
                continue
            outFeature = ogr.Feature(outLayerDefn)
            cont_feature = cont_feature + 1
            outFeature.SetField("id", cont_feature)
            outFeature.SetField("railway", railwayId)
            outFeature.SetField("rail_1", firstRailId)
            outFeature.SetField("rail_2", secondRailId)
            outFeature.SetField("type", objectType)
            outFeature.SetField("enabled", 1)
            outFeature.SetGeometry(geom_box)
            # Add new feature to output Layer
            outLayer.CreateFeature(outFeature)
            geom_boxes.append(geom_box)
            outFeature = None
        yo = 1
    # input_ds = None
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
    parser.add_option("--widthForRailway", dest="widthForRailway", action="store", type="string",
                      help="Width for railway", default=None)
    parser.add_option("--widthForRail", dest="widthForRail", action="store", type="string",
                      help="Width for rail", default=None)
    parser.add_option("--object_type_railway", dest="object_type_railway", action="store", type="string",
                      help="Object type for railway", default=None)
    parser.add_option("--object_type_rail", dest="object_type_rail", action="store", type="string",
                      help="Object type for rail", default=None)
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
    if not options.widthForRailway:
        parser.print_help()
        return
    if not options.widthForRail:
        parser.print_help()
        return
    if not options.object_type_railway:
        parser.print_help()
        return
    if not options.object_type_rail:
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
    widthForRailway = options.widthForRailway
    if not is_number(widthForRailway):
        print("Error:\nInvalid section width: {}".format(widthForRailway))
        return
    widthForRailway = float(widthForRailway)
    widthForRail = options.widthForRail
    if not is_number(widthForRail):
        print("Error:\nInvalid section width: {}".format(widthForRail))
        return
    widthForRail = float(widthForRail)
    objectTypeRailway = options.object_type_railway
    objectTypeRail = options.object_type_rail
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
                        output_shapefile,
                        widthForRailway,
                        widthForRail,
                        objectTypeRailway,
                        objectTypeRail)
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

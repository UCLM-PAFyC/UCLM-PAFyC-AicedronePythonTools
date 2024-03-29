# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import optparse
import numpy
# from osgeo import gdal, osr, ogr
import os
from PIL import Image
from urllib.parse import unquote
import shutil
from os.path import exists
import glob
from math import floor, ceil, sqrt, isnan, modf, trunc, sin, cos
import csv
import re


class OptionParser(optparse.OptionParser):
    def check_required(self, opt):
        option = self.get_option(opt)
        # Assumes the option's 'default' is set to None!
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)


def createTile(file_path, tile_columns, tile_rows, output_path):
    try:
        file_name, file_ext = os.path.splitext(file_path)
        file_name = os.path.basename(file_name)
        output_path = output_path + '\\'
        img = Image.open(file_path)
        width, height = img.size
        new_width = 0
        new_height = 0
        if isinstance(tile_columns, int):
            new_width = tile_columns
        else:
            new_width = floor(width * tile_columns)
        if isinstance(tile_rows, int):
            new_height = tile_rows
        else:
            new_height = floor(height * tile_rows)
        tile_first_row = 0
        tile_row = 1
        # while tile_first_row <= (height - new_height):
        while tile_first_row < height:
            tile_last_row = tile_first_row + new_height
            tile_first_column = 0
            tile_column = 1
            # while tile_first_column <= (width - new_width):
            while tile_first_column < width:
                tile_last_column = tile_first_column + new_width
                tile = (tile_first_column, tile_first_row, tile_last_column, tile_last_row)
                new_img = img.crop(tile)
                new_file_name = f"{file_name}_row_{tile_row}_column_{tile_column}{file_ext}"
                new_file_path = os.path.join(os.path.dirname(output_path), new_file_name)
                new_img.save(new_file_path)
                tile_first_column = tile_first_column + new_width
                tile_column = tile_column + 1
                # os.remove(file_path)
            tile_first_row = tile_first_row + new_height
            tile_row = tile_row + 1
    except Exception as e:
        print(f"An error occurred: {e}")


def main():
    # ==================
    # parse command line
    # ==================
    usage = "usage: %prog [options] "
    parser = OptionParser(usage=usage)
    parser.add_option("--images_path", dest="images_path", action="store", type="string",
                      help="Images path", default=None)
    parser.add_option("--images_file_extension", dest="images_file_extension", action="store", type="string",
                      help="Images file extension", default=None)
    parser.add_option("--tile_columns", dest="tile_columns", action="store", type="string",
                      help="Integer for absolute number of columns or float for relative size as per unit",
                      default=None)
    parser.add_option("--tile_rows", dest="tile_rows", action="store", type="string",
                      help="Integer for absolute number of rows or float for relative size as per unit", default=None)
    parser.add_option("--output_path", dest="output_path", action="store", type="string",
                      help="Path for output image tiles", default=None)
    (options, args) = parser.parse_args()
    if not options.images_path:
        parser.print_help()
        return
    if not options.images_file_extension:
        parser.print_help()
        return
    if not options.tile_columns:
        parser.print_help()
        return
    if not options.tile_rows:
        parser.print_help()
        return
    if not options.output_path:
        parser.print_help()
        return
    images_path = options.images_path
    if not exists(images_path):
        print("Error:\nNot exists images path:\n{}".format(images_path))
        return
    images_file_extension = options.images_file_extension
    images_file_extension = images_file_extension.lower()
    files = os.listdir(images_path)
    images = []
    for file in files:
        if file.lower().endswith(images_file_extension):
            image_path = os.path.join(images_path, file)
            images.append(image_path)
    if len(images) < 1:
        print("Error:\nNot exists images {} in path:\n{}".format(images_file_extension, images_path))
        return
    str_tile_columns = options.tile_columns
    flag = True
    try:
        tile_columns = int(str_tile_columns)
    except ValueError:
        try:
            tile_columns = float(str_tile_columns)
        except ValueError:
            flag = False
    if not flag:
        print("Error:\nInvalid tile columns: {}".format(str_tile_columns))
        return
    str_tile_rows = options.tile_rows
    flag = True
    try:
        tile_rows = int(str_tile_rows)
    except ValueError:
        try:
            tile_rows = float(str_tile_rows)
        except ValueError:
            flag = False
    if not flag:
        print("Error:\nInvalid tile columns: {}".format(str_tile_rows))
        return
    output_path = options.output_path
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    if not os.path.exists(output_path):
        print("Error:\nNot exists output path:\n{}".format(output_path))
        return
    # cont = 0 # debug
    for image in images:
        createTile(image, tile_columns, tile_rows, output_path)
        # cont = cont + 1 # debug
        # if cont > 1:
        #     break


if __name__ == '__main__':
    # https://gdal.org/api/python_gotchas.html
    # err = GdalErrorHandler()
    # gdal.PushErrorHandler(err.handler)
    # gdal.UseExceptions()  # Exceptions will get raised on anything >= gdal.CE_Failure
    # assert err.err_level == gdal.CE_None, 'the error level starts at 0'
    main()

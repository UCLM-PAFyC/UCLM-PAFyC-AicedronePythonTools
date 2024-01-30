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


def main():
    # ==================
    # parse command line
    # ==================
    usage = "usage: %prog [options] "
    parser = OptionParser(usage=usage)
    parser.add_option("--tiles_txt_files_path", dest="tiles_txt_files_path", action="store", type="string",
                      help="Tiles txt files path", default=None)
    parser.add_option("--tiles_n_columns", dest="tiles_n_columns", action="store", type="string",
                      help="Number of columns in tiles structure",
                      default=None)
    parser.add_option("--tiles_n_rows", dest="tiles_n_rows", action="store", type="string",
                      help="Number of rows in tiles structure",
                      default=None)
    parser.add_option("--output_path", dest="output_path", action="store", type="string",
                      help="Path for output image tiles", default=None)
    (options, args) = parser.parse_args()
    if not options.tiles_txt_files_path:
        parser.print_help()
        return
    if not options.tiles_n_columns:
        parser.print_help()
        return
    if not options.tiles_n_rows:
        parser.print_help()
        return
    if not options.output_path:
        parser.print_help()
        return
    tiles_txt_files_path = options.tiles_txt_files_path
    if not exists(tiles_txt_files_path):
        print("Error:\nNot exists tiles txt files path:\n{}".format(tiles_txt_files_path))
        return
    tiles_txt_file_extension = "txt"
    tiles_txt_file_extension = tiles_txt_file_extension.lower()
    files = os.listdir(tiles_txt_files_path)
    images = []
    for file in files:
        if file.lower().endswith(tiles_txt_file_extension):
            image_path = os.path.join(tiles_txt_file_extension, file)
            images.append(image_path)
    if len(images) < 1:
        print("Error:\nNot exists tiles txt files in path:\n{}".format(tiles_txt_files_path))
        return
    str_tiles_n_columns = options.tiles_n_columns
    flag = True
    try:
        tiles_n_columns = int(str_tiles_n_columns)
    except ValueError:
        flag = False
    if not flag:
        print("Error:\nInvalid number of columns in tile structure: {}".format(str_tiles_n_columns))
        return
    str_tiles_n_rows = options.tiles_n_rows
    flag = True
    try:
        tiles_n_rows = int(str_tiles_n_rows)
    except ValueError:
        flag = False
    if not flag:
        print("Error:\nInvalid number of rows in tile structure: {}".format(str_tiles_n_rows))
        return
    output_path = options.output_path
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    if not os.path.exists(output_path):
        print("Error:\nNot exists output path:\n{}".format(output_path))
        return
    # # cont = 0 # debug
    # for image in images:
    #     createTile(image, tile_columns, tile_rows, output_path)
    #     # cont = cont + 1 # debug
    #     # if cont > 1:
    #     #     break


if __name__ == '__main__':
    # https://gdal.org/api/python_gotchas.html
    # err = GdalErrorHandler()
    # gdal.PushErrorHandler(err.handler)
    # gdal.UseExceptions()  # Exceptions will get raised on anything >= gdal.CE_Failure
    # assert err.err_level == gdal.CE_None, 'the error level starts at 0'
    main()

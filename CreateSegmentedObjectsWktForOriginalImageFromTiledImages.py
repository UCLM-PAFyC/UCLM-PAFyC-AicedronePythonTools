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

def joinTiles(image_file_name, image_tiles,
              tile_width,
              tile_height,
              output_path):
    str_error = ''
    wkt_file_name = image_file_name + '.txt'
    output_file_name = os.path.join(output_path, wkt_file_name)
    output_file = open(output_file_name, "w")
    output_lines = []
    output_lines.append('type;wkt\n')
    # output_file.write('type;wkt')
    for tile in image_tiles:
        column = tile['column']
        row = tile['row']
        file = tile['file']
        input_file = open(file, 'r')
        input_lines = input_file.readlines()
        for input_line in input_lines:
            str_line = input_line.strip()#remove /n
            str_values = str_line.split(' ')
            str_type = str_values[0]
            # if int(str_type) == 0:
            #     continue
            pos = 1
            str_output_line = str_type + ';POLYGON(('
            str_first_pto_column = ''
            str_first_pto_row = ''
            while pos < (len(str_values) - 1):
                str_pto_col = str_values[pos]
                str_pto_row = str_values[pos+1]
                pto_col = float(str_pto_col)
                pto_row = float(str_pto_row)
                pto_col = tile_width * pto_col + (column - 1) * tile_width
                pto_row = tile_height * pto_row + (row - 1) * tile_height
                pto_row = -1.0 * pto_row
                str_pto_column = "{0:.2f}".format(pto_col)
                str_pto_row = "{0:.2f}".format(pto_row)
                if pos == 1:
                    str_first_pto_column = str_pto_column
                    str_first_pto_row = str_pto_row
                str_output_line = str_output_line + str_pto_column
                str_output_line = str_output_line + ' '
                str_output_line = str_output_line + str_pto_row
                str_output_line = str_output_line + ','
                pos = pos + 2
            str_output_line = str_output_line + str_first_pto_column
            str_output_line = str_output_line + ' '
            str_output_line = str_output_line + str_first_pto_row
            str_output_line = str_output_line + '))\n'
            output_lines.append(str_output_line)
    output_file.writelines(output_lines)
    output_file.close()
    return True, str_error

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
    parser.add_option("--original_image_width", dest="original_image_width", action="store", type="string",
                      help="Original image width",
                      default=None)
    parser.add_option("--original_image_height", dest="original_image_height", action="store", type="string",
                      help="Original image height",
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
    if not options.original_image_width:
        parser.print_help()
        return
    if not options.original_image_height:
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
    images = {}
    for file in files:
        if not file.lower().endswith(tiles_txt_file_extension):
            continue
        if not '_row' in file.lower():
            continue
        image_path = os.path.join(tiles_txt_files_path, file)
        original_image_file_name_without_extension = file.split('_row')[0]
        str_aux = file.split('_row')[1]
        str_row = str_aux.split('_')[1]
        str_aux = str_aux.split('_column_')[1]
        str_column = str_aux.split('.')[0]
        image_tile = {}
        image_tile['row'] = int(str_row)
        image_tile['column'] = int(str_column)
        image_tile['file'] = image_path
        if not original_image_file_name_without_extension in images:
            images[original_image_file_name_without_extension] = []
        images[original_image_file_name_without_extension].append(image_tile)
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
    str_original_image_width = options.original_image_width
    flag = True
    try:
        original_image_width = int(str_original_image_width)
    except ValueError:
        flag = False
    if not flag:
        print("Error:\nInvalid original image width: {}".format(str_original_image_width))
        return
    str_original_image_height = options.original_image_height
    flag = True
    try:
        original_image_height = int(str_original_image_height)
    except ValueError:
        flag = False
    if not flag:
        print("Error:\nInvalid original image height: {}".format(str_original_image_height))
        return
    tile_width = int(original_image_width / tiles_n_columns)
    tile_height = int(original_image_height / tiles_n_rows)
    output_path = options.output_path
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    if not os.path.exists(output_path):
        print("Error:\nNot exists output path:\n{}".format(output_path))
        return
    cont = 0 # debug
    for image_file_name in images.keys():
        if cont > 2:# debug
            break
        success, str_error = joinTiles(image_file_name, images[image_file_name],
                                       tile_width, tile_height,
                                       output_path)
        if not success:
            if not flag:
                print("Joining tiles for image {}, error: {}".format(image, str_error))
                return
            break
        cont = cont + 1

if __name__ == '__main__':
    # https://gdal.org/api/python_gotchas.html
    # err = GdalErrorHandler()
    # gdal.PushErrorHandler(err.handler)
    # gdal.UseExceptions()  # Exceptions will get raised on anything >= gdal.CE_Failure
    # assert err.err_level == gdal.CE_None, 'the error level starts at 0'
    main()

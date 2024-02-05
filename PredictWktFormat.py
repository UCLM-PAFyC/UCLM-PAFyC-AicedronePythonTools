# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import optparse
import os
from os.path import exists
from ultralytics import YOLO
from ultralytics.utils import ops
import cv2
import numpy as np
import torch


class OptionParser(optparse.OptionParser):
    def check_required(self, opt):
        option = self.get_option(opt)
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)


def predict(model,
            file_path,
            column,
            row,
            output_file_path):
    str_error = ''
    output_lines = []
    if exists(output_file_path):
        input_file = open(output_file_path, 'r')
        input_lines = input_file.readlines()
        for input_line in input_lines:
            output_lines.append(input_line)
        input_file.close()
    output_file = open(output_file_path, 'w')
    # results = model(filename, save=True, save_conf=True, conf=0.5, save_txt=False, stream=True)
    results = model(file_path)
    result = results[0]
    seg_classes = list(result.names.values())
    tile_height = result.orig_shape[0]
    tile_width = result.orig_shape[1]
    for result in results:
        if result.masks == None:
            continue
        masks = result.masks.data
        boxes = result.boxes.data
        clss = boxes[:, 5]
        for i, seg_class in enumerate(seg_classes):
            obj_indices = torch.where(clss == i)
            obj_masks = masks[obj_indices]
            # obj_mask = torch.any(obj_masks, dim=0).int() * 255
            for i, obj_index in enumerate(obj_indices[0].cpu().numpy()):
                obj_masks = masks[torch.tensor([obj_index])]
                obj_mask = torch.any(obj_masks, dim=0).int() * 255
                data_mask = obj_mask.cpu().numpy()
                # data_rows = data_mask.shape[0]
                # data_columns = data_mask.shape[1]
                data_mask_u8 = data_mask.astype(np.uint8)
                contours, hierarchy = cv2.findContours(data_mask_u8, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                str_type = seg_class
                str_output_line = str_type + ";"
                if len(contours) > 1:
                    str_output_line = str_output_line + "MULTIPOLYGON("
                number_of_contour = 0
                for c in range(len(contours)):
                    if len(contours) > 1:
                        if number_of_contour > 0:
                            str_output_line = str_output_line + ","
                        str_output_line = str_output_line + "(("
                    else:
                        str_output_line = str_output_line + "POLYGON(("
                    n_pto = 1
                    str_first_pto_column = ''
                    str_first_pto_row = ''
                    contour = contours[c]
                    x = contour.astype("float32")
                    ops.scale_coords(result.masks.data.shape[1:], x, result.masks.orig_shape, normalize=False)
                    for npto in range(len(x)):
                        coor = x[npto]
                        pto_col = coor[0][0]
                        pto_row = coor[0][1]
                        pto_col = pto_col + (column - 1) * tile_width
                        pto_row = pto_row + (row - 1) * tile_height
                        pto_row = -1.0 * pto_row
                        str_pto_column = "{0:.2f}".format(pto_col)
                        str_pto_row = "{0:.2f}".format(pto_row)
                        if n_pto == 1:
                            str_first_pto_column = str_pto_column
                            str_first_pto_row = str_pto_row
                        n_pto = n_pto + 1
                        str_output_line = str_output_line + str_pto_column
                        str_output_line = str_output_line + " "
                        str_output_line = str_output_line + str_pto_row
                        str_output_line = str_output_line + ","
                    str_output_line = str_output_line + str_first_pto_column
                    str_output_line = str_output_line + " "
                    str_output_line = str_output_line + str_first_pto_row
                    str_output_line = str_output_line + "))"
                    number_of_contour = number_of_contour + 1
                if len(contours) > 1:
                    str_output_line = str_output_line + ")"
                str_output_line = str_output_line + '\n'
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
    parser.add_option("--model_file", dest="model_file", action="store", type="string",
                      help="Model file", default=None)
    parser.add_option("--images_path", dest="images_path", action="store", type="string",
                      help="Images path", default=None)
    parser.add_option("--images_file_extension", dest="images_file_extension", action="store", type="string",
                      help="Images file extension", default=None)
    parser.add_option("--output_path", dest="output_path", action="store", type="string",
                      help="Path for output image tiles", default=None)
    (options, args) = parser.parse_args()
    if not options.model_file:
        parser.print_help()
        return
    if not options.images_path:
        parser.print_help()
        return
    if not options.images_file_extension:
        parser.print_help()
        return
    if not options.output_path:
        parser.print_help()
        return
    model_file = options.model_file
    if not exists(model_file):
        print("Error:\nNot exists model file:\n{}".format(model_file))
        return
    images_path = options.images_path
    if not exists(images_path):
        print("Error:\nNot exists images path:\n{}".format(images_path))
        return
    images_file_extension = options.images_file_extension
    images_file_extension = images_file_extension.lower()
    files = os.listdir(images_path)
    images = {}
    number_of_image_tiles = 0
    for file in files:
        if not file.lower().endswith(images_file_extension):
            continue
        if not '_row' in file.lower():
            continue
        image_path = os.path.join(images_path, file)
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
        number_of_image_tiles = number_of_image_tiles + 1
    if len(images) < 1:
        print("Error:\nNot exists tiles image files in path:\n{}".format(images_path))
        return
    output_path = options.output_path
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    if not os.path.exists(output_path):
        print("Error:\nNot exists output path:\n{}".format(output_path))
        return
    model = YOLO(model_file)
    cont = 0
    for image_file_name in images.keys():
        output_file_name = image_file_name + '.txt'
        output_file_path = os.path.join(output_path, output_file_name)
        if exists(output_file_path):
            os.remove(output_file_path)
        for tile in images[image_file_name]:
            # if cont > 0:  # debug
            #     break
            column = tile['column']
            row = tile['row']
            file_path = tile['file']
            success, str_error = predict(model,
                                         file_path,
                                         column,
                                         row,
                                         output_file_path)
            if not success:
                print("Prediction for image {}, error: {}".format(file_path, str_error))
                return
            cont = cont + 1
            print("Number of image tiles to process ....: {}", (str(number_of_image_tiles-cont)))


if __name__ == '__main__':
    main()

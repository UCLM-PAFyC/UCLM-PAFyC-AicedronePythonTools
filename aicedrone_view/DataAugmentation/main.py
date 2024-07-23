import os
import cv2
import numpy as np
import random
from multiprocessing import Pool, cpu_count
from functools import partial
from polygon_processing import *  # Importar funciones para procesar polígonos

def load_image(image_path):
    """
    Carga una imagen desde la ruta especificada.
    
    Args:
    - image_path: Ruta del archivo de imagen.
    
    Returns:
    - Imagen cargada.
    """
    image = cv2.imread(image_path)
    return image

def save_image(image_path, image):
    """
    Guarda una imagen en la ruta especificada.
    
    Args:
    - image_path: Ruta donde se guardará la imagen.
    - image: Imagen a guardar.
    """
    cv2.imwrite(image_path, image)

def augment_images(seq, num_augmentations, image_filename, image_path, polygon_filename, polygons_path, output_dir):
    """
    Augmenta una imagen y sus polígonos asociados, y guarda los resultados.
    
    Args:
    - seq: Secuencia de aumentación de imgaug.
    - num_augmentations: Número de aumentaciones a generar.
    - image_filename: Nombre del archivo de imagen original.
    - image_path: Ruta del archivo de imagen original.
    - polygon_filename: Nombre del archivo de polígonos original.
    - polygons_path: Ruta del archivo de polígonos original.
    - output_dir: Directorio de salida para las imágenes y polígonos augmentados.
    """
    if os.path.exists(polygons_path):
        original_image = load_image(image_path)
        if original_image is not None:
            image_path_dest = os.path.join(output_dir + '/images', image_filename)
            polygon_path_dest = os.path.join(output_dir + '/labels', polygon_filename)

            # Calcular la relación de aspecto (ancho / altura)
            desired_height = 640
            aspect_ratio = original_image.shape[1] / original_image.shape[0]
            desired_width = int(desired_height * aspect_ratio)

            # Redimensionar la imagen manteniendo la relación de aspecto
            #scaled_image = cv2.resize(original_image, (desired_width, desired_height), interpolation=cv2.INTER_AREA)
            #save_image(image_path_dest, scaled_image)
            save_image(image_path_dest, original_image)

            original_polygons = load_polygon_data(polygons_path)

            # Denormalizar las coordenadas de los polígonos al tamaño original de la imagen
            denormalized_original_polygons = denormalize_polygons(original_polygons, original_image.shape)

            save_polygon_data(polygon_path_dest, original_polygons)

            for i in range(num_augmentations):
                # Guardar imagen augmentada y datos de polígonos en el directorio de salida
                augmented_image_path = os.path.join(output_dir + '/images',
                                                    f'{image_filename.replace(".JPG", f"_aug_{i}.jpg")}')
                augmented_polygon_path = os.path.join(output_dir + '/labels',
                                                      f'{polygon_filename.replace(".txt", f"_aug_{i}.txt")}')

                # Augmentar la imagen y los polígonos juntos
                augmented_image, augmented_polygons = seq(image=original_image, polygons=denormalized_original_polygons)

                # Normalizar las coordenadas de los polígonos augmentados al rango [0, 1]
                normalized_augmented_polygons = normalize_polygons(augmented_polygons, augmented_image.shape)

                # Calcular la relación de aspecto (ancho / altura)
                aspect_ratio = augmented_image.shape[1] / augmented_image.shape[0]
                desired_width = int(desired_height * aspect_ratio)

                # Redimensionar la imagen manteniendo la relación de aspecto
                augmented_image = cv2.resize(augmented_image, (desired_width, desired_height),
                                             interpolation=cv2.INTER_AREA)
                save_image(augmented_image_path, augmented_image)

                save_polygon_data(augmented_polygon_path, normalized_augmented_polygons)

def augment_data_parallel(images_dir, polygons_dir, output_dirs, probabilities, num_augmentations=5):
    """
    Augmenta imágenes y polígonos en paralelo usando múltiples núcleos de CPU.
    
    Args:
    - images_dir: Directorio que contiene las imágenes originales.
    - polygons_dir: Directorio que contiene los archivos de polígonos originales.
    - output_dirs: Lista de directorios de salida para las imágenes y polígonos augmentados.
    - probabilities: Lista de probabilidades para asignar imágenes a los directorios de salida.
    - num_augmentations: Número de augmentaciones a generar por imagen.
    """
    # Asegurarse de que los directorios de salida existan
    for output_dir in output_dirs:
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(output_dir + '/labels/', exist_ok=True)
        os.makedirs(output_dir + '/images/', exist_ok=True)

    images_list = os.listdir(images_dir)

    # Definir la secuencia de augmentación
    seq = iaa.Sequential([
        iaa.Fliplr(0.5),  # Flip horizontal
        iaa.Flipud(0.5),  # Flip vertical
        iaa.Affine(rotate=(-45, 45)),  # Rotación aleatoria
        iaa.Multiply((0.8, 1.2)),  # Ajuste de brillo aleatorio
        iaa.GaussianBlur(sigma=(0, 1.0)),  # Desenfoque aleatorio
        iaa.AdditiveGaussianNoise(scale=(0, 0.05 * 255)),  # Ruido aleatorio
        iaa.Add((-10, 10), per_channel=0.5),  # Añadir valor a cada píxel
        iaa.Multiply((0.5, 1.5), per_channel=0.5),  # Cambiar brillo
        iaa.LinearContrast((0.5, 2.0), per_channel=0.5),  # Cambiar contraste
        iaa.Crop(percent=(0, 0.4))  # Recortar imágenes aleatoriamente
    ])

    # Crear una lista de parámetros para cada imagen a augmentar
    augment_params = []
    for image_filename in images_list:
        image_path = os.path.join(images_dir, image_filename)
        polygon_filename, extension = os.path.splitext(image_filename)
        polygon_filename = polygon_filename + '.txt'
        polygons_path = os.path.join(polygons_dir, polygon_filename)
        output_dir = random.choices(output_dirs, probabilities)[0]

        augment_params.append(
            (seq, num_augmentations, image_filename, image_path, polygon_filename, polygons_path, output_dir))

    if False:
        for seqA, nbAugmentation, iFilename, iPath, pFilename, pPath, oDir in augment_params:
            augment_images(seqA, nbAugmentation, iFilename, iPath, pFilename, pPath, oDir)
        augment_params.clear()
    else:
        if len(augment_params) > 0:
            # Determinar el número de núcleos de CPU para el procesamiento paralelo
            num_cores = cpu_count()

            # Usar partial para fijar argumentos para augment_images
            augment_images_partial = partial(augment_images)

            # Paralelizar el proceso de augmentación de imágenes
            with Pool(processes=num_cores) as pool:
                pool.starmap(augment_images_partial, augment_params)

if __name__ == "__main__":
    images_dir = "./Example_data/Originals/images/"
    polygons_dir = "./Example_data/Originals/labels/"
    output_dirs = ["./Example_data/Augmented/train", "./Example_data/Augmented/valid", "./Example_data/Augmented/test"]
    probabilities = [0.7, 0.15, 0.15]  # Establecer las probabilidades para cada carpeta de salida
    num_augmentations = 10

    augment_data_parallel(images_dir, polygons_dir, output_dirs, probabilities, num_augmentations)

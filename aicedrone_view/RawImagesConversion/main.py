import cv2
import os
import numpy as np
import argparse

def convert_bayer_to_jpg(raw_data, width, height, output_path):
    """
    Convierte una imagen en formato Bayer a formato JPEG.
    
    Args:
    - raw_data: Datos crudos de la imagen en formato Bayer.
    - width: Ancho de la imagen.
    - height: Altura de la imagen.
    - output_path: Ruta de salida para la imagen JPEG.
    """
    bayer_image = np.frombuffer(raw_data, dtype=np.uint8).reshape(height, width)
    rgb_image = cv2.cvtColor(bayer_image, cv2.COLOR_BayerBG2BGR)
    output_path = output_path.replace('\\', '/')
    cv2.imwrite(output_path, rgb_image)
    print(f"Converted and saved image to {output_path}")

def convert_raw_to_jpg(raw_folder, jpg_folder):
    """
    Convierte todas las imágenes en formato raw en una carpeta a formato JPEG.
    
    Args:
    - raw_folder: Carpeta que contiene las imágenes en formato raw.
    - jpg_folder: Carpeta donde se guardarán las imágenes convertidas a JPEG.
    """
    os.makedirs(jpg_folder, exist_ok=True)
    for root, dirs, files in os.walk(raw_folder):
        for file in files:
            if file.endswith('.raw'):
                raw_path = os.path.join(root, file)
                rel_path = os.path.relpath(raw_path, raw_folder)
                jpg_subfolder = os.path.join(jpg_folder, os.path.dirname(rel_path))
                os.makedirs(jpg_subfolder, exist_ok=True)
                jpg_path = os.path.join(jpg_subfolder, os.path.splitext(os.path.basename(rel_path))[0] + '.jpg')
                with open(raw_path, 'rb') as f:
                    raw_data = f.read()
                    convert_bayer_to_jpg(raw_data, 1440, 1080, jpg_path)

def images_to_video(image_folder, output_video_path, frame_rate):
    """
    Convierte una secuencia de imágenes en un video.
    
    Args:
    - image_folder: Carpeta que contiene las imágenes JPEG.
    - output_video_path: Ruta de salida para el video.
    - frame_rate: Tasa de cuadros por segundo para el video.
    """
    image_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(image_folder) for f in filenames if f.endswith('.jpg')]
    image_files.sort()
    first_image = cv2.imread(image_files[0])
    frame_size = (first_image.shape[1], first_image.shape[0])
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    video_writer = cv2.VideoWriter(output_video_path, fourcc, frame_rate, frame_size)
    for image_file in image_files:
        image = cv2.imread(image_file)
        video_writer.write(image)
    video_writer.release()

def create_videos_for_folders(root_folder, jpg_folder, output_folder, frame_rate):
    """
    Crea videos para cada subcarpeta en la carpeta JPEG.
    
    Args:
    - root_folder: Carpeta raíz que contiene las imágenes raw.
    - jpg_folder: Carpeta que contiene las imágenes convertidas a JPEG.
    - output_folder: Carpeta donde se guardarán los videos generados.
    - frame_rate: Tasa de cuadros por segundo para los videos.
    """
    for folder in os.listdir(jpg_folder):
        folder_path = os.path.join(jpg_folder, folder)
        os.makedirs(output_folder, exist_ok=True)
        if os.path.isdir(folder_path):
            output_video_path = os.path.join(output_folder, f"{folder}.avi")
            images_to_video(folder_path, output_video_path, frame_rate)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert RAW images to JPEG and create videos from them.")
    parser.add_argument('--raw_folder', type=str, required=True, help='Folder containing RAW images.')
    parser.add_argument('--jpg_folder', type=str, required=True, help='Folder to save converted JPEG images.')
    parser.add_argument('--output_video_folder', type=str, required=True, help='Folder to save generated videos.')
    parser.add_argument('--frame_rate', type=int, default=10, help='Frame rate for the generated videos.')
    
    args = parser.parse_args()
    
    # Convierte las imágenes raw a JPEG
    convert_raw_to_jpg(args.raw_folder, args.jpg_folder)
    
    # Crea videos para cada subcarpeta en la carpeta JPEG
    create_videos_for_folders(args.raw_folder, args.jpg_folder, args.output_video_folder, args.frame_rate)

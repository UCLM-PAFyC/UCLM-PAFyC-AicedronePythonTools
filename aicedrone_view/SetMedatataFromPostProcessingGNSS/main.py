import os
from PIL import Image
from exif import Image as ExifImage
from datetime import datetime
from pyubx2 import UBXReader

def parse_ubx_log(ubx_log_path):
    # Función para leer el archivo UBX y extraer los datos GPS
    gps_data = []
    with open(ubx_log_path, 'rb') as ubx_file:
        ubr = UBXReader(ubx_file)
        for (raw_data, parsed_data) in ubr:
            # Filtramos los mensajes de tipo NAV-PVT que contienen los datos de posición
            if parsed_data.identity == 'NAV-PVT':
                timestamp = datetime(parsed_data.year, parsed_data.month, parsed_data.day,
                                     parsed_data.hour, parsed_data.min, parsed_data.sec)
                gps_entry = {
                    'timestamp': timestamp,
                    'latitude': parsed_data.lat * 1e-7,
                    'longitude': parsed_data.lon * 1e-7
                }
                gps_data.append(gps_entry)
    return gps_data

def find_closest_gps_data(image_time, gps_data):
    # Función para encontrar el dato GPS más cercano en el tiempo a la marca de tiempo de la imagen
    closest_time_diff = float('inf')
    closest_data = None
    for entry in gps_data:
        time_diff = abs((entry['timestamp'] - image_time).total_seconds())
        if time_diff < closest_time_diff:
            closest_time_diff = time_diff
            closest_data = entry
    return closest_data

def insert_gps_to_image(image_path, gps_data):
    # Función para insertar los datos GPS en los metadatos EXIF de la imagen
    with open(image_path, 'rb') as img_file:
        img = ExifImage(img_file)
    
    if img.has_exif:
        # Convertimos las coordenadas GPS a formato requerido por EXIF
        img.gps_latitude = [(abs(gps_data['latitude']), 1), (0, 1), (0, 1)]
        img.gps_latitude_ref = 'N' if gps_data['latitude'] >= 0 else 'S'
        img.gps_longitude = [(abs(gps_data['longitude']), 1), (0, 1), (0, 1)]
        img.gps_longitude_ref = 'E' if gps_data['longitude'] >= 0 else 'W'
        
        # Guardamos los cambios en la imagen
        with open(image_path, 'wb') as new_img_file:
            new_img_file.write(img.get_file())

def synchronize_images_with_gps(image_folder, ubx_log_path):
    # Función principal para sincronizar las imágenes con los datos GPS
    gps_data = parse_ubx_log(ubx_log_path)
    
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('jpg', 'jpeg', 'png')):
            image_path = os.path.join(image_folder, filename)
            img = Image.open(image_path)
            exif_data = img._getexif()
            if exif_data and 36867 in exif_data:
                # Extraemos la marca de tiempo de la imagen
                image_time = datetime.strptime(exif_data[36867], '%Y:%m:%d %H:%M:%S')
                closest_gps = find_closest_gps_data(image_time, gps_data)
                if closest_gps:
                    # Insertamos los datos GPS en los metadatos EXIF de la imagen
                    insert_gps_to_image(image_path, closest_gps)
                    print(f"Inserted GPS data into {filename}")

# Uso
image_folder = 'ruta/a/la/carpeta/de/imagenes'  # Cambia esto a la ruta de tu carpeta de imágenes
ubx_log_path = 'ruta/al/log/de/gps.ubx'         # Cambia esto a la ruta de tu archivo UBX
synchronize_images_with_gps(image_folder, ubx_log_path)

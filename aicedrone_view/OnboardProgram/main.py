import cv2
import numpy as np
import threading
import struct
from ultralytics import YOLO
import PySpin
import time
import os
from datetime import datetime
import argparse
from sbus_controller import SBUSController

def parse_arguments():
    parser = argparse.ArgumentParser(description="FLIR Camera YOLO Detection with SBUS Control")
    parser.add_argument('--confidence_threshold', type=float, default=0.2, help='Confidence threshold for YOLO detection')
    parser.add_argument('--num_largest_polygons', type=int, default=3, help='Number of largest polygons to detect')
    parser.add_argument('--sbus_port', type=str, default='/dev/ttyUSB0', help='SBUS controller serial port')
    return parser.parse_args()

# Inicialización de la cámara FLIR
system = PySpin.System.GetInstance()
cam_list = system.GetCameras()

# Verificar si hay cámaras detectadas
num_cameras = cam_list.GetSize()
if num_cameras == 0:
    print("No cameras detected.")
    exit()

# Obtener la primera cámara
cam = cam_list.GetByIndex(0)
cam.Init()

# Configurar propiedades de la cámara
cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
cam.AcquisitionFrameRateEnable.SetValue(True)
cam.AcquisitionFrameRate.SetValue(10)  # Ajustar según sea necesario
cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)

# Imprimir información de la cámara opcionalmente
print("Camera information:")
print(f"Model: {cam.DeviceModelName.GetValue()}")
print(f"Serial number: {cam.DeviceSerialNumber.GetValue()}")

# Iniciar el flujo de adquisición de imágenes
print("Starting image acquisition stream...")
cam.BeginAcquisition()

# Definir la ruta de la carpeta para guardar imágenes raw
folder_name = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
folder_path = os.path.join("raw_images", folder_name)
os.makedirs(folder_path, exist_ok=True)  # Crear carpeta si no existe

# Inicializar el modelo YOLO
model = YOLO("./weights/rail_best.pt")

# Definir el escritor de video
output_video_path = 'output_yolo.avi'
width, height, fps = 1024, 1024, 10
writer = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'XVID'), fps, (width, height))

def convert_to_cv2_image(image):
    # Obtener datos de la imagen
    image_data = image.GetNDArray()

    # Convertir a RGB
    rgb_image = cv2.cvtColor(image_data, cv2.COLOR_BAYER_RG2RGB)

    return rgb_image

def detect_objects(image, model, confidence_threshold, num_largest_polygons):
    results = model.predict(image, False, retina_masks=False, conf=confidence_threshold)

    if num_largest_polygons > 0 and results is not None:
        all_polygons = []
        for result in results:
            if result.masks is None:
                return None
            for mask in result.masks:
                xy = mask.xy
                if xy is not None:
                    xy_array = np.array(xy)
                    all_polygons.append(xy_array)

        if all_polygons:
            aspect_ratios = []
            for poly in all_polygons:
                rect = cv2.minAreaRect(poly)
                if rect and rect[1][0] != 0 and rect[1][1] != 0:
                    aspect_ratios.append(rect[1][0] / rect[1][1])

            filtered_polygons = [poly for poly, aspect_ratio in zip(all_polygons, aspect_ratios) if 0.5 < aspect_ratio > 2.0]

            filtered_polygons.sort(key=lambda poly: cv2.contourArea(poly), reverse=True)

            largest_polygons = filtered_polygons[:num_largest_polygons]

            results = largest_polygons

    return results

def main():
    args = parse_arguments()

    # Inicializar el controlador SBUS
    sbus_controller = SBUSController(port=args.sbus_port)
    sbus_controller.connect_serial()

    # Bucle principal para la adquisición y procesamiento de imágenes
    while True:
        # Captura de imagen
        image_result = cam.GetNextImage()
        if image_result.IsIncomplete():
            print('Image incomplete with image status %d ...' % image_result.GetImageStatus())
            continue

        frame = convert_to_cv2_image(image_result)

        # Guardar imagen raw
        subseconds = datetime.now().strftime('%f')[:-3]
        filename = f"{folder_path}/raw_image_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{subseconds}.raw"
        image_result.Save(filename)

        # Detección de objetos y apuntamiento activo
        results = detect_objects(frame, model, args.confidence_threshold, args.num_largest_polygons)

        if results is not None:
            centroids = []
            for result in results:
                color = (0, 255, 0)
                cv2.polylines(frame, [result.astype(np.int32)], isClosed=True, color=color, thickness=10)
                # Calcular el centroide del resultado
                centroid = np.mean(result, axis=0).astype(int)
                centroids.append(centroid)

            if centroids:
                # Calcular el centroide medio de todos los objetos detectados
                mean_centroid = np.mean(centroids, axis=0).astype(int)
                sbus_x = mean_centroid[0] / frame.shape[1]
                sbus_y = mean_centroid[1] / frame.shape[0]
                sbus_controller.update_coordinates(sbus_x, sbus_y)

        writer.write(frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        image_result.Release()

    # Liberar recursos de la cámara y el sistema
    cam.DeInit()
    cam_list.Clear()
    system.ReleaseInstance()
    writer.release()
    sbus_controller.connect_serial()  # Desconectar el puerto serial

if __name__ == "__main__":
    main()

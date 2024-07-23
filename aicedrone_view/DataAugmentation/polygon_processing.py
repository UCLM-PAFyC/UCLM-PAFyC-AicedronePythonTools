import cv2
import numpy as np
import imgaug.augmenters as iaa
from imgaug.augmentables.polys import Polygon, PolygonsOnImage
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import MultiPoint

def get_polygon_area(polygon):
    """
    Calcula el área de un polígono.
    
    Args:
    - polygon: Objeto polígono de Shapely.
    
    Returns:
    - Área del polígono.
    """
    return polygon.area

def multiply_polygon_coordinates(polygon, shape):
    """
    Multiplica las coordenadas de un polígono por las dimensiones de una imagen.
    
    Args:
    - polygon: Objeto polígono de imgaug.
    - shape: Dimensiones de la imagen (altura, ancho).
    
    Returns:
    - Nuevo polígono con coordenadas multiplicadas.
    """
    # Recupera las coordenadas originales
    original_coords = polygon.exterior
    original_label = polygon.label

    # Multiplica cada coordenada por las dimensiones de la imagen
    modified_coords = [(coord[0] * shape[1], coord[1] * shape[0]) for coord in original_coords]

    # Crea un nuevo polígono con las coordenadas modificadas
    modified_polygon = Polygon(modified_coords, label=original_label)

    return modified_polygon

def divide_polygon_coordinates(polygon, shape):
    """
    Divide las coordenadas de un polígono por las dimensiones de una imagen.
    
    Args:
    - polygon: Objeto polígono de imgaug.
    - shape: Dimensiones de la imagen (altura, ancho).
    
    Returns:
    - Nuevo polígono con coordenadas divididas.
    """
    # Recupera las coordenadas originales
    original_coords = polygon.exterior
    original_label = polygon.label

    # Divide cada coordenada por las dimensiones de la imagen
    modified_coords = [(coord[0] / shape[1], coord[1] / shape[0]) for coord in original_coords]

    # Crea un nuevo polígono con las coordenadas modificadas
    modified_polygon = Polygon(modified_coords, label=original_label)

    return modified_polygon

def format_polygon_data(polygons):
    """
    Formatea los datos de polígonos en una representación de cadena.
    
    Args:
    - polygons: Lista de objetos polígonos de Shapely.
    
    Returns:
    - Lista de cadenas que representan los polígonos.
    """
    formatted_polygons = []
    for polygon in polygons:
        if polygon.area > 0:
            coords_list = map(lambda coord: f"{coord[0]} {coord[1]}", polygon.exterior)
            formatted_polygons.append(polygon.label + ' ' + ' '.join(coords_list))
    return formatted_polygons

def save_polygon_data(polygon_path, polygons):
    """
    Guarda los datos de polígonos en un archivo de texto.
    
    Args:
    - polygon_path: Ruta del archivo de texto.
    - polygons: Lista de objetos polígonos de imgaug.
    """
    polygons_to_save = []
    for polygon in polygons:
        intersection = calculate_polygon_intersection(polygon)
        if intersection:
            polygons_to_save.append(intersection)

    formatted_polygons = format_polygon_data(polygons_to_save)
    # Verifica si formatted_polygons está vacío
    if formatted_polygons:
        with open(polygon_path, 'w') as f:
            f.write('\n'.join(formatted_polygons))
    else:
        print("No polygons to save.")

def normalize_polygons(polygons, shape):
    """
    Normaliza las coordenadas de los polígonos a las dimensiones originales de la imagen.
    
    Args:
    - polygons: Lista de objetos polígonos de imgaug.
    - shape: Dimensiones de la imagen (altura, ancho).
    
    Returns:
    - Lista de polígonos normalizados.
    """
    normalized_polygons = []
    for polygon in polygons:
        normalized_polygon = divide_polygon_coordinates(polygon, shape)
        normalized_polygons.append(normalized_polygon)
    return normalized_polygons

def denormalize_polygons(polygons, shape):
    """
    Denormaliza las coordenadas de los polígonos a las dimensiones originales de la imagen.
    
    Args:
    - polygons: Lista de objetos polígonos de imgaug.
    - shape: Dimensiones de la imagen (altura, ancho).
    
    Returns:
    - Lista de polígonos denormalizados.
    """
    denormalized_polygons = []
    for polygon in polygons:
        denormalized_polygons.append(multiply_polygon_coordinates(polygon, shape))
    return denormalized_polygons

def load_polygon_data(polygon_path):
    """
    Carga los datos de polígonos desde un archivo de texto.
    
    Args:
    - polygon_path: Ruta del archivo de texto.
    
    Returns:
    - Lista de objetos polígonos de imgaug.
    """
    polygons = []
    with open(polygon_path, 'r') as f:
        for line in f:
            data = line.strip().split()
            class_id = int(data[0])
            points = [float(val) for val in data[1:]]
            polygon = Polygon([(points[i], points[i + 1]) for i in range(0, len(points), 2)], data[0])
            polygons.append(polygon)
    return polygons

def calculate_polygon_intersection(polygon):
    """
    Calcula la intersección entre un polígono dado y un polígono fijo.
    
    Args:
    - polygon: Objeto polígono de imgaug.
    
    Returns:
    - Polígono de intersección o None si no hay intersección.
    """
    # Definir el polígono fijo con vértices (0, 0), (1, 0), (1, 1) y (0, 1)
    fixed_polygon = ShapelyPolygon(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)))
    fixed_polygon = close_shapely_polygon(fixed_polygon)
    # Extraer coordenadas del polígono dado
    coords = polygon.exterior
    label = polygon.label

    # Crear un polígono de Shapely a partir del polígono de entrada
    input_polygon = ShapelyPolygon(coords)
    input_polygon = close_shapely_polygon(input_polygon)

    # Calcular el polígono de intersección
    intersection_polygon = input_polygon.intersection(fixed_polygon)

    # Verificar si el polígono de intersección no está vacío
    if not intersection_polygon.is_empty:
        # Extraer coordenadas del polígono de intersección
        intersection_coords = list(intersection_polygon.exterior.coords)

        # Crear un objeto Polygon con las coordenadas de intersección
        return Polygon(intersection_coords, label=label)
    else:
        return None

def close_shapely_polygon(polygon):
    """
    Cierra un polígono de Shapely si no está cerrado.
    
    Args:
    - polygon: Objeto polígono de Shapely.
    
    Returns:
    - Polígono cerrado.
    """
    polygon = get_simplest_polygon(polygon)
    if polygon.is_closed:
        return polygon
    coords = list(polygon.exterior.coords)
    closed_coords = coords + [coords[0]]
    closed_polygon = ShapelyPolygon(closed_coords)
    return closed_polygon

def get_simplest_polygon(polygon):
    """
    Obtiene el polígono más simple que envuelve un conjunto de puntos (envolvente convexa).
    
    Args:
    - polygon: Objeto polígono de Shapely.
    
    Returns:
    - Polígono más simple (envolvente convexa).
    """
    # Obtener las coordenadas del polígono de entrada
    coords = list(polygon.exterior.coords)

    # Crear un objeto MultiPoint a partir de las coordenadas
    points = MultiPoint(coords)

    # Calcular la envolvente convexa
    convex_hull = points.convex_hull

    # Convertir la envolvente convexa en un polígono (opcional)
    simplest_polygon = polygon.__class__(convex_hull)

    return simplest_polygon

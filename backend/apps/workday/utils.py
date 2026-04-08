import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Расстояние между двумя GPS-точками в метрах (формула гаверсинуса).
    """
    R = 6_371_000  # радиус Земли в метрах
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def point_in_polygon(lat: float, lng: float, polygon: list) -> bool:
    """
    Проверка, находится ли точка внутри полигона (ray-casting алгоритм).
    polygon — список [[lat, lng], ...].
    """
    if not polygon or len(polygon) < 3:
        return False

    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def check_proximity(lat: float, lng: float, project_object) -> dict:
    """
    Проверяет, находится ли точка (lat, lng) в зоне присутствия объекта.
    Возвращает dict с результатом проверки.
    """
    result = {"within_zone": False, "distance_m": None, "warning": None}

    obj_lat = float(project_object.latitude) if project_object.latitude else None
    obj_lng = float(project_object.longitude) if project_object.longitude else None

    if obj_lat is None or obj_lng is None:
        result["warning"] = "У объекта не заданы координаты"
        return result

    # Проверка по полигону (приоритет)
    if project_object.geofence_polygon and len(project_object.geofence_polygon) >= 3:
        result["within_zone"] = point_in_polygon(lat, lng, project_object.geofence_polygon)
        result["distance_m"] = round(haversine_distance(lat, lng, obj_lat, obj_lng))
        if not result["within_zone"]:
            result["warning"] = f"Вне геозоны объекта (расстояние {result['distance_m']} м)"
        return result

    # Проверка по радиусу
    distance = haversine_distance(lat, lng, obj_lat, obj_lng)
    result["distance_m"] = round(distance)
    radius = project_object.presence_radius or 500  # по умолчанию 500м
    result["within_zone"] = distance <= radius
    if not result["within_zone"]:
        result["warning"] = f"Вне радиуса присутствия ({result['distance_m']} м, допустимо {radius} м)"

    return result

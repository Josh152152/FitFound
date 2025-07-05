from geopy.geocoders import Nominatim
from geopy.distance import geodesic

geolocator = Nominatim(user_agent="app")

def get_location_coordinates(location):
    location_obj = geolocator.geocode(location)
    return (location_obj.latitude, location_obj.longitude)

def calculate_distance(coord1, coord2):
    return geodesic(coord1, coord2).km

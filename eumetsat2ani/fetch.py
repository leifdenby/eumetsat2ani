import eumdac
import datetime
import shutil
import requests
import time
from pathlib import Path

from satpy.resample import get_area_def

def pyresample_area_definition_to_boundary_polygon_wkt(area): 
    lons, lats = area.boundary().contour()
    pts_str = ', '.join(f'{lon} {lat}' for (lon, lat) in zip(lons, lats))
    return f"POLYGON (({pts_str}))"


def pyresample_area_definition_to_boundary_polygon_wkt(area): 
    lons, lats = area.boundary().contour()
    pts_str = ', '.join(f'{lon} {lat}' for (lon, lat) in zip(lons, lats))
    return f"POLYGON (({pts_str}))"

def download_source_files(area_definition, collection_name, t_start, t_end, data_root_path):
    token = eumdac.AccessToken()
    try:
        print(f"This token '{token}' expires {token.expiration}")
    except requests.exceptions.HTTPError as error:
        print(f"Unexpected error: {error}")

    # Maximum number of retries after HTTP 500 errors when connection EUMETSATs services
    datastore = eumdac.DataStore(token)
    selected_collection = datastore.get_collection(collection_name)
    print(f"{selected_collection} - {selected_collection.title}")

    # check search options
    search_options = selected_collection.search_options
    
    geometry = pyresample_area_definition_to_boundary_polygon_wkt(area=area_definition)

    # Retrieve datasets that match our filter
    products = selected_collection.search(
        dtstart=t_start,
        dtend=t_end,
        geo=geometry
    )
    
    local_filepaths = []
    
    for product in products:
        local_filepath = data_root_path / fsrc.name
        with product.open() as fsrc, open(local_filepath, mode='wb') as fdst:
            shutil.copyfileobj(fsrc, fdst)
            
            local_filepaths.append(local_filepath)
            

if __name__ == "__main__":
    collection_name = 'EO:EUM:DAT:MSG:HRSEVIRI'
    t_start = datetime.datetime(2015, 4, 14, 9, 0)
    t_end = t_start + datetime.timedelta(hours=4)
    area = "euro"
    
    root_data_path = Path("data")
    
    area_definition = get_area_def(area)

    filepaths = download_source_files(area_definition=area_definition, collection_name=collection_name, t_start=t_start, t_end=t_end, root_data_path=root_data_path)

import eumdac

import isodate
import datetime
import shutil
import requests
import time
from pathlib import Path
from loguru import logger
import itertools
import numpy as np

from satpy.resample import get_area_def


def pyresample_area_definition_to_boundary_polygon_wkt(area):
    lons, lats = area.boundary().contour()
    
    # use [min, max] combinations to get all 4 corners
    minmap_ops = [np.min, np.max]
    ops = itertools.product(minmap_ops, minmap_ops)
    corners = []
    for op in ops:
        lon_op, lat_op = op
        lonlat_corners = [lon_op(lons), lat_op(lats)]
        corners.append(lonlat_corners)
    
    lons, lats = zip(*corners)
    lons = list(lons) + [lons[0]]
    lats = list(lats) + [lats[0]]
    pts_str = ", ".join(f"{lon} {lat}" for (lon, lat) in zip(lons, lats))
    
    return f"POLYGON (({pts_str}))"


def download_source_files(
    api_key, api_secret, area_definition, collection_name, t_start, t_end, root_data_path
):
    token = eumdac.AccessToken((api_key, api_secret))
    try:
        print(f"This token '{token}' expires {token.expiration}")
    except requests.exceptions.HTTPError as error:
        print(f"Unexpected error: {error}")

    # Maximum number of retries after HTTP 500 errors when connection EUMETSATs services
    datastore = eumdac.DataStore(token)
    selected_collection = datastore.get_collection(collection_name)
    print(f"{selected_collection} - {selected_collection.title}")

    geometry = pyresample_area_definition_to_boundary_polygon_wkt(area=area_definition)

    # Retrieve datasets that match our filter
    products = selected_collection.search(dtstart=t_start, dtend=t_end, geo=geometry)

    local_filepaths = []

    root_data_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Found {len(products)} products")
    for product in products:
        prod_identifier = product.metadata['properties']['identifier']
        fp_local_guess = root_data_path / f"{prod_identifier}.zip"
        if fp_local_guess.exists():
            logger.info(f"Skipping {fp_local_guess} as it already exists")
            continue

        with product.open() as fsrc:
            local_filepath = root_data_path / fsrc.name
            if local_filepath.exists():
                logger.info(f"Skipping {local_filepath} as it already exists")
            else:
                with open(local_filepath, mode="wb") as fdst:
                    shutil.copyfileobj(fsrc, fdst)
                    logger.info(f"Downloaded {local_filepath}")
                    local_filepaths.append(local_filepath)
                

if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--api-key", type=str, required=True)
    argparser.add_argument("--api-secret", type=str, required=True)
    argparser.add_argument("--collection-name", type=str, default="EO:EUM:DAT:MSG:HRSEVIRI")
    argparser.add_argument("--t-start", type=isodate.parse_datetime, default="2015-04-14T09:00:00")
    argparser.add_argument("--t-end", type=isodate.parse_datetime, default="2015-04-14T13:00:00")
    argparser.add_argument("--area", type=str, default="euro")
    argparser.add_argument("--root-data-path", type=Path, default="data")
    args = argparser.parse_args()
    
    # load area definition from satpy
    area_definition = get_area_def(args.area)

    filepaths = download_source_files(
        api_key=args.api_key,
        api_secret=args.api_secret,
        area_definition=area_definition,
        collection_name=args.collection_name,
        root_data_path=args.root_data_path,
        t_start=args.t_start,
        t_end=args.t_end,
    )

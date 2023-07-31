import argparse
from pathlib import Path

import isodate
from loguru import logger
from satpy.resample import get_area_def

from .fetch import download_source_files
from .render import create_animation, render_scenes
from .utils import optional_debugging


class MyFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.MetavarTypeHelpFormatter
):
    pass


argparser = argparse.ArgumentParser(formatter_class=MyFormatter)
argparser.add_argument("--api-key", type=str, required=True, help="EUMETSAT API key")
argparser.add_argument(
    "--api-secret", type=str, required=True, help="EUMETSAT API secret"
)
argparser.add_argument(
    "--collection-name",
    type=str,
    default="EO:EUM:DAT:MSG:HRSEVIRI",
    help="EUMETSAT collection name",
)
argparser.add_argument(
    "--t-start",
    type=isodate.parse_datetime,
    default="2015-04-14T09:00:00",
    help="Start time",
)
argparser.add_argument(
    "--t-end",
    type=isodate.parse_datetime,
    default="2015-04-14T13:00:00",
    help="End time",
)
argparser.add_argument(
    "--area",
    type=str,
    default="euro",
    help="Area definition (using satpy's inbuilt area definitions)",
)
argparser.add_argument(
    "--root-data-path",
    type=Path,
    default="data",
    help="Root path to store downloaded data",
)
argparser.add_argument(
    "--product", type=str, default="natural_color", help="Satpy product to render"
)
argparser.add_argument(
    "--launch-ipdb-on-error", action="store_true", help="Launch ipdb on error"
)
argparser.add_argument(
    "--frame-duration",
    type=float,
    default=0.5,
    help="Duration of each frame in seconds",
)

args = argparser.parse_args()

name_parts = [
    args.product,
    args.collection_name.replace(":", "_"),
    args.t_start.isoformat().replace(":", "-"),
    args.t_end.isoformat().replace(":", "-"),
    "gif",
]

fp_animation_out = args.root_data_path / ".".join(name_parts)

with optional_debugging(with_debugger=args.launch_ipdb_on_error):
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

    logger.info(f"Rendering {args.product} for {len(filepaths)} scenes")
    scene_images_filepaths = render_scenes(
        source_filepaths=filepaths,
        collection_source=args.collection_name,
        satpy_product=args.product,
        area_definition=area_definition,
    )

    create_animation(
        filepaths_images=scene_images_filepaths,
        fp_out=fp_animation_out,
        frame_duration=args.frame_duration,
    )

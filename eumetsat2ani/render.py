import warnings
import zipfile
from pathlib import Path

import imageio
from loguru import logger
from PIL import ImageDraw, ImageFont
from satpy import Scene
from satpy.writers import get_enhanced_image

SATPY_READERS_BY_COLLECTION = {
    "EO:EUM:DAT:MSG:HRSEVIRI": "seviri_l1b_native",
}


def unzip_scene_files(filepath):
    with zipfile.ZipFile(filepath, "r") as zip_ref:
        dst_path = Path(filepath).parent
        files = zip_ref.namelist()

        if any(not (dst_path / fp).exists() for fp in files):
            zip_ref.extractall(dst_path)
            # get files within the zip file
            logger.info(f"Unzipped {', '.join(fp for fp in files)} to {dst_path}")

    return [dst_path / f for f in files]


def add_image_text(image, text, img_fraction=0.6):
    """
    img_fraction: portion of image width you want text width to be
    """
    font_path = "Pillow/Tests/fonts/FreeMono.ttf"
    fontsize = 1

    def _load_font(fontsize):
        return ImageFont.truetype(font_path, fontsize)

    font = _load_font(fontsize)
    draw = ImageDraw.Draw(image)

    # support Pillow >= 10.0.0
    if hasattr(draw, "textsize"):

        def get_textbbox(text):
            return draw.textsize(text, font=font)

    else:

        def get_textbbox(text):
            (left, top, right, bottom) = draw.textbbox(
                xy=(50, 50), text=text, font=font
            )
            width, height = right - left, bottom - top
            return width, height

    while get_textbbox(text)[0] < img_fraction * image.size[0]:
        # iterate until the text size is just larger than the criteria
        fontsize += 1
        font = _load_font(fontsize)

    # optionally de-increment to be sure it is less than criteria
    fontsize -= 1
    font = _load_font(fontsize)

    def render_text(posn, _text, pad=6, loc="upper left"):
        _, height = get_textbbox(_text)
        if loc == "upper left":
            position = (posn[0] + pad, posn[1] + pad // 2)
        elif loc == "lower left":
            position = (posn[0] + pad, posn[1] - height - pad)
        else:
            raise NotImplementedError(f"loc {loc} not implemented")
        left, top, right, bottom = draw.textbbox(position, _text, font=font)
        draw.rectangle((left - pad, top - pad, right + pad, bottom + pad), fill="black")
        draw.text(position, _text, font=font, fill="white")

    render_text((0, 0), text)
    render_text((0, image.size[1]), "made with eumetsat2ani", loc="lower left")


def render_scenes(source_filepaths, collection_source, satpy_product, area_definition):
    satpy_reader = SATPY_READERS_BY_COLLECTION.get(collection_source)
    if satpy_reader is None:
        raise NotImplementedError(
            f"No satpy reader defined for EUMETSAT collection {collection_source}"
        )

    source_filepaths_unzipped = []

    for fp_source_zipfile in source_filepaths:
        fps_scene_unzipped_files = unzip_scene_files(fp_source_zipfile)

        # find first file which has .net file extension
        fp_scene_unzipped = next(
            (fp for fp in fps_scene_unzipped_files if fp.suffix == ".nat"), None
        )

        if fp_scene_unzipped is None:
            raise RuntimeError(
                f"Could not find .nat file in unzipped contents of {fp_source_zipfile}"
            )

        source_filepaths_unzipped.append(fp_scene_unzipped)

    filepaths_images = []

    for fp_scene_unzipped in source_filepaths_unzipped:
        fp_img = Path(fp_scene_unzipped.parent) / f"{fp_scene_unzipped.stem}.png"
        filepaths_images.append(fp_img)
        if fp_img.exists():
            logger.info(f"Skipping {fp_img} as it already exists")
            continue

        scn = Scene(filenames=[fp_scene_unzipped], reader="seviri_l1b_native")

        with warnings.catch_warnings():
            # suppress warnings about missing values from dask and rounding
            # errors in time that satpy gives
            warnings.simplefilter("ignore")
            # supress dask runtimewarnings
            warnings.filterwarnings("ignore", category=RuntimeWarning, module="dask")

            scn.load([satpy_product])
            local_scn = scn.resample(area_definition)
            img = get_enhanced_image(
                local_scn[satpy_product].squeeze(), overlay=None
            ).pil_image()

        image_caption = f"{collection_source} {satpy_product}\n{scn.start_time.isoformat()} (to {scn.end_time.time().isoformat()})"

        add_image_text(image=img, text=image_caption)

        img.save(fp_img)
        logger.info(f"Saved {fp_img}")

    return filepaths_images


def create_animation(filepaths_images, fp_out, frame_duration):
    with imageio.get_writer(
        fp_out, mode="I", duration=frame_duration * 1000, loop=0
    ) as writer:
        for fp in filepaths_images:
            image = imageio.imread(fp)
            writer.append_data(image)

    logger.info(f"Saved animation to {fp_out}")

#!/usr/bin/env python3
"""Download and resize AVAMET camera images referenced by the demo CSV.

Run from this directory with:
    python download_avamet_images.py --dry-run
    python download_avamet_images.py
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parent
DEMO_CSV = MODULE_ROOT / "demo" / "avamet.reading.csv"
IMAGE_DIRECTORY = MODULE_ROOT / "demo" / "images"
OVERLAY_XML = MODULE_ROOT / "demo" / "avamet_images.xml"

IMAGE_ORIGIN = "http://10.100.22.106"
IMAGE_PATH_PREFIX = "/historic/"
IMAGE_SIZE = (320, 240)
JPEG_QUALITY = 55
REQUEST_TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
RECENT_DAY_COUNT = 3
MAX_READINGS_PER_DAY = 5

RECORD_ID_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
IMAGE_FILENAME_PATTERN = re.compile(
    r"^(?P<stamp>\d{8}_\d{6})-webcam(?P<camera>[12])\.jpg$"
)


@dataclass(frozen=True)
class DemoReading:
    external_id: str
    timestamp: datetime
    image_fields: tuple[tuple[str, str], ...]


class DownloadError(Exception):
    """Raised when an image cannot be fetched or safely processed."""


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        raise urllib.error.HTTPError(
            request.full_url,
            code,
            "Image-server redirects are disabled",
            headers,
            file_pointer,
        )


def read_demo_csv(csv_path: Path) -> list[DemoReading]:
    readings = []
    seen_ids = set()
    required_columns = {
        "id",
        "live_updated",
        "webcam1_file",
        "webcam2_file",
    }

    try:
        stream = csv_path.open(encoding="utf-8-sig", newline="")
    except OSError as error:
        raise DownloadError(f"Cannot read demo CSV {csv_path}: {error}") from error

    with stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
            raise DownloadError(
                "The demo CSV must contain id, live_updated, webcam1_file, and webcam2_file."
            )

        for line_number, row in enumerate(reader, start=2):
            external_id = (row.get("id") or "").strip()
            if not RECORD_ID_PATTERN.fullmatch(external_id):
                raise DownloadError(f"Invalid Odoo external ID on CSV line {line_number}.")
            if external_id in seen_ids:
                raise DownloadError(f"Duplicate Odoo external ID {external_id!r}.")
            seen_ids.add(external_id)

            try:
                timestamp = datetime.strptime(
                    (row.get("live_updated") or "").strip(), "%Y-%m-%d %H:%M:%S"
                )
            except ValueError as error:
                raise DownloadError(
                    f"Invalid observation timestamp on CSV line {line_number}."
                ) from error

            image_fields = []
            for camera, field_name in ((1, "webcam1_file"), (2, "webcam2_file")):
                filename = (row.get(field_name) or "").strip()
                if not filename:
                    continue
                match = IMAGE_FILENAME_PATTERN.fullmatch(filename)
                if not match or int(match.group("camera")) != camera:
                    raise DownloadError(
                        f"Unexpected camera filename on CSV line {line_number}: "
                        f"{filename!r}."
                    )
                try:
                    datetime.strptime(match.group("stamp"), "%Y%m%d_%H%M%S")
                except ValueError as error:
                    raise DownloadError(
                        f"Invalid camera timestamp in filename {filename!r}."
                    ) from error
                image_fields.append(
                    ("image_%d" % camera, filename)
                )

            readings.append(
                DemoReading(
                    external_id=external_id,
                    timestamp=timestamp,
                    image_fields=tuple(image_fields),
                )
            )

    return readings


def select_recent_readings(readings: list[DemoReading]) -> list[DemoReading]:
    recent_days = sorted({reading.timestamp.date() for reading in readings}, reverse=True)[
        :RECENT_DAY_COUNT
    ]
    selected_per_day = {day: 0 for day in recent_days}
    selected = []

    for reading in sorted(
        readings,
        key=lambda item: (item.timestamp, item.external_id),
        reverse=True,
    ):
        day = reading.timestamp.date()
        if day in selected_per_day and selected_per_day[day] < MAX_READINGS_PER_DAY:
            selected.append(reading)
            selected_per_day[day] += 1
    return selected


def image_url(filename: str) -> str:
    match = IMAGE_FILENAME_PATTERN.fullmatch(filename)
    if not match:
        raise DownloadError(f"Invalid image filename: {filename!r}.")
    try:
        datetime.strptime(match.group("stamp"), "%Y%m%d_%H%M%S")
    except ValueError as error:
        raise DownloadError(f"Invalid camera timestamp in filename {filename!r}.") from error

    quoted_name = urllib.parse.quote(filename, safe="")
    url = f"{IMAGE_ORIGIN}{IMAGE_PATH_PREFIX}{quoted_name}"
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "10.100.22.106"
        or parsed.port not in (None, 80)
        or parsed.path != f"{IMAGE_PATH_PREFIX}{filename}"
        or parsed.query
        or parsed.fragment
    ):
        raise DownloadError("Refusing to request an image outside the configured AVAMET host.")
    return url


def image_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPHandler(),
        RejectRedirects(),
    )


def fetch_image(
    filename: str,
    opener: urllib.request.OpenerDirector,
) -> bytes:
    request = urllib.request.Request(
        image_url(filename),
        headers={"Accept": "image/jpeg"},
    )

    try:
        with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get_content_type()
            if content_type not in ("image/jpeg", "image/pjpeg", "application/octet-stream"):
                raise DownloadError(
                    f"Unexpected content type for {filename}: {content_type}."
                )
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > MAX_RESPONSE_BYTES:
                        raise DownloadError(f"Image exceeds the size limit: {filename}.")
                except ValueError as error:
                    raise DownloadError(
                        f"Invalid Content-Length for {filename}."
                    ) from error
            content = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise DownloadError(
            f"Image server returned HTTP {error.code} for {filename}."
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise DownloadError(f"Could not download {filename}: {error}") from error

    if len(content) > MAX_RESPONSE_BYTES:
        raise DownloadError(f"Image exceeds the size limit: {filename}.")
    return content


def resize_jpeg(content: bytes, image_module, image_ops_module) -> bytes:
    try:
        with image_module.open(BytesIO(content)) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise DownloadError("Source image exceeds the pixel-count limit.")
            source.load()
            image = image_ops_module.exif_transpose(source)
            if "A" in image.getbands():
                rgba = image.convert("RGBA")
                background = image_module.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

            image.thumbnail(IMAGE_SIZE, image_module.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return output.getvalue()
    except DownloadError:
        raise
    except (OSError, ValueError, image_module.DecompressionBombError) as error:
        raise DownloadError(f"Source image is not a valid, safe JPEG: {error}") from error


def is_ready_jpeg(path: Path, image_module) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        with image_module.open(path) as image:
            image_format = image.format
            width, height = image.size
            image.verify()
        return (
            image_format == "JPEG"
            and width <= IMAGE_SIZE[0]
            and height <= IMAGE_SIZE[1]
        )
    except (OSError, ValueError, image_module.DecompressionBombError):
        return False


def write_atomic(path: Path, content: bytes) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".avamet-", suffix=".tmp", dir=path.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
        os.replace(temporary_path, path)
    except OSError as error:
        raise DownloadError(f"Cannot write {path}: {error}") from error
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def write_overlay(
    readings: list[DemoReading],
    image_directory: Path,
    overlay_path: Path,
) -> int:
    root = ET.Element("odoo")
    data = ET.SubElement(root, "data", {"noupdate": "0"})
    updated_records = 0

    for reading in readings:
        existing_images = []
        for field_name, filename in reading.image_fields:
            image_path = image_directory / filename
            if image_path.is_symlink():
                raise DownloadError(f"Refusing a symlink image path: {image_path}")
            if image_path.is_file():
                relative_path = image_path.relative_to(MODULE_ROOT).as_posix()
                existing_images.append((field_name, relative_path))
        if not existing_images:
            continue

        data.append(
            ET.Comment(
                "%s observation %s"
                % (reading.external_id, reading.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            )
        )
        record = ET.SubElement(
            data,
            "record",
            {
                "id": reading.external_id,
                "model": "avamet.reading",
            },
        )
        for field_name, relative_path in existing_images:
            ET.SubElement(
                record,
                "field",
                {"name": field_name, "type": "base64", "file": relative_path},
            )
        updated_records += 1

    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    output = BytesIO()
    tree.write(output, encoding="utf-8", xml_declaration=True)
    write_atomic(overlay_path, output.getvalue())
    return updated_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download the AVAMET camera files referenced by the demo CSV, resize "
            "them to fit 320x240, and generate an Odoo image overlay."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the demo CSV and show the planned work without network or file changes",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        all_readings = read_demo_csv(DEMO_CSV)
        readings = select_recent_readings(all_readings)
        filenames = {
            filename
            for reading in readings
            for _, filename in reading.image_fields
        }
        if args.dry_run:
            selected_days = sorted(
                {reading.timestamp.date() for reading in readings}, reverse=True
            )
            print(f"Demo records checked: {len(all_readings)}")
            print(
                f"Recent records selected: {len(readings)} "
                f"(up to {MAX_READINGS_PER_DAY} per day for {RECENT_DAY_COUNT} days)"
            )
            print("Selected dates: " + ", ".join(day.isoformat() for day in selected_days))
            print(f"Unique camera images planned: {len(filenames)} (maximum 30)")
            print(f"Image output directory: {IMAGE_DIRECTORY}")
            print(f"XML overlay: {OVERLAY_XML}")
            print("Dry run: no network requests and no files changed.")
            return 0

        try:
            from PIL import Image, ImageOps
        except ImportError as error:
            raise DownloadError(
                "Pillow is required to resize images. Install it with "
                "`python -m pip install Pillow` and rerun this script."
            ) from error

        opener = image_opener()

        resolved_module = MODULE_ROOT.resolve()
        IMAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        resolved_image_directory = IMAGE_DIRECTORY.resolve()
        try:
            resolved_image_directory.relative_to(resolved_module)
        except ValueError as error:
            raise DownloadError("Image output directory must remain inside this module.") from error

        total = len(filenames)
        downloaded = 0
        cached = 0
        for index, filename in enumerate(sorted(filenames), start=1):
            image_path = IMAGE_DIRECTORY / filename
            if image_path.is_symlink():
                raise DownloadError(f"Refusing a symlink image path: {image_path}")
            if is_ready_jpeg(image_path, Image):
                cached += 1
                continue
            raw_image = fetch_image(filename, opener)
            resized_image = resize_jpeg(raw_image, Image, ImageOps)
            write_atomic(image_path, resized_image)
            downloaded += 1
            if index % 100 == 0 or index == total:
                print(f"Processed {index}/{total} image files...")

        updated_records = write_overlay(readings, IMAGE_DIRECTORY, OVERLAY_XML)
        print(
            f"Done: {downloaded} downloaded, {cached} already optimized, "
            f"{updated_records} demo readings linked to images."
        )
        return 0
    except DownloadError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

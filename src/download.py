"""Download raw Airbnb data files for a city defined in config/city_config.yaml."""

import argparse
import gzip
import logging
import shutil
import time
from datetime import date
from pathlib import Path

import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "city_config.yaml"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
LOG_DIR = PROJECT_ROOT / "logs"

MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 30
CHUNK_SIZE = 8192

logger = logging.getLogger("download")


def setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"download_{date.today().isoformat()}.log"

    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return log_path


def load_city_config(config_path: Path = CONFIG_PATH) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if "city" not in config or "urls" not in config:
        raise ValueError(f"Config at {config_path} must contain 'city' and 'urls' keys")

    return config


def download_file(url: str, dest_path: Path) -> Path:
    """Download url to dest_path, retrying with exponential backoff on failure."""
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"START download attempt {attempt}/{MAX_RETRIES}: {url}")
            with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)

            file_size = dest_path.stat().st_size
            logger.info(f"SUCCESS downloaded {dest_path.name} ({file_size} bytes) from {url}")
            return dest_path

        except (requests.RequestException, OSError) as exc:
            last_error = exc
            logger.warning(f"FAILURE attempt {attempt}/{MAX_RETRIES} for {url}: {exc}")
            if attempt < MAX_RETRIES:
                wait_seconds = BACKOFF_BASE_SECONDS ** attempt
                logger.info(f"Retrying in {wait_seconds}s...")
                time.sleep(wait_seconds)

    logger.error(f"FAILURE exhausted {MAX_RETRIES} attempts for {url}: {last_error}")
    raise RuntimeError(f"Failed to download {url} after {MAX_RETRIES} attempts") from last_error


def decompress_gz(gz_path: Path) -> Path:
    """Decompress a .gz file next to itself and remove the .gz afterward."""
    decompressed_path = gz_path.with_suffix("")

    logger.info(f"START decompress {gz_path.name}")
    try:
        with gzip.open(gz_path, "rb") as f_in, open(decompressed_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    except OSError as exc:
        logger.error(f"FAILURE decompress {gz_path.name}: {exc}")
        raise

    file_size = decompressed_path.stat().st_size
    logger.info(f"SUCCESS decompressed {gz_path.name} -> {decompressed_path.name} ({file_size} bytes)")

    gz_path.unlink()
    return decompressed_path


def download_city_data(city: str, urls: dict) -> None:
    city_dir = RAW_DATA_DIR / city
    city_dir.mkdir(parents=True, exist_ok=True)

    failures = []

    for name, url in urls.items():
        filename = url.rsplit("/", 1)[-1]
        dest_path = city_dir / filename

        try:
            downloaded_path = download_file(url, dest_path)
        except RuntimeError as exc:
            logger.error(f"Skipping {name}: {exc}")
            failures.append(name)
            continue

        if downloaded_path.suffix == ".gz":
            try:
                decompress_gz(downloaded_path)
            except OSError:
                failures.append(name)

    if failures:
        logger.error(f"Completed with failures for {city}: {failures}")
    else:
        logger.info(f"All files downloaded successfully for {city}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download raw Airbnb data for a city.")
    parser.add_argument(
        "--city",
        required=True,
        help="City name to download data for (must match 'city' in config/city_config.yaml)",
    )
    args = parser.parse_args()

    log_path = setup_logging()
    logger.info(f"Logging to {log_path}")

    config = load_city_config()
    configured_city = config["city"]

    if args.city.lower() != configured_city.lower():
        logger.error(
            f"Requested city '{args.city}' does not match configured city '{configured_city}'"
        )
        raise SystemExit(1)

    download_city_data(configured_city, config["urls"])


if __name__ == "__main__":
    main()

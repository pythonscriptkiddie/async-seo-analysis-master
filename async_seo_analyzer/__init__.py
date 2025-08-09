#!/usr/bin/env python3
from importlib import metadata

try:
    __version__ = metadata.version("async-seo-analyzer")
except metadata.PackageNotFoundError:
    __version__ = "0.0.0-unknown"

from .analyzer import analyze  # re-export
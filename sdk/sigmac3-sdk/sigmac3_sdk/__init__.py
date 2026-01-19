"""
Sigma SDK
=========

Core schemas, templates, geo utilities, and lightweight clients used across the
Sigma stack. This package is the single source of truth for C4ISR schemas and
transport helpers; transports never embed semantics.
"""

from sigmac3_sdk.core import (
    CabalUnit,
    ExternalFormation,
    TemplateLibrary,
    UNIT_CATEGORY_LABELS,
    UNIT_CATEGORY_NAMES,
    UNIT_SIZE_LABELS,
    UNIT_SIZE_SHORT,
    TaskKind,
    TaskPriority,
    TaskStatus,
)
from sigmac3_sdk.clients.db import DBClient
from sigmac3_sdk.geo import GPSposition, PosVector, gps_distance_m, gps_to_vector, vector_to_gps

__all__ = [
    "CabalUnit",
    "ExternalFormation",
    "TemplateLibrary",
    "UNIT_CATEGORY_LABELS",
    "UNIT_CATEGORY_NAMES",
    "UNIT_SIZE_LABELS",
    "UNIT_SIZE_SHORT",
    "TaskKind",
    "TaskPriority",
    "TaskStatus",
    "DBClient",
    "GPSposition",
    "PosVector",
    "gps_distance_m",
    "gps_to_vector",
    "vector_to_gps",
]

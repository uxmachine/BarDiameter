"""Utility functions for robust diameter statistics.

This module is pure Python so it can be tested outside Rhino.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median
from typing import Iterable, List


@dataclass(frozen=True)
class DiameterSummary:
    estimated_diameter_mm: float
    iqr_mm: float
    valid_station_count: int
    total_station_count: int
    invalid_ratio: float
    confidence: str


def equivalent_diameter_from_area(area_mm2: float) -> float:
    """Compute equivalent circle diameter from a cross-sectional area."""
    if area_mm2 <= 0:
        raise ValueError("area_mm2 must be > 0")
    return math.sqrt((4.0 * area_mm2) / math.pi)


def percentile(sorted_values: List[float], p: float) -> float:
    """Linear-interpolated percentile for sorted values."""
    if not sorted_values:
        raise ValueError("sorted_values cannot be empty")
    if p < 0 or p > 100:
        raise ValueError("p must be in [0, 100]")

    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (len(sorted_values) - 1) * (p / 100.0)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return sorted_values[low]

    weight = rank - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def trimmed(values: Iterable[float], trim_fraction: float) -> List[float]:
    """Drop low/high extremes by a symmetric fraction."""
    seq = sorted(values)
    if not seq:
        return []

    if trim_fraction < 0 or trim_fraction >= 0.5:
        raise ValueError("trim_fraction must be in [0, 0.5)")

    k = int(len(seq) * trim_fraction)
    if k == 0:
        return seq
    return seq[k:-k] if len(seq) > (2 * k) else []


def summarize_diameters(
    valid_diameters_mm: Iterable[float],
    total_station_count: int,
    *,
    trim_fraction: float = 0.1,
    low_confidence_invalid_ratio: float = 0.3,
) -> DiameterSummary:
    """Summarize station diameters into a single robust estimate."""
    valid = sorted(valid_diameters_mm)
    valid_count = len(valid)
    if total_station_count <= 0:
        raise ValueError("total_station_count must be > 0")
    if valid_count == 0:
        return DiameterSummary(
            estimated_diameter_mm=float("nan"),
            iqr_mm=float("nan"),
            valid_station_count=0,
            total_station_count=total_station_count,
            invalid_ratio=1.0,
            confidence="Low",
        )

    kept = trimmed(valid, trim_fraction)
    if not kept:
        kept = valid

    q1 = percentile(valid, 25)
    q3 = percentile(valid, 75)
    invalid_ratio = max(0.0, (total_station_count - valid_count) / float(total_station_count))
    confidence = "Low" if invalid_ratio > low_confidence_invalid_ratio else "High"

    return DiameterSummary(
        estimated_diameter_mm=median(kept),
        iqr_mm=(q3 - q1),
        valid_station_count=valid_count,
        total_station_count=total_station_count,
        invalid_ratio=invalid_ratio,
        confidence=confidence,
    )

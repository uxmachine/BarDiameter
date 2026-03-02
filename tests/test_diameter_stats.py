import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from diameter_stats import equivalent_diameter_from_area, summarize_diameters


def test_equivalent_diameter_from_area_unit_circle_area():
    area = math.pi * (10.0 ** 2)
    diameter = equivalent_diameter_from_area(area)
    assert abs(diameter - 20.0) < 1e-9


def test_summarize_diameters_high_confidence():
    summary = summarize_diameters([19.5, 20.1, 20.0, 19.9], total_station_count=5)
    assert summary.confidence == "High"
    assert 19.5 <= summary.estimated_diameter_mm <= 20.1


def test_summarize_diameters_low_confidence():
    summary = summarize_diameters([20.0], total_station_count=5, low_confidence_invalid_ratio=0.3)
    assert summary.confidence == "Low"
    assert summary.invalid_ratio == 0.8

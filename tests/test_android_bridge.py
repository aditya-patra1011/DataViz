import json

import bridge
import pytest

from core import config, ingest


def sales_bytes() -> bytes:
    return (config.SAMPLES_DIR / "sales.csv").read_bytes()


def test_bridge_returns_plotly_json():
    text = bridge.chart_from_file(
        sales_bytes(), "sales.csv", "Bar", "Month", "Sales", "Region", dark=True
    )
    figure = json.loads(text)
    assert len(figure["data"]) == 4
    assert figure["layout"]["title"]["text"] == "Sales by Month and Region"


def test_bridge_works_without_a_colour_column():
    text = bridge.chart_from_file(
        sales_bytes(), "sales.csv", "Bar", "Month", "Sales", None, dark=False
    )
    assert len(json.loads(text)["data"]) == 1


def test_bridge_passes_on_data_problems_as_errors():
    with pytest.raises(ingest.IngestError):
        bridge.chart_from_file(b"", "empty.csv", "Bar", "a", "b", None, dark=False)

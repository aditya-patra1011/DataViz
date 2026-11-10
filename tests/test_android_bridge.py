import json

import bridge
import pytest

from core import charts, config


@pytest.fixture(autouse=True)
def fresh_session():
    bridge.session = bridge.Session()


def call(function, *args) -> dict:
    return json.loads(function(*args))


def load_sample(name: str = "students.csv") -> dict:
    content = (config.SAMPLES_DIR / name).read_bytes()
    return call(bridge.load_file, content, name, f"sample: {name}")


def test_snapshot_before_loading():
    assert call(bridge.snapshot) == {"ok": True, "loaded": False, "message": ""}


def test_load_file_returns_the_report():
    reply = load_sample()
    assert reply["ok"]
    assert reply["summary"]["rows"] == 20
    assert reply["summary"]["missing cells"] == 2
    assert reply["source"] == "sample: students.csv"
    assert len(reply["preview"]["rows"]) == 20


def test_preview_is_plain_text_with_blanks_for_missing_values():
    science = load_sample()["preview"]
    column = science["columns"].index("Science")
    assert science["rows"][3][column] == ""
    assert all(isinstance(cell, str) for row in science["rows"] for cell in row)


def test_empty_file_is_a_friendly_error():
    reply = call(bridge.load_file, b"", "empty.csv", "empty.csv")
    assert reply["ok"] is False
    assert reply["error"]


def test_load_text():
    reply = call(bridge.load_text, "Fruit,Count\nApple,10\nMango,25")
    assert reply["summary"]["rows"] == 2
    assert reply["source"] == "pasted data"


def test_load_table_keeps_filled_rows_and_makes_numbers():
    table = json.dumps({"columns": ["Label", "Value"], "rows": [["Jan", "1,200"], ["", ""]]})
    reply = call(bridge.load_table, table)
    assert reply["summary"]["rows"] == 1
    assert bridge.session.df["Value"].tolist() == [1200.0]


def test_load_table_rejects_text_in_a_number_column():
    table = json.dumps({"columns": ["Label", "Value"], "rows": [["Jan", "lots"]]})
    reply = call(bridge.load_table, table)
    assert reply == {"ok": False, "error": "'lots' in column 'Value' is not a number."}


def test_fix_updates_the_data_and_the_log():
    load_sample()
    reply = call(bridge.fix, "missing", "Science", "median", None)
    assert reply["summary"]["missing cells"] == 1
    assert len(reply["log"]) == 1
    assert reply["message"] == reply["log"][0]


def test_fix_with_a_problem_changes_nothing():
    load_sample()
    before = bridge.session.df
    reply = call(bridge.fix, "duplicates", None, None, None)
    assert reply["ok"] is False
    assert bridge.session.df is before


def test_outlier_limits_are_reported():
    assert set(load_sample()["limits"]) == {"StudyHours", "Science", "Attendance"}


def test_convert_makes_dates():
    load_sample("sales.csv")
    assert call(bridge.fix, "convert", None, None, None)["ok"]
    assert bridge.session.df["Month"].dtype.kind == "M"


def test_reset_restores_the_original():
    load_sample()
    call(bridge.fix, "drop", "Name", None, None)
    reply = call(bridge.reset)
    assert reply["summary"]["columns"] == 7
    assert reply["log"] == []


def test_loading_new_data_clears_the_log():
    load_sample()
    call(bridge.fix, "drop", "Name", None, None)
    assert load_sample("sales.csv")["log"] == []


def test_chart_options_follow_the_data():
    load_sample("sales.csv")
    options = call(bridge.chart_options, "Bar", "Region", None)
    assert options["x"][0] == "Month"
    assert options["y"] == ["Sales", "Units", "Profit"]
    assert options["color"] == ["Region"]
    assert options["repeats"] is True
    assert options["stacks"] is False


def test_chart_options_turn_on_stacking_with_a_colour():
    load_sample("sales.csv")
    assert call(bridge.chart_options, "Bar", "Month", "Region")["stacks"] is True


def test_chart_options_only_offer_bins_for_numbers():
    load_sample("students.csv")
    assert call(bridge.chart_options, "Histogram", "Math", None)["bins"] is True
    assert call(bridge.chart_options, "Histogram", "Section", None)["bins"] is False


def test_draw_returns_figure_notes_and_data():
    load_sample("sales.csv")
    reply = call(
        bridge.draw, "Bar", "Month", "Sales", "Region", "sum", True, None, None, True
    )
    assert len(json.loads(reply["figure"])["data"]) == 4
    assert reply["data"]["columns"] == ["Month", "Region", "Sales"]


@pytest.mark.parametrize("chart", list(charts.CHARTS))
def test_every_chart_type_draws_from_its_own_options(chart):
    load_sample("students.csv")
    options = call(bridge.chart_options, chart, None, None)
    x = options["x"][0] if options["x"] else None
    y = next((column for column in options["y"] if column != x), None)
    reply = call(bridge.draw, chart, x, y, None, "sum", True, None, "", False)
    assert reply["ok"], reply.get("error")
    assert json.loads(reply["figure"])["data"]


def test_draw_reports_problems():
    call(bridge.load_text, "name,score\nA,5\nB,-1")
    reply = call(bridge.draw, "Pie", "name", "score", None, "sum", True, None, "", False)
    assert reply["ok"] is False
    assert "negative" in reply["error"]

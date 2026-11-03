import pytest
from streamlit.testing.v1 import AppTest

from core import charts, config, ingest

PAGE = str(config.ROOT_DIR / "app" / "pages" / "3_Visualize.py")


def open_page(sample: str | None = "students.csv") -> AppTest:
    page = AppTest.from_file(PAGE, default_timeout=30)
    if sample:
        page.session_state["df"] = ingest.load_sample(sample)
    return page.run()


def test_page_asks_for_data_when_none_is_loaded():
    page = open_page(sample=None)
    assert not page.exception
    assert "No dataset loaded" in page.info[0].value


@pytest.mark.parametrize("sample", ["sales.csv", "students.csv", "weather.csv"])
@pytest.mark.parametrize("chart", list(charts.CHARTS))
def test_every_chart_type_draws_without_errors(sample, chart):
    page = open_page(sample)
    page.selectbox[0].select(chart).run()
    assert not page.exception
    assert not page.error
    assert page.get("plotly_chart")


def test_problem_with_the_data_shows_a_message_not_a_crash():
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["df"] = ingest.parse_text("name,score\nA,5\nB,-1")
    page.run()
    page.selectbox[0].select("Pie").run()
    assert not page.exception
    assert "negative" in page.error[0].value


def test_chart_without_suitable_columns_shows_a_warning():
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["df"] = ingest.parse_text("name\nA\nB")
    page.run()
    assert not page.exception
    assert "no suitable columns" in page.warning[0].value


def test_combine_choice_only_appears_when_rows_share_an_x():
    assert open_page("sales.csv").radio
    page = open_page("students.csv")
    assert not page.radio

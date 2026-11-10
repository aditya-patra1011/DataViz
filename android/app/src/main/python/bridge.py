"""What the Kotlin app calls. All the data work stays in core/; this only translates."""

from io import BytesIO

from core import charts, ingest


def chart_from_file(
    content, filename: str, chart: str, x: str, y: str, color: str | None, dark: bool
) -> str:
    """Build a chart from a file's bytes and return it as Plotly JSON for the WebView."""
    df = ingest.read_file(BytesIO(bytes(content)), filename)
    return charts.build_chart(df, chart, x=x, y=y, color=color, dark=dark).figure.to_json()

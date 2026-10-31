# 📊 DataViz

A web app that turns the data you enter into interactive charts, cleaning reports and insights.
Built with Python, Streamlit, pandas and Plotly.

## Features (planned)

- **Data input** — type data in a table, paste from a spreadsheet, or upload CSV/Excel
- **Cleaning pipeline** — automatic type detection, missing-value handling, validation and outlier checks
- **Visualizations** — bar, line, pie, scatter, histogram, box plot, heatmap and more, all interactive
- **Smart suggestions** — recommends the right chart for your columns and writes plain-English insights
- **Saved datasets** — store and reload datasets (SQLite), export cleaned data and charts

## Architecture

```
app/    → Streamlit pages (presentation only)
core/   → pure-Python logic: ingest, clean, profile, stats, recommend, charts, storage
tests/  → pytest tests for core/
```

`core/` never imports Streamlit, so every piece of logic is testable on its own and could be
reused behind a different front end (for example a REST API).

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt -r requirements-dev.txt
streamlit run app/Home.py
```

## Development

```bash
ruff check .      # lint
pytest            # run tests
```

Every pull request is checked automatically by GitHub Actions (lint + tests).

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Project setup, CI | ✅ Done |
| 1 | Data input (manual, paste, CSV/Excel upload) | ✅ Done |
| 2 | Cleaning & validation pipeline | 🚧 In progress |
| 3 | Visualizations | ⏳ |
| 4 | Chart recommender & auto-insights | ⏳ |
| 5 | Saved datasets & export | ⏳ |
| 6 | Tests, polish & deployment | ⏳ |

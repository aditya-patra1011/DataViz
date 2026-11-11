# 📊 DataViz

An Android app that turns the data you enter into interactive charts, a data-quality report and
plain-English insights. It works fully offline.

The screens are written in Kotlin with Jetpack Compose. All the data work (reading, cleaning,
statistics and building charts) is done by a Python package, `core/`, that runs **on the phone**
through [Chaquopy](https://chaquo.com/chaquopy/), using pandas and Plotly.

## Features

- **Enter data four ways:** type it, paste it from a spreadsheet, open a CSV or Excel (.xlsx)
  file, or load a sample
- **Clean it:** column types, missing values, duplicate rows and outliers (1.5 × IQR rule), with
  one-tap fixes, a log of every change and a reset button
- **Chart it:** bar, line, area, pie, scatter, histogram, box plot and correlation heatmap. Only
  the columns that suit each chart are offered; charts can be zoomed and tapped for exact values
- **Understand it:** plain-English findings (trend over time, best and worst group, strongest
  relationship, data problems), summary statistics and suggested charts
- **Keep it:** save datasets inside the app, export data as CSV and charts as PNG
- Light and dark mode, using colourblind-checked colour palettes

## How it fits together

```
Kotlin screens (Data, Clean, Charts)          android/app/src/main/kotlin/
        │  calls functions, gets JSON back
        ▼
Python bridge                                  android/app/src/main/python/bridge.py
        │
        ▼
core/  ingest · profile · clean · stats · recommend · charts · storage
        │  pandas for the data, Plotly for the chart description
        ▼
WebView + plotly.js draws the chart            android/app/src/main/assets/chart.html
```

`core/` has no Android or web code in it, so it is tested on its own with pytest. The same
package also powers the original web prototype in `app/` (Streamlit).

## Running it on a laptop (no Android phone needed)

You need [Android Studio](https://developer.android.com/studio) installed once, the Android SDK
(the launcher looks in `ANDROID_HOME`, `%USERPROFILE%\Android\Sdk` and
`%LOCALAPPDATA%\Android\Sdk`), Java 17 in `%USERPROFILE%\.jdks`, and a virtual phone called
`DataViz_Phone`. Then, from this folder:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
```

This starts the virtual phone, builds and installs the app, copies the sample CSV files onto the
phone and opens DataViz. Add `-Rebuild` after changing the code.

To use your own CSV files, drag them onto the phone window. They land in the phone's Download
folder; in the app choose **Data → File → Choose file**, then **☰ → Downloads**.

## Installing on a real Android phone

Build the phone version and copy the APK to the phone:

```powershell
cd android
.\gradlew.bat assemblePhoneRelease
```

The file is `android/app/build/outputs/apk/phone/release/app-phone-release.apk`. It needs
Android 7.0 or newer on a 64-bit ARM phone (nearly all phones from the last several years).
Every pull request's CI run also uploads the built APKs.

There are two versions because Python and pandas are compiled separately for each kind of
processor: **phone** (ARM, for real phones) and **emulator** (x86, for the laptop).

## Tests

```bash
pytest            # Python tests for core/, the bridge and the web prototype
ruff check .      # lint
```

Python tests run against two setups: the main one, and `requirements-android.txt`, which pins
the exact versions the phone uses (Python 3.11, pandas 2.1.3). On-device tests in
`android/app/src/androidTest` run the real app's Python on an emulator.

GitHub Actions runs all of this on every pull request, including building the app and running it
on an Android emulator.

## Project history

| Phase | Scope | Status |
|---|---|---|
| 0–3 | Web prototype: setup, data input, cleaning, charts | ✅ Done |
| A1 | Android proof of concept: Python core on the device | ✅ Done |
| A2 | Android screens: Data, Clean, Charts | ✅ Done |
| A3 | Insights, chart suggestions, saved datasets, export | ✅ Done |
| A4 | Smaller app, demo launcher, presentation guide | 🚧 In progress |

See [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for how to present the app.

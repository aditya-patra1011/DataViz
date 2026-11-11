# Presenting DataViz

A step-by-step plan for showing the app to your faculty, about 10 minutes long, plus what to do if
something goes wrong.

---

## The day before

1. **Run the launcher once** so the app is built and installed:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
   ```
2. **Practise the demo below twice**, out loud, with a timer.
3. **Record your second practice run** as a backup video:
   - in the phone window's side toolbar, click **⋯** (Extended controls)
   - choose **Record and playback → Start recording**, do the demo, then **Stop recording** and
     save the file
4. **Keep the backup** on a pen drive or your phone, with this guide.
5. **Prepare the laptop:**
   - fully charged, and bring the charger
   - turn on *Do not disturb* (Windows: Settings → System → Notifications)
   - if you can, test it with the projector you'll use

## 15 minutes before

1. Plug in the charger and close apps you don't need. The virtual phone needs a lot of memory.
2. Run the launcher (same command as above) and wait for **Ready**. Starting the phone from off takes about 5 minutes, because the launcher waits until the phone has settled.
3. **Warm it up:** in the app, tap **Data → Sample → sales.csv** once. Python is slowest the
   first time, so this makes the real demo quick.
4. Make the phone window bigger by dragging its corner, so the room can read it.
5. Open a second window with this guide, or the GitHub page, to switch to while you talk.

---

## The demo

Each step says what to **do** and what to **say**. The times add up to about 10 minutes.

### 1. The problem (30 seconds)
**Say:** "The task was an Android app that makes charts when you enter data. Most people's data
is messy, so DataViz also checks the data, cleans it and explains what the chart shows. It runs
fully offline."

### 2. How it's built (1 minute)
**Say:** "The screens are written in Kotlin. All the data work is done by a Python package, using
pandas and Plotly, and it runs on the phone itself through a library called Chaquopy. Kotlin
sends the data to Python, Python returns the results, and the chart is drawn with plotly.js. The
same Python code first powered a web version, and it has its own automated tests."

*If there's a slide or whiteboard, draw:* Kotlin screens → Python (pandas) → chart.

### 3. Typing data in (1 minute)
**Do:**
1. **Data → Type**
2. Replace the column names `Label, Value` with `Subject, Marks`
3. Rows: `Maths 78`, `Science 85`, `English 72`
4. Tap **Use this data**
5. **Charts → Build your own:** chart type **Bar**, then **Draw chart**
6. Tap a bar to show its exact value

**Say:** "The first column holds labels and the rest hold numbers. Blank rows are ignored."

### 4. Opening a real file (1 minute)
**Do:** **Data → File → Choose file → ☰ → Downloads**, scroll down if needed, then tap
**students.csv**

**Say:** "It reads CSV and Excel files. The launcher copied the sample files onto the phone; you
can drag any CSV onto the phone window to add more."

### 5. Checking and cleaning the data (1.5 minutes)
**Do:**
1. Open **Clean**. Point at *Missing cells: 2* and the *Outliers* section.
2. **Missing values:** column *Science*, fix by **median**, tap **Apply**.
3. Point at the message at the bottom of the screen and the **Cleaning log**.
4. Tap **Reset to original data**.

**Say:** "It finds missing values, duplicates and outliers. Outliers use the 1.5 × IQR rule, the
same rule a box plot uses. Every change is logged and can be undone, because the original data
is never modified."

### 6. Insights and suggested charts (1.5 minutes)
**Do:**
1. Open **Charts**. Read one finding aloud from *What the data shows*.
2. Tap **Show summary statistics**.
3. Under *Suggested charts*, tap **Scatter** (StudyHours vs Math).

**Say:** "It writes findings in plain English, like which group is highest or which columns
move together. It always adds that correlation doesn't prove causation. Suggestions come from
the column types: dates suggest a line chart, groups suggest a bar chart, related numbers
suggest a scatter plot."

### 7. Building a chart yourself (1 minute)
**Do:** **← Options**, chart type **Box plot**, X axis **Section**, Y axis **Math**, then
**Draw chart**. Tap **Show data** to show the table behind the chart, then **Show chart**.

**Say:** "Each chart type only offers the columns that make sense for it, so you can't build a
pie chart from text, for example."

### 8. It catches mistakes (30 seconds)
**Do:** **Data → Type**, type `abc` in a Marks cell, tap **Use this data**.

**Say:** "Bad input gets a clear message instead of a crash or a wrong chart."

### 9. Saving and sharing (1 minute)
**Do:**
1. **Data → Sample → sales.csv**, then under *Keep this data* tap **Save in app**.
2. Open the **Saved** tab to show it's listed.
3. **Charts →** tap the suggested **Line** chart → **Save image → SAVE**.

**Say:** "Datasets are saved in a SQLite database inside the app. Charts save as images, and
data exports as CSV."

### 10. How it was tested (1 minute)
**Say:** "There are over 180 automated Python tests, plus tests that run the real app's Python
on an Android emulator. Every change goes through GitHub, where the tests run automatically,
including building the app and running it on an emulator."

*Optional:* show the project's **Actions** tab on GitHub.

### 11. Close (30 seconds)
**Say:** "Next steps could be forecasting trends, connecting to live data sources, or sharing
dashboards. Thank you. I'm happy to take questions."

---

## Questions you might be asked

| Question | Answer |
|---|---|
| Why use Python in an Android app? | The data work (pandas, statistics, Plotly) is far richer in Python, and the same tested code powers both the web and Android versions. Kotlin handles what Android does best: the screens. |
| How does Python run on a phone? | Chaquopy bundles a Python interpreter and Android builds of pandas and NumPy inside the app. Kotlin calls Python functions directly, and they return JSON. |
| Does it need the internet? | No. Python, the libraries and the chart library are all inside the app. |
| How are outliers found? | Values more than 1.5 × IQR below the 25th percentile or above the 75th, the same rule a box plot uses. |
| How does it choose suggested charts? | From the column types: date + number → line, group + number → bar, two related numbers → scatter, 3+ numbers → heatmap. |
| How does it know a column's type? | If at least 80% of a column's values read as numbers (or dates), it's treated as numbers (or dates), so one typo doesn't hide the real type. |
| Why is the app large? | It carries a full Python runtime plus pandas, NumPy and Plotly. Building a separate version for each processor type and removing unused code took it from about 125 MB to about 67 MB. |
| Which phones does it work on? | Android 7.0 or newer, on 64-bit ARM phones. |
| What are its limits? | Up to 100,000 rows; .xlsx but not the old .xls format; the first start takes a few seconds while Python loads. |
| How did you test it without an Android phone? | The Android emulator on the laptop, automated on-device tests, and GitHub Actions running the app on an emulator for every change. |

## Where to point in the code if asked

| Topic | File |
|---|---|
| Reading files and typed data | `core/ingest.py` |
| Column types, missing values, outliers | `core/profile.py` |
| Cleaning fixes | `core/clean.py` |
| Charts | `core/charts.py` |
| Insights and statistics | `core/stats.py` |
| Chart suggestions | `core/recommend.py` |
| Saved datasets | `core/storage.py` |
| Kotlin ↔ Python link | `android/app/src/main/python/bridge.py` |
| Screens | `android/app/src/main/kotlin/com/adityapatra/dataviz/` |
| Tests | `tests/` and `android/app/src/androidTest/` |

---

## If something goes wrong

| Problem | Fix |
|---|---|
| The phone window is black | While it is starting, that can be normal for a minute; wait for the launcher. If it stays black, close the phone window and run the launcher again with `-SafeGraphics` at the end. |
| "System UI isn't responding" | Tap **Wait**. It happens when the phone has only just started; the launcher normally waits for this to pass. |
| The app shows "Starting DataViz…" for a while | Wait about 10 seconds; Python is loading. That's why you warm it up beforehand. |
| The file picker says "No items" | Tap **☰ → Downloads**. |
| A tap doesn't seem to work | Wait a second. The virtual phone can be slow when the laptop is busy. |
| Nothing works | Play your recorded practice run and talk over it, using the steps above. |

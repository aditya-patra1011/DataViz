package com.adityapatra.dataviz

import com.chaquo.python.Python
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/** A problem with the user's data or choices, with a message that can be shown to them. */
class CoreError(message: String) : Exception(message)

/** Calls the Python code. Python work always runs off the UI thread. */
object Core {
    private val bridge by lazy { Python.getInstance().getModule("bridge") }

    suspend fun call(function: String, vararg args: Any?): JSONObject =
        withContext(Dispatchers.Default) {
            val reply = JSONObject(bridge.callAttr(function, *args).toString())
            if (!reply.getBoolean("ok")) throw CoreError(reply.getString("error"))
            reply
        }
}

data class TableData(val columns: List<String>, val rows: List<List<String>>)

data class ColumnInfo(
    val name: String,
    val type: String,
    val missing: Int,
    val missingPercent: Double,
    val unique: Int,
    val outliers: Int,
    val needsConversion: Boolean,
)

data class Snapshot(
    val source: String,
    val rows: Int,
    val columns: Int,
    val missingCells: Int,
    val duplicateRows: Int,
    val report: List<ColumnInfo>,
    val preview: TableData,
    val limits: Map<String, Pair<Double, Double>>,
    val log: List<String>,
    val missingStrategies: List<String>,
    val outlierMethods: List<String>,
)

data class ChartForm(
    val chart: String = "Bar",
    val x: String? = null,
    val y: String? = null,
    val color: String? = null,
    val agg: String = "sum",
    val stacked: Boolean = true,
    val bins: Int = 20,
    val title: String = "",
)

data class ChartOptions(
    val charts: List<String>,
    val description: String,
    val x: List<String>,
    val xOptional: Boolean,
    val y: List<String>,
    val color: List<String>,
    val aggregations: List<String>,
    val repeats: Boolean,
    val stacks: Boolean,
    val bins: Boolean,
    val usable: Boolean,
)

data class Suggestion(
    val chart: String,
    val reason: String,
    val x: String?,
    val y: String?,
    val color: String?,
    val agg: String,
)

data class Insights(
    val findings: List<String>,
    val stats: TableData,
    val suggestions: List<Suggestion>,
)

data class SavedDataset(
    val name: String,
    val source: String,
    val savedAt: String,
    val rows: Int,
    val columns: Int,
)

data class DrawnChart(val figureJson: String, val notes: List<String>, val data: TableData)

fun JSONArray.strings(): List<String> = List(length()) { getString(it) }

private fun JSONObject.textOrNull(key: String) = if (isNull(key)) null else getString(key)

fun insightsFrom(reply: JSONObject): Insights {
    val suggestions = reply.getJSONArray("suggestions")
    return Insights(
        findings = reply.getJSONArray("findings").strings(),
        stats = tableFrom(reply.getJSONObject("stats")),
        suggestions = List(suggestions.length()) { index ->
            val item = suggestions.getJSONObject(index)
            Suggestion(
                chart = item.getString("chart"),
                reason = item.getString("reason"),
                x = item.textOrNull("x"),
                y = item.textOrNull("y"),
                color = item.textOrNull("color"),
                agg = item.getString("agg"),
            )
        },
    )
}

fun savedFrom(reply: JSONObject): List<SavedDataset> {
    val saved = reply.getJSONArray("saved")
    return List(saved.length()) { index ->
        val item = saved.getJSONObject(index)
        SavedDataset(
            name = item.getString("name"),
            source = item.getString("source"),
            savedAt = item.getString("saved_at"),
            rows = item.getInt("rows"),
            columns = item.getInt("columns"),
        )
    }
}

fun tableFrom(json: JSONObject): TableData {
    val rows = json.getJSONArray("rows")
    return TableData(
        columns = json.getJSONArray("columns").strings(),
        rows = List(rows.length()) { rows.getJSONArray(it).strings() },
    )
}

fun snapshotFrom(reply: JSONObject): Snapshot? {
    if (!reply.getBoolean("loaded")) return null
    val summary = reply.getJSONObject("summary")
    val report = reply.getJSONArray("report")
    val limits = reply.getJSONObject("limits")
    return Snapshot(
        source = reply.getString("source"),
        rows = summary.getInt("rows"),
        columns = summary.getInt("columns"),
        missingCells = summary.getInt("missing cells"),
        duplicateRows = summary.getInt("duplicate rows"),
        report = List(report.length()) { index ->
            val column = report.getJSONObject(index)
            ColumnInfo(
                name = column.getString("column"),
                type = column.getString("type"),
                missing = column.getInt("missing"),
                missingPercent = column.getDouble("missing %"),
                unique = column.getInt("unique"),
                outliers = column.getInt("outliers"),
                needsConversion = column.getBoolean("needs conversion"),
            )
        },
        preview = tableFrom(reply.getJSONObject("preview")),
        limits = limits.keys().asSequence().associateWith { name ->
            val pair = limits.getJSONArray(name)
            pair.getDouble(0) to pair.getDouble(1)
        },
        log = reply.getJSONArray("log").strings(),
        missingStrategies = reply.getJSONArray("missing_strategies").strings(),
        outlierMethods = reply.getJSONArray("outlier_methods").strings(),
    )
}

fun optionsFrom(reply: JSONObject) = ChartOptions(
    charts = reply.getJSONArray("charts").strings(),
    description = reply.getString("description"),
    x = reply.getJSONArray("x").strings(),
    xOptional = reply.getBoolean("x_optional"),
    y = reply.getJSONArray("y").strings(),
    color = reply.getJSONArray("color").strings(),
    aggregations = reply.getJSONArray("aggregations").strings(),
    repeats = reply.getBoolean("repeats"),
    stacks = reply.getBoolean("stacks"),
    bins = reply.getBoolean("bins"),
    usable = reply.getBoolean("usable"),
)

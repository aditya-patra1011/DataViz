package com.adityapatra.dataviz

import android.app.Application
import android.net.Uri
import android.util.Base64
import android.provider.OpenableColumns
import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.chaquo.python.PyException
import java.io.File
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/** Holds what the screens show, so it survives rotating the phone and switching tabs. */
class AppViewModel(application: Application) : AndroidViewModel(application) {
    var ready by mutableStateOf(false)
        private set
    var busy by mutableStateOf(false)
        private set
    var snapshot by mutableStateOf<Snapshot?>(null)
        private set
    var notice by mutableStateOf<String?>(null)
    var options by mutableStateOf<ChartOptions?>(null)
        private set
    var chart by mutableStateOf<DrawnChart?>(null)
    var insights by mutableStateOf<Insights?>(null)
        private set
    var saved by mutableStateOf<List<SavedDataset>>(emptyList())
        private set

    var form by mutableStateOf(ChartForm())
    var pastedText by mutableStateOf("")
    var typedColumns by mutableStateOf("Label, Value")
        private set
    val typedRows = mutableStateListOf(listOf("", ""), listOf("", ""), listOf("", ""))

    val sampleNames: List<String> =
        application.assets.list("samples")?.sorted().orEmpty()

    val typedNames: List<String>
        get() = typedColumns.split(",").map { it.trim() }.filter { it.isNotEmpty() }

    init {
        work { // The first call also starts Python and imports pandas
            val database = File(application.filesDir, "datasets.db").path
            Core.call("set_storage", database)
            saved = savedFrom(Core.call("saved_datasets"))
            show(Core.call("snapshot"))
            ready = true
        }
    }

    private fun work(showBusy: Boolean = true, block: suspend () -> Unit) {
        viewModelScope.launch {
            if (showBusy) busy = true
            try {
                block()
            } catch (error: CoreError) {
                notice = error.message
            } catch (error: IOException) {
                notice = "That file could not be read."
            } catch (error: PyException) {
                Log.e("DataViz", "Python failed", error)
                notice = "Something went wrong while processing the data."
            } finally {
                if (showBusy) busy = false
            }
        }
    }

    private fun show(reply: JSONObject) {
        snapshot = snapshotFrom(reply)
        reply.getString("message").takeIf { it.isNotBlank() }?.let { notice = it }
    }

    private fun load(function: String, vararg args: Any?) = work {
        show(Core.call(function, *args))
        chart = null
    }

    fun loadSample(name: String) = work {
        val content = withContext(Dispatchers.IO) {
            getApplication<Application>().assets.open("samples/$name").use { it.readBytes() }
        }
        show(Core.call("load_file", content, name, "sample: $name"))
        chart = null
    }

    fun loadFile(uri: Uri) = work {
        val resolver = getApplication<Application>().contentResolver
        val (name, content) = withContext(Dispatchers.IO) {
            val name = resolver.query(uri, null, null, null, null)?.use { cursor ->
                val column = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (column >= 0 && cursor.moveToFirst()) cursor.getString(column) else null
            } ?: "file"
            val bytes = resolver.openInputStream(uri)?.use { it.readBytes() }
                ?: throw IOException("No data")
            name to bytes
        }
        show(Core.call("load_file", content, name, name))
        chart = null
    }

    fun loadPasted() = load("load_text", pastedText)

    fun loadTyped() {
        val table = JSONObject()
            .put("columns", JSONArray(typedNames))
            .put("rows", JSONArray(typedRows.map { JSONArray(it) }))
        load("load_table", table.toString())
    }

    fun updateTypedColumns(text: String) {
        typedColumns = text
        val size = typedNames.size
        typedRows.replaceAll { row -> List(size) { row.getOrElse(it) { "" } } }
    }

    fun updateTypedCell(row: Int, column: Int, text: String) {
        typedRows[row] = typedRows[row].toMutableList().also { it[column] = text }
    }

    fun addTypedRow() {
        typedRows.add(List(typedNames.size) { "" })
    }

    fun removeTypedRow(row: Int) {
        typedRows.removeAt(row)
    }

    fun fix(action: String, column: String? = null, choice: String? = null, value: String? = null) =
        load("fix", action, column, choice, value)

    fun reset() = load("reset")

    /** Finds which columns and controls suit the chart, then keeps the form's choices valid. */
    fun refreshOptions() = work(showBusy = false) {
        val current = form
        val latest = optionsFrom(Core.call("chart_options", current.chart, current.x, current.color))
        options = latest

        val x = when {
            current.x in latest.x -> current.x
            latest.xOptional -> null
            else -> latest.x.firstOrNull()
        }
        val y = current.y.takeIf { it in latest.y && it != x }
            ?: latest.y.firstOrNull { it != x }
            ?: latest.y.firstOrNull()
        val color = current.color.takeIf { it in latest.color }
        val agg = current.agg.takeIf { it in latest.aggregations } ?: latest.aggregations.first()
        if (form == current) form = current.copy(x = x, y = y, color = color, agg = agg)
    }

    fun refreshInsights() = work(showBusy = false) {
        insights = insightsFrom(Core.call("insights"))
    }

    fun drawSuggestion(item: Suggestion, dark: Boolean) = work {
        val next = form.copy(
            chart = item.chart,
            x = item.x,
            y = item.y,
            color = item.color,
            agg = item.agg,
            title = "",
        )
        form = next
        options = optionsFrom(Core.call("chart_options", next.chart, next.x, next.color))
        drawForm(dark)
    }

    fun draw(dark: Boolean) = work { drawForm(dark) }

    fun saveDataset(name: String) = work {
        val reply = Core.call("save_dataset", name)
        saved = savedFrom(reply)
        notice = reply.getString("message")
    }

    fun openSaved(name: String) = load("open_saved", name)

    fun deleteSaved(name: String) = work {
        val reply = Core.call("delete_saved", name)
        saved = savedFrom(reply)
        notice = reply.getString("message")
    }

    private suspend fun write(uri: Uri, content: ByteArray) = withContext(Dispatchers.IO) {
        val resolver = getApplication<Application>().contentResolver
        resolver.openOutputStream(uri)?.use { it.write(content) }
            ?: throw IOException("No output")
    }

    fun exportCsv(uri: Uri) = work {
        write(uri, Core.call("export_csv").getString("csv").toByteArray())
        notice = "Saved the data as a CSV file."
    }

    /** Saves a chart image, which the page hands over as a base64 "data:" address. */
    fun saveImage(uri: Uri, image: String) = work {
        write(uri, Base64.decode(image.substringAfter(","), Base64.DEFAULT))
        notice = "Saved the chart as an image."
    }

    private suspend fun drawForm(dark: Boolean) {
        val choices = options ?: return
        val current = form
        val reply = Core.call(
            "draw",
            current.chart,
            current.x,
            current.y,
            current.color,
            if (choices.repeats) current.agg else "sum",
            current.stacked,
            if (choices.bins) current.bins else null,
            current.title.trim(),
            dark,
        )
        val notes = reply.getJSONArray("notes").strings()
        chart = DrawnChart(reply.getString("figure"), notes, tableFrom(reply.getJSONObject("data")))
    }
}

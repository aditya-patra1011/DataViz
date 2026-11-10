package com.adityapatra.dataviz

import android.view.ViewGroup
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import kotlin.math.roundToInt

@Composable
fun ChartsScreen(model: AppViewModel) {
    val snapshot = model.snapshot
    val form = model.form
    LaunchedEffect(snapshot, form.chart, form.x, form.color) {
        if (snapshot != null) model.refreshOptions()
    }

    val chart = model.chart
    when {
        snapshot != null && chart != null -> ChartResult(model, chart)
        else -> ScrollPage {
            PageTitle("📈 Charts")
            val options = model.options
            if (snapshot == null) NeedData() else if (options != null) ChartForm(model, options)
        }
    }
}

@Composable
private fun ChartForm(model: AppViewModel, options: ChartOptions) {
    val form = model.form
    val dark = isSystemInDarkTheme()
    val wide = Modifier.fillMaxWidth()

    Picker("Chart type", form.chart, options.charts, { model.form = form.copy(chart = it) }, wide)
    Text(options.description)

    if (!options.usable) {
        Text("This dataset has no suitable columns for this chart.")
        return
    }

    if (options.x.isNotEmpty()) {
        val choices = (if (options.xOptional) listOf(NO_COLUMN) else emptyList()) + options.x
        Picker("X axis", form.x ?: NO_COLUMN, choices, {
            model.form = form.copy(x = it.takeUnless { name -> name == NO_COLUMN })
        }, wide)
    }
    if (options.y.isNotEmpty()) {
        Picker("Y axis", form.y.orEmpty(), options.y, { model.form = form.copy(y = it) }, wide)
    }
    if (options.color.isNotEmpty()) {
        Picker("Colour by", form.color ?: NO_COLUMN, listOf(NO_COLUMN) + options.color, {
            model.form = form.copy(color = it.takeUnless { name -> name == NO_COLUMN })
        }, wide)
    }
    if (options.repeats) {
        Picker("Several rows share the same X. Combine with", form.agg, options.aggregations, {
            model.form = form.copy(agg = it)
        }, wide)
    }
    if (options.stacks) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Stack bars", Modifier.weight(1f))
            Switch(form.stacked, { model.form = form.copy(stacked = it) })
        }
    }
    if (options.bins) {
        Column {
            Text("Number of bins: ${form.bins}", style = MaterialTheme.typography.labelLarge)
            Slider(
                value = form.bins.toFloat(),
                onValueChange = { model.form = form.copy(bins = it.roundToInt()) },
                valueRange = 5f..100f,
            )
        }
    }
    OutlinedTextField(
        value = form.title,
        onValueChange = { model.form = form.copy(title = it) },
        label = { Text("Chart title (optional)") },
        singleLine = true,
        modifier = wide,
    )
    Button(onClick = { model.draw(dark) }, enabled = !model.busy, modifier = wide) {
        Text("Draw chart")
    }
}

@Composable
private fun ChartResult(model: AppViewModel, chart: DrawnChart) {
    var showData by rememberSaveable { mutableStateOf(false) }
    BackHandler { model.chart = null }

    Column(Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp),
        ) {
            TextButton(onClick = { model.chart = null }) { Text("← Options") }
            Spacer(Modifier.weight(1f))
            TextButton(onClick = { showData = !showData }) {
                Text(if (showData) "Show chart" else "Show data")
            }
        }
        chart.notes.forEach { note ->
            Text(
                "ℹ️ $note",
                modifier = Modifier.padding(horizontal = 16.dp),
                style = MaterialTheme.typography.bodySmall,
            )
        }
        if (showData) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) { DataTable(chart.data) }
        } else {
            key(chart.figureJson) {
                ChartView(chart.figureJson, Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun ChartView(figureJson: String, modifier: Modifier) {
    AndroidView(
        modifier = modifier.fillMaxWidth(),
        factory = { context ->
            WebView(context).apply {
                // Without this the page can't tell how tall the screen is
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT,
                )
                settings.javaScriptEnabled = true
                webViewClient = object : WebViewClient() {
                    override fun onPageFinished(view: WebView, url: String) {
                        view.evaluateJavascript("render($figureJson)", null)
                    }
                }
                loadUrl("file:///android_asset/chart.html")
            }
        },
        onRelease = { it.destroy() },
    )
}

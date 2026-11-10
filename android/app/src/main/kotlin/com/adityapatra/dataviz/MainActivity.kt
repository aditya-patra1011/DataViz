package com.adityapatra.dataviz

import android.content.Context
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.chaquo.python.Python
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private sealed interface ChartState {
    data object Loading : ChartState
    data class Ready(val figureJson: String) : ChartState
    data class Failed(val message: String) : ChartState
}

/** Runs the Python core on the bundled sales sample and returns the chart as Plotly JSON. */
fun buildSalesChart(context: Context, dark: Boolean): String {
    val file = "sales.csv"
    val content = context.assets.open("samples/$file").use { it.readBytes() }
    return Python.getInstance().getModule("bridge")
        .callAttr("chart_from_file", content, file, "Bar", "Month", "Sales", "Region", dark)
        .toString()
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val dark = isSystemInDarkTheme()
            MaterialTheme(colorScheme = if (dark) darkColorScheme() else lightColorScheme()) {
                Surface(Modifier.fillMaxSize()) {
                    Box(Modifier.safeDrawingPadding()) {
                        ChartScreen(dark)
                    }
                }
            }
        }
    }
}

@Composable
private fun ChartScreen(dark: Boolean) {
    val context = LocalContext.current
    var state by remember { mutableStateOf<ChartState>(ChartState.Loading) }

    LaunchedEffect(dark) {
        state = ChartState.Loading
        // Python and pandas take a few seconds to start, so keep that off the UI thread
        state = withContext(Dispatchers.Default) {
            runCatching { buildSalesChart(context, dark) }.fold(
                onSuccess = { ChartState.Ready(it) },
                onFailure = { ChartState.Failed(it.message ?: "The chart could not be built.") },
            )
        }
    }

    when (val current = state) {
        ChartState.Loading -> Box(Modifier.fillMaxSize(), Alignment.Center) {
            CircularProgressIndicator()
        }
        is ChartState.Failed -> Text(current.message, Modifier.padding(16.dp))
        is ChartState.Ready -> key(current.figureJson) { ChartView(current.figureJson) }
    }
}

@Composable
private fun ChartView(figureJson: String) {
    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { context ->
            WebView(context).apply {
                settings.javaScriptEnabled = true
                webViewClient = object : WebViewClient() {
                    override fun onPageFinished(view: WebView, url: String) {
                        view.evaluateJavascript("render($figureJson)", null)
                    }
                }
                loadUrl("file:///android_asset/chart.html")
            }
        },
    )
}

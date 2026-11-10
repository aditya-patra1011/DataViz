package com.adityapatra.dataviz

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.File
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PythonCoreTest {
    @Before
    fun loadSample() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val name = "students.csv"
        val content = context.assets.open("samples/$name").use { it.readBytes() }
        Core.call("load_file", content, name, "sample: $name")
        Unit
    }

    @Test
    fun loadingAFileProducesAReport() = runBlocking {
        val snapshot = assertNotNull(snapshotFrom(Core.call("snapshot")))
        assertEquals(20, snapshot.rows)
        assertEquals(2, snapshot.missingCells)
    }

    @Test
    fun aCleaningStepChangesTheData() = runBlocking {
        val reply = Core.call("fix", "missing", "Science", "median", null)
        assertEquals(1, assertNotNull(snapshotFrom(reply)).missingCells)
    }

    @Test
    fun everyChartTypeDrawsOnTheDevice() = runBlocking {
        val charts = optionsFrom(Core.call("chart_options", "Bar", null, null)).charts
        for (chart in charts) {
            val options = optionsFrom(Core.call("chart_options", chart, null, null))
            val x = options.x.firstOrNull()
            val y = options.y.firstOrNull { it != x }
            val reply = Core.call("draw", chart, x, y, null, "sum", true, null, "", false)
            val figure = JSONObject(reply.getString("figure"))
            assert(figure.getJSONArray("data").length() > 0) { "$chart drew nothing" }
        }
    }

    @Test
    fun insightsAndSuggestionsWorkOnTheDevice() = runBlocking {
        val insights = insightsFrom(Core.call("insights"))
        assert(insights.findings.isNotEmpty())
        assert(insights.suggestions.isNotEmpty())
    }

    @Test
    fun datasetsSaveAndReopenOnTheDevice() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        Core.call("set_storage", File(context.cacheDir, "test-${System.nanoTime()}.db").path)
        assertEquals("mine", savedFrom(Core.call("save_dataset", "mine")).single().name)
        assertEquals(20, assertNotNull(snapshotFrom(Core.call("open_saved", "mine"))).rows)
        assertEquals(0, savedFrom(Core.call("delete_saved", "mine")).size)
    }

    @Test(expected = CoreError::class)
    fun badDataGivesAFriendlyError(): Unit = runBlocking {
        Core.call("load_text", "")
    }

    private fun <T : Any> assertNotNull(value: T?): T {
        assertNotNull("expected a value", value as Any?)
        return value!!
    }
}

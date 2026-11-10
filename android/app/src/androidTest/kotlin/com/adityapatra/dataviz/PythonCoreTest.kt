package com.adityapatra.dataviz

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PythonCoreTest {
    @Test
    fun pythonCoreBuildsAChartOnTheDevice() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val figure = JSONObject(buildSalesChart(context, dark = false))
        assertEquals("one bar series per region", 4, figure.getJSONArray("data").length())
    }
}

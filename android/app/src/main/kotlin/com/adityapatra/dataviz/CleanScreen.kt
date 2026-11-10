package com.adityapatra.dataviz

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp

private const val FIXED_VALUE = "fixed value"

private fun columnCount(count: Int) = if (count == 1) "1 column" else "$count columns"

@Composable
fun CleanScreen(model: AppViewModel) {
    ScrollPage {
        PageTitle("🧹 Clean")
        val snapshot = model.snapshot
        if (snapshot == null) {
            NeedData()
            return@ScrollPage
        }

        DatasetMetrics(snapshot)
        Section("Column report") { ColumnReport(snapshot.report) }
        ConvertTypes(model, snapshot)
        DuplicateRows(model, snapshot)
        MissingValues(model, snapshot)
        Outliers(model, snapshot)
        DropColumn(model, snapshot)
        CleaningLog(model, snapshot)
        Section("Preview") { DataTable(snapshot.preview) }
    }
}

@Composable
fun NeedData() {
    Text("No dataset loaded yet. Open the Data tab to add one.")
}

@Composable
private fun ColumnReport(report: List<ColumnInfo>) {
    report.forEachIndexed { index, column ->
        if (index > 0) HorizontalDivider()
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(column.name, fontWeight = FontWeight.Bold)
            val problems = buildList {
                if (column.missing > 0) add("${column.missing} missing (${column.missingPercent}%)")
                if (column.outliers > 0) add("${column.outliers} outliers")
                if (column.needsConversion) add("stored as text")
            }
            Text(
                (listOf(column.type, "${column.unique} unique") + problems).joinToString(" · "),
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun ConvertTypes(model: AppViewModel, snapshot: Snapshot) {
    val columns = snapshot.report.filter { it.needsConversion }.map { it.name }
    Section("Convert types (${columns.size})") {
        Text("Turns text that holds numbers or dates into real numbers and dates.")
        if (columns.isNotEmpty()) Text("Will convert: " + columns.joinToString(", "))
        Button(
            onClick = { model.fix("convert") },
            enabled = columns.isNotEmpty() && !model.busy,
        ) { Text("Convert") }
    }
}

@Composable
private fun DuplicateRows(model: AppViewModel, snapshot: Snapshot) {
    Section("Duplicate rows (${snapshot.duplicateRows})") {
        Text("Removes rows that are exact copies of an earlier row.")
        Button(
            onClick = { model.fix("duplicates") },
            enabled = snapshot.duplicateRows > 0 && !model.busy,
        ) { Text("Remove duplicates") }
    }
}

@Composable
private fun MissingValues(model: AppViewModel, snapshot: Snapshot) {
    val columns = snapshot.report.filter { it.missing > 0 }.map { it.name }
    var pickedColumn by rememberSaveable { mutableStateOf("") }
    var strategy by rememberSaveable { mutableStateOf(snapshot.missingStrategies.first()) }
    var value by rememberSaveable { mutableStateOf("") }

    Section("Missing values (${columnCount(columns.size)})") {
        if (columns.isEmpty()) {
            Text("No missing values.")
            return@Section
        }
        val column = pickedColumn.takeIf { it in columns } ?: columns.first()
        Picker("Column", column, columns, { pickedColumn = it }, Modifier.fillMaxWidth())
        Picker("Fix by", strategy, snapshot.missingStrategies, { strategy = it }, Modifier.fillMaxWidth())
        if (strategy == FIXED_VALUE) {
            val isNumber = snapshot.report.first { it.name == column }.type == "numeric"
            OutlinedTextField(
                value = value,
                onValueChange = { value = it },
                label = { Text("Fill value") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(
                    keyboardType = if (isNumber) KeyboardType.Decimal else KeyboardType.Text,
                ),
                modifier = Modifier.fillMaxWidth(),
            )
        }
        Button(
            onClick = { model.fix("missing", column, strategy, value) },
            enabled = !model.busy,
        ) { Text("Apply") }
    }
}

@Composable
private fun Outliers(model: AppViewModel, snapshot: Snapshot) {
    val columns = snapshot.report.filter { it.outliers > 0 }.map { it.name }
    var pickedColumn by rememberSaveable { mutableStateOf("") }
    var method by rememberSaveable { mutableStateOf(snapshot.outlierMethods.first()) }

    Section("Outliers (${columnCount(columns.size)})") {
        Text("Values far outside the middle 50% of a column (the 1.5 × IQR rule).")
        if (columns.isEmpty()) {
            Text("No outliers found.")
            return@Section
        }
        val column = pickedColumn.takeIf { it in columns } ?: columns.first()
        Picker("Column", column, columns, { pickedColumn = it }, Modifier.fillMaxWidth())
        snapshot.limits[column]?.let { (low, high) ->
            Text("Normal range: %.2f to %.2f".format(low, high))
        }
        Picker("Fix by", method, snapshot.outlierMethods, { method = it }, Modifier.fillMaxWidth())
        Button(
            onClick = { model.fix("outliers", column, method) },
            enabled = !model.busy,
        ) { Text("Apply") }
    }
}

@Composable
private fun DropColumn(model: AppViewModel, snapshot: Snapshot) {
    val columns = snapshot.report.map { it.name }
    var pickedColumn by rememberSaveable { mutableStateOf("") }

    Section("Drop a column") {
        val column = pickedColumn.takeIf { it in columns } ?: columns.first()
        Picker("Column", column, columns, { pickedColumn = it }, Modifier.fillMaxWidth())
        OutlinedButton(
            onClick = { model.fix("drop", column) },
            enabled = columns.size > 1 && !model.busy,
        ) { Text("Drop") }
    }
}

@Composable
private fun CleaningLog(model: AppViewModel, snapshot: Snapshot) {
    Section("Cleaning log") {
        if (snapshot.log.isEmpty()) Text("No changes yet.")
        snapshot.log.forEachIndexed { index, step -> Text("${index + 1}. $step") }
        OutlinedButton(
            onClick = model::reset,
            enabled = snapshot.log.isNotEmpty() && !model.busy,
        ) { Text("↩ Reset to original data") }
    }
}

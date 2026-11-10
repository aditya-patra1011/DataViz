package com.adityapatra.dataviz

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp

private val inputModes = listOf("Type", "Paste", "File", "Sample")

// Some file apps label CSV files as plain text or generic data
private val fileTypes = arrayOf(
    "text/csv",
    "text/comma-separated-values",
    "application/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "application/octet-stream",
)

@Composable
fun DataScreen(model: AppViewModel) {
    var mode by rememberSaveable { mutableStateOf(inputModes.first()) }

    ScrollPage {
        PageTitle("📥 Data")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            inputModes.forEach { option ->
                FilterChip(
                    selected = mode == option,
                    onClick = { mode = option },
                    label = { Text(option) },
                )
            }
        }

        when (mode) {
            "Type" -> TypeData(model)
            "Paste" -> PasteData(model)
            "File" -> PickFile(model)
            else -> PickSample(model)
        }

        model.snapshot?.let { snapshot ->
            Section("Active dataset") {
                Text(snapshot.source)
                DatasetMetrics(snapshot)
                DataTable(snapshot.preview)
                if (snapshot.rows > snapshot.preview.rows.size) {
                    Text(
                        "Showing the first ${snapshot.preview.rows.size} of ${snapshot.rows} rows.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}

@Composable
private fun TypeData(model: AppViewModel) {
    val names = model.typedNames
    Section("Type your data") {
        Text("The first column holds labels and the others hold numbers.")
        OutlinedTextField(
            value = model.typedColumns,
            onValueChange = model::updateTypedColumns,
            label = { Text("Column names, separated by commas") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        model.typedRows.forEachIndexed { rowIndex, row ->
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                row.forEachIndexed { columnIndex, cell ->
                    val isNumber = columnIndex > 0
                    OutlinedTextField(
                        value = cell,
                        onValueChange = { model.updateTypedCell(rowIndex, columnIndex, it) },
                        label = { Text(names.getOrElse(columnIndex) { "" }) },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(
                            keyboardType = if (isNumber) KeyboardType.Decimal else KeyboardType.Text,
                        ),
                        modifier = Modifier.weight(1f),
                    )
                }
                TextButton(
                    onClick = { model.removeTypedRow(rowIndex) },
                    enabled = model.typedRows.size > 1,
                ) { Text("✕") }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = model::addTypedRow, enabled = names.isNotEmpty()) {
                Text("+ Add row")
            }
            Button(onClick = model::loadTyped, enabled = names.isNotEmpty() && !model.busy) {
                Text("Use this data")
            }
        }
    }
}

@Composable
private fun PasteData(model: AppViewModel) {
    Section("Paste your data") {
        Text("Paste cells copied from a spreadsheet, including the header row, or CSV text.")
        OutlinedTextField(
            value = model.pastedText,
            onValueChange = { model.pastedText = it },
            placeholder = { Text("Month,Sales\nJan,120") },
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 160.dp),
        )
        Button(onClick = model::loadPasted, enabled = !model.busy) { Text("Use this data") }
    }
}

@Composable
private fun PickFile(model: AppViewModel) {
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let(model::loadFile)
    }
    Section("Open a file") {
        Text("Choose a CSV or Excel (.xlsx) file from this phone.")
        Button(onClick = { picker.launch(fileTypes) }, enabled = !model.busy) {
            Text("Choose file")
        }
    }
}

@Composable
private fun PickSample(model: AppViewModel) {
    Section("Try a sample") {
        Text("Load a ready-made dataset to explore the app.")
        model.sampleNames.forEach { name ->
            OutlinedButton(
                onClick = { model.loadSample(name) },
                enabled = !model.busy,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(name) }
        }
    }
}

package com.adityapatra.dataviz

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

const val NO_COLUMN = "(none)"

/** A page that scrolls, with the same margins and spacing everywhere. */
@Composable
fun ScrollPage(content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        content = content,
    )
}

@Composable
fun PageTitle(text: String) {
    Text(text, style = MaterialTheme.typography.headlineMedium)
}

@Composable
fun Section(title: String, content: @Composable ColumnScope.() -> Unit) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            content()
        }
    }
}

@Composable
fun Picker(
    label: String,
    selected: String,
    options: List<String>,
    onPick: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var open by remember { mutableStateOf(false) }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(label, style = MaterialTheme.typography.labelLarge)
        Box {
            OutlinedButton(onClick = { open = true }, Modifier.fillMaxWidth()) {
                Text(
                    selected,
                    modifier = Modifier.weight(1f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text("▾")
            }
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                options.forEach { option ->
                    DropdownMenuItem(
                        text = { Text(option) },
                        onClick = {
                            open = false
                            onPick(option)
                        },
                    )
                }
            }
        }
    }
}

@Composable
fun Metric(label: String, value: Int, modifier: Modifier = Modifier) {
    Column(modifier) {
        Text(label, style = MaterialTheme.typography.labelLarge)
        Text("%,d".format(value), style = MaterialTheme.typography.headlineSmall)
    }
}

@Composable
fun DatasetMetrics(snapshot: Snapshot) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row {
            Metric("Rows", snapshot.rows, Modifier.weight(1f))
            Metric("Columns", snapshot.columns, Modifier.weight(1f))
        }
        Row {
            Metric("Missing cells", snapshot.missingCells, Modifier.weight(1f))
            Metric("Duplicate rows", snapshot.duplicateRows, Modifier.weight(1f))
        }
    }
}

/** A table that scrolls sideways, since most datasets are wider than a phone. */
@Composable
fun DataTable(table: TableData) {
    Column(Modifier.horizontalScroll(rememberScrollState())) {
        TableRow(table.columns, FontWeight.Bold)
        HorizontalDivider(Modifier.width(CELL_WIDTH * table.columns.size))
        table.rows.forEach { TableRow(it, FontWeight.Normal) }
    }
}

private val CELL_WIDTH = 112.dp

@Composable
private fun TableRow(cells: List<String>, weight: FontWeight) {
    Row {
        cells.forEach { cell ->
            Text(
                cell,
                modifier = Modifier
                    .width(CELL_WIDTH)
                    .padding(horizontal = 6.dp, vertical = 6.dp),
                fontWeight = weight,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

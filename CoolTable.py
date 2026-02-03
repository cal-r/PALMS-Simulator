from __future__ import annotations

from PySide6.QtCore import Qt, QObject, QEvent, QTimer
from PySide6.QtGui import QBrush, QColor, QPalette
from PySide6.QtWidgets import *

# We do this so that mypy stops complaining
from PySide6.QtWidgets import QAbstractItemView, QGridLayout, QPushButton, QSizePolicy, QTableWidget, QWidget

import re
import logging

class CoolTable(QWidget):
    def __init__(self, rows: int, cols: int, parent: None | QWidget = None):
        super().__init__(parent = parent)
        self.parent = parent

        self.freeze = True

        self.table = QTableWidget(rows, cols, parent)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.table.verticalHeader().sectionDoubleClicked.connect(self.editExperimentNames) # type: ignore
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive) # type: ignore
        # self.table.resizeColumnsToContents()

        self.table.cellChanged.connect(self.refreshOnChange)

        self.rightPlus = QPushButton('+')
        self.rightPlus.clicked.connect(self.addColumn)
        self.rightPlus.setToolTip('Add a new phase.')
        self.rightPlus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.rightPlus.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.bottomPlus = QPushButton('+')
        self.bottomPlus.clicked.connect(self.addRow)
        self.bottomPlus.setToolTip('Add a new experiment.')
        self.bottomPlus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bottomPlus.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.cButton = QPushButton('C')
        self.cButton.clicked.connect(self.clearEmptyCells)
        self.cButton.setToolTip('Clear empty phases and experiments.')
        self.cButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.rightPlus.setFixedWidth(20)
        self.bottomPlus.setFixedHeight(20)
        self.cButton.setFixedSize(20, 20)

        self.mainLayout = QGridLayout(parent = self)
        self.mainLayout.addWidget(self.table, 0, 0)
        self.mainLayout.addWidget(self.rightPlus, 0, 1)
        self.mainLayout.addWidget(self.bottomPlus, 1, 0)
        self.mainLayout.addWidget(self.cButton, 1, 1)
        self.mainLayout.setColumnStretch(0, 0)
        self.mainLayout.setColumnStretch(1, 0)
        self.mainLayout.setSpacing(0)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.setObjectName('CoolTable')

        self.freeze = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateSizes()

    def updateSizes(self):
        self.setHeaderNames()

        self.table.horizontalHeader().setMaximumSectionSize(-1)
        self.table.horizontalHeader().setMinimumSectionSize(150)
        self.table.resizeColumnsToContents()

        self.table.setFixedHeight(
            sum(self.table.rowHeight(x) for x in range(self.table.rowCount())) +
            self.table.horizontalHeader().height() +
            2 * self.table.frameWidth()
        )

        self.table.updateGeometry()

        QTimer.singleShot(0, self.resizeAllColumns)

    def resizeAllColumns(self):
        hh = self.table.horizontalHeader()

        sectionSizes = [hh.sectionSize(x) for x in range(hh.count())]
        if sum(sectionSizes) > hh.width():
            self.table.horizontalHeader().setMinimumSectionSize(50)
            self.table.resizeColumnsToContents()
            QTimer.singleShot(0, self.resizeLargeColumns)

        self.table.updateGeometry()

    def resizeLargeColumns(self):
        hh = self.table.horizontalHeader()
        length = hh.width()

        sectionSizes = sorted(hh.sectionSize(x) for x in range(hh.count()))
        count = len(sectionSizes)

        for s in sectionSizes:
            if s >= length // count:
                hh.setMaximumSectionSize(length // count)
                break

            length -= s
            count -= 1

        self.table.updateGeometry()

    def editExperimentNames(self, index):
        item = self.table.verticalHeaderItem(index)

        editor = QLineEdit(self.table)
        editor.setPlaceholderText('Experiment Name')
        editor.setFocus()

        def setHeader():
            item.name = editor.text()
            self.setHeaderNames()
            editor.deleteLater()
            self.parent.refreshExperiment()

        editor.editingFinished.connect(setHeader)
        editor.show()

    def getText(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        if item is None:
            return ""

        return item.text()

    def selectedPrefixes(self) -> list[set[str]]:
        changes = {'lambda': 'lamda'}

        prefixes = []
        for item in self.table.selectedItems() or [self.table.itemAt(0, 0)]:
            prefixes.append({changes.get(x[0], x[0]) for x in re.findall(r'(rand|beta|lamb?da)(:?=[0-9]+(\.[0-9]*)?)?/', item.text())})

        return prefixes

    def setPrefixInSelection(self, prefix, value: None | bool | float):
        self.freeze = True
        for item in self.table.selectedItems() or [self.table.itemAt(0, 0)]:
            text = re.sub(rf'{prefix}(=[0-9]+(\.[0-9]*)?)?/', '', item.text())

            if value is None:
                val_prefix = ''
            elif type(value) is bool:
                val_prefix = f'{prefix}/' if value else ''
            else:
                val_prefix = f'{prefix}={value}/'

            item.setText(val_prefix + text)

        self.freeze = False

    def setHeaderNames(self):
        for row in range(self.rowCount()):
            name = None
            if self.table.verticalHeaderItem(row) is not None:
                name = self.table.verticalHeaderItem(row).name

            default = f'Group {1 + row}'

            item = QTableWidgetItem(name or default)
            item.name = name
            self.table.setVerticalHeaderItem(row, item)

        for col in range(self.columnCount()):
            self.table.setHorizontalHeaderItem(col, QTableWidgetItem(f'Phase {col + 1}'))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            for item in self.table.selectedItems():
                item.setText('')

    def refreshOnChange(self):
        if self.freeze:
            return

        self.parent.refreshExperiment()

    def connectPrefixes(self, func):
        self.table.cellChanged.connect(lambda: func(self.selectedPrefixes()))
        self.table.itemSelectionChanged.connect(lambda: func(self.selectedPrefixes()))

    def addColumn(self):
        cols = self.columnCount()
        self.table.insertColumn(cols)
        self.updateGeometry()
        self.updateSizes()

    def addRow(self):
        rows = self.rowCount()
        self.table.insertRow(rows)
        self.updateSizes()

    def clearEmptyRows(self):
        toRemove = []
        for row in range(self.rowCount()):
            if not any(self.getText(row, x) for x in range(self.columnCount())):
                toRemove.append(row)

        if len(toRemove) == self.rowCount():
            toRemove = toRemove[1:]

        for row in toRemove[::-1]:
            self.table.removeRow(row)

    def clearEmptyColumns(self):
        toRemove = []
        for col in range(self.columnCount()):
            if not any(self.getText(x, col) for x in range(self.rowCount())):
                toRemove.append(col)

        if len(toRemove) == self.columnCount():
            toRemove = toRemove[1:]

        for col in toRemove[::-1]:
            self.table.removeColumn(col)

    def clearEmptyCells(self):
        self.clearEmptyRows()
        self.clearEmptyColumns()
        self.updateSizes()

    def clearAll(self):
        self.table.clearContents()
        self.clearEmptyCells()
        self.addRow()
        for row in range(self.rowCount()):
            name = f'Group {row + 1}'
            item = QTableWidgetItem(name)
            item.name = name
            self.table.setVerticalHeaderItem(row, item)

    def rowCount(self):
        return self.table.rowCount()

    def columnCount(self):
        return self.table.columnCount()

    def selectColumn(self, changeCol):
        old_freeze = self.freeze
        self.freeze = True

        default = self.table.palette().color(QPalette.ColorRole.Base)
        highlight = default.lighter(150) if default.valueF() < 0.5 else default.darker(150)

        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.table.item(row, col)
                brush = QBrush(highlight) if col == changeCol else QBrush(default)
                if item:
                    item.setBackground(brush)

        self.freeze = old_freeze

    def loadFile(self, lines):
        self.freeze = True
        self.table.setRowCount(len(lines))

        maxCols = 0
        for row, group in enumerate(lines):
            name, *phase_strs = [x.strip() for x in group.split('|')]

            if len(phase_strs) > maxCols:
                maxCols = len(phase_strs)
                self.table.setColumnCount(maxCols)
                self.table.setHorizontalHeaderLabels([f'Phase {x}' for x in range(1, maxCols + 1)])

            item = QTableWidgetItem(name)
            item.name = name
            self.table.setVerticalHeaderItem(row, item)
            for col, phase in enumerate(phase_strs):
                self.table.setItem(row, col, QTableWidgetItem(phase))

        self.updateSizes()
        self.freeze = False

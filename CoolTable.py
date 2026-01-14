from __future__ import annotations

from PySide6.QtCore import Qt, QObject, QEvent, QTimer
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
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)

        self.table.verticalHeader().sectionDoubleClicked.connect(self.editExperimentNames) # type: ignore
        self.table.horizontalHeader().setMinimumSectionSize(100) # type: ignore
        # self.table.horizontalHeader().setMaximumSectionSize(400) # type: ignore
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive) # type: ignore
        self.table.resizeColumnsToContents()

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
        self.mainLayout.setColumnStretch(0, 1)
        self.mainLayout.setRowStretch(0, 1)
        self.mainLayout.setSpacing(0)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        QTimer.singleShot(0, self.updateSizes)
        self.freeze = False

    def updateSizes(self):
        self.setHeaderNames()

        hh = self.table.horizontalHeader()
        # self.table.horizontalHeader().setCascadingSectionResizes(True)
        self.table.resizeColumnsToContents()

        sizes = [hh.sectionSize(i) for i in range(hh.count())]
        if sum(sizes) > hh.width():
            bigs = [i for i, s in enumerate(sizes) if s > 100]
            size_bigs = hh.width() - sum(x for x in sizes if x <= 100)

            logging.info(f'Resizing sections to {size_bigs // len(bigs) if len(bigs) > 0 else "?"}')
            for b in bigs:
                self.table.horizontalHeader().resizeSection(b, size_bigs // len(bigs))

        # print(f'Sizes:\t{[hh.sectionSize(i) for i in range(hh.count())]}')
        # print(f'Width:\t{hh.width()};\tSum:\t{sum([hh.sectionSize(i) for i in range(hh.count())])}')

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

    def setPrefixInSelection(self, prefix, value: None | bool | float):
        self.freeze = True
        for item in self.table.selectedItems():
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

    def onCellChange(self, func):
        def cellChanged(*args, **kwargs):
            if not self.freeze:
                func()

        self.table.cellChanged.connect(cellChanged)

    def addColumn(self):
        cols = self.columnCount()
        self.table.insertColumn(cols)
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

    def selectColumn(self, col):
        self.table.setRangeSelected(
            QTableWidgetSelectionRange(0, 0, self.rowCount() - 1, self.columnCount() - 1),
            False,
        )

        self.table.setRangeSelected(
            QTableWidgetSelectionRange(0, col, self.rowCount() - 1, col),
            True,
        )

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

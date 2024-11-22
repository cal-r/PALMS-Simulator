from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *

class CoolTable(QWidget):
    def __init__(self, rows: int, cols: int, parent: None | QWidget = None):
        super().__init__(parent = parent)

        self.freeze = True

        self.table = QTableWidget(rows, cols)
        self.table.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.table.verticalHeader().sectionDoubleClicked.connect(self.editExperimentNames)
        self.table.horizontalHeader().setMinimumSectionSize(300)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.rightPlus = QPushButton('+')
        self.rightPlus.clicked.connect(self.addColumn)
        self.rightPlus.setToolTip('Add a new phase.')

        self.bottomPlus = QPushButton('+')
        self.bottomPlus.clicked.connect(self.addRow)
        self.bottomPlus.setToolTip('Add a new experiment.')

        self.cButton = QPushButton('C')
        self.cButton.clicked.connect(self.clearEmptyCells)
        self.cButton.setToolTip('Clear empty phases and experiments.')

        self.rightPlus.setFixedWidth(20)
        self.bottomPlus.setFixedHeight(20)
        self.cButton.setFixedSize(20, 20)

        self.mainLayout = QGridLayout(parent = self)
        self.mainLayout.addWidget(self.table, 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.mainLayout.addWidget(self.rightPlus, 0, 1, Qt.AlignmentFlag.AlignLeft)
        self.mainLayout.addWidget(self.bottomPlus, 1, 0, Qt.AlignmentFlag.AlignTop)
        self.mainLayout.addWidget(self.cButton, 1, 1, Qt.AlignmentFlag.AlignLeft)
        self.mainLayout.setColumnStretch(1, 1)
        self.mainLayout.setRowStretch(1, 1)
        self.mainLayout.setSpacing(0)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.updateSizes()
        self.freeze = False

    def editExperimentNames(self, index):
        item = self.table.verticalHeaderItem(index)

        editor = QLineEdit(self.table)
        editor.setPlaceholderText('Experiment Name')
        editor.setFocus()

        def setHeader():
            item.name = editor.text()
            self.setHeaderNames()
            editor.deleteLater()
            self.parent().refreshExperiment()

        editor.editingFinished.connect(setHeader)
        editor.show()

    def getText(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        if item is None:
            return ""

        return item.text()

    def setRandInSelection(self, set_rand: bool):
        self.freeze = True
        for item in self.table.selectedItems():
            item.setText(item.text().replace('rand/', ''))

            if set_rand:
                item.setText('rand/' + item.text())

        self.freeze = False

    def setLambdaInSelection(self, set_lambda: None | float):
        self.freeze = True
        for item in self.table.selectedItems():
            item.setText(re.sub(r'lamb?da=[0-9]+(\.[0-9]+)?\/', '', item.text()))

            if set_lambda is not None:
                item.setText(f'lambda={set_lambda}/' + item.text())

        self.freeze = False

    def setHeaderNames(self):
        for row in range(self.rowCount()):
            name = None
            if self.table.verticalHeaderItem(row) is not None:
                name = self.table.verticalHeaderItem(row).name

            default = \
                'Control' if row == 0 else \
                'Test' if self.rowCount() == 2 else \
                f'Test {row}'

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

    def updateSizes(self):
        self.setHeaderNames()
        width = 2 + max(self.table.horizontalHeader().length(), 150) + self.table.verticalHeader().width()
        height = 2 + self.table.verticalHeader().length() + self.table.horizontalHeader().height()
        
        self.table.setFixedSize(width, height)
        self.rightPlus.setFixedHeight(height)
        self.bottomPlus.setFixedWidth(width)

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


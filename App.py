import sys
from collections import defaultdict
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import *
from Experiment import RWArgs, run_stuff
from Plots import plot_graphs
from Strengths import History

class CoolTable(QTableWidget):
    def __init__(self, rows: int, cols: int):
        super().__init__(rows, cols)
        self.setVerticalHeaders()
        self.setHorizontalHeaderItem(0, QTableWidgetItem('Phase 1'))
        self.itemChanged.connect(self.autoResize)
        self.freeze = False

    def getText(self, row: int, col: int) -> str:
        item = self.item(row, col)
        if item is None:
            return ""

        return item.text()

    def setVerticalHeaders(self):
        rows = self.rowCount()

        self.setVerticalHeaderItem(0, QTableWidgetItem('Control'))
        self.setVerticalHeaderItem(1, QTableWidgetItem('Test'))

        firstNum = 2 if rows <= 3 else 1
        for e in range(firstNum, rows):
            self.setVerticalHeaderItem(e, QTableWidgetItem(f'Test {e}'))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            for item in self.selectedItems():
                item.setText('')
        else:
            super().keyPressEvent(event)

    def addInsetTextColumn(self):
        currentColumnCount = self.columnCount()
        self.setColumnCount(currentColumnCount + 1)
        self.inset_text_column_index = currentColumnCount
        self.setHorizontalHeaderItem(
            self.inset_text_column_index,
            QTableWidgetItem("Inset Text"),
        )

    def removeInsetTextColumn(self):
        currentColumnCount = self.columnCount()
        if currentColumnCount > 1 and self.inset_text_column_index is not None:
            self.removeColumn(self.inset_text_column_index)
            self.inset_text_column_index = None

    def autoResize(self, item):
        if self.freeze:
            return

        col = item.column()
        row = item.row()

        colCount = self.columnCount()
        rowCount = self.rowCount()

        if item.text():
            if col == colCount - 1:
                self.addColumn()

            if row == rowCount - 1:
                self.addRow()
        else:
            if col == colCount - 2 and not any(self.getText(x, col) for x in range(colCount)):
                self.removeColumn()

            if row == rowCount - 2 and not any(self.getText(x, row) for x in range(rowCount)):
                self.removeRow()

    def addColumn(self):
        cols = self.columnCount()
        self.insertColumn(cols)
        self.setHorizontalHeaderItem(cols, QTableWidgetItem(f'Phase {cols + 1}'))

    def removeColumn(self):
        currentColumnCount = self.columnCount()
        self.setColumnCount(currentColumnCount - 1)

    def addRow(self):
        rows = self.rowCount()
        self.insertRow(rows)
        self.setVerticalHeaders()

    def removeRow(self):
        currentRowCount = self.rowCount()
        self.setRowCount(currentRowCount - 1)
        self.setVerticalHeaders()

    def loadFile(self, lines):
        self.freeze = True

        self.setRowCount(len(lines))

        maxCols = 0
        for row, group in enumerate(lines):
            name, *phase_strs = [x.strip() for x in group.split('|')]

            if len(phase_strs) > maxCols:
                maxCols = len(phase_strs)
                self.setColumnCount(maxCols)

            self.setVerticalHeaderItem(row, QTableWidgetItem(name))
            for col, phase in enumerate(phase_strs):
                self.setItem(row, col, QTableWidgetItem(phase))

        self.freeze = False

class PavlovianApp(QDialog):
    def __init__(self, parent=None):
        super(PavlovianApp, self).__init__(parent)

        self.adaptive_types = ['linear', 'exponential', 'mack', 'hall', 'macknhall', 'dualV', 'lepelley', 'dualmack', 'hybrid']
        self.plot_experiment_types = ['plot experiments', 'plot alpha', 'plot alphas', 'plot macknhall']
        self.current_adaptive_type = None
        self.inset_text_column_index = None

        self.originalPalette = QApplication.palette()

        self.initUI()

        QTimer.singleShot(100, self.updateWidgets)

    def initUI(self):
        styleComboBox = QComboBox()
        styleComboBox.addItems(QStyleFactory.keys())

        styleLabel = QLabel("&Style:")
        styleLabel.setBuddy(styleComboBox)

        self.useStylePaletteCheckBox = QCheckBox("&Use style's standard palette")
        self.useStylePaletteCheckBox.setChecked(True)

        disableWidgetsCheckBox = QCheckBox("&Disable widgets")

        self.tableWidget = CoolTable(2, 1)

        self.createAdaptiveTypeGroupBox()
        self.createParametersGroupBox()

        disableWidgetsCheckBox.toggled.connect(self.adaptiveTypeGroupBox.setDisabled)
        disableWidgetsCheckBox.toggled.connect(self.parametersGroupBox.setDisabled)

        mainLayout = QGridLayout()
        mainLayout.addWidget(self.tableWidget, 0, 0, 1, 2)
        mainLayout.addWidget(self.parametersGroupBox, 1, 0, 1, 1)
        mainLayout.addWidget(self.adaptiveTypeGroupBox, 1, 1, 1, 1)
        self.setLayout(mainLayout)

        self.setWindowTitle("🐕🔔")
        self.restoreDefaultParameters()

    def openFileDialog(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Open File', './Experiments')
        self.tableWidget.loadFile([x.strip() for x in open(file)])

    def createAdaptiveTypeGroupBox(self):
        self.adaptiveTypeGroupBox = QGroupBox("Adaptive Type")

        self.fileButton = QPushButton('Load file')
        self.fileButton.clicked.connect(self.openFileDialog)

        self.adaptivetypeComboBox = QComboBox(self)
        self.adaptivetypeComboBox.addItems(self.adaptive_types)
        self.adaptivetypeComboBox.activated.connect(self.changeAdaptiveType)
        
        self.plotexperimentComboBox = QComboBox(self)
        self.plotexperimentComboBox.addItems(self.plot_experiment_types)
        self.plotexperimentComboBox.activated.connect(self.changePlotExperimentType)

        self.setDefaultParamsButton = QPushButton("Restore Default Parameters")
        self.setDefaultParamsButton.clicked.connect(self.restoreDefaultParameters)

        self.printButton = QPushButton("Plot")
        self.printButton.clicked.connect(self.plotExperiment)

        layout = QVBoxLayout()
        layout.addWidget(self.fileButton)
        layout.addWidget(self.adaptivetypeComboBox)
        layout.addWidget(self.plotexperimentComboBox)
        layout.addWidget(self.setDefaultParamsButton)
        layout.addWidget(self.printButton)
        layout.addStretch(1)
        self.adaptiveTypeGroupBox.setLayout(layout)

    def changePlotExperimentType(self):
        self.plot_experiment_type = self.plotexperimentComboBox.currentText()

        if self.plot_experiment_type in ['plot phase', 'plot stimuli']:
            if self.inset_text_column_index is None:
                self.addInsetTextColumn()
        else:
            if self.inset_text_column_index is not None:
                self.removeInsetTextColumn()

    def changeAdaptiveType(self):
        self.current_adaptive_type = self.adaptivetypeComboBox.currentText()

        widgets_to_enable = {
            'linear': ['alpha', 'lamda', 'beta'],
            'exponential': ['alpha', 'lamda', 'beta'],
            'mack': ['alpha', 'lamda', 'beta', 'thetaE', 'thetaI'],
            'hall': ['lamda', 'beta', 'gamma', 'thetaE', 'thetaI'],
            'macknhall': ['alpha', 'lamda', 'beta', 'gamma', 'window_size'],
            'dualV': ['alpha', 'lamda', 'beta', 'betan', 'gamma'],
            'lepelley': ['alpha', 'lamda', 'beta', 'betan', 'gamma', 'thetaE', 'thetaI'],
            'dualmack': ['alpha', 'lamda', 'beta', 'betan'],
            'hybrid': ['alpha', 'lamda', 'beta', 'betan', 'gamma', 'thetaE', 'thetaI'],
        }

        for key in ['alpha', 'lamda', 'beta', 'betan', 'gamma', 'thetaE', 'thetaI', 'window_size']:
            widget = getattr(self, f'{key}_box')
            widget.setDisabled(True)

        for key in widgets_to_enable[self.current_adaptive_type]:
            widget = getattr(self, f'{key}_box')
            widget.setDisabled(False)

    def createParametersGroupBox(self):
        self.parametersGroupBox = QGroupBox("Parameters")

        params = QFormLayout()
        self.alpha_Label = QLabel("Initial Alpha")
        self.alpha_box = QLineEdit()
        self.lamda_Label = QLabel("Lambda")
        self.lamda_box = QLineEdit()
        self.beta_Label = QLabel("Beta")
        self.beta_box = QLineEdit()
        self.betan_Label = QLabel("Inhibitory Beta")
        self.betan_box = QLineEdit()
        self.gamma_Label = QLabel("Gamma")
        self.gamma_box = QLineEdit()
        self.thetaE_Label = QLabel("Theta E")
        self.thetaE_box = QLineEdit()
        self.thetaI_Label = QLabel("Theta I")
        self.thetaI_box = QLineEdit()
        self.window_size_Label = QLabel("Window Size")
        self.window_size_box = QLineEdit()
        self.num_trials_Label = QLabel("Number Trials")
        self.num_trials_box = QLineEdit()

        params.addRow(self.alpha_Label, self.alpha_box)
        params.addRow(self.lamda_Label, self.lamda_box)
        params.addRow(self.beta_Label, self.beta_box)
        params.addRow(self.betan_Label, self.betan_box)
        params.addRow(self.gamma_Label, self.gamma_box)
        params.addRow(self.thetaE_Label, self.thetaE_box)
        params.addRow(self.thetaI_Label, self.thetaI_box)
        params.addRow(self.window_size_Label, self.window_size_box)
        params.addRow(self.num_trials_Label, self.num_trials_box)

        self.parametersGroupBox.setLayout(params)

    def restoreDefaultParameters(self):
        defaults = {
            'alpha': '0.1',
            'lamda': '1',
            'beta': '0.3',
            'betan': '0.2',
            'gamma': '0.5',
            'thetaE': '0.3',
            'thetaI': '0.1',
            'window_size': '10',
            'num_trials': '1000'
        }

        for key, value in defaults.items():
            widget = getattr(self, f'{key}_box')
            widget.setText(value)

    def plotExperiment(self):
        self.current_adaptive_type = self.adaptivetypeComboBox.currentText()
        self.plot_experiment_type = self.plotexperimentComboBox.currentText()
        
        args = RWArgs(
            adaptive_type = self.current_adaptive_type,

            alphas = defaultdict(lambda: float(self.alpha_box.text())),
            alpha = float(self.alpha_box.text()),
            beta = float(self.beta_box.text()),
            beta_neg = float(self.betan_box.text()),
            lamda = float(self.lamda_box.text()),
            gamma = float(self.gamma_box.text()),
            thetaE = float(self.thetaE_box.text()),
            thetaI = float(self.thetaI_box.text()),

            window_size = int(self.window_size_box.text()),
            num_trials = int(self.num_trials_box.text()),

            use_configurals = False,
            xi_hall = 0.5,
        )

        rowCount = self.tableWidget.rowCount()
        columnCount = self.tableWidget.columnCount()
        while not any(self.tableWidget.getText(row, columnCount - 1) for row in range(rowCount)):
            columnCount -= 1

        strengths = [History.emptydict() for _ in range(columnCount)]
        phases = dict()
        for row in range(rowCount):
            name = self.tableWidget.verticalHeaderItem(row).text()
            phase_strs = [self.tableWidget.getText(row, column) for column in range(columnCount)]
            if not any(phase_strs):
                continue

            local_strengths, local_phases = run_stuff(name, phase_strs, args)
            strengths = [a | b for a, b in zip(strengths, local_strengths)]
            phases[name] = local_phases

        plot_graphs(strengths, phases = phases)

        return strengths

    def updateWidgets(self):
        self.tableWidget.update()
        self.tableWidget.repaint()
        self.update()
        self.repaint()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gallery = PavlovianApp()
    gallery.show()
    sys.exit(app.exec())

import sys
import os
from collections import defaultdict
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import *
from Experiment import RWArgs, create_group_and_phase, run_group_experiments, group_results, Phase
from Plots import show_plots, generate_figures
from Strengths import History

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib import pyplot

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

        self.adaptive_types = ['linear', 'exponential', 'mack', 'hall', 'macknhall', 'dualV', 'newDualV', 'lepelley', 'dualmack', 'hybrid']
        self.current_adaptive_type = None
        self.inset_text_column_index = None

        self.originalPalette = QApplication.palette()

        self.phase = 1
        self.numPhases = 0
        self.figures = []
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

        self.plotBox = QGroupBox('Plot')
        self.plotBoxLayout = QVBoxLayout()

        self.plotCanvas = FigureCanvasQTAgg()

        self.phaseBox = QGroupBox()

        self.phaseBoxLayout = QGridLayout()
        self.leftPhaseButton = QPushButton('<')
        self.leftPhaseButton.clicked.connect(self.prevPhase)

        self.phaseInfo = QLabel('')
        self.rightPhaseButton = QPushButton('>')
        self.rightPhaseButton.clicked.connect(self.nextPhase)

        self.phaseBoxLayout.addWidget(self.leftPhaseButton, 0, 0, 1, 1)
        self.phaseBoxLayout.addWidget(self.phaseInfo, 0, 1, 1, 4, Qt.AlignmentFlag.AlignCenter)
        self.phaseBoxLayout.addWidget(self.rightPhaseButton, 0, 6, 1, 1)
        self.phaseBox.setLayout(self.phaseBoxLayout)

        self.plotBoxLayout.addWidget(self.plotCanvas, stretch = 1)
        self.plotBoxLayout.addWidget(self.phaseBox)
        self.plotBox.setLayout(self.plotBoxLayout)

        mainLayout = QGridLayout()
        mainLayout.addWidget(self.tableWidget, 0, 0, 1, 6)
        mainLayout.addWidget(self.parametersGroupBox, 1, 0, 1, 1)
        mainLayout.addWidget(self.plotBox, 1, 1, 1, 4)
        mainLayout.addWidget(self.adaptiveTypeGroupBox, 1, 5, 1, 1)
        self.setLayout(mainLayout)

        self.setWindowTitle("🐕🔔")
        self.restoreDefaultParameters()

    def openFileDialog(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Open File', './Experiments')
        self.tableWidget.loadFile([x.strip() for x in open(file)])
        self.refreshExperiment()

    def createAdaptiveTypeGroupBox(self):
        self.adaptiveTypeGroupBox = QGroupBox("Adaptive Type")

        self.fileButton = QPushButton('Load file')
        self.fileButton.clicked.connect(self.openFileDialog)

        self.saveButton = QPushButton("Save Experiment")
        self.saveButton.clicked.connect(self.saveExperiment)

        self.adaptivetypeComboBox = QComboBox(self)
        self.adaptivetypeComboBox.addItems(self.adaptive_types)
        self.adaptivetypeComboBox.activated.connect(self.changeAdaptiveType)

        self.plotAlphaCheckbox = QCheckBox('Plot α')
        self.plotMnHCheckbox = QCheckBox("Mack'n'Hall")
        
        self.plotTickBoxesLayout = QHBoxLayout()
        self.plotTickBoxesLayout.addWidget(self.plotAlphaCheckbox)
        self.plotTickBoxesLayout.addWidget(self.plotMnHCheckbox)
        self.plotTickBoxes = QGroupBox('')
        self.plotTickBoxes.setLayout(self.plotTickBoxesLayout)

        self.setDefaultParamsButton = QPushButton("Restore Default Parameters")
        self.setDefaultParamsButton.clicked.connect(self.restoreDefaultParameters)

        self.refreshButton = QPushButton("Refresh")
        self.refreshButton.clicked.connect(self.refreshExperiment)

        self.printButton = QPushButton("Plot")
        self.printButton.clicked.connect(self.plotExperiment)

        layout = QVBoxLayout()
        layout.addWidget(self.fileButton)
        layout.addWidget(self.saveButton)
        layout.addWidget(self.adaptivetypeComboBox)
        layout.addWidget(self.plotTickBoxes)
        layout.addWidget(self.setDefaultParamsButton)
        layout.addWidget(self.refreshButton)
        layout.addWidget(self.printButton)
        layout.addStretch(1)
        self.adaptiveTypeGroupBox.setLayout(layout)

    def saveExperiment(self):
        default_directory = os.path.join(os.getcwd(), 'Experiments')
        os.makedirs(default_directory, exist_ok=True)
        default_file_name = os.path.join(default_directory, "experiment.rw")

        fileName, _ = QFileDialog.getSaveFileName(self, "Save Experiment", default_file_name, "RW Files (*.rw);;All Files (*)")
        if not fileName:
            return

        if not fileName.endswith(".rw"):
            fileName += ".rw"

        rowCount = self.tableWidget.rowCount()
        columnCount = self.tableWidget.columnCount()
        while columnCount > 0 and not any(self.tableWidget.getText(row, columnCount - 1) for row in range(rowCount)):
            columnCount -= 1

        lines = []
        for row in range(rowCount):
            name = self.tableWidget.verticalHeaderItem(row).text()
            phase_strs = [self.tableWidget.getText(row, column) for column in range(columnCount)]
            if not any(phase_strs):
                continue

            lines.append(name + '|' + '|'.join(phase_strs))

        with open(fileName, 'w') as file:
            for line in lines:
                file.write(line + '\n')

    def changeAdaptiveType(self):
        self.current_adaptive_type = self.adaptivetypeComboBox.currentText()

        widgets_to_enable = {
            'linear': ['alpha', 'lamda', 'beta'],
            'exponential': ['alpha', 'lamda', 'beta'],
            'mack': ['alpha', 'lamda', 'beta', 'thetaE', 'thetaI'],
            'hall': ['lamda', 'beta', 'gamma', 'thetaE', 'thetaI'],
            'macknhall': ['alpha', 'lamda', 'beta', 'gamma', 'window_size'],
            'dualV': ['alpha', 'lamda', 'beta', 'betan', 'gamma'],
            'newDualV': ['alpha', 'lamda', 'beta', 'betan', 'gamma'],
            'lepelley': ['alpha', 'lamda', 'beta', 'betan', 'gamma', 'thetaE', 'thetaI'],
            'dualmack': ['alpha', 'lamda', 'beta', 'betan'],
            'hybrid': ['alpha', 'lamda', 'beta', 'betan', 'gamma', 'thetaE', 'thetaI'],
        }

        for key in ['alpha', 'lamda', 'beta', 'betan', 'gamma', 'thetaE', 'thetaI', 'window_size']:
            widget = getattr(self, f'{key}').box
            widget.setDisabled(True)

        for key in widgets_to_enable[self.current_adaptive_type]:
            widget = getattr(self, f'{key}').box
            widget.setDisabled(False)

        self.refreshExperiment()

    def createParametersGroupBox(self):
        self.parametersGroupBox = QGroupBox("Parameters")

        class DualLabel:
            def __init__(self, text, layout, parent, font = None):
                self.label = QLabel(text)
                self.box = QLineEdit()
                self.box.returnPressed.connect(parent.refreshExperiment)

                if font is not None:
                    self.label.setFont(QFont(font))

                layout.addRow(self.label, self.box)

        params = QFormLayout()
        self.alpha = DualLabel("α ", params, self, 'Monospace')
        self.alpha_mack = DualLabel("αᴹ", params, self, 'Monospace')
        self.alpha_hall = DualLabel("αᴴ", params, self, 'Monospace')
        self.lamda = DualLabel("λ ", params, self, 'Monospace')
        self.beta = DualLabel("β⁺", params, self, 'Monospace')
        self.betan = DualLabel("β⁻", params, self, 'Monospace')
        self.gamma = DualLabel("γ ", params, self, 'Monospace')
        self.thetaE = DualLabel("θᴱ", params, self, 'Monospace')
        self.thetaI = DualLabel("θᴵ", params, self, 'Monospace')
        self.window_size = DualLabel("Window Size", params, self)
        self.num_trials = DualLabel("Number Trials", params, self)

        params.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

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
            widget = getattr(self, f'{key}').box
            widget.setText(value)

    @staticmethod
    def floatOrNone(text: str) -> None | float:
        if text == '':
            return None
        return float(text)

    def generateResults(self) -> tuple[dict[str, History], dict[str, list[Phase]], RWArgs]:
        self.current_adaptive_type = self.adaptivetypeComboBox.currentText()

        args = RWArgs(
            adaptive_type = self.current_adaptive_type,

            alphas = defaultdict(lambda: float(self.alpha.box.text())),
            alpha = float(self.alpha.box.text()),
            alpha_mack = self.floatOrNone(self.alpha_mack.box.text()),
            alpha_hall = self.floatOrNone(self.alpha_hall.box.text()),

            beta = float(self.beta.box.text()),
            beta_neg = float(self.betan.box.text()),
            lamda = float(self.lamda.box.text()),
            gamma = float(self.gamma.box.text()),
            thetaE = float(self.thetaE.box.text()),
            thetaI = float(self.thetaI.box.text()),

            window_size = int(self.window_size.box.text()),
            num_trials = int(self.num_trials.box.text()),

            plot_alpha = self.plotAlphaCheckbox.checkState() == Qt.CheckState.Checked,
            plot_macknhall = self.plotMnHCheckbox.checkState() == Qt.CheckState.Checked,

            use_configurals = False,
            xi_hall = 0.5,
        )

        rowCount = self.tableWidget.rowCount()
        columnCount = self.tableWidget.columnCount()
        while columnCount > 0 and not any(self.tableWidget.getText(row, columnCount - 1) for row in range(rowCount)):
            columnCount -= 1

        strengths = [History.emptydict() for _ in range(columnCount)]
        phases = dict()
        for row in range(rowCount):
            name = self.tableWidget.verticalHeaderItem(row).text()
            phase_strs = [self.tableWidget.getText(row, column) for column in range(columnCount)]
            if not any(phase_strs):
                continue

            group, local_phases = create_group_and_phase(name, phase_strs, args)
            results = run_group_experiments(group, local_phases, args.num_trials)
            local_strengths = group_results(results, name, args)

            strengths = [a | b for a, b in zip(strengths, local_strengths)]
            phases[name] = local_phases

        return strengths, phases, args

    def refreshExperiment(self):
        for fig in self.figures:
            pyplot.close(fig)

        strengths, phases, args = self.generateResults()
        self.numPhases = max(len(v) for v in phases.values())
        self.phase = min(self.phase, self.numPhases)
        print(self.phase, self.numPhases)

        self.figures = generate_figures(
            strengths,
            phases = phases,
            plot_alpha = args.plot_alpha,
            plot_macknhall = args.plot_macknhall,
        )
        self.refreshFigure()

    def refreshFigure(self):
        # pyplot.ion()
        self.plotCanvas.setMinimumSize(800, 400)
        print(f'Phase is {self.phase} {self.numPhases}')
        self.plotCanvas.figure = self.figures[self.phase - 1]
        self.plotCanvas.draw()

        self.phaseInfo.setText(f'Phase {self.phase}/{self.numPhases}')

    def plotExperiment(self):
        strengths, phases, args = self.generateResults()
        show_plots(
            strengths,
            phases = phases,
            plot_alpha = args.plot_alpha,
            plot_macknhall = args.plot_macknhall,
        )

        return strengths

    def updateWidgets(self):
        self.tableWidget.update()
        self.tableWidget.repaint()
        self.update()
        self.repaint()

    def prevPhase(self):
        if self.phase == 1:
            return

        self.phase -= 1
        self.refreshFigure()
    
    def nextPhase(self):
        if self.phase >= self.numPhases:
            return

        self.phase += 1 
        self.refreshFigure()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gallery = PavlovianApp()
    gallery.show()
    sys.exit(app.exec())

import os
import re
import sys

from argparse import ArgumentParser
from collections import defaultdict
from contextlib import nullcontext
from itertools import chain, zip_longest
from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import *

from Experiment import RWArgs, Experiment, Phase
from Plots import show_plots, generate_figures
from Environment import StimulusHistory
from AdaptiveType import AdaptiveType

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib import pyplot

class CoolTable(QWidget):
    def __init__(self, rows: int, cols: int, parent: None | QWidget = None):
        super().__init__(parent = parent)

        self.freeze = True

        self.table = QTableWidget(rows, cols)
        self.table.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

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

    def setHeaders(self):
        self.table.setVerticalHeaderItem(0, QTableWidgetItem('Control'))
        self.table.setVerticalHeaderItem(1, QTableWidgetItem('Test'))

        if self.rowCount() > 2:
            for e in range(1, self.rowCount()):
                self.table.setVerticalHeaderItem(e, QTableWidgetItem(f'Test {e}'))

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
        self.setHeaders()

        width = 150 * (1 + self.columnCount())
        height = 30 * (1 + self.rowCount())
        self.table.setFixedSize(width, height)
        self.rightPlus.setFixedHeight(height)
        self.bottomPlus.setFixedWidth(width)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

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

            self.table.setVerticalHeaderItem(row, QTableWidgetItem(name))
            for col, phase in enumerate(phase_strs):
                self.table.setItem(row, col, QTableWidgetItem(phase))

        self.updateSizes()
        self.freeze = False

class PavlovianApp(QDialog):
    def __init__(self, dpi = 200, parent=None):
        super(PavlovianApp, self).__init__(parent)

        self.adaptive_types = AdaptiveType.types().keys()
        self.current_adaptive_type = None
        self.inset_text_column_index = None

        self.phaseNum = 1
        self.numPhases = 0
        self.figures = []
        self.phases = {}
        self.hidden = False
        self.dpi = dpi
        self.initUI()

        QTimer.singleShot(100, self.updateWidgets)

    def initUI(self):
        self.tableWidget = CoolTable(2, 1, parent = self)
        self.tableWidget.table.setMaximumHeight(120)
        self.tableWidget.onCellChange(self.refreshExperiment)

        self.addActionsButtons()
        self.createParametersGroupBox()

        self.plotBox = QGroupBox('Plot')

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

        self.plotBoxLayout = QVBoxLayout()
        self.plotBoxLayout.addWidget(self.plotCanvas)
        self.plotBoxLayout.addWidget(self.phaseBox)
        self.plotBoxLayout.setStretch(0, 1)
        self.plotBoxLayout.setStretch(1, 0)
        self.plotBox.setLayout(self.plotBoxLayout)

        self.adaptiveTypeButtons = self.addAdaptiveTypeButtons()

        mainLayout = QGridLayout()
        mainLayout.addWidget(self.tableWidget, 0, 0, 1, 4)
        mainLayout.addWidget(self.adaptiveTypeButtons, 1, 0, 3, 1)
        mainLayout.addWidget(self.parametersGroupBox, 1, 1, 3, 1)
        mainLayout.addWidget(self.plotBox, 1, 2, 3, 1)
        mainLayout.addWidget(self.phaseOptionsGroupBox, 1, 3, 1, 1)
        mainLayout.addWidget(self.plotOptionsGroupBox, 2, 3, 1, 1)
        mainLayout.addWidget(self.fileOptionsGroupBox, 3, 3, 1, 1)
        mainLayout.setRowStretch(0, 1)
        mainLayout.setRowStretch(1, 0)
        mainLayout.setRowStretch(2, 1)
        mainLayout.setRowStretch(3, 1)
        mainLayout.setColumnStretch(0, 0)
        mainLayout.setColumnStretch(1, 0)
        mainLayout.setColumnStretch(2, 1)
        mainLayout.setColumnStretch(3, 0)
        self.setLayout(mainLayout)

        self.setWindowTitle("PALMS Simulator")
        self.restoreDefaultParameters()

        self.adaptiveTypeButtons.children()[1].click()

        self.resize(1250, 600)

    def addAdaptiveTypeButtons(self):
        buttons = QGroupBox('Adaptive Type')
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        buttonGroup = QButtonGroup(self)
        buttonGroup.setExclusive(True)

        for i, adaptive_type in enumerate(self.adaptive_types):
            button = QPushButton(adaptive_type)
            button.adaptive_type = adaptive_type
            button.setCheckable(True)

            noMarginStyle = ""
            checkedStyle = "QPushButton:checked { background-color: lightblue; font-weight: bold; border: 2px solid #0057D8; }"
            button.setStyleSheet(noMarginStyle + checkedStyle)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            buttonGroup.addButton(button, i)
            layout.addWidget(button)

            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        buttonGroup.buttonClicked.connect(self.changeAdaptiveType)
        buttons.setLayout(layout)
        return buttons

    def loadFile(self, filename):
        lines = [x.strip() for x in open(filename)]
        self.tableWidget.loadFile(lines)

    def openFileDialog(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Open File', './Experiments')
        self.loadFile(file)
        self.refreshExperiment()

    def addActionsButtons(self):
        self.phaseOptionsGroupBox = QGroupBox('Phase Options')
        self.plotOptionsGroupBox = QGroupBox("Plot Options")
        self.fileOptionsGroupBox = QGroupBox("File Options")

        self.fileButton = QPushButton('Load file')
        self.fileButton.clicked.connect(self.openFileDialog)

        self.saveButton = QPushButton("Save Experiment")
        self.saveButton.clicked.connect(self.saveExperiment)
        
        self.expand_canvas = False

        self.plotAlphaButton = QPushButton('Plot α')
        checkedStyle = "QPushButton:checked { background-color: lightblue; font-weight: bold; border: 2px solid #0057D8; }"
        self.plotAlphaButton.setStyleSheet(checkedStyle)
        self.plotAlphaButton.setFixedHeight(50)
        self.plotAlphaButton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.plotAlphaButton.clicked.connect(self.togglePlotAlpha)
        self.plotAlphaButton.setCheckable(True)
        self.plot_alpha = False
        self.plot_macknhall = False

        self.toggleRandButton = QPushButton('Toggle Rand')
        self.toggleRandButton.clicked.connect(self.toggleRand)
        self.toggleRandButton.setCheckable(True)
        self.toggleRandButton.setStyleSheet(checkedStyle)

        self.phaseLambdaButton = QPushButton('Per-Phase λ')
        self.phaseLambdaButton.clicked.connect(self.togglePhaseLambda)
        self.phaseLambdaButton.setCheckable(True)
        self.phaseLambdaButton.setStyleSheet(checkedStyle)

        self.setDefaultParamsButton = QPushButton("Restore Default Parameters")
        self.setDefaultParamsButton.clicked.connect(self.restoreDefaultParameters)

        self.refreshButton = QPushButton("Refresh")
        self.refreshButton.clicked.connect(self.refreshExperiment)

        self.printButton = QPushButton("Plot")
        self.printButton.clicked.connect(self.plotExperiment)

        self.hideButton = QPushButton("Toggle Visibility")
        self.hideButton.clicked.connect(self.hideExperiment)

        phaseOptionsLayout = QVBoxLayout()
        phaseOptionsLayout.addWidget(self.toggleRandButton)
        phaseOptionsLayout.addWidget(self.phaseLambdaButton)
        self.phaseOptionsGroupBox.setLayout(phaseOptionsLayout)

        plotOptionsLayout = QVBoxLayout()
        plotOptionsLayout.addWidget(self.plotAlphaButton)
        plotOptionsLayout.addWidget(self.refreshButton)
        plotOptionsLayout.addWidget(self.printButton)
        plotOptionsLayout.addWidget(self.hideButton)
        self.plotOptionsGroupBox.setLayout(plotOptionsLayout)

        fileOptionsLayout = QVBoxLayout()
        fileOptionsLayout.addWidget(self.fileButton)
        fileOptionsLayout.addWidget(self.saveButton)
        fileOptionsLayout.addWidget(self.setDefaultParamsButton)
        fileOptionsLayout.addStretch()
        self.fileOptionsGroupBox.setLayout(fileOptionsLayout)

    def toggleRand(self):
        set_rand = any(p[self.phaseNum - 1].rand for p in self.phases.values())
        self.tableWidget.setRandInSelection(not set_rand)
        self.refreshExperiment()

    def hideExperiment(self):
        if self.hidden:
            self.hidden = False
        else:
            self.hidden = True
        self.hideLines()
        #for f in self.figures:
        #    f.set_canvas(self.plotCanvas)

    def togglePhaseLambda(self):
        set_lambda = any(p[self.phaseNum - 1].lamda is not None for p in self.phases.values())
        self.tableWidget.setLambdaInSelection(self.floatOrZero(self.lamda.box.text()) if not set_lambda else None)
        self.refreshExperiment()

    def togglePlotAlpha(self):
        if self.plot_alpha or self.plot_macknhall:
            self.plot_alpha = False
            self.plot_macknhall = False
            self.resize(self.width() - self.plotCanvas.width() // 2, self.height())
        else:
            if self.current_adaptive_type != 'LePelley Hybrid':
                self.plot_alpha = True
            else:
                self.plot_macknhall = True

            self.resize(self.width() + self.plotCanvas.width(), self.height())

        self.refreshExperiment()

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
            name = self.tableWidget.table.verticalHeaderItem(row).text()
            phase_strs = [self.tableWidget.getText(row, column) for column in range(columnCount)]
            if not any(phase_strs):
                continue

            lines.append(name + '|' + '|'.join(phase_strs))

        with open(fileName, 'w') as file:
            for line in lines:
                file.write(line + '\n')

    def changeAdaptiveType(self, button):
        self.current_adaptive_type = button.adaptive_type

        for key in AdaptiveType.parameters():
            widget = getattr(self, f'{key}').box
            widget.setDisabled(True)

        for key in AdaptiveType.types()[self.current_adaptive_type].parameters():
            widget = getattr(self, f'{key}').box
            widget.setDisabled(False)

        if self.plot_alpha and self.current_adaptive_type == 'LePelley Hybrid':
            self.plot_alpha = False
            self.plot_macknhall = True
        elif self.plot_macknhall and self.current_adaptive_type != 'LePelley Hybrid':
            self.plot_alpha = True
            self.plot_macknhall = False

        for key, default in AdaptiveType.types()[self.current_adaptive_type].defaults().items():
            getattr(self, key).box.setText(str(default))

        self.refreshExperiment()

    def createParametersGroupBox(self):
        self.parametersGroupBox = QGroupBox("Parameters")
        self.parametersGroupBox.setMaximumWidth(100)

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
        self.salience = DualLabel("S ", params, self, 'Monospace')
        self.window_size = DualLabel("WS", params, self)
        self.num_trials = DualLabel("№", params, self)
        self.num_trials.box.setDisabled(True)

        params.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.parametersGroupBox.setLayout(params)

    def restoreDefaultParameters(self):
        defaults = {
            'alpha': '0.1',
            'alpha_mack': '0.1',
            'alpha_hall': '0.1',
            'lamda': '1',
            'beta': '0.3',
            'betan': '0.2',
            'gamma': '0.5',
            'thetaE': '0.3',
            'thetaI': '0.1',
            'salience': '0.5',
            'window_size': '10',
            'num_trials': '100'
        }

        for key, value in defaults.items():
            widget = getattr(self, f'{key}').box
            widget.setText(value)

    # Convenience function: convert a string to a float, or return a default.
    @classmethod
    def floatOr(cls, text: str, default: None | float = None) -> None | float:
        if text == '':
            return default

        return float(text)

    # Same as floatOr(text, 0); added separately to help mypy with typing.
    @classmethod
    def floatOrZero(cls, text: str) -> float:
        f = cls.floatOr(text)
        return f or 0

    def generateResults(self) -> tuple[list[dict[str, StimulusHistory]], dict[str, list[Phase]], RWArgs]:
        args = RWArgs(
            adaptive_type = self.current_adaptive_type,

            alphas = defaultdict(lambda: self.floatOrZero(self.alpha.box.text())),
            alpha = self.floatOrZero(self.alpha.box.text()),
            alpha_mack = self.floatOr(self.alpha_mack.box.text()),
            alpha_hall = self.floatOr(self.alpha_hall.box.text()),

            beta = self.floatOrZero(self.beta.box.text()),
            beta_neg = self.floatOrZero(self.betan.box.text()),
            lamda = self.floatOrZero(self.lamda.box.text()),
            gamma = self.floatOrZero(self.gamma.box.text()),
            thetaE = self.floatOrZero(self.thetaE.box.text()),
            thetaI = self.floatOrZero(self.thetaI.box.text()),

            salience = self.floatOrZero(self.salience.box.text()),
            saliences = defaultdict(lambda: self.floatOrZero(self.salience.box.text())),

            window_size = int(self.window_size.box.text()),
            num_trials = int(self.num_trials.box.text()),

            plot_alpha = self.plot_alpha,
            plot_macknhall = self.plot_macknhall,

            xi_hall = 0.5,
        )

        rowCount = self.tableWidget.rowCount()
        columnCount = self.tableWidget.columnCount()

        strengths = [StimulusHistory.emptydict() for _ in range(columnCount)]
        phases = dict()
        for row in range(rowCount):
            name = self.tableWidget.table.verticalHeaderItem(row).text()
            phase_strs = [self.tableWidget.getText(row, column) for column in range(columnCount)]
            if not any(phase_strs):
                continue

            experiment = Experiment(name, phase_strs)
            local_strengths = experiment.run_all_phases(args)

            strengths = [a | b for a, b in zip_longest(strengths, local_strengths, fillvalue = StimulusHistory.emptydict())]
            phases[name] = experiment.phases

        return strengths, phases, args

    def refreshExperiment(self):
        for fig in self.figures:
            pyplot.close(fig)

        strengths, phases, args = self.generateResults()
        if len(phases) == 0:
            return

        self.numPhases = max(len(v) for v in phases.values())
        self.phaseNum = min(self.phaseNum, self.numPhases)
        self.phases = phases

        self.figures = generate_figures(
            strengths,
            plot_alpha = args.plot_alpha,
            plot_macknhall = args.plot_macknhall,
            dpi = self.dpi,
            ticker_threshold = True,
        )
        for f in self.figures:
            f.set_canvas(self.plotCanvas)

        self.refreshFigure()

    def refreshFigure(self):
        current_figure = self.figures[self.phaseNum - 1]
        self.plotCanvas.figure = current_figure

        self.plotCanvas.resize(self.plotCanvas.width() + 1, self.plotCanvas.height() + 1)
        self.plotCanvas.resize(self.plotCanvas.width() - 1, self.plotCanvas.height() - 1)

        self.plotCanvas.mpl_connect('pick_event', self.pickLine)

        w, h = current_figure.get_size_inches()
        self.plotCanvas.draw()
        self.tableWidget.selectColumn(self.phaseNum - 1)

        self.phaseInfo.setText(f'Phase {self.phaseNum}/{self.numPhases}')

        any_rand = any(p[self.phaseNum - 1].rand for p in self.phases.values())
        self.num_trials.box.setDisabled(not any_rand)
        self.toggleRandButton.setChecked(any_rand)

        any_lambda = any(p[self.phaseNum - 1].lamda is not None for p in self.phases.values())
        self.phaseLambdaButton.setChecked(any_lambda)

    def pickLine(self, event):
        line = event.artist
        label = line.get_label()

        for ax in line.figure.get_axes():
            for line in ax.get_lines():
                if line.get_label() == label:
                    line.set_alpha(.5 - line.get_alpha())

            for line in ax.get_legend().get_lines():
                if line.get_label() == label:
                    line.set_alpha(.75 - line.get_alpha())

        line.figure.canvas.draw_idle()

    def hideLines(self):
        for fig in self.figures:
            for ax in fig.get_axes():
                # Hide/show all lines in the plot
                for line in ax.get_lines():
                    if self.hidden:
                        line.set_alpha(0)
                    else:
                        line.set_alpha(.5)
                
                # Hide/show all lines in the legend
                legend = ax.get_legend()
                if legend is not None:
                    for legend_handle in legend.legend_handles:
                        if self.hidden:
                            legend_handle.set_alpha(.25)
                        else:
                            legend_handle.set_alpha(.5)
            
            # Redraw the figure
            fig.canvas.draw_idle()


    def plotExperiment(self):
        strengths, phases, args = self.generateResults()
        if len(phases) == 0:
            return

        figures = show_plots(
            strengths,
            phases = phases,
            plot_alpha = args.plot_alpha,
            plot_macknhall = args.plot_macknhall,
            dpi = self.dpi,
        )

        for fig in figures:
            fig.canvas.mpl_connect('pick_event', self.pickLine)
            fig.show()
        return strengths

    def updateWidgets(self):
        self.tableWidget.update()
        self.tableWidget.repaint()
        self.tableWidget.updateSizes()
        self.update()
        self.repaint()

    def prevPhase(self):
        if self.phaseNum == 1:
            return

        self.phaseNum -= 1
        self.refreshFigure()
    
    def nextPhase(self):
        if self.phaseNum >= self.numPhases:
            return

        self.phaseNum += 1
        self.refreshFigure()

def parse_args():
    args = ArgumentParser('Display a GUI for simulating models.')
    args.add_argument('--dpi', type = int, default = 200, help = 'DPI for shown and outputted figures.')
    args.add_argument('--debug', action = 'store_true', help = 'Whether to go to a debugging console if there is an exception')
    args.add_argument('load_file', nargs = '?', help = 'File to load initially')
    return args.parse_args()

def main():
    args = parse_args()

    app = QApplication(sys.argv)
    gallery = PavlovianApp(dpi = args.dpi)
    gallery.show()

    if args.load_file:
        gallery.loadFile(args.load_file)
        gallery.refreshExperiment()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()

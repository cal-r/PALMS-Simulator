from __future__ import annotations

import os
import sys

from argparse import ArgumentParser
from collections import defaultdict
from contextlib import nullcontext
from itertools import chain, zip_longest
from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import *

from Experiment import RWArgs, Experiment, Phase
from Plots import show_plots, generate_figures
from Environment import StimulusHistory
from AdaptiveType import AdaptiveType
from CoolTable import CoolTable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib import pyplot

class PavlovianApp(QDialog):
    adaptive_types: list[str]
    current_adaptive_type: str

    figures: list[pyplot.Figure]
    phases: dict[str, list[Phase]]
    phaseNum: int
    numPhases: int

    per_cs_box: dict[str, QWidget]
    per_cs_param: dict[str, dict[str, PavlovianApp.DualLabel]]
    enabled_params: set[str]

    hidden: bool
    dpi: int
    def __init__(self, dpi = 200, parent=None):
        super(PavlovianApp, self).__init__(parent)

        self.adaptive_types = AdaptiveType.types().keys()
        self.current_adaptive_type = None

        self.figures = []
        self.phases = {}
        self.phaseNum = 1
        self.numPhases = 0

        percs = ['alpha', 'alpha_mack', 'alpha_hall', 'salience']
        self.per_cs_box = {}
        self.per_cs_param = {x: {} for x in percs}
        self.enabled_params = set()

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
        self.createAlphasBox()

        self.alphasBox.setVisible(False)
        self.refreshAlphasGroupBox(set())
        self.plotBox = QGroupBox('Plot')

        self.plotCanvas = FigureCanvasQTAgg()
        self.phaseBox = QGroupBox()

        self.leftPhaseButton = QPushButton('<')
        self.leftPhaseButton.clicked.connect(self.prevPhase)

        self.phaseInfo = QLabel('')
        self.phaseInfo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.rightPhaseButton = QPushButton('>')
        self.rightPhaseButton.clicked.connect(self.nextPhase)
        
        self.iconBox = QGroupBox()

        phaseBoxLayout = QHBoxLayout()
        phaseBoxLayout.addWidget(self.leftPhaseButton)
        phaseBoxLayout.addWidget(self.phaseInfo, stretch = 1, alignment = Qt.AlignmentFlag.AlignCenter)
        phaseBoxLayout.addWidget(self.rightPhaseButton)
        self.phaseBox.setLayout(phaseBoxLayout)

        plotBoxLayout = QVBoxLayout()
        plotBoxLayout.addWidget(self.plotCanvas)
        plotBoxLayout.addWidget(self.phaseBox)
        plotBoxLayout.setStretch(0, 1)
        plotBoxLayout.setStretch(1, 0)
        self.plotBox.setLayout(plotBoxLayout)

        self.adaptiveTypeButtons = self.addAdaptiveTypeButtons()
        
        self.IconLabel = QLabel()
        self.IconLabel.setPixmap(QPixmap("resources/palms.png").scaled(150,150))
        self.IconLabel.show()
        iconBoxLayout = QVBoxLayout()
        iconBoxLayout.addWidget(self.IconLabel)
        iconBoxLayout.setStretch(0, 1)
        iconBoxLayout.setStretch(1, 0)
        self.iconBox.setLayout(iconBoxLayout)
        

        mainLayout = QGridLayout()
        mainLayout.addWidget(self.tableWidget, 0, 0, 1, 4)
        mainLayout.addWidget(self.iconBox, 0, 4, 1, 1)
        mainLayout.addWidget(self.adaptiveTypeButtons, 1, 0, 3, 1)
        mainLayout.addWidget(self.parametersGroupBox, 1, 1, 3, 1)
        mainLayout.addWidget(self.alphasBox, 1, 2, 3, 1)
        mainLayout.addWidget(self.plotBox, 1, 3, 3, 1)
        mainLayout.addWidget(self.phaseOptionsGroupBox, 1, 4, 1, 1)
        mainLayout.addWidget(self.plotOptionsGroupBox, 2, 4, 1, 1)
        mainLayout.addWidget(self.fileOptionsGroupBox, 3, 4, 1, 1)
        mainLayout.setRowStretch(0, 1)
        mainLayout.setRowStretch(1, 0)
        mainLayout.setRowStretch(2, 1)
        mainLayout.setRowStretch(3, 1)
        mainLayout.setColumnStretch(0, 0)
        mainLayout.setColumnStretch(1, 0)
        mainLayout.setColumnStretch(2, 0)
        mainLayout.setColumnStretch(3, 1)
        mainLayout.setColumnStretch(4, 0)
        self.setLayout(mainLayout)

        self.setWindowTitle("PALMS Simulator")

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

        self.toggleRandButton = QPushButton('Toggle Rand')
        self.toggleRandButton.clicked.connect(self.toggleRand)
        self.toggleRandButton.setCheckable(True)
        self.toggleRandButton.setStyleSheet(checkedStyle)

        self.phaseLambdaButton = QPushButton('Per-Phase λ')
        self.phaseLambdaButton.clicked.connect(self.togglePhaseLambda)
        self.phaseLambdaButton.setCheckable(True)
        self.phaseLambdaButton.setStyleSheet(checkedStyle)

        self.toggleAlphasButton = QPushButton('Per-CS Parameters')
        self.toggleAlphasButton.clicked.connect(self.toggleAlphasBox)
        self.toggleAlphasButton.setCheckable(True)
        self.toggleAlphasButton.setStyleSheet(checkedStyle)

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
        phaseOptionsLayout.addWidget(self.toggleAlphasButton)
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

    def togglePhaseLambda(self):
        set_lambda = any(p[self.phaseNum - 1].lamda is not None for p in self.phases.values())
        self.tableWidget.setLambdaInSelection(self.floatOrZero(self.lamda.box.text()) if not set_lambda else None)
        self.refreshExperiment()

    def togglePlotAlpha(self):
        if self.plot_alpha:
            self.plot_alpha = False
            self.resize(self.width() - self.plotCanvas.width() // 2, self.height())
        else:
            self.plot_alpha = True
            self.resize(self.width() + self.plotCanvas.width(), self.height())

        self.refreshExperiment()

    def saveExperiment(self):
        default_directory = os.path.join(os.getcwd(), 'Experiments')
        os.makedirs(default_directory, exist_ok = True)
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
        self.enabled_params = set(AdaptiveType.types()[self.current_adaptive_type].parameters())
        self.enableParams()

        for key, default in AdaptiveType.types()[self.current_adaptive_type].defaults().items():
            getattr(self, key).box.setText(str(default))
            if key in self.per_cs_param:
                for pair in self.per_cs_param[key].values():
                    pair.box.setText(str(default))

        self.refreshExperiment()

    class DualLabel:
        def __init__(self, text, parent, default, font = 'Monospace', hoverText=None):
            self.label = QLabel(text)
            self.label.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.box = QLineEdit(default)
            self.box.setMaximumWidth(40)
            self.box.returnPressed.connect(parent.refreshExperiment)
            self.label.setFont(QFont(font))
            
            if hoverText:
                self.label.setToolTip(hoverText)

        def addRow(self, layout):
            layout.addRow(self.label, self.box)
            return self

    def createParametersGroupBox(self):
        self.parametersGroupBox = QGroupBox("Parameters")
        self.parametersGroupBox.setMaximumWidth(90)

        short_names = dict(
            alpha = "α ",
            alpha_mack = "αᴹ",
            alpha_hall = "αᴴ",
            salience = "S ",
            lamda = "λ ",
            beta = "β⁺",
            betan = "β⁻",
            gamma = "γ ",
            thetaE = "θᴱ",
            thetaI = "θᴵ",
            habituation = "h ",
            rho = "ρ ",
            nu = "ν ",
            window_size = "WS",
            num_trials = "№ ",
        )
        
        descriptions = dict(
            alpha = "Learning rate of the model",
            alpha_mack = "Learning rate based on Mackintosh's model (if applicable)",
            alpha_hall = "Learning rate based on Pearce-Hall model (if applicable)",
            salience = "Salience of the stimuli",
            lamda = "Asymptote of learning",
            rho = "Parameter for MLAB hybrid",
            nu = "Parameter for MLAB hybrid",
            beta = "Associativity of US+",
            betan = "Associativity of US-",
            gamma = "Weight parameter for past trials",
            thetaE = "Excitory theta based on LePelley's model",
            thetaI = "Inhibitory theta based on LePelley's model",
            habituation = "Habituation",
            window_size = "Window size for moving average window",
            num_trials = "Number of trials per experiment (used for random trials)",
        )
        params = QFormLayout()
        for key, val in AdaptiveType.first_defaults().items():
            label = self.DualLabel(short_names[key], self, str(val), hoverText=descriptions[key]).addRow(params)
            setattr(self, key, label)
        self.num_trials.box.setGeometry(100, 120, 120, 60)
        self.num_trials.box.setDisabled(True)

        params.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.parametersGroupBox.setLayout(params)

    def createAlphasBox(self):
        layout = QHBoxLayout()
        for perc in self.per_cs_param.keys():
            boxLayout = QFormLayout()
            boxLayout.setContentsMargins(0, 0, 0, 0)
            boxLayout.setSpacing(5)

            self.per_cs_box[perc] = QWidget()
            self.per_cs_box[perc].setLayout(boxLayout)
            layout.addWidget(self.per_cs_box[perc])

        self.alphasBox = QGroupBox('Per-CS')
        self.alphasBox.setLayout(layout)

    def toggleAlphasBox(self):
        if not self.alphasBox.isVisible():
            self.alphasBox.setVisible(True)

            for perc, form in self.per_cs_param.items():
                for cs, pair in form.items():
                    pair.box.setText(getattr(self, perc).box.text())
        else:
            self.alphasBox.setVisible(False)
            self.refreshExperiment()

        self.enableParams()

    def enableParams(self):
        for key in AdaptiveType.parameters():
            widget = getattr(self, f'{key}').box
            widget.setDisabled(True)

            if key in self.per_cs_box:
                self.per_cs_box[key].setVisible(False)

        for key in self.enabled_params:
            if not self.alphasBox.isVisible() or key not in self.per_cs_param:
                widget = getattr(self, f'{key}').box
                widget.setDisabled(False)
            else:
                self.per_cs_box[key].setVisible(True)

    def refreshAlphasGroupBox(self, css: set[str]):
        shortnames = {'alpha': 'α', 'alpha_mack': 'αᴹ', 'alpha_hall': 'αᴴ', 'salience': 'S'}
        for perc, form in self.per_cs_param.items():
            val = getattr(self, perc).box.text()
            layout = self.per_cs_box[perc].layout()

            to_remove = []
            for e, (cs, pair) in enumerate(form.items()):
                if cs not in css:
                    to_remove.append((e, cs))

            for (rowNum, cs) in to_remove[::-1]:
                layout.removeRow(rowNum)
                del form[cs]

            for cs in sorted(css):
                if cs not in form:
                    form[cs] = self.DualLabel(f'{shortnames[perc]}<sub>{cs}</sub>', self, val, hoverText=f'Initial learning rate for {shortnames[perc]}<sub>{cs}</sub>').addRow(layout)

    def restoreDefaultParameters(self):
        defaults = AdaptiveType.first_defaults()
        for key, value in defaults.items():
            widget = getattr(self, f'{key}').box
            widget.setText(str(value))

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

    def csPercDict(self, perc) -> dict[str, float]:
        value = self.floatOrZero(getattr(self, perc).box.text())
        if not self.alphasBox.isVisible() or perc not in self.per_cs_param:
            return defaultdict(lambda: value)

        return {cs: self.floatOr(pair.box.text(), value) for cs, pair in self.per_cs_param[perc].items()}

    def generateResults(self) -> tuple[list[dict[str, StimulusHistory]], dict[str, list[Phase]], RWArgs]:
        args = RWArgs(
            adaptive_type = self.current_adaptive_type,

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

            alphas = self.csPercDict('alpha'),
            alpha_macks = self.csPercDict('alpha_mack'),
            alpha_halls = self.csPercDict('alpha_hall'),
            saliences = self.csPercDict('salience'),

            habituation = self.floatOrZero(self.habituation.box.text()),
            rho = self.floatOrZero(self.rho.box.text()),
            nu = self.floatOrZero(self.nu.box.text()),



            window_size = int(self.window_size.box.text()),
            num_trials = int(self.num_trials.box.text()),

            plot_alpha = self.plot_alpha and not AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
            plot_macknhall = self.plot_alpha and AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),

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
        self.tableWidget.updateSizes()

        for fig in self.figures:
            pyplot.close(fig)

        strengths, phases, args = self.generateResults()
        if len(phases) == 0:
            self.refreshAlphasGroupBox(set())
            return

        css = set.union(*[phase.cs() for group in phases.values() for phase in group])
        self.refreshAlphasGroupBox(css)

        self.numPhases = max(len(v) for v in phases.values())
        self.phaseNum = min(self.phaseNum, self.numPhases)
        self.phases = phases

        self.figures = generate_figures(
            strengths,
            plot_alpha = args.plot_alpha and not AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
            plot_macknhall = args.plot_macknhall and AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
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

        self.plotCanvas.draw()
        self.tableWidget.selectColumn(self.phaseNum - 1)

        self.phaseInfo.setText(f'{self.phaseNum}/{self.numPhases}')

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
            plot_alpha = args.plot_alpha and not AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
            plot_macknhall = args.plot_macknhall and AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
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

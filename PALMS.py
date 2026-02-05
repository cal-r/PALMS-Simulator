from __future__ import annotations

import os
os.environ["QT_API"] = "PySide6"

import logging
import sys
import Simulator

from argparse import ArgumentParser
from collections import defaultdict
from itertools import zip_longest
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QGuiApplication, QCursor
from PySide6.QtWidgets import *

from Experiment import RWArgs, Experiment, Phase
from Plots import generate_figures, save_plots
from Environment import StimulusHistory, Stimulus
from Models import Model
from CoolTable import CoolTable
from GUIUtils import *

from PySide6.QtWidgets import QLabel, QLineEdit, QMainWindow, QMessageBox, QWidget

class PavlovianApp(QMainWindow):
    models: list[str]
    current_model: str

    figures: list # list[pyplot.Figure]
    strengths: list[dict[str, StimulusHistory]]
    phases: dict[str, list[Phase]]
    phaseNum: int
    numPhases: int

    params: dict[str, 'PavlovianApp.DualLabel']

    per_cs_box: dict[str, QWidget]
    per_cs_param: dict[str, dict[str, 'PavlovianApp.DualLabel']]
    enabled_params: set[str]

    configural_cues: bool

    legend_page: int
    line_hidden: dict[str, bool]
    plot_alpha: bool
    plot_part_stimuli: bool
    show_legend: bool

    out_of_range: dict[str, tuple[float, float, float]]

    max_workers: Optional[int]
    screenshot_ready: bool
    dpi: int

    initial_file: None | str

    def __init__(
        self,
        dpi = None,
        screenshot_ready = False,
        parent = None,
        smoke_test = False,
        max_workers = None,
        initial_file = None,
    ):
        super(PavlovianApp, self).__init__(parent)

        self.called_refresh = False

        self.initial_file = initial_file

        self.models = list(Model.types().keys())
        self.current_model = None

        self.figures = []
        self.strengths = []
        self.phases = {}
        self.phaseNum = 1
        self.numPhases = 0

        self.params = {}

        percs = [
            'alpha',
            'alpha_mack',
            'alpha_hall',
            'salience',
            # 'habituation',
        ]
        self.per_cs_box = {}
        self.per_cs_param = {x: {} for x in percs}
        self.enabled_params = set()

        self.configural_cues = False
        self.plot_alpha = False
        self.plot_part_stimuli = False
        self.show_legend = True

        self.out_of_range = {}

        self.legend_page = 0
        self.line_hidden = {}
        self.dpi = dpi
        self.max_workers = max_workers
        self.screenshot_ready = screenshot_ready

        self.initUI()
        QTimer.singleShot(100, self.updateWidgets)

        if smoke_test:
            def run_smoke_test():
                logging.info('Setting single shot smoke test for 60 seconds')
                QTimer.singleShot(60000, self.closeProgram)

            QTimer.singleShot(0, run_smoke_test)

    def initUI(self):
        logging.info(f'Init UI using {QGuiApplication.platformName()}')
        self.tableWidget = CoolTable(2, 1, parent = self)
        self.tableWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.parametersGroupBox = ParametersGroupBox(self)
        self.parametersGroupBox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.alphasBox = AlphasBox(self)
        self.alphasBox.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)

        aboutButton = AboutButton(self)

        self.adaptiveTypeButtons = AdaptiveTypeButtons(self)
        self.adaptiveTypeButtons.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        iconLabel = QLabel(self)
        iconLabel.setPixmap(self.getPixmap('palms.png'))
        iconLabel.setScaledContents(True)
        iconLabel.setFixedSize(120, 120)
        iconLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        iconLabel.setToolTip('Pavlovian\N{bellhop bell} \N{dog face} Associative\N{handshake} Learning\N{brain} Models\N{bar chart} Simulator\N{desktop computer}.')

        self.plotBox = PlotBox(self)
        self.plotBox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.plotCanvas = self.plotBox.plotCanvas

        self.actionButtons = ActionButtons(self)
        self.actionButtons.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.tableWidget.connectPrefixes(self.parametersGroupBox.enablePerPhaseParameters)
        self.tableWidget.connectPrefixes(self.actionButtons.enablePerPhaseParameters)

        mainLayout = QGridLayout()
        mainLayout.setContentsMargins(5, 5, 0, 5)
        mainLayout.setSpacing(0)
        mainLayout.addWidget(self.tableWidget, 0, 0, 1, 4)
        mainLayout.addWidget(iconLabel, 0, 4, 1, 1, alignment = Qt.AlignmentFlag.AlignCenter)
        mainLayout.addWidget(self.adaptiveTypeButtons, 1, 0, 4, 1)
        mainLayout.addWidget(self.parametersGroupBox, 1, 1, 4, 1)
        mainLayout.addWidget(self.alphasBox, 1, 2, 4, 1)
        mainLayout.addWidget(self.plotBox, 1, 3, 4, 1)
        mainLayout.addWidget(self.actionButtons, 1, 4, 3, 1)
        mainLayout.addWidget(aboutButton, 4, 4, 1, 1)
        mainLayout.setRowStretch(0, 0)
        mainLayout.setRowStretch(1, 1)
        mainLayout.setRowStretch(2, 0)
        mainLayout.setRowStretch(3, 0)
        mainLayout.setRowStretch(4, 0)
        mainLayout.setColumnStretch(0, 0)
        mainLayout.setColumnStretch(1, 0)
        mainLayout.setColumnStretch(2, 0)
        mainLayout.setColumnStretch(3, 1)
        mainLayout.setColumnStretch(4, 0)
        centralWidget = QWidget(self)
        centralWidget.setLayout(mainLayout)
        centralWidget.setObjectName('CentralWidget')
        self.setCentralWidget(centralWidget)

        self.setWindowTitle("PALMS Simulator")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMaximizeButtonHint)
        self.adaptiveTypeButtons.buttonGroup.button(0).click()

    def loadFile(self, filename):
        logging.info(f'Load file with DPI {self.dpi}.')
        lines = []
        changes = {}
        percs_changes = {}
        for line in open(filename):
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            if not line.startswith('@'):
                lines.append(line.strip())
                continue

            for prop in line.strip('@').split(';'):
                name, value = prop.split('=')

                replacements = {'betap': 'beta', 'lambda': 'lamda', 'model': 'model'}
                name = replacements.get(name, name)

                if name == 'model':
                    value = value.replace('LePelley', 'Le Pelley')
                    value = value.replace('Rescorla Wagner w/ Variable Learning Rate', 'MLAB Model')
                    self.adaptiveTypeButtons.clickAdaptiveTypeButton(value)
                elif name == 'configural_cues':
                    self.actionButtons.configuralButton.click()
                elif '_' in name and name not in ('alpha_mack', 'alpha_hall', 'num_trials'):
                    percs_changes[name] = value
                else:
                    changes[name] = value


        self.tableWidget.loadFile(lines)

        for name, value in changes.items():
            self.params[name].setText(value, set_modified = True)

        if percs_changes:
            if not self.alphasBox.isVisible():
                self.actionButtons.toggleAlphasButton.click()

            values = {tuple(key.rsplit('_', 1)): val for key, val in percs_changes.items()}
            self.alphasBox.refresh(values)

        elif self.alphasBox.isVisible():
            self.actionButtons.toggleAlphasButton.click()

        self.refreshExperiment()

    def getPixmap(self, filename, scale = 1):
        here = Path(__file__).resolve().parent
        pixmap = QPixmap(str(here / "resources" / filename), flags = Qt.ImageConversionFlag.NoFormatConversion)
        return pixmap.scaled(int(150 * scale), int(150 * scale), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    class DualLabel:
        label: QLabel
        box: QLineEdit
        hoverText: str

        long_name: str

        parent: QWidget

        def __init__(self, text, parent, default, font = 'Monospace', hoverText = None, maximumWidth = 40, long_name: str = ''):
            self.parent = parent

            self.label = QLabel(text, parent)
            self.label.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.box = QLineEdit(default, parent)
            self.box.setMaximumWidth(maximumWidth)
            self.box.returnPressed.connect(self.changeText)
            self.label.setFont(QFont(font))

            self.box.setModified(False)
            self.long_name = long_name

            self.hoverText = hoverText
            if hoverText:
                self.label.setToolTip(hoverText)

            # self.label.setStyleSheet('border: 2px solid red')
            # self.box.setStyleSheet('border: 2px solid red')

        # Programatically set the text of this DualLabel.
        def setText(self, text: str, set_modified: None | bool = None):
            self.box.setText(text)
            self.checkBounds()

            if set_modified is not None:
                self.box.setModified(set_modified)

        def addRow(self, layout):
            layout.addRow(self.label, self.box)
            return self

        def setDisabled(self, disabled):
            self.box.setDisabled(disabled)
            self.checkBounds()

        def checkBounds(self):
            model = self.parent.current_model
            lower, upper = Model.base(model).bounds().get(self.long_name, (-float('inf'), float('inf')))
            value = float(self.box.text())

            if not self.box.isEnabled() or value >= lower and value <= upper:
                self.parent.removeOutOfRange(self.label.text())
            else:
                self.parent.addOutOfRange(self.label.text(), value, lower, upper)

        # Connected function to text change.
        def changeText(self):
            self.box.setModified(True)
            self.checkBounds()
            self.parent.refreshExperiment()

    def enableParams(self):
        for key in Model.parameters():
            self.params[key].setDisabled(True)

            if key in self.per_cs_box:
                self.per_cs_box[key].setVisible(False)

        for key in self.enabled_params:
            if not self.alphasBox.isVisible() or key not in self.per_cs_param:
                widget = self.params[key].setDisabled(False)
            else:
                self.per_cs_box[key].setVisible(True)

    # Convenience function: convert a string to a float, or return None if empty.
    @classmethod
    def floatOrNone(cls, text: str) -> None | float:
        if text == '':
            return None

        return float(text)

    # Convenience function: convert a string to a float, or return a default value if empty.
    @classmethod
    def floatOr(cls, text: str, default: float) -> float:
        if text == '':
            return default

        return float(text)

    def csPercDict(self, perc) -> dict[str, float]:
        value = self.floatOr(self.params[perc].box.text(), 0)
        if not self.alphasBox.isVisible() or perc not in self.per_cs_param:
            return defaultdict(lambda: value)

        return {cs: self.floatOr(pair.box.text(), value) for cs, pair in self.per_cs_param[perc].items()}

    def packArgs(self) -> RWArgs:
        should_plot_macknhall = Model.types()[self.current_model].should_plot_macknhall()
        return RWArgs(
            model = self.current_model,

            alpha = self.floatOr(self.params['alpha'].box.text(), 0),
            alpha_mack = self.floatOrNone(self.params['alpha_mack'].box.text()),
            alpha_hall = self.floatOrNone(self.params['alpha_hall'].box.text()),

            beta = self.floatOr(self.params['beta'].box.text(), 0),
            beta_neg = self.floatOr(self.params['betan'].box.text(), 0),
            lamda = self.floatOr(self.params['lamda'].box.text(), 0),
            gamma = self.floatOr(self.params['gamma'].box.text(), 0),
            thetaE = self.floatOr(self.params['thetaE'].box.text(), 0),
            thetaI = self.floatOr(self.params['thetaI'].box.text(), 0),

            salience = self.floatOr(self.params['salience'].box.text(), 0),

            configural_cues = self.configural_cues,
            part_stimuli = self.plot_part_stimuli,

            alphas = self.csPercDict('alpha'),
            alpha_macks = self.csPercDict('alpha_mack'),
            alpha_halls = self.csPercDict('alpha_hall'),

            saliences = self.csPercDict('salience'),

            # Data for MLAB Hybrid.
            habituations = defaultdict(lambda: 0),
            habituation = 0,
            rho = 0,
            nu = 0,
            kay = 0,
            # habituations = self.csPercDict('habituation'),
            # rho = self.floatOr(self.params['rho'].box.text(), 0),
            # nu = self.floatOr(self.params['nu'].box.text(), 0),
            # habituation = self.floatOr(self.params['habituation'].box.text(), 0),
            # kay = self.floatOr(self.params['kay'].box.text(), 0),

            num_trials = int(self.params['num_trials'].box.text()),

            should_plot_macknhall = should_plot_macknhall,

            plot_alpha = self.plot_alpha and not should_plot_macknhall,
            plot_macknhall = self.plot_alpha and should_plot_macknhall,

            xi_hall = 0.5,
        )

    def generateResults(self, args: Optional[RWArgs] = None) -> tuple[list[dict[str, StimulusHistory]], dict[str, list[Phase]]]:
        assert self.called_refresh, 'RefreshExperiment never called.'

        # Tempoary code; please delete.
        if args is None:
            logging.warning('Warning: empty args in generateResults.')
            args = self.packArgs()

        rowCount = self.tableWidget.rowCount()
        columnCount = self.tableWidget.columnCount()

        strengths = [StimulusHistory.emptydict() for _ in range(columnCount)]
        phases = dict()
        for row in range(rowCount):
            name = self.tableWidget.table.verticalHeaderItem(row).text()
            phase_strs = [self.tableWidget.getText(row, column) for column in range(columnCount)]
            if not any(phase_strs):
                continue

            try:
                experiment = Experiment(name, phase_strs, max_workers = self.max_workers)
            except ValueError as e:
                error = str(e)
                if len(error) > 250:
                    error = error[:250] + '…'
                QMessageBox.critical(self, 'Syntax Error', str(error))

                # Apologies for the Go-like code. This should be a sum type!
                return [], {}

            local_strengths = experiment.run_all_phases(args)

            strengths = [a | b for a, b in zip_longest(strengths, local_strengths, fillvalue = StimulusHistory.emptydict())]
            phases[name] = experiment.phases

        return strengths, phases

    def plotExperiment(self):
        if len(self.phases) == 0:
            return

        # Get the locations of the legends of all axes of all figures.
        self.legend_locs = [[ax.get_legend()._loc for ax in fig.get_axes()] for fig in self.figures]
        self.legend_locs = (self.legend_locs + self.numPhases * [[]])[:self.numPhases]

        # We need to regenerate the figures due to matplotlib canvas manager issues.
        args = self.packArgs()
        figures = generate_figures(
            self.strengths,
            phases = self.phases,
            plot_V = not args.plot_alpha and not args.plot_macknhall,
            plot_alpha = args.plot_alpha and not Model.types()[self.current_model].should_plot_macknhall(),
            plot_macknhall = args.plot_macknhall and Model.types()[self.current_model].should_plot_macknhall(),
            dpi = self.dpi,
            singular_legend = not self.show_legend,
            plot_stimuli = [k for k, v in self.line_hidden.items() if not v],
            legend_locs = self.legend_locs,
        )

        for fig in figures:
            fig.canvas.mpl_connect('pick_event', self.pickLine)
            fig.show()

    def addOutOfRange(self, param: str, value: float, lower: float, upper: float):
        self.out_of_range[param] = (value, lower, upper)

    def removeOutOfRange(self, param: str):
        self.out_of_range.pop(param, None)

    def refreshExperiment(self, caller = None):
        if caller is not None:
            logging.info(f'Called refreshExperiment from {caller}')

        self.called_refresh = True

        if self.out_of_range:
            header = f'Parameters out of range for {self.current_model}:'
            messages = []
            for param, (value, lower, upper) in self.out_of_range.items():
                messages.append(f"<li style='margin:2px 0'>{param} = {value} ∉ [{lower}, {upper}]</li>")

            if len(messages) > 5:
                messages = messages[:5] + [' ', f'and {len(messages) - 5} other parameter{'' if len(messages) == 6 else 's'}.']

            text = header + "<ul style='list-style-type:none; margin:4px 0; padding-left:48px;'>" + ''.join([f'<li>{m}</li>' for m in messages]) + '</ul>'
            warning = QMessageBox(
                QMessageBox.Warning,
                'Parameters out of range',
                text,
                parent = self
            )
            warning.setTextFormat(Qt.RichText)
            warning.exec()

        self.plotBox.phaseBox.setLoading()
        self.tableWidget.updateSizes()

        args = self.packArgs()
        self.strengths, self.phases = self.generateResults(args)

        self.refreshFigures()

    def refreshFigures(self):
        from matplotlib import pyplot
        if len(self.phases) == 0:
            self.alphasBox.clear()
            self.numPhases = 1
            self.phaseNum = 1
            self.figures = [pyplot.Figure()]
            self.refreshCurrentFigure()
            return

        self.css = set.union(*[phase.cs() for group in self.phases.values() for phase in group])
        self.alphasBox.refresh(self.css)

        self.numPhases = max(len(v) for v in self.phases.values())
        self.phaseNum = min(self.phaseNum, self.numPhases)

        # Get the locations of the legends of all axes of all figures.
        self.legend_locs = [[ax.get_legend()._loc for ax in fig.get_axes()] for fig in self.figures]
        self.legend_locs = (self.legend_locs + self.numPhases * [[]])[:self.numPhases]

        for fig in self.figures:
            pyplot.close(fig)

        args = self.packArgs()
        self.figures = generate_figures(
            self.strengths,
            plot_V = not args.plot_alpha and not args.plot_macknhall,
            plot_alpha = args.plot_alpha and not Model.types()[self.current_model].should_plot_macknhall(),
            plot_macknhall = args.plot_macknhall and Model.types()[self.current_model].should_plot_macknhall(),
            dpi = self.dpi,
            singular_legend = not self.show_legend,
            legend_locs = self.legend_locs,
        )

        line_names = set.union(*[set(x.keys()) for x in self.strengths])
        self.line_hidden = {k: self.line_hidden.get(k, False) for k in line_names}

        self.refreshCurrentFigure()

    def refreshCurrentFigure(self):
        current_figure = self.figures[self.phaseNum - 1]
        self.plotCanvas.figure = current_figure
        current_figure.set_canvas(self.plotCanvas)
        self.plotCanvas.mpl_connect('pick_event', self.pickLine)
        self.plotCanvas.mpl_connect('motion_notify_event', self.mouseMove)

        for ax in current_figure.get_axes():
            for line in ax.get_lines():
                label = line.get_label().split(': ')[-1].strip()
                if label in self.line_hidden:
                    line.set_alpha(0 if self.line_hidden[label] else 1)

            if ax.get_legend() is not None:
                if ax.get_legend().paginated:
                    self.legend_page = max(0, min(self.legend_page, ax.get_legend().paginator.num_pages - 1))
                    ax.get_legend().paginator.showPage(ax, self.legend_page)

                for line in ax.get_legend().get_lines():
                    label = line.get_label().split(': ')[-1]
                    if label in self.line_hidden:
                        line.set_alpha(.25 if self.line_hidden[label] else 1)

        self.plotCanvas.resize(self.plotCanvas.width() + 1, self.plotCanvas.height() + 1)
        self.plotCanvas.resize(self.plotCanvas.width() - 1, self.plotCanvas.height() - 1)

        self.plotCanvas.draw()

        self.tableWidget.selectColumn(self.phaseNum - 1)
        self.plotBox.phaseBox.setInfo(self.phaseNum, self.numPhases)

        fig = self.plotCanvas.figure

    def pickLine(self, event):
        label = event.artist.get_label().split(': ')[-1].strip()

        match label:
            case '':
                return
            case 'Next':
                self.legend_page += 1
            case 'Prev':
                self.legend_page -= 1
            case _:
                self.line_hidden[label] = not self.line_hidden[label]

        self.refreshCurrentFigure()

    def mouseMove(self, event):
        if not event.inaxes:
            return

        yaxis = event.inaxes.yaxis.label._text
        if yaxis.endswith('Strength'):
            ylabel = 'V'
        elif yaxis.endswith('Alpha'):
            ylabel = 'α'
        else:
            ylabel = 'Y'

        self.plotBox.phaseBox.setCoordInfo(max(1 + event.xdata, 1), ylabel, event.ydata)

    def updateWidgets(self):
        if self.dpi is None:
            win = self.window()
            self.dpi = 120 * win.devicePixelRatioF()
            logging.info(f'{win.devicePixelRatioF()=:.2f} {win.physicalDpiY()=} {win.physicalDpiX()=} {win.logicalDpiY()=} {win.logicalDpiX()=}')
            logging.info(f'Using DPI {self.dpi}')

        if self.initial_file:
            self.loadFile(self.initial_file)

        self.tableWidget.updateSizes()
        self.plotBox.setInitialSize()
        self.update()
        self.repaint()

        QTimer.singleShot(0, self.resizeAndCenterWindow)

    def resizeAndCenterWindow(self):
        available = self.screen().availableGeometry()

        margin = 5
        self.resize(min(self.width(), available.width() - margin), min(self.height(), available.height() - margin))

        QTimer.singleShot(0, self.centerWindow)

    def centerWindow(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()

        fg = self.frameGeometry()
        fg.moveCenter(geo.center())

        x = max(geo.left(), min(fg.left(), geo.right() - fg.width() + 1))
        y = max(geo.top(), min(fg.top(), geo.bottom() - fg.height() + 1))

        self.move(x, y)

    def relax_size(self, elem):
        elem.setMinimumSize(0, 0)
        for child in elem.findChildren(QWidget):
            self.relax_size(child)

    def closeProgram(self):
        logging.info('Closing program')
        self.close()

    def savePlots(self, filename, width, height, singular_legend):
        if len(self.phases) == 0:
            return

        # Get the locations of the legends of all axes of all figures.
        self.legend_locs = [[ax.get_legend()._loc for ax in fig.get_axes()] for fig in self.figures]
        self.legend_locs = (self.legend_locs + self.numPhases * [[]])[:self.numPhases]

        args = self.packArgs()
        save_plots(
            self.strengths,
            phases = self.phases,
            plot_V = not args.plot_alpha and not args.plot_macknhall,
            plot_alpha = args.plot_alpha and not Model.types()[self.current_model].should_plot_macknhall(),
            plot_macknhall = args.plot_macknhall and Model.types()[self.current_model].should_plot_macknhall(),
            dpi = self.dpi,
            filename = filename,
            plot_width = width,
            plot_height = height,
            singular_legend = singular_legend,
            plot_stimuli = {k for k, v in self.line_hidden.items() if not v},
            legend_locs = self.legend_locs,
        )

def parse_args():
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'cli':
        sys.argv[0] = f'{sys.argv[0]} {sys.argv[1]}'
        sys.argv[1:] = sys.argv[2:]
        Simulator.main()
        sys.exit(0)

    parser = ArgumentParser('PALMS Simulator')
    subparsers = parser.add_subparsers(dest = 'mode', required = False)

    cli_parser = subparsers.add_parser('cli', help = f'Run PALMS command-line interface. {sys.argv[0]} cli --help for mode information.')
    gui_parser = subparsers.add_parser('gui', help = f'Run PALMS GUI interface. This is the default if no mode is selected.')

    gui_parser.add_argument('--dpi', type = int, help = 'DPI for shown and outputted figures.')
    gui_parser.add_argument('--fontsize', type = int, default = None, help = 'Fontsize of the GUI; screenshots are taken in fontsize 16.')
    gui_parser.add_argument('--fontscale', type = float, default = 1.15, help = 'Scale of the font (overriden by --fontsize).')
    gui_parser.add_argument('--screenshot-ready', action = 'store_true', help = 'Hide guide numbers for easier screenshots.')
    gui_parser.add_argument('--debug', action = 'store_true', help = 'Whether to go to a debugging console if there is an exception')
    gui_parser.add_argument('--smoke-test', action = 'store_true', help = 'Run a smoke test: open the app, log everything, wait 5 seconds, close the app.')
    gui_parser.add_argument('--verbose', '-v', action = 'store_true', help = 'Verbose logging.')
    gui_parser.add_argument('--max-workers', type = int, help = 'Maximum number of multiprocessing cores used in randomised phases. This is constrained by the total CPU count and number of trials.')
    gui_parser.add_argument('--spawn', action = 'store_true', help = 'Force spawn instead of fork for multiprocessing. This should only have an effect on Linux, and is used for debugging.')
    gui_parser.add_argument('initial_file', nargs = '?', help = 'File to load initially')

    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(parser.format_help())

    return gui_parser.parse_args()

def logScreenInfo(app: QApplication):
    logging.info(f'Logical DPI: {app.primaryScreen().logicalDotsPerInch()}.')
    logging.info(f'Platform name: {QGuiApplication.platformName()}')
    logging.info(f'Primary screen height: {app.primaryScreen().size().height()}')
    logging.info(f'Font size: {app.font().pointSizeF()}')
    logging.info(f'Physical DPI: {app.primaryScreen().physicalDotsPerInch()}.')
    logging.info(f'Device pixel ratio: {app.primaryScreen().devicePixelRatio()}.')
    logging.info(f'Available geometry: {app.primaryScreen().availableGeometry()}')
    logging.info(f'Available virtual geometry: {app.primaryScreen().availableVirtualGeometry()}')

    for envvar in ("QT_AUTO_SCREEN_SCALE_FACTOR","QT_SCALE_FACTOR", "QT_SCREEN_SCALE_FACTORS","QT_DEVICE_PIXEL_RATIO"):
        logging.info(f'Env {envvar}: {os.environ.get(envvar)}')

def defineFont(app: QApplication, fontScale: None | float, fontSize: None | int) -> QFont:
    fontSize = app.font().pointSizeF()

    if fontScale:
        fontSize *= fontScale

    if fontSize:
        fontSize = fontSize

    font = QFont()
    font.setPointSize(fontSize)
    return font

def main():
    args = parse_args()
    logging.basicConfig(level = logging.WARN, format = '[%(relativeCreated)d] %(message)s')
    if args.smoke_test or args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    if args.spawn:
        import multiprocessing
        multiprocessing.set_start_method("spawn", force = True)

    app = QApplication(sys.argv)

    app.setFont(defineFont(app, args.fontscale, args.fontsize))
    logScreenInfo(app)

    gallery = PavlovianApp(
        dpi = args.dpi,
        screenshot_ready = args.screenshot_ready,
        smoke_test = args.smoke_test,
        max_workers = args.max_workers,
        initial_file = args.initial_file,
    )
    gallery.show()
    app.processEvents()

    code = app.exec()

    sys.exit(code)

if __name__ == '__main__':
    # Handle spawn processes fine (damn you Tim Cook).
    import multiprocessing
    multiprocessing.freeze_support()

    # Close the splash screen.
    try:
        import pyi_splash
        pyi_splash.close()
    except:
        pass

    main()

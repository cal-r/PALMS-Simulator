from __future__ import annotations

import os
# os.environ["QT_QPA_PLATFORM"] = "xcb"
# os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
os.environ["QT_API"] = "PySide6"

import logging
import sys
import Simulator

from argparse import ArgumentParser
from collections import defaultdict
from itertools import zip_longest
from pathlib import Path
from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QGuiApplication
from PySide6.QtWidgets import *

from Experiment import RWArgs, Experiment, Phase
from Plots import generate_figures, save_plots
from Environment import StimulusHistory, Stimulus
from AdaptiveType import AdaptiveType
from CoolTable import CoolTable

import matplotlib
from matplotlib import pyplot

from GUIUtils import *

pyInstalled = False
try:
    import pyi_splash
    pyi_splash.close()
    pyInstalled = True
except:
    pass

class PavlovianApp(QMainWindow):
    adaptive_types: list[str]
    current_adaptive_type: str

    figures: list[pyplot.Figure]
    phases: dict[str, list[Phase]]
    phaseNum: int
    numPhases: int

    params: dict[str, PavlovianApp.DualLabel]

    per_cs_box: dict[str, QWidget]
    per_cs_param: dict[str, dict[str, PavlovianApp.DualLabel]]
    enabled_params: set[str]

    configural_cues: bool

    line_hidden: dict[str, bool]
    plot_alpha: bool
    plot_part_stimuli: bool

    dpi: int

    def __init__(self, dpi = 200, screenshot_ready = False, parent = None, smoke_test = False):
        super(PavlovianApp, self).__init__(parent)

        self.adaptive_types = AdaptiveType.types().keys()
        self.current_adaptive_type = None

        self.figures = []
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

        self.line_hidden = {}
        self.dpi = dpi
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
        self.tableWidget.table.setMaximumHeight(120)
        self.tableWidget.onCellChange(self.refreshExperiment)

        self.parametersGroupBox = ParametersGroupBox(self)

        self.alphasBox = AlphasBox(self)
        aboutButton = AboutButton(self)
        self.adaptiveTypeButtons = AdaptiveTypeButtons(self)

        iconLabel = QLabel(self)
        iconLabel.setPixmap(self.getPixmap('palms.png'))
        iconLabel.setToolTip('Pavlovian\N{bellhop bell} \N{dog face} Associative\N{handshake} Learning\N{brain} Models\N{bar chart} Simulator\N{desktop computer}.')

        self.plotBox = PlotBox(self)
        self.plotCanvas = self.plotBox.plotCanvas

        self.actionButtons = ActionButtons(self)

        mainLayout = QGridLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
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
        self.setCentralWidget(centralWidget)

        self.setWindowTitle("PALMS Simulator")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMaximizeButtonHint)
        self.adaptiveTypeButtons.buttonGroup.button(0).click()

        self.adjustSize()

        windowSize = QSize(self.width() * 1.25, self.height() * 1.1)

        screen = self.screen()
        if screen:
            windowSize = windowSize.boundedTo(screen.availableGeometry().size())

        self.resize(windowSize)

    def loadFile(self, filename):
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

                replacements = {'betap': 'beta', 'lambda': 'lamda', 'model': 'adaptive_type'}
                name = replacements.get(name, name)

                if name == 'adaptive_type':
                    self.adaptiveTypeButtons.clickAdaptiveTypeButton(value)
                elif name == 'configural_cues':
                    self.actionButtons.configuralButton.click()
                elif '_' in name and name.split('_')[-1].isupper():
                    percs_changes[name] = value
                else:
                    changes[name] = value


        self.tableWidget.loadFile(lines)

        for name, value in changes.items():
            self.params[name].setText(value, set_modified = True)

        if percs_changes:
            self.refreshExperiment()
            self.actionButtons.toggleAlphasButton.click()

            for name, value in percs_changes.items():
                perc, cs = name.rsplit('_', 1)
                self.per_cs_param[perc][cs].setText(value, set_modified = True)

    def getPixmap(self, filename):
        here = Path(__file__).resolve().parent
        pixmap = QPixmap(str(here / "resources" / filename), flags = Qt.ImageConversionFlag.NoFormatConversion)
        return pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    class DualLabel:
        label: QLabel
        box: QLineEdit
        hoverText: str
        modified: bool

        def __init__(self, text, parent, default, font = 'Monospace', hoverText = None, maximumWidth = 40):
            self.parent = parent

            self.label = QLabel(text)
            self.label.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.box = QLineEdit(default)
            self.box.setMaximumWidth(maximumWidth)
            self.box.returnPressed.connect(self.changeText)
            self.label.setFont(QFont(font))

            self.modified = False

            self.hoverText = hoverText
            if hoverText:
                self.label.setToolTip(hoverText)

        def setText(self, text: str, set_modified: None | bool = None):
            self.box.setText(text)

            if set_modified is not None:
                self.modified = set_modified

        def addRow(self, layout):
            layout.addRow(self.label, self.box)
            return self

        def changeText(self):
            self.modified = True
            self.parent.refreshExperiment()

    def enableParams(self):
        for key in AdaptiveType.parameters():
            widget = self.params[key].box
            widget.setDisabled(True)

            if key in self.per_cs_box:
                self.per_cs_box[key].setVisible(False)

        for key in self.enabled_params:
            if not self.alphasBox.isVisible() or key not in self.per_cs_param:
                widget = self.params[key].box
                widget.setDisabled(False)
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

    def generateResults(self) -> tuple[list[dict[str, StimulusHistory]], dict[str, list[Phase]], RWArgs]:
        should_plot_macknhall = AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall()
        args = RWArgs(
            adaptive_type = self.current_adaptive_type,

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
                experiment = Experiment(name, phase_strs)
            except ValueError as e:
                QMessageBox.critical(self, 'Syntax Error', str(e))

                # Apologies for the Go-like code. This should be a sum type!
                return [], {}, args

            local_strengths = experiment.run_all_phases(args)

            strengths = [a | b for a, b in zip_longest(strengths, local_strengths, fillvalue = StimulusHistory.emptydict())]
            phases[name] = experiment.phases

        return strengths, phases, args

    def plotExperiment(self):
        strengths, phases, args = self.generateResults()
        if len(phases) == 0:
            return

        figures = generate_figures(
            strengths,
            phases = phases,
            plot_V = not args.plot_alpha and not args.plot_macknhall,
            plot_alpha = args.plot_alpha and not AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
            plot_macknhall = args.plot_macknhall and AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
            dpi = self.dpi,
            ticker_threshold = True,
        )

        for fig in figures:
            fig.canvas.mpl_connect('pick_event', self.pickLine)
            fig.show()
        return strengths

    def refreshExperiment(self):
        self.tableWidget.updateSizes()

        for fig in self.figures:
            pyplot.close(fig)

        strengths, phases, args = self.generateResults()
        if len(phases) == 0:
            self.alphasBox.clear()
            self.numPhases = 1
            self.phaseNum = 1
            self.figures = [pyplot.Figure()]
            self.figures[0].set_canvas(self.plotCanvas)
            self.refreshFigure()
            return

        css = set.union(*[phase.cs() for group in phases.values() for phase in group])
        self.alphasBox.refresh(css)

        self.numPhases = max(len(v) for v in phases.values())
        self.phaseNum = min(self.phaseNum, self.numPhases)
        self.phases = phases

        self.figures = generate_figures(
            strengths,
            plot_V = not args.plot_alpha and not args.plot_macknhall,
            plot_alpha = args.plot_alpha and not AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
            plot_macknhall = args.plot_macknhall and AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
            dpi = self.dpi,
            ticker_threshold = True,
        )
        for f in self.figures:
            f.set_canvas(self.plotCanvas)

        line_names = set.union(*[set(x.keys()) for x in strengths])
        self.line_hidden = {k: self.line_hidden.get(k, False) for k in line_names}

        self.refreshFigure()

    def refreshFigure(self):
        current_figure = self.figures[self.phaseNum - 1]
        self.plotCanvas.figure = current_figure

        for ax in current_figure.get_axes():
            for line in ax.get_lines():
                label = line.get_label().split(': ')[-1].strip()
                line.set_alpha(0 if self.line_hidden[label] else 1)

            if ax.get_legend() is not None:
                for line in ax.get_legend().get_lines():
                    label = line.get_label().split(': ')[-1]
                    line.set_alpha(.25 if self.line_hidden[label] else 1)

        self.plotCanvas.resize(self.plotCanvas.width() + 1, self.plotCanvas.height() + 1)
        self.plotCanvas.resize(self.plotCanvas.width() - 1, self.plotCanvas.height() - 1)

        self.plotCanvas.mpl_connect('pick_event', self.pickLine)
        self.plotCanvas.mpl_connect('motion_notify_event', self.mouseMove)

        self.plotCanvas.draw()

        self.tableWidget.selectColumn(self.phaseNum - 1)

        self.plotBox.phaseBox.setInfo(self.phaseNum, self.numPhases)

        any_rand = any(p[self.phaseNum - 1].rand for p in self.phases.values())
        self.params['num_trials'].box.setDisabled(not any_rand)
        self.actionButtons.toggleRandButton.setChecked(any_rand)

        any_lambda = any(p[self.phaseNum - 1].lamda is not None for p in self.phases.values())
        self.actionButtons.phaseLambdaButton.setChecked(any_lambda)

        fig = self.plotCanvas.figure
        logging.info(f'{fig.dpi=}')
        logging.info(f'{fig.get_size_inches()=}')
        logging.info(f'{self.plotCanvas.get_width_height()=}')

        logging.info(f'DPI ratio: {getattr(self.plotCanvas, "_dpi_ratio", None)}')
        logging.info(f'{self.plotCanvas.devicePixelRatioF()=}')

    def pickLine(self, event):
        label = event.artist.get_label().split(': ')[-1].strip()
        if label == '':
            return

        self.line_hidden[label] = not self.line_hidden[label]
        self.refreshFigure()

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
        self.relax_size(self)
        self.tableWidget.update()
        self.tableWidget.repaint()
        self.tableWidget.updateSizes()
        self.update()
        self.repaint()

    def relax_size(self, elem):
        elem.setMinimumSize(0, 0)
        for child in elem.findChildren(QWidget):
            self.relax_size(child)

    def closeProgram(self):
        logging.info('Closing program')
        self.close()

    def savePlots(self, filename, width, height, singular_legend):
        strengths, phases, args = self.generateResults()
        if len(phases) == 0:
            return

        save_plots(
            strengths,
            phases = phases,
            plot_V = not args.plot_alpha and not args.plot_macknhall,
            plot_alpha = args.plot_alpha and not AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
            plot_macknhall = args.plot_macknhall and AdaptiveType.types()[self.current_adaptive_type].should_plot_macknhall(),
            dpi = self.dpi,
            filename = filename,
            plot_width = width,
            plot_height = height,
            singular_legend = singular_legend,
            hide_lines = {k for k, v in self.line_hidden.items() if v},
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

    gui_parser.add_argument('--dpi', type = int, default = None, help = 'DPI for shown and outputted figures.')
    gui_parser.add_argument('--fontsize', type = int, default = None, help = 'Fontsize of the GUI; screenshots are taken in fontsize 16.')
    gui_parser.add_argument('--screenshot-ready', action = 'store_true', help = 'Hide guide numbers for easier screenshots.')
    gui_parser.add_argument('--debug', action = 'store_true', help = 'Whether to go to a debugging console if there is an exception')
    gui_parser.add_argument('--smoke-test', action = 'store_true', help = 'Run a smoke test: open the app, log everything, wait 5 seconds, close the app.')
    gui_parser.add_argument('--verbose', '-v', action = 'store_true', help = 'Verbose logging.')
    gui_parser.add_argument('load_file', nargs = '?', help = 'File to load initially')

    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(parser.format_help())

    return gui_parser.parse_args()

def logScreenInfo(app):
    logging.info(f'Is PyInstaller? {pyInstalled}')
    logging.info(f'Logical DPI: {app.primaryScreen().logicalDotsPerInch()}.')
    logging.info(f'Logical DPI: {app.primaryScreen().physicalDotsPerInch()}.')
    logging.info(f'Device pixel ratio: {app.primaryScreen().devicePixelRatio()}.')
    logging.info(f'Pyplot backend: {pyplot.get_backend()}.')
    logging.info(f'Primary screen height: {app.primaryScreen().size().height()}')
    for envvar in ("QT_AUTO_SCREEN_SCALE_FACTOR","QT_SCALE_FACTOR", "QT_SCREEN_SCALE_FACTORS","QT_DEVICE_PIXEL_RATIO"):
        logging.info(f'Env {envvar}: {os.environ.get(envvar)}')

    # logging.info("Qt rounding policy:", getattr(app, "highDpiScaleFactorRoundingPolicy", lambda: None)())
    # logging.info("AA_EnableHighDpiScaling:", app.testAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling))
    # logging.info("AA_UseHighDpiPixmaps:", app.testAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps))

    # every = dict()
    # for data in dir(app.primaryScreen()):
    #     if data.startswith('__') or data == 'thread':
    #         continue

    #     try:
    #         thing = getattr(app.primaryScreen(), data)
    #         every[data] = thing()
    #     except:
    #         continue

    # import pprint
    # logging.info('Logging primary screen data')
    # pprint.pprint(every)

def main():
    args = parse_args()
    logging.basicConfig(level = logging.WARN, format = '[%(relativeCreated)d] %(message)s')
    if args.smoke_test or args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    logging.info('Starting')

    app = QApplication(sys.argv)
    logScreenInfo(app)

    if args.fontsize is None:
        args.fontsize = 13

    font = QFont()
    font.setPointSize(args.fontsize)
    app.setFont(font)

    dpi = args.dpi
    if dpi is None:
        dpi = app.primaryScreen().logicalDotsPerInch()
        if not pyInstalled:
            dpi *= app.primaryScreen().devicePixelRatio()

        logging.info(f'Final DPI: {dpi}')

    logging.info('Creating gallery')

    gallery = PavlovianApp(dpi = dpi, screenshot_ready = args.screenshot_ready, smoke_test = args.smoke_test)
    gallery.show()

    logging.info('Loading file')
    if args.load_file:
        gallery.loadFile(args.load_file)
        gallery.refreshExperiment()

    logging.info('Executing app')
    code = app.exec()

    logging.info('Finished!')
    sys.exit(code)

if __name__ == '__main__':
    main()

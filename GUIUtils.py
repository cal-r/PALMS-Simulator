import os
os.environ["QT_API"] = "PySide6"

import sys
from typing import cast

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import *

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PIL import Image

from AdaptiveType import AdaptiveType
from Environment import StimulusHistory

class PhaseBox(QGroupBox):
    def __init__(self, parent = None, screenshot_ready = False):
        super().__init__(parent)
        self.parent = parent

        leftPhaseButton = QPushButton('<')
        leftPhaseButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        leftPhaseButton.clicked.connect(self.prevPhase)

        rightPhaseButton = QPushButton('>')
        rightPhaseButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rightPhaseButton.clicked.connect(self.nextPhase)

        self.phaseInfo = QLabel('')
        self.phaseInfo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.xCoordInfo = QLabel('')
        self.xCoordInfo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.yCoordInfo = QLabel('')
        self.yCoordInfo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        phaseBoxLayout = QHBoxLayout()
        phaseBoxLayout.addWidget(leftPhaseButton)
        phaseBoxLayout.addWidget(self.xCoordInfo, stretch = 1, alignment = Qt.AlignmentFlag.AlignLeft)
        phaseBoxLayout.addWidget(self.phaseInfo, stretch = 1, alignment = Qt.AlignmentFlag.AlignCenter)
        phaseBoxLayout.addWidget(self.yCoordInfo, stretch = 1, alignment = Qt.AlignmentFlag.AlignRight)
        phaseBoxLayout.addWidget(rightPhaseButton)
        phaseBoxLayout.setSpacing(50)

        # if screenshot_ready:
        if True:
            self.xCoordInfo.setVisible(False)
            self.yCoordInfo.setVisible(False)

        self.setLayout(phaseBoxLayout)
        # self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def setInfo(self, phaseNum, numPhases):
        self.phaseInfo.setText(f'Phase {phaseNum}/{numPhases}')

    def setCoordInfo(self, trial, ylabel, ydata):
        self.xCoordInfo.setText(f'Trial: {trial:.0f}')
        self.yCoordInfo.setText(f'{ylabel}: {ydata:.2f}')

    def prevPhase(self):
        parent = self.parent
        if parent.phaseNum == 1:
            return

        parent.phaseNum -= 1
        parent.refreshFigure()

    def nextPhase(self):
        parent = self.parent
        if parent.phaseNum >= parent.numPhases:
            return

        parent.phaseNum += 1
        parent.refreshFigure()

class AboutButton(QPushButton):
    def __init__(self, parent = None):
        super().__init__('About', parent = parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.clicked.connect(self.aboutPALMS)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def aboutPALMS(self):
        about = '''\
PALMS: Pavlovian Associative Learning Models Simulator
Version 0.xx

Built by Alessandro Abati, Martin Fixman, Julián Jimenez Nimmo, Sean Lim and Esther Mondragón.

For the MSc in Artificial Intelligence in City St George's, University of London. \
If you have any questions, contact any of the authors.

2024. All rights reserved. Licensed under the LGPL v3. See LICENSE for details.\
        '''
        QMessageBox.information(self, 'About', about)

class ActionButtons(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        checkedStyle = "QPushButton:checked { background-color: lightblue; font-weight: bold; border: 2px solid #0057D8; }"

        fileButton = QPushButton('Load file')
        fileButton.clicked.connect(self.openFileDialog)
        fileButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        saveButton = QPushButton("Save Experiment")
        saveButton.clicked.connect(self.saveExperiment)
        saveButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        plotAlphaButton = QPushButton('Plot α')
        plotAlphaButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        plotAlphaButton.setStyleSheet(checkedStyle)
        plotAlphaButton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        plotAlphaButton.clicked.connect(self.togglePlotAlpha)
        plotAlphaButton.setCheckable(True)
        self.parent.plot_alpha = False

        self.toggleRandButton = QPushButton('Random')
        self.toggleRandButton.clicked.connect(self.toggleRand)
        self.toggleRandButton.setCheckable(True)
        self.toggleRandButton.setStyleSheet(checkedStyle)
        self.toggleRandButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.phaseBetaButton = QPushButton('Per-Phase β')
        self.phaseBetaButton.clicked.connect(self.togglePhaseBeta)
        self.phaseBetaButton.setCheckable(True)
        self.phaseBetaButton.setStyleSheet(checkedStyle)
        self.phaseBetaButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.phaseLambdaButton = QPushButton('Per-Phase λ')
        self.phaseLambdaButton.clicked.connect(self.togglePhaseLambda)
        self.phaseLambdaButton.setCheckable(True)
        self.phaseLambdaButton.setStyleSheet(checkedStyle)
        self.phaseLambdaButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.toggleAlphasButton = QPushButton('Per-CS Parameters')
        self.toggleAlphasButton.clicked.connect(self.toggleAlphasBox)
        self.toggleAlphasButton.setCheckable(True)
        self.toggleAlphasButton.setStyleSheet(checkedStyle)
        self.toggleAlphasButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.configuralButton = QPushButton('Configural Cues')
        self.configuralButton.clicked.connect(self.toggleConfiguralCues)
        self.configuralButton.setCheckable(True)
        self.configuralButton.setStyleSheet(checkedStyle)
        self.configuralButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        partStimuliButton = QPushButton('Plot Trial Type Data')
        partStimuliButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        partStimuliButton.setStyleSheet(checkedStyle)
        partStimuliButton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        partStimuliButton.clicked.connect(self.togglePlotPartStimuli)
        partStimuliButton.setCheckable(True)

        exportDataButton = QPushButton("Export Data")
        exportDataButton.clicked.connect(self.exportData)
        exportDataButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # refreshButton = QPushButton("Refresh")
        # refreshButton.clicked.connect(parent.refreshExperiment)
        # refreshButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        printButton = QPushButton("Pop-out Plots")
        printButton.clicked.connect(self.parent.plotExperiment)
        printButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        savePlotButton = QPushButton('Save Plots')
        savePlotButton.clicked.connect(self.savePlots)
        savePlotButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        hideButton = QPushButton("Clear Figures")
        hideButton.clicked.connect(self.hideExperiment)
        hideButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        clearButton = QPushButton("Clear Experiment")
        clearButton.clicked.connect(self.clearExperiment)
        clearButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        modelInfoButton = QPushButton('Model Info')
        modelInfoButton.clicked.connect(self.showModelInfo)
        modelInfoButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        phaseOptionsLayout = QVBoxLayout()
        phaseOptionsLayout.addWidget(self.toggleRandButton)
        phaseOptionsLayout.addWidget(self.phaseBetaButton)
        phaseOptionsLayout.addWidget(self.phaseLambdaButton)
        phaseOptionsLayout.addWidget(self.toggleAlphasButton)
        phaseOptionsLayout.addWidget(self.configuralButton)
        phaseOptionsLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        phaseOptionsGroupBox = QGroupBox('Phase Options')
        phaseOptionsGroupBox.setLayout(phaseOptionsLayout)

        plotOptionsLayout = QVBoxLayout()
        plotOptionsLayout.addWidget(plotAlphaButton)
        plotOptionsLayout.addWidget(partStimuliButton)
        plotOptionsLayout.addWidget(printButton)
        plotOptionsLayout.addWidget(savePlotButton)
        plotOptionsLayout.addWidget(hideButton)
        plotOptionsLayout.addWidget(clearButton)
        plotOptionsLayout.addWidget(modelInfoButton)
        plotOptionsLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        plotOptionsGroupBox = QGroupBox("Plot Options")
        plotOptionsGroupBox.setLayout(plotOptionsLayout)

        fileOptionsLayout = QVBoxLayout()
        fileOptionsLayout.addWidget(fileButton)
        fileOptionsLayout.addWidget(saveButton)
        fileOptionsLayout.addWidget(exportDataButton)
        fileOptionsLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        fileOptionsGroupBox = QGroupBox("File Options")
        fileOptionsGroupBox.setLayout(fileOptionsLayout)

        layout = QVBoxLayout()
        layout.addWidget(phaseOptionsGroupBox)
        layout.addWidget(plotOptionsGroupBox)
        layout.addWidget(fileOptionsGroupBox)
        self.setLayout(layout)

    def openFileDialog(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Open File', './Experiments')
        if file == '':
            return

        self.parent.loadFile(file)
        self.parent.refreshExperiment()

    def saveExperiment(self):
        default_directory = os.path.join(os.getcwd(), 'Experiments')
        default_file_name = "experiment.rw"
        if os.path.exists(default_directory):
            default_file_name = os.path.join(default_directory, "experiment.rw")

        fileName, _ = QFileDialog.getSaveFileName(self, "Save Experiment", default_file_name, "RW Files (*.rw);;All Files (*)")
        if not fileName:
            return

        if not fileName.endswith(".rw"):
            fileName += ".rw"

        lines = []

        lines.append(f'@model={self.parent.current_adaptive_type}')
        if self.parent.configural_cues:
            lines.append('@configural_cues=True')

        params = [f'{key}={dual.box.text()}' for key, dual in self.parent.params.items() if dual.modified]
        if params:
            lines.append('@' + ';'.join(params))

        if self.parent.alphasBox.isVisible():
            percs_params = [f'{perc}_{cs}={dual.box.text()}' for perc, value in self.parent.per_cs_param.items() for cs, dual in value.items() if dual.modified]
            if percs_params:
                lines.append('@' + ';'.join(percs_params))

        rowCount = self.parent.tableWidget.rowCount()
        columnCount = self.parent.tableWidget.columnCount()
        while columnCount > 0 and not any(self.parent.tableWidget.getText(row, columnCount - 1) for row in range(rowCount)):
            columnCount -= 1

        for row in range(rowCount):
            name = self.parent.tableWidget.table.verticalHeaderItem(row).text()
            phase_strs = [self.parent.tableWidget.getText(row, column) for column in range(columnCount)]
            if not any(phase_strs):
                continue

            lines.append(name + '|' + '|'.join(phase_strs))

        with open(fileName, 'w') as file:
            for line in lines:
                file.write(line + '\n')

    def togglePlotAlpha(self):
        if self.parent.plot_alpha:
            self.parent.plot_alpha = False
            # self.parent.resize(int(self.parent.width() - self.parent.plotCanvas.width() / 0.5), self.parent.height())
        else:
            self.parent.plot_alpha = True
            # self.parent.resize(int(self.parent.width() + self.parent.plotCanvas.width() * 0.5), self.parent.height())

        self.parent.refreshExperiment()

    def toggleRand(self):
        set_rand = any(p[self.parent.phaseNum - 1].rand for p in self.parent.phases.values())
        self.parent.tableWidget.setPrefixInSelection('rand', not set_rand)
        self.parent.refreshExperiment()

    def togglePhaseBeta(self):
        set_beta = any(p[self.parent.phaseNum - 1].beta is not None for p in self.parent.phases.values())
        self.parent.tableWidget.setPrefixInSelection('beta', self.parent.floatOr(self.parent.params['beta'].box.text(), 0) if not set_beta else None)
        self.parent.refreshExperiment()

    def togglePhaseLambda(self):
        set_lambda = any(p[self.parent.phaseNum - 1].lamda is not None for p in self.parent.phases.values())
        self.parent.tableWidget.setPrefixInSelection('lambda', self.parent.floatOr(self.parent.params['lamda'].box.text(), 0) if not set_lambda else None)
        self.parent.refreshExperiment()

    def toggleAlphasBox(self):
        if not self.parent.alphasBox.isVisible():
            self.parent.alphasBox.setVisible(True)

            for perc, form in self.parent.per_cs_param.items():
                for cs, pair in form.items():
                    global_val = float(self.parent.params[perc].box.text())
                    local_val = global_val ** len(cs.strip('()'))
                    pair.setText(f'{local_val:.2g}', set_modified = False)
        else:
            self.parent.alphasBox.setVisible(False)
            self.parent.refreshExperiment()

        self.parent.enableParams()

    def toggleConfiguralCues(self):
        self.parent.configural_cues = not self.parent.configural_cues
        self.parent.refreshExperiment()

    def togglePlotPartStimuli(self):
        self.parent.plot_part_stimuli = not self.parent.plot_part_stimuli
        self.parent.refreshExperiment()

    def exportData(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Export Data", "data.csv", "CSV files (*.csv);;All Files (*)")
        if not fileName:
            return

        strengths, _, args = self.parent.generateResults()

        with open(fileName, 'w') as file:
            StimulusHistory.exportData(strengths, file, args.should_plot_macknhall)

    def savePlots(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Save Plots")
        layout = QVBoxLayout(dialog)

        # File selection (read-only)
        file_layout = QHBoxLayout()
        file_label = QLabel("Save as:")
        file_edit = QLineEdit('plot.png')
        file_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")

        # File dialog with filter and suggested extension
        def choose_file():
            fname, _ = QFileDialog.getSaveFileName(
                dialog,
                "Save Plots",
                os.path.join(os.environ['HOME'], 'Desktop', 'plot.png'),
                "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;All Files (*)",
            )
            if fname:
                file_edit.setText(fname)
        browse_btn.clicked.connect(choose_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(file_edit)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        width = QLineEdit('11')
        width.setAlignment(Qt.AlignmentFlag.AlignRight)
        width.setMaximumWidth(40)

        height = QLineEdit('6')
        height.setAlignment(Qt.AlignmentFlag.AlignRight)
        height.setMaximumWidth(40)

        wh_layout = QHBoxLayout()
        wh_layout.addWidget(QLabel('Dimensions'))
        wh_layout.addWidget(width)
        wh_layout.addWidget(QLabel('×'))
        wh_layout.addWidget(height)

        legend_checkbox = QCheckBox("Separate legend")
        wh_layout.addWidget(legend_checkbox)

        layout.addLayout(wh_layout)

        info = QToolButton()
        info.setIcon(QIcon.fromTheme("dialog-question"))
        info.setIconSize(QSize(20, 20))
        info.setText('Info')
        info.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        info_text = '''\
The filenames are generated dynamically, one per phase, with the phase number besides the name.\n
For example, if the selected filename is "plot.png", then generate files will be namednamed "plot_1.png", "plot_2.png", ..., "plot_N.png".\n
Selecting "separate legend" removes the legend from these plots, and creates a new files called "plot_legend.png" with the legend\
        '''
        info.clicked.connect(lambda: QMessageBox.information(info, "Saving plots", info_text))

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(info)
        button_layout.addWidget(btn_box)

        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.Accepted:
            file_path = file_edit.text()
            if not file_path:
                QMessageBox.warning(self, "No file selected", "Please select a file to save.")
                return
            try:
                width = int(width.text())
                height = int(height.text())
            except ValueError:
                QMessageBox.warning(self, "Invalid input", "Width and Height must be integers.")
                return
            separate_legend = legend_checkbox.isChecked()
            self.parent.savePlots(file_path, width, height, separate_legend)

    def hideExperiment(self):
        value = not all(self.parent.line_hidden.values())
        self.parent.line_hidden = {k: value for k in self.parent.line_hidden.keys()}
        self.parent.refreshFigure()

    def clearExperiment(self):
        self.parent.tableWidget.clearAll()
        self.parent.parametersGroupBox.clearFields()
        self.parent.alphasBox.clearFields()
        self.parent.refreshExperiment()

    def showModelInfo(self):
        root = getattr(sys, '_MEIPASS', '.')
        image_filename = AdaptiveType.types()[self.parent.current_adaptive_type].image_filename
        image_path = os.path.join(root, 'resources', image_filename)
        try:
            image = Image.open(image_path)
            image.show()
        except (FileNotFoundError, IsADirectoryError):
             QMessageBox.warning(self, '', 'Rendered formula file not found')

class ParametersGroupBox(QGroupBox):
    def __init__(self, parent):
        super().__init__('Parameters')

        short_names = dict(
            alpha = "α ",
            alpha_mack = "αᴹ",
            alpha_hall = "αᴴ",
            salience = "S ",
            habituation = "h ",
            kay = "Κ ",
            lamda = "λ ",
            beta = "β⁺",
            betan = "β⁻",
            gamma = "γ ",
            thetaE = "θᴱ",
            thetaI = "θᴵ",
            rho = "ρ ",
            nu = "ν ",
            num_trials = "Nº",
        )

        descriptions = dict(
            alpha = "Initial learning rate of the stimuli. α ∈ [0, 1].",
            alpha_mack = "Initial learning rate of the stimuli based on Mackintosh's model, which controls how much of an stumulus is remembered between steps. αᴹ ∈ [0, 1].",
            alpha_hall = "Initial learning rate of the stimuli based on Hall's model, which controls how much a new stimulus affects the association. αᴴ ∈ [0, 1].",
            salience = "Initial salience of the stimuli.",
            habituation = "Initial habituation of the stimuli.",
            kay = "Constant for hybrid model.",
            lamda = "Asymptote of learning with positive stimuli. λ ∈ (0, 1].",
            rho = "Parameter for MLAB hybrid formulation.",
            nu = "Parameter for MLAB hybrid formulation.",
            beta = "Associativity of positive US.",
            betan = "Associativity of negative US.",
            gamma = "Weight parameter for past trials.",
            thetaE = "Excitory theta based on LePelley's model.",
            thetaI = "Inhibitory theta based on LePelley's model.",
            num_trials = "Number of random trials per experiment.",
        )

        self.params = parent.params

        layout = QFormLayout()
        layout.setSpacing(10)
        for key, val in AdaptiveType.initial_defaults().items():
            label = parent.DualLabel(short_names[key], parent, str(val), hoverText = descriptions[key]).addRow(layout)
            self.params[key] = label

        self.params['num_trials'].box.setGeometry(100, 120, 120, 60)
        self.params['num_trials'].box.setDisabled(True)

        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)
        self.setMaximumWidth(90)

    def clearFields(self, defaults, only_unmodified = False):
        for key, default in defaults.items():
            if not only_unmodified or not self.params[key].modified:
                self.params[key].setText(str(default), set_modified = False)

class AlphasBox(QGroupBox):
    def __init__(self, parent):
        super().__init__('Per-CS', parent = parent)
        self.parent = parent
        self.per_cs_param = parent.per_cs_param

        # scrollArea = QScrollArea()
        scrollArea = QWidget()
        layout = QHBoxLayout(scrollArea)
        layout.setContentsMargins(5, 5, 5, 5)
        for perc in parent.per_cs_param.keys():
            boxLayout = QFormLayout()
            boxLayout.setContentsMargins(0, 0, 0, 0)
            boxLayout.setSpacing(10)
            boxLayout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
            boxLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

            parent.per_cs_box[perc] = QWidget()
            parent.per_cs_box[perc].setLayout(boxLayout)
            parent.per_cs_box[perc].setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
            layout.addWidget(parent.per_cs_box[perc])

        # scrollArea.setLayout(layout)
        # scrollArea.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        # scrollArea.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        # scrollArea.setWidgetResizable(True)

        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(scrollArea)

        self.setLayout(mainLayout)
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.clear()

    def clear(self):
        self.refresh(set())

    def refresh(self, css: set[str]):
        parent = self.parent

        shortnames = {
            'alpha': 'α',
            'alpha_mack': 'αᴹ',
            'alpha_hall': 'αᴴ',
            'salience': 'S',
            'habituation': 'h',
        }
        for perc, form in parent.per_cs_param.items():
            global_val = float(parent.params[perc].box.text())
            layout = cast(QFormLayout, parent.per_cs_box[perc].layout())

            to_remove = []
            for e, (cs, pair) in enumerate(form.items()):
                if cs not in css:
                    to_remove.append((e, cs))

            for (rowNum, cs) in to_remove[::-1]:
                layout.removeRow(rowNum)
                del form[cs]

            for cs in sorted(css):
                if cs not in form:
                    hoverText = parent.params[perc].hoverText.replace('of the stimuli', f' for stimulus {cs}')
                    local_val = global_val ** len(cs.strip('()'))

                    form[cs] = parent.DualLabel(
                        f'{shortnames[perc]}<sub>{cs}</sub>',
                        parent,
                        f'{local_val:.3f}',
                        hoverText = hoverText,
                        maximumWidth = 50,
                    ).addRow(layout)

        # print(self.width())
        # self.setMinimumWidth(self.width())

    def clearFields(self, defaults, only_unmodified = False):
        common_keys = defaults.keys() & self.per_cs_param.keys()
        for key in common_keys:
            default = defaults[key]
            param = self.per_cs_param[key]
            for cs, pair in param.items():
                if not only_unmodified or not pair.modified:
                    val = default ** len(cs.strip('()'))
                    pair.setText(f'{val:.3f}', set_modified = False)

class AdaptiveTypeButtons(QGroupBox):
    def __init__(self, parent):
        super().__init__('Models', parent = parent)
        self.parent = parent

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.buttonGroup = QButtonGroup(parent)
        self.buttonGroup.setExclusive(True)

        for i, adaptive_type in enumerate(parent.adaptive_types):
            button = QPushButton(adaptive_type.replace('/ ', '/\n'))
            button.adaptive_type = adaptive_type
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

            noMarginStyle = ""
            checkedStyle = "QPushButton:checked { background-color: lightblue; font-weight: bold; border: 2px solid #0057D8; }"
            button.setStyleSheet(noMarginStyle + checkedStyle)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            self.buttonGroup.addButton(button, i)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

            layout.addWidget(button)

        self.buttonGroup.buttonClicked.connect(lambda button: self.changeAdaptiveType(button.adaptive_type))
        self.setLayout(layout)

    def clickAdaptiveTypeButton(self, adaptive_type):
        for button in self.buttonGroup.buttons():
            if button.adaptive_type == adaptive_type:
                button.click()
                return

        print(f'Secret adaptive type! {adaptive_type}')
        buttonGroup.checkedButton.release()
        self.changeAdaptiveType(self, adaptive_type)

    def changeAdaptiveType(self, adaptive_type):
        parent = self.parent
        parent.current_adaptive_type = adaptive_type
        parent.enabled_params = set(AdaptiveType.types()[parent.current_adaptive_type].parameters())
        parent.enableParams()

        defaults = AdaptiveType.types()[self.parent.current_adaptive_type].defaults()
        parent.parametersGroupBox.clearFields(defaults = defaults, only_unmodified = True)
        parent.alphasBox.clearFields(defaults = defaults, only_unmodified = True)
        parent.refreshExperiment()

class PlotBox(QGroupBox):
    def __init__(self, parent):
        super().__init__('Plot', parent = parent)
        # self.setContentsMargins(0, 0, 0, 0)
        self.parent = parent

        self.plotCanvas = FigureCanvasQTAgg()
        self.phaseBox = PhaseBox(parent, screenshot_ready = False)

        layout = QVBoxLayout()
        layout.addWidget(self.plotCanvas)
        layout.addWidget(self.phaseBox)
        layout.setStretch(0, 1)
        layout.setStretch(1, 0)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

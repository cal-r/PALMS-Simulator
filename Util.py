import os
os.environ["QT_API"] = "PySide6"

import sys
from csv import DictWriter
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import *

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PIL import Image

from AdaptiveType import AdaptiveType

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

        if screenshot_ready:
            self.xCoordInfo.setVisible(False)
            self.yCoordInfo.setVisible(False)

        self.setLayout(phaseBoxLayout)

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

        toggleRandButton = QPushButton('Random')
        toggleRandButton.clicked.connect(self.toggleRand)
        toggleRandButton.setCheckable(True)
        toggleRandButton.setStyleSheet(checkedStyle)
        toggleRandButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        phaseLambdaButton = QPushButton('Per-Phase λ')
        phaseLambdaButton.clicked.connect(self.togglePhaseLambda)
        phaseLambdaButton.setCheckable(True)
        phaseLambdaButton.setStyleSheet(checkedStyle)
        phaseLambdaButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        toggleAlphasButton = QPushButton('Per-CS Parameters')
        toggleAlphasButton.clicked.connect(self.toggleAlphasBox)
        toggleAlphasButton.setCheckable(True)
        toggleAlphasButton.setStyleSheet(checkedStyle)
        toggleAlphasButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        configuralButton = QPushButton('Add Configural Cues')
        configuralButton.clicked.connect(self.toggleConfiguralCues)
        configuralButton.setCheckable(True)
        configuralButton.setStyleSheet(checkedStyle)
        configuralButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        exportDataButton = QPushButton("Export Data")
        exportDataButton.clicked.connect(self.exportData)
        exportDataButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # refreshButton = QPushButton("Refresh")
        # refreshButton.clicked.connect(parent.refreshExperiment)
        # refreshButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        printButton = QPushButton("Plot")
        printButton.clicked.connect(self.parent.plotExperiment)
        printButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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
        phaseOptionsLayout.addWidget(toggleRandButton)
        phaseOptionsLayout.addWidget(phaseLambdaButton)
        phaseOptionsLayout.addWidget(toggleAlphasButton)
        phaseOptionsLayout.addWidget(configuralButton)
        phaseOptionsGroupBox = QGroupBox('Phase Options')
        phaseOptionsGroupBox.setLayout(phaseOptionsLayout)

        plotOptionsLayout = QVBoxLayout()
        plotOptionsLayout.addWidget(plotAlphaButton)
        # plotOptionsLayout.addWidget(refreshButton)
        plotOptionsLayout.addWidget(printButton)
        plotOptionsLayout.addWidget(hideButton)
        plotOptionsLayout.addWidget(clearButton)
        plotOptionsLayout.addWidget(modelInfoButton)
        plotOptionsGroupBox = QGroupBox("Plot Options")
        plotOptionsGroupBox.setLayout(plotOptionsLayout)

        fileOptionsLayout = QVBoxLayout()
        fileOptionsLayout.addWidget(fileButton)
        fileOptionsLayout.addWidget(saveButton)
        fileOptionsLayout.addWidget(exportDataButton)
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

        rowCount = self.parent.tableWidget.rowCount()
        columnCount = self.parent.tableWidget.columnCount()
        while columnCount > 0 and not any(self.parent.tableWidget.getText(row, columnCount - 1) for row in range(rowCount)):
            columnCount -= 1

        lines = []
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
            self.parent.resize(int(self.parent.width() - self.parent.plotCanvas.width() / 0.5), self.parent.height())
        else:
            self.parent.plot_alpha = True
            self.parent.resize(int(self.parent.width() + self.parent.plotCanvas.width() * 0.5), self.parent.height())

        self.parent.refreshExperiment()

    def toggleRand(self):
        set_rand = any(p[self.parent.phaseNum - 1].rand for p in self.parent.phases.values())
        self.parent.tableWidget.setRandInSelection(not set_rand)
        self.parent.refreshExperiment()

    def togglePhaseLambda(self):
        set_lambda = any(p[self.parent.phaseNum - 1].lamda is not None for p in self.parent.phases.values())
        self.parent.tableWidget.setLambdaInSelection(self.parent.floatOr(self.parent.params['lamda'].box.text(), 0) if not set_lambda else None)
        self.parent.refreshExperiment()

    def toggleAlphasBox(self):
        if not self.parent.alphasBox.isVisible():
            self.parent.alphasBox.setVisible(True)

            for perc, form in self.parent.per_cs_param.items():
                for cs, pair in form.items():
                    global_val = float(self.parent.params[perc].box.text())
                    local_val = global_val ** len(cs.strip('()'))
                    pair.box.setText(f'{local_val:.2g}')
        else:
            self.parent.alphasBox.setVisible(False)
            self.parent.refreshExperiment()

        self.parent.enableParams()

    def toggleConfiguralCues(self):
        self.parent.configural_cues = not self.parent.configural_cues
        self.parent.refreshExperiment()

    def exportData(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Export Data", "data.csv", "CSV files (*.csv);;All Files (*)")
        if not fileName:
            return

        strengths, _, args = self.parent.generateResults()

        with open(fileName, 'w') as file:
            fieldnames = ['Phase', 'Group', 'CS', 'Trial', 'Assoc']
            if not args.should_plot_macknhall:
                fieldnames += ['Alpha']
            else:
                fieldnames += ['Alpha Mack', 'Alpha Hall']

            writer = DictWriter(file, fieldnames = fieldnames, extrasaction = 'ignore')
            writer.writeheader()

            for phase_num, phase in enumerate(strengths, start = 1):
                for group_cs, hist in phase.items():
                    group, cs = group_cs.rsplit(' - ', maxsplit = 1)
                    for trial, stimulus in enumerate(hist, start = 1):
                        row = {
                            'Phase': phase_num,
                            'Group': group,
                            'CS': cs,
                            'Trial': trial,
                            'Assoc': stimulus.assoc,
                            'Alpha': stimulus.alpha,
                            'Alpha Mack': stimulus.alpha_mack,
                            'Alpha Hall': stimulus.alpha_hall,
                        }
                        writer.writerow(row)

    def hideExperiment(self):
        value = not all(self.parent.line_hidden.values())
        self.parent.line_hidden = {k: value for k in self.parent.line_hidden.keys()}
        self.parent.refreshFigure()

    def clearExperiment(self):
        self.parent.tableWidget.clearAll()
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
        params = QFormLayout()
        params.setSpacing(10)
        for key, val in AdaptiveType.initial_defaults().items():
            label = parent.DualLabel(short_names[key], parent, str(val), hoverText = descriptions[key]).addRow(params)
            parent.params[key] = label

        parent.params['num_trials'].box.setGeometry(100, 120, 120, 60)
        parent.params['num_trials'].box.setDisabled(True)

        params.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.setLayout(params)
        self.setMaximumWidth(90)


class AlphasBox(QGroupBox):
    def __init__(self, parent):
        super().__init__('Per-CS', parent = parent)
        self.parent = parent

        layout = QHBoxLayout()
        for perc in parent.per_cs_param.keys():
            boxLayout = QFormLayout()
            boxLayout.setContentsMargins(0, 0, 0, 0)
            boxLayout.setSpacing(10)

            parent.per_cs_box[perc] = QWidget()
            parent.per_cs_box[perc].setLayout(boxLayout)
            layout.addWidget(parent.per_cs_box[perc])

        self.setLayout(layout)
        self.setVisible(False)
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
                        f'{local_val:.2g}',
                        hoverText = hoverText,
                    ).addRow(layout)

class AdaptiveTypeButtons(QGroupBox):
    def __init__(self, parent):
        super().__init__('Models', parent = parent)
        self.parent = parent

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        buttonGroup = QButtonGroup(parent)
        buttonGroup.setExclusive(True)

        for i, adaptive_type in enumerate(parent.adaptive_types):
            button = QPushButton(adaptive_type)
            button.adaptive_type = adaptive_type
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

            noMarginStyle = ""
            checkedStyle = "QPushButton:checked { background-color: lightblue; font-weight: bold; border: 2px solid #0057D8; }"
            button.setStyleSheet(noMarginStyle + checkedStyle)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            buttonGroup.addButton(button, i)
            layout.addWidget(button)

            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        buttonGroup.buttonClicked.connect(self.changeAdaptiveType)
        self.setLayout(layout)

    def changeAdaptiveType(self, button):
        parent = self.parent
        parent.current_adaptive_type = button.adaptive_type
        parent.enabled_params = set(AdaptiveType.types()[parent.current_adaptive_type].parameters())
        parent.enableParams()

        for key, default in AdaptiveType.types()[parent.current_adaptive_type].defaults().items():
            parent.params[key].box.setText(str(default))
            if key in parent.per_cs_param:
                for cs, pair in parent.per_cs_param[key].items():
                    val = default ** len(cs.strip('()'))
                    pair.box.setText(str(val))

        parent.refreshExperiment()

class PlotBox(QGroupBox):
    def __init__(self, parent):
        super().__init__('Plot', parent = parent)
        self.parent = parent

        self.plotCanvas = FigureCanvasQTAgg()
        self.phaseBox = PhaseBox(parent, screenshot_ready = False)

        layout = QVBoxLayout()
        layout.addWidget(self.plotCanvas)
        layout.addWidget(self.phaseBox)
        layout.setStretch(0, 1)
        layout.setStretch(1, 0)
        self.setLayout(layout)

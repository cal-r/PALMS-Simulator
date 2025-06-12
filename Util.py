from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtWidgets import *

class PhaseBox:
    def __init__(self, left_callback, right_callback, screenshot_ready = False):
        leftPhaseButton = QPushButton('<')
        leftPhaseButton.clicked.connect(left_callback)
        leftPhaseButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.phaseInfo = QLabel('')
        self.phaseInfo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.xCoordInfo = QLabel('')
        self.xCoordInfo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.yCoordInfo = QLabel('')
        self.yCoordInfo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        rightPhaseButton = QPushButton('>')
        rightPhaseButton.clicked.connect(right_callback)
        rightPhaseButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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

        self.phaseBox = QGroupBox()
        self.phaseBox.setLayout(phaseBoxLayout)

    def widget(self):
        return self.phaseBox

    def setInfo(self, phaseNum, numPhases):
        self.phaseInfo.setText(f'Phase {self.phaseNum}/{self.numPhases}')

    def setCoordInfo(self, trial, ylabel, ydata):
        self.xCoordInfo.setText(f'Trial: {trial:.0f}')
        self.yCoordInfo.setText(f'{ylabel}: {ydata:.2f}')

class AboutButton:
    def __init__(self):
        self.aboutButton = QPushButton('About')
        self.aboutButton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.aboutButton.clicked.connect(self.aboutPALMS)
        self.aboutButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def widget(self):
        return self.aboutButton

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
    

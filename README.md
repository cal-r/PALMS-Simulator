# **P**avlovian **A**ssociative **L**earning **M**odels **S**imulator

Associative learning simulator, originally cased on the **extra task** of INM703 Computational Cognitive Systems.

This simulator will be presented in the paper ``PALMS: Pavlovian Associative Learning Models Simulator`` by Alessandro Abati, Martin Fimxan, Julián Jiménez Nimmo, Sean Lim, and Esther Mondragón.

## Runnable executable bundled with the prerequisites.

> I DON'T CARE ABOUT THE CODE! WHY IS THERE CODE? MAKE AN .EXE FILE AND GIVE IT TO ME.
— a wise man on Reddit.

Each version of PALMS get automatically compiled 

## Prerequisites

Before running the simulator, ensure you have the following prerequisites installed:

- Python 3.10 or higher
- Matplotlib
- Seaborn

## Installation

1. Clone the repository to your local machine:

```bash
git clone https://github.com/mfixman/rw-model
```

2. Navigate to the cloned repository:

```bash
cd Rescorla-Wagner-Simulator
```

## Running the Simulator

To run the simulator, use the RW_simulator.py script. This script accepts various command-line arguments to customize the simulation parameters.

```bash
python RW_simulator.py [path to your experiment file]
```

### Advanced Options
- -h, --help: Shows help message and exit
- --beta: Set the associativity of the US (Unconditioned Stimulus) positive reinforcement. Default is 1.
- --beta-neg: Set the associativity of the absence of US positive reinforcement. Default is equal to --beta value.
- --lamda: Set the asymptote of learning for positive reinforcement. Default is 1.
- --lamda-neg: Set the asymptote for the absence of US positive reinforcement. Default is 0.
- --use-configurals: Enable the use of compound stimuli with configural cues.
- --adaptive-type: Set the type of adaptive attention mode (linear or exponential).
- --window-size: Set the size of the sliding window for adaptive learning.

### Example
```bash
python RW_simulator.py --beta 1 --lamda 1 --use-configurals --adaptive-type linear --window-size 5 --experiment_file Blocking.rw
```
This example runs a blocking experiment with linear adaptive attention and a window size of 5 for adaptive learning.

## Experiment File Format
The experiment file should contain lines representing different experimental groups or conditions. Each line should follow this format:

GroupName|Phase1|Phase2|...

Where each phase is defined as:

numberOfTrialsStimulusSign

where:

- numberOfTrials is the number of times the stimuli are presented.
- Stimulus can be a single stimulus (A, B, etc.) or a compound (AB, AC, etc.).
- Sign is + for positive reinforcement and - for negative reinforcement (or omitted for neutral).

Example line in an experiment file:
Test|20A+|20AB+|1B+

This defines a group named "Test" with three phases: 20 trials of stimulus A with positive reinforcement, followed by 20 trials of compound stimulus AB with positive reinforcement, and finally a single trial of stimulus B with positive reinforcement.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details.






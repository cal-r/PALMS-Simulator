# PALMS: **P**avlovian **A**ssociative **L**earning **M**odels **S**imulator

The Pavlovian Associative Learning Models Simulator (PALMS) is a unified Python environment to simulate Pavlovian conditioning experiments.

PALMS incorporates several attentional learning approaches, including
Pearce-Kaye-Hall, Mackintosh Extended, Le Pelley's Hybrid, and a novel
extension of the Rescorla-Wagner model with a unified variable learning rate.

The simulator’s graphical interface allows for the input of entire experimental
designs in an alphanumeric format, akin to that used by experimental neuroscientists.

Moreover, it uniquely enables the simulation of experiments involving hundreds
of stimuli, as well as the computation of configural cues and configural-cue
compounds across all models, thereby considerably expanding their predictive
capabilities.

PALMS is licensed under the open-source GNU Lesser General Public License 3.0.

## Runnable executable bundled with the prerequisites.

The executable version of the simulator can be found [in the latest release](https://github.com/cal-r/PALMS-Simulator/releases/latest).
* [Linux version](https://github.com/cal-r/PALMS-Simulator/releases/latest/download/PALMS_linux.tar.gz)
* [MacOS version](https://github.com/cal-r/PALMS-Simulator/releases/latest/download/PALMS_macos.tar.gz)
* [Windows version](https://github.com/cal-r/PALMS-Simulator/releases/latest/download/PALMS_windows.tar.gz)

Each version of PALMS has releases bundled with Python and its respective
libraries to create executables for Linux, MacOS, and Windows. These bundles
work on systems that don't have Python or its respective libraries installed.

## Simulating Experiments

The simulator can simulate a wide variety of experiments with a large amount of
stimuli and various different configurations.

![Le Pelley's Hybrid](screenshots/screenshot_1.png)

Various experiments are provided within the releases and in this repo, proving
the wide variety of experiments that can be run.

![Rescorla Wagner](screenshots/screenshot_2.png)

The simulator comes with four existing models of cognitive learning, and also
comes bundled with our own formulation, the MLAB Model.

![MLAB Model](screenshots/screenshot_3.png)

More information about the models and the simulator itself is present in the
paper.

## Licence and Notice

This project is licensed under the GNU Lesser General Public License (LGPL),
version 3.

Citation Requirement: Any publication using this project must contain the
following citation in the text.

```
@article{
    title = {{PALMS: Pavlovian Associative Learning Models Simulator}},
    author = {
        Fixman, Martin and
        Abati, Alessandro and
        Jimenez, Julian Nimmo and
        Lim, Sean and
        Mondragon, Esther
    },
    journal = {Computer Methods and Programs in Biomedicine},
}
```

Authors must be notified of any modifications and releases of this system.

Any modifications or uses of the simulator, the adaptive type formulas, or any
other code in this repository must be released and licensed under the LGPL. It
might however be bundled with non LGPL'd code.

## Running the Python code

### Requirements

- Python ≥ 3.10
- Seaborn
- PyQt6
- colorcet

Once Python is installed, the requirements can be installed with the following
command.

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python PALMS.py
```

## Disclaimer
IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, INDIRECT
OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
SOFTWARE. THE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE, AND NON-INFRINGEMENT. THIS SOFTWARE AND ITS DOCUMENTATION ARE PROVIDED
ON AN "AS IS" BASIS, AND THE AUTHORS HAVE NO OBLIGATION TO PROVIDE MAINTENANCE,
SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.

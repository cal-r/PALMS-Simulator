# **P**avlovian **A**ssociative **L**earning **M**odels **S**imulator

Associative learning simulator, originally cased on the **extra task** of INM703 Computational Cognitive Systems.

This simulator will be presented in the paper ``PALMS: Pavlovian Associative Learning Models Simulator`` by Alessandro Abati, Martin Fixman, Julián Jiménez Nimmo, Sean Lim, and Esther Mondragón.

## Runnable executable bundled with the prerequisites.

https://github.com/mfixman/rw-model/releases

> I DON'T CARE ABOUT THE CODE! WHY IS THERE CODE? MAKE AN .EXE FILE AND GIVE IT TO ME YOU SMELLY NERDS.

— a wise man on the Github subreddit.

Each version of PALMS has releases bundled with Python and its respective libraries to create executables for Linux, MacOS, and Windows. These bundles work on systems that don't have Python or its respective libraries installed.

While convenient, these executables are considerably large. We recommend downloading and running the Python source code if you already have the dependencies set up and aren't stuck in Python version hell.

The latest releases can be found in [this link]((https://github.com/cal-r/PALMS-Simulator/releases/tag/latest)).

## Running the Python code

### Requirements

- Python ≥ 3.9
- Seaborn
- PyQt6

Once Python is installed, the requirements can be installed with the following command.
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Simulator

The GUI simulator has two arguments, which are convenient for debugging and posting screenshots.

```
python PALMS.py --help
usage: Display a GUI for simulating models. [-h] [--dpi DPI] [load_file]

positional arguments:
  load_file   File to load initially

options:
  -h, --help  show this help message and exit
  --dpi DPI   DPI for shown and outputted figures.
```

Additionally, the simulator contains a CLI option with various arguments. Both versions are able to run the same models.

```
 $ python Simulator.py --help
usage: Simulator.py [-h]
                    [--adaptive-type {rescorla_wagner,rescorla_wagner_linear,pearce_hall,pearce_kaye_hall,le_pelley,le_pelley_hybrid,rescorla_wagner_exponential,mack,hall,macknhall,new_dual_v,dualmack,hybrid}]
                    [--alpha ALPHA] [--alpha-mack ALPHA_MACK] [--alpha-hall ALPHA_HALL] [--beta BETA]
                    [--beta-neg BETA_NEG] [--lamda LAMDA] [--gamma GAMMA] [--thetaE THETAE]
                    [--thetaI THETAI] [--window-size WINDOW_SIZE] [--salience SALIENCE]
                    [--xi-hall XI_HALL] [--num-trials NUM_TRIALS] [--plot-phase PLOT_PHASE]
                    [--plot-experiments [PLOT_EXPERIMENTS ...]] [--plot-stimuli [PLOT_STIMULI ...]]
                    [--plot-alphas | --no-plot-alphas] [--plot-alpha | --no-plot-alpha]
                    [--plot-macknhall | --no-plot-macknhall] [--title-suffix TITLE_SUFFIX]
                    [--savefig SAVEFIG]
                    [experiment_file]

Behold! My Rescorla-Wagnerinator!

positional arguments:
  experiment_file       Path to the experiment file.

options:
  -h, --help            show this help message and exit
  --adaptive-type {rescorla_wagner,rescorla_wagner_linear,pearce_hall,pearce_kaye_hall,le_pelley,le_pelley_hybrid,rescorla_wagner_exponential,mack,hall,macknhall,new_dual_v,dualmack,hybrid}
                        Type of adaptive attention mode to use
  --alpha ALPHA         Alpha for all other stimuli
  --alpha-mack ALPHA_MACK
                        Alpha_mack for all other stimuli
  --alpha-hall ALPHA_HALL
                        Alpha_hall for all other stimuli
  --beta BETA           Associativity of the US +.
  --beta-neg BETA_NEG   Associativity of the absence of US +. Equal to beta by default.
  --lamda LAMDA         Asymptote of learning.
  --gamma GAMMA         Weighting how much you rely on past experinces on DualV adaptive type.
  --thetaE THETAE       Theta for excitatory phenomena in LePelley blocking
  --thetaI THETAI       Theta for inhibitory phenomena in LePelley blocking
  --window-size WINDOW_SIZE
                        Size of sliding window for adaptive learning
  --salience SALIENCE   Salience for all parameters without an individually defined salience. This is
                        used in the Pearce & Hall model.
  --xi-hall XI_HALL     Xi parameter for Hall alpha calculation
  --num-trials NUM_TRIALS
                        Amount of trials done in randomised phases
  --plot-phase PLOT_PHASE
                        Plot a single phase
  --plot-experiments [PLOT_EXPERIMENTS ...]
                        List of experiments to plot. By default plot everything
  --plot-stimuli [PLOT_STIMULI ...]
                        List of stimuli, compound and simple, to plot. By default plot everything
  --plot-alphas, --no-plot-alphas
                        Whether to plot all the alphas, including total alpha, alpha Mack, and alpha
                        Hall.
  --plot-alpha, --no-plot-alpha
                        Whether to plot the total alpha.
  --plot-macknhall, --no-plot-macknhall
                        Whether to plot the alpha Mack and alpha Hall.
  --title-suffix TITLE_SUFFIX
                        Title suffix
  --savefig SAVEFIG     Instead of showing figures, they will be saved to "fig_n.png"

  --alpha_[A-Z] ALPHA Associative strength of CS A..Z. By default 0
```

## Experiment Syntax Specification
The experiments are saved in `.rw` files, which use a headerless pipe-separated data format specifying each step of the experiment.

```
<file>         ::= <group> { "\n" <group> }*
<group>        ::= <name> "|" <phase> { "|" <phase> }*
<phase>        ::= { "rand/" }? { "lambda=[0-9](.[0-9])?/" }? <phase_parts>
<phase_parts>  ::= <part> { "/" <part> }*
<part>         ::= <number>? <stimuli> <us>
<stimuli>      ::= <cs> { <cs> }*
<cs>           ::= [A-Z]
<us>           ::= { "+" | "-" }?
```

### File Structure
Each line represents a **Row** in the table, typically indicating an experiment group.
The first column of each group is its name. The remaining column are the phases, separated by `|`.

```
<group_name_1> | <phase_1_1> | <phase_1_2> | ... | <phase_1_n>
<group_name_2> | <phase_2_1> | <phase_2_2> | ... | <phase_2_n>
<group_name_3> | <phase_3_1> | <phase_3_2> | ... | <phase_3_n>
```

The phases can be empty; in that case the group does not do anything for that particular phases.

### Phases

Each phase column contains a **Phase Description**, which may include one or more **Attributes**.

- **Format**: `(rand/)?(lambda=\d(\.\d+)?/)?/<part_1>/.../<part_n>`
  - `rand`: Indicates this phase needs to be randomised.
  - `lambda=<value>`: Specifies a per-phase λ. The λ gets reset to the global one on the following phase.

Phases can be completely empty, in which case they are skipped for this particular group.

### Parts
Each parts contains a certain amount of an association between a non-empty set of conditioned stimuli and an unconditioned stimulus.
- **Format**: `[0-9]*[A-Z]*[+-]?`
  - Empty `<repetitions>` defaults to `1`.
  - Empty `<us>` defaults to `+`.

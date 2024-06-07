import seaborn
from matplotlib import pyplot
from RW_strengths import History
from matplotlib.ticker import MaxNLocator

def plot_graphs(data: list[dict[str, History]], plot_phase = None, plot_alpha = False, plot_macknhall = False):
    seaborn.set()
    pyplot.ion()

    if plot_phase is not None:
        data = [data[plot_phase - 1]]

    for phase_num, experiments in enumerate(data, start = 1):
        if not plot_alpha and not plot_macknhall:
            fig, axes = pyplot.subplots(1, 1, figsize = (8, 6))
            axes = [axes]
        else:
            fig, axes = pyplot.subplots(1, 2, figsize = (16, 6))

        colors = dict(zip(experiments.keys(), seaborn.color_palette('husl', len(experiments))))
        for key, hist in experiments.items():
            axes[0].plot(hist.assoc, label=key, marker='D', color = colors[key], markersize=4, alpha=.5)

            if len(axes) > 1:
                if plot_alpha:
                    axes[1].plot(hist.alpha, label=key, color = colors[key], marker='D', markersize=8, alpha=.5)
                else:
                    axes[1].plot([], label=key, color = colors[key], marker='D', markersize=8, alpha=.5)

                if plot_macknhall:
                    axes[1].plot(hist.alpha_mack, color = colors[key], marker='$M$', markersize=8, alpha=.5)
                    axes[1].plot(hist.alpha_hall, color = colors[key], marker='$H$', markersize=8, alpha=.5)

        axes[0].set_xlabel('Trial Number')
        axes[0].set_ylabel('Associative Strength')
        axes[0].set_title(f'Phase {phase_num} Associative Strengths')
        axes[0].xaxis.set_major_locator(MaxNLocator(integer = True))
        axes[0].legend(fontsize = 'small')

        if plot_alpha or plot_macknhall:
            axes[1].set_xlabel('Trial Number')
            axes[1].set_ylabel('Alpha')
            axes[1].set_title(f'Phase {phase_num} Alphas')
            axes[1].xaxis.set_major_locator(MaxNLocator(integer = True))
            axes[1].legend(fontsize = 'small')

        pyplot.tight_layout()
        pyplot.show()

    input('Press any key to continue...')

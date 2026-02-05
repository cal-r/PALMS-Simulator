from __future__ import annotations

import os
os.environ["QT_API"] = "PySide6"

import sys
import logging

from argparse import ArgumentParser
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtGui import QGuiApplication

import Simulator
from PavlovianApp import PavlovianApp

from version import __version__

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

    gui_parser.add_argument('--version', action = 'store_true', help = 'Show program version and exit.')

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

    args = gui_parser.parse_args()
    if args.version:
        print(PavlovianApp.aboutMessage())
        exit(0)

    return args

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

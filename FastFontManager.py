import logging
import threading

import matplotlib
from matplotlib import cbook, font_manager
from matplotlib.font_manager import findSystemFonts

_log = logging.getLogger(__name__)

# Custom font manager for matplotlib that does not waste time looking for fonts in the system.
# This can considerably accelerate the first run of the program on PyInstaller builds.
class FastFontManager(font_manager.FontManager):
    def __init__(self, size=None, weight='normal'):
        if font_manager._fontManager is not None:
            _log.warning("matplotlib.font_manager._fontManager already instantiated! "
                         "FastFontManager patch too late.")
        else:
            logging.info('Using fast font manager')

        self._version = self.__version__

        self.__default_weight = weight
        self.default_size = size

        paths = [cbook._get_data_path('fonts', subdir) for subdir in ['ttf', 'afm', 'pdfcorefonts']]
        # _log.debug('font search path %s', paths)

        self.defaultFamily = {
            'ttf': 'DejaVu Sans',
            'afm': 'Helvetica',
        }

        self.afmlist = []
        self.ttflist = []

        # Delay the warning by 5s.
        timer = threading.Timer(5, lambda: _log.warning('Matplotlib is building the font cache; this may take a moment.'))
        timer.start()
        try:
            for fontext in ["afm", "ttf"]:
                for path in findSystemFonts(paths, fontext=fontext):
                    try:
                        self.addfont(path)
                    except OSError as exc:
                        _log.info("Failed to open font file %s: %s", path, exc)
                    except Exception as exc:
                        _log.info("Failed to extract font properties from %s: "
                                  "%s", path, exc)
        finally:
            timer.cancel()

font_manager.FontManager = FastFontManager

def _get_fast_font_manager():
    logging.info("Custom _get_font_manager called")
    if font_manager._fontManager is None:
        logging.info("Creating FastFontManager")
        font_manager._fontManager = FastFontManager()
    return font_manager._fontManager

font_manager._get_font_manager = _get_fast_font_manager

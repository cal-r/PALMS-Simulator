import importlib
import logging
import threading

# Patch out matplotlib.font_manager._rebuild BEFORE importing matplotlib
fm_mod = importlib.import_module("matplotlib.font_manager")
fm_mod._rebuild = lambda *args, **kwargs: None

import matplotlib
from matplotlib import cbook, font_manager
from matplotlib.font_manager import findSystemFonts

_log = logging.getLogger(__name__)

class FastFontManager(font_manager.FontManager):
    def __init__(self, size=None, weight='normal'):
        if getattr(font_manager, "_fontManager", None) is not None:
            _log.warning("matplotlib.font_manager._fontManager already instantiated! FastFontManager patch too late.")
        else:
            _log.info("Using fast font manager")

        self._version = self.__version__
        self.__default_weight = weight
        self.default_size = size

        paths = [cbook._get_data_path('fonts', subdir) for subdir in ['ttf', 'afm', 'pdfcorefonts']]
        self.defaultFamily = {'ttf': 'DejaVu Sans', 'afm': 'Helvetica'}
        self.afmlist = []
        self.ttflist = []

        timer = threading.Timer(5, lambda: _log.warning('Getting hardcoded fonts.'))
        timer.start()
        try:
            for fontext in ["afm", "ttf"]:
                for path in findSystemFonts(paths, fontext=fontext):
                    try:
                        self.addfont(path)
                    except OSError as exc:
                        _log.info("Failed to open font file %s: %s", path, exc)
                    except Exception as exc:
                        _log.info("Failed to extract font properties from %s: %s", path, exc)
        finally:
            timer.cancel()

# Patch only the class and getter (do NOT reassign the module)
font_manager.FontManager = FastFontManager
font_manager._get_font_manager = lambda: FastFontManager()

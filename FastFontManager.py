import json
import logging
import matplotlib
import os
import threading

cachedir = matplotlib.get_cachedir()
version = matplotlib.__version__.replace(".", "")
fontcache = os.path.join(cachedir, f"fontlist-v{version}.json")

if not os.path.exists(fontcache):
    with open(fontcache, "w") as f:
        # You might want a real cache, but even a dummy dict is enough to bypass the warning
        json.dump({"version": version, "cache": []}, f)

from matplotlib import cbook, font_manager
from matplotlib.font_manager import findSystemFonts

_log = logging.getLogger(__name__)

class FastFontManager(font_manager.FontManager):
    def __init__(self, size=None, weight='normal'):
        if getattr(font_manager, "_fontManager", None) is not None:
            _log.warning("matplotlib.font_manager._fontManager already instantiated! FastFontManager patch too late.")
        else:
            _log.info("Using fast font manager")

        print('Hello')

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

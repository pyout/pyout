"""Terminal styling for tabular data.

Exposes a single entry point, the Tabular class.
"""

from __future__ import unicode_literals

import sys

__version__ = "0.1.0"

from pyout.elements import schema

if sys.platform == "win32":
    from pyout.tabular_dummy import Tabular
else:
    from pyout.tabular import Tabular

del sys

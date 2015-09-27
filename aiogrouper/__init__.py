from pkg_resources import get_distribution, DistributionNotFound
import os.path

__distribution__ = 'aiogrouper'

# Kudos to http://stackoverflow.com/a/17638236

try:
    _dist = get_distribution(__distribution__)
    # Normalize case for Windows systems
    _dist_loc = os.path.normcase(_dist.location)
    _here = os.path.normcase(__file__)
    if not _here.startswith(os.path.join(_dist_loc, __distribution__)):
        # not installed, but there is another version that *is*
        raise DistributionNotFound
except DistributionNotFound:
    __version__ = 'dev'
else:
    __version__ = _dist.version

del os, get_distribution, DistributionNotFound
del _dist, _dist_loc, _here

from .grouper import *
from .group import *
from .query import *
from .stem import *
from .subject import *


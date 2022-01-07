# -*- coding: utf-8 -*-

version_major = 0
version_minor = 0
version_micro = 1
version_extra = ''

# Format expected by setup.py and doc/source/conf.py: string of form "X.Y.Z"
__version__ = "%s.%s.%s%s" % (version_major,
                              version_minor,
                              version_micro,
                              version_extra)
CLASSIFIERS = ['Development Status :: 5 - Production/Stable',
               'Environment :: Console',
               'Intended Audience :: Developers',
               'Intended Audience :: Science/Research',
               'Intended Audience :: Education',
               'Operating System :: OS Independent',
               'Programming Language :: Python',
               'Topic :: Scientific/Engineering',
               'Topic :: Utilities',
               'Topic :: Software Development :: Libraries']


description = 'Deep learning utilities to characterize sulcus patterns'

# versions for dependencies
SPHINX_MIN_VERSION = '1.0'

# Main setup parameters
NAME = 'deep_folding'
PROJECT = 'deep_folding'
ORGANISATION = "neurospin"
MAINTAINER = "nobody"
MAINTAINER_EMAIL = "support@neurospin.info"
DESCRIPTION = description
URL = "https://github.com/neurospin/deep_folding"
DOWNLOAD_URL = "https://github.com/neurospin/deep_folding"
LICENSE = "CeCILL license version 2"
AUTHOR = "Louise Guillon and Joel Chavas"
AUTHOR_EMAIL = ""
PLATFORMS = "OS Independent"
PROVIDES = ["deep_folding"]
REQUIRES = ['six', 'numpy', 'pytest', 'GitPython', 'typing', 'joblib', 'pqdm']
EXTRA_REQUIRES = {
    "plotting": ["matplotlib"],
    "doc": ["sphinx>=" + SPHINX_MIN_VERSION]}

brainvisa_build_model = 'pure_python'


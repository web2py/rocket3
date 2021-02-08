import ast
import re

import setuptools
from rocket3 import __version__

setuptools.setup(
    name = "rocket3",
    version = __version__,
    url = 'https://github.com/web2py/rocket3',
    license = 'BSD',
    author = 'Timothy Ferrell and Massimo Di Pierro',
    author_email = 'massimo.dipierro@gmail.com',
    maintainer = 'Massimo Di Pierro',
    maintainer_email = 'massimo.dipierro@gmail.com',
    description = 'The original web2py multi-threaded web server',
    long_description = "This is a spin-off of the web2py web server",
    long_description_content_type = "text/markdown",
    packages = ['rocket3'],
    include_package_data = True,
    zip_safe = False,
    platforms = 'any',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)

#!/usr/bin/env python3

from setuptools import setup, find_packages
import sys


setup(
    name='gpulimit',
    version="0.0.1",
    author="lcy",
    description=("GPU limit management"),

    url="https://github.com/lichunown/gpulimit",
    packages=find_packages(),
    data_files=[],
    install_requires=[
    ],

    entry_points={'console_scripts': [
       'gpulimit_server = gpulimit.gpulimit_server:main',
       'gpulimit = gpulimit.gpulimit:main',
    ]},

    zip_safe=False
)
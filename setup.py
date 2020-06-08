#!/usr/bin/env python3

import os
import sys
from setuptools import setup, find_packages



with open(os.path.join(os.path.split(__file__)[0], "readme.md"), "r", encoding='utf8') as fh:
    long_description = fh.read()


setup(
    name='gpulimit',
    version="0.2.1",
    author="lcy",
    author_email="lichunyang_1@outlook.com",
    description=("DL training on GPU management"),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lichunown/gpu-limit",

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    packages=find_packages(),
    data_files=[],
    install_requires=[
        'psutil',
    ],

    entry_points={'console_scripts': [
       'gpulimit-server = gpulimit.gpulimit_server:main',
       'gpulimit = gpulimit.gpulimit_client:main',
       'gpulimitc = gpulimit.gpulimit_client:main',
    ]},

    zip_safe=False
)
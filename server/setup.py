#!/usr/bin/env python

import sys
from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    requires = f.read()


setup(name='wxpy_control', version='0.1',
      long_description=long_description,
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      description='wxpy_control',
      )

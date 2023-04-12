#!/usr/bin/env python

from setuptools import setup
with open("requirements.txt") as f:
    reqs = [line.replace('\n', '') for line in f.readlines()]


setup(name='qlweb',
      version='1.0',
      description='Web API for QL-570',
      install_requires=reqs,
)

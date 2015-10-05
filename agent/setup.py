#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='pulp-agent',
    version='2.8.0a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=['m2crypto']
)

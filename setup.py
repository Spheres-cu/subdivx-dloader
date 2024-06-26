#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup

long_description = open('README.md').read() + '\n' + open('HISTORY.md').read()

setup(
    name='subdivx-dloader',
    version='1.7.5',
    description='A command line tool to download the best matching subtitle from subdivx.com',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=u"Spheres-cu",
    author_email='Spheres-cu@gmail.com',
    url='https://github.com/Spheres-cu/subdivx-dloader',
    packages=['subdivx_dloader',],
    license='GNU GENERAL PUBLIC LICENCE v3.0',
    install_requires=['tvnamer', 'guessit', 'rarfile', 'colorama', 'urllib3', 'certifi', 'rich'],
    entry_points={
        'console_scripts': ['subdivx-dloader=subdivx_dloader.cli:main'],
    },
    classifiers=[
        'Development Status :: 1.7.5',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: Spanish',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ]
)

#!/usr/bin/env python
# -*- coding:utf-8 -*-

from setuptools import setup
from pip.req import parse_requirements

def required_deps():
    '''
    Parse the REQUIREMENTS.txt file and return a list of dependencies.
    
    Returns:
        (list): The list of dependencies.
    '''
    requires = parse_requirements('REQUIREMENTS.txt')
    dependencies = [str(r.req) for r in requires]
    return dependencies

setup(
    name='libipa',
    version='0.0.4',
    author='Andrew Udvare',
    author_email='audvare@gmail.com',
    packages=['ipa'],
    url='https://github.com/Tatsh/libipa',
    license='LICENSE.txt',
    description='Library to read IPA files (iOS application archives).',
    long_description='No description.',
    requires=required_deps(),
    #install_requires=[ 'biplist>=0.7','six>=1.7.3',],
)

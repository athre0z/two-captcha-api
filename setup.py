# -*- coding: utf8 -*-
from distutils.core import setup

setup(
    name='twocaptchaapi',
    version='0.1',
    packages=['twocaptchaapi'],
    url='https://github.com/athre0z/twocaptcha-api',
    license='MIT',
    author='Joel Höner (athre0z)',
    author_email='joel@zyantific.com',
    description='Python API implementation for 2Captcha.com',
    install_requires=[
        'requests>=2.9',
    ],
)

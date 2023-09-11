#!/usr/bin/env python

'''The setup script.'''

from setuptools import setup, find_packages

setup(
    author='JDG, EEM',
    author_email='johnathon.gard@colorado.edu',
    python_requires='>=3.5',
    description='SQUID Series Array Testing Script',
    install_requires=['numpy', 'matplotlib', 'tqdm', 'pyserial'],
    license='MIT license',
    include_package_data=True,
    keywords='SQUID',
    name='SQUID_SSA_Char',
    packages=['squid_ssa_char'],
    test_suite='tests',
    url='https://github.com/DarkTyr/squid_ssa_char',
    version='0.0.0',
    zip_safe=False,
#    package_data={'dastardcommander': ['ui/*.ui', 'ui/*.png']},
#    entry_points={
#        'console_scripts': ['dcom=dastardcommander.dc:main'],
#    },
)
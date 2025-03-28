from setuptools import setup, find_packages

# read the contents of your README file
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='cbpi4-LCD',
      version='0.1.0',
      description='CraftBeerPi4 LCD Plugin',
      author='Alexander Vollkopf',
      author_email='avollkopf@web.de',
      url='https://github.com/PiBrewing/cbpi4-LCDisplay',
      license='GPLv3',
      keywords='globalsettings',
      packages=find_packages(),
      include_package_data=True,
      package_data={
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'cbpi4-LCD': ['*','*.txt', '*.rst', '*.yaml']},
      install_requires=[
      'RPLCD',
      'smbus2',
      ],
      long_description=long_description,
      long_description_content_type='text/markdown'
     )


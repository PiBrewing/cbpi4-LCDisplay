from setuptools import setup, find_packages
<<<<<<< Updated upstream
from os import path
=======
>>>>>>> Stashed changes

# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='cbpi4-LCDisplay',
<<<<<<< Updated upstream
      version='5.0.9',
      description='CraftBeerPi4 LCD Plugin',
      author='Jan Battermann',
      author_email='Jan.Battermann@t-online.de',
      url='https://github.com/JamFfm/cbpi4-LCDisplay',
=======
      version='0.0.4',
      description='CraftBeerPi4 LCD Plugin Mod',
      author='Alexander Vollkopf',
      author_email='avollkopf@web.de',
      url='https://github.com/avollkopf/cbpi4-LCDisplay',
>>>>>>> Stashed changes
      license='GPLv3',
      include_package_data=True,
      package_data={
<<<<<<< Updated upstream
          # If any package contains *.txt or *.rst files, include them:
          '': ['*.txt', '*.rst', '*.yaml'],
          'cbpi4-LCDisplay': ['*', '*.txt', '*.rst', '*.yaml']},
      # packages=['cbpi4-LCDisplay'],
      packages=find_packages(),
      install_requires=[
=======
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'LCDisplay': ['*','*.txt', '*.rst', '*.yaml']},
      #packages=['cbpi4-LCDisplay'],
	    install_requires=[
>>>>>>> Stashed changes
            'cbpi>=4.0.0.33',
            'smbus2',
            'RPLCD',
      ],
      long_description=long_description,
      long_description_content_type='text/markdown'
      )

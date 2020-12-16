from setuptools import setup
from pathlib import Path
from cwatm import __version__, __author__, __email__

setup(
      name='CWatM',
      version=__version__,
      description='The Community Water Model: An open source hydrological model',
      long_description=Path("README.md").read_text(encoding="utf-8"),
      long_description_content_type="text/x-rst",
      license='GPLv3',
      classifiers=[
            'License :: OSI Approved :: GNU General Public License v3',
            'Operating System :: OS Independent',
      ],
      url='https://github.com/CWatM',
      author=__author__,
      author_email=__email__,
      packages=[
            'cwatm',
            'cwatm.hydrological_modules',
            'cwatm.hydrological_modules.groundwater_modflow',
            'cwatm.hydrological_modules.routing_reservoirs',
            'cwatm.hydrological_modules.water_demand',
            'cwatm.management_modules'
      ],
      package_data={
            'cwatm': [
                  'metaNetcdf.xml',
            ],
            'cwatm.hydrological_modules': [
                  'routing_reservoirs/t5.dll',
                  'routing_reservoirs/t5cyg.so',
                  'routing_reservoirs/t5_linux.o',
                  'routing_reservoirs/t5_linux.so',
                  'routing_reservoirs/t5.cpp',
            ],
      },
      zip_safe=True,
      install_requires=[
            'numpy',
            'scipy',
            'netCDF4',
            'gdal',
            'pyflow',
            'pytest',
            'pytest-html'
      ],
      entry_points={
            'console_scripts': ['cwatm=cwatm.run_cwatm:run_from_command_line']
      }
)
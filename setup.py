from setuptools import setup
from cwatm import __version__, __author__, __email__

setup(
      name='CWatM',
      version=__version__,
      description='',
      url='https://github.com/CWatM',
      author=__author__,
      author_email=__email__,
      packages=[
            'cwatm',
            'cwatm.hydrological_modules',
            'cwatm.hydrological_modules.groundwater_modflow',
            'cwatm.hydrological_modules.routing_reservoirs',
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
      ]
)
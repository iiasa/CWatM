from setuptools import setup

setup(name='CWatM',
      version='1.4',
      description='',
      url='https://github.com/CWatM',
      author='Peter Burek',
      author_email='burek@iiasa.ac.at',
      packages=[
            'cwatm',
            'cwatm.hydrological_modules',
            'cwatm.hydrological_modules.groundwater_modflow',
            'cwatm.hydrological_modules.routing_reservoirs',
            'cwatm.management_modules'
      ],
      package_data={
            'cwatm.hydrological_modules': [
                  'routing_reservoirs/t5.dll',
                  'routing_reservoirs/t5cyg.so',
                  'routing_reservoirs/t5_linux.o',
                  'routing_reservoirs/t5_linux.so',
                  'routing_reservoirs/t5.cpp',
            ],
      },
      zip_safe=False,
      install_requires=[
            'numpy',
            'scipy',
            'netCDF4',
            'gdal',
            'pyflow'
      ]
)
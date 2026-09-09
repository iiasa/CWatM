
############
Testing Data
############


Testing data 
============

| The model is only as good as the data!
| To give out a list of data and to check the data the model can run a check.

example::

   python run_cwatm settings1.ini -c
   or
   python run_cwatm settings1.ini -c > checkdata.txt 

A list is created with::

   Name:      Name of the variable
   Filename:  filename or if the value if it is a fixed value
   nonMV:     non missing value in 2D map
   MV:        missing value in 2D map
   lon-lat:   longitude x latitude of 2D map
   CompressV: 2D is compressed to 1D?
   MV-comp:   missing value in 1D
   Zero-comp: Number of 0 in 1D
   NonZero:   Number of non 0 in 1D
   min:       minimum in 1D (or 2D)
   mean:      mean in 1D (or 2D)
   max:       maximum in 1D (or 2D)
   
example::

   Name                          File/Value                                    nonMV         MV    lon-lat   Compress    MV-comp  Zero-comp    NonZero        min       mean        max
   MaskMap                       put5min_netcdf/areamaps/rhine5min.map          5236          0      68x77      False          0       2404       2832       0.00       0.54       1.00
   Ldd                           _5min/input5min_netcdf/routing/ldd.nc          5236          0      68x77      False          0          0       5236       1.00       5.34       9.00
   Mask+Ldd                                                                     2832          0      68x77       True          0       2832          0       0.00       0.00       0.00
   CellArea                      n_netcdf/landsurface/topo/cellarea.nc          2832          0      68x77       True          0          0       2832   5.31E+07   5.63E+07   5.94E+07
   precipitation_coversion       86.4                                              -          -          -          -          -                 86.40           
   evaporation_coversion         1.00                                              -          -          -          -          -                  1.00           
   crop_correct                  1.534                                             -          -          -          -          -                  1.53           
   NumberSnowLayers              7                                                 -          -          -          -          -                  7.00           
   GlacierTransportZone          3                                                 -          -          -          -          -                  3.00           
   ElevationStD                  min_netcdf/landsurface/topo/elvstd.nc          2832          0      68x77       True          0          0       2832       0.04      78.67     672.68
   ...
   ...



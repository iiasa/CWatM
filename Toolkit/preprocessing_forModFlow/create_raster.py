
## I recommend to use a virtual environment where GDal should be installed: C:\Users\guillaumot\Documents\CWatM_ModFlow_preprocess\GdalProj\Scripts\activate
## as well as the other packages
## Due to geopandas, GDAL versionning problem

import subprocess
import numpy as np
import os
from osgeo import gdal, osr
import geopandas as gpd

#GDAL_POLYGONIZE = r"C:\Users\jadeb\Miniconda3\envs\abm\Scripts\gdal_polygonize.py"
GDAL_POLYGONIZE = 'C:/Users/smilovic/AppData/Local/Programs/Python/Python310/Scripts/gdal_polygonize.py'
assert os.path.exists(GDAL_POLYGONIZE)

# these lines are necessary sometimes
from shapely import speedups
speedups.disable()

def create_raster(gt, xsize, ysize, epsg, entrys_file, output_shp):
    """This function creates rasters from CWatM and grid informations in the aim to use them in QGIS.
    arg1: gt : geotransform (x limit, x resolution, 0, y limit, 0, y resolution)
    arg2: x size : number of rows in the grid
    arg3: y size : number of columns in the grid
    arg4: epsg : epsg reference of the coordinates system (4326 for the WGS84 in CWatM,...)
    arg5: entrys_file : path where new information are saved
    arg6: output_shp : Name of the shapefile created created
    """

    tif_file = os.path.join(entrys_file, 'tmp.tif')

    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(tif_file, xsize, ysize, 1, gdal.GDT_Int32)

    array = np.arange(ysize * xsize).reshape((ysize, xsize))

    ds.SetGeoTransform(gt)
    ds.GetRasterBand(1).WriteArray(array)
    source = osr.SpatialReference()
    source.ImportFromEPSG(epsg)
    ds.SetProjection(source.ExportToWkt())
    ds = None

    shapefilename = os.path.join(entrys_file, output_shp)
    subprocess.call("python " + GDAL_POLYGONIZE + f" {tif_file} {shapefilename}", shell=True)
    #gdal.Polygonize(tif_file, -f, output_shp, shell=True)

    gdf = gpd.GeoDataFrame.from_file(os.path.join(entrys_file, output_shp))
    #print('gdf.var :', gdf.var())

    def x():
        for _ in range(ysize):
            for j in range(xsize):
                yield j

    def y():
        for i in range(ysize):
            for _ in range(xsize):
                yield i

    xi = x()
    yi = y()
    #print('gdf :', gdf)
    gdf['x'] = gdf['DN'].apply(lambda _: next(xi))
    gdf['y'] = gdf['DN'].apply(lambda _: next(yi))

    gdf = gdf.drop('DN', axis=1)

    gdf.to_file(os.path.join(entrys_file, output_shp))
    os.remove(os.path.join(entrys_file, 'tmp.tif'))

    print('/nShapefile created :/n', os.path.join(entrys_file, output_shp))

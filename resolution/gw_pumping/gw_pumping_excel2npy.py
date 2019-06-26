
# @author: Luca, edited Mikhail

# Import modules
import numpy as np
import pyproj
import xlrd

## DEFINE GEOREFERENCING SYSTEM ##
wgs84=pyproj.Proj("+init=EPSG:4326")        # Associated coord system
UTM=pyproj.Proj("+init=EPSG:32643")         # Projection system for the Upper Bhima basin

wb1 = xlrd.open_workbook("pumping_wells.xlsx")
sh1 = wb1.sheet_by_name(u'Sheet1')

lon=[]
lat=[]
pumping = []

header_row = 4 # The row with the column titles

for i in range(header_row, sh1.nrows):

    a=sh1.row_values(i)[0]
    b=sh1.row_values(i)[1]
    p = -1 * sh1.row_values(i)[2] # pumping rates in the Excel are positive, and here made negative

    lat.append(a)
    lon.append(b)
    pumping.append(p)


## CONVERSION OF THE COORDINATES into UTM ##

x=[]
y=[]

for i in range (len(lat)):
    Coord=pyproj.transform(wgs84, UTM, lon[i], lat[i])
    x.append(Coord[0])
    y.append(Coord[1])

print(x)
print(y)

##Conversion into indices
f = open('UB_limits.txt')
lines = list(f)

min_x = float(lines[0])//1
max_y = float(lines[2])//1

xi=[]
yi=[]

for i in range (len(lat)):
    xi.append( int((x[i] - min_x)//500))
    yi.append( int((max_y - y[i])//500))

print(xi)
print(yi)


Wells = np.array([[yi[i], xi[i], pumping[i]] for i in range(len(lat))])



## SAVE DATA ##
np.save('Pumping_input_file', Wells)
# Script to calculate upstream area, manning coefficient, and channel width
# by PB, edited by MS 07.02.2019

# USAGE: pcrcalc -f mann_width.mod 

# Input:
# ------
# ldd.map
# cell area map
# dem

# Creates:
# --------
# upa.map
# chanman.map
# chanwidth.map

binding

Ldd = "ldd_UB.map";
ChanArea = "cellarea_UB.map";
DEM = "dem_UB.map";

areamap Ldd;
timer 1 1 1;

initial

##-------------------------------------------------
# Upstream contributing area (pixels) for each pixel 

upstream = accuflux(Ldd,1);
upstreamArea = accuflux(Ldd,ChanArea);
#report upa.map = upstreamArea;

##----------------------------------------------------------------
## chanmanning

chanmann = 0.025 + 0.015 *min((2*ChanArea)/upstreamArea,1) + 0.030*min(DEM/2000,1);

report chanmann.map=chanmann;

##----------------------------------------------------------------
## chanwidth

chanwidth = upstreamArea/(500.);
chanwidth = max(chanwidth,3.0);

report chanwidth.map = chanwidth;








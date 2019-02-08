# Script to calculate channel banfull depth
#
# by PB, edited by MS 08.02.2019
# USAGE: pcrcalc -f height.mod 

binding

Ldd="ldd_UB.map";
Cell_area = "cellarea_UB.map";

##disavg="avgdis.map";
##chanman="chanman.map";
##chanbw="chanbw.map";
##chanslope="changrad.map";

areamap Ldd;
timer 1 1 1;

initial
##----------------------------------------------------------------
# chanbnkf

# old 
upstream=accuflux(Ldd, Cell_area)/1;
chanbnkf= 0.27 * (upstream**0.26);

# new

# using manning strickler euqation see Burek Lisflood handbook 
# and solving it for heigh
# assumption: bankful discharge = 2 x average discharge
#     Perimeter = Width + 2 x Height but difficult to solve so:
#     assuming height << width: Perimeter = 1.01*Width

##dis=2*disavg;
##chanbnkf=1.004*(chanman**(3/5))*(dis**(3/5))*(chanbw**(-3/5))*(chanslope**(-3/10));

report chanheight_UB.map=chanbnkf;

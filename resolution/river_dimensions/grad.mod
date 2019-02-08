# Script to calculate channel slope/gradient
#
# by PB, edited by MS 07.02.2019
# USAGE: pcrcalc -f chanslope.mod 


# several assumptions:
# - water level and natural riverbeds are parallel with the neigbouring surface
# - riverbeds are located at the bottom of a valley
#     --> in a 5 x 5 km2 pixel the lowest point is the bottom of a valley
# the difference in elevation of a channel is the difference of the lowest point in the
# next upstream pixel and the lowest point
# Channel length is taken from the channel length map

# Improvements
# Katalin shifted the whole elevation upstream:
#    so every slope value in a cell is the value of the downstream cell
#    maybe the effect is not so import but:
#    a. it is wrong
#    b. all the most upstream pixel (maybe  half of all pixels) are not taken into account
# Therefore I changed this:
#  shifting the elevation downstream is diffculty, because a cell can have more than 1 tributaries (a junction)
#     - therefore  only tributaries are taken, which have an contributing upstream area >= average contributing upstream area


# Shortcomings:
# a. in a 5 x 5 km 2 pixel the loest point could be very low and belonging to a 
#      small piece of floodplain from a bigger (lower) river
#        -> its a lot of effort to fix this



binding

# Script uses:
# ldd.map
# SRTM 100m resolution aggregated to 5 x  5 km2 median      -> e.g. europemedian.map 
# SRTM 100m resolution aggregated to minimum in 5 x  5 km2  -> e.g. europemin.map
# Length of each channel in a 5 x 5 km2 gridcell            -> chanleng.map 


Ldd = "india_ldd2.map";
DEM = "as_dem_30s_clone.map";
ChanL="chanleng_clone.map";

DGMmedian="Aggrega_median_clone.map";
DGMmin="Aggrega_minimum1_clone.map";

areamap Ldd;

timer 1 1 1;

initial

# step 0
# Upstream contributing area (pixels) for each pixel 
upstream=accuflux(Ldd,1);


#report ups1.map=upstream;

# step 1
# how many upstream cells are flowing into a cell
uptrib=upstream(Ldd,1);


# step 2
# what is the average number of upstream pixels 
# dividing the sum of upstream area of a cell (minus 1 for the cell itself) with the number of tributaries
upmean=cover((upstream-scalar(1))/uptrib,scalar(1));

# step 3
# shifting upmean 1 cell upstream 
#  (the command in pcraster is downstream -- cell gets value of the neighbouring downstream cell
#    I always get irritated because downstream shifts the value upstream)
downmean=downstream(Ldd,upmean);

#step 4
# In this part the tributaries are dismissed, which have less upstream pixels than the average tributary
# -> only the big rivers are taken into account (small tributaries may have a really step slope)
downbool=if(upstream ge downmean,scalar(1),scalar(0));

# step 5
# now this information is shifted back to the origin (-> downstream)
# but shifting downstream is not as simple as upstream, because:
# upstream:    1 cell is distrubuted to 1 cell or more than 1 cell (a clear cut)
# downstream:  1 or more cells  are distributed to 1 cell ( not a clear cut)
#             therefore pcraster calculate the sum of the upstream cells
upbool=upstream(Ldd,downbool);
   #  calculate the number of used tributaries for each cell
upmindgm=upstream(Ldd,(downbool*DGMmin));
   # calculate the sum of minimum elevation of used tributaries
   
# step 6
# the lowest point in (a) upstream cell(s) = the highest point in the channel for the considered cell
# diving the sum of upstream mininmal elevations with the number of tribitaries
# e.g. if there is only 1 tributary (no junction) than the min. value of the cell is tranferred to the condidered cell
DGMminmax=upmindgm/upbool;


  
# step 7
# the difference in elevation of a channel is:
# Minimum of upstream cell(s) - minimum of cell
diff=DGMminmax-DGMmin;


report diff.map=diff;

# step 8
# calculation the slope: difference / length
chslope=diff/ChanL;


report slope1.map=chslope;

# step 9
# we are still missing the most upstream part with a upstream = 1, because there is no DGMminmax
# I assume a slope in a river can be described with an exponential function
# elevation = Elevation(Min) * exp(k * length of the river)
# with k as topographic constant deriving from
# k = ln(elev(median)/elev(min))/(celllength/2)
#k=ln(max(1,DGMmedian)/max(1,DGMmin))/scalar(2500);
k=ln(max(1,DGMmedian)/max(1,DGMmin))/(ChanL/2);


# so next assumption:
# to get the slope I am using the derivative: elev * exp(k*x)  --> k * elev * exp(k*x)
# (the derivative of a function  = the slope)
# slope = k * Elevetion(MIN) * exp(k*x)
# Now I have to decide with x
# at the outlet x=0, but the slope at the outlet is maybe not representative for the whole pixel
# - assuming at the top pixel, every part of the pixel is contributing to the middle
# - and a real river forms from the middle of a pixel to the border -> total river length = 2500
# now I take the half : 1250

# or with grad 0.1

#slope=k*max(0,DGMmin)*exp(k*1250);
slope=k*max(0,DGMmin)*exp(k*(ChanL/4));
report slope2.map=slope;


# step 10
# joining both parts
# a chanel slope should be > 0 but values above 0.7 are also unusual
chslope=cover(chslope,slope);
chslope=min(max(chslope,scalar(0.00001)),scalar(0.2));




# step 11
# smoothen the big streams
# for every stream >= 100 pixels the slope is smoothen
# by a 3 x 3 pixel window
bigch=if(upstream ge 500,chslope);
bigch0=if(boolean(bigch),windowaverage(bigch,0.5));
bigch=if(upstream ge 100,chslope);
bigch1=if(boolean(bigch),windowaverage(bigch,0.3));
bigch=if(upstream ge 50,chslope);
bigch2=if(boolean(bigch),windowaverage(bigch,0.2));

chslope=cover(bigch0,bigch1,bigch2,chslope);




# step 12  - report the result

report changrad.map=chslope;

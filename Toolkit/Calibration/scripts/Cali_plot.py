# -*- coding: utf-8 -*-
"""Please refer to quick_guide.pdf for usage instructions"""

import os
import sys
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
import hydroStats
import numpy as np
import datetime
import pdb
import time
import pandas
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()



import math
import glob
import string
from configparser import ConfigParser

from sys import platform

from matplotlib import rcParams
#from matplotlib import rc

#rc('font',**{'family':'serif','serif':['Palatino']})
#rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})
#rc('text', usetex=False)
rcParams.update({'figure.autolayout': True})

t = time.time()


#load = "streamflow_simulated_best"
#iniFile = "settings_fast_2.txt"

iniFile = os.path.normpath(sys.argv[1])
savefig = os.path.normpath(sys.argv[2])

station = "lobith"
loadsim = "streamflow_simulated_best.csv"
#savefig = "calibration_plot.pdf"

########################################################################
#   Read settings file
########################################################################

(drive, path) = os.path.splitdrive(iniFile)
(path, fil)  = os.path.split(path)
print (">> Reading settings file ("+fil+")...")

##PB file_CatchmentsToProcess = os.path.normpath(sys.argv[2])

parser = ConfigParser()
parser.read(iniFile)

if platform == "win32":
    root = parser.get('DEFAULT','RootPC')
else:
	root = parser.get('DEFAULT', 'Root')
#rootbasin = os.path.join(root,parser.get('DEFAULT', 'Rootbasin'))
rootbasin = root +"/"+ parser.get('DEFAULT', 'Rootbasin')

ForcingStart = datetime.datetime.strptime(parser.get('DEFAULT','ForcingStart'),"%d/%m/%Y")  # Start of forcing
ForcingEnd = datetime.datetime.strptime(parser.get('DEFAULT','ForcingEnd'),"%d/%m/%Y")  # Start of forcing

#WarmupDays = int(parser.get('DEFAULT', 'WarmupDays'))
WarmupDays = 0

#SubCatchmentPath = os.path.join(rootbasin,parser.get('Path','SubCatchmentPath'))
SubCatchmentPath =  rootbasin +"/"+ parser.get('Path','SubCatchmentPath')

#path_result = parser.get('Path', 'Result')

Qtss_csv = os.path.join(rootbasin,parser.get('ObservedData', 'Qtss'))
Qtss_col = parser.get('ObservedData', 'Column')
Header = parser.get('ObservedData', 'Header')

##PB Qgis_csv = parser.get('CSV', 'Qgis')



########################################################################
#   Loop through catchments and perform calibration
########################################################################

print (">> Reading Qgis2.csv file...")
#stationdata = pandas.read_csv(os.path.join(path_result,"Qgis2.csv"),sep=",",index_col=0)
#stationdata_sorted = stationdata.sort_index(by=['CatchmentArea'],ascending=True)
stationdata_sorted = [1]

"""
PB CatchmentsToProcess = pandas.read_csv(file_CatchmentsToProcess,sep=",",header=None)
for index, row in stationdata_sorted.iterrows():
	Series = CatchmentsToProcess.ix[:,0]
	if len(Series[Series==str(row["ID"])]) == 0: # Only process catchments whose ID is in the CatchmentsToProcess.txt file
		continue
	path_subcatch = os.path.join(SubCatchmentPath,row['ID'])
	
	print (row['ID']+" "+row['Val_Start']) # For debugging
"""
for index in stationdata_sorted:
	path_subcatch = os.path.join(SubCatchmentPath)
	print (index, path_subcatch)
	#if index!=805: # Runs only this catchment
	#    continue
		
	# Make figures directory
	#try:
	#	os.stat(os.path.join(path_subcatch,"FIGURES"))
	#except:
	#	os.mkdir(os.path.join(path_subcatch,"FIGURES"))
		
	# Delete contents of figures directory
	#for filename in glob.glob(os.path.join(path_subcatch,"FIGURES",'*.*')):
	#	os.remove(filename)

	# Compute the time steps at which the calibration should start and end
	"""
	if row['Val_Start'][:10]!="Streamflow": # Check if Q record is long enough for validation
		Val_Start = datetime.datetime.strptime(row['Val_Start'],"%m/%d/%Y")
		Val_End = datetime.datetime.strptime(row['Val_End'],"%m/%d/%Y")
		Val_Start_Step = (Val_Start-ForcingStart).days+1 # For LISFLOOD, not for indexing in Python!!!
		Val_End_Step = (Val_End-ForcingStart).days+1 # For LISFLOOD, not for indexing in Python!!!
	else:
		Val_Start = []
		Val_End = []
		Val_Start_Step = []
		Val_End_Step = []

	Cal_Start = datetime.datetime.strptime(row['Cal_Start'],"%m/%d/%Y")
	Cal_End = datetime.datetime.strptime(row['Cal_End'],"%m/%d/%Y")
	Cal_Start_Step = (Cal_Start-ForcingStart).days+1 # For LISFLOOD, not for indexing in Python!!!
	Cal_End_Step = (Cal_End-ForcingStart).days+1 # For LISFLOOD, not for indexing in Python!!!
	Forcing_End_Step = (ForcingEnd-ForcingStart).days+1 # For LISFLOOD, not for indexing in Python!!!
	"""

	ForcingStart = datetime.datetime.strptime(parser.get('DEFAULT', 'ForcingStart'), "%d/%m/%Y")  # Start of forcing
	ForcingEnd = datetime.datetime.strptime(parser.get('DEFAULT', 'ForcingEnd'), "%d/%m/%Y")  # Start of forcing
	Cal_Start = ForcingStart
	Cal_End = ForcingEnd

	# Load observed streamflow
	streamflow_data = pandas.read_csv(Qtss_csv, sep=",", parse_dates=True, index_col=0)
	#Qobs1 = streamflow_data[Qtss_col] * 1.0

	Qobs1 = streamflow_data[station] * 1.0
	#streamflow_data = pandas.read_csv(Qtss_csv,sep=",", parse_dates=True, index_col=0, infer_datetime_format=True)
	#Qobs = streamflow_data[row['ID']]
	#Qobs[Qobs<0] = np.NaN
	print (ForcingStart,ForcingEnd, Qobs1.shape)
	print (path_subcatch,loadsim)
	
	# Load streamflow of best run
	if os.path.isfile(os.path.join(path_subcatch,loadsim)):
		#print "Making figures for catchment "+row['ID']+", size "+str(row['CatchmentArea'])+" pixels..."
		print ("Making figures for catchment ")
		#Qsim1 = pandas.read_csv(os.path.join(path_subcatch,loadsim), sep=",", parse_dates=True, index_col=0, header=None)
		Qsim1 = pandas.read_csv(os.path.join(path_subcatch,loadsim), sep=",", parse_dates=True, index_col=0, header=None)
		#Qsim1 = streamflow_data[station+"SIM"] * 1.0

	else:
		print ("streamflow_simulated_best.csv missing for catchment")
		continue
		
	#Qsim = Qsim.ix[:,1] # from dataframe to series
	Qobs1[Qobs1 < -9000] = np.nan
	Qobs = Qobs1[~np.isnan(Qobs1)]
	Qsim = Qsim1[~np.isnan(Qobs1)]


	# Make dataframe with aligned Qsim and Qobs columns
	Q = pandas.concat([Qsim, Qobs], axis=1)#.reset_index()
	
	
	########################################################################
	#   Make figure consisting of several subplots
	########################################################################


	fig = plt.figure()
	fig.tight_layout()
	gs = plt.GridSpec(26,12)
	
	# TEXT OF CALIBRATION RESULTS
	ax0 = plt.subplot(gs[0,2:11])
	#texts = r"\huge \bfseries "+str(row["ID"])+": "+str(row["RiverName"])+" at "+str(row["StationName"])
	#texts = r"\huge \bfseries " + "1  River: Nile, Station: Jinja Pier"
	#texts = r"\huge \bfseries " + Header
	texts = Header

	
	#texts = texts.replace("_","\_")
	#texts_filtered = filter(lambda x: x in string.printable, texts)
	#ax0.text(0.5, 0.0, texts_filtered, verticalalignment='top',horizontalalignment='center', transform=ax0.transAxes)
	ax0.text(0.5, 2.0, texts, verticalalignment='top', horizontalalignment='center', transform=ax0.transAxes,fontsize=10)
	#ax0.text(100, 140, texts,fontsize=12, weight='bold')
	plt.axis('off')

	
	# FIGURE OF CALIBRATION PERIOD TIME SERIES
	Dates_Cal = Q.loc[Cal_Start:Cal_End].index
	#Q_sim_Cal = Q.loc[Cal_Start:Cal_End].ix[:,0].values
	#Q_obs_Cal = Q.loc[Cal_Start:Cal_End].ix[:,1].values
	Q_sim_Cal = Q[1].values
	Q_obs_Cal = Q[station].values



	ax1 = plt.subplot(gs[2:6,1:11])
	ax1.plot(Dates_Cal,Q_sim_Cal,'r',Dates_Cal,Q_obs_Cal,'b', linewidth=1)
	ax1.set_title('(a) Streamflow time series for calibration period',  fontsize=8)
	locs, labels = plt.xticks(fontsize= 6)
	plt.setp(labels,rotation=0)
	plt.ylabel(r'Streamflow [m$^{3}$ s$^{-1}$]', fontsize=6)
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label] +
				 ax1.get_xticklabels() + ax1.get_yticklabels()):
		item.set_fontsize(6)

	ns = hydroStats.NS(s=Q_sim_Cal,o=Q_obs_Cal,warmup=WarmupDays)
	corrS = r'  R$^{2}$'
	statsum = r" " \
		+"KGE="+"{0:.2f}".format(hydroStats.KGE(s=Q_sim_Cal, o=Q_obs_Cal, warmup=WarmupDays)) \
		+"  NSE="+"{0:.2f}".format(hydroStats.NS(s=Q_sim_Cal,o=Q_obs_Cal,warmup=WarmupDays)) \
		+ r'  R$^{2}$=' +"{0:.2f}".format(hydroStats.correlation(s=Q_sim_Cal, o=Q_obs_Cal, warmup=WarmupDays)) \
		+"  B="+"{0:.2f}".format(hydroStats.pc_bias2(s=Q_sim_Cal,o=Q_obs_Cal,warmup=WarmupDays)) +"%"
	ax1.text(0.025, 0.93, statsum, verticalalignment='top',horizontalalignment='left', transform=ax1.transAxes, fontsize=6)
	leg = ax1.legend(['Simulated', 'Observed'], fancybox=True, framealpha=0.8,prop={'size':6},labelspacing=0.1, loc = 1)
	leg.get_frame().set_edgecolor('white')

	
	# FIGURE OF XY scatter plot
	ax2 = plt.subplot(gs[11:15,1:6])
	t = np.arange(len(Q_sim_Cal))
	print (t.shape)
	#t = np.arange(5844)
	#qmax = 500
	qmax = max(np.max(Q_sim_Cal),np.max(Q_obs_Cal)) * 1.1

	#ax2.plot(Q_sim_Cal,'r',Q_obs_Cal,'b')
	#ax2.scatter(Q_obs_Cal, Q_sim_Cal, c=t, cmap='viridis_r')
	ax2.scatter(Q_obs_Cal, Q_sim_Cal, c='blue', s=10,edgecolors  ="black")
	
	ax2.plot([0,qmax],[0,qmax], 'r--', linewidth=1)
	ax2.set_title('(b) Scatterplot for calibration period',  fontsize=8)
	plt.xlim([0,qmax])
	plt.ylim([0,qmax])
	plt.ylabel(r'Sim. Streamflow [m$^{3}$ s$^{-1}$]')
	plt.xlabel(r'Obs. Streamflow [m$^{3}$ s$^{-1}$]')

	for item in ([ax2.title, ax2.xaxis.label, ax2.yaxis.label] +
				 ax2.get_xticklabels() + ax2.get_yticklabels()):
		item.set_fontsize(6)



	# FIGURE OF TEXT VALUES

	#ax = plt.subplot(gs[8:9, 8:11])
	ax = plt.subplot(gs[7, 8:11],frame_on=False)
	ax.xaxis.set_visible(False)
	ax.yaxis.set_visible(False)

	cols = ('Obs.','Sim.')
	rows =('KGE','NS','NSlog',r'R$^{2}$','Bias','RMSE','MAE',' ','Mean',"Min","5%","50%","95%","99%","Max")

	cell_text = [["","{0:.3f}".format(hydroStats.KGE(s=Q_sim_Cal, o=Q_obs_Cal, warmup=WarmupDays))],
				 ["","{0:.3f}".format(hydroStats.NS(s=Q_sim_Cal,o=Q_obs_Cal,warmup=WarmupDays))],
				 ["", "{0:.3f}".format(hydroStats.NSlog(s=Q_sim_Cal, o=Q_obs_Cal, warmup=WarmupDays))],
				 ["","{0:.3f}".format(hydroStats.correlation(s=Q_sim_Cal, o=Q_obs_Cal, warmup=WarmupDays))],
				 ["","{0:.2f}%".format(hydroStats.pc_bias2(s=Q_sim_Cal,o=Q_obs_Cal,warmup=WarmupDays))],
				 ["", "{0:.0f}".format(hydroStats.rmse(s=Q_sim_Cal, o=Q_obs_Cal, warmup=WarmupDays))],
				 ["", "{0:.0f}".format(hydroStats.mae(s=Q_sim_Cal, o=Q_obs_Cal, warmup=WarmupDays))],
				 ["",""],
				 ["{0:.0f}".format(np.mean(Q_obs_Cal)),"{0:.0f}".format(np.mean(Q_sim_Cal))],
				 ["{0:.0f}".format(np.min(Q_obs_Cal)), "{0:.0f}".format(np.min(Q_sim_Cal))],
				 ["{0:.0f}".format(np.percentile(Q_obs_Cal,5)),"{0:.0f}".format(np.percentile(Q_sim_Cal,5))],
				 ["{0:.0f}".format(np.percentile(Q_obs_Cal, 50)), "{0:.0f}".format(np.percentile(Q_sim_Cal, 50))],
				 ["{0:.0f}".format(np.percentile(Q_obs_Cal, 95)), "{0:.0f}".format(np.percentile(Q_sim_Cal, 95))],
				 ["{0:.0f}".format(np.percentile(Q_obs_Cal, 99)), "{0:.0f}".format(np.percentile(Q_sim_Cal, 99))],
				 ["{0:.0f}".format(np.max(Q_obs_Cal)),"{0:.0f}".format(np.max(Q_sim_Cal))]]
	thetable = ax.table(cellText=cell_text,  rowLabels=rows, colLabels=cols, colWidths = [.5,.9])
	thetable.set_fontsize(8)


	#texts = r"(b) Calibration statistic"
	#texts_filtered = filter(lambda x: x in string.printable, texts)
	#ax.text(0.0, 0.0, texts_filtered, verticalalignment='top', horizontalalignment='center', transform=ax.transAxes, fontsize=14)
	#plt.axis('off')


	"""
	# FIGURE OF VALIDATION PERIOD TIME SERIES
	#if row['Val_Start'][:10]!="Streamflow": # Check if Q record is long enough for validation
	i = 1
	if i == 1:
		Dates_Val = Q.loc[Val_Start:Val_End].index
		Q_sim_Val = Q.loc[Val_Start:Val_End].ix[:,0].values
		Q_obs_Val = Q.loc[Val_Start:Val_End].ix[:,1].values
		if len(Q_obs_Val[~np.isnan(Q_obs_Val)])>(365*2):
			ax2 = plt.subplot(gs[4:7,:])
			ax2.plot(Dates_Val,Q_sim_Val,'r',Dates_Val,Q_obs_Val,'b')
			ax2.set_title('(b) Streamflow time series for validation period')
			plt.ylabel(r'Streamflow [m$^3$ s$^{-1}$]')
			statsum = r"$R="+"{0:.2f}".format(HydroStats.correlation(s=Q_sim_Val,o=Q_obs_Val,warmup=WarmupDays))+"$, NS$_\mathrm{log}="+"{0:.2f}".format(HydroStats.NSlog(s=Q_sim_Val,o=Q_obs_Val,warmup=WarmupDays))+"$, $B="+"{0:.2f}".format(HydroStats.pc_bias2(s=Q_sim_Val,o=Q_obs_Val,warmup=WarmupDays))+"$ \%"
			ax2.text(0.025, 0.93, statsum, verticalalignment='top', horizontalalignment='left', transform=ax2.transAxes)
	"""
		
	# FIGURE OF MONTHLY CLIMATOLOGY FOR CALIBRATION PERIOD
	Q_obs_clim_Cal = np.zeros(shape=(12,1))*np.NaN
	Q_sim_clim_Cal = np.zeros(shape=(12,1))*np.NaN
	Q_obs_clim_Cal_stddev = np.zeros(shape=(12,1))*np.NaN
	Q_sim_clim_Cal_stddev = np.zeros(shape=(12,1))*np.NaN
	for month in range(1,13):
		mask = ~np.isnan(Q_obs_Cal) & ~np.isnan(Q_sim_Cal)
		Q_obs_clim_Cal[month-1] = np.mean(Q_obs_Cal[(Dates_Cal.month==month) & mask])
		Q_sim_clim_Cal[month-1] = np.mean(Q_sim_Cal[(Dates_Cal.month==month) & mask])
		Q_obs_clim_Cal_stddev[month-1] = np.std(Q_obs_Cal[(Dates_Cal.month==month) & mask])
		Q_sim_clim_Cal_stddev[month-1] = np.std(Q_sim_Cal[(Dates_Cal.month==month) & mask])

	ax3 = plt.subplot(gs[19:24,1:6])
	months = np.array([9,10,11,12,1,2,3,4,5,6,7,8,9,10]) # water year
	ax3.fill_between(np.arange(0,14),(Q_sim_clim_Cal[months-1]+0.5*Q_sim_clim_Cal_stddev[months-1]).reshape(-1),(Q_sim_clim_Cal[months-1]-0.5*Q_sim_clim_Cal_stddev[months-1]).reshape(-1),facecolor='red',alpha=0.1,edgecolor='none')
	ax3.fill_between(np.arange(0,14),(Q_obs_clim_Cal[months-1]+0.5*Q_obs_clim_Cal_stddev[months-1]).reshape(-1),(Q_obs_clim_Cal[months-1]-0.5*Q_obs_clim_Cal_stddev[months-1]).reshape(-1),facecolor='blue',alpha=0.1,edgecolor='none')
	ax3.plot(range(0,14),Q_sim_clim_Cal[months-1],'r',range(0,14),Q_obs_clim_Cal[months-1],'b',  linewidth=1)
	ax3.set_title('(c) Monthly $Q$ climatology cal.\ period')
	#leg2 = ax3.legend(['121', '122','343','334'], loc='best', fancybox=True, framealpha=0.5,prop={'size':12},labelspacing=0.1)
	plt.xticks(range(0,14), months)
	plt.xlim([0.5,12.5])
	plt.ylabel(r'Streamflow [m$^3$ s$^{-1}$]')
	plt.xlabel(r'Month')
	leg.get_frame().set_edgecolor('white')

	for item in ([ax3.title, ax3.xaxis.label, ax3.yaxis.label] +
				 ax3.get_xticklabels() + ax3.get_yticklabels()):
		item.set_fontsize(6)

	"""
	# FIGURE OF MONTHLY CLIMATOLOGY FOR VALIDATION PERIOD
	#if row['Val_Start'][:10]!="Streamflow": # Check if Q record is long enough for validation
	i = 1
	if i == 1:
		#if len(Q_obs_Val[~np.isnan(Q_obs_Val)])>365:
		if len(Q_obs_Cal[~np.isnan(Q_obs_Cal)]) > 365:
			Q_obs_clim_Val = np.zeros(shape=(12,1))*np.NaN
			Q_sim_clim_Val = np.zeros(shape=(12,1))*np.NaN
			Q_obs_clim_Val_stddev = np.zeros(shape=(12,1))*np.NaN
			Q_sim_clim_Val_stddev = np.zeros(shape=(12,1))*np.NaN
			for month in range(1,13):
				#mask = ~np.isnan(Q_obs_Val) & ~np.isnan(Q_sim_Val)
				mask = ~np.isnan(Q_obs_Cal) & ~np.isnan(Q_sim_Cal)
				#Q_obs_clim_Val[month-1] = np.mean(Q_obs_Val[(Dates_Val.month==month) & mask])
				Q_obs_clim_Val[month - 1] = np.mean(Q_obs_Cal[(Dates_Cal.month == month) & mask])
				#Q_sim_clim_Val[month-1] = np.mean(Q_sim_Val[(Dates_Val.month==month) & mask])
				Q_sim_clim_Val[month - 1] = np.mean(Q_sim_Cal[(Dates_Cal.month == month) & mask])
				#Q_obs_clim_Val_stddev[month-1] = np.std(Q_obs_Val[(Dates_Val.month==month) & mask])
				Q_obs_clim_Val_stddev[month - 1] = np.std(Q_obs_Cal[(Dates_Cal.month == month) & mask])
				#Q_sim_clim_Val_stddev[month-1] = np.std(Q_sim_Val[(Dates_Val.month==month) & mask])
				Q_sim_clim_Val_stddev[month - 1] = np.std(Q_sim_Cal[(Dates_Cal.month == month) & mask])
			ax4 = plt.subplot(gs[7:10,3:6])
			months = np.array([9,10,11,12,1,2,3,4,5,6,7,8,9,10]) # water year            
			ax4.fill_between(np.arange(0,14),(Q_sim_clim_Val[months-1]+0.5*Q_sim_clim_Val_stddev[months-1]).reshape(-1),(Q_sim_clim_Val[months-1]-0.5*Q_sim_clim_Val_stddev[months-1]).reshape(-1),facecolor='red',alpha=0.1,edgecolor='none')
			ax4.fill_between(np.arange(0,14),(Q_obs_clim_Val[months-1]+0.5*Q_obs_clim_Val_stddev[months-1]).reshape(-1),(Q_obs_clim_Val[months-1]-0.5*Q_obs_clim_Val_stddev[months-1]).reshape(-1),facecolor='blue',alpha=0.1,edgecolor='none')
			ax4.plot(range(0,14),Q_sim_clim_Val[months-1],'r',range(0,14),Q_obs_clim_Val[months-1],'b')
			ax4.set_title('(d) Monthly $Q$ climatology val.\ period')
			plt.xticks(range(0,14), months)
			plt.xlim([0.5,12.5])
			plt.ylabel(r'Streamflow [m$^3$ s$^{-1}$]')
			plt.xlabel(r'Month')
	"""
	"""
	# FIGURES OF CALIBRATION EVOLUTION
	front_history = pandas.read_csv(os.path.join(path_subcatch,"front_history.csv"),sep=",", parse_dates=True, index_col=0)    

	ax10 = plt.subplot(gs[20:25,0:4])
	x = front_history['gen'].values
	#plt.fill_between(x,front_history["effavg_R"].values-0.5*front_history["effstd_R"].values, front_history["effavg_R"].values+0.5*front_history["effstd_R"].values, facecolor='0.8',edgecolor='none')
	#plt.hold(True)
	plt.plot(x,front_history['effavg_R'].values,'black', linewidth=1)
	ax10.set_title('(d) KGE evolution')
	ax = plt.gca()
	plt.ylabel(r"KGE")
	plt.xlabel(r"Generation")
	#p = plt.Rectangle((0, 0), 0, 0, facecolor='0.8',edgecolor='none')
	#ax.add_patch(p)
	#leg2 = ax10.legend(['Mean', 'Std.\ dev.'], loc=4, fancybox=True, framealpha=0.8,prop={'size':12},labelspacing=0.1)
	#leg2.get_frame().set_edgecolor('white')
	##leg2.draw_frame(False)
	"""
	"""
	ax11 = plt.subplot(gs[10:13,2:4])
	plt.fill_between(x,front_history["effavg_R"].values-0.5*front_history["effstd_R"].values, front_history["effavg_R"].values+0.5*front_history["effstd_R"].values, facecolor='0.8',edgecolor='none')
	plt.hold(True)
	plt.plot(x,front_history['effavg_R'].values,'black')
	ax11.set_title('(f) Pareto front KGE')
	ax = plt.gca()
	plt.ylabel(r"KGE [$-$]")
	plt.xlabel(r"Generation")
	
	ax12 = plt.subplot(gs[10:13,4:6])
	plt.fill_between(x,front_history["effavg_B"].values-0.5*front_history["effstd_B"].values, front_history["effavg_B"].values+0.5*front_history["effstd_B"].values, facecolor='0.8',edgecolor='none')
	plt.hold(True)
	plt.plot(x,front_history['effavg_B'].values,'black')
	ax12.set_title('(g) Pareto front $|B|$')
	ax = plt.gca()
	plt.ylabel(r"$|B|$ [\%]")
	plt.xlabel(r"Generation")
	"""
	
	#adjustprops = dict(left=0.1, bottom=0, right=1, top=1, wspace=-0.2, hspace=0.0)
	#fig.subplots_adjust(**adjustprops)
	#plt.tight_layout()
	#plt.show()
	plt.draw()
	
	#gs.tight_layout(fig,rect=[0,0.03,1,0.95]) #pad=0.1, w_pad=0.1, h_pad=0.1
	
	#fig.set_size_inches(22/2.54,30/2.54)
	
	#fig.savefig(os.path.join(path_subcatch,"FIGURES",row['ID']+'_summary.pdf'), format='PDF')
	#fig.savefig(os.path.join(path_subcatch,"FIGURES",row['ID']+'_summary.png'), dpi=300, format='PNG')
	#fig.savefig(os.path.join(path_subcatch,"FIGURES","1"+'_summary.pdf'), format='PDF')


	#fig.savefig(os.path.join(path_subcatch,"FIGURES",savefig), dpi=400, format='PNG')
	#fig.savefig(os.path.join(path_subcatch, "FIGURES", savefig), format='PDF')
	fig.savefig('figures/'+savefig, format='PDF')

	#plt.show()
	plt.close("all")

	#pdb.set_trace()
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Calibration tool for Hydrological models
using a distributed evolutionary algorithms in python
DEAP library
https://github.com/DEAP/deap/blob/master/README.md

Félix-Antoine Fortin, François-Michel De Rainville, Marc-André Gardner, Marc Parizeau and Christian Gagné, "DEAP: Evolutionary Algorithms Made Easy", Journal of Machine Learning Research, vol. 13, pp. 2171-2175, jul 2012

The calibration tool was created by Hylke Beck 2014 (JRC, Princeton) hylkeb@princeton.edu
Thanks Hylke for making it available for use and modification
Modified by Peter Burek

The submodule Hydrostats was created 2011 by:
Sat Kumar Tomer (modified by Hylke Beck)
Please see his book "Python in Hydrology"   http://greenteapress.com/pythonhydro/pythonhydro.pdf

"""
import os
import sys
import shutil
import hydroStats
import array
import random
import numpy as np
import datetime
from deap import algorithms
from deap import base
from deap import benchmarks
from deap import creator
from deap import tools
import pandas

import multiprocessing
import time
from configparser import ConfigParser
import glob
from subprocess import Popen, PIPE

import ast
from sys import platform
import pickle

## Set global parameter
global gen
gen = 0
WarmupDays = 0


########################################################################
#   Read settings file
########################################################################

iniFile = os.path.normpath(sys.argv[1])

parser = ConfigParser()
parser.read(iniFile)

if platform == "win32":
    root = parser.get('DEFAULT','RootPC')
else:
	root = parser.get('DEFAULT', 'Root')
rootbasin = os.path.join(root,parser.get('DEFAULT', 'Rootbasin'))

ForcingStart = datetime.datetime.strptime(parser.get('DEFAULT','ForcingStart'),"%d/%m/%Y")  # Start of forcing

timeperiod = parser.get('DEFAULT','timeperiod')
if timeperiod == "monthly":
	monthly = 1
	dischargetss = 'discharge_monthavg.tss'
	frequen = 'MS'
else:
	monthly = 0
	dischargetss = 'discharge_daily.tss'
	frequen = 'd'



ParamRangesPath = os.path.join(rootbasin,parser.get('Path','ParamRanges'))
SubCatchmentPath = os.path.join(rootbasin,parser.get('Path','SubCatchmentPath'))
#SubCatchmentPath = parser.get('Path','SubCatchmentPath')
Qtss_csv = os.path.join(rootbasin,parser.get('ObservedData', 'Qtss'))
#Qtss_col = parser.get('ObservedData', 'Column')

modeltemplate = parser.get('Path','Templates')
ModelSettings_template = parser.get('Templates','ModelSettings')
RunModel_template = parser.get('Templates','RunModel')

use_multiprocessing = int(parser.get('DEAP','use_multiprocessing'))

try:
    pool_limit = int(parser.get('DEAP','pool_limit'))
except:
    pool_limit = 10000

ngen = int(parser.get('DEAP','ngen'))
mu = int(parser.get('DEAP','mu'))
lambda_ = int(parser.get('DEAP','lambda_'))
maximize =  parser.getboolean('DEAP','maximize')
if maximize: maxDeap = 1.0
else: maxDeap = -1.0


firstrun = parser.getboolean('Option', 'firstrun')   # using default run as first run
if firstrun:
	para_first = ast.literal_eval(parser.get("Option", "para_first"))
bestrun = parser.getboolean('Option', 'bestrun')

########################################################################
#   Preparation for calibration
########################################################################

path_subcatch = os.path.join(SubCatchmentPath)

# Load xml and .bat template files
runmodel = os.path.splitext(os.path.join(rootbasin,modeltemplate,RunModel_template))[0]

if platform == "win32":
	runmodel = runmodel +".bat"
else:
	runmodel = runmodel + ".sh"

f = open(runmodel,"r")
template_bat = f.read()
f.close()
f = open(os.path.join(rootbasin,modeltemplate,ModelSettings_template),"r")
template_xml = f.read()
f.close()

# Load parameter range file
ParamRanges = pandas.read_csv(ParamRangesPath,sep=",",index_col=0)
# ar = np.recfromcsv('example.csv'), my_data = genfromtxt('my_file.csv', delimiter=',')

# Load observed streamflow
streamflow_data = pandas.read_csv(Qtss_csv,sep=",", parse_dates=True, index_col=0)
#observed_streamflow = streamflow_data['lobith']
#observed_streamflow = streamflow_data[Qtss_col]
observed_streamflow = streamflow_data.values.astype(np.float32)
observed_streamflow[observed_streamflow<-9000]= np.nan


# first standard parameter set
# Snowmelt, crop KC, soil depth,pref. flow, arno beta, groundwater recession, runoff conc., routing, manning, No of run
# recalculated to a population setting
if firstrun:
	#para_first = [0.0035, 1.0, 1.0, 3.0, 1.0, 1.0, 1.0, 0.05, 1.]
	para_first2 = []
	for ii in range(0, len(ParamRanges - 1)):
		delta = float(ParamRanges.iloc[ii, 1]) - float(ParamRanges.iloc[ii, 0])
		if delta == 0:
			para_first2.append(0.)
		else:
			para_first2.append((para_first[ii] - float(ParamRanges.iloc[ii, 0])) / delta)

ii = 1



########################################################################
#   Function for running the model, returns objective function scores
########################################################################

def RunModel(Individual):

	# Convert scaled parameter values ranging from 0 to 1 to usncaled parameter values
	Parameters = [None] * len(ParamRanges)
	for ii in range(0,len(ParamRanges-1)):
		Parameters[ii] = Individual[ii]*(float(ParamRanges.iloc[ii,1])-float(ParamRanges.iloc[ii,0]))+float(ParamRanges.iloc[ii,0])

	# Note: The following code must be identical to the code near the end where the model is run
	# using the "best" parameter set. This code:
	# 1) Modifies the settings file containing the unscaled parameter values amongst other things
	# 2) Makes a .bat file to run the model
	# 3) Run the model and loads the simulated streamflow

	# Random number is appended to settings and .bat files to avoid simultaneous editing
	#run_rand_id = str(gen).zfill(2) + "_" + str(int(random.random()*100000000)).zfill(10)
	id =int(Individual[-1])
	run_rand_id = str(id//1000).zfill(2) + "_" + str(id%1000).zfill(3)

	directory_run = os.path.join(path_subcatch, run_rand_id)

	template_xml_new = template_xml
	template_xml_new = template_xml_new.replace("%root", root)
	for ii in range(0,len(ParamRanges)-1):
		template_xml_new = template_xml_new.replace("%"+ParamRanges.index[ii],str(Parameters[ii]))
	# replace output directory
	template_xml_new = template_xml_new.replace('%run_rand_id', directory_run)

	if os.path.isdir(directory_run):
		if os.path.exists(os.path.join(directory_run,dischargetss)):
			runmodel = False
		else:
			runmodel = True
			shutil.rmtree(directory_run)
	else: runmodel = True


	if runmodel:
		os.mkdir(directory_run)
		f = open(os.path.join(directory_run, ModelSettings_template[:-4] + '-Run' + run_rand_id + '.ini'), "w")
		f.write(template_xml_new)
		f.close()

		template_bat_new = template_bat
		template_bat_new = template_bat_new.replace('%run',ModelSettings_template[:-4]+'-Run'+run_rand_id+'.ini')
		runfile = os.path.join(directory_run,RunModel_template[:-4]+run_rand_id)
		if platform == "win32":
			runfile = runfile + ".bat"
			if use_multiprocessing == 0:
				print("multiprocess off")
				template_bat_new = template_bat_new.split()[0] + " " + template_bat_new.split()[1] + " " + template_bat_new.split()[2] + " -l\npause"
		else:
			runfile = runfile + ".sh"
			if use_multiprocessing == 0:
				template_bat_new = template_bat_new.split()[0] + " " + template_bat_new.split()[1] + " " + template_bat_new.split()[2] + " -l"
		f = open(runfile, "w")
		f.write(template_bat_new)
		f.close()

		currentdir = os.getcwd()
		os.chdir(directory_run)

		p = Popen(runfile, shell=True, stdout=PIPE, stderr=PIPE, bufsize=16*1024*1024)
		output, errors = p.communicate()
		f = open("log"+run_rand_id+".txt",'w')
		content = "OUTPUT:\n"+str(output)+"\nERRORS:\n"+str(errors)
		f.write(content)
		f.close()

		os.chdir(currentdir)


	Qsim_tss = os.path.join(directory_run,dischargetss)
	
	
	if os.path.isfile(Qsim_tss)==False:
		print("run_rand_id: "+str(run_rand_id)+" File: "+ Qsim_tss)
		raise Exception("No simulated streamflow found. Probably the model failed to start? Check the log files of the run!")
	simulated_streamflow = pandas.read_csv(Qsim_tss,sep=r"\s+",index_col=0,skiprows=4,header=None,skipinitialspace=True)
	simulated_streamflow[1][simulated_streamflow[1]==1e31] = np.nan

	if len(observed_streamflow) != len(simulated_streamflow[1]):
		raise Exception("run_rand_id: " + str(
			run_rand_id) + ": observed and simulated streamflow arrays have different number of elements (" + str(
			len(observed_streamflow)) + " and " + str(len(simulated_streamflow[1])) + " elements, respectively)")

	#Qobs = observed_streamflow[Cal_Start:Cal_End].values+0.001
	#Qobs = observed_streamflow
	q1 = simulated_streamflow[1].values+0.0001
	Qobs = observed_streamflow[~np.isnan(observed_streamflow)]
	#Qsim = q1[~np.isnan(observed_streamflow)]
	Qsim1=[]
	for i in range(observed_streamflow.shape[0]):
		if not(np.isnan(observed_streamflow[i])):
			Qsim1.append(q1[i])
	Qsim = np.asarray(Qsim1)



	# Compute objective function score

	KGE = hydroStats.KGE(s=Qsim,o=Qobs,warmup=WarmupDays)
	print("   run_rand_id: "+str(run_rand_id)+", KGE: "+"{0:.3f}".format(KGE))
	with open(os.path.join(path_subcatch,"runs_log.csv"), "a") as myfile:
		myfile.write(str(run_rand_id)+","+str(KGE)+"\n")
	return KGE, # If using just one objective function, put a comma at the end!!!

	"""
	COR = hydroStats.correlation(s=Qsim,o=Qobs,warmup=WarmupDays)
	print("   run_rand_id: "+str(run_rand_id)+", COR "+"{0:.3f}".format(COR))
	with open(os.path.join(path_subcatch,"runs_log.csv"), "a") as myfile:
		myfile.write(str(run_rand_id)+","+str(COR)+"\n")
	return COR, # If using just one objective function, put a comma at the end!!!


	NSE = hydroStats.NS(s=Qsim, o=Qobs, warmup=WarmupDays)
	print "   run_rand_id: " + str(run_rand_id) + ", NSE: " + "{0:.3f}".format(NSE)
	with open(os.path.join(path_subcatch, "runs_log.csv"), "a") as myfile:
		myfile.write(str(run_rand_id) + "," + str(NSE) + "\n")
	return NSE,  # If using just one objective function, put a comma at the end!!!
	"""

########################################################################
#   Perform calibration using the DEAP module
########################################################################

creator.create("FitnessMin", base.Fitness, weights=(maxDeap,))
creator.create("Individual", array.array, typecode='d', fitness=creator.FitnessMin)

toolbox = base.Toolbox()

# Attribute generator
toolbox.register("attr_float", random.uniform, 0, 1)

# Structure initializers
toolbox.register("Individual", tools.initRepeat, creator.Individual, toolbox.attr_float, len(ParamRanges))
toolbox.register("population", tools.initRepeat, list, toolbox.Individual)

def checkBounds(min, max):
	def decorator(func):
		def wrappper(*args, **kargs):
			offspring = func(*args, **kargs)
			for child in offspring:
				for i in range(len(child)):
					if child[i] > max:
						child[i] = max
					elif child[i] < min:
						child[i] = min
			return offspring
		return wrappper
	return decorator

toolbox.register("evaluate", RunModel)
toolbox.register("mate", tools.cxBlend, alpha=0.15)
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.3, indpb=0.3)
toolbox.register("select", tools.selNSGA2)

toolbox.decorate("mate", checkBounds(0, 1))
toolbox.decorate("mutate", checkBounds(0, 1))

if __name__ == "__main__":

	t = time.time()

	if use_multiprocessing==True:
		pool_size = multiprocessing.cpu_count() * 1
		print(pool_size, pool_limit)
		if pool_size > pool_limit: pool_size = pool_limit
		pool = multiprocessing.Pool(processes=pool_size)
		toolbox.register("map", pool.map)
		print(pool_size)
	

	# For someone reason, if sum of cxpb and mutpb is not one, a lot less Pareto optimal solutions are produced
	cxpb = 0.9
	mutpb = 0.1

	startlater = False
	checkpoint = os.path.join(SubCatchmentPath,"checkpoint.pkl")
	if os.path.exists(os.path.join(checkpoint)):
		with open(checkpoint, "rb" ) as cp_file:
			cp = pickle.load(cp_file)
			population = cp["population"]
			start_gen = cp["generation"]
			random.setstate(cp["rndstate"])
			if start_gen > 0:
				offspring = cp["offspring"]
				halloffame =  cp["halloffame"]
				startlater = True
				gen = start_gen

	else:
		population = toolbox.population(n=mu)
		# Numbering of runs
		for ii in range(mu):
			population[ii][-1]= float(gen * 1000 + ii+1)

		#first run parameter set:
		if firstrun:
			for ii in range(len(population[0])):
				population[0][ii] = para_first2[ii]
			population[0][-1] = 0.


	effmax = np.zeros(shape=(ngen+1,1))*np.NaN
	effmin = np.zeros(shape=(ngen+1,1))*np.NaN
	effavg = np.zeros(shape=(ngen+1,1))*np.NaN
	effstd = np.zeros(shape=(ngen+1,1))*np.NaN
	if startlater == False:
		halloffame = tools.ParetoFront()

		# saving population
		cp = dict(population=population, generation=gen, rndstate=random.getstate())
		with open(checkpoint, "wb") as cp_file:
			pickle.dump(cp, cp_file)
		cp_file.close()


		# Evaluate the individuals with an invalid fitness
		invalid_ind = [ind for ind in population if not ind.fitness.valid]
		fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
		for ind, fit in zip(invalid_ind, fitnesses):
			ind.fitness.values = fit

		halloffame.update(population)

		# Loop through the different objective functions and calculate some statistics
		# from the Pareto optimal population

		for ii in range(1):
			effmax[0,ii] = np.amax([halloffame[x].fitness.values[ii] for x in range(len(halloffame))])
			effmin[0,ii] = np.amin([halloffame[x].fitness.values[ii] for x in range(len(halloffame))])
			effavg[0,ii] = np.average([halloffame[x].fitness.values[ii] for x in range(len(halloffame))])
			effstd[0,ii] = np.std([halloffame[x].fitness.values[ii] for x in range(len(halloffame))])
		gen = 0
		print(">> gen: "+str(gen)+", effmax_KGE: "+"{0:.3f}".format(effmax[gen,0]))
		gen = 1



	# Begin the generational process
	conditions = {"ngen" : False, "StallFit" : False}
	while not any(conditions.values()):
		if startlater == False:
			# Vary the population
			offspring = algorithms.varOr(population, toolbox, lambda_, cxpb, mutpb)

			# put in the number of run
			for ii in range(lambda_):
				offspring[ii][-1] = float(gen * 1000 + ii + 1)

		# saving population
		cp = dict(population=population, generation=gen, rndstate=random.getstate(), offspring=offspring, halloffame=halloffame)
		with open(checkpoint, "wb") as cp_file:
			pickle.dump(cp, cp_file)
		cp_file.close()
		startlater = False



		# Evaluate the individuals with an invalid fitness
		invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
		fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
		for ind, fit in zip(invalid_ind, fitnesses):
			ind.fitness.values = fit

		# Update the hall of fame with the generated individuals
		if halloffame is not None:
			halloffame.update(offspring)

		# Select the next generation population
		population[:] = toolbox.select(population + offspring, mu)

		# put in the number of run
		#for ii in xrange(mu):
		#	population[ii][-1] = float(gen * 1000 + ii + 1)

		# Loop through the different objective functions and calculate some statistics
		# from the Pareto optimal population
		for ii in range(1):
			effmax[gen,ii] = np.amax([halloffame[x].fitness.values[ii] for x in range(len(halloffame))])
			effmin[gen,ii] = np.amin([halloffame[x].fitness.values[ii] for x in range(len(halloffame))])
			effavg[gen,ii] = np.average([halloffame[x].fitness.values[ii] for x in range(len(halloffame))])
			effstd[gen,ii] = np.std([halloffame[x].fitness.values[ii] for x in range(len(halloffame))])
		print(">> gen: "+str(gen)+", effmax_KGE: "+"{0:.3f}".format(effmax[gen,0]))

		# Terminate the optimization after ngen generations
		if gen >= ngen:
			print(">> Termination criterion ngen fulfilled.")
			conditions["ngen"] = True

		gen += 1
		# Copied and modified from algorithms.py eaMuPlusLambda until here




	# Finito
	if use_multiprocessing == True:
		pool.close()
	elapsed = time.time() - t
	print(">> Time elapsed: "+"{0:.2f}".format(elapsed)+" s")


	########################################################################
	#   Save calibration results
	########################################################################

	# Save history of the change in objective function scores during calibration to csv file
	print(">> Saving optimization history (front_history.csv)")
	front_history = pandas.DataFrame({'gen':list(range(gen)),
									  'effmax_R':effmax[:,0],
									  'effmin_R':effmin[:,0],
									  'effstd_R':effstd[:,0],
									  'effavg_R':effavg[:,0],
									  })
	front_history.to_csv(os.path.join(path_subcatch,"front_history.csv"),',')
	# as numpy  numpy.asarray  ; numpy.savetxt("foo.csv", a, delimiter=","); a.tofile('foo.csv',sep=',',format='%10.5f')

	# Compute overall efficiency scores from the objective function scores for the
	# solutions in the Pareto optimal front
	# The overall efficiency reflects the proximity to R = 1, NSlog = 1, and B = 0 %
	front = np.array([ind.fitness.values for ind in halloffame])
	effover = 1 - np.sqrt((1-front[:,0]) ** 2)
	best = np.argmax(effover)

	# Convert the scaled parameter values of halloffame ranging from 0 to 1 to unscaled parameter values
	paramvals = np.zeros(shape=(len(halloffame),len(halloffame[0])))
	paramvals[:] = np.NaN
	for kk in range(len(halloffame)):
		for ii in range(len(ParamRanges)):
			paramvals[kk][ii] = halloffame[kk][ii]*(float(ParamRanges.iloc[ii,1])-float(ParamRanges.iloc[ii,0]))+float(ParamRanges.iloc[ii,0])

	# Save Pareto optimal solutions to csv file
	# The table is sorted by overall efficiency score
	print(">> Saving Pareto optimal solutions (pareto_front.csv)")
	ind = np.argsort(effover)[::-1]
	pareto_front = pandas.DataFrame({'effover':effover[ind],'R':front[ind,0]})
	for ii in range(len(ParamRanges)):
		pareto_front["param_"+str(ii).zfill(2)+"_"+ParamRanges.index[ii]] = paramvals[ind,ii]
	pareto_front.to_csv(os.path.join(path_subcatch,"pareto_front.csv"),',')

	# Select the "best" parameter set and run Model for the entire forcing period
	Parameters = paramvals[best,:]


	if bestrun:
		print(">> Running Model using the \"best\" parameter set")
		# Note: The following code must be identical to the code near the end where Model is run
		# using the "best" parameter set. This code:
		# 1) Modifies the settings file containing the unscaled parameter values amongst other things
		# 2) Makes a .bat file to run Model
		# 3) Runs Model and loads the simulated streamflow
		# Random number is appended to settings and .bat files to avoid simultaneous editing

		run_rand_id = str(gen).zfill(2) + "_best"
		template_xml_new = template_xml
		directory_run = os.path.join(path_subcatch, run_rand_id)
		template_xml_new = template_xml_new.replace("%root", root)
		for ii in range(0,len(ParamRanges)):
			template_xml_new = template_xml_new.replace("%"+ParamRanges.index[ii],str(Parameters[ii]))
		template_xml_new = template_xml_new.replace('%run_rand_id', directory_run)

		os.mkdir(directory_run)

		#template_xml_new = template_xml_new.replace('%InitModel',"1")
		f = open(os.path.join(directory_run,ModelSettings_template[:-4]+'-Run'+run_rand_id+'.ini'), "w")
		f.write(template_xml_new)
		f.close()
		template_bat_new = template_bat
		template_bat_new = template_bat_new.replace('%run',ModelSettings_template[:-4]+'-Run'+run_rand_id+'.ini')

		runfile = os.path.join(directory_run, RunModel_template[:-4] + run_rand_id)
		if platform == "win32":
			runfile = runfile + ".bat"
		else:
			runfile = runfile + ".sh"
		f = open(runfile, "w")
		f.write(template_bat_new)
		f.close()

		currentdir = os.getcwd()
		os.chdir(directory_run)

		p = Popen(runfile, shell=True, stdout=PIPE, stderr=PIPE, bufsize=16*1024*1024)
		output, errors = p.communicate()
		f = open("log"+run_rand_id+".txt",'w')
		content = "OUTPUT:\n"+str(output)+"\nERRORS:\n"+str(errors)
		f.write(content)
		f.close()
		os.chdir(currentdir)

		Qsim_tss = os.path.join(directory_run,dischargetss)
		
		simulated_streamflow = pandas.read_table(Qsim_tss,sep=r"\s+",index_col=0,skiprows=4,header=None,skipinitialspace=True)
		simulated_streamflow[1][simulated_streamflow[1]==1e31] = np.nan
		Qsim = simulated_streamflow[1].values

		# Save simulated streamflow to disk
		print(">> Saving \"best\" simulated streamflow (streamflow_simulated_best.csv)")
		Qsim = pandas.DataFrame(data=Qsim, index=pandas.date_range(ForcingStart, periods=len(Qsim), freq=frequen))
		Qsim.to_csv(os.path.join(path_subcatch,"streamflow_simulated_best.csv"),',',header="")
		try: os.remove(os.path.join(path_subcatch,"out",'streamflow_simulated_best.tss'))
		except: pass
		#os.rename(Qsim_tss, os.path.join(path_subcatch,"out",'streamflow_simulated_best.tss'))

	"""
	# Delete all .xml, .bat, .tmp, and .txt files created for the runs
	for filename in glob.glob(os.path.join(path_subcatch,"*.xml")):
		os.remove(filename)
	for filename in glob.glob(os.path.join(path_subcatch,"*.bat")):
		os.remove(filename)
	for filename in glob.glob(os.path.join(path_subcatch,"*.tmp")):
		os.remove(filename)
	for filename in glob.glob(os.path.join(path_subcatch,"*.txt")):
		os.remove(filename)
	"""

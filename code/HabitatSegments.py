#HabitatSegments.py
#written by Sam Roy, 4/19/19
#This script uses the NHDPlus_v2 dataset to identify downstream neighboring features, useful for determining upstream resources
#Designed to calculate the amount of American Shad habitat segmented between features: for example, between dams, or between a coastal outlet and upstream dams

#Datasets used:
#NHD Plus, version 2, east coast HUCs (NE,MA,SA)
    #NHDPlusflowline.shp
    #NHDPlusCatchment.shp
    #NHDPlusAttributes.dbf
    #NHDPlusEROMExtension.dbf
#Dam geodatabase provided by TNC:
    #SEACAP for southern atlantic states
    #Northeast Aquatic Connectivity geodatabase for north atlantic states

#useful definitions
#COMID: unique identification number given to each flowline and associated catchment
#FEATUREID: COMID for catchments

#import necessary libraries
import numpy as np
import os
import sys
#debug
import pdb

#user input args
place=sys.argv[1]
width=float(sys.argv[2])
slope=float(sys.argv[3])

#declare directories/files
basedir=r"D:/FoD/data/"
savedir=r"D:/FoD/data/joe/habitatSegments/"
#f_dams=basedir + r"joe/damCOMIDtest%s.csv" %place #file containing dam-flowline/catchment linked COMIDs. These are actually linked to catchments, not flowlines, because of occasional offset in boundaries of both. More important to match dam to its containing catchment
#f_outlets=basedir + r"joe/outletCOMIDtest%s.csv" %place #file containing dam-flowline/catchment linked COMIDs. These are actually linked to catchments, not flowlines, because of occasional offset in boundaries of both. More important to match dam to its containing catchment
#f_chandims=basedir + r"joe/CHANDIMtest%s.csv" % place #these data come from the EROMextension and simple geomorph rules for bankfull width
f_lines=basedir + r"joe/flownets/COMIDflownet%s.csv" % place
f_hab = basedir + r"joe/habitatOut/Habitat%s_wd%sm_slp%s.csv" % (place, width, slope)

#import data
ctchHome=np.loadtxt(f_hab,delimiter=',',skiprows=1,usecols=(2))
ctchDown=np.array([0] * ctchHome.size)
IDs=np.genfromtxt(f_hab,delimiter=',',skip_header=1,usecols=(0),dtype='str')
type=np.genfromtxt(f_hab,delimiter=',',skip_header=1,usecols=(1),dtype='str')
habUp=np.loadtxt(f_hab,delimiter=',',skiprows=1,usecols=(3))
habSeg=np.array([0] * habUp.size)
flow=np.loadtxt(f_lines,delimiter=',',skiprows=1,usecols=(0,3))

#optional input args: array of decisions user can provide for each dam
if len(sys.argv)>4:
    f_decisions = sys.argv[4]
    decisions = np.genfromtxt(f_decisions,delimiter=',',dtype='str')
else:
    decisions = ['keep'] * type[type == 'dam'].size
    decisions.extend(['outlet'] * type[type == 'outlet'].size)
    decisions=np.array(decisions)

#optional input args: array of passage probabilities user can provide for each dam
if len(sys.argv)>5:
    f_passage = sys.argv[5]
    passage = np.loadtxt(f_passage,delimiter=',')
else:
    passage = [0.] * type[type == 'dam'].size #assume dams have 0% passage unless stated otherwise by user
    passage.extend([1.] * type[type == 'outlet'].size) #outlets must have passage = 1 (100%)
    passage = np.array(passage)
    passageComp = passage

#write-out file
f = open(basedir + r"joe/habitatSegments/Habitat%s_wd%sm_slp%s.csv" % (place, width, slope), "w")
f.write('UNIQUE_ID, type, catchmentHome, catchmentDown, decision, habUp_sqkm, habSegment_sqkm, passage\n')

#loop through dams, retieve full list of upstream flowlines/catchments saved to txt
for i in xrange(ctchHome[type == 'dam'].size):
    print '%i of %i' % (i+1, len(ctchHome)) #show them you're working on it
    #go look for downstream neighbor
    look=1
    upTemp=ctchHome[i]
    while look: #break this while loop if there are no more upstream flowlines
        downTemp = np.unique(flow[flow[:,0]==upTemp,1]) #must be unique as multiple dams could reside in same home catchment
        if i == 28: #debugging a forever loop case. My current plan is to use field divergence from NHDPlusAttributes/PlusFlowlineVAA to select main reach, ignore sub-reach. Good enough for calcs now, where passage is always 0 for dams.
            pdb.set_trace()
        if np.any(np.isin(downTemp,ctchHome)):
            downTemp=downTemp[np.isin(downTemp,ctchHome)]#this is a hack, avoids islands where a dam is found sooner on one side versus the other. Ignores the other reach.
            try:
                passageComp[i] = passageComp[i] * np.unique(passage[ctchHome == downTemp])#can hae multiple dams at downstream Catchment, for now remove by unique, but when we play with different passage rates/decisions, etc, will need a comprehensive fix
            except:
                pdb.set_trace()
            if ctchDown[i] == 0 and np.any(np.isin(decisions[np.isin(ctchHome,downTemp)], np.array(['keep','improve passage','outlet']))):
                ctchDown[i] = downTemp
            if passageComp[i] == 0 or np.isin(decisions[np.isin(ctchHome,downTemp)], np.array(['outlet'])):
                look=0
        upTemp=downTemp

for i in xrange(ctchHome.size):
    habSeg[ctchHome == ctchDown[i]]=habUp[ctchHome == ctchDown[i]]-habUp[i]
    f.write('%s,%s,%s,%s,%s,%s,%s,%s\n' % (IDs[i], type[i], ctchHome[i], ctchDown[i], decision[i], habUp[i], habSeg[i], passageComp[i]))

f.close()

#damDelineateByFlowlines.py
#written by Sam Roy, 4/15/19
#This script uses the NHDPlus_v2 dataset to delineate dam upstream watersheds, useful for determining upstream resources
#Designed specifically to estimate amount of American Shad habitat upstream of dams along the entire east coast of the US. Project headed by Joe Zydlewski

#Notes on previous versions, improvements
#This approach replaces a previous version that used NHD flow direction rasters to delineate each dam watershed entirely. That takes significantly more time.
#This approach also importantly does not require the use of arcpy, there is no need for an ARC license :)

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

#import necessary libraries
import numpy as np
import os
import sys

#user input args
place=sys.argv[1]
width=float(sys.argv[2])

#declare directories/files
basedir=r"D:/FoD/data/"
loadir=r"D:/FoD/data/joe/watershedFlowlineLists/"
f_ctch=basedir + r"joe/damCOMIDtest%s.csv" %place #file containing dam-flowline/catchment linked COMIDs. These are actually linked to catchments, not flowlines, because of occasional offset in boundaries of both. More important to match dam to its containing catchment
f_chandims=basedir + r"joe/CHANDIMtest%s.csv" % place #these data come from the EROMextension and simple geomorph rules for bankfull width
#f_lines=basedir + r"/NHD/NHDPlusSA/NHDPlus03S/NHDPlusAttributes/COMIDflownet.csv" #flow network file identifies immediate downstream neighbor of each flowline/catchment

#import data
home_ctch=np.loadtxt(f_ctch,delimiter=',',skiprows=1,usecols=(1))
damIDs=np.genfromtxt(f_ctch,delimiter=',',skip_header=1,usecols=(0),dtype='str')
chandims=np.loadtxt(f_chandims,delimiter=',',skiprows=1,usecols=(0,1,4,5))

#Declare empty habitat array
#habitat=np.zeros((home_ctch.size,3))

#write-out file
f = open(basedir + r"joe/Habitat%s_width%sm.csv" % (place, width), "w")

#loop through dams, retieve full list of upstream flowlines/catchments saved to txt
for i in xrange(home_ctch.size):
    #if not os.path.isfile(savedir + 'dam_%i_wfll.csv' % int(dams[i])):
    print 'dam %i of %i' % (i, len(home_ctch)) #show them you're working on it
    #load flowlist, read FEATUREID/CatchCOMID from row[1], that is the next upstream flowline. Select it, then use it to select the correct split line section
    f_flowlist = loadir + r'NHDPlus%s/dam_%s_wfll.csv' % (place,int(home_ctch[i]))
    flist=np.loadtxt(f_flowlist,delimiter=',')
    #retrieve channel dimension data based on COMID/FEATUREID match:
    dims=chandims[np.isin(chandims[:,0],flist),:]
    hab=np.sum(dims[dims[:,3]>=width,1]*(dims[dims[:,3]>=width,3]/1e3))
    f.write("%s, %s, %s\n" % (damIDs[i], home_ctch[i], hab))
f.close()

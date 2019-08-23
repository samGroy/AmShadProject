#damDelineateByFlowlines.py
#written by Sam Roy, 4/15/19
#This script uses the NHDPlus_v2 dataset to delineate dam upstream watersheds, useful for determining upstream resources
#Designed specifically to estimate amount of American Shad habitat upstream of dams along the entire east coast of the US. Project headed by AmShad Zydlewski

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
#debug
#import pdb

#user input args. If none given, provide default values. Zero values mean no threshold requested.
if len(sys.argv)>1:
    place=sys.argv[1]
    if place.lower() in 'all':
        place=''
else:
    print('No search region specified. default region: ALL')
    place=''
if len(sys.argv)>2:
    width=float(sys.argv[2])
else:
    print('no width threshold selected (0)')
    width=0.
if len(sys.argv)>3:
    slope=float(sys.argv[3])
else:
    print('no slope threshold selected (0)')
    slope=9999.
if len(sys.argv)>4:
    tidal=int(sys.argv[4])
else:
    print('no tidal threshold selected (0)')
    tidal=0

#declare directories/files
savedir = r"./"
f_dams = r"./data/dams.csv" #file containing dam-flowline/catchment linked COMIDs. These are actually linked to catchments, not flowlines, because of occasional offset in boundaries of both. More important to match dam to its containing catchment
f_outlets = r"./data/outlets.csv" #file containing dam-flowline/catchment linked COMIDs. These are actually linked to catchments, not flowlines, because of occasional offset in boundaries of both. More important to match dam to its containing catchment
f_chandat = r"./data/flowdata.csv" #additional data, including tidal flag
f_lines = r"./data/flownets.csv" #downstream neighbor list
#import data
#LOAD dams and outlets COMIDS
dams=np.loadtxt(f_dams,delimiter=',',skiprows=1,usecols=(1))
outs=np.loadtxt(f_outlets,delimiter=',',skiprows=1,usecols=(1))
dams_outs=np.concatenate((outs,dams))
#dams_outs=outs
#LOAD dams and outlets unique IDs
IDs2=np.genfromtxt(f_dams,delimiter=',',skip_header=1,usecols=(0),dtype='str')
IDs1=np.genfromtxt(f_outlets,delimiter=',',skip_header=1,usecols=(0),dtype='str')
IDs=np.concatenate((IDs1,IDs2))
#IDs=IDs1
#LOAD dams and IDs TERMCODEs and location data
locations2=np.genfromtxt(f_dams,delimiter=',',skip_header=1,usecols=(3,4,5,6,7,9,10,11),dtype='str')
locations1=np.genfromtxt(f_outlets,delimiter=',',skip_header=1,usecols=(3,4,5,6,7,9,10,11),dtype='str')
locations=np.concatenate((locations1,locations2))
#locations=locations1
#LOAD dams and outlets type
type2=np.genfromtxt(f_dams,delimiter=',',skip_header=1,usecols=(2),dtype='str')
type1=np.genfromtxt(f_outlets,delimiter=',',skip_header=1,usecols=(2),dtype='str')
type=np.concatenate((type1,type2))
#type=type1
#chandat=np.loadtxt(f_chandat,delimiter=',',skiprows=1,usecols=(0,1,4,5))
#LOAD channel data
chandat = np.loadtxt(f_chandat,delimiter=',',skiprows=1,usecols=(0,1,2,3,4,5))
#chandat = np.loadtxt(f_chandat,delimiter=',',skiprows=1,usecols=(0,1,3,4,2))
#LOAD channel TERMCODEs
termcode = np.genfromtxt(f_chandat,dtype='str',delimiter=',',skip_header=1,usecols=(6))
#Keep only unique channel COMIDs
#chandat,udx = np.unique(chandat[:,0],return_index=True)
#chandat = chandat[udx,:]
#termcode = termcode[udx]
#lOAD flow network (from-to list)
flow=np.loadtxt(f_lines,delimiter=',',skiprows=1,usecols=(0,1))

#keep COMIDS of everything within place requested by user
#Constraints:
#TERMCODE/location
#channel width
#channel slope
#tidal: currently ignored because the binary value is not sensitive to freshwater tidal regions suitable for habitat
comids=chandat[(np.char.find(termcode,place)==0) & (np.greater_equal(chandat[:,3],width)) & (np.less_equal(chandat[:,5],slope)),0]
#keep only flowlines/features that match the comids list selected by constraints
IDs = IDs[np.isin(dams_outs,comids)]
type = type[np.isin(dams_outs,comids)]
locations = locations[np.isin(dams_outs,comids),:]
termcode = termcode[np.isin(chandat[:,0],comids)]
flow = flow[np.isin(flow[:,0],comids)+np.isin(flow[:,1],comids)>0,:]
dams_outs = dams_outs[np.isin(dams_outs,comids)]
chandat = chandat[np.isin(chandat[:,0],comids)]

#temp maxslp to calculate maximum slope to flowline...
#maxslp = chandat[:,2]
#print chandat[:,0].size
#print maxslp.size
#optional input args: array of decision user can provide for each dam
#if len(sys.argv)>5:
#    f_decision = sys.argv[5]
#    decision = np.genfromtxt(f_decision,delimiter=',',dtype='str')
#else:
#    decision = ['keep'] * type[type == 'dam'].size
#    decision.extend(['outlet'] * type[type == 'outlet'].size)
#    decision=np.array(decision)

#optional input args: array of passage probabilities user can provide for each dam
passage = [1.] * type[type == 'outlet'].size #assume dams have 0% passage unless stated otherwise by user
passage.extend([0.] * type[type == 'dam'].size) #outlets must have passage = 1 (100%)
passage = np.array(passage)
#passage[decision=='remove'] = 1.
passageComp = passage
if len(sys.argv)>6:
    f_passage = sys.argv[6]
    plist = np.loadtxt(f_passage,delimiter=',',usecols=[0,1])
    passage[1,np.where(np.isin(IDs,plist[:,0]))]=plist[1,np.where(np.isin(plist[:,0],IDs))]

#declare the arrays, other variables
habup = np.array([0.] * dams_outs.size)
habseg = np.array([0.] * dams_outs.size)
damOrder = np.array([0] * dams_outs.size)

#loop through dams, retieve full list of upstream flowlines/catchments saved to txt
for i in xrange(dams_outs.size):
    #if not os.path.isfile(savedir + 'dam_%i_wfll.csv' % int(dams[i])):
    print '%s, %i of %i' % (type[i], i+1, len(dams_outs)) #show them you're working on it
    current=np.array([dams_outs[i]]) #declare the current search location as dams_outs[i]
    currentseg=current #separate declaraton for segment area calc, separate from total upstream area calc
    #current=np.array([6290171])
    watershed=[] #declare the list of upstream COMIDs
    #maxslptemp=chandat[np.isin(chandat[:,0],current),2] #temp addition max slope...
    #import pdb
    #pdb.set_trace()
    #check if there are double features on one flowline, and fix the dam count accordingly
    #if i == 1:#if IDs[i] in 'ME_ME00148' or IDs[i] in 'ME_ME00582':
    #    import pdb; pdb.set_trace()
    #if type[i] not in 'dam':
    #    continue
    if type[i] in 'dam' and np.sum(np.isin(dams_outs,dams_outs[i]))>1: #if it's a dam, and there's more than one feature at its flowline
        if np.where(IDs[np.isin(dams_outs,dams_outs[i])]==IDs[i])[0][0]>0: #if it's not the first feature in the list of features in that flowline
            if np.sum(np.isin(damOrder[np.isin(dams_outs,dams_outs[i])],damOrder[i]))>1:
    #            import pdb; pdb.set_trace()
                damOrder[i] +=1
    #(np.unique(dams_outs[np.isin(dams_outs,current)]).size < dams_outs[np.isin(dams_outs,current)].size and
    #np.sum(np.diff(damOrder[np.where((np.isin(dams_outs,current)) & (np.char.find(type,'dam')==0))]))==0):
        #for j in xrange(1,dams_outs[np.isin(dams_outs,current)].size):
        #    damOrder[np.where((np.isin(dams_outs,current)) & (np.char.find(type,'dam')==0) & np.isin(IDs,IDs[(np.isin(dams_outs,current)) & (np.char.find(type,'dam')==0)][j]))] += 1

    while np.sum(current)>0: #break this while loop if there are no more upstream flowlines
        watershed=np.concatenate([watershed,current])
        up=np.array([]) #reset upstream population
        upseg=np.array([])
        upgrp=np.array([])
        #upmaxslptemp=np.array([])
        #sum habitat, habitat segment
        if tidal:
            #pdb.set_trace()
            habup[i] = habup[i] + np.sum(chandat[(np.isin(chandat[:,0],current)) & (chandat[:,4]==0),1]*(chandat[(np.isin(chandat[:,0],current)) & (chandat[:,4]==0),3]/1e3))
            habseg[i] = habseg[i] + np.sum(chandat[(np.isin(chandat[:,0],currentseg)) & (chandat[:,4]==0),1]*(chandat[(np.isin(chandat[:,0],currentseg)) & (chandat[:,4]==0),3]/1e3))
        else:
            habup[i] = habup[i] + np.sum(chandat[np.isin(chandat[:,0],current),1]*(chandat[np.isin(chandat[:,0],current),3]/1e3))
            habseg[i] = habseg[i] + np.sum(chandat[np.isin(chandat[:,0],currentseg),1]*(chandat[np.isin(chandat[:,0],currentseg),3]/1e3))
        #pdb.set_trace()
        for j in xrange(current.size): #loop through list of dams that were upstream
            #find match of current COMID in 'TO' column of flow, retrieve COMID in 'FROM' column. We are looking upstream for COMIDS.
            #print '   upstream number %i' % j
            #import pdb
            #pdb.set_trace()
            upgrp = flow[flow[:,1]==current[j],0]
            up=np.concatenate([up,upgrp])
            #if np.isin(1736696,up):
            #    import pdb; pdb.set_trace()
            #upmaxslptemp=np.concatenate([upmaxslptemp,[maxslptemp[j]] * (len(flow[flow[:,1]==current[j],0]))]) #temp addition max slope...
            #print upmaxslptemp
            if np.isin(current[j],currentseg):
                upseg=np.concatenate([upseg,flow[flow[:,1]==current[j],0]])
            #do max slope here
            #dslp = maxslp[np.isin(chandat[:,0],current[j])]
            #for k in xrange(upgrp.size):
            #    if upgrp[k] not in watershed:
            #        uslp = maxslp[np.isin(chandat[:,0],upgrp[k])]
            #        if dslp>uslp:
            #            maxslp[np.isin(chandat[:,0],upgrp[k])] = dslp

        #cprev=current
        #current, udx = np.unique(up[up>0],return_index=True) #take the unique list because islands can cause upstream merging, duplicate COMIDs that persist and compound with the total number of islands all the way to headwaters (FROMMCOMID=0)
        current = np.unique(up[up>0]) #take the unique list because islands can cause upstream merging, duplicate COMIDs that persist and compound with the total number of islands all the way to headwaters (FROMMCOMID=0)
        #try:
        #    maxslptemp = upmaxslptemp[udx]
        #except:
        #    import pdb; pdb.set_trace()
        upseg=upseg[np.isin(upseg,dams_outs,invert=True)] #for the feature's segment, remove flowlines that intersect upstream dams
        currentseg=np.unique(upseg[upseg>0])
        #maxslptemp = maxslptemp[np.isin(current,watershed,invert=True)]
        current = current[np.isin(current,watershed,invert=True)]#third way to remove duplicates...if an island has unequal number of reaches on either side the unique comparison will be offset. So, check if the offending COMID(s) already exist in watershed
        currentseg=currentseg[np.isin(currentseg,watershed,invert=True)]
        #maxslptemp = maxslptemp[np.isin(current,chandat[:,0])]
        current=current[np.isin(current,chandat[:,0])]#get rid of "coastline" dams_outs that somehow infiltrated the list
        currentseg=currentseg[np.isin(currentseg,chandat[:,0])]
        #look for dams on this flowline
        #compound passage for upstream dams_outs, if they are found in this search round
        if np.any(np.isin(dams_outs,current)):
            #if np.isin('ME_ME00200',IDs[np.isin(dams_outs,current)]):
            #    import pdb; pdb.set_trace()
            current_passageComp=passageComp[i]
            passageComp[(np.isin(dams_outs,current)) & (np.char.find(type,'dam')==0)] = passageComp[(np.isin(dams_outs,current)) & (np.char.find(type,'dam')==0)] * passage[i]
            #passageComp[(np.isin(dams_outs,current)) & (np.isin(IDs[np.isin(dams_outs,current,invert=True)],IDs[i]))] = passageComp[(np.isin(dams_outs,current)) & (np.isin(IDs[np.isin(dams_outs,current,invert=True)],IDs[i]))] * passage[i]
            passageComp[i] = current_passageComp
            damOrder[(np.isin(dams_outs,current)) & (np.char.find(type,'dam')==0)] += 1
        #temp addition to report max slope to flowline
        #curslp = chandat[np.isin(chandat[:,0],current),2]
        #if np.where(curslp>maxslptemp)[0].any():
        #    import pdb; pdb.set_trace()
        #if curslp.size>maxslptemp.size:
            #import pdb; pdb.set_trace()
        #    print "jumped"
        #    continue
            #import pdb; pdb.set_trace()
            #maxslptemp=np.concatenate(maxslptemp,curslp[curslp.size-1])
        #if current.size>0:
        #    maxslptemp[np.where(curslp>maxslptemp)]=curslp[np.where(curslp>maxslptemp)]
            #print maxslptemp
        #    icom=np.where(np.isin(chandat[:,0],current))
        #    for r in xrange(len(icom[0])):
        #        try:
        #            if maxslptemp[r] > maxslp[icom[0][r]]:
        #                maxslp[icom[0][r]] = maxslptemp[r]

        #        except:
        #            import pdb; pdb.set_trace()

        #if slope: #remove flow lines with slopes exceeding threshold
        #    #import pdb; pdb.set_trace()
        #    curslp=chandat[np.isin(chandat[:,0],current),2]
        #    current=current[curslp<=slope]
        #    curslpseg=chandat[np.isin(chandat[:,0],currentseg),2]
        #    currentseg=currentseg[curslpseg<=slope]
        #if width:
        #    #pdb.set_trace()
        #    curwd=chandat[np.isin(chandat[:,0],current),3]
        #    try:
        #        current=current[curwd>=width]
        #    except:
        #        pdb.set_trace()
        #    curwdseg=chandat[np.isin(chandat[:,0],currentseg),3]
        #    currentseg=currentseg[curwdseg>=width]
        #print '    there are %i upstream reaches' % watershed.size #this could become a very big number
    #np.savetxt(savedir + 'dam_%i_wfll.csv' % int(dams_outs[i]), watershed,fmt='%i', delimiter=',')
    #np.savetxt(savedir + 'dam_6290171_wfll.csv', watershed,fmt='%i', delimiter=',')

#Next, write results to a file on disk. Print them in descending order based on functional habitat amounts.
idx=np.argsort(habup)[::-1]

#write-out file
f = open(savedir + r"Habitat%s_wd%sm_slp%s_tidal%i.csv" % (place, width, slope*100., tidal), "w")
#f.write('Location: %s\n' % place)
#f.write('%.2f,Total functional habitat\n' % np.sum(habseg*passageComp))
#f.write('%.2f,Maximum habitat\n' % np.sum(habseg))
#f.write('%.2f,Channel width threshold\n' % width)
#f.write('%s,Slope threshold\n' % slope)
#f.write('%i,Omit tidal reaches\n' % tidal)
f.write('UNIQUE_ID,type,catchmentID,habitat_sqkm,habitatSegment_sqkm,functional_habitatSegment_sqkm,PassageToHabitat,TERMCODE,terminal_name_huc10,terminal_name_huc8,terminal_name_huc6,terminal_name_huc4,dam_name,latitude,longitude,dam_order\n')
for i in idx:
    f.write('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n'
        % (IDs[i], type[i], dams_outs[i], habup[i], habseg[i], habseg[i]*passageComp[i], passageComp[i],
        locations[i,0],locations[i,1],locations[i,2],locations[i,3],locations[i,4],locations[i,5],locations[i,6],locations[i,7],damOrder[i]))
f.close()

#temp macxslope write out...
#f2 = open(savedir + "max_slope_to_flowline%s.csv" % place, "w")
#f2.write('COMID,maxSlope\n')
#for j in xrange(chandat[:,0].size):
#    f2.write('%s,%s\n' % (chandat[j,0], maxslp[j]))
#f2.close()

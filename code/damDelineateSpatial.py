import numpy as np
import arcpy
from arcpy import env
import sys

#debug library
import pdb

#user input args
place=sys.argv[1]
makespatial=int(sys.argv[2])
wshdtrig=int(sys.argv[3])

basedir=r"D:/FoD/data/"
loadir=basedir + r"joe/watershedFlowlineLists/"
scratch = "D:/FoD/scratch/"
savedir_lines = basedir + r"joe/watershedFlowlines/"
savedir_polys = basedir + r"joe/watershedPolys/"
#f_flowlist=loadir + r"dam_4512772_wfll.csv" #file containing dam-flowline/catchment linked COMIDs. These are actually linked to catchments, not flowlines, because of occasional offset in boundaries of both. More important to match dam to its containing catchment

#flist=np.loadtxt(f_flowlist,delimiter=',')

env.workspace = scratch
arcpy.env.overwriteOutput=True
arcpy.CheckOutExtension('Spatial')

#seek options
if place == 'NE':
    nbr = '01'
    fnbr1 = '01a'
    fnbr2 = 0
elif place == 'MA':
    nbr = '02'
    fnbr1 = '02a'
    fnbr2 = '02b'
elif place == 'SA1':
    nbr = '03N'
    fnbr1 = '03a'
    fnbr2 = '03b'
elif place == 'SA2':
    nbr = '03S'
    fnbr1 = '03c'
    fnbr2 = '03d'

#import pdb
#pdb.set_trace()
damFile = basedir + r"joe/dams/dams_%s.shp" % place
dams = arcpy.MakeFeatureLayer_management(damFile)
flinesFile = basedir + r"NHD/NHDPlus%s/NHDPlus%s/NHDSnapshot/Hydrography/NHDFlowline.shp" % (place, nbr)
flines = arcpy.MakeFeatureLayer_management(flinesFile)
ctchFile = basedir + r"NHD/NHDPlus%s/NHDPlus%s/NHDPlusCatchment/Catchment.shp" % (place, nbr)
ctch = arcpy.MakeFeatureLayer_management(ctchFile)

#flow accum and dir rasters
fac1 = basedir + r"NHD/NHDPlus%s/NHDPlus%s/NHDPlusFdrFac%s/fac" % (place, nbr, fnbr1)
fdr1 = basedir + r"NHD/NHDPlus%s/NHDPlus%s/NHDPlusFdrFac%s/fdr" % (place, nbr, fnbr1)
if fnbr2:
    fac2 = basedir + r"NHD/NHDPlus%s/NHDPlus%s/NHDPlusFdrFac%s/fac" % (place, nbr, fnbr2)
    fdr2 = basedir + r"NHD/NHDPlus%s/NHDPlus%s/NHDPlusFdrFac%s/fdr" % (place, nbr, fnbr2)

#declare temps
fac_cliptemp = scratch + "faccliptemp.tif"
fdr_cliptemp = scratch + "fdrcliptemp.tif"
pour_temp = scratch + "pour_temp.tif"
wshd_temp = scratch + "wshd_temp.tif"
poly_temp = scratch + "poly_temp.shp"
fsplit_temp = scratch + "flineSplit_temp.shp"
fline_append = scratch + "fline_append.shp"

#declare mergers
poly_dissolve = scratch + "poly_dissolve.shp"
fline_merge = savedir_lines + "dam_flowlines_%s.shp" %place
poly_merge = savedir_polys + "dam_watersheds_%s.shp" %place
#spatial reference for merging polys
ctch_spref = arcpy.Describe(ctch).spatialReference

#triggers
merger=0 #trigger to build merged poly file before appending

#error log
logf = open(basedir + r"joe/error.log", "w")

#internal functions
#fn to determine existence of field
def FieldExist(featureclass, fieldname):
    fieldList = arcpy.ListFields(featureclass, fieldname)

    fieldCount = len(fieldList)

    if (fieldCount == 1):
        return True
    else:
        return False


#Objectives:
#1) select flowlines upstream of dam
#2) select catchment polygons upstream of dam
#3) improve accuracy within the dam's enclosing catchment
#for the third objective, need to use flow accumulation, direction rasters in addition to flowline and catchment features
#need to use additional tools: snap pour point, clip, watershed, split line at point

#import pdb
#pdb.set_trace()
#fields. adding one field
if (not FieldExist(dams, 'HAB_0m_km')):
    arcpy.AddField_management(dams,'HAB_0m_km','DOUBLE',18,6)

Cols = ['UNIQUE_ID','COMID','FEATUREID','OBJECTID','HAB_0m_km']
#expressions for catchment/flowline selection
dam_column = '"%s"' % Cols[0]
flines_column = '"%s"' % Cols[1]
ctch_column = '"%s"' % Cols[2]

cur=arcpy.da.UpdateCursor(dams,Cols) #just go through ones that previously passed the environment/development/impoundment tests.
for row in cur:
    #if not row[0] == 'e3214':
    #    continue
    print '%s' % row[0]

    #select the enclosing stuff, excluding upstream catchment/flowlines
    s_encl = str(row[2])
    fline_encl_exp = flines_column + ' IN (%s)'%s_encl
    ctch_encl_exp = ctch_column + ' IN (%s)'%s_encl
    dam_exp = dam_column + ' = \'%s\''%row[0]
    dam_select = arcpy.SelectLayerByAttribute_management(dams,"NEW_SELECTION",dam_exp)
    flines_select = arcpy.SelectLayerByAttribute_management(flines,"NEW_SELECTION",fline_encl_exp)
    ctch_select = arcpy.SelectLayerByAttribute_management(ctch,"NEW_SELECTION",ctch_encl_exp)

    #clip flow accum, direction
    #pdb.set_trace()
    if wshdtrig:
        try:
            arcpy.Clip_management(fac1, "#", fac_cliptemp, ctch_select, "-2147483647", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
            arcpy.Clip_management(fdr1, "#", fdr_cliptemp, ctch_select, "0", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
        except:
            try:
                arcpy.Clip_management(fac2, "#", fac_cliptemp, ctch_select, "-2147483647", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
                arcpy.Clip_management(fdr2, "#", fdr_cliptemp, ctch_select, "0", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
            except Exception, e:
                print "    trouble clipping fac/fdr with dam %s at catchment %s" %(row[0],row[2])
                print "    %s"%str(e)
                logf.write("trouble clipping fac/fdr with dam %s at catchment %s : ERROR_MSG %s" %(row[0],row[2], str(e)))
                #pdb.set_trace()
                continue

        #snap pour point
        try:
            arcpy.gp.SnapPourPoint_sa(dam_select, fac_cliptemp, pour_temp, "100", "OBJECTID")
        except Exception, e:
            print "    trouble snapping pour point with dam %s at catchment %s" %(row[0],row[2])
            print "    %s"%str(e)
            logf.write("trouble snapping pour point with dam %s at catchment %s : ERROR_MSG %s" %(row[0],row[2], str(e)))
            #pdb.set_trace()
            continue

        #watershed
        try:
            arcpy.gp.Watershed_sa(fdr_cliptemp, pour_temp, wshd_temp, "Value")
        except Exception, e:
            print "    trouble delineating watershed with dam %s at catchment %s" %(row[0],row[2])
            print "    %s"%str(e)
            logf.write("trouble delineating watershed with dam %s at catchment %s : ERROR_MSG %s" %(row[0],row[2], str(e)))
            #pdb.set_trace()
            continue

        #raster to poly
        try:
            arcpy.RasterToPolygon_conversion(wshd_temp, poly_temp, "NO_SIMPLIFY", "Value")
            if (not FieldExist(poly_temp, "AreaSqKM")):
                arcpy.AddField_management(poly_temp,"AreaSqKM",'DOUBLE',18,6)
                arcpy.CalculateField_management(poly_temp,"AreaSqKM",'!shape.area@squarekilometers!','PYTHON')#ctch_spref)
            #add field UNIQUE_ID and FEATUREID from dam
        except Exception, e:
            print "    trouble converting raster to poly with dam %s at catchment %s" %(row[0],row[2])
            print "    %s"%str(e)
            logf.write("trouble converting raster to poly with dam %s at catchment %s : ERROR_MSG %s" %(row[0],row[2], str(e)))
            #pdb.set_trace()
            continue

    #split line at point
    try:
        #pdb.set_trace()
        arcpy.SplitLineAtPoint_management(flines_select, dam_select, fsplit_temp, "")
    except Exception, e:
        print "    trouble splitting flowline with dam %s at catchment %s" %(row[0],row[2])
        print "    %s"%str(e)
        logf.write("trouble splitting flowline with dam %s at catchment %s : ERROR_MSG %s" %(row[0],row[2], str(e)))
        #pdb.set_trace()
        continue

    #load flowlist, read FEATUREID/CatchCOMID from row[1], that is the next upstream flowline. Select it, then use it to select the correct split line section
    f_flowlist = loadir + r'NHDPlus%s/dam_%s_wfll.csv' % (place,s_encl)
    flist=np.loadtxt(f_flowlist,delimiter=',')

    #Use adjacent upstream neighbor to separate split upstream section from downstream section
    #If there are no upstream neighbors...it's a headwater stream, assume there is no habitat available for american shad
    if not flist.size > 1:
        row[4] = 0 #This isn't pretty, but far as I know, Shad typically don't utilize headwater streams anyway. It's kind of necessary right now because I can't think of a good way to select the upstream split line piece without using upstream neighbors.
    else:
        fnbr_exp = flines_column + ' IN (%s)'%int(flist[1])
        fnbr_select = arcpy.SelectLayerByAttribute_management(flines,"NEW_SELECTION",fnbr_exp)
        fsplit_lyr = arcpy.MakeFeatureLayer_management(fsplit_temp)
        fsplit_up = arcpy.SelectLayerByLocation_management(fsplit_lyr, "INTERSECT", fnbr_select, "", "NEW_SELECTION", "NOT_INVERT")
        #fsplit_down = arcpy.SelectLayerByLocation_management(fsplit_temp, "INTERSECT", fnbr_select, "", "NEW_SELECTION", "INVERT")
        try:
            arcpy.CalculateField_management(fsplit_up,'LENGTHKM','!shape.length@kilometers!','PYTHON')#ctch_spref)

        except Exception, e:
            print "    trouble calculating length for split flowline with dam %s at catchment %s" %(row[0],row[2])
            print "    %s"%str(e)
            logf.write("trouble calculating length for split flowline with dam %s at catchment %s : ERROR_MSG %s" %(row[0],row[2], str(e)))
            #pdb.set_trace()
            continue
        arcpy.CopyFeatures_management(fsplit_up,fline_append)
        cur2=arcpy.da.SearchCursor(fline_append,['LENGTHKM']) #just go through ones that previously passed the environment/development/impoundment tests.
        for row2 in cur2:
            new_lengthkm=row2[0]
        #import channel dimensions data, used for calculating area/habitat area
        f_chandims = basedir + r"joe/CHANDIMtest%s.csv" % place
        chandims=np.loadtxt(f_chandims,delimiter=',',skiprows=1,usecols=(0,1,4,5))
        hab_raw = np.sum(chandims[np.isin(chandims[:,0],flist[1:]),1] * (chandims[np.isin(chandims[:,0],flist[1:]),3]/1e3))
        hab_adjacent = new_lengthkm * (chandims[np.isin(chandims[:,0],flist[0]),3]/1e3)
        hab_zerowidth = hab_raw + hab_adjacent
        #pdb.set_trace()
        row[4] = hab_zerowidth[0]
        cur.updateRow(row)

        #select the line section upstream of the dam, calculate its distance
        #select by first selecting the next upstream flowline, then selecting the adjacent split line
        #take length ratio compared to total length of split line pairs, multiply by total length to get new length
        if makespatial:
            #select the upstream stuff, excluding the enclosing catchment/flowline
            s_up = ','.join([str(j) for j in (filter(lambda a: a != 0, flist[1:]))]) #flist[1:] is everything but the first
            fline_up_exp = flines_column + ' IN (%s)'%s_up
            flines_up_select = arcpy.SelectLayerByAttribute_management(flines,"NEW_SELECTION",fline_up_exp)
            if wshdtrig:
                ctch_up_exp = ctch_column + ' IN (%s)'%s_up
                ctch_up_select = arcpy.SelectLayerByAttribute_management(ctch,"NEW_SELECTION",ctch_up_exp)

            #build merged and dissolved flownets, watershed polygons
            #append poly to upstream catchments file
            try:
                if wshdtrig:
        	           arcpy.Append_management(ctch_up_select, poly_temp, "NO_TEST","","")
                arcpy.Append_management(flines_up_select, fline_append, "TEST","","")
            except Exception, e:
                print "    trouble appending polygon with dam %s at catchment %s" %(row[0],row[2])
                print "    %s"%str(e)
                logf.write("trouble appending polygon with dam %s at catchment %s : ERROR_MSG %s" %(row[0],row[2], str(e)))
                #pdb.set_trace()
                continue

            #dissolve catchments
            if wshdtrig:
                try:
                    arcpy.Dissolve_management(poly_temp, poly_dissolve, "", "AreaSqKM SUM", "MULTI_PART", "DISSOLVE_LINES")
                except Exception, e:
                    print "    trouble dissolving catchments with dam %s at catchment %s" %(row[0],row[2])
                    print "    %s"%str(e)
                    logf.write("trouble dissolving catchments with dam %s at catchment %s : ERROR_MSG %s" %(row[0],row[2], str(e)))
                    #pdb.set_trace()
                    continue
                poly_lyr = arcpy.MakeFeatureLayer_management(poly_dissolve)
                #add UNIQUE_ID field of dam
                #poly
                if (not FieldExist(poly_lyr, Cols[0])):
                    arcpy.AddField_management(poly_lyr,Cols[0],'TEXT',field_length="50")
                arcpy.CalculateField_management(poly_lyr,Cols[0],'"%s"' % row[0],'PYTHON')#ctch_spref)
            #flow lines
            fline_lyr = arcpy.MakeFeatureLayer_management(fline_append)
            if (not FieldExist(fline_lyr, Cols[0])):
                arcpy.AddField_management(fline_lyr,Cols[0],'TEXT',field_length="50")
            arcpy.CalculateField_management(fline_lyr,Cols[0],'"%s"' % row[0],'PYTHON')#ctch_spref)


            #append dissolved stuff over entire region
            if not merger:
                if wshdtrig:
                    arcpy.CopyFeatures_management(poly_lyr,poly_merge)
                arcpy.CopyFeatures_management(fline_lyr,fline_merge)
                merger +=1
            else:
                if wshdtrig:
                    arcpy.Append_management(poly_lyr, poly_merge, "TEST")
                arcpy.Append_management(fline_lyr, fline_merge, "TEST")

    #pdb.set_trace()
    #arcpy.CopyFeatures_management(flines_up_select, savedir_lines + "dam_4512772_wfll.shp")

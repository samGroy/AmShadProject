import numpy as np
import arcpy
from arcpy import env
import sys

#debug library
import pdb

#user input args
place=sys.argv[1]

basedir=r"D:/FoD/data/"
loadir=basedir + r"joe/watershedFlowlineLists/"

#seek options
if place == 'NE':
    nbr = '01'
elif place == 'MA':
    nbr = '02'
elif place == 'SA1':
    nbr = '03N'
elif place == 'SA2':
    nbr = '03S'

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

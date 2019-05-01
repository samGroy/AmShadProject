import numpy as np
import arcpy
from arcpy import env

basedir=r"D:/FoD/data"
loadir=basedir + r"/joe/watershedFlowlineLists/"
savedir=basedir + r"/joe/watershedFlowlines/"
f_flowlist=loadir + r"dam_4512772_wfll.csv" #file containing dam-flowline/catchment linked COMIDs. These are actually linked to catchments, not flowlines, because of occasional offset in boundaries of both. More important to match dam to its containing catchment

flist=np.loadtxt(f_flowlist,delimiter=',')

env.workspace = savedir
arcpy.env.overwriteOutput=True
arcpy.CheckOutExtension('Spatial')
flinesFile = basedir + r"/NHD/NHDPlusMA/NHDPlus02/NHDSnapshot/Hydrography/NHDFlowline.shp"
flines = arcpy.MakeFeatureLayer_management(flinesFile)

Cols = ['COMID']
column = '"%s"' % Cols[0]
s = ','.join([str(j) for j in (filter(lambda a: a != 0, flist))])
exp = column + ' IN (%s)'%s

select = arcpy.SelectLayerByAttribute_management(flines,"NEW_SELECTION",exp)
arcpy.CopyFeatures_management(select, savedir + r"dam_4512772_wfll.shp")

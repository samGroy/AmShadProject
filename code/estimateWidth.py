#estimateWidth.py
#calculate river km, then estimate width from river km. Canada doesn't have drainage area data for their flowlines, from what I've seen at least :(
import numpy as np
import pdb

place = 'CN'
basedir=r"D:/FoD/data/AmShad/"
savedir=basedir + r"HabitatOut/"

f_lines=basedir + r"flownets/COMIDflownet%s.csv" % place #downstream neighbor list
flow=np.loadtxt(f_lines,delimiter=',',skiprows=1,usecols=(0,1))

f_chandat=basedir + r"flowData/flowdata%s.csv" % place #additional data, including tidal flag
chandat=np.loadtxt(f_chandat,delimiter=',',skiprows=1,usecols=(0))

total = np.loadtxt(f_chandat,delimiter=',',skiprows=1,usecols=(1)) / 2#np.array([0.] * chandat.shape[0])
segment = np.loadtxt(f_chandat,delimiter=',',skiprows=1,usecols=(1))
heads = flow[flow[:,0]==0,1]
#cumkm[np.isin(chandat,heads)]=chandat[np.isin(chandat,heads),1]
#pdb.set_trace()

ct=0
for i in heads:
    ct+=1
    print 'head %s of %s' % (ct,heads.size)
    dnprev=i
    try:
        dn = flow[flow[:,0]==i,1][0]
    except:
        continue
    dist=segment[chandat==dn]

    while dn:
        total[chandat==dn] = total[chandat==dn] + dist#cumkm[chandat==dnprev][0]
        dist = dist + segment[chandat==dn]
        #cumkm[chandat==dn] = cumkm[chandat==dn] + cumbase[chandat==dnprev][0]#cumkm[chandat==dnprev][0]
        #f.write('%s,%s,%s,%s\n' % (dnprev, dn, cumbase[chandat==dn], cumkm[chandat==dn]))
        dnprev = dn
        dn = flow[flow[:,0]==dn,1][0]
    #f.write('\n')

#f = open(savedir + r"CNckm.csv", "w")
#f.write('COMID,cumkm\n')

#for i in chandat:
#    dnprev=i
#    try:
#        dn = flow[flow[:,0]==i,1][0]
#    except:
#        continue
#    while dn:
#        try:
#            cumkm[chandat==dn] = cumkm[chandat==dn] + cumbase[chandat==dnprev][0]
#        except:
#            pdb.set_trace()
#        #dnprev = dn
#        dn = flow[flow[:,0]==dn,1][0]

f = open(savedir + r"CNckm.csv", "w")
f.write('COMID,downkm\n')
#f.write('from,to,cmbase,cmkm\n')

for j in xrange(total.size):
    f.write('%s,%s,%s\n' % (chandat[j].astype('int32'), total[j], segment[j]))
f.close()

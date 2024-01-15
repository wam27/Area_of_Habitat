# -*- coding: utf-8 -*-
"""
Created on Tue Dec 26 20:07:24 2023

@author: wam27
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Mar 30 22:37:51 2021

@author: wam27
"""

################# FUNCTIONS ###########################################################################
#======================================================================================================
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from geopandas.tools import sjoin
import os, arcpy
from arcpy import env
import arcpy.sa
import zipfile
pd.options.mode.chained_assignment = None
import warnings


#======================================================================================================
#//////////////////////////////////////////////////////////////////////////////////////////////////////

################# ENVIRONMENT #########################################################################
#======================================================================================================
#import json
warnings.filterwarnings("ignore")
#Chek out ArcGis Analyst and allow overwrite files
arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True
# Set relative paths
#scriptWS= os.path.basename(sys.argv[0])
rootWS= os.getcwd()
main= '\Explore'    #SET Change this for the project folder name
data_dir= rootWS + main
#rootWS= os.path.dirname(sys.path[0])
dataWS = os.path.join(data_dir, 'Data')  # 'data'
scratchWS = os.path.join(data_dir, 'Scratch')
docsWS = os.path.join(data_dir, 'Docs')
data_out= os.path.join(rootWS, 'RioBirds\Data')
w_out= os.path.join(rootWS, 'RioBirds\Scratch')


#Set work environment
env.workspace= dataWS
#Call variables
os.chdir(rootWS)
#======================================================================================================
#//////////////////////////////////////////////////////////////////////////////////////////////////////


################# VARIABLES ###########################################################################
#======================================================================================================
epsg=4326
sr = arcpy.SpatialReference(epsg)
Continent_pol=gpd.read_file(dataWS + '\World_Borders\World_Borders.shp')#'ECP\Bra_Pan.shp'
Continent_pol=Continent_pol[~(Continent_pol.geometry.isnull())]
Continent_pol=Continent_pol.to_crs(epsg)
Continent_pol=Continent_pol.rename(columns={'COUNTRY':'Country'})
Species_info=gpd.read_file(w_out+'\ThreatRio_30.shp')
Species_info_df=pd.read_csv(w_out+'\BirdRanges_RIO-Threatened.csv', encoding='latin1')



n=''
Create_folders=True
AGGREGATE=True
get_rid=False
filter_errors=True
GBIF=False
PRIVATE=False
Reports=True
roundeBird=False
OCCUR=False


#%%%
if Create_folders:
    folders=['Pres','Temp','Graphs','Hull', 'BL','Areas']
    for f in folders:
        os.mkdir(os.path.join(w_out,str(f)))
        
        
#%%%%%%%%%%%%%%%%%%%%%
#========================================================================================================
#////////////////////////////////////////////////////////////////////////////////////////////////////////

#Simulation
b=13

c='{}'.format(Species_info_df['ScientificName'][b])
print('Starting ' + c)


report=[]
report_errors=[]
eBird_all=[]

#Start lopping over each species
for b in range(26,27): # bs.Index_name: # # range(86,90): 
    try:
        a='{}'.format(Species_info_df['ScientificName'][b])
        s='{}'.format(Species_info_df['eBirdName'][b])
        
        if '/' in a:
           r=a.split('/') 
           c=r[0]
        elif '[' in a:
            c=s
        else:
            c=a
        print(str(b)+ ' ' + c)
        
        sp_gdf=Species_info.loc[Species_info['eBirdName']==c]
        if not sp_gdf.empty:
            sp_gdf.to_file(w_out +'\BL\{}_BL.shp'.format(c), driver='ESRI Shapefile', encoding = 'utf-8')  
        else:
            sp_gdf=Species_info.loc[Species_info['eBirdName']==s]
            sp_gdf.to_file(w_out +'\BL\{}_BL.shp'.format(c), driver='ESRI Shapefile', encoding = 'utf-8')  
            

    ########################################
    ########################################
    ####### GETTING EBIRD OCCURENCES #######
    ########################################
    ########################################
        
#        print('Getting eBird')
#        if EBD:
#          ebd=dd.read_csv(dataWS + "\eBird\ebd_relJan-2021.txt",dtype={'REASON': 'object'} ,sep='\t')
#          ebd_sp=ebd[ebd['SCIENTIFIC NAME'].str.contains(Species_info_df['Scientific'][0])]
#          ebd_sp2=ebd_sp.compute()
        #else:
        file_path1='ebd_{}_relNov-2023'.format(Species_info_df['SPECIES_CODE'][b])
            #file_path2='ebd_{}_relDec-2021'.format(Species_info_df['SPECIES_CODE'][b])
        if  os.path.isfile(data_out+'\\eBird\\30spp_Nov23\\'+file_path1+'.zip'):
            zap=zipfile.ZipFile(data_out+'\\eBird\\30spp_Nov23\\'+file_path1+'.zip') 
            ebird=pd.read_csv(zap.open(file_path1+'.txt'),sep='\t')
       
        
        if not ebird.empty:
            if roundeBird:
                ebird['LONGITUDE'] = ebird['LONGITUDE'].apply(lambda x: round(x, 2))
                ebird['LATITUDE'] = ebird['LATITUDE'].apply(lambda x: round(x, 2))
        
            
            ebird['OBSERVATION COUNT'].replace('X',0, inplace=True)
            ebird['OBSERVATION COUNT']=ebird['OBSERVATION COUNT'].fillna(0)
            ebird['OBSERVATION COUNT']=ebird['OBSERVATION COUNT'].apply(int)
            
            ebird_f=ebird[(ebird['APPROVED']==1) &
                              (ebird['ALL SPECIES REPORTED']==1) &
                              ~(ebird['DURATION MINUTES']>180) &
                        ~((ebird['PROTOCOL TYPE']=='Traveling') &  
                          (ebird['EFFORT DISTANCE KM']>7)) &
                        ~((ebird['PROTOCOL TYPE']=='Historical') &  
                          (ebird['EFFORT DISTANCE KM']>7))]
            
            if not ebird_f.empty:
                ebird_f.to_csv(w_out +'\Pres\{}_eBird.csv'.format(c), encoding = 'utf-8')
                ebird_f['geometry']=ebird_f.apply(lambda x: Point((float(x.LONGITUDE), float(x.LATITUDE))), axis=1)
                ebird_f=gpd.GeoDataFrame(ebird_f, geometry='geometry', 
                                             crs={'proj': 'latlong', 'ellps': 'WGS84', 'datum': 'WGS84', 'no_defs': True, 'wktext': True})
                ebird_f=ebird_f.to_crs({'init' :'epsg:4326'})
                ebird_f2=sjoin(ebird_f,Continent_pol,how='inner', op='intersects').reset_index(drop=True) #selecting occurences only in continental areas with ECP shapefile
                ebird_f2=ebird_f2.loc[:,:'geometry']
                #ebird_f2=sjoin(ebird_f2,States,how='inner', op='within').reset_index(drop=True)
                #ebird_f2.crs= {'init' :'epsg:4326'}
                
                ebird_count=len(ebird_f2)
            else:
                ebird_f2=ebird_f
                PR=0
                PTr=0
                PTest=0
                ebird_count=0
                len_occur1=0
                len_occur2=0
                print ('no eBird')
                
        else:
            ebird_f2=ebird
            PR=0
            PTr=0
            PTest=0
            ebird_count=0
            len_occur1=0
            len_occur2=0
            print ('no eBird')
            
#######################################
#######################################
############# END EBIRD ###############
#######################################
#######################################
        
        
        
        #occur.sort_values(['LONGITUDE', 'LATITUDE','YEAR','ELEVATION'], inplace=True)
        #occur.drop_duplicates(subset=['LONGITUDE', 'LATITUDE','YEAR','ELEVATION'],inplace=True)
        ebird_f2.sort_values(['LONGITUDE', 'LATITUDE'], inplace=True)
        ebird_f2.drop_duplicates(subset=['LONGITUDE', 'LATITUDE'],inplace=True)
        ebird_f2.to_csv(scratchWS +'\Pres\{}_pres.csv'.format(c), encoding = 'utf-8')
        #occur.crs= {'init' :'epsg:4326'}
        ebird_f2=ebird_f2.to_crs({'init' :'epsg:4326'})
        ebird_f2.to_file(scratchWS +'\Pres\{}_pres.shp'.format(c), driver='ESRI Shapefile', encoding = 'utf-8')  #PRESENCES
        PR=len(ebird_f2)
        PTr=0
        PTest=0
        
            
        
            ##############################
            ##############################
            ####### END OCURRENCES #######
            ##############################
            ##############################
        
        ebird_f2.to_file(w_out +'\Pres\{}_ebird.shp'.format(c), driver='ESRI Shapefile', encoding = 'utf-8') #PRESENCES
                       
            
        if Reports:              
            #SAVING DATA TO A REPORT TABLE AND EXPORT TO CSV
            report.append([c,ebird_count])
            Report_Table=pd.DataFrame(report,columns=['Scientific Name', 'Presences'])
            Report_Table.to_csv(scratchWS + "\Report_Presences"+n+".csv", encoding = 'utf-8') 
            print('******* ' + c +' ******* done!\n')
            arcpy.ResetEnvironments()
    
    except ValueError as e:
        report_errors.append([c,e])
    Report_Errors=pd.DataFrame(report_errors,columns=['Scientific Name','Error'])
    Report_Errors.to_csv(scratchWS + "\Report_Errors"+n+".csv", index_label='Index_name') 

print ('Complete!')
    
    



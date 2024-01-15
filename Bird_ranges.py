# -*- coding: utf-8 -*-
"""
Created on Sun Apr 16 01:08:32 2023

@author: wam27
"""

import zipfile
import fiona
import warnings
#import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
import os
import arcpy
from arcpy import env
import arcpy.sa
import requests
import json
import numpy as np
from IUCN_Habitat import Habitat

pd.options.mode.chained_assignment = None
#import dill
warnings.filterwarnings("ignore")


# Chek out ArcGis Analyst and allow overwrite files
arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

# Set relative paths
main= '\\'    #SET Change this for the project folder name
#scriptWS= os.path.basename(sys.argv[0])
rootWS= os.getcwd()+ main
#rootWS= os.path.dirname(sys.path[0])
dataWS = os.path.join(rootWS, 'Data')  # 'data'
scratchWS = os.path.join(rootWS, 'Scratch')
docsWS = os.path.join(rootWS, 'Docs')

# Set work environment
env.workspace = dataWS

# Call variables
os.chdir(os.getcwd())
# dems=glob.glob('FOREST_COVER2016\Hansen\Treecover2000\Rasters\**.tif')
# arcpy.Mosaic_management(dems,'FOREST_COVER2016\Hansen\Treecover2000\Hansen_GFC-2018-v1.6_treecover2000_00N_070W.tif')
epsg = 4326
sr = arcpy.SpatialReference(epsg)


# %%
# Read the range shapefile

#input_shp = dataWS +'\BirdLife\Birds_filt.shp' # dataWS+ '\BirdLife\\BOTW.gdb'  #  #
range_size = 'NA'
group= 'b' # b-birds, m-mammals, r-reptiles, a-amphibians, ch=bats
# AREA OF INTEREST (AOI): Shapefile of the geographical area of interest. Here we use the Northern Andes ecoregion as AOI.
Area_of_Interest = gpd.read_file(dataWS +'\\Boundaries\\Rio.shp', encoding="utf-8" )
Area_of_Interest = Area_of_Interest.to_crs({'init': 'epsg:4326'})
Area_of_Interest = Area_of_Interest.dissolve()
# TAXONOMIC DATABASE REFERENCE (TDR): eBird clements taxonomy
TaxonomicReference = pd.read_csv(dataWS+'\Databases\eBird_Taxonomy_v2022.csv', encoding='latin1')
TaxonomicReference = TaxonomicReference.rename(columns={'SCI_NAME':'ScientificName'})
# OTHER REFERENCE LISTS (ORL): List of birds of Ecuador
ReferenceList1 = pd.read_csv(dataWS + '\Databases\ecuador_lista-master-final_2022.csv', encoding='latin1')



def ranges(input_shp, range_size=int, Terrestrial=True,
           Area_of_Interest=None, TaxonomicReference=None,
           ReferenceList1=None, ReferenceList2=None):

    token = '9bb4facb6d23f48efbf424bb05c0c1ef1cf6f468393bc745d42179ac4aca5fee'
    
    #Read Birdlife taxonomy checklist and use some columns only
    #Birdlife_Ccklist = pd.read_csv(dataWS+'\Birdlife\BirdLife_Taxonomic_Checklist_V5.csv', encoding='latin1')
    
    #Read Birdlife shapefile with all species and rename column binomial
    BOTW = 'D:\PhD_Projects\Explore\Data\Birdlife2\BOTW_2022_2\BOTW.gdb'
    layers = fiona.listlayers(BOTW)
    Birdlife_gdf = gpd.read_file(BOTW, layer=layers[0])
    Birdlife_gdf = Birdlife_gdf.to_crs({'init': 'epsg:4326'})
    
    Birdlife_Ccklist = gpd.read_file(BOTW, layer=layers[1])
    Birdlife_Ccklist = Birdlife_Ccklist[['Family','CommonName', 'ScientificName','RL_Category', 'Synonyms', 'TaxonomicSources']]
 
    
    
    #Select native and breeding species only to end up with 13124 spp
    BOTW_POS=Birdlife_gdf[(Birdlife_gdf['presence']==1) & (Birdlife_gdf['origin']==1) &
                     (Birdlife_gdf['seasonal']==1) | (Birdlife_gdf['seasonal']==2)]
    BOTW_POS=BOTW_POS.sort_values(['sci_name']).reset_index(drop=True)
    BOTW_POS = BOTW_POS.rename(columns={'sci_name':'ScientificName'})
    
    #Birdlife_gdf = Birdlife_gdf.rename(columns={'binomial': 'ScientificName'})
    
    
    
#    Birdlife_gdf_ckl_eBird=Birdlife_gdf_ckl_eBird.drop_duplicates(subset='ScientificName').reset_index(drop=True)
    # Intersect with AOI
    Spp_AOI = gpd.sjoin(BOTW_POS, Area_of_Interest,'inner', 'intersects').reset_index(drop=True)
    #Spp_AOI.to_file(dataWS +'\BirdLife\Birds_AOI.shp', driver='ESRI Shapefile', encoding = 'utf-8')
    Spp_AOI = Spp_AOI.sort_values(['ScientificName']).reset_index(drop=True)
    

    # Fix invalid geometries of species ranges by buffering to 0
    Spp_list = []
    for v in range(len(Spp_AOI)):
        r = '{}'.format(Spp_AOI["ScientificName"][v])
        print(v, r)
        sp = Spp_AOI[Spp_AOI['ScientificName'] == r]
        if len(sp.geometry) <= 1:
            sp['geometry'] = sp.geometry.buffer(0)
            Spp_list.append(sp)  # Fix the invalid and add them to the list
        else:
            Spp_list.append(sp)  # add the good to the list
    Spp_df = pd.concat(Spp_list, ignore_index=True, sort=False)
    if 'Shape_Area_left' in Spp_df.columns:
        Spp_df.sort_values(['Shape_Area_left'], inplace=True)
        # 1844 spp ECU  #2098 COL_ECU #2204 NAndes
        Spp_df.drop_duplicates(subset='Shape_Area_left', inplace=True)
    else:
        Spp_df.sort_values(['Shape_Area'], inplace=True)
        # 1844 spp ECU  #2098 COL_ECU #2204 NAndes
        Spp_df.drop_duplicates(subset='Shape_Area', inplace=True)

    # Project data to Cylindrical equal area, cea
    Spp_df = Spp_df.to_crs({'proj': 'cea'})
    # Calculate the area of each species distribution
    Spp_df['Area'] = Spp_df.area/10**6
    # Set a dataframe with only Area
    Spp_df2 = Spp_df[['ScientificName', 'Area']]
    # Group by species name and sum up Area
    Spp_df3 = Spp_df2.groupby('ScientificName')['Area'].sum().reset_index()
    # Get species with distribution area <50.000 sqr Km
    if type(range_size) == int:
        Spp_50 = Spp_df3[Spp_df3['Area'] < range_size].reset_index(
            drop=True)  # 166 spp
    else:
        Spp_50 = Spp_df3

    # f=1
    Spp_50_list = []
    for f in range(len(Spp_50)):
        z2 = '{}'.format(Spp_50["ScientificName"][f])
        Spp_50_match = BOTW_POS[BOTW_POS['ScientificName'].str.match(z2)]
        Spp_50_list.append(Spp_50_match)
    Spp_50_df = pd.concat(
        Spp_50_list, ignore_index=True, sort=False)  # 194 spp
    # Project data to Cylindrical equal area, cea
    Spp_50_df = Spp_50_df.to_crs({'proj': 'cea'})
    # Calculate the area of each species distribution
    Spp_50_df['Area'] = Spp_50_df.area/10**6
    Spp_50_df.sort_values(['Area'], inplace=True)
    Spp_50_df.drop_duplicates(subset='Area', inplace=True)


    # Dissolve by species summing up by area
    Spp_50_df['geometry'] = Spp_50_df.geometry.buffer(0)
#    Spp_v = Spp_50_df.dissolve(by='ScientificName', aggfunc='sum').reset_index()
    # Get species with distribution area <100.000 sqr Km
    if type(range_size) == int:
        Spp_50_gdf = Spp_50_df[Spp_50_df['Area'] < range_size].reset_index(
            drop=True)  # 164 spp Ecu # 320 ColEcu  #379 NAndes
    else:
        Spp_50_gdf = Spp_50_df
    Spp_50_gdf = Spp_50_gdf.sort_values(
        ['ScientificName']).reset_index(drop=True)
    Spp_50_gdf=Spp_50_gdf.drop_duplicates(subset='ScientificName').reset_index(drop=True)
    #sp=EcuSpp_50_gdf[EcuSpp_50_gdf['binomial']=='Scytalopus robbinsi']

    # g=gdf.loc[:0]
    # g.to_file(scratchWS +'\sp1_gbif.shp', driver='ESRI Shapefile', encoding = 'utf-8') #Create gbif shapefile
    

    # Add ecological data: habitat and elevation
    report_errors = []
    spp_info_list = []
    # b=152
    for s in range(276,len(Spp_50_gdf)):  # range(38,63): #
        try:
            c = '{}'.format(Spp_50_gdf["ScientificName"][s])
            print(s, c)

            # Find the habitat for each species
            name = c.replace(' ', '%20')
            url_habitat = '{}'.format('https://apiv3.iucnredlist.org/api/v3/habitats/species/name/'+name+'?token='+token)
            r = requests.get(url_habitat, verify=False)
            content = r.content
            output = json.loads(content)
            spp_habitat = pd.DataFrame(output['result'])
            if spp_habitat.empty:
                print('No data associated with',c)
                c = '{}'.format(Spp_50_gdf["SCI_NAME"][s])
                print(s, c)

                # Find the habitat for each species
                name = c.replace(' ', '%20')
                url_habitat = '{}'.format('https://apiv3.iucnredlist.org/api/v3/habitats/species/name/'+name+'?token='+token)
                r = requests.get(url_habitat, verify=False)
                content = r.content
                output = json.loads(content)
                spp_habitat = pd.DataFrame(output['result'])
            habitat = spp_habitat['habitat'] + ' ('+spp_habitat['majorimportance'] + ')'
            H = habitat.str.cat(sep=', ')
            Spp_50_gdf.at[s, 'Habitat (Major importance)'] = H

            # Find elevation ranges, eoo and aoo if available
            url_spp = '{}'.format('https://apiv3.iucnredlist.org/api/v3/species/'+name+'?token='+token)
            r2 = requests.get(url_spp, verify=False)
            content2 = r2.content
            output_spp = json.loads(content2)
            if 'result' in output_spp:
                spp_info = pd.DataFrame(output_spp['result'])

            if (spp_info['elevation_upper']).isna()[0]:
                spp_info['elevation_upper'] = 0
            if(spp_info['elevation_lower']).isna()[0]:
                spp_info['elevation_lower'] = 0
            #if (spp_info['elevation_upper'] == 0)[0] and (spp_info['elevation_lower'] == 0)[0] and type(ReferenceList1) != 'pandas.core.frame.DataFrame':
                # if not ReferenceList1.loc[ReferenceList1['HBW-BL Scientific Name'].str.contains((r'^(?=.*{})(?=.*{})').format(c.split()[0], c.split()[1]), na=False)].empty:
                #     spp_info['elevation_upper'] = pd.to_numeric(ReferenceList1.loc[ReferenceList1['HBW-BL Scientific Name'].str.contains(
                #         (r'^(?=.*{})(?=.*{})').format(c.split()[0], c.split()[1]), na=False), 'Alt_max'].iloc[0])
                #     spp_info['elevation_lower'] = pd.to_numeric(ReferenceList1.loc[ReferenceList1['HBW-BL Scientific Name'].str.contains(
                #         (r'^(?=.*{})(?=.*{})').format(c.split()[0], c.split()[1]), na=False), 'Alt_min'].iloc[0])

            
            spp_info_list.append(spp_info)
        except ValueError as e:
            report_errors.append([c, e])
       # Report_Errors=pd.DataFrame(report_errors,columns=['Scientific Name','Error'])
    print('Complete!')

    spp_info_df = pd.concat(spp_info_list, ignore_index=True, sort=False)
    spp_info_df = spp_info_df.rename(columns={'scientific_name': 'ScientificName'})
    spp_info_df['eoo_km2'] = pd.to_numeric(spp_info_df['eoo_km2'])
    spp_info_df['aoo_km2'] = pd.to_numeric(spp_info_df['aoo_km2'], errors='coerce')
    spp_info_df.drop(['depth_upper', 'depth_lower', 'errata_flag', 'errata_reason',
                  'amended_flag', 'amended_reason'], axis=1, inplace=True)
   
    
   # spp_info_df = spp_info.rename(
       # columns={'scientific_name': 'binomial'})
    
    Spp_50_gdf2 = Spp_50_gdf.merge(spp_info_df, on='ScientificName', how='left')
    Spp_50_gdf2.drop_duplicates(subset='ScientificName', inplace=True)

    if type(range_size) == int:
        Spp_50_H = Spp_50_gdf2[(Spp_50_gdf2['Habitat (Major importance)'].str.contains('Forest')) &
                               ~((Spp_50_gdf2['Habitat (Major importance)'].str.contains('Marine')) |
                               (Spp_50_gdf2['Habitat (Major importance)'].str.contains('Wetlands')) |
            (Spp_50_gdf2['Habitat (Major importance)'].str.contains(
                'Mangrove'))  # |
            # (Spp_50_gdf2['Habitat (Major importance)'].str.contains('High Altitude'))
        )]
    else:
        if Terrestrial:
            Spp_50_H = Spp_50_gdf2[~(
                (Spp_50_gdf2['Habitat (Major importance)'].str.contains('Marine')))]
        else:
            Spp_50_H = Spp_50_gdf2
    Spp_50_H = Spp_50_H.to_crs({'init': 'epsg:4326'})
    
    Spp_50_H = Spp_50_H.merge(Birdlife_Ccklist, on='ScientificName', how='left')
    
    eBird_list = []
    # cn=1
    for cn in range(len(Spp_50_H)):
        cnm = Spp_50_H["ScientificName"][cn]
        enm = Spp_50_H["CommonName"][cn]
        syn = Spp_50_H["Synonyms"][cn]
        if any(x in enm for x in ['Grey', 'grey']):
            enm = enm.replace('Grey', 'Gray')
        CN = TaxonomicReference[TaxonomicReference['ScientificName'].str.contains((r'^(?=.*{})(?=.*{})').format(
            cnm.split()[0], cnm.split()[1]), na=False)].reset_index(drop=True)
        if CN.empty:
            CN = TaxonomicReference[TaxonomicReference['PRIMARY_COM_NAME'].str.contains(
                enm, na=False)].reset_index(drop=True)
        if CN.empty:
            if syn != None:
                CN = TaxonomicReference[TaxonomicReference['ScientificName'].str.contains(
                    syn, na=False)].reset_index(drop=True)
        CN = CN.rename(columns={'ScientificName':'eBirdName'})     
        CN['ScientificName'] = cnm
        #EeB=CN.groupby('BL_ScientificName').agg(lambda x: str(x).split('Name:',1)[0]).reset_index()
        eBird_list.append(CN)
    Spp_eBird = pd.concat(eBird_list, ignore_index=True, sort=False)
    Spp_eBird.drop_duplicates(subset='ScientificName', inplace=True)
    #Ecu_eBird_F=Ecu_eBird_F.rename(columns={'English Name':'CommonName','CommonName':'english name'})
    Spp_50_H = Spp_50_H.merge(Spp_eBird, on='ScientificName', how='left')
    Spp_50_H = Spp_50_H.to_crs({'init': 'epsg:4326'})
    
    Spp_50_H.to_file(scratchWS+'\BirdRanges_RIO.shp', driver='ESRI Shapefile', encoding='utf-8')
    Spp_50_H = Spp_50_H.drop(columns=['geometry'])
    Spp_50_H.to_csv(scratchWS+"\BirdRanges_RIO.csv", index=False)

# -*- coding: utf-8 -*-
"""
Created on Tue Dec 26 18:44:59 2023

@author: wam27
"""

#The following parameters are required: df (pandas dataframe) is a dataframe generated in the first step fo the protocol that consists on extracting species ranges for an area of interest.
#The data frame usually is a list of species containing data from Birds of the World databases from BirdLife and other information extracted from the IUCN API such asmin and max elevation ranges and habitat.
# It also contains information based on eBird.
#n (int) is the number assigned to each run. This is to code each output after each run.
#occ (points, pandas geodataframe) is the list of occurrences for each species on the list.
#hull (multypolygon, pandas geofatframe) is the alphahull for each species generated in step three of the protocol.
#cs (int) cell size of the raster dataset
#proj (int) is the desired projection to make estimates in the metric system
#AOH_output (str) is the path for the output where AOHs will be saved
#temp_output (str) is the path for saving temporal files
#aoi (polygon, pandas geodataframe), is the area of interest within the species range. Sometimes we want to know the distribution of a species in a local area using high resolution data.
#The aoi allows for estimating AOH within a smaller region than the species distribtuion range.
#bl (Optional,polygon, pandas geodataframe) is the BirdLife range of the species
#g (multipolygon, pandas geodataframe) is a grid of variabel size and 5x5 km resolution where checklists are counted and will define the absence areas.
#se_df (point, pandas geodataframe) is the sampling effort that will help to define absence areas.

import os, arcpy
import arcpy.sa
import pandas as pd
import geopandas as gpd
import rasterio

import numpy as np
from Forest_api import forest_api
from Forest_extract import extract_forest
from Elevation_tiles import elevation_tiles
from Elevation_extract import extract_elevation



def AOH(df, n, occ, hull, cs, proj,
        AOH_output, temp_output,
        aoi=None,bl=None,g= None,se_df=None):
    
    #define coordinates georeference
    epsg_WGS84= 4326
    #conversion units from sq m to sq km
    m2= 1/10**6
     
    #Report lists
    report_Habitat=[]
    report_Errors=[]
    
    #Path to errors file
    errors= AOH_output + "\Report_Error_Areas_{}.csv".format(n)
    
    for b in  range(len(df)): #len(df)
        try:
            #Select species
            c= df.loc[[b]]['ScientificName'][b]
            print(str(b+1)+" " + c)
            
            #Set path to occurrences and alpahulls
            occ_path=  occ + c + "_ebird.shp"
            hull_path= hull + c + "_hull.shp"
            
            
            #Set paths for output files
            output1= AOH_output + '\{}_AOH.tif'.format(c)
            AOH_shp= temp_output + '\{}_AOH.shp'.format(c)
            Non_detection= temp_output +'\{}_Non_Detection.shp'.format(c)
            Cckl_spp_dir= temp_output +'\Cckl_spp.shp'
            Cckl_spp_hab_dir= temp_output +'\Cckl_spp_hab.shp'
            Absences= temp_output +'\{}_Absences.shp'.format(c)
            Chcklists_pixel= temp_output +'\{}_Absences_pix.shp'.format(c)
            Pres_Abs_path= temp_output +'\{}_Pres_Abs.shp'.format(c)
            idw_spp= temp_output + '\{}_IDW.tif'.format(c)
            Potential_AOH_spp= AOH_output + '\{}_PO_AOH.tif'.format(c)
            Unoccupied_AOH_spp= AOH_output + '\{}_AU_AOH.tif'.format(c)
            
            #Path to reports
            Report= AOH_output + "\Report_Habitat_{}.csv".format(n)
            
            #Test whether there is occurrences and alphahulls
            if os.path.isfile(occ_path) and os.path.isfile(hull_path):
                
                #Read presences
                presences = gpd.read_file(occ_path)
                presences.crs = epsg_WGS84
                #Read alphahulls
                alphahull = gpd.read_file(hull_path)
                alphahull.crs = epsg_WGS84
                
                #Get countries where species is found
                if "COUNTRY" in presences.columns:
                    GD=presences.COUNTRY.unique()
                    GD=', '.join(GD)
                else:
                    GD=presences.country.unique()
                    GD=', '.join(GD)
                    
                #Get number of presences
                number_presences= len(presences)
                
                ######################################################################
                ######################## HABITAT #####################################
                ######################################################################
                print ('1. Refining Habitat')
                ##### TREE COVER #####################################################
                
                #Estimate tree cover
                print ('1. Tree Cover')
                #Use fores_api function to get all trre cover values within the alphahull
                TreeCover= forest_api(alphahull)
                
                #Extract values from the raster array using occurrences
                presences=extract_forest(TreeCover,presences)
                
                #Get year as a new column
                presences['Year']=pd.DatetimeIndex(presences.OBSERVAT_1).year
                #select 2000 and above presences and those within more than 0 tree cover percentage 
                presences_above_2000_TC= presences[(presences.Year>1999) & (presences['Tree_Cover']>0)]
                
                #Test for empty dataframe
                if not presences_above_2000_TC.empty:
                    #Define tree cover threshold that will be used for triming the forest raster
                    TC_threshold=int(round(pd.Series.quantile(presences_above_2000_TC['Tree_Cover'], 0.25)))
                    #Define forest species if threshold is greater than 50% of tree cover
                    if TC_threshold > 50:
                        Forest_Species= 'Yes'
                    else:
                        Forest_Species= 'No'
                else:
                    TC_threshold=0
                    Forest_Species= 'No'
                
                #clip alphahull to the are of interest if desired    
                if not aoi.empty:
                    AOI = gpd.clip(alphahull, aoi)
                
                #mask forest raster by aoi
                TreeCover= forest_api(hull= AOI,
                                      generate=True)
                TC_in_hull=TreeCover[1]
                array= TC_in_hull[0] #get the array, a matrix of raster values
                affine= TC_in_hull[1] #get info from the raster
                #Forest trimmed by a threshold within the alphahull
                TC_by_spp=(array> TC_threshold).astype(int) #subset the array after a condition
                
                
                
                print ('2. Elevation')
                ##### ELEVATION #####################################################
                #Get elevation values within the alphahull
                ElevT=elevation_tiles(hull=alphahull, interv=3, res='SRTMGL1', 
                                      API_key='0aaf39ac1b4a879c80948abbee940504', 
                                      generate=False)
                
                #Extract elevation values for each occurrence
                presences=extract_elevation(datasets= ElevT, 
                                  points= presences)
                
                #Get elevation column
                PresElevation=presences.Elevation
                
                #Define elevation extremes based on lower and upper 1%.
                E_threshold= pd.Series.quantile(PresElevation, [0.01,0.99])
                #set lower and upper elevations
                LE=int(round(E_threshold[0.01]))
                UE=int(round(E_threshold[0.99]))
                
                #Rename to min and max
                Min=LE
                Max=UE
                
                #test for empty elevations within the df
                if type(df['elevation_upper'][b]) != np.floating or  type(df['elevation_lower'][b]) != np.floating:
                    pass
                else:
                    # select the minimum and maximum elevations by comparing documented elevations with estimated elevations
                    BLmin=int(round(df['elevation_lower'][b]))
                    Min= min(BLmin, LE)
                
                    BLmax=int(round(df['elevation_upper'][b]))
                    Max= max(BLmax, UE)
                
                #mask elevation raster by species alphahull
                ElevT=elevation_tiles(hull=AOI, interv=3, res='SRTMGL1', 
                                      API_key='0aaf39ac1b4a879c80948abbee940504',
                                      transform=affine, generate=True)
                
                #Get array
                E_in_hull=ElevT[1]
                array_E= E_in_hull[0].astype(int) #get the array, a matrix of raster values
                
                if array.size!=array_E.size:
                    height=array.shape[1]-array_E.shape[1]
                    width=array.shape[2]-array_E.shape[2]
                    array_E = np.pad(array_E, ((0, 0), (0, height), (0, width)), mode='constant')
                    
                #Elevation trimmed by a threshold within the alphahull
                if np.isnan(Min):
                    E_by_spp=(array_E<=Max).astype(int) #subset the array after a condition
                if np.isnan(Max):
                    E_by_spp=(array_E<=Min).astype(int) #subset the array after a condition
                if np.isnan(Min) and np.isnan(Max):
                    E_by_spp=array_E
                if ~np.isnan(Min) and ~np.isnan(Max):
                    E_by_spp= ((array_E<Max) & (array_E>Min)).astype(int)
                    
                    
                #Overlap elevation and habitat to create the AOH within the alphahull
                AOH_path=output1
                AOH= TC_by_spp*E_by_spp
                with rasterio.open(
                        AOH_path,
                        'w', driver='GTiff',
                        height=AOH.shape[1],width=AOH.shape[2],
                        count=1,dtype=str(AOH.dtype),
                        crs=epsg_WGS84,transform=affine, nodata=0
                        ) as new_dataset:
                    new_dataset.write(AOH)
                new_dataset.close()
                
                size_raster=len(AOH[AOH==1])
                AOH_area=round((size_raster*proj**2)*m2) 
                #########
                
                #Estimate absences based on number of checklists with no confirmed presences
                if type(se_df) is not type(None):
                    #Set extent based on the alphahull
                    arcpy.env.extent = hull_path
                    #Convert AOH to polygon
                    arcpy.RasterToPolygon_conversion(AOH_path, AOH_shp, "NO_SIMPLIFY")
                
                    ######################################################################
                    ######################## ABSENCES ####################################
                    ######################################################################
                    
                    print ('3. Subsetting Checklists')
                    #Get sampling effort within the alphahull
                    Cckl_spp=gpd.sjoin(se_df,alphahull,'inner','intersects').reset_index(drop=True) #Get Checklists within alpha hull
                    
                    
                    if not Cckl_spp.empty:
                        
                        Cckl_spp=Cckl_spp.drop('index_right', axis=1) #Get rid of undesired column
                        Cckl_spp.to_file(Cckl_spp_dir, driver='ESRI Shapefile', encoding = 'utf-8') #Save new ChecklistsCckl_spp_hab=  #Checklists in habitat path file
                        arcpy.SpatialJoin_analysis(Cckl_spp_dir, AOH_shp, Cckl_spp_hab_dir, 
                                                   '', 'KEEP_COMMON', '', 'INTERSECT', float(cs)) # Intersecting checklists within a radius distance of the cell size of habitat
                        Cckl_spp_hab2=gpd.read_file(Cckl_spp_hab_dir) #Checklists intersected
                        
                        #Create grid feature with Habitat raster as extent
                        Cckl_spp_grid=gpd.sjoin(g,Cckl_spp_hab2,'inner','intersects').reset_index(drop=True)
                        Cckl_spp_grid['Count'] = Cckl_spp_grid.groupby('PageName')['PageName'].transform('count')
                        #Get squares with more than 25 checklists
                        Cckl_spp_grid25=Cckl_spp_grid[Cckl_spp_grid.Count>=25]
                        Cckl_spp_grid25=Cckl_spp_grid25.drop('index_right', axis=1) #Get rid of undesired column
                        Cckl_spp_grid25=Cckl_spp_grid25.drop_duplicates('PageName')
                        #Get squares with presences
                        Cckl_25inpres= gpd.sjoin(Cckl_spp_grid25,presences,'inner','intersects').reset_index(drop=True)
                        #Get squares with no presences - non detection areas
                        Cckl_25outpres=(Cckl_spp_grid25[~Cckl_spp_grid25.PageName.isin(Cckl_25inpres.PageName)])
                        
                        #If absences, convert squares to points. These will be used for interpolation
                        if not Cckl_25outpres.empty:
                            Cckl_25outpres.to_file(Non_detection, driver='ESRI Shapefile', encoding = 'utf-8')
                            Cckl_25outpres_copy=Cckl_25outpres.copy()
                            Cckl_25outpres_copy.geometry=Cckl_25outpres.geometry.centroid
                            Cckl_25outpres_copy.to_file(Absences, driver='ESRI Shapefile', encoding = 'utf-8')
                            
                            #Get Checklists from Non_detection pixels
                            Select_abs=arcpy.SelectLayerByLocation_management(Cckl_spp_hab_dir, 'INTERSECT', Non_detection)
                            arcpy.CopyFeatures_management(Select_abs, Chcklists_pixel)
                            
                            #Reading absences
                            Abs=Cckl_25outpres_copy[['PageName','PageNumber','ID','Count','geometry']]
                            Abs=Abs.drop_duplicates()
                            Abs_r=len(Abs)
                                
                    if  Cckl_spp.empty or Cckl_25outpres.empty:
                        print('No Absences')
                        Abs_r=None
                        PO_AOH_area=None
                        AU_AOH_area=None
                        
                
                    else:
                        presences['ID']=0
                        Pres=presences[['ID','geometry']]
                        Pres_Abs=pd.concat([Abs,Pres])
                        Pres_Abs.to_file(Pres_Abs_path, driver='ESRI Shapefile', encoding = 'latin1')
                        
                        ######################################################################
                        ######################## INTERPOLATION ###############################
                        ######################################################################
                        
                        print ('4. Interpolating')
                        arcpy.env.extent = AOH_path
                        #Use IDW interpolation to get AUAOHs and POAOHs within the AOHs
                        IDW=arcpy.Idw_3d(Pres_Abs_path, 'ID', idw_spp, AOH_path, 1, 'VARIABLE 1')
                        
                        IDW_array=rasterio.open(IDW[0]).read().astype(int)
                       
                        #Apparently Unoccupied AOH early
                        Unoccupied_AOH= IDW_array*AOH
                        with rasterio.open(
                                Unoccupied_AOH_spp,
                                'w', driver='GTiff',
                                height=Unoccupied_AOH.shape[1],width=Unoccupied_AOH.shape[2],
                                count=1,dtype=str(Unoccupied_AOH.dtype),
                                crs=epsg_WGS84,transform=affine, nodata=0
                                ) as new_dataset:
                            new_dataset.write(Unoccupied_AOH)
                        new_dataset.close()
                        
                
                        size_AU_AOH= len(Unoccupied_AOH[Unoccupied_AOH==1])
                        AU_AOH_area=round((size_AU_AOH*proj**2)*m2)
                        
                        #Potentially Occupied AOH Early
                        Potential_AOH= AOH-Unoccupied_AOH
                        with rasterio.open(
                                Potential_AOH_spp,
                                'w', driver='GTiff',
                                height=Potential_AOH.shape[1],width=Potential_AOH.shape[2],
                                count=1,dtype=str(Potential_AOH.dtype),
                                crs=epsg_WGS84,transform=affine, nodata=0
                                ) as new_dataset:
                            new_dataset.write(Potential_AOH)
                        new_dataset.close()
                        
                        size_PO_AOH= len(Potential_AOH[Potential_AOH==1])
                        PO_AOH_area=round((size_PO_AOH*proj**2)*m2)
                        
                    ######################################################################
                    ######################## END 1 #######################################
                    ######################################################################
                else:
                    print('No Absences')
                    Abs_r=None
                    PO_AOH_area=None
                    AU_AOH_area=None
            
            
            else:
                print('No Presences')
                bl_path= bl + c + "_BL.shp"
                alphahull = gpd.read_file(bl_path)
                
                if not aoi.empty:
                    AOI = gpd.clip(alphahull, aoi)
                
                print ('1. Refining Habitat')
                #mask forest raster by species alphahull
                TreeCover= forest_api(hull= AOI, generate=True)
                
                TC_in_hull=TreeCover[1]
                array= TC_in_hull[0] #get the array, a matrix of raster values
                affine= TC_in_hull[1] #get info from the raster
                #Forest trimmed by a threshold within the alphahull
                TC_by_spp=(array>0).astype(int) #subset the array after a condition
                
                print ('2. Elevation')
                Min=int(round(df['elevation_lower'][b]))
                Max=int(round(df['elevation_upper'][b]))
                
                #mask elevation raster by species alphahull
                ElevT=elevation_tiles(hull=AOI, interv=3, res='SRTMGL1', 
                                      API_key='4efc9ca7ccb3b61ac67e964b14b6c820',
                                      transform=affine, generate=True)
                           
                
                E_in_hull=ElevT[1]
                array_E= E_in_hull[0].astype(int) #get the array, a matrix of raster values
                
                if array.size!=array_E.size:
                    height=array.shape[1]-array_E.shape[1]
                    width=array.shape[2]-array_E.shape[2]
                    array_E = np.pad(array_E, ((0, 0), (0, height), (0, width)), mode='constant')
     
                
                E_by_spp= ((array_E<Max) & (array_E>Min)).astype(int)
                
                
                #Habitat 2000
                AOH_path=output1
                AOH= TC_by_spp*E_by_spp
                
                size_raster=len(AOH[AOH==1])
                AOH_area=round((size_raster*proj**2)*m2) 
                
                
                with rasterio.open(
                        AOH_path,
                        'w', driver='GTiff',
                        height=AOH.shape[1],width=AOH.shape[2],
                        count=1,dtype=str(AOH.dtype),
                        crs=epsg_WGS84,transform=affine, nodata=0
                        ) as new_dataset:
                    new_dataset.write(AOH)
                new_dataset.close()
                
                
                
                TC_threshold= None
                Forest_Species= None
                GD= None
                Abs_r= None
                PO_AOH_area=  None
                AU_AOH_area=None
                number_presences= None
            #SAVING DATA TO A REPORT TABLE AND EXPORT TO CSV
            report_Habitat.append([c,
                                   AOH_area, 
                                   PO_AOH_area,
                                   AU_AOH_area,
                                   TC_threshold,Forest_Species,GD,Abs_r,
                                   number_presences, Min,Max])
            Report_Table=pd.DataFrame(report_Habitat,columns=['Scientific Name',
                                                              'Area of Habitat (Km\u00b2)',
                                                              'Potential AOH (Km\u00b2)',
                                                              'Unnocupied AOH (Km\u00b2)',
                                                              'Forest Threshold', 'Forest Species',
                                                              'Geographical Distribution','Abs',
                                                              'Presence Records', 'Lower Elev', 'Upper Elev'])
            Report_Table.to_csv(Report,encoding='latin-1', index=False)
            print('******* ' + c +' ******* done!\n')
            arcpy.ResetEnvironments()
            
        
                
            
        except ValueError as e:
            report_Errors.append([c,e])
            RErrors=pd.DataFrame(report_Errors,columns=['Scientific Name','Error'])
            RErrors.to_csv(errors,encoding='latin-1', index=False)
    print ('Complete!')
    return Report_Table
    
        
    


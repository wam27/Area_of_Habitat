# -*- coding: utf-8 -*-
"""
Created on Wed Jan  3 22:18:10 2024
@author: Wilderson Medina
Duke University
wildersonmb@gmail.com

"""
#Get elevation values from the Open Topography website.
#This tool relies on the elevation_tiles function wich provides a list of raster datasets retrieved from https://portal.opentopography.org/apidocs/#/Public/getGlobalDem.
#For each dataset, elevation is sampled using point coordinates and stored in the same dataframe.

import pandas as pd
from rasterio.sample import sample_gen

def extract_elevation(datasets, points):
    
    #Store point coordinates in a list
    coords = [(x,y) for x, y in zip(points.LONGITUDE, points.LATITUDE)] # Read points from shapefile
    
    #Create an empty list where points per dataset will be temporay stored
    elevation_list=[]
    
    #Loop over each dataset to extract values to points
    for d in datasets:
        
        # Get the generator for sampling
        sample_generator = sample_gen(d, coords)
        
        # From the generator extract elevation values and their coordinates
        for (x, y), values in zip(coords, sample_generator):
            row, col = d.index(x, y)
            v_points= pd.DataFrame(data={'LONGITUDE': [x], 'LATITUDE':[y], 'Elevation': [values[0]]})
            
            #Append each set of points per dataset in the created list
            elevation_list.append(v_points)
    
    #Concatenate all lists in a single dataframe, remove no data values and duplicates generated in the above proccess     
    elev_total=pd.concat(elevation_list,ignore_index=True, sort=False)
    elev_total = elev_total[elev_total.Elevation>=0]
    elev_total.sort_values(['LATITUDE','LONGITUDE','Elevation'], inplace=True)
    elev_total=elev_total.drop_duplicates(['LATITUDE','LONGITUDE'], keep='last').reset_index(drop=True)
    
    #Add elevation values based on coordinates in the point dataframe
    points2=points.merge(elev_total, left_on=['LONGITUDE','LATITUDE'], right_on=['LONGITUDE','LATITUDE'])
        
    return points2  
   

   
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  4 02:01:45 2024
@author: Wilderson Medina
Duke University
wildersonmb@gmail.com

"""

#Get forest percentages from the Hansen tree cover dataset.
#This tool depends on the forest_api function wich provides a list of raster datasets retrieved from the earth engine partners website.
#For each dataset, tree cover percentages are sampled using point coordinates and stored in the same dataframe.

import pandas as pd
from rasterio.sample import sample_gen


def extract_forest(datasets, points):
    #Store point coordinates in a list
    coords = [(x,y) for x, y in zip(points.LONGITUDE, points.LATITUDE)] # Read points from shapefile
    
    #Create an empty list where points per dataset will be temporay stored
    forest_list=[]
    
    #Loop over each dataset to extract values to points
    for d in datasets:
        # Get the generator for sampling. This sampling tool gets the associated coordinates for every point and allows for easy storage in a new dataframe
        sample_generator = sample_gen(d, coords)
        
        # From the generator extract tree cover values and their coordinates
        for (x, y), values in zip(coords, sample_generator):
            row, col = d.index(x, y)
            v_points= pd.DataFrame(data={'LONGITUDE': [x], 'LATITUDE':[y], 'Tree_Cover': [values[0]]})
            #Append each set of points per dataset in the created list
            forest_list.append(v_points)
    
    #Concatenate all lists in a single dataframe, remove no data values and duplicates generated in the previous proccess    
    forest_total=pd.concat(forest_list,ignore_index=True, sort=True)
    forest_total = forest_total[forest_total.Tree_Cover>=0]
    forest_total.sort_values(['LATITUDE','LONGITUDE','Tree_Cover'], inplace=True)
    forest_total=forest_total.drop_duplicates(['LATITUDE','LONGITUDE'], keep='last').reset_index(drop=True)
    
    #Add tree cover percentages based on coordinates in the point dataframe
    points2=points.merge(forest_total, left_on=['LONGITUDE','LATITUDE'], right_on=['LONGITUDE','LATITUDE'])
    
    
    return points2 
   

   
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 30 12:15:00 2023
@author: Wilderson Medina
Duke University
wildersonmb@gmail.com

"""
#Get elevation tiles of variable size from an API.
#The resolution can be 30 m (SRTMGL1) or 90 m (SRTMGL3). The function requires an area of interest defined by the extent of a polygon.
#See details on maximum extent size allowed for each type of resolution in https://portal.opentopography.org
#The interval that divides the extent in a grid of equal parts. Suggested between 1 and 10.
#And an API key that can be obtained from https://portal.opentopography.org

import geopandas as gpd
import rasterio
import numpy as np
from io import BytesIO
from shapely.geometry import Polygon
from urllib import request
from rasterio.merge import merge
from rasterio import mask


report_errors = []
epsg_WGS84= 4326

def elevation_tiles(hull, interv, res, API_key, transform=None, generate=False):
   
    print ('Preparing DEM!')
    #Get the bounding box from polygon shapefile    
    bbox= hull.bounds
        
    minX=int(np.floor(bbox.minx.iloc[0]))
    minY=int(np.floor(bbox.miny.iloc[0]))
    maxX=int(np.ceil(bbox.maxx.iloc[0]))
    maxY=int(np.ceil(bbox.maxy.iloc[0]))
    
    # Generate lists of latitude and longitude values
    latitudes = list(range(maxY, minY, -interv))
    longitudes = list(range(minX, maxX, interv))
    
    # Generate square polygons and create a GeoDataFrame
    squares = []
    for lat in latitudes:
        for lon in longitudes:
            # Define the vertices of the square
            square_vertices = [
                (lon, lat),
                (lon + interv, lat),
                (lon + interv, lat - interv),
                (lon, lat - interv),
                (lon, lat),  # Closing the square
            ]
    
            # Create a Polygon geometry
            square_geometry = Polygon(square_vertices)
    
            # Append to the list
            squares.append(square_geometry)
            
    # Create GeoDataFrame
    gdf_squares = gpd.GeoDataFrame(geometry=squares)
    gdf_squares.crs = "EPSG:4326"
    
    #Get only those squares intersecting the polygon
    df_in_box=gpd.sjoin(hull,gdf_squares,'inner','intersects') #Get Checklists within alpha hull
    unique_indices = list(set(df_in_box.index_right))
    
    #Iterate over the intersectign polygons to get the raster within
    datasets = []
    for b in unique_indices:
        try:
            #Get bounding box of each square
            gdf_sq= gdf_squares.iloc[[b]]
            bbox2= gdf_sq.bounds
            
            minX2=int(np.floor(bbox2.minx.iloc[0]))
            minY2=int(np.floor(bbox2.miny.iloc[0]))
            maxX2=int(np.ceil(bbox2.maxx.iloc[0]))
            maxY2=int(np.ceil(bbox2.maxy.iloc[0]))
            
            #Access data from the API. The resolution can be either 30 m or 90 m
            URL = 'https://portal.opentopography.org/API/globaldem?demtype='+res+'&south='+str(minY2)+'&north='+str(maxY2)+'&west='+str(minX2)+'&east='+str(maxX2)+'&outputFormat=GTiff&API_Key='+API_key
            r = request.urlopen(URL)
            tif_bytes = BytesIO(r.read())
            
            # Open the raster file with rasterio
            raster= rasterio.open(tif_bytes)
            
            #datasets is a list of all raster datasets intersecting the polygon
            datasets.append(raster)
            
        except Exception as e:
            report_errors.append([e])
    #Create a single raster by merging the raster datasets and clip it by the polygon      
    
    if generate:
        if len(datasets)>1:
            print ('       Generating DEM!')
            mosaic, out_trans = merge(datasets)
            
    
            # Update metadata of the merged dataset
            out_meta = datasets[0].meta.copy()
            out_meta.update({'driver': 'GTiff',
                             'height': mosaic.shape[1],
                             'width': mosaic.shape[2],
                             'transform': transform,
                             'count': 1,
                             'dtype': str(mosaic.dtype)})
            
            
            with rasterio.MemoryFile() as memfile:
                with memfile.open(**out_meta) as dat:
                    dat.write(mosaic)
                    #Clip by the polygon
                    dem_in_gdf=mask.mask(dat,hull.geometry, crop=True, pad=False)
        else:
            
            dem_in_gdf=mask.mask(raster,hull.geometry, crop=True, pad=False)

                        
        # The output of generate will be a list of raster datasets and the merged version cliped by the polygon shapefile
        return datasets, dem_in_gdf
    
    #If not generate then produce the list of raster datasets
    return datasets
                
       

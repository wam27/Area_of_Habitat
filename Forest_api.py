# -*- coding: utf-8 -*-
"""
Created on Wed Dec 27 13:13:08 2023
@author: Wilderson Medina
Duke University
wildersonmb@gmail.com

"""

#Read and generate tree cover raster from a list of datasets retrieved from https://earthenginepartners.appspot.com/science-2013-global-forest/download_v1.7.html
#This tools uses a bounding box provided by a polygon shapefile and identify and read all raster datasets intersecting the shapefile.
#After getting the datasets, it is possible to extract tree cover percentages using the forest_extract function.
#Alternatively, the user can generate a merged dataset that results in the mosaicking of the dataset list within the shapefile boundaries.
#It is recommended to use the forest_api function to get the datasets, then use the extract_forest function to get tree cover percentages from coordinates.
#It is also very important to consider that the merged raster do not exceed certain size given some memory limitations of the PC.


import geopandas as gpd
from shapely.geometry import Polygon
import rasterio
from urllib import request
from io import BytesIO
from rasterio.merge import merge
from rasterio import mask


epsg_WGS84= 4326

def forest_api(hull, generate=False):
    print ('Preparing Tree Cover!')
    
    #Get bounding box from shapefile
    bbox= hull.bounds
    minX = int((bbox.minx.iloc[0] // 10) * 10)
    minY = int((bbox.miny.iloc[0] // 10) * 10)
    maxX = int(((bbox.maxx.iloc[0] - 1) // 10 + 1) * 10)
    maxY = int(((bbox.maxy.iloc[0] - 1) // 10 + 1) * 10)
    
    # Define the intervals for latitude and longitude
    interv= 10
    
    # Generate lists of latitude and longitude values
    latitudes = list(range(minY, maxY+1, interv))
    longitudes = list(range(minX, maxX+1, interv))
    
    # Generate square polygons to create a grid and create a GeoDataFrame
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
    
    # Create GeoDataFrame to store the geometries for each square
    gdf_squares = gpd.GeoDataFrame(geometry=squares)
    gdf_squares.crs = "EPSG:4326"
    
    #Count number of unique squares
    unique_indices = list(set(gdf_squares.index))
    
    #Get tree cover raster datasets from the API
    report_errors=[]
    datasets=[]
    for l in unique_indices:
        try:
            #Define the upper right coordinates of each square
            bb=gdf_squares.iloc[[l]]
            bb2=bb.bounds
            bb_minX= abs(int(bb2.minx.iloc[0]))
            bb_maxY= abs(int(bb2.maxy.iloc[0]))
            
            if int(bb2.minx.iloc[0])<0:
                dx= 'W'
            else:
                dx= 'E'
            if int(bb2.maxy.iloc[0])<0:
                dy= 'S'
            else:
                dy= 'N'
                
            #Access the API by using the above coordinates and directions. No key required
            URL = 'https://storage.googleapis.com/earthenginepartners-hansen/GFC-2019-v1.7/Hansen_GFC-2019-v1.7_treecover2000_'+str(bb_maxY)+dy+'_0'+str(bb_minX)+dx+'.tif'
            r = request.urlopen(URL)
            tif_bytes = BytesIO(r.read())
            
            # Open the raster file with rasterio
            raster= rasterio.open(tif_bytes)
            datasets.append(raster)
                    
        except Exception as e:
            report_errors.append([e])
    #Option to merge all datasets in a single raster        
    if generate:
        print ('       Generating Tree Cover!')
        # Merge the datasets into a single rasterio dataset
        mosaic, out_trans = merge(datasets)
        
        # Update metadata of the merged dataset
        out_meta = datasets[0].meta.copy()
        out_meta.update({'driver': 'GTiff',
                         'height': mosaic.shape[1],
                         'width': mosaic.shape[2],
                         'transform': out_trans,
                         'count': 1,
                         'dtype': str(mosaic.dtype)})
        
        
        with rasterio.MemoryFile() as memfile:
            with memfile.open(**out_meta) as dat:
                dat.write(mosaic)
                #mask dataset to the given polygon shapefile
                tc_in_gdf=mask.mask(dat,hull.geometry,crop=True, pad=False)
                
        # The output of generate will be a list of raster datasets and the merged version cliped by the polygon shapefile        
        return datasets, tc_in_gdf
    #If not generate then produce the list of raster datasets
    return datasets


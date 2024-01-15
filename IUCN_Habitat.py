# -*- coding: utf-8 -*-
"""
Created on Tue Mar  2 19:00:31 2021

@author: wam27
"""

import pandas as pd
import os, arcpy
from arcpy import env
import arcpy.sa
import requests
import json
pd.options.mode.chained_assignment = None
import warnings
#import dill
warnings.filterwarnings("ignore")


#Chek out ArcGis Analyst and allow overwrite files
arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Set relative paths
#scriptWS= os.path.basename(sys.argv[0])
rootWS= os.getcwd()
#rootWS= os.path.dirname(sys.path[0])
dataWS=os.path.join(rootWS, 'Data') #'data'
scratchWS=os.path.join(rootWS, 'Scratch')
docsWS=os.path.join(rootWS, 'Docs')

#Set work environment
env.workspace= dataWS

#Call variables
os.chdir(os.getcwd())

report_errors=[]
def Habitat(Species_df):
    Species=Species_df
    token='9bb4facb6d23f48efbf424bb05c0c1ef1cf6f468393bc745d42179ac4aca5fee'
    #Species_df.sort_values(Species_df.columns[0],inplace=True)
    for n in range(len(Species.iloc[:,0])):  #range(38,63): #  
        try:
            s=Species.iloc[:,0][n]
            if type(s) == float:
                Species.at[n, 'Suitable Habitat'] = ''
                Species.at[n, 'Major Habitat'] = ''
                continue
            else:
                print(s)
                #Find the habitat for each species
                name=s.replace(' ','%20')
                url_habitat='{}'.format('https://apiv3.iucnredlist.org/api/v3/habitats/species/name/'+name+'?token='+token)
                r=requests.get(url_habitat)  
                content=r.content
                output=json.loads(content)
                spp_habitat=pd.DataFrame(output['result'])
                if not spp_habitat.empty:
                    habitat=spp_habitat.loc[spp_habitat['suitability']=='Suitable','habitat']
                    habitat_suitable=habitat.str.cat(sep=', ')
                    Species.at[n, 'Suitable Habitat'] = habitat_suitable
                    
                    habitat_Major=spp_habitat['habitat']+ ' ('+spp_habitat['majorimportance']+ ')'
                    HMajor=habitat_Major.str.cat(sep=', ')
                    Species.at[n, 'Major Habitat'] = HMajor
                else:
                    Species.at[n, 'Suitable Habitat'] = ''
                    Species.at[n, 'Major Habitat'] = ''
                    continue
            
        except ValueError as e:
            report_errors.append([s,e])
            Errors=pd.concat(report_errors)
       # Report_Errors=pd.DataFrame(report_errors,columns=['Scientific Name','Error'])
    print ('Complete!')
    return Species, Errors

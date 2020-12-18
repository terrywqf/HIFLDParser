#!/usr/bin/env python
# coding: utf-8

# In[3]:


import pandas as pd
import numpy as np
import networkx as nx
import csv
import json
import os.path
import zipfile

Max_Value = 3000
Min_Value = 0
coord_precision = '.9f'

def get_Zone(Z_csv):
    zone = pd.read_csv(Z_csv)

    # Create dictionary to store the mapping of states and codes
    zone_dic={}
    for i in range(len(zone)):
        zone_dic[zone['STATE'][i]]=zone['ID'][i]
    return zone_dic


# Clean data; throw substations which are outside the United States and not available.
def Clean(E_csv,zone_dic):
    csv_data = pd.read_csv(E_csv)
    Num_sub = len(csv_data)
    row_indexs = []
    for i in range(Num_sub):
        if((csv_data['STATE'][i] not in zone_dic) or (csv_data['STATUS'][i] != 'IN SERVICE') or (csv_data['LINES'][i] == 0)):
            row_indexs.append(i)
    clean_data = csv_data.drop(labels = row_indexs)
    return clean_data

def Clean_p(P_csv):
    csv_data = pd.read_csv(P_csv)
    Num_sub = len(csv_data)
    row_indexs = []
    for i in range(Num_sub):
        if(csv_data['STATUS'][i] != 'OP'):
            row_indexs.append(i)
    clean_data = csv_data.drop(labels = row_indexs)
    return clean_data

def LocOfsub(clean_data):
    LocOfsub_dict = {}
    ZipOfsub_dict = {}
    for index, row in clean_data.iterrows():
        loc = (format(row['LATITUDE'], coord_precision),format(row['LONGITUDE'], coord_precision))
        sub = row['ID']
        zi = row['ZIP']
        LocOfsub_dict[loc] = sub
        ZipOfsub_dict[zi] = sub
    return LocOfsub_dict, ZipOfsub_dict

def Cal_P(G_csv):
    Pmin = {}
    csv_data = pd.read_csv(G_csv)
    for index, row in csv_data.iterrows():
        Pmin[str(row["Plant Name"]).upper()] = row["Minimum Load (MW)"]
    return Pmin

def write_plant(clean_data,ZipOfsub_dict):
    plant = open('plant.csv','w',newline='')
    csv_writer = csv.writer(plant)
    csv_writer.writerow(["plant_id","bus_id","Pg","status","Pmax","Pmin","ramp_30","type"])
    for index, row in clean_data.iterrows():
        if(row['PLANT'] in Pmin):
            if(row['ZIP'] in ZipOfsub_dict):
                bus_id = ZipOfsub_dict[row['ZIP']]
            else:
                bus_id = 0
            pmax = min(row['SUMMER_CAP'],row['WINTER_CAP'])
            pmin = Pmin[row['PLANT']]
            csv_writer.writerow([row['PLANT']+'-'+row['NAME']+'-'+row['ZIP'],bus_id, 1, "OP", pmax,pmin,pmin,type_dict[row['TYPE']]])
        elif(row['ZIP'] in ZipOfsub_dict):
            bus_id = ZipOfsub_dict[row['ZIP']]
            pmax = min(row['SUMMER_CAP'],row['WINTER_CAP'])
            pmin = 0
            csv_writer.writerow([row['PLANT']+'-'+row['NAME']+'-'+row['ZIP'],bus_id, 1, "OP", pmax,pmin,pmin,type_dict[row['TYPE']]])
    plant.close()

def Write_gen(clean_data):
    gencost = open('gencost.csv','w',newline='')
    csv_writer = csv.writer(gencost)
    csv_writer.writerow(["plant_id","type","n","c2","c1","c0"])
    for index, row in clean_data.iterrows():
        csv_writer.writerow([row['PLANT']+'-'+row['NAME']+'-'+row['ZIP'],row['TYPE'],1,1,type_dict[row['TYPE']],0])
    gencost.close()

zone_dic = get_Zone("data/zone.csv")

clean_data = Clean("data/Electric_Substations.csv",zone_dic)
LocOfsub_dict, ZipOfsub_dict = LocOfsub(clean_data)
clean_data = Clean_p("data/General_Units.csv")
Pmin = Cal_P("data/Generator_Y2019.csv")

type_dict = {}
type_data = pd.read_csv("data/type.csv")
for index, row in type_data.iterrows():
    type_dict[row['TYPE']] = row['Type_code']

write_plant(clean_data, ZipOfsub_dict)
Write_gen(clean_data)


# In[ ]:





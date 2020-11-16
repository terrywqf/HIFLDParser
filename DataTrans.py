#!/usr/bin/env python
# coding: utf-8


import pandas as pd
import numpy as np
import networkx as nx
import csv
import json
import os.path
import zipfile

Max_Value = 3000
Min_Value = 0

def get_Zone(Z_csv):
    zone=pd.read_csv(Z_csv)

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



#Create dictionary to store neighbors of each sub
def Neighbors(subs):
    N_dict={}
    nodes=[]
    if not os.path.isfile('data/Electric_Power_Transmission_Lines.geojson'):
        with zipfile.ZipFile('data/Electric_Power_Transmission_Lines.geojson.zip', 'r') as zip_ref:
            zip_ref.extractall('data/')
    with open('data/Electric_Power_Transmission_Lines.geojson','r',encoding='utf8')as fp:
        data = json.load(fp)
    for i in range(len(data['features'])):
        sub1 = (data['features'][i]['properties'][ 'SUB_1'],format(data['features'][i]['geometry'][ 'coordinates'][0][0][1], '.3f'),format(data['features'][i]['geometry'][ 'coordinates'][0][0][0], '.3f'))
        sub2 = (data['features'][i]['properties'][ 'SUB_2'],format(data['features'][i]['geometry'][ 'coordinates'][0][-1][1], '.3f'),format(data['features'][i]['geometry'][ 'coordinates'][0][-1][0], '.3f'))
   #     if((sub1 not in subs) or (sub2 not in subs)):
   #         continue
        if(sub1 in N_dict):
            N_dict[sub1].append(sub2)
        else:
            nodes.append(sub1)
            N_dict[sub1] = [sub2]
        if(sub2 in N_dict):
            N_dict[sub2].append(sub1)
        else:
            nodes.append(sub2)
            N_dict[sub2] = [sub1]
    return nodes, N_dict

#create the graph for our Power Network
def GraphOfNet(nodes, N_dict):
    G = nx.Graph()
    for node in nodes:
        G.add_node(node)

    for key in N_dict:
        for value in N_dict[key]:
            G.add_edge(key, value)

    return G

#Find the biggest islands, only used to test at present
def GetMaxIsland(G):
    Max_nodeSet = []
    Max_size = 0
    #list1 = []
    num = 0
    for c in nx.connected_components(G):
        num = num +1
        nodeSet = G.subgraph(c).nodes()
        size = len(nodeSet)
        #list1.append(size)
        if(size > Max_size):
            Max_nodeSet = nodeSet
            Max_size = size
    #list1.sort(reverse=True)
    return Max_nodeSet

#Calculate the base_KV for each node, save the nodes to be calculated

def InitKV(clean_data):
    KV_dict = {}
    to_cal = []
    Max_Value = 3000
    Min_Value = 0
    for index, row in clean_data.iterrows():
        base_KV = -999999.0
        Min_Vol = row['MIN_VOLT']
        Max_Vol = row['MAX_VOLT']
        if(Min_Vol >= Max_Value or Min_Vol <= Min_Value):
            if(Max_Vol < Max_Value and Max_Vol > Min_Value):
                base_KV = Max_Vol
            else:
                to_cal.append((row['NAME'],format(row['LATITUDE'], '.3f'),format(row['LONGITUDE'], '.3f')))
                continue
        else:
            if(Max_Vol<Max_Value and Max_Vol>Min_Value):
                base_KV = (Max_Vol + Min_Vol)/2
            else:
                base_KV = Min_Vol
        KV_dict[(row['NAME'],format(row['LATITUDE'], '.3f'),format(row['LONGITUDE'], '.3f'))] = base_KV
    return KV_dict, to_cal

# Give a node, find its neighbors in 5 iteration

def get_neigbors(g, node, depth=1):
    output = {}
    layers = dict(nx.bfs_successors(g, source=node, depth_limit=depth))
    nodes = [node]
    for i in range(1,depth+1):
        output[i] = []
        for x in nodes:
            output[i].extend(layers.get(x,[]))
        nodes = output[i]
    return output

# Estimate KV using neighbors

def Cal_KV(N_dict,G,KV_dict,to_cal):
    for sub in to_cal:
        if(sub not in N_dict):
            continue
        neigh = get_neigbors(G,sub,depth=5)
        temp_KV = 0
        num = 0
        for i in range(1,6):
            for nei in neigh[i]:
                if(nei in KV_dict):
                    temp_KV = temp_KV + KV_dict[nei]
                    num = num + 1
            if(num > 0):
                KV_dict[sub] = temp_KV / num
                continue
            else:
                KV_dict[sub] = -999999
    return KV_dict
    

# Write sub.csv
def Write_sub(clean_data,zone_dic):
    sub = open('output/sub.csv','w',newline='')
    csv_writer = csv.writer(sub)
    csv_writer.writerow(["sub_id","sub_name","lat","lon","zone_id","type"])
    for index, row in clean_data.iterrows():
        csv_writer.writerow([row['ID'],row['NAME'],row['LATITUDE'],row['LONGITUDE'],zone_dic[row['STATE']],row['TYPE']])
    sub.close()


#Write bus.csv
def Write_Bus(clean_data,zone_dic,KV_dict):
    bus = open('output/bus.csv','w',newline='')
    csv_writer = csv.writer(bus)
    csv_writer.writerow(["Bus_id","PD","Zone_id","base_KV"])
    for index, row in clean_data.iterrows():
        sub =(row['NAME'],format(row['LATITUDE'], '.3f'),format(row['LONGITUDE'], '.3f'))
        if(sub in KV_dict):
            csv_writer.writerow([row['ID'],0,zone_dic[row['STATE']],KV_dict[sub]])
        else:
            print(sub)
    bus.close()


#Write bus2sub.csv
def Write_bus2sub(clean_data):
    bus2sub = open('output/bus2sub.csv','w',newline='')
    csv_writer = csv.writer(bus2sub)
    csv_writer.writerow(["Bus_id","sub_id"])
    for index, row in clean_data.iterrows():
        csv_writer.writerow([row['ID'],row['ID']])
    bus2sub.close()


def DataTransform(E_csv,T_csv,Z_csv):

    zone_dic = get_Zone(Z_csv)

    clean_data = Clean(E_csv,zone_dic)

    #Have not decided how to define subs. I will encapsulate it later.
    subs=[(0,0,0)]
    for index, row in clean_data.iterrows():
        tuple=(row['NAME'],format(row['LATITUDE'], '.3f'),format(row['LONGITUDE'], '.3f'))
        subs.append(tuple)
        
    nodes, N_dict = Neighbors(subs)
    G = GraphOfNet(nodes, N_dict)
    KV_dict,to_cal = InitKV(clean_data)
    KV_dict = Cal_KV(N_dict,G,KV_dict,to_cal)
    
        
    Write_sub(clean_data,zone_dic)
    Write_Bus(clean_data,zone_dic,KV_dict)
    Write_bus2sub(clean_data)

if __name__ == '__main__':
    DataTransform("data/Electric_Substations.csv","data/Electric_Power_Transmission_Lines.csv","data/zone.csv")


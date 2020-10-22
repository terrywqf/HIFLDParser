#!/usr/bin/env python
# coding: utf-8


import pandas as pd
import numpy as np
import csv
Max_Value=3000
Min_Value=0

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
    Num_sub=len(csv_data)
    row_indexs=[]
    for i in range(Num_sub):
        if((csv_data['STATE'][i] not in zone_dic) or (csv_data['STATUS'][i] != 'IN SERVICE') ):
            row_indexs.append(i)
    clean_data=csv_data.drop(labels=row_indexs)
    return clean_data



#Create dictionary to store neighbors of each sub
def Neighbors(T_csv):
    Trans_data = pd.read_csv(T_csv, usecols=['VOLTAGE','SUB_1','SUB_2'])
    N_dict={}
    for i in range(len(Trans_data)):
        if(Trans_data['SUB_1'][i] in N_dict):
            N_dict[Trans_data['SUB_1'][i]].append(Trans_data['SUB_2'][i])
        else:
            N_dict[Trans_data['SUB_1'][i]]=[Trans_data['SUB_2'][i]]
        if(Trans_data['SUB_2'][i] in N_dict):
            N_dict[Trans_data['SUB_2'][i]].append(Trans_data['SUB_1'][i])
        else:
            N_dict[Trans_data['SUB_2'][i]]=[Trans_data['SUB_1'][i]]
    return N_dict

#Calculate the base_KV for each node

def cal_KV(clean_data,N_dict):
    KV_dict={}   # store base_KV of each node
    to_cal=[]  # store nodes needed to be calculated
   
    for index, row in clean_data.iterrows():
        base_KV=-999999.0
        Min_Vol=row['MIN_VOLT']
        Max_Vol=row['MAX_VOLT']
        if(Min_Vol>=Max_Value or Min_Vol<=Min_Value): # only values between 0 to 3000 are valid
            if(Max_Vol<Max_Value and Max_Vol>Min_Value):
                base_KV=Max_Vol
            else:
                to_cal.append(row['NAME'])
                continue
        else:
            if(Max_Vol<Max_Value and Max_Vol>Min_Value):
                base_KV=(Max_Vol+Min_Vol)/2
            else:
                base_KV=Min_Vol
        KV_dict[row['NAME']]=base_KV

     #Go through to_cal repeatedly until it doesn;t change  
    length=100000
    while(len(to_cal)<length):
        length=len(to_cal)
        for sub in to_cal:
            temp_KV=0.0
            num=0
            if(sub not in N_dict):
                continue
            for nei in N_dict[sub]: #Calculate average base_KV of neighbors
                if(nei in KV_dict):
                    temp_KV=temp_KV+KV_dict[nei]
                    num=num+1
            if(num>0):
                KV_dict[sub]=temp_KV/num
                to_cal.remove(sub)
                
    #for nodes not connected to clean nodes, set the KV as -999999    
    for sub in to_cal:
        KV_dict[sub]=-999999

    return KV_dict

# Write sub.csv
def Write_sub(clean_data,zone_dic):
    sub = open('sub.csv','w',newline='')
    csv_writer = csv.writer(sub)
    csv_writer.writerow(["sub_id","sub_name","lat","lon","zone_id","type"])
    for index, row in clean_data.iterrows():
        csv_writer.writerow([row['ID'],row['NAME'],row['LATITUDE'],row['LONGITUDE'],zone_dic[row['STATE']],row['TYPE']])
    sub.close()


#Write bus.csv
def Write_Bus(clean_data,zone_dic,KV_dict):
    bus = open('bus.csv','w',newline='')
    csv_writer = csv.writer(bus)
    csv_writer.writerow(["Bus_id","PD","Zone_id","base_KV"])
    for index, row in clean_data.iterrows():
        csv_writer.writerow([row['ID'],0,zone_dic[row['STATE']],KV_dict[row['NAME']]])
    bus.close()


#Write bus2sub.csv
def Write_bus2sub(clean_data):
    bus2sub = open('bus2sub.csv','w',newline='')
    csv_writer = csv.writer(bus2sub)
    csv_writer.writerow(["Bus_id","sub_id"])
    for index, row in clean_data.iterrows():
        csv_writer.writerow([row['ID'],row['ID']])
    bus2sub.close()


def DataTransform(E_csv,T_csv,Z_csv):

    zone_dic=get_Zone(Z_csv)

    clean_data=Clean(E_csv,zone_dic)


    N_dict=Neighbors(T_csv)
    KV_dict=cal_KV(clean_data,N_dict)
    
        
    Write_sub(clean_data,zone_dic)
    Write_Bus(clean_data,zone_dic,KV_dict)
    Write_bus2sub(clean_data)

if __name__ == '__main__':
    DataTransform("Electric_Substations.csv","Electric_Power_Transmission_Lines.csv","zone.csv")


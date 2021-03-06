import pandas as pd
import numpy as np
import csv
from geopy.distance import geodesic

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

# Get the lattitude and longitude of sunstations, and the substations in the area of each zip code
def LocOfsub(clean_data):
    LocOfsub_dict = {}
    ZipOfsub_dict = {}
    for index, row in clean_data.iterrows():
        loc = (format(row['LATITUDE'], coord_precision),format(row['LONGITUDE'], coord_precision))
        sub = row['ID']
        zi = row['ZIP']
        LocOfsub_dict[sub] = loc
        if(zi in ZipOfsub_dict):
            list1 = ZipOfsub_dict[zi]
            list1.append(sub)
            ZipOfsub_dict[zi] = list1
        else:
            list1 = [sub]
            ZipOfsub_dict[zi] = list1
    return LocOfsub_dict, ZipOfsub_dict

# Calculate the Pmin for each plant
def Cal_P(G_csv):
    Pmin = {}
    csv_data = pd.read_csv(G_csv)
    for index, row in csv_data.iterrows():
        tu = (str(row["Plant Name"]).upper(),row['Energy Source 1'])
        Pmin[tu] = row["Minimum Load (MW)"]
    return Pmin

#Get the lattitude and longitude of plants 
def Loc_of_plant():
    loc_of_plant = {}
    csv_data = pd.read_csv("data/Power_Plants.csv")
    for index, row in csv_data.iterrows():
        loc = (format(row['LATITUDE'], coord_precision),format(row['LONGITUDE'], coord_precision))
        loc_of_plant[row['NAME']] = loc
    return loc_of_plant

def getCostCurve():
    points = {}
    csv_data = pd.read_csv("data/needs.csv")
    df = np.array(csv_data)
    cost = df.tolist()
    for pla in cost:
        name = (str(pla[0]).upper(), pla[4])
        points[name] = int(pla[13])
    return points

def Getregion():
    region = {}
    csv_data = pd.read_csv("data/needs.csv")
    df = np.array(csv_data)
    needs = df.tolist()
    for pla in needs:
        name = (str(pla[0]).upper(), pla[4])
        if (name not in region):
            if(pla[8][0:3] == 'ERC'):
                re = 'ERCOT'
            elif(pla[8][0:3] == 'WEC'):
                re = 'Western'
            else:
                re = 'Eastern'
            region[name] = re
    return region

def Plant_agg(clean_data,ZipOfsub_dict,loc_of_plant,LocOfsub_dict,Pmin,region,points):
    plant_dict = {}
  
    for index, row in clean_data.iterrows():
        tu = (row['PLANT'],row['PRIM_FUEL'])
        r = (row['PLANT'],row['NAME'])
        if(tu not in plant_dict):
            bus_id = ''
            pmin = ''
            if(tu in Pmin and row['PLANT'] in loc_of_plant):
                if(row['ZIP'] in ZipOfsub_dict):
                    min_d = 100000.0
                    min_s = ""
                    for value in ZipOfsub_dict[row['ZIP']]:
                    # calculate the distance between the plant and substations
                        if(geodesic(loc_of_plant[row['PLANT']],LocOfsub_dict[value]).m < min_d):
                            min_s = value
                            min_d = geodesic(loc_of_plant[row['PLANT']],LocOfsub_dict[value]).m
                    bus_id = value
                    pmin = Pmin[tu]
            # if this zip does not contain subs, we try to find subs in neighbor zip.
                else: 
                    zi = int(row['ZIP'])
                    for i in range(-5,6):
                        min_d = 100000.0
                        min_s = ""
                        if(str(zi+i) in Pmin and str(zi+i) in loc_of_plant):
                            for value in ZipOfsub_dict[str(zi+i)]:
                                if(geodesic(loc_of_plant[row['PLANT']],LocOfsub_dict[value]).m < min_d):
                                    min_s = value
                                    min_d = geodesic(loc_of_plant[row['PLANT']],LocOfsub_dict[value]).m
                    bus_id = value
                    pmin = 0
           
            pmaxwin = row['WINTER_CAP']
            pmaxsum = row['SUMMER_CAP']
            if(r in points):
                cur = points[r]
                re = region[r]
            else:
                cur = 0
                re = 'uncertain'
            list1 = [bus_id,pmaxwin,pmaxsum,pmin,cur,1,re]
            plant_dict[tu] = list1
        else:
            list1 = plant_dict[tu]
            list1[1] = list1[1] + row['WINTER_CAP']
            list1[2] = list1[2] + row['SUMMER_CAP']
            if(r in points):
                list1[4] = list1[4] + points[r]
                list1[5] = list1[5] + 1
            plant_dict[tu] = list1
    return plant_dict

def write_plant(plant_dict):
    plant = open('output/plant.csv','w',newline='')
    csv_writer = csv.writer(plant)
    csv_writer.writerow(["plant_id","bus_id","Pg","status","Pmax","Pmin","ramp_30","type","region"])
    for key in plant_dict:
        list1 = plant_dict[key]
        csv_writer.writerow([key[0]+'-'+key[1],list1[0], 1, "OP", min(list1[1],list1[2]),list1[3],list1[3],key[1],list1[6]])
    plant.close()

def Write_gen(plant_dict, type_dict):
    gencost = open('output/gencost.csv','w',newline='')
    csv_writer = csv.writer(gencost)
    csv_writer.writerow(["plant_id","type","n","c2","c1","c0"])
    for key in plant_dict:
        c1 = plant_dict[key][4]/plant_dict[key][5]
        csv_writer.writerow([key[0]+'-'+key[1],key[1],1,0,c1,0])
    gencost.close()

def Plant(E_csv, U_csv, G2019_csv):
    zone_dic = get_Zone("data/zone.csv")

    clean_sub = Clean(E_csv,zone_dic)
    LocOfsub_dict, ZipOfsub_dict = LocOfsub(clean_sub)
    loc_of_plant = Loc_of_plant()
    clean_data = Clean_p(U_csv)
    Pmin = Cal_P(G2019_csv)

    type_dict = {}
    type_data = pd.read_csv("data/type.csv")
    for index, row in type_data.iterrows():
        type_dict[row['TYPE']] = row['Type_code']
    region = Getregion()
    points = getCostCurve()
    plant_dict = Plant_agg(clean_data,ZipOfsub_dict,loc_of_plant,LocOfsub_dict,Pmin,region,points)
    write_plant(plant_dict)
    points = getCostCurve()
    Write_gen(plant_dict, type_dict)

if __name__ == '__main__':
    Plant("data/Electric_Substations.csv", "data/General_Units.csv","data/Generator_Y2019.csv")

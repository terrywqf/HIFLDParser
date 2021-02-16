import pandas as pd
import numpy as np
import csv
from geopy.distance import geodesic
from sklearn.linear_model import LinearRegression

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
        if(tu in Pmin):
            cur = Pmin[tu]
        else:
            cur = 0.0
        if(row["Minimum Load (MW)"] == ' '):
            row["Minimum Load (MW)"] == 0.0
        if(row["Energy Source 1"] == 'NUC'):
            if(float(row["Minimum Load (MW)"]) > 0.9*min(float(row["Summer Capacity (MW)"]),float(row["Winter Capacity (MW)"]))):
                Pmin[tu] = float(row["Minimum Load (MW)"]) + cur
            else:
                Pmin[tu] = 0.9*min(float(row["Summer Capacity (MW)"]),float(row["Winter Capacity (MW)"])) + cur
        else:
            Pmin[tu] = float(row["Minimum Load (MW)"]) + cur
    return Pmin

#Get the lattitude and longitude of plants 
def Loc_of_plant():
    loc_of_plant = {}
    csv_data = pd.read_csv("data/Power_Plants.csv")
    for index, row in csv_data.iterrows():
        loc = (format(row['LATITUDE'], coord_precision),format(row['LONGITUDE'], coord_precision))
        loc_of_plant[row['NAME']] = loc
    return loc_of_plant

def LP(x_train, y_train):
    model = LinearRegression()
    x_train = np.array(x_train)
    y_train = np.array(y_train)
    x_train = x_train.reshape(-1,1)
    y_train = y_train.reshape(-1,1)
    model.fit(x_train,y_train)
    score = model.score(x_train,y_train)
    c = model.intercept_
    m = model.coef_

    return m, score

def getCostCurve():
    points = {}
    csv_data = pd.read_csv("data/EIA923.csv")
    df = np.array(csv_data)
    cost = df.tolist()
    for pla in cost:
        name = (str(pla[3]).upper(), pla[14])
        if (name in points):
            x = points[name][0]
            y = points[name][1]
            for n in range(12):
                x[n] = x[n] + float(pla[n+79])
                y[n] = y[n] + float(pla[n+67])
            points[name] = (x,y)
        else:
            x = [0.0]*12
            y = [0.0]*12
            for n in range(12):
                x[n] = x[n] + float(pla[n+79])
                y[n] = y[n] + float(pla[n+67])
            points[name] = (x,y)
    return points
    
def Plant_agg(clean_data,ZipOfsub_dict,loc_of_plant,LocOfsub_dict,Pmin):
    plant_dict = {}
  
    for index, row in clean_data.iterrows():
        tu = (row['PLANT'],row['PRIM_FUEL'])
        if(tu not in plant_dict):
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
            list1 = [bus_id,pmaxwin,pmaxsum,pmin]
            plant_dict[tu] = list1
        else:
            list1 = plant_dict[tu]
            list1[1] = list1[1] + row['WINTER_CAP']
            list1[2] = list1[2] + row['SUMMER_CAP']
            plant_dict[tu] = list1
    return plant_dict

def write_plant(plant_dict):
    plant = open('output/plant.csv','w',newline='')
    csv_writer = csv.writer(plant)
    csv_writer.writerow(["plant_id","bus_id","Pg","status","Pmax","Pmin","ramp_30","type"])
    for key in plant_dict:
        list1 = plant_dict[key]
        csv_writer.writerow([key[0]+'-'+key[1],list1[0], 1, "OP", min(list1[1],list1[2]),list1[3],list1[3],key[1]])
    plant.close()

def Write_gen(plant_dict, points):
    gencost = open('output/gencost.csv','w',newline='')
    csv_writer = csv.writer(gencost)
    csv_writer.writerow(["plant_id","type","n","c2","c1","c0"])
    for key in plant_dict:
        if(key in points):
            m, score = LP(points[key][0],points[key][1])
            if(score > 0.95):
                csv_writer.writerow([key[0]+'-'+key[1],key[1],1,0,m[0][0],0])
            else:
                if(sum(points[key][0]) != 0.0):
                    csv_writer.writerow([key[0]+'-'+key[1],key[1],1,0,sum(points[key][1])/sum(points[key][0]),0])
                else:
                    csv_writer.writerow([key[0]+'-'+key[1],key[1],1,0,'none',0])
        else:
            csv_writer.writerow([key[0]+'-'+key[1],key[1],1,0,'none',0])
    gencost.close()

def Plant(E_csv, U_csv, G2019_csv):
    zone_dic = get_Zone("data/zone.csv")

    clean_sub = Clean(E_csv,zone_dic)
    LocOfsub_dict, ZipOfsub_dict = LocOfsub(clean_sub)
    loc_of_plant = Loc_of_plant()
    clean_data = Clean_p(U_csv)
    Pmin = Cal_P(G2019_csv)

    #type_dict = {}
    #type_data = pd.read_csv("data/type.csv")
    #for index, row in type_data.iterrows():
    #    type_dict[row['TYPE']] = row['Type_code']
    plant_dict = Plant_agg(clean_data,ZipOfsub_dict,loc_of_plant,LocOfsub_dict,Pmin)
    write_plant(plant_dict)
    points = getCostCurve()
    Write_gen(plant_dict, points)


if __name__ == '__main__':
    Plant("data/Electric_Substations.csv", "data/General_Units.csv","data/Generator_Y2019.csv")

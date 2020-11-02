#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd

def build_graph(T_csv):
    trans_data = pd.read_csv(T_csv, usecols=['SUB_1','SUB_2'])
    graph = {}
    for i in range(len(trans_data)):
        if (trans_data['SUB_1'][i] not in graph):
            graph[trans_data['SUB_1'][i]] = []
        graph[trans_data['SUB_1'][i]].append(trans_data['SUB_2'][i])
        if (trans_data['SUB_2'][i] not in graph):
            graph[trans_data['SUB_2'][i]] = []
        graph[trans_data['SUB_2'][i]].append(trans_data['SUB_1'][i])
    return graph

# BFS to detect island
def find_islands(graph):
    islands = []
    visited = set()
    for sub in graph:
        if sub in visited:
            continue
        island = [sub]
        queue = [sub]
        visited.add(sub)
        while queue:
            cur = queue.pop()
            neighbors = graph[cur]
            for neighbor in neighbors:
                if (neighbor in visited):
                    continue
                queue.append(neighbor)
                island.append(neighbor)
                visited.add(neighbor)
        islands.append(island)
    return islands


def islands_statistics(T_csv):
    graph = build_graph(T_csv)
    print('graph size: ' + str(len(graph)))
    islands = find_islands(graph)
    print('total islands number: ' + str(len(islands)))

    print('***************** Report *******************')
    islands.sort(key = len, reverse = True)
    for island in islands:
        print('island size: ' + str(len(island)) + ', ' + str(island))
    print('***************** Report End *******************')

if __name__ == '__main__':
    islands_statistics("Electric_Power_Transmission_Lines.csv")
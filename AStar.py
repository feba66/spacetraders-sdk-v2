from dataclasses import dataclass
from json import load
from math import sqrt
from numbers import Number
from typing import Optional


@dataclass
class AStarNode:
    name:str
    connections:list
    x:Optional[int]
    y:Optional[int]


@dataclass
class CostNode:
    name:str
    cost:Number
    path_cost: Optional[int]
    path: Optional[list]
    def __init__(self,name,cost,path_cost=None,path=None) -> None:
        self.name = name
        self.cost=cost
        self.path_cost =path_cost
        self.path = path

def heuristic(a,b):
        return sqrt((a.x-b.x)**2+(a.y-b.y)**2)/1.1

def nodefromlist(nodename: str, list: list):
    return [x for x in list if x.name == nodename][0]


def AStarSearch(departure: str, destination: str, network:list[AStarNode]):
    networknames = [n.name for n in network]
    goalnode = nodefromlist(destination, network)
    node = CostNode(departure, 0, 0, [departure])
    frontier = [node]  # letztes element hat kleinste pfadkosten
    explored = []
    while True:
        # print("Frontiers:")
        # for f in frontier:
        #     print(f)
        # print()
        if len(frontier) == 0:
            return -1
        node = frontier.pop()
        # print("Visit: "+str(node))
        nodeinfo = nodefromlist(node.name, network)
        if node.name == destination:
            return node
        explored.append(node.name)
        for action in nodeinfo.connections:
            if action.name in networknames:
                child = CostNode(action.name,action.cost+node.cost,
                                node.cost+action.cost+heuristic(nodefromlist(action.name, network),goalnode),
                                node.path+[action.name])
                #print("Child: "+str(child))
                if child.name not in explored and len([x for x in frontier if x.name == child.name]) < 1:
                    frontier.append(child)
                    frontier.sort(key=lambda x: x.path_cost, reverse=True)
                elif len([x for x in frontier if x.name == child.name and x.path_cost > child.path_cost]) > 0:
                    frontier.remove([x for x in frontier if x.name == child.name and x.path_cost > child.path_cost][0])#TODO sometimes errors
                    frontier.append(child)
                    frontier.sort(key=lambda x: x.path_cost, reverse=True)
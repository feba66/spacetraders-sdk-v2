from collections import defaultdict
from datetime import datetime
import os
import sys
import time
from zoneinfo import ZoneInfo
from objects import Extraction, Survey
sys.path.insert(1, './spacetraders-sdk-v2')
from api import SpaceTraders,FORMAT_STR



if __name__ == "__main__":
    st = SpaceTraders()
    # st.Status()

    # pprint(st.Register("feba662","ASTRO"))
    st.Login(os.getenv("TOKEN"))
    time.sleep(.3)
    st.cur.execute(
        """select * from surveys where symbol = 'X1-AD50-85905A'"""
    )
    st.conn.commit()
    surveys = [Survey(s[1],s[4],s[0],s[3],s[2],s[5]) for s in st.cur.fetchall() if s[5] > datetime(2023,6,5,12,12,50,0)]
    print(len(surveys))
    st.cur.execute(
        """select * from surveysdepleted"""
    )
    st.conn.commit()
    depleted = [(s[1],s[0]) for s in st.cur.fetchall() if s[0] > datetime(2023,6,5,12,12,50,0)]
    print(len(depleted))
    
    st.cur.execute(
        """select * from extractions where waypointsymbol = 'X1-AD50-85905A'"""
    )
    st.conn.commit()
    extractions = [(s[2],s[3],s[4],s[5]) for s in st.cur.fetchall() if s[5] > datetime(2023,6,5,12,12,50,0)]
    print(len(extractions))
    
    survs:dict[str,Survey] = {}
    dep_list = [d[0] for d in depleted]
    danger = []
    for s in surveys:
        if s.signature in dep_list:
            if s.signature in survs:
                danger.append(s.signature)
                print("DANGER")
            survs[s.signature]=s
    
    extractlist = defaultdict(list)
    
    for e in extractions:
        if e[2]:
            extractlist[e[2]].append((e[0],e[1]))
    sizes = defaultdict(dict[str,dict[int,int]])
    for d in depleted:
        dep = extractlist[d[0]]
        if d[0] in survs:
            s  =survs[d[0]]
            l = len(dep)
            if l in sizes[s.size]:
                sizes[s.size][l]+=1
            else:
                sizes[s.size][l]=1

    print(sizes)
    # lengths = defaultdict(int)
    # deposits = defaultdict(int)
    # size = defaultdict(int)
    # runtimes = defaultdict(int)
    # for s in surveys:
    #     for d in s.deposits:
    #         deposits[d]+=1
    #     lengths[len(s.deposits)]+=1
    #     size[s.size]+=1
    #     runtimes[round((s.expiration-s.timestamp).total_seconds()/10)*10]+=1
    # print(deposits)
    # print(lengths)
    # print(size)
    # l = [f"{k};{v}|" for k,v in runtimes.items()]
    # print(l)
    # i=0
    # while len(l)/100>i:
    #     print(l[0+i*100:99+i*100])
    #     i+=1
    # print()
    print()
from collections import defaultdict
from datetime import datetime
import os
import sys
import time
from zoneinfo import ZoneInfo
from objects import Survey
sys.path.insert(1, './spacetraders-sdk-v2')
from api import SpaceTraders,FORMAT_STR

import matplotlib.pyplot as plt


if __name__ == "__main__":
    st = SpaceTraders()
    # st.Status()

    # pprint(st.Register("feba662","ASTRO"))
    st.Login(os.getenv("TOKEN"))
    time.sleep(.3)
    # st.cur.execute(
    #     """select * from creditleaderboard where agentsymbol = 'FEBA66'
    #     order by timestamp"""
    # )
    # st.conn.commit()
    # credits = [s for s in st.cur.fetchall()]
    # plt.plot([c[2] for c in credits],[c[1] for c in credits])
    # # plt.plot([c[0] for c in credits[1:]],[(c[2]-credits[i][2])/(c[0]-credits[i][0]).total_seconds() for i,c in enumerate(credits[1:])])
    
    # plt.ylabel('some numbers')
    # plt.show()
    
    st.cur.execute(
        """select * from credits where agent = 'FEBA66'
        order by time"""
    )
    st.conn.commit()
    credits = [s for s in st.cur.fetchall()]
    data = [credits[0][2]]
    times = [credits[0][0]]
    diff = [0]
    lasttime=credits[0][0]
    res = 60*60
    for i,c in enumerate(credits):
        if (c[0]-lasttime).total_seconds()>res:
            diff.append((c[2]-data[-1])/(c[0]-times[-1]).total_seconds()*3600)
            data.append(c[2])
            times.append(c[0])
    # plt.plot(times,data)
    plt.plot(times,diff)
    # plt.plot([c[0] for c in credits[1:]],[(c[2]-credits[i][2])/(c[0]-credits[i][0]).total_seconds() for i,c in enumerate(credits[1:])])
    plt.ylabel('some numbers')
    plt.show()
    # surveys = [Survey(s[1],s[4],s[0],datetime.strptime(s[3].replace(" ","T")+"Z",FORMAT_STR),s[2],s[5]) for s in st.cur.fetchall() if s[5] > datetime(2023,6,5,12,12,50,0)]
    # print(len(surveys))
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
    # # i=0
    # # while len(l)/100>i:
    # #     print(l[0+i*100:99+i*100])
    # #     i+=1
    # print()
    # print()
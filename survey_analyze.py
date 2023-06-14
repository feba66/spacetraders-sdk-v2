from collections import defaultdict
from datetime import datetime
import os
import sys
import time
from zoneinfo import ZoneInfo
from objects import Survey
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
    lengths = defaultdict(int)
    deposits = defaultdict(int)
    size = defaultdict(int)
    runtimes = defaultdict(int)
    for s in surveys:
        for d in s.deposits:
            deposits[d]+=1
        lengths[len(s.deposits)]+=1
        size[s.size]+=1
        runtimes[round((s.expiration-s.timestamp).total_seconds()/10)*10]+=1
    print(deposits)
    print(lengths)
    print(size)
    l = [f"{k};{v}|" for k,v in runtimes.items()]
    print(l)
    # i=0
    # while len(l)/100>i:
    #     print(l[0+i*100:99+i*100])
    #     i+=1
    print()
    print()
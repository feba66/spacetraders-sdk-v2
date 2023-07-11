from collections import defaultdict
from math import ceil
import os
from pprint import pprint
import sys
import time

sys.path.insert(1, './spacetraders-sdk-v2')
from api import SpaceTraders
from objects import Ship, WaypointTrait
from enums import Factions, ShipFrameType, WaypointTraitSymbols, WaypointType


if __name__ == "__main__":
    st = SpaceTraders()
    while st.cur == None:
        time.sleep(.05)
    while True:
        done=[]
        st.cur.execute(f"""select symbol,token from agents""")
        data = [s for s in st.cur.fetchall()]
        for d in data:
            st.ships={}
            st.Login(d[1])
            # st.Init_Systems()
            st.Get_Agent()
            ships,m = st.Get_Ships()
            for s in ships:
                w = ships[s].nav.waypointSymbol
                if w in done:
                    continue
                else:
                    done.append(w)
                st.Get_Market(w)
                st.Get_Shipyard(w)
        time.sleep(60)
        
    st.exit()
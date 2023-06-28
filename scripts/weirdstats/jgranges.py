from collections import defaultdict
from dataclasses import dataclass
from math import ceil
import os
from pprint import pprint
import sys
import time

sys.path.insert(1, './spacetraders-sdk-v2')
from api import SpaceTraders
from objects import Ship, WaypointTrait
from enums import Factions, ShipFrameType, WaypointTraitSymbols, WaypointType

@dataclass
class tmp:
    sys:str
    wp:str
    good:str
    supply:str
    buy:int
    sell:int
    tvol:int

@dataclass
class route:
    wp1:str
    wp2:str
    buy:int
    sell:int
    profit:int
    profit_per_time:float
    good:str
    volb:int
    vols:int
    time:int
    fuel:int

if __name__ == "__main__":
    st = SpaceTraders()
    st.Login(os.getenv("FEBA66GAL"))
    st.Init_Systems()
    # pprint(st.Register("FEBA_C0000",Factions.COSMIC))
    # pprint(st.Get_Agent())
    # st.Get_Ships()
    # home = st.systems[st.system_from_waypoint(st.agent.headquarters)]
    # ship = st.ships[st.agent.symbol+"-1"]
    time.sleep(.5)
    
    # st.cur.execute(f"""select * from systems""")
    # st.conn.commit()
    # systems = [s for s in st.cur.fetchall()]
    st.cur.execute(f"""select * from jumpgateconnections""")
    st.conn.commit()
    jgconnections = [s for s in st.cur.fetchall()]
    
    for jg in jgconnections:
        system = st.system_from_waypoint(jg[0])
        
        for cs in jg[1]:
            d = st.get_dist_systems(system,cs)
            if 2000 < d < 2010:
                print(f"{system} <-> {cs} = {d:.4f}")
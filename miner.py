from math import ceil
import os
import time
from api import SpaceTraders
from enums import ShipNavStatus
from objects import Ship
import threading
import random

def mine(st:SpaceTraders, ship:Ship):
    cd = st.Get_Cooldown(ship.symbol)
    if ship.nav.waypointSymbol != "X1-AD50-85905A":
        if ship.nav.status != ShipNavStatus.IN_TRANSIT:
            nav,_ = st.Navigate(ship.symbol,"X1-AD50-85905A")
        st.sleep_till(nav=nav)
    while True:
        # if random.randint(0,60) < 1:
        #     st.Get_Market("X1-AD50-85905A")
        ship = st.ships[ship.symbol]
        if cd!=None and st.time_till(cd.expiration) > 0:
            st.sleep_till(cooldown=cd)
        surveys = st.sort_surveys_by_worth(st.get_surveys_for(ship.nav.waypointSymbol))
        if len(surveys)<10:
            if ship.nav.status != ShipNavStatus.IN_ORBIT:
                st.Orbit(ship.symbol)
            _,cd = st.Create_Survey(ship.symbol)
        else:
            if ship.cargo.units > 0:
                for c in ship.cargo.inventory:
                    if c.symbol != "ANTIMATTER":
                        if ship.nav.status != ShipNavStatus.DOCKED:
                            st.Dock(ship.symbol)
                        st.Sell(ship.symbol,c.symbol,c.units)
            ship = st.ships[ship.symbol]
            if ship.nav.status != ShipNavStatus.IN_ORBIT:
                st.Orbit(ship.symbol)
            if surveys[0][0] in st.surveys:
                extract,cargo,cd = st.Extract(ship.symbol,st.surveys[surveys[0][0]])
                # extract,cargo,cd = st.Extract(ship.symbol)
                
                ship = st.ships[ship.symbol]
                if extract!=None:
                    st.Dock(ship.symbol)
                    st.Sell(ship.symbol,extract.yield_.symbol,extract.yield_.units)


threads = []
running = True

st = SpaceTraders()
st.Login(os.getenv("TOKEN"))
st.Get_Agent()
i = 20
ships = []
while len(st.db_queue) > 0 or running:
    if i >= 20:
        _,meta = st.Get_Ships()
        while meta.page < ceil(meta.total/20):
            _,meta = st.Get_Ships(meta.page+1)
        for ship in list(st.ships.values()):
            if ship.symbol not in ships:
                ships.append(ship.symbol)
                t = threading.Thread(target=mine,name=ship.symbol,args=[st,ship])
                t.daemon=True
                t.start()
        i=0
        # if st.agent.credits>=500000 and meta.total<30:
        #     st.Purchase_Ship("SHIP_ORE_HOUND","X1-UY52-72027D")
    
    time.sleep(3)
    i+=1
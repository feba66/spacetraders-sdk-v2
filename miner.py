from math import ceil
import os
import time
from api import SpaceTraders
from enums import ShipFrameType, ShipNavStatus
from objects import Ship
import threading
import random

def minesurvey(st:SpaceTraders, ship:Ship):
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
        if len(surveys)<3:
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
def mine(st:SpaceTraders, ship:Ship):
    if ship.cargo.units > 0:
        for c in ship.cargo.inventory:
            if c.symbol != "ANTIMATTER":
                if ship.nav.status != ShipNavStatus.DOCKED:
                    st.Dock(ship.symbol)
                st.Sell(ship.symbol,c.symbol,c.units)
    storage = "FEBA66-28"
    mounts = [m.symbol.name for m in ship.mounts]
    if mounts.count("MOUNT_MINING_LASER_II")<2:
        if ship.nav.status == ShipNavStatus.IN_TRANSIT:
            st.sleep_till(ship.nav)
        st.Orbit(ship.symbol)
        nav,_ = st.Navigate(ship.symbol,"X1-AD50-96037Z")
        st.sleep_till(nav=nav)
        st.Dock(ship.symbol)
        st.Remove_Mount(ship.symbol,"MOUNT_SURVEYOR_I")
        st.Transfer(ship.symbol,"MOUNT_SURVEYOR_I",1,storage) 
        st.Transfer(storage,"MOUNT_MINING_LASER_II",1,ship.symbol) 
        st.Install_Mount(ship.symbol,"MOUNT_MINING_LASER_II")
        st.Orbit(ship.symbol)
        ship = st.Get_Ship(ship.symbol)
    
    cd = st.Get_Cooldown(ship.symbol)
    if ship.nav.waypointSymbol != "X1-AD50-85905A":
        if ship.nav.status != ShipNavStatus.IN_TRANSIT:
            nav,_ = st.Navigate(ship.symbol,"X1-AD50-85905A")
        st.sleep_till(nav=nav)
    elif ship.nav.status == ShipNavStatus.IN_TRANSIT:
        st.sleep_till(nav=ship.nav)
        
    st.Orbit(ship.symbol)
    while True:
        ship = st.ships[ship.symbol]
        if cd!=None and st.time_till(cd.expiration) > 0:
            st.sleep_till(cooldown=cd)
        
        if ship.cargo.units > 0:
            for c in ship.cargo.inventory:
                if c.symbol != "ANTIMATTER":
                    if ship.nav.status != ShipNavStatus.DOCKED:
                        st.Dock(ship.symbol)
                    st.Sell(ship.symbol,c.symbol,c.units)
        no = True
        with st.miners:
            surveys = st.sort_surveys_by_worth(st.get_surveys_for(ship.nav.waypointSymbol,"DIAMONDS"))
            if len(surveys)>0 and surveys[0][0] in st.surveys:
                no=False
                try:
                    st.Orbit(ship.symbol)
                    extract,cargo,cd = st.Extract(ship.symbol,st.surveys[surveys[0][0]])
                    st.Dock(ship.symbol)
                    st.Sell(ship.symbol,extract.yield_.symbol,extract.yield_.units)
                except:
                    pass
            # extract,cargo,cd = st.Extract(ship.symbol)
        if no:
            time.sleep(random.randrange(1,10))
def survey(st:SpaceTraders, ship:Ship):
    cd = st.Get_Cooldown(ship.symbol)
    if ship.nav.waypointSymbol != "X1-AD50-85905A":
        if ship.nav.status != ShipNavStatus.IN_TRANSIT:
            nav,_ = st.Navigate(ship.symbol,"X1-AD50-85905A")
        st.sleep_till(nav=nav)
    if ship.nav.status == ShipNavStatus.IN_TRANSIT:
        st.sleep_till(nav=ship.nav)
    st.Orbit(ship.symbol)
    while True:
        ship = st.ships[ship.symbol]
        if cd!=None and st.time_till(cd.expiration) > 0:
            st.sleep_till(cooldown=cd)
        
        _,cd = st.Create_Survey(ship.symbol)
        


threads = []
running = True

st = SpaceTraders()
st.Login(os.getenv("TOKEN"))
st.Get_Agent()
i = 20
ships = []
disallowed_ships = ["FEBA66-1"]
while len(st.db_queue) > 0 or running:
    if i >= 20:
        st.Get_Market("X1-AD50-85905A")
        ships = [t.name for t in threading.enumerate()]
        _,meta = st.Get_Ships()
        while meta.page < ceil(meta.total/20):
            _,meta = st.Get_Ships(meta.page+1)
        for ship in list(st.ships.values()):
            if ship.symbol not in ships:
                if ship.frame.symbol == ShipFrameType.FRAME_MINER and ship.symbol not in disallowed_ships:
                    print([m.symbol for m in ship.mounts])
                    mounts = [m.symbol.name for m in ship.mounts]
                    surveyors = "MOUNT_SURVEYOR_II" in mounts or "MOUNT_SURVEYOR_III" in mounts
                    miners = "MOUNT_MINING_LASER_I" in mounts or "MOUNT_MINING_LASER_II" in mounts or "MOUNT_MINING_LASER_III" in mounts
                    if surveyors and not miners:
                        t = threading.Thread(target=survey,name=ship.symbol,args=[st,ship])
                    elif not surveyors and miners:
                        t = threading.Thread(target=mine,name=ship.symbol,args=[st,ship])
                    
                    t.daemon=True
                    t.start()
        i=0
        # if st.agent.credits>=500000 and meta.total<30:
        #     st.Purchase_Ship("SHIP_ORE_HOUND","X1-UY52-72027D")
    
    time.sleep(3)
    i+=1
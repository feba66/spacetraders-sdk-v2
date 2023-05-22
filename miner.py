import os
import time
from api import SpaceTraders
from enums import ShipNavStatus
from objects import Ship
import threading

def mine(st:SpaceTraders, ship:Ship):
    cd = st.Get_Cooldown(ship.symbol)
    if ship.nav.waypointSymbol != "X1-UY52-72325C":
        if ship.nav.status != ShipNavStatus.IN_TRANSIT:
            nav,_ = st.Navigate(ship.symbol,"X1-UY52-72325C")
        st.sleep_till(nav=nav)
    while True:
        st.Get_Market("X1-UY52-72325C")
        ship = st.ships[ship.symbol]
        if cd!=None:
            st.sleep_till(cooldown=cd)
        surveys = st.sort_surveys_by_worth(st.get_surveys_for(ship.nav.waypointSymbol))
        if len(surveys)<1 or surveys[0][1]<40:
            if ship.nav.status != ShipNavStatus.IN_ORBIT:
                st.Orbit(ship.symbol)
            _,cd = st.Create_Survey(ship.symbol)
        else:
            if ship.nav.status != ShipNavStatus.IN_ORBIT:
                st.Orbit(ship.symbol)
            extract,cargo,cd = st.Extract(ship.symbol,st.surveys[surveys[0][0]])
            if extract!=None:
                st.Dock(ship.symbol)
                st.Sell(ship.symbol,extract.yield_.symbol,extract.yield_.units)

threads = []
running = True

st = SpaceTraders()
st.Login(os.getenv("TOKEN"))

i = 20
ships = []
while len(st.db_queue) > 0 or running:
    if i >= 20:
        st.Get_Ships()
        for ship in list(st.ships.values()):
            if ship.symbol not in ships:
                ships.append(ship.symbol)
                t = threading.Thread(target=mine,name=ship.symbol,args=[st,ship])
                t.daemon=True
                t.start()
        i=0
    
    time.sleep(3)
    i+=1
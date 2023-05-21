import os
import time
from api import SpaceTraders
from enums import ShipNavStatus




st = SpaceTraders()
st.Login(os.getenv("TOKEN"))

st.Init_Systems()
st.Get_Ships()
ship = list(st.ships.values())[0]
surveys=[]
cd = st.Get_Cooldown(ship.symbol)
while True:
    st.Get_Market("X1-UY52-72325C")
    ship = st.ships[ship.symbol]
    surveys = st.sort_surveys_by_worth(st.get_surveys_for(ship.nav.waypointSymbol))
    if len(surveys)<1 or surveys[0][1]<40:
        if cd!=None:
            st.sleep_till(cooldown=cd)
        _,cd = st.Create_Survey(ship.symbol)
    else:
        if ship.nav.status != ShipNavStatus.IN_ORBIT:
            st.Orbit(ship.symbol)
        if cd!=None:
            st.sleep_till(cooldown=cd)
        extract,cargo,cd = st.Extract(ship.symbol,st.surveys[surveys[0][0]])
        if extract!=None:
            st.Dock(ship.symbol)
            st.Sell(ship.symbol,extract.yield_.symbol,extract.yield_.units)

    pass
while len(st.db_queue) > 0:
    time.sleep(3)
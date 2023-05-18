
from datetime import datetime
from math import ceil
import threading
import time
import psycopg2
import ratelimit
import logging
import requests
import json
import os
from pprint import pprint
from dotenv import load_dotenv
from dataclasses import dataclass
from enum import Enum
from enums import Factions
from objects import Agent, Contract, Cooldown, Faction, JumpGate, Market, Meta, Ship, ShipFuel, ShipNav, Shipyard, Survey, System, Waypoint

class Queue_Obj_Type(Enum):
    WAYPOINT=1,
    SYSTEM=2,
    MARKET=3,
    SHIPYARD=4,
    SHIP=5,
    SHIPNAV=8,
    SHIPFUEL=9,
    CONSUMPTION=6,
    LEADERBOARD=7
@dataclass
class Queue_Obj:
    type:Queue_Obj_Type
    data:object


class SpaceTraders:
    FORMAT_STR = "%Y-%m-%dT%H:%M:%S.%fZ"
    server = "https://api.spacetraders.io/v2"

    session: requests.Session
    logger: logging.Logger
    
    t_db: threading.Thread
    db_queue:list[Queue_Obj]
    db_lock:threading.Lock
    
    agent: Agent
    ships: dict[str, Ship]
    contracts: dict[str, Contract]
    faction: Faction
    systems: dict[str, System]
    markets: dict[str, Market]

    waypoints: dict[str, Waypoint]
    shipyards: dict[str, Shipyard]
    jumpgates: dict[str, JumpGate]
    cooldowns: dict[str, Cooldown]
    surveys: dict[str, Survey]

    def __init__(self) -> None:
        load_dotenv(".env")

        # region inits
        self.session = requests.session()
        self.ships = {}
        self.contracts = {}
        self.waypoints = {}
        self.systems = {}
        self.markets = {}
        self.shipyards = {}
        self.jumpgates = {}
        self.cooldowns = {}
        self.surveys = {}
        self.db_queue = []
        # endregion
        # region logging
        self.logger = logging.getLogger("SpaceTraders-"+str(threading.current_thread().native_id))
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(thread)d - %(name)s - %(levelname)s - %(message)s')

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        fh = logging.FileHandler("SpaceTraders.log", encoding="utf-8")
        fh.setLevel(logging.DEBUG)

        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        # endregion
        # region db
        self.db_lock = threading.Lock()
        self.db_queue=[]
        self.t_db = threading.Thread(target=self.db_thread,name="DB_Thread")
        self.t_db.daemon = True
        self.t_db.start()
        # endregion
    
    def db_thread(self):
        user = os.getenv("USER")
        db = os.getenv("DB")
        ip = os.getenv("IP")
        port = os.getenv("PORT")

        conn = psycopg2.connect(dbname=db,user=user,password=os.getenv("PASSWORD"),host=ip,port=port)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS waypoints (systemSymbol varchar, symbol varchar PRIMARY KEY, type varchar, x integer,y integer,orbitals varchar[],traits varchar[],chart varchar,faction varchar);")
        cur.execute("CREATE TABLE IF NOT EXISTS systems (symbol varchar PRIMARY KEY, type varchar, x integer, y integer);")
        cur.execute("CREATE TABLE IF NOT EXISTS markets (symbol varchar, good varchar, type varchar, PRIMARY KEY (symbol, good, type));")
        # cur.execute("CREATE TABLE IF NOT EXISTS shipyards (symbol varchar, shiptype varchar, PRIMARY KEY (symbol, shiptype));")
        cur.execute("CREATE TABLE IF NOT EXISTS prices (waypointsymbol varchar, symbol varchar, supply varchar, purchase integer, sell integer,tradevolume integer,timestamp varchar, PRIMARY KEY (waypointsymbol, symbol,timestamp));")
        cur.execute("CREATE TABLE IF NOT EXISTS transactions (WAYPOINTSYMBOL varchar, SHIPSYMBOL varchar, TRADESYMBOL varchar, TYPE varchar, UNITS integer, PRICEPERUNIT integer, TOTALPRICE integer, timestamp varchar, PRIMARY KEY (WAYPOINTSYMBOL,TRADESYMBOL,SHIPSYMBOL, timestamp));")
        
        # region reworked tables 
        cur.execute("""CREATE TABLE IF NOT EXISTS SHIPS (SYMBOL CHARACTER varying NOT NULL, faction CHARACTER varying, ROLE CHARACTER varying, FRAME CHARACTER varying,  ENGINE CHARACTER varying,  SPEED CHARACTER varying,  MODULES CHARACTER varying[],  MOUNTS CHARACTER varying[],  cargo_capacity integer, PRIMARY KEY (SYMBOL));""")
        cur.execute("""CREATE TABLE IF NOT EXISTS SHIPNAVS(SYMBOL CHARACTER varying NOT NULL, WAYPOINTSYMBOL CHARACTER varying, DEPARTURE CHARACTER varying, DESTINATION CHARACTER varying, ARRIVAL CHARACTER varying, DEPARTURETIME CHARACTER varying, STATUS CHARACTER varying, FLIGHTMODE CHARACTER varying, PRIMARY KEY (SYMBOL));""")
        cur.execute("""CREATE TABLE IF NOT EXISTS SHIPCARGOS (SYMBOL CHARACTER varying, GOOD CHARACTER varying, UNITS integer, PRIMARY KEY (SYMBOL, GOOD));""")
        cur.execute("""CREATE TABLE IF NOT EXISTS SHIPFUEL (SYMBOL CHARACTER varying, FUEL integer, CAPACITY integer, PRIMARY KEY (SYMBOL));""")
        cur.execute("""CREATE TABLE IF NOT EXISTS SHIPCONSUMTION (SYMBOL CHARACTER varying, AMOUNT integer, DEPARTEDFROM CHARACTER varying, DESTINATION CHARACTER varying, FLIGHTMODE CHARACTER varying, FLIGHTTIME integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (SYMBOL, TIMESTAMP));""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS CREDITLEADERBOARD (AGENTSYMBOL CHARACTER varying, CREDITS integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));""")
        cur.execute("""CREATE TABLE IF NOT EXISTS CHARTLEADERBOARD (AGENTSYMBOL CHARACTER varying, CHARTCOUNT integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));""")
        conn.commit()
        # endregion

        while True:
            tmp:list[Queue_Obj] = []
            if len(self.db_queue)>0:
                with self.db_lock:
                    for _ in range(min(len(self.db_queue),5)):
                        tmp.append(self.db_queue.pop(0))
                while len(tmp)>0:
                    q_obj = tmp.pop(0)
                    if q_obj.type == Queue_Obj_Type.WAYPOINT:
                        wps:list[Waypoint] = q_obj.data
                        temp = []
                        for wp in wps:
                            temp.extend([wp.systemSymbol, wp.symbol,wp.type.name,wp.x,wp.y,[x.symbol for x in wp.orbitals],[x.symbol.name for x in wp.traits],wp.chart.submittedBy if wp.chart else "UNCHARTED",wp.faction.symbol if wp.faction else " "])
                        cur.execute(f"""INSERT INTO waypoints (systemSymbol, symbol, type, x, y, orbitals, traits, chart,faction)
                            VALUES  {','.join([f'(%s, %s, %s, %s, %s, %s, %s, %s, %s)' for _ in range(int(len(temp)/9))])}
                            ON CONFLICT (symbol) 
                            DO UPDATE SET traits = excluded.traits, chart = excluded.chart,faction = excluded.faction """,temp)
                        conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SYSTEM:
                        systems:list[System] = q_obj.data
                        for i in range(ceil(len(systems)/1000)):
                            temp = []
                            for sys in systems[i*1000:min((i+1)*1000,len(systems))]:
                                temp.extend([sys.symbol,sys.type.name,sys.x,sys.y])
                            cur.execute(f"""INSERT INTO systems (symbol, type, x,y)
                            VALUES {','.join([f'(%s, %s, %s, %s)' for _ in range(int(len(temp)/4))])} 
                            ON CONFLICT (symbol) DO NOTHING""",
                                list(temp))
                        conn.commit()
                    elif q_obj.type == Queue_Obj_Type.MARKET:
                        m:Market = q_obj.data
                        temp = []
                        for x in m.imports:
                            temp.extend([m.symbol,x.symbol.name,"IMPORT"])
                        for x in m.exports:
                            temp.extend([m.symbol,x.symbol.name,"EXPORT"])
                        for x in m.exchange:
                            temp.extend([m.symbol,x.symbol.name,"EXCHANGE"])
                        if len(temp)>0:
                            cur.execute(f"""INSERT INTO markets (symbol, good, type)
                            VALUES {','.join([f'(%s, %s, %s)' for _ in range(len(m.tradeGoods))])} 
                            ON CONFLICT (symbol, good, type) DO NOTHING""",
                                list(temp))
                        if m.tradeGoods:
                            temp = []
                            for x in m.tradeGoods:
                                temp.extend([m.symbol,x.symbol,x.supply.name,x.purchasePrice,x.sellPrice,x.tradeVolume,datetime.strftime(datetime.utcnow(),self.FORMAT_STR)])
                            cur.execute(f"""INSERT INTO PRICES (WAYPOINTSYMBOL,symbol,SUPPLY,PURCHASE,SELL,TRADEVOLUME,TIMESTAMP)
                            VALUES {','.join([f'(%s, %s, %s, %s, %s, %s, %s)' for _ in range(int(len(temp)/7))])} 
                            ON CONFLICT (WAYPOINTSYMBOL, symbol, TIMESTAMP) DO UPDATE 
                            SET SUPPLY = excluded.SUPPLY,
                                PURCHASE = excluded.PURCHASE,
                                SELL = excluded.SELL,
                                TRADEVOLUME = excluded.TRADEVOLUME""",
                                list(temp))
                        conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SHIPYARD:
                        pass
                    elif q_obj.type == Queue_Obj_Type.SHIP:
                        ships:list[Ship] = q_obj.data
                        temp = []
                        for s in ships:
                            temp.extend([s.symbol,s.registration.factionSymbol,s.registration.role,s.frame.symbol.name,s.engine.symbol.name,s.engine.speed,[x.symbol.name for x in s.modules],[x.symbol.name for x in s.mounts],s.cargo.capacity])
                        cur.execute(f"""INSERT INTO SHIPS (SYMBOL, FACTION, ROLE, FRAME, ENGINE, SPEED, MODULES, MOUNTS, CARGO_CAPACITY)
                        VALUES {','.join([f'(%s, %s, %s, %s,%s, %s, %s, %s,%s)' for _ in range(int(len(temp)/9))])} 
                        ON CONFLICT (SYMBOL) DO NOTHING""",
                            list(temp))
                        temp = []
                        for s in ships:
                            temp.extend([s.symbol,s.fuel.current,s.fuel.capacity])
                        cur.execute(f"""INSERT INTO SHIPFUEL (SYMBOL, FUEL, CAPACITY)
                        VALUES {','.join([f'(%s,%s,%s)' for _ in range(int(len(temp)/3))])}
                        ON CONFLICT (SYMBOL) DO UPDATE SET FUEL=excluded.FUEL""",
                            list(temp))
                        temp = []
                        for s in ships:
                            for c in s.cargo.inventory:
                                temp.extend([s.symbol,c.symbol,c.units])
                        cur.execute(f"""INSERT INTO SHIPCARGOS (SYMBOL, GOOD, UNITS)
                            VALUES {','.join([f'(%s, %s, %s)' for _ in range(int(len(temp)/3))])}
                            ON CONFLICT (SYMBOL, GOOD) DO UPDATE SET UNITS = excluded.UNITS""",
                                list(temp))
                        temp = []
                        for s in ships:
                            temp.extend([s.symbol,s.nav.waypointSymbol,s.nav.route.departure.symbol,s.nav.route.destination.symbol,s.nav.route.arrival,s.nav.route.departureTime,s.nav.status.name,s.nav.flightMode.name])
                        cur.execute(f"""INSERT INTO SHIPNAVS (SYMBOL, WAYPOINTSYMBOL, DEPARTURE, DESTINATION, ARRIVAL, DEPARTURETIME, STATUS, FLIGHTMODE)
                            VALUES {','.join([f'(%s, %s, %s,%s, %s, %s,%s, %s)' for _ in range(int(len(temp)/8))])}
                            ON CONFLICT (SYMBOL) DO UPDATE SET WAYPOINTSYMBOL = excluded.WAYPOINTSYMBOL, DEPARTURE = excluded.DEPARTURE, DESTINATION = excluded.DESTINATION,ARRIVAL = excluded.ARRIVAL,DEPARTURETIME = excluded.DEPARTURETIME,STATUS = excluded.STATUS,FLIGHTMODE = excluded.FLIGHTMODE""",
                                list(temp))
                        
                        conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SHIPNAV:
                        ship:Ship = q_obj.data
                        temp = []
                        for s in [ship]:
                            temp.extend([s.symbol,s.nav.waypointSymbol,s.nav.route.departure.symbol,s.nav.route.destination.symbol,s.nav.route.arrival,s.nav.route.departureTime,s.nav.status.name,s.nav.flightMode.name])
                        cur.execute(f"""INSERT INTO SHIPNAVS (SYMBOL, WAYPOINTSYMBOL, DEPARTURE, DESTINATION, ARRIVAL, DEPARTURETIME, STATUS, FLIGHTMODE)
                            VALUES {','.join([f'(%s, %s, %s,%s, %s, %s,%s, %s)' for _ in range(int(len(temp)/8))])}
                            ON CONFLICT (SYMBOL) DO UPDATE SET WAYPOINTSYMBOL = excluded.WAYPOINTSYMBOL, DEPARTURE = excluded.DEPARTURE, DESTINATION = excluded.DESTINATION,ARRIVAL = excluded.ARRIVAL,DEPARTURETIME = excluded.DEPARTURETIME,STATUS = excluded.STATUS,FLIGHTMODE = excluded.FLIGHTMODE""",
                                list(temp))
                        
                        conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SHIPFUEL:
                        ship:Ship = q_obj.data
                        temp = []
                        for s in [ships]:
                            temp.extend([s.symbol,s.fuel.current,s.fuel.capacity])
                        cur.execute(f"""INSERT INTO SHIPFUEL (SYMBOL, FUEL, CAPACITY)
                        VALUES {','.join([f'(%s,%s,%s)' for _ in range(int(len(temp)/3))])}
                        ON CONFLICT (SYMBOL) DO UPDATE SET FUEL=excluded.FUEL""",
                            list(temp))
                        conn.commit()
                    elif q_obj.type == Queue_Obj_Type.CONSUMPTION:
                        pass
                    elif q_obj.type == Queue_Obj_Type.LEADERBOARD:
                        lb:dict = q_obj.data
                        temp = []
                        for c in lb["mostCredits"]:
                            temp.extend([c["agentSymbol"],c["credits"],datetime.strftime(datetime.utcnow(),self.FORMAT_STR)])
                        cur.execute(f"""INSERT INTO CREDITLEADERBOARD (AGENTSYMBOL, CREDITS, TIMESTAMP)
                            VALUES {','.join([f'(%s, %s, %s)' for _ in range(int(len(temp)/3))])}
                            ON CONFLICT (AGENTSYMBOL, TIMESTAMP) DO NOTHING""",
                                list(temp))
                        temp = []
                        for c in lb["mostSubmittedCharts"]:
                            temp.extend([c["agentSymbol"],c["chartCount"],datetime.strftime(datetime.utcnow(),self.FORMAT_STR)])
                        cur.execute(f"""INSERT INTO CHARTLEADERBOARD (AGENTSYMBOL, CHARTCOUNT, TIMESTAMP)
                            VALUES {','.join([f'(%s, %s, %s)' for _ in range(int(len(temp)/3))])}
                            ON CONFLICT (AGENTSYMBOL, TIMESTAMP) DO NOTHING""",
                                list(temp))
                        conn.commit()
                # TODO add the msg to db
                # TODO add the queue-ing to all functions
            else:
                time.sleep(.01)
    
    @ratelimit.sleep_and_retry
    @ratelimit.limits(calls=2, period=1)
    def my_req(self, url, method, data=None, json=None):
        r = self.session.request(method, self.server+url, data=data, json=json)

        self.logger.info(f"{r.request.method} {r.request.url} {r.status_code}")
        self.logger.debug(f"{r.request.method} {r.request.url} {r.status_code} {r.text}")

        if r.status_code == 429:
            time.sleep(0.5)
            
            r = self.session.request(method, self.server+url, data=data, json=json)
            
            self.logger.info(f"{r.request.method} {r.request.url} {r.status_code}")
            self.logger.debug(f"{r.request.method} {r.request.url} {r.status_code} {r.text}")
            
        # TODO add monitoring, measure time of the requests and send them to the db aswell
        
        return r
    
    
    def Login(self, token):
        self.session.headers.update({"Authorization": "Bearer "+token})

    # region helpers
    def parse_time(self,tstr):
        return datetime.strptime(tstr,self.FORMAT_STR)
    def get_time_diff(self,big,small):
        return (big-small).total_seconds()
    def time_till(self,future):
        return self.get_time_diff(self.parse_time(future), datetime.utcnow())
    # endregion

    # region added
    # endregion

    # region statekeeping
    def Register(self, symbol: str, faction: Factions,email:str=None, login=True):
        path = "/register"
        if 3 > len(symbol) > 14:
            raise ValueError("symbol must be 3-14 characters long")
        if email != None:
            r = self.my_req(path, "post", data={"symbol": symbol, "faction": faction, "email": email})
        else:
            r = self.my_req(path, "post", data={"symbol": symbol, "faction": faction})

        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data["agent"])
        self.faction = Faction(data["faction"])
        contract = Contract(data["contract"])
        self.contracts[contract.id] = contract
        ship = Ship(data["ship"])
        self.ships[ship.symbol] = ship
        token = data["token"]
        if login:
            self.Login(token)
        return token
    def Get_Agent(self):
        path = "/my/agent"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data)
        return self.agent
    # endregion

    # region done
    def Status(self):
        path ="/"
        r = self.my_req(path, "get")
        try:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.LEADERBOARD,r.json()["leaderboards"]))
        except:
            pass
        return r
    def Get_Ships(self, page=1, limit=20):
        path = "/my/ships"
        r = self.my_req(path+f"?page={page}&limit={limit}", "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        for d in data:
            ship = Ship(d)
            self.ships[ship.symbol] = ship
        with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIP,[Ship(ship) for ship in data]))
        return self.ships,Meta(j["meta"])
    def Get_Ship(self, shipSymbol):
        path = f"/my/ships/{shipSymbol}"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.ships[shipSymbol] = Ship(data)
        with self.db_lock:
            self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIP,self.ships[shipSymbol]))
        return self.ships[shipSymbol]
    def Orbit(self, shipSymbol):
        path = f"/my/ships/{shipSymbol}/orbit"
        r = self.my_req(path, "post")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        shipnav = ShipNav(data["nav"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].nav = shipnav
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPNAV,self.ships[shipSymbol]))
        return self.ships[shipSymbol].nav
    def Dock(self, shipSymbol):
        path = f"/my/ships/{shipSymbol}/dock"
        r = self.my_req(path, "post")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        shipnav = ShipNav(data["nav"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].nav = shipnav
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPNAV,self.ships[shipSymbol]))
        return self.ships[shipSymbol].nav
    def Navigate(self, shipSymbol, waypointSymbol):
        path = f"/my/ships/{shipSymbol}/navigate"
        r = self.my_req(path, "post", data={"waypointSymbol": waypointSymbol})
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        shipnav = ShipNav(data["nav"])
        shipfuel = ShipFuel(data["fuel"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].nav = shipnav
            self.ships[shipSymbol].fuel = shipfuel
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPNAV,self.ships[shipSymbol]))
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL,self.ships[shipSymbol]))
        return (shipnav, shipfuel)
    def Get_Waypoints(self, systemSymbol, page=1, limit=20):
        path = f"/systems/{systemSymbol}/waypoints"
        r = self.my_req(path+f"?page={page}&limit={limit}", "get")
        j = r.json()

        meta = Meta(j["meta"]) if "meta" in j else None
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        way = []
        way:list[str]
        for d in data:
            w = Waypoint(d)
            self.waypoints[w.symbol] = w
            way.append(w.symbol)
        q_tmp = []
        q_tmp.append(Queue_Obj(Queue_Obj_Type.WAYPOINT,[self.waypoints[w] for w in way]))
        with self.db_lock:
            self.db_queue.extend(q_tmp)
        return (way, meta)
    def Purchase_Ship(self, shipType, waypointSymbol):
        path = "/my/ships"
        r = self.my_req(path, "post", data={"shipType": shipType, "waypointSymbol": waypointSymbol})
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data["agent"])
        ship = Ship(data["ship"])
        with self.db_lock:
            self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIP,ship))
        self.ships[ship.symbol] = ship
        return ship
    def Init_Systems(self):
        path = "/systems.json"

        if not os.path.exists("systems.json"):  # TODO smarter caching
            r = self.my_req(path, "get")
            with open("systems.json", "w") as f:
                f.write(r.text)
            j = r.json()
            with self.db_lock:
                self.db_queue.extend(Queue_Obj(Queue_Obj_Type.SHIP,[System(system) for system in j]))
        else:
            with open("systems.json", "r") as f:
                j = json.load(f)
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SYSTEM,[System(system) for system in j]))
        for s in j:
            system = System(s)
            self.systems[system.symbol] = system
        return self.systems
    def Get_Market(self, waypointSymbol):
        systemSymbol = waypointSymbol[0:waypointSymbol.find("-", 4)]
        path = f"/systems/{systemSymbol}/waypoints/{waypointSymbol}/market"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        market = Market(data)
        self.markets[waypointSymbol] = market
        with self.db_lock:
            self.db_queue.append(Queue_Obj(Queue_Obj_Type.MARKET,market))
        return data
    # endregion
if __name__ == "__main__":
    
    st = SpaceTraders()
    st.Login(os.getenv("TOKEN"))
    # st.Get_Market("X1-DF55-17335A")
    # pprint(st.Register("feba66","ASTRO"))
    # pprint(st.Get_Agent())
    pprint(st.Get_Ships())
    ship = list(st.ships.values())[0]
    # pprint(st.Get_Waypoints(ship.nav.systemSymbol))
    # pprint(st.Navigate(ship.symbol,"X1-AC10-39507F"))
    pprint(st.Get_Market("X1-AC10-39507F"))
    # st.Init_Systems()
    print("done")
    time.sleep(2)
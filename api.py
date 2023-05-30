from datetime import datetime
from http.client import RemoteDisconnected
from urllib3.exceptions import ProtocolError
from requests.exceptions import ConnectionError
from math import ceil
import threading
import time
import psycopg2
import logging
import requests
import json
import os
from pprint import pprint
from dotenv import load_dotenv
from dataclasses import dataclass
from enum import Enum
from constants import FORMAT_STR
from enums import Factions, WaypointType
from feba_ratelimit import BurstyLimiter, Limiter
from objects import (
    Agent,
    Chart,
    Contract,
    Cooldown,
    Error,
    Extraction,
    Faction,
    JumpGate,
    Market,
    MarketTransaction,
    Meta,
    Ship,
    ShipCargo,
    ShipFuel,
    ShipNav,
    Shipyard,
    Survey,
    System,
    Waypoint,
)


class Queue_Obj_Type(Enum):
    WAYPOINT = 1
    SYSTEM = 2
    MARKET = 3
    SHIPYARD = 4
    SHIP = 5
    CONSUMPTION = 6
    LEADERBOARD = 7
    SHIPNAV = 8
    SHIPFUEL = 9
    SHIPCARGO = 10
    FACTION = 11


@dataclass
class Queue_Obj:
    type: Queue_Obj_Type
    data: object


class SpaceTraders:
    
    SERVER_URL = "https://api.spacetraders.io/v2"

    worth = {"ALUMINUM_ORE": 40, "AMMONIA_ICE": 26, "COPPER_ORE": 50, "DIAMONDS": 3454, "FUEL": 234, "GOLD_ORE": 57,
             "ICE_WATER": 7, "IRON_ORE": 37, "PLATINUM_ORE": 61, "QUARTZ_SAND": 16, "SILICON_CRYSTALS": 24, "SILVER_ORE": 56}

    # region variables
    session: requests.Session
    logger: logging.Logger

    use_db: bool

    t_db: threading.Thread
    db_queue: list[Queue_Obj]
    db_lock: threading.Lock

    agent: Agent
    ships: dict[str, Ship]
    contracts: dict[str, Contract]
    faction: Faction
    factions: dict[str, Faction]
    systems: dict[str, System]
    markets: dict[str, Market]

    waypoints: dict[str, Waypoint]
    shipyards: dict[str, Shipyard]
    jumpgates: dict[str, JumpGate]
    cooldowns: dict[str, Cooldown]
    surveys: dict[str, Survey]
    survey_lock = threading.Lock()

    token:str
    # endregion

    def __init__(self,use_db=True) -> None:
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
        self.agent = Agent()
        self.token = None
        # endregion
        # region logging
        self.logger = logging.getLogger("SpaceTraders-" + str(threading.current_thread().native_id))
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(thread)d - %(name)s - %(levelname)s - %(message)s")

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
        self.use_db=use_db
        if self.use_db:
            self.db_lock = threading.Lock()
            self.db_queue = []
            self.t_db = threading.Thread(target=self.db_thread, name="DB_Thread")
            self.t_db.daemon = True
            self.t_db.start()
        # endregion

    def db_thread(self):
        user = os.getenv("DB_USER")
        db = os.getenv("DB")
        ip = os.getenv("IP")
        port = os.getenv("PORT")

        self.conn = psycopg2.connect(dbname=db, user=user, password=os.getenv("DB_PASSWORD"), host=ip, port=port)
        self.cur = self.conn.cursor()

        self.cur.execute("CREATE TABLE IF NOT EXISTS waypoints (systemSymbol varchar, symbol varchar PRIMARY KEY, type varchar, x integer,y integer,orbitals varchar[],traits varchar[],chart varchar,faction varchar);")
        self.cur.execute("CREATE TABLE IF NOT EXISTS systems (symbol varchar PRIMARY KEY, type varchar, x integer, y integer);")
        self.cur.execute("CREATE TABLE IF NOT EXISTS markets (symbol varchar, good varchar, type varchar, PRIMARY KEY (symbol, good, type));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS shipyards (symbol varchar, shiptype varchar, PRIMARY KEY (symbol, shiptype));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS prices (waypointsymbol varchar, symbol varchar, supply varchar, purchase integer, sell integer,tradevolume integer,timestamp varchar, PRIMARY KEY (waypointsymbol, symbol,timestamp));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS transactions (WAYPOINTSYMBOL varchar, SHIPSYMBOL varchar, TRADESYMBOL varchar, TYPE varchar, UNITS integer, PRICEPERUNIT integer, TOTALPRICE integer, timestamp varchar, PRIMARY KEY (WAYPOINTSYMBOL,TRADESYMBOL,SHIPSYMBOL, timestamp));")

        # region reworked tables
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPS (SYMBOL CHARACTER varying NOT NULL, faction CHARACTER varying, ROLE CHARACTER varying, FRAME CHARACTER varying,  ENGINE CHARACTER varying,  SPEED CHARACTER varying,  MODULES CHARACTER varying[],  MOUNTS CHARACTER varying[],  cargo_capacity integer, PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPNAVS(SYMBOL CHARACTER varying NOT NULL, WAYPOINTSYMBOL CHARACTER varying, DEPARTURE CHARACTER varying, DESTINATION CHARACTER varying, ARRIVAL CHARACTER varying, DEPARTURETIME CHARACTER varying, STATUS CHARACTER varying, FLIGHTMODE CHARACTER varying, PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPCARGOS (SYMBOL CHARACTER varying, GOOD CHARACTER varying, UNITS integer, PRIMARY KEY (SYMBOL, GOOD));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPFUEL (SYMBOL CHARACTER varying, FUEL integer, CAPACITY integer, PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPCONSUMTION (SYMBOL CHARACTER varying, AMOUNT integer, DEPARTEDFROM CHARACTER varying, DESTINATION CHARACTER varying, FLIGHTMODE CHARACTER varying, FLIGHTTIME integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (SYMBOL, TIMESTAMP));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS CREDITLEADERBOARD (AGENTSYMBOL CHARACTER varying, CREDITS integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS CHARTLEADERBOARD (AGENTSYMBOL CHARACTER varying, CHARTCOUNT integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS FACTIONS (SYMBOL CHARACTER varying NOT NULL, name CHARACTER varying, description CHARACTER varying, headquarters CHARACTER varying,  traits CHARACTER varying[], PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SURVEYS (signature CHARACTER varying,symbol CHARACTER varying,deposits CHARACTER varying[],expiration CHARACTER varying,size CHARACTER varying,timestamp CHARACTER varying,PRIMARY KEY (signature))")
        self.cur.execute("CREATE TABLE IF NOT EXISTS EXTRACTIONS (shipSymbol CHARACTER varying,symbol CHARACTER varying,units CHARACTER varying[],timestamp CHARACTER varying, PRIMARY KEY (shipSymbol,timestamp))")
        self.conn.commit()
        # endregion

        while True:
            tmp: list[Queue_Obj] = []
            if len(self.db_queue) > 0:
                with self.db_lock:
                    for _ in range(min(len(self.db_queue), 5)):
                        tmp.append(self.db_queue.pop(0))
                while len(tmp) > 0:
                    q_obj = tmp.pop(0)
                    if q_obj.type == Queue_Obj_Type.WAYPOINT:
                        wps: list[Waypoint] = q_obj.data
                        temp = []
                        for wp in wps:
                            temp.extend(
                                [
                                    wp.systemSymbol,
                                    wp.symbol,
                                    wp.type.name,
                                    wp.x,
                                    wp.y,
                                    [x.symbol for x in wp.orbitals],
                                    [x.symbol.name for x in wp.traits],
                                    wp.chart.submittedBy if wp.chart else "UNCHARTED",
                                    wp.faction.symbol if wp.faction else " ",
                                ]
                            )
                        self.cur.execute(
                            f"""INSERT INTO waypoints (systemSymbol, symbol, type, x, y, orbitals, traits, chart,faction)
                            VALUES  {','.join([f'(%s, %s, %s, %s, %s, %s, %s, %s, %s)' for _ in range(int(len(temp)/9))])}
                            ON CONFLICT (symbol)
                            DO UPDATE SET traits = excluded.traits, chart = excluded.chart,faction = excluded.faction """,
                            temp,
                        )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SYSTEM:
                        systems: list[System] = q_obj.data
                        for i in range(ceil(len(systems) / 1000)):
                            temp = []
                            for sys in systems[
                                i * 1000: min((i + 1) * 1000, len(systems))
                            ]:
                                temp.extend(
                                    [sys.symbol, sys.type.name, sys.x, sys.y])
                            self.cur.execute(
                                f"""INSERT INTO systems (symbol, type, x,y)
                            VALUES {','.join([f'(%s, %s, %s, %s)' for _ in range(int(len(temp)/4))])} 
                            ON CONFLICT (symbol) DO NOTHING""",
                                list(temp),
                            )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.MARKET:
                        m: Market = q_obj.data
                        temp = []
                        for x in m.imports:
                            temp.extend([m.symbol, x.symbol.name, "IMPORT"])
                        for x in m.exports:
                            temp.extend([m.symbol, x.symbol.name, "EXPORT"])
                        for x in m.exchange:
                            temp.extend([m.symbol, x.symbol.name, "EXCHANGE"])
                        if len(temp) > 0:
                            self.cur.execute(
                                f"""INSERT INTO markets (symbol, good, type)
                            VALUES {','.join([f'(%s, %s, %s)' for _ in range(int(len(temp)/3))])} 
                            ON CONFLICT (symbol, good, type) DO NOTHING""",
                                list(temp),
                            )
                        if m.tradeGoods:
                            temp = []
                            for x in m.tradeGoods:
                                temp.extend(
                                    [
                                        m.symbol,
                                        x.symbol,
                                        x.supply.name,
                                        x.purchasePrice,
                                        x.sellPrice,
                                        x.tradeVolume,
                                        datetime.strftime(datetime.utcnow(), FORMAT_STR),
                                    ]
                                )
                            self.cur.execute(
                                f"""INSERT INTO PRICES (WAYPOINTSYMBOL,symbol,SUPPLY,PURCHASE,SELL,TRADEVOLUME,TIMESTAMP)
                            VALUES {','.join([f'(%s, %s, %s, %s, %s, %s, %s)' for _ in range(int(len(temp)/7))])} 
                            ON CONFLICT (WAYPOINTSYMBOL, symbol, TIMESTAMP) DO UPDATE 
                            SET SUPPLY = excluded.SUPPLY,
                                PURCHASE = excluded.PURCHASE,
                                SELL = excluded.SELL,
                                TRADEVOLUME = excluded.TRADEVOLUME""",
                                list(temp),
                            )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SHIPYARD:
                        yard: list[Shipyard] = q_obj.data
                        temp = []
                        for sy in [yard]:
                            for shiptype in sy.shipTypes:
                                temp.extend([sy.symbol, shiptype.name])
                            # temp.extend([wp.systemSymbol, wp.symbol,wp.type.name,wp.x,wp.y,[x.symbol for x in wp.orbitals],[x.symbol.name for x in wp.traits],wp.chart.submittedBy if wp.chart else "UNCHARTED",wp.faction.symbol if wp.faction else " "])
                        self.cur.execute(
                            f"""INSERT INTO shipyards (symbol,shiptype)
                            VALUES  {','.join([f'(%s, %s)' for _ in range(int(len(temp)/2))])}
                            ON CONFLICT (symbol,shiptype) 
                            DO NOTHING""",
                            temp,
                        )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SHIP:
                        ships: list[Ship] = q_obj.data
                        temp = []
                        for s in ships:
                            temp.extend(
                                [
                                    s.symbol,
                                    s.registration.factionSymbol,
                                    s.registration.role,
                                    s.frame.symbol.name,
                                    s.engine.symbol.name,
                                    s.engine.speed,
                                    [x.symbol.name for x in s.modules],
                                    [x.symbol.name for x in s.mounts],
                                    s.cargo.capacity,
                                ]
                            )
                        self.cur.execute(
                            f"""INSERT INTO SHIPS (SYMBOL, FACTION, ROLE, FRAME, ENGINE, SPEED, MODULES, MOUNTS, CARGO_CAPACITY)
                        VALUES {','.join([f'(%s, %s, %s, %s,%s, %s, %s, %s,%s)' for _ in range(int(len(temp)/9))])} 
                        ON CONFLICT (SYMBOL) DO NOTHING""",
                            list(temp),
                        )
                        temp = []
                        for s in ships:
                            temp.extend(
                                [s.symbol, s.fuel.current, s.fuel.capacity])
                        self.cur.execute(
                            f"""INSERT INTO SHIPFUEL (SYMBOL, FUEL, CAPACITY)
                        VALUES {','.join([f'(%s,%s,%s)' for _ in range(int(len(temp)/3))])}
                        ON CONFLICT (SYMBOL) DO UPDATE SET FUEL=excluded.FUEL""",
                            list(temp),
                        )
                        temp = []
                        for s in ships:
                            for c in s.cargo.inventory:
                                temp.extend([s.symbol, c.symbol, c.units])
                        if len(temp)>0:
                            self.cur.execute(
                                f"""INSERT INTO SHIPCARGOS (SYMBOL, GOOD, UNITS)
                                VALUES {','.join([f'(%s, %s, %s)' for _ in range(int(len(temp)/3))])}
                                ON CONFLICT (SYMBOL, GOOD) DO UPDATE SET UNITS = excluded.UNITS""",
                                list(temp),
                            )
                        temp = []
                        for s in ships:
                            temp.extend(
                                [
                                    s.symbol,
                                    s.nav.waypointSymbol,
                                    s.nav.route.departure.symbol,
                                    s.nav.route.destination.symbol,
                                    s.nav.route.arrival,
                                    s.nav.route.departureTime,
                                    s.nav.status.name,
                                    s.nav.flightMode.name,
                                ]
                            )
                        self.cur.execute(
                            f"""INSERT INTO SHIPNAVS (SYMBOL, WAYPOINTSYMBOL, DEPARTURE, DESTINATION, ARRIVAL, DEPARTURETIME, STATUS, FLIGHTMODE)
                            VALUES {','.join([f'(%s, %s, %s,%s, %s, %s,%s, %s)' for _ in range(int(len(temp)/8))])}
                            ON CONFLICT (SYMBOL) DO UPDATE SET WAYPOINTSYMBOL = excluded.WAYPOINTSYMBOL, DEPARTURE = excluded.DEPARTURE, DESTINATION = excluded.DESTINATION,ARRIVAL = excluded.ARRIVAL,DEPARTURETIME = excluded.DEPARTURETIME,STATUS = excluded.STATUS,FLIGHTMODE = excluded.FLIGHTMODE""",
                            list(temp),
                        )

                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SHIPCARGO:
                        ships: list[Ship] = q_obj.data
                        
                        temp = []
                        for s in ships:
                            for c in s.cargo.inventory:
                                temp.extend([s.symbol, c.symbol, c.units])
                        if len(temp)>0:
                            self.cur.execute(
                                f"""INSERT INTO SHIPCARGOS (SYMBOL, GOOD, UNITS)
                                VALUES {','.join([f'(%s, %s, %s)' for _ in range(int(len(temp)/3))])}
                                ON CONFLICT (SYMBOL, GOOD) DO UPDATE SET UNITS = excluded.UNITS""",
                                list(temp),
                            )
                    elif q_obj.type == Queue_Obj_Type.SHIPNAV:
                        ship: Ship = q_obj.data
                        temp = []
                        for s in [ship]:
                            temp.extend(
                                [
                                    s.symbol,
                                    s.nav.waypointSymbol,
                                    s.nav.route.departure.symbol,
                                    s.nav.route.destination.symbol,
                                    s.nav.route.arrival,
                                    s.nav.route.departureTime,
                                    s.nav.status.name,
                                    s.nav.flightMode.name,
                                ]
                            )
                        self.cur.execute(
                            f"""INSERT INTO SHIPNAVS (SYMBOL, WAYPOINTSYMBOL, DEPARTURE, DESTINATION, ARRIVAL, DEPARTURETIME, STATUS, FLIGHTMODE)
                            VALUES {','.join([f'(%s, %s, %s,%s, %s, %s,%s, %s)' for _ in range(int(len(temp)/8))])}
                            ON CONFLICT (SYMBOL) DO UPDATE SET WAYPOINTSYMBOL = excluded.WAYPOINTSYMBOL, DEPARTURE = excluded.DEPARTURE, DESTINATION = excluded.DESTINATION,ARRIVAL = excluded.ARRIVAL,DEPARTURETIME = excluded.DEPARTURETIME,STATUS = excluded.STATUS,FLIGHTMODE = excluded.FLIGHTMODE""",
                            list(temp),
                        )

                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SHIPFUEL:
                        ship: Ship = q_obj.data
                        temp = []
                        for s in [ship]:
                            temp.extend(
                                [s.symbol, s.fuel.current, s.fuel.capacity])
                        self.cur.execute(
                            f"""INSERT INTO SHIPFUEL (SYMBOL, FUEL, CAPACITY)
                        VALUES {','.join([f'(%s,%s,%s)' for _ in range(int(len(temp)/3))])}
                        ON CONFLICT (SYMBOL) DO UPDATE SET FUEL=excluded.FUEL""",
                            list(temp),
                        )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.CONSUMPTION:
                        pass
                    elif q_obj.type == Queue_Obj_Type.LEADERBOARD:
                        lb: dict = q_obj.data
                        temp = []
                        for c in lb["mostCredits"]:
                            temp.extend(
                                [
                                    c["agentSymbol"],
                                    c["credits"],
                                    datetime.strftime(
                                        datetime.utcnow(), FORMAT_STR
                                    ),
                                ]
                            )
                        self.cur.execute(
                            f"""INSERT INTO CREDITLEADERBOARD (AGENTSYMBOL, CREDITS, TIMESTAMP)
                            VALUES {','.join([f'(%s, %s, %s)' for _ in range(int(len(temp)/3))])}
                            ON CONFLICT (AGENTSYMBOL, TIMESTAMP) DO NOTHING""",
                            list(temp),
                        )
                        if len(lb["mostSubmittedCharts"]) > 0:
                            temp = []
                            for c in lb["mostSubmittedCharts"]:
                                temp.extend(
                                    [
                                        c["agentSymbol"],
                                        c["chartCount"],
                                        datetime.strftime(
                                            datetime.utcnow(), FORMAT_STR
                                        ),
                                    ]
                                )
                            self.cur.execute(
                                f"""INSERT INTO CHARTLEADERBOARD (AGENTSYMBOL, CHARTCOUNT, TIMESTAMP)
                                VALUES {','.join([f'(%s, %s, %s)' for _ in range(int(len(temp)/3))])}
                                ON CONFLICT (AGENTSYMBOL, TIMESTAMP) DO NOTHING""",
                                list(temp),
                            )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.FACTION:
                        factions: list[Faction] = q_obj.data
                        temp = []
                        for f in factions:
                            temp.extend(
                                [
                                    f.symbol,
                                    f.name,
                                    f.description,
                                    f.headquarters,
                                    [t.symbol.name for t in f.traits],
                                ]
                            )
                        self.cur.execute(
                            f"""INSERT INTO FACTIONS (SYMBOL, NAME, DESCRIPTION,HEADQUARTERS,TRAITS)
                            VALUES {','.join([f'(%s, %s, %s, %s, %s)' for _ in range(int(len(temp)/5))])}
                            ON CONFLICT (SYMBOL) DO NOTHING""",
                            list(temp),
                        )
                        self.conn.commit()

                # TODO add the msg to db
                # TODO add the queue-ing to all functions
            else:
                time.sleep(0.01)

    @BurstyLimiter(Limiter(2,1),Limiter(10,10))
    def req_and_log(self, url, method, data=None, json=None):
        # before = time.perf_counter()
        r = self.session.request(method, self.SERVER_URL + url, data=data, json=json)
        # after = time.perf_counter()

        self.logger.info(f"{r.request.method} {r.request.url} {r.status_code}")
        self.logger.debug(f"{r.request.method} {r.request.url} {r.status_code} {r.text}")
        return r

    # @ratelimit.sleep_and_retry
    # @ratelimit.limits(calls=3, period=1)
    def my_req(self, url, method, data=None, json=None):
        try:
            r = self.req_and_log(url, method, data, json)
            while r.status_code == 429:
                time.sleep(0.5)
                r = self.req_and_log(url, method, data, json)
        except RemoteDisconnected as e:
            self.reset_connection()
        except ProtocolError as e:
            self.reset_connection()
        except ConnectionError as e:
            self.reset_connection()
        # TODO add monitoring, measure time of the requests and send them to the db aswell

        return r
    
    def reset_connection(self):
        self.session = requests.session()
        if self.token!=None:
            self.Login(self.token)
        time.sleep(5)
    def Login(self, token):
        self.token=token
        self.session.headers.update({"Authorization": "Bearer " + token})

    # region helpers
    def parse_time(self, tstr: str):
        return datetime.strptime(tstr, FORMAT_STR)

    def get_time_diff(self, big: datetime, small: datetime):
        return (big - small).total_seconds()

    def time_till(self, future: str):
        return self.get_time_diff(self.parse_time(future), datetime.utcnow())

    def sleep_till(self, nav: ShipNav = None, cooldown: Cooldown = None):
        if nav != None:
            t = max(0, self.time_till(nav.route.arrival))
        elif cooldown != None:
            t = max(0, self.time_till(cooldown.expiration))
        else:
            return
        self.logger.info(f"Sleep for {t}")
        time.sleep(t)

    def clean_surveys(self):
        with self.survey_lock:
            for k in self.surveys.keys():
                survey = self.surveys[k]
                if self.time_till(survey.expiration) < 0:
                    self.surveys.pop(k)

    def get_surveys_for(self, waypointSymbol):
        keys = [k for k in self.surveys.keys() if self.surveys[k].symbol == waypointSymbol]
        return keys

    def get_survey_worth(self, survey: Survey):
        value = sum([self.worth[g.symbol]
                    for g in survey.deposits])/len(survey.deposits)
        return value

    def sort_surveys_by_worth(self, surveys: list[str]):
        sortd = [(k, self.get_survey_worth(self.surveys[k])) for k in surveys]
        sortd.sort(key=lambda x: x[1], reverse=True)
        return sortd
    # endregion

    # region endpoints
    def Register(self, symbol: str, faction: Factions, email: str = None, login=True):
        path = "/register"
        if 3 > len(symbol) > 14:
            raise ValueError("symbol must be 3-14 characters long")
        if email != None:
            r = self.my_req(path, "post", data={"symbol": symbol, "faction": faction, "email": email},)
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

    def Status(self):
        path = "/"
        r = self.my_req(path, "get")
        
        if self.use_db:
            try:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.LEADERBOARD, r.json()["leaderboards"]))
            except:
                pass
        return r

    def Get_Agent(self):
        path = "/my/agent"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data)
        return self.agent

    # region Systems
    def Get_Systems(self, page=1, limit=20):
        path = f"/systems"
        r = self.my_req(path + f"?page={page}&limit={limit}", "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        systems = []
        for d in data:
            system = System(d)
            systems.append(system)
            self.systems[system.symbol] = system
            
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SYSTEM, systems))
        return systems, Meta(j["meta"])

    def Init_Systems(self):
        path = "/systems.json"

        if not os.path.exists("systems.json"):  # TODO smarter caching
            r = self.my_req(path, "get")
            with open("systems.json", "w") as f:
                f.write(r.text)
            j = r.json()
            
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SYSTEM, [System(system) for system in j]))
        else:
            with open("systems.json", "r") as f:
                j = json.load(f)
            
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SYSTEM, [System(system) for system in j]))
        for s in j:
            system = System(s)
            self.systems[system.symbol] = system
        return self.systems

    def Get_System(self, systemSymbol):
        path = f"/systems/{systemSymbol}"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        system = System(data)
        self.systems[systemSymbol] = system
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SYSTEM, [system]))
        return system

    def Get_Waypoints(self, systemSymbol, page=1, limit=20):
        path = f"/systems/{systemSymbol}/waypoints"
        r = self.my_req(path + f"?page={page}&limit={limit}", "get")
        j = r.json()

        meta = Meta(j["meta"]) if "meta" in j else None
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        way = []
        way: list[str]
        for d in data:
            w = Waypoint(d)
            self.waypoints[w.symbol] = w
            way.append(w.symbol)
        if self.use_db:
            if len(way) > 0:
                with self.db_lock:
                    self.db_queue.append(
                        Queue_Obj(Queue_Obj_Type.WAYPOINT, [self.waypoints[w] for w in way]))
        return (way, meta)

    def Get_Waypoint(self, waypointSymbol):
        systemSymbol = waypointSymbol[0: waypointSymbol.find("-", 4)]
        path = f"/systems/{systemSymbol}/waypoints/{waypointSymbol}"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        w = Waypoint(data)
        self.waypoints[w.symbol] = w
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.WAYPOINT, [w]))
        return w

    def Get_Market(self, waypointSymbol):
        systemSymbol = waypointSymbol[0: waypointSymbol.find("-", 4)]
        path = f"/systems/{systemSymbol}/waypoints/{waypointSymbol}/market"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        market = Market(data)
        self.markets[waypointSymbol] = market
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.MARKET, market))
        return market

    def Get_Shipyard(self, waypointSymbol):
        systemSymbol = waypointSymbol[0: waypointSymbol.find("-", 4)]
        path = f"/systems/{systemSymbol}/waypoints/{waypointSymbol}/shipyard"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        yard = Shipyard(data)
        self.shipyards[waypointSymbol] = yard
        # TODO add ship listings when at waypoint
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPYARD, yard))
        return yard

    def Get_JumpGate(self, waypointSymbol):
        systemSymbol = waypointSymbol[0: waypointSymbol.find("-", 4)]
        path = f"/systems/{systemSymbol}/waypoints/{waypointSymbol}/jump-gate"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        gate = JumpGate(data)
        self.jumpgates[waypointSymbol] = gate
        return gate

    # endregion

    # region Contracts
    def Get_Contracts(self, page=1, limit=20):
        path = f"/my/contracts?page={page}&limit={limit}"
        r = self.my_req(path, "get")
        j = r.json()

        meta = Meta(j["meta"]) if "meta" in j else None
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        contracts = []
        for d in data:
            contract = Contract(d)
            contracts.append(contract)
            self.contracts[contract.id] = contract
        # if self.use_db:
            # with self.db_lock:
            #     self.db_queue.append(Queue_Obj(Queue_Obj_Type.CONTRACT,contracts))
        return (contracts, meta)

    def Get_Contract(self, contractId):
        path = f"/my/contracts/{contractId}"
        r = self.my_req(path, "get")
        j = r.json()

        meta = Meta(j["meta"]) if "meta" in j else None
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        contract = Contract(data)
        self.contracts[contract.id] = contract
        # if self.use_db:
            # with self.db_lock:
            #     self.db_queue.append(Queue_Obj(Queue_Obj_Type.CONTRACT,contracts))
        return contract

    def Accept_Contract(self, contractId):
        path = f"/my/contracts/{contractId}/accept"
        r = self.my_req(path, "post")
        j = r.json()

        self.agent = Agent(data["agent"])
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        contract = Contract(data)
        self.contracts[contract.id] = contract
        # if self.use_db:
            # with self.db_lock:
            #     self.db_queue.append(Queue_Obj(Queue_Obj_Type.CONTRACT,contracts))
        return contract

    def Deliver_Contract(self, contractId, shipSymbol, tradeSymbol, units):
        path = f"/my/contracts/{contractId}/deliver"
        r = self.my_req(
            path,
            "post",
            data={"shipSymbol": shipSymbol,
                  "tradeSymbol": tradeSymbol, "units": units},
        )
        j = r.json()

        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        contract = Contract(data)
        self.contracts[contract.id] = contract
        cargo = ShipCargo(data["cargo"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].cargo = cargo
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPCARGO, [self.ships[shipSymbol]]))
                    # self.db_queue.append(Queue_Obj(Queue_Obj_Type.CONTRACT,contracts))
        return contract

    def Fulfill_Contract(self, contractId):
        path = f"/my/contracts/{contractId}/fulfill"
        r = self.my_req(path, "post")
        j = r.json()

        self.agent = Agent(data["agent"])
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        contract = Contract(data)
        self.contracts[contract.id] = contract
        # if self.use_db:
            # with self.db_lock:
            #     self.db_queue.append(Queue_Obj(Queue_Obj_Type.CONTRACT,contracts))
        return contract

    # endregion
    # region Factions
    def Get_Factions(self, page=1, limit=20):
        path = f"/factions?page={page}&limit={limit}"
        r = self.my_req(path, "get")
        j = r.json()

        meta = Meta(j["meta"]) if "meta" in j else None
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        factions = []
        for d in data:
            faction = Faction(d)
            factions.append(faction)
            self.factions[faction.symbol] = faction
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.Faction, factions))
        return (factions, meta)

    def Get_Faction(self, factionSymbol):
        path = f"/factions/{factionSymbol}"
        r = self.my_req(path, "get")
        j = r.json()

        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error

        faction = Faction(data)
        self.factions[faction.symbol] = faction
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.Faction, [faction]))
        return faction

    # endregion

    # region Fleet
    def Get_Ships(self, page=1, limit=20):
        path = "/my/ships"
        r = self.my_req(path + f"?page={page}&limit={limit}", "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        for d in data:
            ship = Ship(d)
            self.ships[ship.symbol] = ship
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIP, [Ship(ship) for ship in data]))
        return self.ships, Meta(j["meta"])

    def Purchase_Ship(self, shipType, waypointSymbol):
        path = "/my/ships"
        r = self.my_req(
            path, "post", data={"shipType": shipType, "waypointSymbol": waypointSymbol}
        )
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data["agent"])
        ship = Ship(data["ship"])
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIP, [ship]))
        self.ships[ship.symbol] = ship
        return ship

    def Get_Ship(self, shipSymbol):
        path = f"/my/ships/{shipSymbol}"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.ships[shipSymbol] = Ship(data)
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIP, self.ships[shipSymbol]))
        return self.ships[shipSymbol]

    def Get_Cargo(self, shipSymbol):
        path = f"/my/ships/{shipSymbol}/cargo"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        cargo = ShipCargo(data)
        if shipSymbol in self.ships:
            self.ships[shipSymbol].cargo = cargo
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPCARGO, self.ships[shipSymbol]))
        return cargo

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
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPNAV, self.ships[shipSymbol]))
        return self.ships[shipSymbol].nav

    # refine
    def Chart(self, shipSymbol):
        path = f"/my/ships/{shipSymbol}/chart"
        r = self.my_req(path, "post")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        chart = Chart(data["chart"])
        waypoint = Waypoint(data["waypoint"])

        self.waypoints[waypoint.symbol] = waypoint
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(
                    Queue_Obj(Queue_Obj_Type.WAYPOINT, [waypoint]))
        return (chart, waypoint)

    def Get_Cooldown(self, shipSymbol):
        path = f"/my/ships/{shipSymbol}/cooldown"
        r = self.my_req(path, "get")
        if r.status_code==204:
            return Cooldown({"remainingSeconds":0,"totalSeconds":0,"expiration":datetime.strftime(datetime.utcnow(),FORMAT_STR),"shipSymbol":shipSymbol})
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error

        cooldown = Cooldown(data)
        self.cooldowns[shipSymbol] = cooldown
        return cooldown

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
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPNAV, self.ships[shipSymbol]))
        return self.ships[shipSymbol].nav

    def Create_Survey(self, shipSymbol):
        path = f"/my/ships/{shipSymbol}/survey"
        r = self.my_req(path, "post")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        cooldown = Cooldown(data["cooldown"])
        self.cooldowns[shipSymbol] = cooldown
        surveys = []
        
        for s in data["surveys"]:
            survey = Survey(s)
            surveys.append(survey)
            # TODO add survey to database
            with self.survey_lock:
                self.surveys[survey.signature] = survey
        
        # if self.use_db:
            # self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL,self.ships[shipSymbol])) # TODO cooldown to db
        return (surveys, cooldown)

    def Extract(self, shipSymbol, survey: Survey = None):
        path = f"/my/ships/{shipSymbol}/extract"
        if survey:
            r = self.my_req(path, "post", json={"survey": survey.dict()})
        else:
            r = self.my_req(path, "post")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            error = Error(j["error"])
            if error.code in [4221,4224]:
                self.surveys.pop(survey.signature)
                return (None,None,None)
            else:
                raise Exception(j)  # TODO raise error
        extraction = Extraction(data["extraction"])
        cooldown = Cooldown(data["cooldown"])
        self.cooldowns[shipSymbol] = cooldown
        cargo = ShipCargo(data["cargo"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].cargo = cargo
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPCARGO, [self.ships[shipSymbol]]))
        # self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL,self.ships[shipSymbol])) # TODO cooldown to db
        return (extraction, cargo, cooldown)
    # jettison

    def Jump(self, shipSymbol, systemSymbol):
        path = f"/my/ships/{shipSymbol}/jump"
        r = self.my_req(path, "post", data={"systemSymbol": systemSymbol})
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        cooldown = Cooldown(data)
        self.cooldowns[shipSymbol] = cooldown
        # if self.use_db:
            # self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL,self.ships[shipSymbol])) # TODO cooldown to db
        return cooldown

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
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPNAV, self.ships[shipSymbol]))
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL, self.ships[shipSymbol]))
        return (shipnav, shipfuel)

    def Warp(self, shipSymbol, waypointSymbol):
        path = f"/my/ships/{shipSymbol}/warp"
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
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPNAV, self.ships[shipSymbol]))
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL, self.ships[shipSymbol]))
        return (shipnav, shipfuel)

    def Sell(self, shipSymbol, symbol, units):
        path = f"/my/ships/{shipSymbol}/sell"
        r = self.my_req(path, "post", data={"symbol": symbol, "units": units})
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data["agent"])
        transaction = MarketTransaction(data["transaction"])
        self.worth[transaction.tradeSymbol]=transaction.pricePerUnit
        if shipSymbol in self.ships:
            self.ships[shipSymbol].cargo = ShipCargo(data["cargo"])
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPCARGO, [self.ships[shipSymbol]]))
        return (self.agent, self.ships[shipSymbol].cargo, transaction)

    # scan systems
    # scan waypoints
    # scan ships
    def Refuel(self, shipSymbol):
        path = f"/my/ships/{shipSymbol}/refuel"
        r = self.my_req(path, "post")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data["agent"])
        fuel = ShipFuel(data["fuel"])
        transaction = MarketTransaction(data["transaction"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].fuel = fuel
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL, self.ships[shipSymbol]))
        return (self.agent, fuel, transaction)

    def Purchase(self, shipSymbol, symbol, units):
        path = f"/my/ships/{shipSymbol}/purchase"
        r = self.my_req(path, "post", data={"symbol": symbol, "units": units})
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data["agent"])
        transaction = MarketTransaction(data["transaction"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].cargo = ShipCargo(data["cargo"])
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPCARGO, [self.ships[shipSymbol]]))
        return (self.agent, self.ships[shipSymbol].cargo, transaction)

    def Transfer(self, shipSymbol, symbol, units, recvShipSymbol):
        path = f"/my/ships/{shipSymbol}/transfer"
        r = self.my_req(
            path,
            "post",
            data={"tradeSymbol": symbol, "units": units,
                  "shipSymbol": recvShipSymbol},
        )
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        cargo = ShipCargo(data["cargo"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].cargo = cargo
            if self.use_db:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPCARGO, [self.ships[shipSymbol]]))
        return cargo

    # endregion

    # endregion


if __name__ == "__main__":
    st = SpaceTraders()
    st.Status()

    # pprint(st.Register("feba_66","ASTRO"))
    st.Login(os.getenv("TOKEN"))
    # pprint(st.Get_Contracts())
    # c_id = "clhmfp5wa0734s60dmss50pes"
    # st.Navigate()
    # pprint(st.Accept_Contract(c_id))
    # exit()
    # pprint(st.Register("test_9871","CULT"))
    # exit()
    # st.Get_Systems(limit=3)
    # pprint(st.Get_Waypoint("X1-AC10-73119Z"))
    # st.Get_Market("X1-JP81-52264Z")
    # exit()
    st.Init_Systems()
    # st.Purchase_Ship("SHIP_ORE_HOUND","X1-UY52-72027D")
    st.Get_Ships()
    ship = list(st.ships.values())[0]

    # survey = Survey(json.loads('{"signature": "X1-UY52-72325C-B211DC","symbol": "X1-UY52-72325C","deposits": [{"symbol": "SILVER_ORE"},{"symbol": "ICE_WATER"},{"symbol": "ICE_WATER"}],"expiration": "2023-05-21T00:15:59.841Z","size": "MODERATE"}'))
    # pprint(st.Extract(ship.symbol,survey))
    # nav, fuel = st.Navigate(ship.symbol, "X1-UY52-72325C")
    # st.sleep_till(nav)
    # st.Get_Shipyard("X1-UY52-72027D")
    # gate = st.Get_JumpGate("X1-AC10-73119Z")
    # pprint(gate.connectedSystems[0:10])
    # wps,_ = st.Get_Waypoints("X1-SR51")
    # warpGoal = ""
    # for w in wps:
    #     if st.waypoints[w].type == WaypointType.JUMP_GATE:
    #         warpGoal=w
    #         break
    # pprint(st.Jump(ship.symbol,"X1-AC10"))
    # pprint(st.Warp(ship.symbol,"X1-AC10-73119Z"))
    time.sleep(1)
    if True:
        st.cur.execute(
            """select systemsymbol from waypoints
               where 'UNCHARTED' = any(traits)
               group by systemsymbol"""
        )
        st.conn.commit()
        todo = [p[0] for p in st.cur.fetchall()]

        for t in todo:
            l, meta = st.Get_Waypoints(t)
            if meta.total > 20:
                st.Get_Waypoints(t, 2)
    if False:
        st.cur.execute(
            """select systemsymbol from waypoints
                        group by systemsymbol"""
        )
        st.conn.commit()
        known = [p[0] for p in st.cur.fetchall()]

        for syskey in st.systems.keys():
            sys = st.systems[syskey]
            if sys.symbol not in known:
                l, meta = st.Get_Waypoints(sys.symbol)
                if meta.total > 20:
                    st.Get_Waypoints(sys.symbol, 2)
    if False:
        st.cur.execute(
            """select symbol from waypoints
                        where 'SHIPYARD' = any (traits)"""
        )
        st.conn.commit()
        shipyards = [p[0] for p in st.cur.fetchall()]
        for market in shipyards:
            st.Get_Shipyard(market)
    if False:
        st.cur.execute(
            """select symbol from waypoints
                        where 'MARKETPLACE' = any (traits)"""
        )

        st.conn.commit()
        markets = [p[0] for p in st.cur.fetchall()]
        for market in markets:
            st.Get_Market(market)
    # st.Get_Market("X1-DF55-17335A")
    # pprint(st.Get_Agent())
    # pprint(st.Get_Ships())
    # pprint(st.Get_Waypoints(ship.nav.systemSymbol))
    # pprint(st.Navigate(ship.symbol,"X1-AC10-39507F"))
    # pprint(st.Get_Market("X1-AC10-39507F"))
    # pprint(st.Get_Shipyard("X1-AC10-39507F"))
    # st.Init_Systems()
    print("done")
    
    if st.use_db:
        while len(st.db_queue) > 0:
            time.sleep(3)

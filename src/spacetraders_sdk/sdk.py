from datetime import datetime
from http.client import RemoteDisconnected
import itertools
import math
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
from dotenv import load_dotenv,find_dotenv
from dataclasses import dataclass
from enum import Enum
from a_star import AStarSearch,AStarNode,CostNode
from constants import FORMAT_STR
from enums import Factions, MarketTradeGoodSupply, MarketTransactionType, ShipEngineType, ShipFrameType, ShipModuleType, ShipMountType, ShipNavFlightMode, ShipReactorType, ShipType, SystemType, TradeSymbol, WaypointType
from ratelimit import BurstyLimiter, Limiter
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
    ShipMount,
    ShipNav,
    Shipyard,
    Survey,
    System,
    Transaction,
    Waypoint,
    WaypointTraitSymbols,
    ShipNavStatus,
    ContractDeliverGood
)
from st_db import Queue_Obj_Type,Queue_Obj,DB
# from api import SpaceTradersApi

@dataclass
class Node:
    name:str
    x:int
    y:int

class SpaceTraders:
    # region variables
    # api:SpaceTradersApi

    use_db: bool
    db:DB
    
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
    waypoint_systems: dict[str, list[str]]
    surveys: dict[str, Survey]
    survey_lock = threading.Lock()
    req_lock= threading.Semaphore(1)
    miners = threading.Semaphore(3)

    # endregion

    def __init__(self,url="https://api.spacetraders.io/v2",name="ST",use_db=True,log=True) -> None:
        load_dotenv(find_dotenv(".env"))
        # self.api = SpaceTradersApi(url,name,log)
        self.name=name
        # region inits
        self.session = requests.Session()
        self.ships = {}
        self.contracts = {}
        self.waypoints = {}
        self.waypoint_systems = {}
        self.systems = {}
        self.markets = {}
        self.shipyards = {}
        self.jumpgates = {}
        self.cooldowns = {}
        self.surveys = {}
        self.factions = {}
        self.agent = Agent()
        self.token = None
        self.cur = None
        # endregion
        # region logging
        self.logger = logging.getLogger(f"SpaceTraders-{name}-{threading.current_thread().name}")
        if not self.logger.hasHandlers():
            self.logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s - %(thread)d - %(name)s - %(levelname)s - %(message)s")

            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            
            fh = logging.FileHandler(f"{os.getenv('WORKING_FOLDER')}SpaceTraders-{name}.log", encoding="utf-8")
                
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
            
            self.jumpgatenodelist = []
        # endregion

    def db_thread(self):
        self.db = DB()
        user = os.getenv("DB_USER")
        db = os.getenv("DB")
        ip = os.getenv("IP")
        port = os.getenv("PORT")

        self.conn = psycopg2.connect(dbname=db, user=user, password=os.getenv("DB_PASSWORD"), host=ip, port=port)
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cur = self.conn.cursor()
        self.db.create_enum_type("MARKETTRADEGOODSUPPLY",MarketTradeGoodSupply)
        self.db.create_enum_type("MARKETTRANSACTIONTYPE",MarketTransactionType)
        self.db.create_enum_type("SHIPENGINETYPE",ShipEngineType)
        self.db.create_enum_type("SHIPFRAMETYPE",ShipFrameType)
        self.db.create_enum_type("SHIPMOUNTTYPE",ShipMountType)
        self.db.create_enum_type("SHIPMODULETYPE",ShipModuleType)
        self.db.create_enum_type("SHIPNAVFLIGHTMODE",ShipNavFlightMode)
        self.db.create_enum_type("SHIPNAVSTATUS",ShipNavStatus)
        self.db.create_enum_type("SHIPREACTORTYPE",ShipReactorType)
        self.db.create_enum_type("SHIPTYPE",ShipType)
        self.db.create_enum_type("SYSTEMTYPE",SystemType)
        self.db.create_enum_type("TRADESYMBOL",TradeSymbol)
        self.db.create_enum_type("WAYPOINTTRAITSYMBOLS",WaypointTraitSymbols)
        self.db.create_enum_type("WAYPOINTTYPE",WaypointType)
        self.db.create_tables()
        # # endregion

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
                                if len(sys.waypoints)>0:
                                    temp.extend([sys.symbol, sys.type.name, sys.x, sys.y])
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
                        if m.transactions:
                            temp = []
                            for tr in m.transactions:
                                temp.extend([m.symbol,tr.shipSymbol,tr.tradeSymbol,tr.type.name,tr.units,tr.pricePerUnit,tr.totalPrice,tr.timestamp])
                            self.cur.execute(
                                f"""INSERT INTO TRANSACTIONS (WAYPOINTSYMBOL,SHIPSYMBOL,TRADESYMBOL,TYPE,UNITS,PRICEPERUNIT,TOTALPRICE,TIMESTAMP)
                                    VALUES {','.join([f'(%s,%s,%s,%s,%s,%s,%s,%s)' for _ in range(int(len(temp)/8))])} 
                                    ON CONFLICT (WAYPOINTSYMBOL,SHIPSYMBOL,TRADESYMBOL,TIMESTAMP) DO NOTHING""",
                                temp,
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
                            self.cur.execute(f"""INSERT INTO prices2 (WAYPOINTSYMBOL,symbol,SUPPLY,PURCHASE,SELL,TRADEVOLUME,TIMESTAMP)
                            VALUES {','.join([f'(%s, %s, %s, %s, %s, %s, %s)' for _ in range(int(len(temp)/7))])} 
                            ON CONFLICT (WAYPOINTSYMBOL, symbol) DO UPDATE 
                            SET SUPPLY = excluded.SUPPLY,
                                PURCHASE = excluded.PURCHASE,
                                SELL = excluded.SELL,
                                TRADEVOLUME = excluded.TRADEVOLUME,
                                TIMESTAMP = EXCLUDED.TIMESTAMP""",
                                list(temp))
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SHIPYARD:
                        yards: list[Shipyard] = q_obj.data
                        temp = []
                        for yard in [yards]:
                            yard:Shipyard
                            for shiptype in yard.shipTypes:
                                temp.extend([yard.symbol, shiptype.name])
                            self.cur.execute(
                                f"""INSERT INTO shipyards (symbol,shiptype)
                                VALUES  {','.join([f'(%s, %s)' for _ in range(int(len(temp)/2))])}
                                ON CONFLICT (symbol,shiptype) DO NOTHING""",
                                temp,
                            )
                            if yard.transactions:
                                temp = []
                                for t in yard.transactions:
                                    temp.extend([yard.symbol,t.shipSymbol,t.price,t.agentSymbol,t.timestamp])
                                if len(temp)>0:
                                    sql = f"""INSERT INTO SHIPYARDTRANSACTION (WAYPOINTSYMBOL, SHIPSYMBOL, PRICE, AGENTSYMBOL, TIMESTAMP)
        VALUES {','.join([f'(%s, %s, %s, %s, %s)' for _ in range(int(len(temp)/5))])}
        ON CONFLICT (WAYPOINTSYMBOL,SHIPSYMBOL,AGENTSYMBOL,TIMESTAMP) DO NOTHING"""
                                    self.cur.execute(
                                                    sql,
                                                    list(temp),
                                                )
                            if yard and yard.ships:
                                temp = []
                                for s in yard.ships:
                                    f = s.frame
                                    temp.extend([f.symbol.name,f.moduleSlots,f.fuelCapacity,f.name,f.description,f.mountingPoints,f.condition])
                                self.cur.execute(
                                                f"""INSERT INTO shipframe (symbol,moduleSlots,fuelCapacity,name,description,mountingPoints,condition)
                                                VALUES {','.join([f'(%s, %s, %s, %s, %s, %s, %s)' for _ in range(int(len(temp)/7))])}
                                                ON CONFLICT (SYMBOL) DO NOTHING""",
                                                list(temp),
                                            )
                                temp = []
                                for s in yard.ships:
                                    e = s.engine
                                    temp.extend([e.symbol.name,e.name,e.description,e.speed,e.condition])
                                self.cur.execute(
                                                f"""INSERT INTO ShipEngine (symbol,name,description,speed,condition)
                                                VALUES {','.join([f'(%s, %s, %s, %s, %s)' for _ in range(int(len(temp)/5))])}
                                                ON CONFLICT (SYMBOL) DO NOTHING""",
                                                list(temp),
                                            )
                                temp = []
                                for s in yard.ships:
                                    r = s.reactor
                                    temp.extend([r.symbol.name,r.name,r.description,r.powerOutput,r.condition])
                                self.cur.execute(
                                                f"""INSERT INTO ShipReactor (symbol,name,description,powerOutput,condition)
                                                VALUES {','.join([f'(%s, %s, %s, %s, %s)' for _ in range(int(len(temp)/5))])}
                                                ON CONFLICT (SYMBOL) DO NOTHING""",
                                                list(temp),
                                            )
                                temp = []
                                for s in yard.ships:
                                    ms = s.modules
                                    for m in ms:
                                        temp.extend([m.symbol.name,m.name,m.capacity,m.range,m.description])
                                self.cur.execute(
                                                f"""INSERT INTO ShipModule (symbol,name,capacity,range,description)
                                                VALUES {','.join([f'(%s, %s, %s, %s, %s)' for _ in range(int(len(temp)/5))])}
                                                ON CONFLICT (SYMBOL) DO NOTHING""",
                                                list(temp),
                                            )
                                temp = []
                                for s in yard.ships:
                                    ms = s.mounts
                                    for m in ms:
                                        temp.extend([m.symbol.name,m.name,m.description,m.strength])
                                self.cur.execute(
                                                f"""INSERT INTO ShipMount (symbol,name,description,strength)
                                                VALUES {','.join([f'(%s, %s, %s, %s)' for _ in range(int(len(temp)/4))])}
                                                ON CONFLICT (SYMBOL) DO NOTHING""",
                                                list(temp),
                                            )
                                temp = []
                                for s in yard.ships:
                                    temp.extend([yard.symbol,s.engine.symbol.name,s.reactor.symbol.name,s.name,s.description,[m.symbol.name for m in s.mounts] if len(s.mounts)>0 else [None],s.purchasePrice,[m.symbol.name for m in s.modules] if len(s.modules)>0 else [None],s.frame.symbol.name,s.type.name])
                                self.cur.execute(
                                                f"""INSERT INTO ShipyardShip (waypointsymbol,engine,reactor,name,description,mounts,purchasePrice,modules,frame,type)
                                                VALUES {','.join([f'(%s,%s, %s, %s, %s, %s::ShipMountType[], %s, %s::ShipModuleType[], %s, %s)' for _ in range(int(len(temp)/10))])}
                                                ON CONFLICT (waypointsymbol,type) DO NOTHING""",
                                                temp,
                                            )
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
                            f"""INSERT INTO LBCREDITS (AGENTSYMBOL, CREDITS, TIMESTAMP)
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
                                f"""INSERT INTO LBCHARTS (AGENTSYMBOL, CHARTCOUNT, TIMESTAMP)
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
                    elif q_obj.type == Queue_Obj_Type.REQUEST_METRIC:
                        data: tuple = q_obj.data

                        self.cur.execute(
                            f"""INSERT INTO REQUESTS (BEFORE,AFTER,DURATION,METHOD,ENDPOINT,STATUS_CODE,ERROR_CODE)
                                VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                            list(data),
                        )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.TRANSACTION:
                        data: tuple = q_obj.data
                        if len(data)>1 and data[0]:
                            tr:MarketTransaction = data[0]
                            self.cur.execute(
                                f"""INSERT INTO TRANSACTIONS (WAYPOINTSYMBOL,SHIPSYMBOL,TRADESYMBOL,TYPE,UNITS,PRICEPERUNIT,TOTALPRICE,TIMESTAMP)
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                                [data[1],tr.shipSymbol,tr.tradeSymbol,tr.type.name,tr.units,tr.pricePerUnit,tr.totalPrice,tr.timestamp],
                            )
                        if len(data)>2:
                            self.cur.execute(
                                f"""INSERT INTO CREDITS (TIME,AGENT,CREDITS)
                                    VALUES (%s,%s,%s)""",
                                list(data[2]),
                            )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.EXTRACTION:
                        data: tuple = q_obj.data

                        if len(data)>1:
                            self.cur.execute(
                                f"""INSERT INTO EXTRACTIONS (shipSymbol,waypointsymbol,symbol,units,survey,timestamp)
                                    VALUES (%s,%s,%s,%s,%s,%s)""",
                                list(data),
                            )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.SURVEY:
                        data: list(Survey) = q_obj.data
                        temp = []
                        for s in data:
                            s:Survey
                            temp.extend(
                                [
                                    s.signature,
                                    s.symbol,
                                    [d.symbol for d in s.deposits],
                                    datetime.strptime(s.expiration,FORMAT_STR),
                                    s.size.name,
                                    datetime.utcnow()
                                ]
                            )
                        if len(temp)>1:
                            try:
                                self.cur.execute(
                                    f"""INSERT INTO SURVEYS (signature,symbol,deposits,expiration,size,timestamp)
                                        VALUES {','.join([f'(%s, %s, %s, %s, %s, %s)' for _ in range(int(len(temp)/6))])}""",
                                    list(temp),
                                )
                            except:
                                self.logger.warning(f"did not add survey to db: {temp}")
                    elif q_obj.type == Queue_Obj_Type.SURVEY_DEPLETED:
                        data: tuple = q_obj.data

                        if len(data)>1:
                            self.cur.execute(
                                f"""INSERT INTO surveysdepleted (time, surveyid)
                                    VALUES (%s,%s)""",
                                list(data),
                            )
                        self.conn.commit()
                    elif q_obj.type == Queue_Obj_Type.RESET_WIPE:
                        
                        self.conn.close()
                        
                        user = os.getenv("DB_USER")
                        db = os.getenv("DB")
                        ip = os.getenv("IP")
                        port = os.getenv("PORT")

                        tmp = psycopg2.connect(dbname="postgres", user=user, password=os.getenv("DB_PASSWORD"), host=ip, port=port)
                        cur = tmp.cursor()
                        
                        cur.execute(f"""IALTER DATABASE test RENAME TO test_{datetime.utcnow().isoformat("YYYYMMDD")};""",)
                    elif q_obj.type == Queue_Obj_Type.JUMPGATE:
                        self.db.insert_jumpgates(q_obj.data)
                        # wp,jumpgate = q_obj.data
                        # temp = [wp,[cs.symbol for cs in jumpgate.connectedSystems]]

                        # if len(temp)>1:
                        #     self.cur.execute(
                        #         f"""INSERT INTO JumpGateConnections (waypointSymbol,connections)
                        #             VALUES {','.join([f'(%s, %s)' for _ in range(int(len(temp)/2))])} ON CONFLICT (waypointSymbol) DO NOTHING""",
                        #         list(temp),
                        #     )
                    elif q_obj.type == Queue_Obj_Type.AGENT:
                        data: tuple = q_obj.data
                        self.db.insert_agent(data)
                        # self.cur.execute(
                        #     f"""INSERT INTO AGENTS (SYMBOL, ACCOUNTID, HEADQUARTERS, STARTINGFACTION, CREDITS, TOKEN)
                        #         VALUES (%s,%s,%s,%s,%s,%s)
                        #         ON CONFLICT (SYMBOL) DO UPDATE SET CREDITS=excluded.CREDITS""",
                        #     list(data),
                        # )
                        
                # TODO add the msg to db
                # TODO add the queue-ing to all functions
            else:
                time.sleep(0.01)

    # @BurstyLimiter(Limiter(2,1.05),Limiter(10,10.5))
    def req_and_log(self, url:str, method:str, data=None, json=None):
        # before after duration method endpoint status_code error_code
        before = datetime.utcnow()
        r = self.session.request(method, self.SERVER_URL + url, data=data, json=json)
        after = datetime.utcnow()
        duration = (after-before).total_seconds()
        # self.logger.info(f"{before} {after} {duration}")
        if self.use_db:
            with self.db_lock:
                j= None
                if len(r.text)>0:
                    try:
                        j = r.json()
                    except:
                        pass
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.REQUEST_METRIC, (before,after,duration,method,url,r.status_code,(j["error"]["code"] if "error" in j else None) if j else None)))
        
        self.logger.info(f"{r.request.method} {r.request.url} {r.status_code}")
        self.logger.debug(f"{r.request.method} {r.request.url} {r.status_code} {r.text}")
        return r

    # @ratelimit.sleep_and_retry
    # @ratelimit.limits(calls=3, period=1)
    def my_req(self, url, method, data=None, json=None):
        try:
            # with self.req_lock:
            r = self.req_and_log(url, method, data, json)
            while r.status_code in [408,429,503]:
                r = self.req_and_log(url, method, data, json)
            return r
        except RemoteDisconnected as e:
            pass
        except ProtocolError as e:
            pass
        except ConnectionError as e:
            pass
        self.reset_connection()
        return self.my_req(url, method, data, json)
        # TODO add monitoring, measure time of the requests and send them to the db aswell

    def exit(self):
        if self.use_db:
            while len(self.db_queue) > 0:
                time.sleep(2)
        
        print("done")
        exit()

    def reset_connection(self):
        time.sleep(5)
        self.session = requests.session()
        if self.token!=None:
            self.Login(self.token)
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

    def get_surveys_for(self, waypointSymbol,good=None):
        with self.survey_lock:
            if good:
                keys = [k for k in self.surveys.keys() if self.surveys[k].symbol == waypointSymbol and good in [d.symbol for d in self.surveys[k].deposits]]
            else:
                keys = [k for k in self.surveys.keys() if self.surveys[k].symbol == waypointSymbol]
        return keys

    def get_survey_worth(self, survey: Survey):
        value = sum([self.worth[g.symbol]
                    for g in survey.deposits])/len(survey.deposits)
        return value

    def sort_surveys_by_worth(self, surveys: list[str]):
        with self.survey_lock:
            sortd = [(k, self.get_survey_worth(self.surveys[k])) for k in surveys if k in self.surveys]
        sortd.sort(key=lambda x: x[1], reverse=True)
        return sortd
    
    def system_from_waypoint(self,wp):
        return wp[0: wp.find("-", 4)]
    
    def get_systems_jumpgate(self,wp:str):
        if wp.count("-")>1:
            wp = self.system_from_waypoint(wp)
        
        for jg in self.jumpgates:
            if jg.startswith(wp):
                return jg
    def get_dist_waypoints(self,a:str,b:str):
        if a not in self.waypoints:
            self.Get_Waypoint(a)
        if b not in self.waypoints:
            self.Get_Waypoint(b)
        a = self.waypoints[a]
        b = self.waypoints[b]
        return self.get_dist(a,b)
    def get_dist_systems(self,a:str,b:str):
        if a not in self.systems:
            self.Get_Waypoint(a)
        if b not in self.systems:
            self.Get_Waypoint(b)
        a = self.systems[a]
        b = self.systems[b]
        return self.get_dist(a,b)
    def get_dist(self,a,b) -> float:
        """gets distance between object that have x and y variables
        if x or y does not exist: bonfire!

        Args:
            a (Any): Object 1
            b (Any): Object 2

        Returns:
            float: eucledian distance
        """
        return math.sqrt((a.x-b.x)**2+(a.y-b.y)**2)
    
    def nav_to(self, ship:Ship, goal:str):# jump through one gate and nav to location
        """jump through one gate and nav to location
            Blocking!!!
        Args:
            ship (Ship): which ship
            goal (str): where to
        """
        if ship.nav.waypointSymbol == goal:
            return
        start = ship.nav.waypointSymbol
        start_sys = self.system_from_waypoint(start)
        goal_sys = self.system_from_waypoint(goal)
        cd = self.cooldowns[ship.symbol] if ship.symbol in self.cooldowns else self.Get_Cooldown(ship.symbol)
        self.sleep_till(ship.nav)
        self.sleep_till(cooldown=cd)
        if start_sys!=goal_sys:
            if self.use_db:
                if self.jumpgatenodelist == []:
                    with self.db_lock:
                        try:
                            self.cur.execute("""select * from jumpgateconnections""")
                            # self.conn.commit()
                            gates = [(p[0],p[1]) for p in self.cur.fetchall()]
                        except:
                            
                            self.cur.execute("""select * from jumpgateconnections""")
                            # self.conn.commit()
                            gates = [(p[0],p[1]) for p in self.cur.fetchall()]
                    for g in gates:
                        system = self.systems[self.system_from_waypoint(g[0])]
                        newnode = AStarNode(system.symbol, [CostNode(self.systems[cs].symbol,self.get_dist(system,self.systems[cs]),0,[]) for cs in g[1]], system.x, system.y)
                        self.jumpgatenodelist.append(newnode)
                res = AStarSearch(start_sys, goal_sys, self.jumpgatenodelist)
                pprint(res)
                wps,_ = self.Get_Waypoints(res.path[0])
                jg = [wp for wp in wps if self.waypoints[wp].type == WaypointType.JUMP_GATE][0]
                if ship.nav.waypointSymbol != jg:
                    self.Orbit(ship.symbol)
                    n,f =self.Navigate(ship.symbol,jg)
                    self.sleep_till(nav=n)
                self.Orbit(ship.symbol)
                for p in res.path[1:]:
                    self.sleep_till(cooldown=cd)
                    cd = self.Jump(ship.symbol,p)
                
                
        if ship.nav.waypointSymbol != goal:
            self.Orbit(ship.symbol)
            nav,f = self.Navigate(ship.symbol,goal)
            self.sleep_till(nav)
        
    def nav_to_dry(self, start:str, goal:str,speed:int=30):
        """
            
        Args:
            ship (Ship): which ship
            goal (str): where to
        """
        steps = []
        fuel = 0
        t = 0
        start_sys = self.system_from_waypoint(start)
        goal_sys = self.system_from_waypoint(goal)
        if start_sys==goal_sys:
            d=self.get_dist(self.waypoints[goal],self.waypoints[start])
            fuel+=round(d)
            t+=round(round(d)*15/speed+15)
            steps.append(("NAV",goal,d))
            
        else:
            if self.use_db:
                if self.jumpgatenodelist == []:
                    with self.db_lock:
                        self.cur.execute("""select * from jumpgateconnections""")
                        # self.conn.commit()
                        gates = [(p[0],p[1]) for p in self.cur.fetchall()]
                    for g in gates:
                        system = self.systems[self.system_from_waypoint(g[0])]
                        newnode = AStarNode(system.symbol, [CostNode(self.systems[cs].symbol,self.get_dist(system,self.systems[cs]),0,[]) for cs in g[1]], system.x, system.y)
                        self.jumpgatenodelist.append(newnode)
                res = AStarSearch(start_sys, goal_sys, self.jumpgatenodelist)
                pprint(res)
                if res.path[0] not in self.waypoint_systems:
                    wps,_ = self.Get_Waypoints(res.path[0])
                    self.waypoint_systems[res.path[0]]=wps
                else:
                    wps = self.waypoint_systems[res.path[0]]
                jg = [wp for wp in wps if self.waypoints[wp].type == WaypointType.JUMP_GATE][0]
                if start != jg:
                    d=self.get_dist(self.waypoints[jg],self.waypoints[start])
                    fuel+=round(d)
                    t+=round(round(d)*15/speed+15)
                    steps.append(("NAV",start,jg,d))
                    start=jg
                
                
                for p in res.path[1:]:
                    if p not in self.waypoint_systems:
                        wps,_ = self.Get_Waypoints(p)
                        self.waypoint_systems[p]=wps
                    else:
                        wps = self.waypoint_systems[p]
                    
                    jg = [wp for wp in wps if self.waypoints[wp].type == WaypointType.JUMP_GATE][0]
                    d=self.get_dist(self.systems[p],self.systems[start_sys])
                    t+=round(d/10)
                    steps.append(("JUM",start_sys,p,d))
                    start_sys = p
                    start = jg
        
        if start != goal:
            d=self.get_dist(self.waypoints[goal],self.waypoints[start])
            fuel+=round(d)
            t+=round(round(d)*15/speed+15)
            steps.append(("NAV",start,goal,d))
        return (fuel,t,steps)
    
    def tsp0(self,points):
        best = None
        best_cost= 9e999999 # basically infinitely big
        for p in itertools.permutations(points):
            cost = 0
            # path=[p[0].name]
            for i,n in enumerate(p):
                n2 = p[i+1] if len(p)-1>i else p[0]
                d = self.get_dist(n,n2)
                t,f = self.nav_cost(30,d,ShipNavFlightMode.CRUISE)
                cost+=t
                # path.append(n2.name)
            if best_cost>cost:
                best=p
                best_cost=cost
            # print(f"{cost} {path}")
        print(f"{best_cost} {best}")
        return (best,best_cost)
    def nav_cost(self,speed,d,mode:ShipNavFlightMode):
        d = round(d)
        if mode == ShipNavFlightMode.CRUISE: fuel, t = d, round(d*15/speed+15)
        elif mode == ShipNavFlightMode.DRIFT: fuel, t = 1, round(d*150/speed+15)
        elif mode == ShipNavFlightMode.BURN: fuel, t = 2 * d, round(d*7.5/speed+15)
        else: fuel, t = d, round(d*15/speed+15)
        return (t, fuel)
    # endregion

    # region endpoints
    def Register(self, symbol: str, faction: Factions, email: str = None, login=True,raw=False):
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
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.TRANSACTION, (None,None,(datetime.utcnow(),self.agent.symbol,self.agent.credits))))
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,token)))
                
        if raw:
            return r
        return token

    def Status(self,raw=False):
        path = "/"
        r = self.my_req(path, "get")
        
        if self.use_db:
            try:
                with self.db_lock:
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.LEADERBOARD, r.json()["leaderboards"]))
            except:
                pass
        if raw:
            return r
        return r

    def Get_Agent(self,raw=False):
        path = "/my/agent"
        r = self.my_req(path, "get")
        if raw:
            return r
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data)
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.TRANSACTION, (None,None,(datetime.utcnow(),self.agent.symbol,self.agent.credits))))
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,self.token)))
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
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.JUMPGATE, (waypointSymbol,gate)))
        return gate

    # endregion

    # region Contracts
    def Get_Contracts(self, page=1, limit=20) -> tuple[list[Contract],Meta]:
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

        data = j["data"] if "data" in j else None
        self.agent = Agent(data["agent"])
        if data == None:
            return  # TODO raise error
        contract = Contract(data["contract"])
        self.contracts[contract.id] = contract
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.TRANSACTION, (None,None,(datetime.utcnow(),self.agent.symbol,self.agent.credits))))
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,self.token)))
        #     self.db_queue.append(Queue_Obj(Queue_Obj_Type.CONTRACT,contracts))
        return contract

    def Deliver_Contract(self, contractId, shipSymbol, tradeSymbol, units):
        path = f"/my/contracts/{contractId}/deliver"
        r = self.my_req(
            path,
            "post",
            data={"shipSymbol": shipSymbol, "tradeSymbol": tradeSymbol, "units": units},
        )
        j = r.json()

        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        contract = Contract(data["contract"])
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

        data = j["data"] if "data" in j else None
        self.agent = Agent(data["agent"])
        if data == None:
            return  # TODO raise error
        contract = Contract(data["contract"])
        self.contracts[contract.id] = contract
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.TRANSACTION, (None,None,(datetime.utcnow(),self.agent.symbol,self.agent.credits))))
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,self.token)))
            #     self.db_queue.append(Queue_Obj(Queue_Obj_Type.CONTRACT,contracts))
        return contract

    # endregion
    # region Factions
    def Get_Factions(self, page=1, limit=20,raw=False):
        path = f"/factions?page={page}&limit={limit}"
        r = self.my_req(path, "get")
        if raw:
            return r
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
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.FACTION, factions))
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
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.FACTION, [faction]))
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
                temp = []
                for s in self.ships:
                    f = self.ships[s].frame
                    temp.extend([f.symbol.name,f.moduleSlots,f.fuelCapacity,f.name,f.description,f.mountingPoints,f.condition])
                    self.cur.execute(
                                    f"""INSERT INTO shipframe (symbol,moduleSlots,fuelCapacity,name,description,mountingPoints,condition)
                                    VALUES {','.join([f'(%s, %s, %s, %s, %s, %s, %s)' for _ in range(int(len(temp)/7))])}
                                    ON CONFLICT (SYMBOL) DO NOTHING""",
                                    list(temp),
                                )
                temp = []
                for s in self.ships:
                    e = self.ships[s].engine
                    temp.extend([e.symbol.name,e.name,e.description,e.speed,e.condition])
                    self.cur.execute(
                                    f"""INSERT INTO ShipEngine (symbol,name,description,speed,condition)
                                    VALUES {','.join([f'(%s, %s, %s, %s, %s)' for _ in range(int(len(temp)/5))])}
                                    ON CONFLICT (symbol) DO NOTHING""",
                                    list(temp),
                                )
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
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.TRANSACTION, (None,None,(datetime.utcnow(),self.agent.symbol,self.agent.credits))))
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,self.token)))
        self.ships[ship.symbol] = ship
        return ship

    def Get_Ship(self, shipSymbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
        path = f"/my/ships/{shipSymbol}"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.ships[shipSymbol] = Ship(data)
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIP, [self.ships[shipSymbol]]))
        return self.ships[shipSymbol]

    def Get_Cargo(self, shipSymbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
        
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.SURVEY,surveys)) 
            # TODO cooldown to db
        return (surveys, cooldown)

    def Extract(self, shipSymbol, survey: Survey = None):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
                if error.code == 4224:
                    if self.use_db:
                        with self.db_lock:
                            self.db_queue.append(Queue_Obj(Queue_Obj_Type.SURVEY_DEPLETED,(datetime.utcnow(),survey.signature))) 
                with self.survey_lock:
                    if survey.signature in self.surveys:
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
                with self.db_lock: # (shipSymbol,symbol,units,survey,timestamp
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPCARGO, [self.ships[shipSymbol]]))
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.EXTRACTION, (shipSymbol,self.ships[shipSymbol].nav.waypointSymbol if shipSymbol in self.ships else None,extraction.yield_.symbol,extraction.yield_.units,survey.signature if survey else None,datetime.utcnow())))
                    
        # self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL,self.ships[shipSymbol])) # TODO cooldown to db
        return (extraction, cargo, cooldown)
    # jettison

    def Jump(self, shipSymbol, systemSymbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
        path = f"/my/ships/{shipSymbol}/jump"
        r = self.my_req(path, "post", data={"systemSymbol": systemSymbol})
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        nav = ShipNav(data["nav"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].nav = nav
        cooldown = Cooldown(data["cooldown"])
        self.cooldowns[shipSymbol] = cooldown
        self.logger.info(f"Jump: {cooldown.totalSeconds} secs for {self.get_dist(self.systems[nav.route.departure.systemSymbol],self.systems[nav.route.destination.systemSymbol])} units")
        # if self.use_db:
            # self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL,self.ships[shipSymbol])) # TODO cooldown to db
        return cooldown

    def Navigate(self, shipSymbol, waypointSymbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,self.token)))
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPCARGO, [self.ships[shipSymbol]]))
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.TRANSACTION, (transaction,self.ships[shipSymbol].nav.waypointSymbol,(datetime.utcnow(),self.agent.symbol,self.agent.credits))))
        return (self.agent, self.ships[shipSymbol].cargo, transaction)

    # scan systems
    # scan waypoints
    # scan ships
    
    def Get_Mounts(self,shipSymbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
        path = f"/my/ships/{shipSymbol}/mounts"
        r = self.my_req(path, "get")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        mounts=[]
        for d in data:
            mounts.append(ShipMount(d)) 
        
        if shipSymbol in self.ships:
            self.ships[shipSymbol].mounts = mounts
        return mounts
    def Install_Mount(self,shipSymbol,symbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
        path = f"/my/ships/{shipSymbol}/mounts/install"
        r = self.my_req(path, "post",data={"symbol": symbol})
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data["agent"])
        cargo = ShipCargo(data["cargo"])
        mounts=[]
        for d in data["mounts"]:
            mounts.append(ShipMount(d)) 
        transaction = Transaction(data["transaction"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].cargo = cargo
            self.ships[shipSymbol].mounts = mounts
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,self.token)))
        return (mounts,cargo,transaction)
    def Remove_Mount(self,shipSymbol,symbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
        path = f"/my/ships/{shipSymbol}/mounts/remove"
        r = self.my_req(path, "post",data={"symbol": symbol})
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        self.agent = Agent(data["agent"])
        cargo = ShipCargo(data["cargo"])
        mounts=[]
        for d in data["mounts"]:
            mounts.append(ShipMount(d)) 
        transaction = Transaction(data["transaction"])
        if shipSymbol in self.ships:
            self.ships[shipSymbol].cargo = cargo
            self.ships[shipSymbol].mounts = mounts
        if self.use_db:
            with self.db_lock:
                self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,self.token)))
        return (mounts,cargo,transaction)
    
    
    def Negotiate_Contract(self,shipSymbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
        path = f"/my/ships/{shipSymbol}/negotiate/contract"
        r = self.my_req(path, "post")
        j = r.json()
        data = j["data"] if "data" in j else None
        if data == None:
            return  # TODO raise error
        contract = Contract(data["contract"])
        self.contracts[contract.id]=contract
        # if self.use_db:
        #     with self.db_lock:
        #         self.db_queue.append(Queue_Obj(Queue_Obj_Type.SHIPFUEL, self.ships[shipSymbol]))
        return contract
    
    def Refuel(self, shipSymbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.TRANSACTION, (transaction,self.ships[shipSymbol].nav.waypointSymbol,(datetime.utcnow(),self.agent.symbol,self.agent.credits))))
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,self.token)))
        return (self.agent, fuel, transaction)

    def Purchase(self, shipSymbol, symbol, units):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
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
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.TRANSACTION, (transaction,self.ships[shipSymbol].nav.waypointSymbol,(datetime.utcnow(),self.agent.symbol,self.agent.credits))))
                    self.db_queue.append(Queue_Obj(Queue_Obj_Type.AGENT, (self.agent.symbol,self.agent.accountId,self.agent.headquarters,self.agent.startingFaction,self.agent.credits,self.token)))
        return (self.agent, self.ships[shipSymbol].cargo, transaction)

    def Transfer(self, shipSymbol, symbol, units, recvShipSymbol):
        if isinstance(shipSymbol,Ship):
            shipSymbol = shipSymbol.symbol
        if isinstance(recvShipSymbol,Ship):
            recvShipSymbol = recvShipSymbol.symbol
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
    
    st.exit()
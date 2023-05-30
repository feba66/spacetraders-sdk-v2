

from dataclasses import dataclass
from enum import Enum
from math import ceil
import os
import threading
from dotenv import load_dotenv

import psycopg2
from enums import WaypointType

from objects import System, Waypoint



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


    

class St_DB:
    db_queue: list[Queue_Obj]
    db_lock: threading.Lock
    
    def __init__(self) -> None:
        load_dotenv(".env")
        user = os.getenv("DB_USER")
        db = os.getenv("DB")
        ip = os.getenv("IP")
        port = os.getenv("PORT")

        self.conn = psycopg2.connect(dbname=db, user=user, password=os.getenv("DB_PASSWORD"), host=ip, port=port)
        self.cur = self.conn.cursor()
    
    def reset(self):
        self.cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        self.conn.commit()
        self.create_tables()

    def create_tables(self):
        # region Ships
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPS (SYMBOL CHARACTER varying NOT NULL, faction CHARACTER varying, ROLE CHARACTER varying, FRAME CHARACTER varying,  ENGINE CHARACTER varying,  SPEED CHARACTER varying,  MODULES CHARACTER varying[],  MOUNTS CHARACTER varying[],  cargo_capacity integer, PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPNAVS(SYMBOL CHARACTER varying NOT NULL, WAYPOINTSYMBOL CHARACTER varying, DEPARTURE CHARACTER varying, DESTINATION CHARACTER varying, ARRIVAL CHARACTER varying, DEPARTURETIME CHARACTER varying, STATUS CHARACTER varying, FLIGHTMODE CHARACTER varying, PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPCARGOS (SYMBOL CHARACTER varying, GOOD CHARACTER varying, UNITS integer, PRIMARY KEY (SYMBOL, GOOD));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPFUEL (SYMBOL CHARACTER varying, FUEL integer, CAPACITY integer, PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPCONSUMTION (SYMBOL CHARACTER varying, AMOUNT integer, DEPARTEDFROM CHARACTER varying, DESTINATION CHARACTER varying, FLIGHTMODE CHARACTER varying, FLIGHTTIME integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (SYMBOL, TIMESTAMP));")
        # endregion
        
        # region reworked tables
        self.cur.execute(f"CREATE TYPE WAYPOINTTYPE AS ENUM ({','.join([t.name_pg() for t in WaypointType])})")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SYSTEMS (SYMBOL varchar PRIMARY KEY,TYPE WAYPOINTTYPE,X integer, Y integer);")
        
        self.cur.execute("CREATE TABLE IF NOT EXISTS CREDITLEADERBOARD (AGENTSYMBOL CHARACTER varying, CREDITS integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS CHARTLEADERBOARD (AGENTSYMBOL CHARACTER varying, CHARTCOUNT integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS FACTIONS (SYMBOL CHARACTER varying NOT NULL, name CHARACTER varying, description CHARACTER varying, headquarters CHARACTER varying,  traits CHARACTER varying[], PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SURVEYS (signature CHARACTER varying,symbol CHARACTER varying,deposits CHARACTER varying[],expiration CHARACTER varying,size CHARACTER varying,timestamp CHARACTER varying,PRIMARY KEY (signature))")
        self.cur.execute("CREATE TABLE IF NOT EXISTS EXTRACTIONS (shipSymbol CHARACTER varying,symbol CHARACTER varying,units CHARACTER varying[],timestamp CHARACTER varying, PRIMARY KEY (shipSymbol,timestamp))")
        self.conn.commit()
        # endregion
        
        # after this comment sql needs formatting
        self.cur.execute("CREATE TABLE IF NOT EXISTS waypoints (systemSymbol varchar, symbol varchar PRIMARY KEY, type varchar, x integer,y integer,orbitals varchar[],traits varchar[],chart varchar,faction varchar);")
        
        self.cur.execute("CREATE TABLE IF NOT EXISTS markets (symbol varchar, good varchar, type varchar, PRIMARY KEY (symbol, good, type));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS shipyards (symbol varchar, shiptype varchar, PRIMARY KEY (symbol, shiptype));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS prices (waypointsymbol varchar, symbol varchar, supply varchar, purchase integer, sell integer,tradevolume integer,timestamp varchar, PRIMARY KEY (waypointsymbol, symbol,timestamp));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS transactions (WAYPOINTSYMBOL varchar, SHIPSYMBOL varchar, TRADESYMBOL varchar, TYPE varchar, UNITS integer, PRICEPERUNIT integer, TOTALPRICE integer, timestamp varchar, PRIMARY KEY (WAYPOINTSYMBOL,TRADESYMBOL,SHIPSYMBOL, timestamp));")

    def queue_add(self,obj:Queue_Obj):
        with self.db_lock:
            self.db_queue.append(obj)
    
    def waypoints(self,q_obj:Queue_Obj):
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
            temp)
        self.conn.commit()
    def systems(self,q_obj: Queue_Obj):
        systems: list[System] = q_obj.data
        for i in range(ceil(len(systems) / 1000)):
            temp = []
            for sys in systems[i * 1000: min((i + 1) * 1000, len(systems))]:
                temp.extend([sys.symbol, sys.type.name, sys.x, sys.y])
            self.cur.execute(
                f"""INSERT INTO systems (symbol, type, x,y)
            VALUES {','.join([f'(%s, %s, %s, %s)' for _ in range(int(len(temp)/4))])} 
            ON CONFLICT (symbol) DO NOTHING""",
                temp)
        self.conn.commit()
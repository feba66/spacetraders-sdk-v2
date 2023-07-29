from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
import threading
import time
from dotenv import find_dotenv, load_dotenv
import psycopg2
from sqlalchemy import create_engine,Engine,text,Connection
from sqlalchemy.orm import sessionmaker
from space_traders_enums import myEnum
from space_traders_objects import Agent,Contract,Ship
from space_traders_enums import MarketTradeGoodSupply,ContractType,FactionSymbol,FactionTraitSymbol,MarketTransactionType,ShipCrewRotation,ShipEngineType,ShipFrameType,ShipModuleType,ShipMountType,ShipNavFlightMode,ShipNavStatus,ShipReactorType,ShipType,SurveySize,SystemType,TradeSymbol,WaypointTraitSymbols,WaypointType
from space_traders_db_schema import Base

class Queue_Obj_Type(Enum):
    AGENT = 19
    CONSUMPTION = 1
    EXTRACTION = 2
    FACTION = 3
    JUMPGATE = 18
    LEADERBOARD = 4
    MARKET = 5
    REQUEST_METRIC = 6
    RESET_WIPE = 7
    SHIP = 8
    SHIPCARGO = 9
    SHIPFUEL = 10
    SHIPNAV = 11
    SHIPYARD = 12
    SURVEY = 13
    SURVEY_DEPLETED = 14
    SYSTEM = 15
    TRANSACTION = 16
    WAYPOINT = 17
    CONTRACT = 20


@dataclass
class Queue_Obj:
    type: Queue_Obj_Type
    data: object


class SpaceTradersDB:
    db_lock: threading.Lock
    db_queue: list[Queue_Obj]
    conn: any
    cur: any
    engine:Engine
    Session:sessionmaker

    def __init__(self,) -> None:
        load_dotenv(find_dotenv(".env"))
        self.db_lock = threading.Lock()
        self.db_queue = []

        user = os.getenv("DB_USER")
        db = os.getenv("DB")
        ip = os.getenv("IP")
        port = os.getenv("PORT")

        self.connect(user, db, ip, port)

    def connect(self, user, db, ip, port):
        self.conn = psycopg2.connect(dbname=db, user=user, password=os.getenv("DB_PASSWORD"), host=ip, port=port)
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cur = self.conn.cursor()
        self.engine = create_engine(f"postgresql+psycopg2://{user}:{os.getenv('DB_PASSWORD')}@{ip}:{port}/{db}_test",echo=True)
        self.Session = sessionmaker(self.engine)
        Base.metadata.create_all(self.engine)
        
    def run(self):
        self.create_enum_type("MARKETTRADEGOODSUPPLY",MarketTradeGoodSupply)
        self.create_enum_type("MARKETTRANSACTIONTYPE",MarketTransactionType)
        self.create_enum_type("SHIPENGINETYPE",ShipEngineType)
        self.create_enum_type("SHIPFRAMETYPE",ShipFrameType)
        self.create_enum_type("SHIPMOUNTTYPE",ShipMountType)
        self.create_enum_type("SHIPMODULETYPE",ShipModuleType)
        self.create_enum_type("SHIPNAVFLIGHTMODE",ShipNavFlightMode)
        self.create_enum_type("SHIPNAVSTATUS",ShipNavStatus)
        self.create_enum_type("SHIPREACTORTYPE",ShipReactorType)
        self.create_enum_type("SHIPTYPE",ShipType)
        self.create_enum_type("SYSTEMTYPE",SystemType)
        self.create_enum_type("TRADESYMBOL",TradeSymbol)
        self.create_enum_type("WAYPOINTTRAITSYMBOLS",WaypointTraitSymbols)
        self.create_enum_type("WAYPOINTTYPE",WaypointType)
        self.create_tables()
        while True:
            tmp: list[Queue_Obj] = []
            if len(self.db_queue) > 0:
                with self.db_lock:
                    for _ in range(min(len(self.db_queue), 5)):
                        tmp.append(self.db_queue.pop(0))
                while len(tmp) > 0:
                    q_obj = tmp.pop(0)
                    print(q_obj.type)
                    if q_obj.type == Queue_Obj_Type.SHIP:
                        self.insert_ships(q_obj.data)
                    elif q_obj.type == Queue_Obj_Type.SHIPFUEL:
                        self.insert_ships_fuel(q_obj.data)
                    elif q_obj.type == Queue_Obj_Type.SHIPCARGO:
                        self.insert_ships_cargo(q_obj.data)
                    elif q_obj.type == Queue_Obj_Type.SHIPNAV:
                        self.insert_ships_nav(q_obj.data)
                    elif q_obj.type == Queue_Obj_Type.AGENT:
                        self.insert_agent(q_obj.data[0],q_obj.data[1])
                    else:
                        print(q_obj.type + "Not Implemented into DB!")
            else:
                time.sleep(0.01)
    

    def create_enum_type(self, name, enum: myEnum):
        self.cur.execute(
            f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({','.join([t.name_pg() for t in enum])}); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    def create_tables(self):
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHIPREQUIREMENTS (SYMBOL VARCHAR PRIMARY KEY,POWER INTEGER,CREW INTEGER,SLOTS INTEGER)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHIPFRAME (SYMBOL SHIPFRAMETYPE PRIMARY KEY,MODULESLOTS INT,FUELCAPACITY INT,NAME VARCHAR,DESCRIPTION VARCHAR,MOUNTINGPOINTS INT,CONDITION INT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHIPENGINE (SYMBOL SHIPENGINETYPE PRIMARY KEY,NAME VARCHAR,DESCRIPTION VARCHAR,SPEED INT,CONDITION INT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHIPREACTOR (SYMBOL SHIPREACTORTYPE PRIMARY KEY,NAME VARCHAR,DESCRIPTION VARCHAR,POWEROUTPUT INT,CONDITION INT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHIPMODULE (SYMBOL SHIPMODULETYPE PRIMARY KEY,NAME VARCHAR,CAPACITY INT,RANGE INT,DESCRIPTION VARCHAR)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHIPMOUNT (SYMBOL SHIPMOUNTTYPE PRIMARY KEY,NAME VARCHAR,DESCRIPTION VARCHAR,STRENGTH INT)")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPYARDSHIP (TYPE SHIPTYPE ,waypointsymbol varchar ,ENGINE SHIPENGINETYPE,REACTOR SHIPREACTORTYPE,NAME VARCHAR,DESCRIPTION VARCHAR,MOUNTS SHIPMOUNTTYPE[],PURCHASEPRICE INT,MODULES SHIPMODULETYPE[],FRAME SHIPFRAMETYPE, primary key (TYPE,waypointsymbol))")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPYARDTRANSACTION (WAYPOINTSYMBOL VARCHAR, SHIPSYMBOL VARCHAR, PRICE INT, AGENTSYMBOL VARCHAR,TIMESTAMP TIMESTAMP WITHOUT TIME ZONE,PRIMARY KEY (WAYPOINTSYMBOL,SHIPSYMBOL,AGENTSYMBOL,TIMESTAMP))")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS JUMPGATECONNECTIONS (WAYPOINTSYMBOL VARCHAR, CONNECTIONS VARCHAR[], PRIMARY KEY (WAYPOINTSYMBOL))")

        self.cur.execute("CREATE TABLE IF NOT EXISTS waypoints (systemSymbol varchar, symbol varchar PRIMARY KEY, type varchar, x integer,y integer,orbitals varchar[],traits varchar[],chart varchar,faction varchar);")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS systems (symbol varchar PRIMARY KEY, type varchar, x integer, y integer);")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS markets (symbol varchar, good varchar, type varchar, PRIMARY KEY (symbol, good, type));")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS shipyards (symbol varchar, shiptype varchar, PRIMARY KEY (symbol, shiptype));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS prices (waypointsymbol varchar, symbol varchar, supply varchar, purchase integer, sell integer,tradevolume integer,timestamp timestamp without time zone, PRIMARY KEY (waypointsymbol, symbol,timestamp));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS prices2 (waypointsymbol varchar, symbol varchar, supply varchar, purchase integer, sell integer,tradevolume integer,timestamp timestamp without time zone, PRIMARY KEY (waypointsymbol, symbol));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS TRANSACTIONS (WAYPOINTSYMBOL VARCHAR,SHIPSYMBOL VARCHAR,TRADESYMBOL TRADESYMBOL,TYPE VARCHAR,UNITS INTEGER,PRICEPERUNIT INTEGER,TOTALPRICE INTEGER,TIMESTAMP TIMESTAMP WITHOUT TIME ZONE,PRIMARY KEY (WAYPOINTSYMBOL,TRADESYMBOL,SHIPSYMBOL,TIMESTAMP));")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS AGENTS (SYMBOL VARCHAR, ACCOUNTID VARCHAR,HEADQUARTERS VARCHAR, STARTINGFACTION VARCHAR, CREDITS VARCHAR, TOKEN VARCHAR, PRIMARY KEY (SYMBOL));")

        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPS (SYMBOL varchar NOT NULL, faction varchar, ROLE varchar, FRAME varchar,  ENGINE varchar,  SPEED varchar,  MODULES varchar[],  MOUNTS varchar[],  cargo_capacity integer, PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPNAVS(SYMBOL varchar NOT NULL, WAYPOINTSYMBOL varchar, DEPARTURE varchar, DESTINATION varchar, ARRIVAL varchar, DEPARTURETIME varchar, STATUS varchar, FLIGHTMODE varchar, PRIMARY KEY (SYMBOL));")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHIPCARGOS (SYMBOL varchar, GOOD varchar, UNITS integer, PRIMARY KEY (SYMBOL, GOOD));")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHIPFUEL (SYMBOL varchar, FUEL integer, CAPACITY integer, PRIMARY KEY (SYMBOL));")
        self.cur.execute("CREATE TABLE IF NOT EXISTS SHIPCONSUMTION (SYMBOL varchar, AMOUNT integer, DEPARTEDFROM varchar, DESTINATION varchar, FLIGHTMODE varchar, FLIGHTTIME integer, TIMESTAMP timestamp without time zone, PRIMARY KEY (SYMBOL, TIMESTAMP));")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS LBCREDITS (AGENTSYMBOL varchar, CREDITS integer, TIMESTAMP timestamp without time zone, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS LBCHARTS (AGENTSYMBOL varchar, CHARTCOUNT integer, TIMESTAMP timestamp without time zone, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS FACTIONS (SYMBOL varchar NOT NULL, name varchar, description varchar, headquarters varchar,  traits varchar[], PRIMARY KEY (SYMBOL));")
        self.cur.execute(
            """CREATE TABLE IF NOT EXISTS SURVEYS (signature varchar,symbol varchar,deposits varchar[],expiration varchar,size varchar,"timestamp" timestamp without time zone)""")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS EXTRACTIONS (shipSymbol varchar,waypointsymbol varchar,symbol varchar,units integer, survey varchar, timestamp timestamp without time zone)")
        self.cur.execute("CREATE TABLE IF NOT EXISTS requests(before timestamp without time zone,after timestamp without time zone,duration numeric,method varchar,endpoint varchar,status_code integer,error_code integer)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS credits(time timestamp without time zone,agent varchar,credits integer)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS surveysdepleted(time timestamp without time zone,surveyid varchar)")

    def reset(self):

        self.conn.close()

        user = os.getenv("DB_USER")
        db = os.getenv("DB")
        ip = os.getenv("IP")
        port = os.getenv("PORT")

        tmp = psycopg2.connect(dbname="postgres", user=user, password=os.getenv("DB_PASSWORD"), host=ip, port=port)
        cur = tmp.cursor()

        cur.execute(f"""ALTER DATABASE test RENAME TO test_{datetime.utcnow().year}_{datetime.utcnow().month}_{datetime.utcnow().day};""",)
        cur.close()
        tmp.close()
        self.connect(user,db,ip,port)

    def insert_jumpgates(self, data):
        wp, jumpgate = data
        temp = [wp, [cs.symbol for cs in jumpgate.connectedSystems]]

        if len(temp) > 1:
            self.cur.execute(
                f"""INSERT INTO JumpGateConnections (waypointSymbol,connections)
                VALUES {','.join([f'(%s, %s)' for _ in range(int(len(temp)/2))])} ON CONFLICT (waypointSymbol) DO NOTHING""",
                list(temp),
            )

    def insert_agent(self, agent:Agent,token:str):
        self.cur.execute(
            f"""INSERT INTO AGENTS (SYMBOL, ACCOUNTID, HEADQUARTERS, STARTINGFACTION, CREDITS, TOKEN)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (SYMBOL) DO UPDATE SET CREDITS=excluded.CREDITS""",
            [agent.symbol,agent.accountId,agent.headquarters,agent.startingFaction,agent.credits,token],
        )
    def insert_ships(self, ships:list[Ship]):
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
            temp
        )
        self.insert_ships_fuel(ships)
        self.insert_ships_cargo(ships)
    def insert_ships_fuel(self,ships: list[Ship]):
        temp = []
        for s in ships:
            temp.extend([s.symbol, s.fuel.current, s.fuel.capacity])
        self.cur.execute(
            f"""INSERT INTO SHIPFUEL (SYMBOL, FUEL, CAPACITY)
        VALUES {','.join([f'(%s,%s,%s)' for _ in range(int(len(temp)/3))])}
        ON CONFLICT (SYMBOL) DO UPDATE SET FUEL=excluded.FUEL""",
            list(temp),
        )
    def insert_ships_cargo(self,ships: list[Ship]):
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
    def insert_ships_nav(self,ships: list[Ship]):
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
    
    
if __name__ == "__main__":
    db = SpaceTradersDB()
    result = db.al_conn.execute(text("select * from agents"))
    db.al_conn.commit()
    print(result.all())
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
import threading
from dotenv import find_dotenv, load_dotenv
import psycopg2

from enums import myEnum


class Queue_Obj_Type(Enum):
    CONSUMPTION = 1
    EXTRACTION = 2
    FACTION = 3
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
    JUMPGATE = 18
    AGENT = 19


@dataclass
class Queue_Obj:
    type: Queue_Obj_Type
    data: object


class DB:
    db_lock: threading.Lock
    db_queue: list[Queue_Obj]
    conn: any
    cur: any

    def __init__(self) -> None:
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

    def insert_agent(self, data):
        self.cur.execute(
            f"""INSERT INTO AGENTS (SYMBOL, ACCOUNTID, HEADQUARTERS, STARTINGFACTION, CREDITS, TOKEN)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (SYMBOL) DO UPDATE SET CREDITS=excluded.CREDITS""",
            list(data),
        )

    def insert_jumpgates(self, data):
        wp, jumpgate = data
        temp = [wp, [cs.symbol for cs in jumpgate.connectedSystems]]

        if len(temp) > 1:
            self.cur.execute(
                f"""INSERT INTO JumpGateConnections (waypointSymbol,connections)
                    VALUES {','.join([f'(%s, %s)' for _ in range(int(len(temp)/2))])} ON CONFLICT (waypointSymbol) DO NOTHING""",
                list(temp),
            )

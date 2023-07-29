
import os
from pprint import pprint
from typing import Optional

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import BigInteger, Integer, String, create_engine, text
from sqlalchemy.orm import sessionmaker,DeclarativeBase,Mapped,mapped_column,relationship
from space_traders_db_schema import  Base,Agent, Faction, FactionTrait
from space_traders_api import SpaceTradersApi as STApi
from space_traders_enums import FactionSymbol
load_dotenv(find_dotenv(".env"))


user = os.getenv("DB_USER")
db = os.getenv("DB")
ip = os.getenv("IP")
port = os.getenv("PORT")

engine = create_engine(f"postgresql+psycopg2://{user}:{os.getenv('DB_PASSWORD')}@{ip}:{port}/{db}_test",echo=True)

# Base.metadata.clear()
# Base.metadata.create_all(engine)

Session = sessionmaker(engine)
with Session() as s:
    api = STApi()
    # r = api.register("FEBATEST17",Factions.GALACTIC)
    # j = r.json()["data"]
    # d_agent = j["agent"]
    # token = j["token"]
    # agent = Agent(accountId = d_agent["accountId"],symbol = d_agent["symbol"],headquarters = d_agent["headquarters"],credits = d_agent["credits"],startingFaction = d_agent["startingFaction"],token=token)
    # res = s.execute(text("select * from agents"))
    # agent = Agent(accountId = "asdiuasid2",symbol = "testname",headquarters = "headquarter",credits = 150000,startingFaction = "ASTRO")
    # s.add(agent)
    r = api.get_faction("ASTRO")
    d = r.json()["data"]
    faction = Faction(symbol=d["symbol"],description=d["description"],headquarters=d["headquarters"],isRecruiting=d["isRecruiting"],traits=[])
    faction.traits.extend([FactionTrait(symbol=t["symbol"],name=t["name"],description=t["description"]) for t in d["traits"]])
    pprint(d)
    # a = A()
    # a.b.append(B())
    # s.add(a)
    s.add(faction)
    s.commit()
    # res = s.execute(text("select * from agents"))
    # print(res.all())
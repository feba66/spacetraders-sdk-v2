
from pprint import pprint
import time
from space_traders_api import SpaceTradersApi as STApi
from space_traders_enums import FactionSymbol
from space_traders_db import SpaceTradersDB,Queue_Obj,Queue_Obj_Type

import logging
import threading
import os

from space_traders_logger import SpaceTradersLogger
from space_traders_objects import Agent,Contract,Faction,Ship


class SpaceTraders:
    db: SpaceTradersDB
    log:bool
    name:str
    logger:SpaceTradersLogger
    api:STApi
    agent:Agent
    contracts:dict[str,Contract]
    ships:dict[str,Ship]

    def __init__(self,url="https://api.spacetraders.io/v2", name="ST",log=True,use_db=True) -> None:
        self.name=name
        self.log=log
        self.use_db=use_db
        if log:
            self.logger=SpaceTradersLogger("st-sdk")
        if use_db:
            self.db = SpaceTradersDB()
            self.t_db = threading.Thread(target=self.db.run)
            self.t_db.daemon=True
            self.t_db.start()
        self.api=STApi(log=log,name=name,url=url)
        self.contracts = {}
        self.ships = {}
        
    def exit(self):
        if self.use_db:
            while len(self.db.db_queue) > 0:
                time.sleep(2)
        
        print("done")
        exit()



    def register(self, symbol: str, faction: FactionSymbol, email: str = None, login=True):
        r = self.api.register(symbol,faction,email,login)
        d = r.json()["data"]
        agent = Agent(d["agent"])
        contract = Contract(d["contract"])
        faction = Faction(d["faction"])
        ship = Ship(d["ship"])
        token = d["token"]

        self.agent=Agent
        self.ships[ship.symbol]=ship
        self.contracts[contract.id]=contract
        if self.use_db:
            with self.db.db_lock:
                self.db.db_queue.extend([Queue_Obj(Queue_Obj_Type.SHIP,[ship]),Queue_Obj(Queue_Obj_Type.AGENT,(agent,token))])
            # TODO contract
        return agent,contract,faction,ship,token

    

if __name__ == "__main__":
    st = SpaceTraders()
    a,c,f,s,t = st.register("TESTFEBA9",FactionSymbol.GALACTIC)
    # pprint(a)
    # pprint(c)
    # pprint(f)
    # pprint(s)
    pprint(t)
    time.sleep(3)
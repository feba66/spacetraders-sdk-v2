from http.client import RemoteDisconnected
from urllib3.exceptions import ProtocolError
from requests.exceptions import ConnectionError
import threading
import time
import logging
import requests
import json
import os
from space_traders_enums import FactionSymbol
from ratelimit import BurstyLimiter, Limiter
from space_traders_helper import system_symbol_from_waypoint_symbol
from space_traders_logger import SpaceTradersLogger


class SpaceTradersApi:

	# region variables
	server_url: str
	name: str
	session: requests.Session
	logger: SpaceTradersLogger
	log:bool
	token: str
	# endregion

	def __init__(self,url="https://api.spacetraders.io/v2",name="ST",log=True) -> None:
		# region inits
		self.name=name
		self.server_url = url
		self.log = log
		self.session = requests.Session()
		self.token = None
		# endregion

		# region logging
		if log:
			self.logger=SpaceTradersLogger("st-api")
		# endregion


	@BurstyLimiter(Limiter(2,1.05),Limiter(10,10.5))
	def req_and_log(self, url: str, method: str, data=None, json=None):
		r = self.session.request(method, self.server_url + url, data=data, json=json)
		if self.log:
			self.logger.info(f"{r.request.method} {r.request.url} {r.status_code}")
			self.logger.debug(f"{r.request.method} {r.request.url} {r.status_code} {r.text}")
		return r

	def my_req(self, url, method, data=None, json=None):
		try:
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


	def reset_connection(self):
		time.sleep(5)
		self.session = requests.session()
		if self.token!=None:
			self.Login(self.token)

	def Login(self, token):
		self.token=token
		self.session.headers.update({"Authorization": "Bearer " + token})

	# region endpoints
	def register(self, symbol: str, faction: FactionSymbol, email: str = None, login=True):
		path = "/register"
		if 3 > len(symbol) > 14:
			raise ValueError("symbol must be 3-14 characters long")
		data = {"symbol": symbol, "faction": faction}
		if email:
			data["email"]=email
		r = self.my_req(path, "post", data=data)

		j = r.json()
		data = j["data"] if "data" in j else None
		if not data:
			raise Exception(r)
		token = data["token"]
		if login:
			self.Login(token)
		return r

	def status(self):
		path = "/"
		r = self.my_req(path, "get")
		return r

	def get_my_agent(self):
		path = "/my/agent"
		r = self.my_req(path, "get")
		return r

	def get_agents(self, page=1, limit=20):
		path = f"/agents"
		r = self.my_req(path + f"?page={page}&limit={limit}", "get")
		return r
	def get_agent(self, agent_symbol: str):
		path = f"/agents/{agent_symbol}"
		r = self.my_req(path, "get")
		return r

	# region Systems
	def get_systems(self, page=1, limit=20):
		path = f"/systems"
		r = self.my_req(path + f"?page={page}&limit={limit}", "get")
		return r

	def init_systems(self) -> dict:
		path = "/systems.json"

		if not os.path.exists("systems.json"): # TODO smarter caching
			r = self.my_req(path, "get")
			with open("systems.json", "w") as f:
				f.write(r.text)
			j = r.json()
		else:
			with open("systems.json", "r") as f:
				j = json.load(f)

		return j

	def get_system(self, system_symbol: str):
		path = f"/systems/{system_symbol}"
		r = self.my_req(path, "get")
		return r

	def get_waypoints(self, system_symbol: str, page=1, limit=20):
		path = f"/systems/{system_symbol}/waypoints"
		r = self.my_req(path + f"?page={page}&limit={limit}", "get")
		return r

	def get_waypoint(self, waypoint_symbol: str):
		system_symbol = system_symbol_from_waypoint_symbol(waypoint_symbol)
		path = f"/systems/{system_symbol}/waypoints/{waypoint_symbol}"
		r = self.my_req(path, "get")
		return r

	def get_market(self, waypoint_symbol: str):
		system_symbol = system_symbol_from_waypoint_symbol(waypoint_symbol)
		path = f"/systems/{system_symbol}/waypoints/{waypoint_symbol}/market"
		r = self.my_req(path, "get")
		return r

	def get_shipyard(self, waypoint_symbol: str):
		system_symbol = system_symbol_from_waypoint_symbol(waypoint_symbol)
		path = f"/systems/{system_symbol}/waypoints/{waypoint_symbol}/shipyard"
		r = self.my_req(path, "get")
		return r

	def get_jumpgate(self, waypoint_symbol: str):
		system_symbol = system_symbol_from_waypoint_symbol(waypoint_symbol)
		path = f"/systems/{system_symbol}/waypoints/{waypoint_symbol}/jump-gate"
		r = self.my_req(path, "get")
		return r

	# endregion

	# region Contracts
	def get_contracts(self, page=1, limit=20):
		path = f"/my/contracts?page={page}&limit={limit}"
		r = self.my_req(path, "get")
		return r

	def get_contract(self, contract_id: str):
		path = f"/my/contracts/{contract_id}"
		r = self.my_req(path, "get")
		return r

	def accept_contract(self, contract_id: str):
		path = f"/my/contracts/{contract_id}/accept"
		r = self.my_req(path, "post")
		return r

	def deliver_contract(self, contract_id: str, ship_symbol: str, trade_symbol: str, units: int):
		path = f"/my/contracts/{contract_id}/deliver"
		r = self.my_req(path,"post",data={"shipSymbol": ship_symbol, "tradeSymbol": trade_symbol, "units": units})
		return r

	def fulfill_contract(self, contract_id: str):
		path = f"/my/contracts/{contract_id}/fulfill"
		r = self.my_req(path, "post")
		return r

	# endregion
	# region Factions
	def get_factions(self, page=1, limit=20):
		path = f"/factions?page={page}&limit={limit}"
		r = self.my_req(path, "get")
		return r

	def get_faction(self, faction_symbol):
		path = f"/factions/{faction_symbol}"
		r = self.my_req(path, "get")
		return r
	# endregion

	# region Fleet
	def get_ships(self, page=1, limit=20):
		path = "/my/ships"
		r = self.my_req(path + f"?page={page}&limit={limit}", "get")
		return r

	def purchase_ship(self, ship_type: str, waypoint_symbol: str):
		path = "/my/ships"
		r = self.my_req(
			path, "post", data={"shipType": ship_type, "waypointSymbol": waypoint_symbol}
		)
		return r

	def get_ship(self, ship_symbol: str):
		path = f"/my/ships/{ship_symbol}"
		r = self.my_req(path, "get")
		return r

	def get_cargo(self, ship_symbol: str):
		path = f"/my/ships/{ship_symbol}/cargo"
		r = self.my_req(path, "get")
		return r

	def orbit(self, ship_symbol: str):
		path = f"/my/ships/{ship_symbol}/orbit"
		r = self.my_req(path, "post")
		return r

	# refine
	def chart(self, ship_symbol: str):
		path = f"/my/ships/{ship_symbol}/chart"
		r = self.my_req(path, "post")
		return r

	def get_cooldown(self, ship_symbol: str):
		path = f"/my/ships/{ship_symbol}/cooldown"
		r = self.my_req(path, "get")
		return r

	def dock(self, ship_symbol: str):
		path = f"/my/ships/{ship_symbol}/dock"
		r = self.my_req(path, "post")
		return r

	def create_survey(self, ship_symbol: str):
		path = f"/my/ships/{ship_symbol}/survey"
		r = self.my_req(path, "post")
		return r

	def extract(self, ship_symbol: str, survey: dict):
		path = f"/my/ships/{ship_symbol}/extract"
		r = self.my_req(path, "post", json={"survey": survey}) if survey else self.my_req(path, "post")
		return r
	# jettison

	def jump(self, ship_symbol: str, system_symbol: str):
		path = f"/my/ships/{ship_symbol}/jump"
		r = self.my_req(path, "post", data={"systemSymbol": system_symbol})
		return r

	def navigate(self, ship_symbol: str, waypoint_symbol: str):
		path = f"/my/ships/{ship_symbol}/navigate"
		r = self.my_req(path, "post", data={"waypointSymbol": waypoint_symbol})
		return r

	def warp(self, ship_symbol: str, waypoint_symbol: str):
		path = f"/my/ships/{ship_symbol}/warp"
		r = self.my_req(path, "post", data={"waypointSymbol": waypoint_symbol})
		return r

	def sell(self, ship_symbol: str, symbol: str, units: int):
		path = f"/my/ships/{ship_symbol}/sell"
		r = self.my_req(path, "post", data={"symbol": symbol, "units": units})
		return r
	# scan systems
	# scan waypoints
	# scan ships

	def get_mounts(self,ship_symbol: str):
		path = f"/my/ships/{ship_symbol}/mounts"
		r = self.my_req(path, "get")
		return r

	def install_mount(self,ship_symbol: str,symbol: str):
		path = f"/my/ships/{ship_symbol}/mounts/install"
		r = self.my_req(path, "post",data={"symbol": symbol})
		return r

	def remove_mount(self,ship_symbol: str,symbol: str):
		path = f"/my/ships/{ship_symbol}/mounts/remove"
		r = self.my_req(path, "post",data={"symbol": symbol})
		return r

	def negotiate_contract(self,ship_symbol: str):
		path = f"/my/ships/{ship_symbol}/negotiate/contract"
		r = self.my_req(path, "post")
		return r

	def refuel(self, ship_symbol: str,fuel_units: int):
		path = f"/my/ships/{ship_symbol}/refuel"
		r = self.my_req(path, "post",data={"units":fuel_units})
		return r

	def purchase(self, ship_symbol: str, symbol: str, units: int):
		path = f"/my/ships/{ship_symbol}/purchase"
		r = self.my_req(path, "post", data={"symbol": symbol, "units": units})
		return r

	def transfer(self, ship_symbol: str, symbol: str, units: int, recv_ship_symbol: str):
		path = f"/my/ships/{ship_symbol}/transfer"
		r = self.my_req(path, "post", data={"tradeSymbol": symbol, "units": units, "shipSymbol": recv_ship_symbol})
		return r

	# endregion

	# endregion

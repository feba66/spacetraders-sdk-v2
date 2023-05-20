# spacetraders-sdk-v2
Total rewrite to use no generated code

## Installation & Usage
```sh
pip install -r requirements.txt
py api.py
```
## TODO

- [ ] redo all endpoints
- [x] logging
- [ ] database connections
- [ ] error handling
- [ ] add monitoring, measure time of the requests and send them to the db aswell
- [ ] add cooldown to database
- [ ] add contracts to database
- [ ] add survey to database

## Documentation for API Endpoints

Class          | HTTP request  | Description   | Implemented
------------   | ------------- | ------------- | -------------
|              | **get** /     | Status        | leaderboard db
|              | **post** /register | Register New Agent | statekeeping
| *Agents*     | **get** /my/agent | Fetch your agent's details. | statekeeping
| *Contracts*  | **get** /my/contracts | List all of your contracts. | statekeeping 
| *Contracts*  | **get** /my/contracts/{contractId} | Get the details of a contract by ID. | statekeeping 
| *Contracts*  | **post** /my/contracts/{contractId}/accept | Accept a contract. | statekeeping
| *Contracts*  | **post** /my/contracts/{contractId}/deliver | Deliver cargo on a given contract. | statekeeping & db/2
| *Contracts*  | **post** /my/contracts/{contractId}/fulfill | Fulfill a contract | statekeeping
| *Factions*   | **get** /factions | List all discovered factions in the game. | statekeeping & db
| *Factions*   | **get** /factions/{factionSymbol} | View the details of a faction. | statekeeping & db
| *Fleet*      | **get** /my/ships | Retrieve all of your ships. | statekeeping & db
| *Fleet*      | **post** /my/ships | Purchase a ship | statekeeping & db/2
| *Fleet*      | **get** /my/ships/{shipSymbol} | Retrieve the details of your ship. |  statekeeping & db
| *Fleet*      | **get** /my/ships/{shipSymbol}/cargo | Retrieve the cargo of your ship. |  statekeeping & db
| *Fleet*      | **post** /my/ships/{shipSymbol}/orbit | Orbit Ship | statekeeping & db
| *Fleet*      | **post** /my/ships/{shipSymbol}/refine | Ship Refine | 
| *Fleet*      | **post** /my/ships/{shipSymbol}/chart | Create Chart | statekeeping & db
| *Fleet*      | **get** /my/ships/{shipSymbol}/cooldown | Get Ship Cooldown | statekeeping
| *Fleet*      | **post** /my/ships/{shipSymbol}/dock | Dock Ship | statekeeping & db
| *Fleet*      | **post** /my/ships/{shipSymbol}/survey | Create Survey | statekeeping
| *Fleet*      | **post** /my/ships/{shipSymbol}/extract | Extract Resources | 
| *Fleet*      | **post** /my/ships/{shipSymbol}/jettison | Jettison Cargo | 
| *Fleet*      | **post** /my/ships/{shipSymbol}/jump | Jump Ship | statekeeping & db/2
| *Fleet*      | **post** /my/ships/{shipSymbol}/navigate | Navigate Ship | statekeeping & db
| *Fleet*      |**post** /my/ships/{shipSymbol}/negotiate/contract | Negotiate Contract |
| *Fleet*      | **patch** /my/ships/{shipSymbol}/nav | Patch Ship Nav | 
| *Fleet*      | **get** /my/ships/{shipSymbol}/nav | Get Ship Nav | 
| *Fleet*      | **post** /my/ships/{shipSymbol}/warp | Warp Ship | statekeeping & db
| *Fleet*      | **post** /my/ships/{shipSymbol}/sell | Sell Cargo | statekeeping & db
| *Fleet*      | **post** /my/ships/{shipSymbol}/scan/systems | Scan Systems | 
| *Fleet*      | **post** /my/ships/{shipSymbol}/scan/waypoints | Scan Waypoints | 
| *Fleet*      | **post** /my/ships/{shipSymbol}/scan/ships | Scan Ships | 
| *Fleet*      | **post** /my/ships/{shipSymbol}/refuel | Refuel Ship | statekeeping & db
| *Fleet*      | **post** /my/ships/{shipSymbol}/purchase | Purchase Cargo | statekeeping & db
| *Fleet*      | **post** /my/ships/{shipSymbol}/transfer | Transfer Cargo | statekeeping & db
| *Systems*    | **get** /systems | List Systems | statekeeping & db
| *Systems*    | **get** /systems.json | Get all systems. |  statekeeping & db
| *Systems*    | **get** /systems/{systemSymbol} | Get System | statekeeping & db
| *Systems*    | **get** /systems/{systemSymbol}/waypoints | List Waypoints | statekeeping & db
| *Systems*    | **get** /systems/{systemSymbol}/waypoints/{waypointSymbol} | Get Waypoint | statekeeping & db
| *Systems*    | **get** /systems/{systemSymbol}/waypoints/{waypointSymbol}/market | Get Market | statekeeping & db
| *Systems*    | **get** /systems/{systemSymbol}/waypoints/{waypointSymbol}/shipyard | Get Shipyard | statekeeping & db
| *Systems*    | **get** /systems/{systemSymbol}/waypoints/{waypointSymbol}/jump-gate | Get Jump Gate | statekeeping
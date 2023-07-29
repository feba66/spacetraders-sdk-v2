from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from space_traders_enums import (
    ContractType,
    FactionTraitSymbol,
    MarketTradeGoodSupply,
    MarketTransactionType,
    ShipCrewRotation,
    ShipEngineType,
    ShipFrameType,
    ShipModuleType,
    ShipMountType,
    ShipNavFlightMode,
    ShipNavStatus,
    ShipReactorType,
    ShipType,
    SurveySize,
    SystemType,
    TradeSymbol,
    WaypointTraitSymbols,
    WaypointType,
)


@dataclass
class Meta:
    total: int
    page: int
    limit: int

    def __init__(self, data) -> None:
        self.total = data["total"]
        self.page = data["page"]
        self.limit = data["limit"]


@dataclass
class Agent:
    accountId: str
    symbol: str
    headquarters: str
    credits: int
    startingFaction: str
    def __init__(self, data=None) -> None:
        if data != None:
            self.accountId = data["accountId"]
            self.symbol = data["symbol"]
            self.headquarters = data["headquarters"]
            self.credits = data["credits"]
            self.startingFaction = data["startingFaction"]
        else:
            self.accountId = ""
            self.symbol = ""
            self.headquarters = ""
            self.credits = 0
            self.startingFaction = ""

@dataclass
class ContractPayment:
    onFulfilled: int
    onAccepted: int

    def __init__(self, data) -> None:
        self.onFulfilled = data["onFulfilled"]
        self.onAccepted = data["onAccepted"]


@dataclass
class ContractDeliverGood:
    tradeSymbol: str
    unitsRequired: int
    destinationSymbol: str
    unitsFulfilled: int

    def __init__(self, data) -> None:
        self.tradeSymbol = data["tradeSymbol"]
        self.unitsRequired = data["unitsRequired"]
        self.destinationSymbol = data["destinationSymbol"]
        self.unitsFulfilled = data["unitsFulfilled"]


@dataclass
class ContractTerms:
    payment: ContractPayment
    deadline: str
    deliver: Optional[list[ContractDeliverGood]]


@dataclass
class Contract:
    terms: ContractTerms
    factionSymbol: str
    fulfilled: bool
    accepted: bool
    expiration: Optional[str]
    deadlineToAccept: Optional[str]
    id: str
    type: ContractType

    def __init__(self, data) -> None:
        self.terms = ContractTerms(
            ContractPayment(data["terms"]["payment"]),
            data["terms"]["deadline"],
            [ContractDeliverGood(d) for d in data["terms"]["deliver"]],
        )
        self.id = data["id"]
        self.fulfilled = data["fulfilled"]
        self.accepted = data["accepted"]
        self.expiration = data["expiration"] if "expiration" in data else None
        self.deadlineToAccept = (
            data["deadlineToAccept"] if "deadlineToAccept" in data else None
        )
        self.factionSymbol = data["factionSymbol"]
        self.type = ContractType[data["type"]]


@dataclass
class FactionTrait:
    symbol: FactionTraitSymbol
    name: str
    description: str

    def __init__(self, data) -> None:
        self.name = data["name"]
        self.description = data["description"]
        self.symbol = FactionTraitSymbol[data["symbol"]]


@dataclass
class Faction:
    symbol: str
    headquarters: str
    traits: list[FactionTrait]
    name: str
    description: str
    isRecruiting: bool

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.headquarters = data["headquarters"]
        self.name = data["name"]
        self.description = data["description"]
        self.traits = [FactionTrait(t) for t in data["traits"]]
        self.isRecruiting = data["isRecruiting"]


@dataclass
class ShipRequirements:
    power: int
    crew: int
    slots: int

    def __init__(self, data) -> None:
        self.power = data["power"] if "power" in data else None
        self.crew = data["crew"] if "crew" in data else None
        self.slots = data["slots"] if "slots" in data else None


@dataclass
class ShipEngine:
    symbol: ShipEngineType
    requirements: ShipRequirements
    name: str
    description: str
    speed: int
    condition: Optional[int]

    def __init__(self, data) -> None:
        self.symbol = ShipEngineType[data["symbol"]]
        self.requirements = ShipRequirements(data["requirements"])
        self.name = data["name"]
        self.description = data["description"]
        self.speed = data["speed"]
        self.condition = data["condition"] if "condition" in data else None


@dataclass
class ShipReactor:
    symbol: ShipReactorType
    requirements: ShipRequirements
    name: str
    description: str
    powerOutput: int
    condition: Optional[int]

    def __init__(self, data) -> None:
        self.symbol = ShipReactorType[data["symbol"]]
        self.requirements = ShipRequirements(data["requirements"])
        self.name = data["name"]
        self.description = data["description"]
        self.powerOutput = data["powerOutput"]
        self.condition = data["condition"] if "condition" in data else None


@dataclass
class Consumed:
    amount: int
    timestamp: str

    def __init__(self, data) -> None:
        self.amount = data["amount"]
        self.timestamp = data["timestamp"]


@dataclass
class ShipFuel:
    current: int
    capacity: int
    consumed: Consumed

    def __init__(self, data) -> None:
        self.current = data["current"]
        self.capacity = data["capacity"]
        self.consumed = Consumed(data["consumed"])


@dataclass
class ShipCargoItem:
    symbol: str
    name: str
    description: str
    units: int

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.name = data["name"]
        self.description = data["description"]
        self.units = data["units"]


@dataclass
class ShipModule:
    symbol: ShipModuleType
    requirements: ShipRequirements
    name: str
    capacity: Optional[int]
    range: Optional[int]
    description: Optional[str]

    def __init__(self, data) -> None:
        self.symbol = ShipModuleType[data["symbol"]]
        self.requirements = ShipRequirements(data["requirements"])
        self.name = data["name"]
        self.capacity = data["capacity"] if "capacity" in data else None
        self.range = data["range"] if "range" in data else None
        self.description = data["description"] if "description" in data else None


@dataclass
class ShipMount:
    symbol: ShipMountType
    requirements: ShipRequirements
    name: str
    description: Optional[str]
    strength: Optional[int]

    def __init__(self, data) -> None:
        self.symbol = ShipMountType[data["symbol"]]
        self.requirements = ShipRequirements(data["requirements"])
        self.name = data["name"]
        self.description = data["description"] if "description" in data else None
        self.strength = data["strength"] if "strength" in data else None


@dataclass
class ShipCargo:
    units: int
    inventory: list[ShipCargoItem]
    capacity: int

    def __init__(self, data) -> None:
        self.units = data["units"]
        self.inventory = [ShipCargoItem(x) for x in data["inventory"]]
        self.capacity = data["capacity"]


@dataclass
class ShipFrame:
    symbol: ShipFrameType
    moduleSlots: int
    requirements: ShipRequirements
    fuelCapacity: int
    name: str
    description: str
    mountingPoints: int
    condition: Optional[int]

    def __init__(self, data) -> None:
        self.symbol = ShipFrameType[data["symbol"]]
        self.moduleSlots = data["moduleSlots"]
        self.requirements = ShipRequirements(data["requirements"])
        self.fuelCapacity = data["fuelCapacity"]
        self.name = data["name"]
        self.description = data["description"]
        self.mountingPoints = data["mountingPoints"]
        self.condition = data["condition"] if "condition" in data else None


@dataclass
class ShipCrew:
    # The amount of credits per crew member paid per hour. Wages are paid when a ship docks at a civilized waypoint.
    wages: int
    current: int
    rotation: ShipCrewRotation
    morale: int
    required: int
    capacity: int

    def __init__(self, data) -> None:
        self.wages = data["wages"]
        self.current = data["current"]
        self.rotation = ShipCrewRotation[data["rotation"]]
        self.morale = data["morale"]
        self.required = data["required"]
        self.capacity = data["capacity"]


@dataclass
class ShipRegistration:
    role: str
    name: str
    factionSymbol: Optional[str]

    def __init__(self, data) -> None:
        self.role = data["role"]
        self.name = data["name"]
        self.factionSymbol = data["factionSymbol"] if "factionSymbol" in data else None


@dataclass
class ShipNavRouteWaypoint:
    symbol: str
    systemSymbol: str
    x: int
    y: int
    type: WaypointType

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.systemSymbol = data["systemSymbol"]
        self.x = data["x"]
        self.y = data["y"]
        self.type = WaypointType[data["type"]]


@dataclass
class ShipNavRoute:
    arrival: str
    departureTime: str
    destination: ShipNavRouteWaypoint
    departure: ShipNavRouteWaypoint

    def __init__(self, data) -> None:
        self.arrival = data["arrival"]
        self.departureTime = data["departureTime"]
        self.destination = ShipNavRouteWaypoint(data["destination"])
        self.departure = ShipNavRouteWaypoint(data["departure"])


@dataclass
class ShipNav:
    route: ShipNavRoute
    systemSymbol: str
    waypointSymbol: str
    flightMode: ShipNavFlightMode
    status: ShipNavStatus

    def __init__(self, data) -> None:
        self.route = ShipNavRoute(data["route"])
        self.systemSymbol = data["systemSymbol"]
        self.waypointSymbol = data["waypointSymbol"]
        self.flightMode = ShipNavFlightMode[data["flightMode"]]
        self.status = ShipNavStatus[data["status"]]


@dataclass
class Ship:
    symbol: str
    nav: ShipNav
    engine: ShipEngine
    fuel: ShipFuel
    reactor: ShipReactor
    mounts: list[ShipMount]
    registration: ShipRegistration
    cargo: ShipCargo
    modules: list[ShipModule]
    crew: ShipCrew
    frame: ShipFrame

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.nav = ShipNav(data["nav"])
        self.engine = ShipEngine(data["engine"])
        self.fuel = ShipFuel(data["fuel"])
        self.reactor = ShipReactor(data["reactor"])
        self.registration = ShipRegistration(data["registration"])
        self.cargo = ShipCargo(data["cargo"])
        self.crew = ShipCrew(data["crew"])
        self.frame = ShipFrame(data["frame"])
        self.mounts = [ShipMount(x) for x in data["mounts"]]
        self.modules = [ShipModule(x) for x in data["modules"]]


@dataclass
class SystemWaypoint:
    symbol: str
    x: int
    y: int
    type: WaypointType

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.x = data["x"] if type(data["x"]) != int else data["x"]
        self.y = data["y"] if type(data["y"]) != int else data["y"]
        self.type = WaypointType[data["type"]]


@dataclass
class System:
    symbol: str
    sectorSymbol: str
    x: int
    y: int
    type: SystemType
    waypoints: list[SystemWaypoint]
    factions: list[str]

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.sectorSymbol = data["sectorSymbol"]
        self.x = data["x"] if type(data["x"]) != int else data["x"]
        self.y = data["y"] if type(data["y"]) != int else data["y"]
        self.type = SystemType[data["type"]]
        self.waypoints = [SystemWaypoint(w) for w in data["waypoints"]]
        self.factions = [str(f) for f in data["factions"]]


@dataclass
class WaypointTrait:
    symbol: WaypointTraitSymbols
    name: str
    description: str

    def __init__(self, data) -> None:
        self.symbol = WaypointTraitSymbols[data["symbol"]]
        self.name = data["name"]
        self.description = data["description"]

    def __repr__(self) -> str:
        return (
            "WaypointTrait(name='"
            + self.name
            + "', description='"
            + self.description
            + "')"
        )


@dataclass
class WaypointFaction:
    symbol: str

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]


@dataclass
class Chart:
    submittedBy: Optional[str]
    submittedOn: Optional[str]

    def __init__(self, data) -> None:
        self.submittedBy = data["submittedBy"] if "submittedBy" in data else None
        self.submittedOn = data["submittedOn"] if "submittedOn" in data else None


@dataclass
class WaypointOrbital:
    symbol: str

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]


@dataclass
class Waypoint:
    symbol: str
    traits: list[WaypointTrait]
    systemSymbol: str
    x: int
    y: int
    type: WaypointType
    orbitals: list[WaypointOrbital]
    faction: Optional[WaypointFaction]
    chart: Optional[Chart]

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.traits = [WaypointTrait(t) for t in data["traits"]]
        self.systemSymbol = data["systemSymbol"]
        self.x = data["x"]
        self.y = data["y"]
        self.type = WaypointType[data["type"]]
        self.orbitals = [WaypointOrbital(o) for o in data["orbitals"]]
        self.faction = WaypointFaction(data["faction"]) if "faction" in data else None
        self.chart = Chart(data["chart"]) if "chart" in data else None


@dataclass
class ShipyardTransaction:
    price: int
    agentSymbol: str
    timestamp: str
    shipSymbol: Optional[str]

    def __init__(self, data) -> None:
        self.price = data["price"]
        self.agentSymbol = data["agentSymbol"]
        self.timestamp = data["timestamp"]
        self.shipSymbol = data["shipSymbol"] if "shipSymbol" in data else None


@dataclass
class ShipyardShip:
    engine: ShipEngine
    reactor: ShipReactor
    name: str
    description: str
    mounts: list[ShipMount]
    purchasePrice: int
    modules: list[ShipModule]
    frame: ShipFrame
    type: Optional[ShipType]

    def __init__(self, data) -> None:
        self.engine = ShipEngine(data["engine"])
        self.reactor = ShipReactor(data["reactor"])
        self.name = data["name"]
        self.description = data["description"]
        self.mounts = [ShipMount(x) for x in data["mounts"]]
        self.purchasePrice = data["purchasePrice"]
        self.modules = [ShipModule(x) for x in data["modules"]]
        self.frame = ShipFrame(data["frame"])
        self.type = ShipType[data["type"]] if "type" in data else None


@dataclass
class Shipyard:
    shipTypes: list[ShipType]
    symbol: str
    transactions: Optional[list[ShipyardTransaction]]
    ships: Optional[list[ShipyardShip]]

    def __init__(self, data) -> None:
        self.shipTypes = [ShipType[t["type"]] for t in data["shipTypes"]]
        self.symbol = data["symbol"]
        self.transactions = (
            [ShipyardTransaction(t) for t in data["transactions"]]
            if "transactions" in data
            else None
        )
        self.ships = (
            [ShipyardShip(s) for s in data["ships"]] if "ships" in data else None
        )


@dataclass
class TradeGood:
    symbol: TradeSymbol
    name: str
    description: str

    def __init__(self, data) -> None:
        self.symbol = TradeSymbol[data["symbol"]]
        self.name = data["name"]
        self.description = data["description"]


@dataclass
class MarketTransaction:
    shipSymbol: str
    units: int
    type: MarketTransactionType
    pricePerUnit: int
    timestamp: str
    tradeSymbol: str
    totalPrice: int

    def __init__(self, data) -> None:
        self.shipSymbol = data["shipSymbol"]
        self.units = data["units"]
        self.type = MarketTransactionType[data["type"]]
        self.pricePerUnit = data["pricePerUnit"]
        self.timestamp = data["timestamp"]
        self.tradeSymbol = data["tradeSymbol"]
        self.totalPrice = data["totalPrice"]

@dataclass
class Transaction:
    timestamp: str
    totalPrice: int

    def __init__(self, data) -> None:
        self.timestamp = data["timestamp"]
        self.totalPrice = data["totalPrice"]

@dataclass
class MarketTradeGood:
    tradeVolume: int
    symbol: str
    sellPrice: int
    purchasePrice: int
    supply: MarketTradeGoodSupply

    def __init__(self, data) -> None:
        self.tradeVolume = data["tradeVolume"]
        self.symbol = data["symbol"]
        self.sellPrice = data["sellPrice"]
        self.purchasePrice = data["purchasePrice"]
        self.supply = MarketTradeGoodSupply[data["supply"]]


@dataclass
class Market:
    symbol: str
    imports: list[TradeGood]
    exports: list[TradeGood]
    exchange: list[TradeGood]
    transactions: Optional[list[MarketTransaction]]
    tradeGoods: Optional[list[MarketTradeGood]]

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.imports = [TradeGood(t) for t in data["imports"]]
        self.exports = [TradeGood(t) for t in data["exports"]]
        self.exchange = [TradeGood(t) for t in data["exchange"]]
        self.transactions = (
            [MarketTransaction(t) for t in data["transactions"]]
            if "transactions" in data
            else None
        )
        self.tradeGoods = (
            [MarketTradeGood(t) for t in data["tradeGoods"]]
            if "tradeGoods" in data
            else None
        )


@dataclass
class ConnectedSystem:
    symbol: str
    distance: int
    sectorSymbol: str
    x: int
    y: int
    type: SystemType
    factionSymbol: Optional[str]

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.distance = data["distance"]
        self.sectorSymbol = data["sectorSymbol"]
        self.x = data["x"]
        self.y = data["y"]
        self.type = SystemType[data["type"]]
        self.factionSymbol = data["factionSymbol"] if "factionSymbol" in data else None


@dataclass
class JumpGate:
    connectedSystems: list[ConnectedSystem]
    jumpRange: int
    factionSymbol: Optional[str]

    def __init__(self, data) -> None:
        self.connectedSystems = [ConnectedSystem(s) for s in data["connectedSystems"]]
        self.jumpRange = data["jumpRange"]
        self.factionSymbol = data["factionSymbol"] if "factionSymbol" in data else None


@dataclass
class Cooldown:
    remainingSeconds: int
    totalSeconds: int
    expiration: str
    shipSymbol: str
    expiredAt: Optional[str]

    def __init__(self, data) -> None:
        self.remainingSeconds = data["remainingSeconds"]
        self.totalSeconds = data["totalSeconds"]
        self.expiration = data["expiration"]
        self.shipSymbol = data["shipSymbol"]
        self.expiredAt = data["expiredAt"] if "expiredAt" in data else None


@dataclass
class SurveyDeposit:
    symbol: str

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]


@dataclass
class Survey:
    symbol: str
    size: SurveySize
    signature: str
    expiration: str
    deposits: list[SurveyDeposit]
    timestamp:Optional[datetime]

    def __init__(self, symbol,size=None,signature=None,expiration=None,deposits=None,timestamp=None) -> None:
        if size == None:
            self.symbol = symbol["symbol"]
            self.size = SurveySize[symbol["size"]]
            self.signature = symbol["signature"]
            self.expiration = symbol["expiration"]
            self.deposits = [SurveyDeposit(d) for d in symbol["deposits"]]
        else:
            self.symbol=symbol
            self.size=size
            self.signature=signature
            self.expiration=expiration
            self.deposits=deposits
            self.timestamp=timestamp
            

    def dict(self):
        return {
            "signature": self.signature,
            "symbol": self.symbol,
            "deposits": [{"symbol": x.symbol} for x in self.deposits],
            "expiration": self.expiration,
            "size": self.size.name,
        }


@dataclass
class ExtractionYield:
    symbol: str
    units: int

    def __init__(self, data) -> None:
        self.symbol = data["symbol"]
        self.units = data["units"]


@dataclass
class Extraction:
    yield_: ExtractionYield
    shipSymbol: str

    def __init__(self, data) -> None:
        self.yield_ = ExtractionYield(data["yield"])
        self.shipSymbol = data["shipSymbol"]

@dataclass
class Error:
    message: str
    code: int

    def __init__(self, data) -> None:
        self.message = data["message"]
        self.code = data["code"]

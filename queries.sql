
CREATE TABLE IF NOT EXISTS waypoints (systemSymbol varchar, symbol varchar PRIMARY KEY, type varchar, x integer,y integer,orbitals varchar[],traits varchar[],chart varchar,faction varchar);
CREATE TABLE IF NOT EXISTS systems (symbol varchar PRIMARY KEY, type varchar, x integer, y integer);
CREATE TABLE IF NOT EXISTS markets (symbol varchar, good varchar, type varchar, PRIMARY KEY (symbol, good, type));
CREATE TABLE IF NOT EXISTS shipyards (symbol varchar, shiptype varchar, PRIMARY KEY (symbol, shiptype));
CREATE TABLE IF NOT EXISTS prices (waypointsymbol varchar, symbol varchar, supply varchar, purchase integer, sell integer,tradevolume integer,timestamp varchar, PRIMARY KEY (waypointsymbol, symbol,timestamp));
CREATE TABLE IF NOT EXISTS transactions (WAYPOINTSYMBOL varchar, SHIPSYMBOL varchar, TRADESYMBOL varchar, TYPE varchar, UNITS integer, PRICEPERUNIT integer, TOTALPRICE integer, timestamp varchar, PRIMARY KEY (WAYPOINTSYMBOL,TRADESYMBOL,SHIPSYMBOL, timestamp));
CREATE TABLE IF NOT EXISTS prices (waypointsymbol varchar, symbol varchar, supply varchar, purchase integer, sell integer,tradevolume integer,timestamp varchar, PRIMARY KEY (waypointsymbol, symbol,timestamp));
CREATE TABLE IF NOT EXISTS markets (symbol varchar, good varchar, type varchar, PRIMARY KEY (symbol, good, type));




CREATE TABLE IF NOT EXISTS SHIPS (SYMBOL CHARACTER varying NOT NULL, faction CHARACTER varying, ROLE CHARACTER varying, FRAME CHARACTER varying,  ENGINE CHARACTER varying,  SPEED CHARACTER varying,  MODULES CHARACTER varying[],  MOUNTS CHARACTER varying[],  cargo_capacity integer, PRIMARY KEY (SYMBOL));
CREATE TABLE IF NOT EXISTS SHIPNAVS(SYMBOL CHARACTER varying NOT NULL, WAYPOINTSYMBOL CHARACTER varying, DEPARTURE CHARACTER varying, DESTINATION CHARACTER varying, ARRIVAL CHARACTER varying, DEPARTURETIME CHARACTER varying, STATUS CHARACTER varying, FLIGHTMODE CHARACTER varying, PRIMARY KEY (SYMBOL));
CREATE TABLE IF NOT EXISTS SHIPCARGOS (SYMBOL CHARACTER varying, GOOD CHARACTER varying, UNITS integer, PRIMARY KEY (SYMBOL, GOOD));
CREATE TABLE IF NOT EXISTS SHIPFUEL (SYMBOL CHARACTER varying, FUEL integer, CAPACITY integer, PRIMARY KEY (SYMBOL));
CREATE TABLE IF NOT EXISTS SHIPCONSUMTION (SYMBOL CHARACTER varying, AMOUNT integer, DEPARTEDFROM CHARACTER varying, DESTINATION CHARACTER varying, FLIGHTMODE CHARACTER varying, FLIGHTTIME integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (SYMBOL, TIMESTAMP));
CREATE TABLE IF NOT EXISTS CREDITLEADERBOARD (AGENTSYMBOL CHARACTER varying, CREDITS integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));
CREATE TABLE IF NOT EXISTS CHARTLEADERBOARD (AGENTSYMBOL CHARACTER varying, CHARTCOUNT integer, TIMESTAMP CHARACTER varying, PRIMARY KEY (AGENTSYMBOL,TIMESTAMP));
CREATE TABLE IF NOT EXISTS FACTIONS (SYMBOL CHARACTER varying NOT NULL, name CHARACTER varying, description CHARACTER varying, headquarters CHARACTER varying,  traits CHARACTER varying[], PRIMARY KEY (SYMBOL));

INSERT INTO waypoints (systemSymbol, symbol, type, x, y, orbitals, traits, chart,faction) VALUES  {','.join([f'(%s, %s, %s, %s, %s, %s, %s, %s, %s)' for _ in range(int(len(temp)/9))])} ON CONFLICT (symbol) DO UPDATE SET traits = excluded.traits, chart = excluded.chart,faction = excluded.faction;





CREATE TABLE IF NOT EXISTS SURVEYS (
    signature CHARACTER varying,
    symbol CHARACTER varying,
    deposits CHARACTER varying[],
    expiration CHARACTER varying,
    size CHARACTER varying,
    timestamp CHARACTER varying,
    PRIMARY KEY (signature)
)

CREATE TABLE IF NOT EXISTS EXTRACTIONS (
    shipSymbol CHARACTER varying,
    symbol CHARACTER varying,
    units CHARACTER varying[],
    timestamp CHARACTER varying,
    PRIMARY KEY (shipSymbol,timestamp)
)


-- prices2 lj markets
select waypointsymbol,prices2.symbol,supply,type,purchase,sell,tradevolume from prices2
left join markets on markets.symbol = prices2.waypointsymbol and markets.good = prices2.symbol
order by prices2.symbol,sell desc

-- get which markets trade the good at what range to your system
-- enter xy system cords for where youre at. If negative it should be like this: x-(-10198) or x+10198
select systemsymbol,waypoints.symbol,good,markets.type,sqrt((systems.x-(10198))^2+(systems.y-(10079))^2) as dist from markets
left join waypoints on waypoints.symbol = markets.symbol
left join systems on systems.symbol = waypoints.systemsymbol
where good ='MOUNT_MINING_LASER_II'
order by dist

-- to scan:
select systemsymbol,waypoints.symbol,good,markets.type,sqrt((systems.x-10198)^2+(systems.y-10079)^2) as dist from markets
left join waypoints on waypoints.symbol = markets.symbol
left join systems on systems.symbol = waypoints.systemsymbol
where (markets.type = 'IMPORT' or markets.type = 'EXPORT')
and not (markets.symbol = any((select prices2.waypointsymbol from prices2
group by prices2.waypointsymbol)))
order by dist

-- to scan but only unique waypoints
select  systemsymbol,waypoints.symbol,sqrt((systems.x-10198)^2+(systems.y-10079)^2) as dist from markets --,waypoints.symbol,good,markets.type
left join waypoints on waypoints.symbol = markets.symbol
left join systems on systems.symbol = waypoints.systemsymbol
where (markets.type = 'IMPORT' or markets.type = 'EXPORT')
and not (markets.symbol = any((select prices2.waypointsymbol from prices2
group by prices2.waypointsymbol)))
group by systemsymbol,waypoints.symbol,dist
order by dist
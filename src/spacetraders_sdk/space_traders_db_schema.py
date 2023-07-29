from datetime import datetime
from sqlalchemy.orm import DeclarativeBase,mapped_column,Mapped,relationship
from sqlalchemy import  Column, Enum, ForeignKey, Integer, String,BigInteger, Table
from typing import List, Optional
from space_traders_enums import FactionTraitSymbol, FactionSymbol,ContractType,TradeSymbol

class Base(DeclarativeBase):
    pass

class Agent(Base):
    __tablename__ = "agents"
    accountId: Mapped[str]=mapped_column(primary_key=True)
    symbol: Mapped[str]=mapped_column(String(14))
    headquarters: Mapped[str]
    credits: Mapped[int]=mapped_column(BigInteger())
    startingFaction: Mapped[FactionSymbol]
    shipCount: Mapped[Optional[int]]
    token:Mapped[Optional[str]]
    
AssFacTra = Table("assfactra",
    Base.metadata,
    Column("factionSymbol",Enum(FactionSymbol),ForeignKey("factions.symbol")),
    Column("factionTraitSymbol",Enum(FactionTraitSymbol),ForeignKey("factiontraits.symbol"))
)

class FactionTrait(Base):
    __tablename__="factiontraits"
    symbol:Mapped[FactionTraitSymbol]=mapped_column(primary_key=True)
    name:Mapped[str]
    description:Mapped[str]

class Faction(Base):
    __tablename__="factions"
    symbol:Mapped[FactionSymbol]=mapped_column(primary_key=True)
    name:Mapped[str]
    description:Mapped[str]
    headquarters:Mapped[str]
    traits:Mapped[List[FactionTrait]]=relationship(secondary=AssFacTra)
    isRecruiting:Mapped[bool]
    
# class B(Base):
#     __tablename__="b"
#     id:Mapped[int]=mapped_column(ForeignKey("a.id"), primary_key=True)

# class A(Base):s
#     __tablename__ = "a"
#     id:Mapped[int]=mapped_column(primary_key=True)
#     b:Mapped[B] = relationship()

# class ContractPayment(Base):
#     __tablename__ = "contractpayments"
#     id:Mapped[int]=mapped_column(primary_key=True)
#     c_id:Mapped[int]=mapped_column(ForeignKey("contractterms.id"))
#     onAccepted:Mapped[int]
#     onFulfilled:Mapped[int]

# class ContractDeliverGood(Base):
#     __tablename__ = "contractdelivergoods"
#     id:Mapped[int]=mapped_column(primary_key=True)
#     c_id:Mapped[int]=mapped_column(ForeignKey("contractterms.id"))
#     tradeSymbol:Mapped[TradeSymbol]
#     destinationSymbol:Mapped[str]
#     unitsRequired:Mapped[int]
#     unitsFulfilled:Mapped[int]

# class ContractTerms(Base):
#     __tablename__ = "contractterms"
#     id:Mapped[int]=mapped_column(primary_key=True)
#     c_id:Mapped[int]=mapped_column(ForeignKey("contracts.id"))
#     deadline:Mapped[datetime]
#     payment:Mapped[ContractPayment] = relationship()
#     deliver:Mapped[Optional[list[ContractDeliverGood]]] = relationship()

# class Contract(Base):
#     __tablename__ = "contracts"
#     id:Mapped[str]=mapped_column(primary_key=True)
#     factionSymbol:Mapped[Factions]
#     type:Mapped[ContractType]
#     terms:Mapped[ContractTerms] = relationship()
#     accepted:Mapped[bool]
#     fulfilled:Mapped[bool]
#     expiration:Mapped[datetime]
#     deadlineToAccept:Mapped[Optional[datetime]]

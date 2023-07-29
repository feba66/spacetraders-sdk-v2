
from enum import Enum
import os
from dotenv import find_dotenv, load_dotenv
from peewee import PostgresqlDatabase,Model,TextField,IntegerField,Check,BigIntegerField,Field,BooleanField,ForeignKeyField
from space_traders_enums import FactionSymbol, FactionTraitSymbol
from playhouse.postgres_ext import ArrayField
from space_traders_api import SpaceTradersApi as STApi

load_dotenv(find_dotenv(".env"))

user = os.getenv("DB_USER")
db = os.getenv("DB")
ip = os.getenv("IP")
port = os.getenv("PORT")

db = PostgresqlDatabase(f"{db}_test",user=user,password=os.getenv('DB_PASSWORD'),host=ip,port=port)

class Base(Model):
    class Meta:
        database = db
    
    @classmethod
    def create_table(cls, *args, **kwargs):
        for field in cls._meta.fields.values():
            if hasattr(field, "pre_field_create"):
                field.pre_field_create(cls)

        cls._schema.create_table()
class EnumField(Field):
    def pre_field_create(self, model):
        field = self.help_text if self.help_text else "e_%s" % self.name

        tail = ', '.join(["'%s'"] * len(self.choices)) % tuple(self.choices)
        self.model._meta.database.execute_sql(f" DO $$ BEGIN CREATE TYPE {field} AS ENUM ({tail}); EXCEPTION WHEN duplicate_object THEN null; END $$;")
        self.field_type = field

class Agent(Base):
    accountId = TextField(primary_key=True,column_name="accountid")
    symbol= TextField(constraints=[Check('length(symbol) >= 3'),Check('length(symbol) <= 14')])
    
    headquarters = TextField()
    credits =BigIntegerField()
    startingFaction = EnumField(help_text="FactionSymbol",choices=FactionSymbol,column_name="startingfaction")
    shipCount = IntegerField(null=True,column_name="shipcount")
    token = TextField(null=True)

class FactionTrait(Base):
    symbol = EnumField(help_text="FactionTraitSymbol",choices=FactionTraitSymbol,primary_key=True)
    name=TextField()
    description=TextField()

class Faction(Base):
    symbol = EnumField(help_text="FactionSymbol",choices=FactionSymbol,primary_key=True)
    name=TextField()
    description=TextField()
    headquarters=TextField()
    isRecruiting= BooleanField()
class FactionTraitFaction(Base):
    faction = ForeignKeyField(Faction)
    trait = ForeignKeyField(FactionTrait)
    
all_tables = [Agent,FactionTrait,Faction,FactionTraitFaction]
db.connect()
db.drop_tables(all_tables)
db.create_tables(all_tables)

api = STApi()
r = api.get_faction("ASTRO")
d = r.json()["data"]

faction = Faction.create(symbol=d["symbol"],name=d["name"],description=d["description"],headquarters=d["headquarters"],isRecruiting=d["isRecruiting"])
for t in d["traits"]:
    trait = FactionTrait.create(symbol=t["symbol"],name=t["name"],description=t["description"])
    FactionTraitFaction.create(faction=faction,trait=trait)

db.commit()
db.close()
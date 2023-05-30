from __future__ import annotations
import json
from pprint import pprint
import os



with open("api-docs\models\Market.json","r") as f:
    jsn = json.load(f)

pprint(jsn)

def fix_type(type):
    if type == "string":
        return "str"
    elif type == "integer":
        return "int"
    elif type == "boolean":
        return "bool"
    elif type == "array":
        return "list"
    else: return type
def parse(jsn,name):
    type = jsn["type"]
    optional_var = False
    vars = []
    if type == "object":
        for p in jsn["properties"]:
            opt = p in jsn["required"] if "required" in jsn else False
            if not opt:
                optional_var = True
            vars.append((p,
                         opt,
                         fix_type(jsn["properties"][p]["type"]),
                         jsn["properties"][p]["description"] if "description" in jsn["properties"][p] else None,
                         jsn["properties"][p]["enum"] if "enum" in jsn["properties"][p] else None
                         ))
            # if "enum" in jsn["properties"][p]:
                # print()
            # print(p)
    # pprint(vars)
    vars.sort(key=lambda x: x[1],reverse=True)
    s = f"""from __future__ import annotations\nfrom pydantic import BaseModel, constr\n{'from typing import Optional' if optional_var else ''}\n\nclass {name}(BaseModel):\n"""
    for v in vars:
        s +=f'''    {v[0]}: {f'Optional[{v[2]}]' if not v[1] else v[2]}{f'{chr(10)}    """{v[3]}""" '  if v[3] else ''}\n'''
    s+=f"""    def __init__(self,{', '.join([f'{v[0]}:{v[2] if v[1] else f"{v[2]} = None"}' for v in vars])}):\n"""
    for v in vars:
        s+= f"""        self.{v[0]} = {v[0]}\n"""
    s+= f"\n    @staticmethod\n    def from_dict(dict) -> {name}:\n"
    s+= f"""        return {name}({', '.join({f'dict["{v[0]}"]{f" if {chr(34)}{v[0]}{chr(34)} in dict else None" if not v[1] else ""}' for v in vars})})"""
    # print(s)
    return s
# parse(jsn,"Market")
done,fail = 0,0
with os.scandir('api-docs\models') as entries:
    for entry in entries:
        print(entry.path,end="")
        name = entry.name.split('.')[0]
        with open(f"spacetraders-sdk-v2/gen/{name}.py","w") as f:
            try:
                with open(entry.path,"r") as g:
                    f.write(parse(json.load(g),name))
                done+=1
                print(" success!")
            except :
                fail+=1
                f.write("fail")
                print(" failed!")
print(f"Success: {done}, failed: {fail}")
class a:
    @staticmethod
    def stuff(dict) -> a:
        return a()
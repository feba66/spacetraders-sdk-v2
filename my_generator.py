from __future__ import annotations
import json
from pprint import pprint
import os

forbidden_vars = ["yield"]

def fix_type(type):
    if type == "string":
        return "str"
    elif type == "integer":
        return "int"
    elif type == "boolean":
        return "bool"
    elif type == "array":
        return "list"
    elif type == "number":
        return "float"
    elif "./" in type and ".json" in type:
        return type[2:-5]
    else: 
        return type

def parse(jsn,name):
    type = jsn["type"]
    optional_var = False
    vars = []
    imports = ["from __future__ import annotations","from pydantic import BaseModel, constr"]
    s = ""
    if type == "object":
        for p in jsn["properties"]:
            opt = p in jsn["required"] if "required" in jsn else False
            if not opt and "from typing import Optional" not in imports:
                imports.append("from typing import Optional")
            if "type" in jsn["properties"][p]:
                t = fix_type(jsn["properties"][p]["type"])
            else:
                t = fix_type(jsn["properties"][p]["$ref"])
                imports.append(f"from {t} import {t}")
            if t == "list":
                if "type" in jsn["properties"][p]["items"]:
                    t+=f"""[{fix_type(jsn["properties"][p]["items"]["type"])}]"""
                else:
                    t2 = fix_type(jsn["properties"][p]["items"]["$ref"])
                    t+=f"""[{t2}]"""
                    imports.append(f"from {t2} import {t2}")
            vars.append((p,
                         opt,
                         t,
                         jsn["properties"][p]["description"] if "description" in jsn["properties"][p] else None,
                         jsn["properties"][p]["enum"] if "enum" in jsn["properties"][p] else None
                         ))
            # if "enum" in jsn["properties"][p]:
                # print()
            # print(p)
        # pprint(vars)
        vars.sort(key=lambda x: x[1],reverse=True)
        s = f"""{f"{chr(10).join(imports)}"}\n\n\nclass {name}(BaseModel):\n"""
        if "description" in jsn:
            s+=f'''    """{jsn["description"]}"""\n'''
        for v in vars:
            s +=f'''    {v[0] if v[0] not in forbidden_vars else f"_{v[0]}"}: {f'Optional[{v[2]}]' if not v[1] else v[2]}{f'{chr(10)}    """{v[3]}"""'  if v[3] else ''}\n'''
        
        s+=f"""\n    def __init__(self, {', '.join([f'{v[0] if v[0] not in forbidden_vars else f"_{v[0]}"}: {v[2] if v[1] else f"{v[2]} = None"}' for v in vars])}):\n"""
        
        for v in vars:
            n = v[0] if v[0] not in forbidden_vars else f"_{v[0]}"
            s+= f"""        self.{n} = {n}\n"""
        
        s+= f"\n    @staticmethod\n    def from_dict(dict) -> {name}:\n"
        s+= f'''        return {name}({', '.join({f'dict["{v[0]}"]{f""" if "{v[0]}" in dict else None""" if not v[1] else ""}' if not "list" in v[2] else f'[{v[2].split("[")[1][:-1]}(elem) for elem in dict["{v[0]}"]]{f""" if "{v[0]}" in dict else None""" if not v[1] else ""}' for v in vars})})'''
        s+="\n"
    elif type == "string":
        if "enum" in jsn:
            imports.append("from enum import Enum")
            s = f"""{f"{chr(10).join(imports)}"}\n\n\nclass {name}(Enum):\n"""
            if "description" in jsn:
                s+=f'''    """{jsn["description"]}"""\n'''
            for en in jsn["enum"]:
                s+=f'''    {en} = "{en}"\n'''
    elif type == "integer":
        s = f"""{f"{chr(10).join(imports)}"}\n\n\nclass {name}(int):\n"""
        if "description" in jsn:
            s+=f'''    """{jsn["description"]}{f" min:{jsn['minimum']}" if "minimum" in jsn else ""}{f" max:{jsn['maximum']}" if "maximum" in jsn else ""}"""\n'''
    else:
        print()
        print(type)
    if s == "":
        pass
    return s
done,fail = 0,0
with os.scandir('api-docs\models') as entries:
    for entry in entries:
        print(entry.path,end="")
        name = entry.name.split('.')[0]
        with open(f"spacetraders-sdk-v2/gen/{name}.py","w") as f:
            # try:
                with open(entry.path,"r") as g:
                    f.write(parse(json.load(g),name))
                done+=1
                print(" success!")
            # except :
            #     fail+=1
            #     f.write("fail")
            #     print(" failed!")
print(f"Success: {done}, failed: {fail}")
class a:
    @staticmethod
    def stuff(dict) -> a:
        return a()
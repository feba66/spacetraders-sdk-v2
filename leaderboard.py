import json
from pprint import pprint
import time
from api import SpaceTraders


st = SpaceTraders()
old_j=json.loads(st.Status().text)
time.sleep(5)
while True:
    j = json.loads(st.Status().text)
    if j!=old_j:
        pprint(j)
        old_j=j
        time.sleep(30*60-10)
    time.sleep(180)
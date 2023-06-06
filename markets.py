import os
import sys
import time
from api import SpaceTraders


if __name__ == "__main__":
    st = SpaceTraders()
    # st.Status()

    # pprint(st.Register("feba662","ASTRO"))
    st.Login(os.getenv("TOKEN"))
    while True:
        st.Get_Market("X1-AD50-85905A")
        time.sleep(30)
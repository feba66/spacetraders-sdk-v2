

from datetime import datetime
import os
from dotenv import find_dotenv, load_dotenv
import psycopg2

load_dotenv(find_dotenv(".env"))

user = os.getenv("DB_USER")
db = os.getenv("DB")
ip = os.getenv("IP")
port = os.getenv("PORT")

tmp = psycopg2.connect(dbname="postgres", user=user, password=os.getenv("DB_PASSWORD"), host=ip, port=port)
tmp.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cur = tmp.cursor()
cur.execute(f"""SELECT pg_terminate_backend (pid) FROM pg_stat_activity WHERE datname = 'st';""")
cur.execute(f"""ALTER DATABASE st RENAME TO st_{str(datetime.utcnow().date()).replace("-","_")};""",)
cur.execute("CREATE DATABASE st")
tmp.close()
# try:
#     connection = psycopg2.connect(dbname="postgres", user=user, password=os.getenv("DB_PASSWORD"), host=ip, port=port)
#     connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
#     with connection.cursor() as cursor:
        
# finally:
#     if connection:
#         connection.close()

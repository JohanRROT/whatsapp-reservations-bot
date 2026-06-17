import os
from psycopg2 import connect
from dotenv import load_dotenv

load_dotenv()

host=os.getenv("DB_HOST")
port=os.getenv("DB_PORT")
dbname=os.getenv("DB_NAME")
user=os.getenv("DB_USER")
password=os.getenv("DB_PASSWORD")

with connect(dbname=dbname, user=user, password=password, host=host, port=port) as conn:
	with conn.cursor() as cursor:
		cursor.execute("SELECT COUNT(*) FROM conversations")
		result = cursor.fetchone()
		print(result)


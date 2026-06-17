import os
from psycopg2 import connect
from dotenv import load_dotenv

load_dotenv()

def get_connection():
	host=os.getenv("DB_HOST")
	port=os.getenv("DB_PORT")
	dbname=os.getenv("DB_NAME")
	user=os.getenv("DB_USER")
	password=os.getenv("DB_PASSWORD")
	conn=connect(dbname=dbname, user=user, password=password, host=host, port=port)
	return conn





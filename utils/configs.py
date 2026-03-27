from dotenv import load_dotenv
import os

load_dotenv()

DB_SETTINGS = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("POSTGRES_DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

DBT_PROJECT_DIR = os.getenv("DBT_PROJECT_DIR")
DBT_PROFILES_DIR = os.getenv("DBT_PROFILES_DIR")
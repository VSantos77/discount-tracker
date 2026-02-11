import psycopg2
from os import getenv
from dotenv import load_dotenv
from utils.scripts.get_project_root_path import get_project_root_path

def normalize_data():

    load_dotenv()
    # 1. Connect to your Postgres DB (using your Docker credentials)
    conn = psycopg2.connect(
        dbname=getenv("DB_NAME"),
        user=getenv("DB_USER"),
        password=getenv("DB_PASSWORD"),
        host=getenv("DB_HOST") # Or 'db' if running inside the same Docker network
    )
    cur = conn.cursor()

    try:
        # Populate dim_issuers from stg_discounts
        print("Normalizing Issuers...")

        with open(get_project_root_path() / "utils" / "queries" / "insert_to_dim_issuers.sql", 'r') as f:
            sql_query = f.read()

        cur.execute(sql_query)

        # Normalize merchants
        print("Normalizing Merchants...")

        with open(get_project_root_path() / "utils" / "queries" / "insert_to_dim_merchants.sql", 'r') as f:
            sql_query = f.read()

        cur.execute(sql_query)

        # Add payment methods to raw
        print("Normalizing Payment Methods...")
        with open(get_project_root_path() / "utils" / "queries" / "insert_to_dim_payment_methods_raw.sql", 'r') as f:
            sql_query = f.read() 

        cur.execute(sql_query)

        # Populate map_dim_payment_methods
        print("Mapping Discount to Payment Methods...")
        with open(get_project_root_path() / "utils" / "queries" / "insert_to_map_dim_payment_methods.sql", 'r') as f:
            sql_query = f.read() 

        cur.execute(sql_query)

        # Move data to fct_discounts by joining with the new IDs
        print("Populating Fact Table...")

        with open(get_project_root_path() / "utils" / "queries" / "insert_to_fct_discounts.sql", 'r') as f:
            sql_query = f.read()

        cur.execute(sql_query)

        # Clear Staging
        cur.execute("TRUNCATE TABLE stg_discounts;")

        conn.commit()
        print("Success! Data normalized and staging cleared.")

    except Exception as e:
        conn.rollback()
        print(f"Error during normalization: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    normalize_data()
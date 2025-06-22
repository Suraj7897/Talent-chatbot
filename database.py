# database.py

from sqlalchemy import create_engine, text
import pandas as pd

DB_FILE = "sqlite:///talent.db"
engine = create_engine(DB_FILE)

def save_to_db(df, table_name="talent_data"):
    df.to_sql(table_name, con=engine, if_exists="replace", index=False)

def load_from_db(table_name="talent_data"):
    return pd.read_sql(f"SELECT * FROM {table_name}", con=engine)

def db_table_exists(table_name="talent_data"):
    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        )
        return result.fetchone() is not None

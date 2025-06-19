from sqlalchemy import create_engine, text
from config import Config

# Create SQLAlchemy engine using centralized config
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

# SQL statements to create tables
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    userid VARCHAR(255) UNIQUE NOT NULL,
    balance DECIMAL(65,2) DEFAULT 0.00
);
"""

CREATE_RECHARGE_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS recharge_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    userid VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    card_number VARCHAR(255),
    amount DECIMAL(10,2),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20)
);
"""

def create_tables():
    try:
        with engine.connect() as conn:
            # Create tables
            conn.execute(text(CREATE_USERS_TABLE))
            conn.execute(text(CREATE_RECHARGE_RECORDS_TABLE))
            conn.commit()
            print("Tables created successfully!")

            # Verify tables exist
            result = conn.execute(text("SHOW TABLES;"))
            print("\nExisting tables:")
            for row in result:
                print(row[0])
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()

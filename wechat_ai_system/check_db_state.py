from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import pymysql
from config import Config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
db = SQLAlchemy(app)

def check_database_state():
    with app.app_context():
        try:
            # Check tables
            result = db.session.execute(text('SHOW TABLES')).fetchall()
            print('\nCurrent tables in database:')
            if not result:
                print('No tables found in database!')
            else:
                for table in result:
                    table_name = table[0]
                    print(f'\nTable: {table_name}')

                    # Get table structure
                    structure = db.session.execute(text(f'DESCRIBE {table_name}')).fetchall()
                    print('Columns:')
                    for col in structure:
                        print(f'  - {col[0]} ({col[1]})')

                    # Check for data
                    row_count = db.session.execute(text(f'SELECT COUNT(*) FROM {table_name}')).scalar()
                    print(f'Row count: {row_count}')

                    # Show sample data if exists
                    if row_count > 0:
                        sample = db.session.execute(text(f'SELECT * FROM {table_name} LIMIT 3')).fetchall()
                        print('Sample data (up to 3 rows):')
                        for row in sample:
                            print(f'  {row}')
        except Exception as e:
            print(f'Error checking database state: {str(e)}')

if __name__ == '__main__':
    check_database_state()

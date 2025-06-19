from main import app, db
from sqlalchemy import text

def check_transaction_isolation():
    with app.app_context():
        # Check current isolation level
        result = db.session.execute(text('SHOW VARIABLES LIKE "transaction_isolation"'))
        current_level = result.fetchone()
        print('Current transaction isolation level:', current_level)

        # Test if we can set SERIALIZABLE
        try:
            db.session.execute(text('SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE'))
            print('Successfully set SERIALIZABLE isolation level')

            # Verify the change
            result = db.session.execute(text('SHOW VARIABLES LIKE "transaction_isolation"'))
            new_level = result.fetchone()
            print('New isolation level:', new_level)
        except Exception as e:
            print('Failed to set SERIALIZABLE:', str(e))
        finally:
            db.session.rollback()

if __name__ == '__main__':
    check_transaction_isolation()

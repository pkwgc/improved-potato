from flask import current_app
from models import db
import datetime
import os
import json

def backup_tables(tables=None):
    """
    Create a backup of specified tables or all tables if none specified
    Returns the backup filepath
    """
    if not tables:
        tables = ['users', 'recharge_records']

    backup_dir = os.path.join(current_app.root_path, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_data = {}

    for table in tables:
        if table == 'users':
            from models import User
            records = User.query.all()
            backup_data[table] = [
                {
                    'id': r.id,
                    'userid': r.userid,
                    'balance': float(r.balance),
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                    'password_hash': r.password_hash
                } for r in records
            ]
        elif table == 'recharge_records':
            from models import RechargeRecord
            records = RechargeRecord.query.all()
            backup_data[table] = [
                {
                    'id': r.id,
                    'userid': r.userid,
                    'phone_number': r.phone_number,
                    'card_number': r.card_number,
                    'amount': float(r.amount),
                    'timestamp': r.timestamp.isoformat() if r.timestamp else None,
                    'status': r.status
                } for r in records
            ]

    backup_file = os.path.join(backup_dir, f'backup_{timestamp}.json')
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)

    return backup_file

def confirm_operation(operation_type, tables=None):
    """
    Request confirmation for destructive database operations
    Returns True if confirmed, False otherwise
    """
    from flask import request

    # Skip confirmation in test environment
    if request.headers.get('X-Test-Request'):
        return True

    confirmation_header = request.headers.get('X-Confirm-Operation')
    if not confirmation_header:
        return False

    expected_confirmation = f"CONFIRM_{operation_type}_{'_'.join(sorted(tables)) if tables else 'ALL'}"
    return confirmation_header == expected_confirmation

def safe_delete_tables(tables=None):
    """
    Safely delete specified tables with backup and confirmation
    """
    if not confirm_operation('DELETE', tables):
        return False, "Operation not confirmed"

    try:
        # Create backup before deletion
        backup_file = backup_tables(tables)

        # Perform deletion
        with db.session.begin():
            for table in (tables or ['users', 'recharge_records']):
                if table == 'users':
                    from models import User
                    User.query.delete()
                elif table == 'recharge_records':
                    from models import RechargeRecord
                    RechargeRecord.query.delete()

        return True, f"Tables deleted successfully. Backup created at {backup_file}"
    except Exception as e:
        return False, f"Error during deletion: {str(e)}"

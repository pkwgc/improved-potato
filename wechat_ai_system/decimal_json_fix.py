import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def decimal_json_dumps(obj):
    """Helper function to convert Decimal objects to float before JSON serialization"""
    return json.dumps(obj, cls=DecimalEncoder)

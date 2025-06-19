import json
from decimal import Decimal

def decimal_json_dumps(obj, **kwargs):
    """JSON encoder that handles Decimal objects"""
    def decimal_default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return json.dumps(obj, default=decimal_default, **kwargs)

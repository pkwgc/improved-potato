
from decimal import Decimal

token_usage_data=json.dumps({
    'labels': token_usage_data['labels'],
    'values': [float(v) if isinstance(v, Decimal) else v for v in token_usage_data['values']]
})

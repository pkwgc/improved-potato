from statistics_py import StatisticsService

class StatisticsServiceWrapper:
    """统计服务包装器，解决导入冲突问题"""
    
    def __init__(self, db):
        self.service = StatisticsService(db)
    
    def get_dashboard_stats(self):
        return self.service.get_dashboard_stats()
    
    def get_user_stats(self, user_id=None, username=None):
        return self.service.get_user_stats(user_id, username)
    
    def get_billing_stats(self, time_range='month'):
        return self.service.get_billing_stats(time_range)
    
    def get_token_package_stats(self):
        return self.service.get_token_package_stats()
    
    def get_user_chat_history(self, user_id=None, username=None, page=1, per_page=10, filter_type='all', search=None):
        return self.service.get_user_chat_history(user_id, username, page, per_page, filter_type, search)

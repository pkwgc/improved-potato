import time
import threading
from datetime import datetime, timedelta
from database import get_db
from proactive_messaging import ProactiveMessagingService
import logging

logger = logging.getLogger(__name__)

class SimpleScheduler:
    """简单的定时任务调度器，不依赖外部库"""
    def __init__(self):
        self.tasks = []
        self.running = False
    
    def every_minutes(self, minutes, func):
        """每N分钟执行一次"""
        self.tasks.append({
            'func': func,
            'interval': minutes * 60,  # 转换为秒
            'last_run': 0,
            'type': 'interval'
        })
    
    def every_hours(self, hours, func):
        """每N小时执行一次"""
        self.tasks.append({
            'func': func,
            'interval': hours * 3600,  # 转换为秒
            'last_run': 0,
            'type': 'interval'
        })
    
    def daily_at(self, time_str, func):
        """每天在指定时间执行"""
        hour, minute = map(int, time_str.split(':'))
        self.tasks.append({
            'func': func,
            'type': 'daily',
            'hour': hour,
            'minute': minute,
            'last_run_date': None
        })
    
    def run_pending(self):
        """检查并运行待执行的任务"""
        current_time = time.time()
        current_datetime = datetime.now()
        
        for task in self.tasks:
            try:
                if task.get('type') == 'daily':
                    if (current_datetime.hour == task['hour'] and 
                        current_datetime.minute == task['minute'] and
                        task['last_run_date'] != current_datetime.date()):
                        task['func']()
                        task['last_run_date'] = current_datetime.date()
                        logger.info(f"执行每日任务: {task['func'].__name__}")
                elif task.get('type') == 'interval':
                    if current_time - task['last_run'] >= task['interval']:
                        task['func']()
                        task['last_run'] = current_time
                        logger.info(f"执行间隔任务: {task['func'].__name__}")
            except Exception as e:
                logger.error(f"执行定时任务失败: {str(e)}")
    
    def clear(self):
        """清除所有任务"""
        self.tasks = []

class ScheduledTaskManager:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.proactive_service = ProactiveMessagingService(socketio)
        self.running = False
        self.scheduler = SimpleScheduler()
        
    def start_scheduler(self):
        """启动定时任务调度器"""
        if self.running:
            return
            
        self.running = True
        
        self.scheduler.every_minutes(1, self._send_pending_messages)
        self.scheduler.every_hours(1, self._check_follow_ups)
        self.scheduler.daily_at("02:00", self._cleanup_expired_data)
        
        def run_scheduler():
            while self.running:
                self.scheduler.run_pending()
                time.sleep(60)  # 每分钟检查一次
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("定时任务调度器已启动")
    
    def stop_scheduler(self):
        """停止定时任务调度器"""
        self.running = False
        self.scheduler.clear()
        logger.info("定时任务调度器已停止")
    
    def _send_pending_messages(self):
        """发送待发送的主动消息"""
        try:
            db = next(get_db())
            self.proactive_service.send_pending_messages(db)
            db.close()
        except Exception as e:
            logger.error(f"发送待发送消息失败: {str(e)}")
    
    def _check_follow_ups(self):
        """检查需要跟进的客户"""
        try:
            db = next(get_db())
            self.proactive_service.check_and_schedule_follow_ups(db)
            db.close()
        except Exception as e:
            logger.error(f"检查跟进客户失败: {str(e)}")
    
    def _cleanup_expired_data(self):
        """清理过期数据"""
        try:
            db = next(get_db())
            from database import OperationLog
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=30)
            
            expired_logs = db.query(OperationLog).filter(
                OperationLog.created_at < cutoff_date
            ).delete()
            
            db.commit()
            db.close()
            
            logger.info(f"已清理 {expired_logs} 条过期操作日志")
        except Exception as e:
            logger.error(f"清理过期数据失败: {str(e)}")

task_manager = None

def initialize_scheduler(socketio):
    """初始化定时任务调度器"""
    global task_manager
    task_manager = ScheduledTaskManager(socketio)
    task_manager.start_scheduler()

def shutdown_scheduler():
    """关闭定时任务调度器"""
    global task_manager
    if task_manager:
        task_manager.stop_scheduler()

"""
运行时间记录器
记录软件B的运行开始时间、结束时间和持续时间
"""
import time
import logging
import os
from datetime import datetime, timedelta

class RuntimeLogger:
    """软件B运行时间记录器"""
    
    def __init__(self, log_file="software_b_runtime.log"):
        """
        初始化运行时间记录器
        
        Args:
            log_file (str): 日志文件路径
        """
        self.log_file = log_file
        self.logger = logging.getLogger("RuntimeLogger")
        self.start_time = None
        self.process_name = ""
        
        # 确保日志文件存在并创建表头
        self._init_log_file()
    
    def _init_log_file(self):
        """初始化日志文件"""
        if not os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write("=== 软件B运行时间记录 ===\n")
                    f.write("格式：开始时间 | 结束时间 | 持续时间 | 进程名称\n")
                    f.write("=" * 80 + "\n\n")
                self.logger.info(f"创建运行时间日志文件: {self.log_file}")
            except Exception as e:
                self.logger.error(f"创建日志文件失败: {str(e)}")
    
    def set_process_name(self, process_name):
        """设置要监控的进程名称"""
        self.process_name = process_name
        self.logger.info(f"设置监控进程: {process_name}")
    
    def record_start(self, process_name=None):
        """记录软件B开始运行的时间"""
        if process_name:
            self.process_name = process_name
        
        self.start_time = time.time()
        start_datetime = datetime.fromtimestamp(self.start_time)
        
        self.logger.info(f"记录软件B开始运行: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 写入日志文件（开始记录）
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"🚀 开始运行: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')} | ")
                f.write(f"进程: {self.process_name}\n")
        except Exception as e:
            self.logger.error(f"写入开始时间日志失败: {str(e)}")
    
    def record_end(self):
        """记录软件B结束运行的时间并计算持续时间"""
        if self.start_time is None:
            self.logger.warning("未记录开始时间，无法计算持续时间")
            return
        
        end_time = time.time()
        end_datetime = datetime.fromtimestamp(end_time)
        start_datetime = datetime.fromtimestamp(self.start_time)
        
        # 计算持续时间
        duration_seconds = end_time - self.start_time
        duration_timedelta = timedelta(seconds=int(duration_seconds))
        
        # 格式化持续时间
        hours, remainder = divmod(int(duration_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        self.logger.info(f"记录软件B结束运行: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"运行持续时间: {duration_str}")
        
        # 写入日志文件（完整记录）
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"🔴 结束运行: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')} | ")
                f.write(f"持续时间: {duration_str} | ")
                f.write(f"进程: {self.process_name}\n")
                f.write(f"完整记录: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')} -> ")
                f.write(f"{end_datetime.strftime('%Y-%m-%d %H:%M:%S')} ")
                f.write(f"({duration_str})\n")
                f.write("-" * 80 + "\n")
        except Exception as e:
            self.logger.error(f"写入结束时间日志失败: {str(e)}")
        
        # 重置开始时间
        self.start_time = None
    
    def record_crash_or_interrupt(self, reason="未知原因"):
        """记录软件B异常退出或中断"""
        if self.start_time is None:
            self.logger.warning("未记录开始时间，无法记录异常退出")
            return
        
        end_time = time.time()
        end_datetime = datetime.fromtimestamp(end_time)
        start_datetime = datetime.fromtimestamp(self.start_time)
        
        # 计算持续时间
        duration_seconds = end_time - self.start_time
        hours, remainder = divmod(int(duration_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        self.logger.warning(f"记录软件B异常退出: {reason}")
        
        # 写入日志文件（异常记录）
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"⚠️ 异常退出: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')} | ")
                f.write(f"持续时间: {duration_str} | ")
                f.write(f"原因: {reason} | ")
                f.write(f"进程: {self.process_name}\n")
                f.write(f"完整记录: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')} -> ")
                f.write(f"{end_datetime.strftime('%Y-%m-%d %H:%M:%S')} ")
                f.write(f"({duration_str}) [异常退出]\n")
                f.write("-" * 80 + "\n")
        except Exception as e:
            self.logger.error(f"写入异常退出日志失败: {str(e)}")
        
        # 重置开始时间
        self.start_time = None
    
    def get_current_runtime(self):
        """获取当前运行时间（如果正在运行中）"""
        if self.start_time is None:
            return None
        
        current_time = time.time()
        duration_seconds = current_time - self.start_time
        
        hours, remainder = divmod(int(duration_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return duration_str
    
    def is_running(self):
        """检查是否正在记录运行时间"""
        return self.start_time is not None
    
    def get_log_file_path(self):
        """获取日志文件路径"""
        return os.path.abspath(self.log_file)
    
    def get_stats(self):
        """获取运行时间统计信息"""
        if not os.path.exists(self.log_file):
            return {"total_sessions": 0, "total_runtime": "00:00:00"}
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            sessions = 0
            total_seconds = 0
            
            for line in lines:
                if "持续时间:" in line:
                    sessions += 1
                    # 提取持续时间
                    try:
                        duration_part = line.split("持续时间:")[1].split("|")[0].strip()
                        time_parts = duration_part.split(":")
                        if len(time_parts) == 3:
                            hours = int(time_parts[0])
                            minutes = int(time_parts[1])
                            seconds = int(time_parts[2])
                            total_seconds += hours * 3600 + minutes * 60 + seconds
                    except:
                        pass
            
            # 格式化总时间
            total_hours, remainder = divmod(total_seconds, 3600)
            total_minutes, total_secs = divmod(remainder, 60)
            total_runtime = f"{total_hours:02d}:{total_minutes:02d}:{total_secs:02d}"
            
            return {
                "total_sessions": sessions,
                "total_runtime": total_runtime,
                "total_seconds": total_seconds
            }
            
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {str(e)}")
            return {"total_sessions": 0, "total_runtime": "00:00:00"} 
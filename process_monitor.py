import time
import logging
import psutil
import win32gui
import win32process

class ProcessMonitor:
    def __init__(self, process_name):
        """初始化进程监控器
        
        Args:
            process_name (str): 要监控的进程名称
        """
        self.process_name = process_name
        self.logger = logging.getLogger("ProcessMonitor")
        self.logger.info(f"进程监控器初始化，监控进程: {process_name}")
    
    def set_process_name(self, process_name):
        """设置要监控的进程名称
        
        Args:
            process_name (str): 进程名称
        """
        self.process_name = process_name
        self.logger.info(f"更新监控进程名称: {process_name}")
    
    def is_process_running(self):
        """检查进程是否正在运行
        
        Returns:
            bool: 进程是否在运行
        """
        if not self.process_name:
            return False
        
        self.logger.info(f"检查进程 '{self.process_name}' 是否运行")
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and self.process_name.lower() in proc.info['name'].lower():
                        self.logger.info(f"找到运行中的进程: {proc.info['name']} (PID: {proc.info['pid']})")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            self.logger.info(f"未找到进程 '{self.process_name}'")
            return False
            
        except Exception as e:
            self.logger.error(f"检查进程状态时出错: {str(e)}")
            return False
    
    def get_process_pid(self):
        """获取进程的PID
        
        Returns:
            int: 进程PID，如果未找到返回0
        """
        if not self.process_name:
            return 0
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and self.process_name.lower() in proc.info['name'].lower():
                        self.logger.info(f"找到进程ID: {proc.info['pid']} 对应进程名: {proc.info['name']}")
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            self.logger.warning(f"未找到进程名为 '{self.process_name}' 的进程ID")
            return 0
            
        except Exception as e:
            self.logger.error(f"获取进程ID时出错: {str(e)}")
            return 0
    
    def get_all_process_pids(self):
        """获取所有匹配进程的PID列表
        
        Returns:
            List[int]: 进程PID列表
        """
        if not self.process_name:
            return []
        
        pids = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and self.process_name.lower() in proc.info['name'].lower():
                        pids.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            self.logger.warning(f"未找到进程名为 '{self.process_name}' 的进程")
            
        except Exception as e:
            self.logger.error(f"获取进程PID列表时出错: {str(e)}")
        
        self.logger.info(f"查找进程 '{self.process_name}' 的窗口，找到进程ID: {pids}")
        return pids
    
    def get_main_window(self):
        """获取进程的主窗口
        
        Returns:
            tuple: (hwnd, title) 窗口句柄和标题，失败时返回(0, "")
        """
        pids = self.get_all_process_pids()
        if not pids:
            return (0, "")
        
        result = []
        
        def callback(hwnd, data):
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid in pids:
                    title = win32gui.GetWindowText(hwnd)
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    if width > 100 and height > 100:  # 只考虑足够大的窗口
                        data.append((hwnd, width * height, title))
            return True
        
        win32gui.EnumWindows(callback, result)
        
        # 按窗口面积排序，取最大的作为主窗口
        if result:
            result.sort(key=lambda x: x[1], reverse=True)
            hwnd, _, title = result[0]
            self.logger.info(f"找到进程 '{self.process_name}' 的主窗口: 句柄={hwnd}, 标题='{title}'")
            return (hwnd, title)
        
        self.logger.warning(f"未找到进程 '{self.process_name}' 的主窗口")
        return (0, "")
    
    def wait_for_process_exit(self, check_interval=10):
        """等待进程退出
        
        Args:
            check_interval (int): 检查间隔（秒）
        """
        self.logger.info(f"开始监控进程 '{self.process_name}' 直到退出，检查间隔: {check_interval}秒")
        
        while self.is_process_running():
            time.sleep(check_interval)
        
        self.logger.info(f"进程 '{self.process_name}' 已退出")
    
    def wait_for_process_start(self, timeout=300, check_interval=5):
        """等待进程启动
        
        Args:
            timeout (int): 超时时间（秒）
            check_interval (int): 检查间隔（秒）
            
        Returns:
            bool: 进程是否在超时时间内启动
        """
        self.logger.info(f"开始监控进程 '{self.process_name}' 直到启动，超时: {timeout}秒，检查间隔: {check_interval}秒")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_process_running():
                self.logger.info(f"进程 '{self.process_name}' 已启动")
                return True
            time.sleep(check_interval)
        
        self.logger.warning(f"监控超时，进程 '{self.process_name}' 未启动")
        return False
    
    def get_process_info(self):
        """获取进程详细信息
        
        Returns:
            Dict: 进程信息字典
        """
        pid = self.get_process_pid()
        if not pid:
            return {}
        
        try:
            proc = psutil.Process(pid)
            info = {
                "pid": pid,
                "name": proc.name(),
                "status": proc.status(),
                "create_time": proc.create_time(),
                "cpu_percent": proc.cpu_percent(),
                "memory_info": proc.memory_info()._asdict(),
                "num_threads": proc.num_threads()
            }
            
            # 尝试获取可执行文件路径
            try:
                info["exe"] = proc.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                info["exe"] = "无权限访问"
            
            return info
            
        except Exception as e:
            self.logger.error(f"获取进程信息时出错: {str(e)}")
            return {}
    
    def terminate_process(self):
        """终止监控的进程
        
        Returns:
            bool: 是否成功终止进程
        """
        pid = self.get_process_pid()
        if not pid:
            self.logger.warning(f"未找到要终止的进程 '{self.process_name}'")
            return False
        
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            
            # 等待进程终止
            try:
                proc.wait(timeout=10)
                self.logger.info(f"成功终止进程 '{self.process_name}' (PID: {pid})")
                return True
            except psutil.TimeoutExpired:
                # 如果进程没有在10秒内终止，强制杀死
                proc.kill()
                self.logger.info(f"强制杀死进程 '{self.process_name}' (PID: {pid})")
                return True
                
        except Exception as e:
            self.logger.error(f"终止进程时出错: {str(e)}")
            return False 
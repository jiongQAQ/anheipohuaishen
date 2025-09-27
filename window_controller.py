import os
import time
import logging
import subprocess
import psutil
import win32gui
import win32con
import win32api
import win32process
import re

class WindowController:
    """窗口控制器，处理窗口的查找、操作和进程控制"""
    
    def __init__(self):
        """初始化窗口控制器"""
        # 配置日志
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger("WindowController")
    
    def start_process(self, process_path):
        """启动一个进程
        
        Args:
            process_path (str): 进程可执行文件的路径
            
        Returns:
            int: 进程ID
        """
        try:
            # 处理路径中的空格
            if ' ' in process_path and not process_path.startswith('"'):
                process_path = f'"{process_path}"'
            
            self.logger.info(f"启动进程: {process_path}")
            
            # 启动进程并返回进程ID
            # 使用shell=True来处理路径中的空格问题
            process = subprocess.Popen(process_path, shell=True)
            
            # 获取真实的进程ID (可能与shell进程不同)
            if process.pid:
                self.logger.info(f"进程ID: {process.pid}")
                
                # 等待一会儿确保进程启动
                time.sleep(1)
                
                # 尝试根据可执行文件名查找真实进程
                exe_name = os.path.basename(process_path.replace('"', ''))
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        if exe_name.lower() in proc.info['name'].lower() or \
                           (proc.info['exe'] and exe_name.lower() in proc.info['exe'].lower()):
                            real_pid = proc.info['pid']
                            self.logger.info(f"找到匹配进程: {real_pid}, {proc.info['name']}")
                            return real_pid
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                
                # 如果找不到更精确的匹配，返回原始PID
                return process.pid
            else:
                raise Exception("无法获取进程ID")
        except Exception as e:
            self.logger.error(f"启动进程失败: {str(e)}")
            raise
    
    def terminate_process(self, pid):
        """终止一个进程
        
        Args:
            pid (int): 进程ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            process = psutil.Process(pid)
            process.terminate()
            return True
        except Exception as e:
            self.logger.error(f"终止进程失败: {str(e)}")
            return False
    
    def is_process_running(self, pid):
        """检查进程是否在运行
        
        Args:
            pid (int): 进程ID
            
        Returns:
            bool: 进程是否在运行
        """
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except:
            return False
    
    def find_window_by_pid(self, pid):
        """根据进程ID查找窗口句柄
        
        Args:
            pid (int): 进程ID
            
        Returns:
            int: 窗口句柄，失败时返回0
        """
        self.logger.info(f"尝试查找PID为 {pid} 的窗口")
        result = []
        
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == pid:
                    title = win32gui.GetWindowText(hwnd)
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    self.logger.info(f"找到匹配窗口: 句柄={hwnd}, 标题='{title}', 大小={width}x{height}")
                    hwnds.append((hwnd, width * height, title))
            return True
        
        win32gui.EnumWindows(callback, result)
        
        # 过滤掉小窗口，通常主窗口会更大
        main_windows = []
        for hwnd, size, title in result:
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            # 窗口必须足够大才可能是主窗口
            if width > 100 and height > 100:  # 降低尺寸要求以匹配更多窗口
                main_windows.append((hwnd, size, title))
        
        # 按窗口面积排序，取最大的
        if main_windows:
            main_windows.sort(key=lambda x: x[1], reverse=True)
            self.logger.info(f"选择最大的匹配窗口: {main_windows[0][0]}, 标题='{main_windows[0][2]}'")
            return main_windows[0][0]
        
        self.logger.warning(f"未找到PID为 {pid} 的可见窗口")
        return 0
    
    def find_all_windows_by_process_name(self, process_name):
        """根据进程名查找所有窗口
        
        Args:
            process_name (str): 进程名称
            
        Returns:
            list: [(hwnd, pid, title), ...] 窗口句柄、进程ID和标题的列表
        """
        result = []
        
        # 获取与进程名匹配的所有PID
        pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        self.logger.info(f"查找进程名 '{process_name}' 的窗口，找到相关进程ID: {pids}")
        
        # 查找所有这些PID的窗口
        def callback(hwnd, data):
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid in pids:
                    title = win32gui.GetWindowText(hwnd)
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    if width > 100 and height > 100:  # 只考虑足够大的窗口
                        self.logger.info(f"找到窗口: 句柄={hwnd}, PID={found_pid}, 标题='{title}', 大小={width}x{height}")
                        data.append((hwnd, found_pid, title, width * height))
            return True
            
        windows = []
        win32gui.EnumWindows(callback, windows)
        
        # 按大小排序
        windows.sort(key=lambda x: x[3], reverse=True)
        
        return [(hwnd, pid, title) for hwnd, pid, title, _ in windows]
    
    def find_window_by_title_pattern(self, pattern):
        """根据窗口标题模式查找窗口句柄
        
        Args:
            pattern (str): 窗口标题的正则表达式模式
            
        Returns:
            int: 窗口句柄，失败时返回0
        """
        self.logger.info(f"使用模式 '{pattern}' 查找窗口")
        result = []
        regex = re.compile(pattern)
        
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and regex.search(title):
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    # 窗口必须足够大才可能是主窗口
                    if width > 100 and height > 100:  # 降低尺寸要求
                        self.logger.info(f"找到匹配模式的窗口: 句柄={hwnd}, 标题='{title}', 大小={width}x{height}")
                        hwnds.append((hwnd, width * height, title))
            return True
        
        win32gui.EnumWindows(callback, result)
        
        # 按窗口面积排序，取最大的
        if result:
            result.sort(key=lambda x: x[1], reverse=True)
            self.logger.info(f"选择最大的匹配窗口: {result[0][0]}, 标题='{result[0][2]}'")
            return result[0][0]
        
        self.logger.warning(f"未找到匹配模式 '{pattern}' 的窗口")
        return 0
    
    def get_window_rect(self, hwnd):
        """获取窗口矩形
        
        Args:
            hwnd (int): 窗口句柄
            
        Returns:
            tuple: (left, top, right, bottom)，失败时返回None
        """
        try:
            return win32gui.GetWindowRect(hwnd)
        except Exception as e:
            self.logger.error(f"获取窗口位置失败: {str(e)}")
            return None
    
    def get_window_position(self, hwnd):
        """获取窗口位置
        
        Args:
            hwnd (int): 窗口句柄
            
        Returns:
            tuple: (x, y)，失败时返回None
        """
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return (rect[0], rect[1])
        except Exception as e:
            self.logger.error(f"获取窗口位置失败: {str(e)}")
            return None
    
    def set_window_position(self, hwnd, x, y):
        """设置窗口位置
        
        Args:
            hwnd (int): 窗口句柄
            x (int): 窗口左上角的x坐标
            y (int): 窗口左上角的y坐标
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取当前窗口的宽高
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            
            self.logger.info(f"设置窗口位置: hwnd={hwnd}, 新位置=({x}, {y}), 大小={width}x{height}")
            
            # 调整窗口位置，不改变大小
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, width, height, 
                                 win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            return True
        except Exception as e:
            self.logger.error(f"设置窗口位置失败: {str(e)}")
            return False
    
    def activate_window(self, hwnd):
        """激活窗口并设为前台
        
        Args:
            hwnd (int): 窗口句柄
            
        Returns:
            bool: 操作是否成功
        """
        if not hwnd:
            self.logger.error("无效的窗口句柄")
            return False
            
        try:
            # 确保窗口可见且不是最小化状态
            if not win32gui.IsWindowVisible(hwnd):
                self.logger.info(f"窗口 {hwnd} 不可见，尝试显示")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # 检查窗口是否最小化，如果是则恢复
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                self.logger.info(f"窗口 {hwnd} 已最小化，尝试恢复")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # 将窗口设为前台
            self.logger.info(f"尝试激活窗口 {hwnd} 并设为前台")
            
            # 获取当前前台窗口
            foreground_hwnd = win32gui.GetForegroundWindow()
            
            # 如果当前窗口已经是前台，则无需操作
            if foreground_hwnd == hwnd:
                self.logger.info("窗口已经是前台窗口")
                return True
            
            # 尝试常规方法设为前台
            if not win32gui.SetForegroundWindow(hwnd):
                self.logger.warning("SetForegroundWindow失败，尝试替代方法")
                
                # 替代方法1: 使用Alt+Tab模拟
                try:
                    # 获取窗口线程ID
                    current_thread = win32api.GetCurrentThreadId()
                    window_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
                    
                    # 附加线程输入
                    win32process.AttachThreadInput(current_thread, window_thread, True)
                    
                    # 设置为前台
                    win32gui.SetForegroundWindow(hwnd)
                    win32gui.BringWindowToTop(hwnd)
                    
                    # 分离线程
                    win32process.AttachThreadInput(current_thread, window_thread, False)
                except Exception as e:
                    self.logger.error(f"替代方法1失败: {str(e)}")
                    
                    # 替代方法2: 使用SendMessage
                    try:
                        win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_RESTORE, 0)
                        win32gui.SendMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
                    except Exception as e2:
                        self.logger.error(f"替代方法2失败: {str(e2)}")
                        return False
            
            # 验证窗口是否成为前台
            time.sleep(0.5)  # 给系统一些时间处理
            if win32gui.GetForegroundWindow() == hwnd:
                self.logger.info("窗口已成功设为前台")
                return True
            else:
                self.logger.warning("无法将窗口设为前台")
                return False
                
        except Exception as e:
            self.logger.error(f"激活窗口失败: {str(e)}")
            return False
    
    def force_activate_window(self, hwnd):
        """强制激活窗口到前台（更激进的方法）
        
        Args:
            hwnd (int): 窗口句柄
            
        Returns:
            bool: 操作是否成功
        """
        if not hwnd:
            self.logger.error("无效的窗口句柄")
            return False
            
        try:
            self.logger.info(f"强制激活窗口 {hwnd}")
            
            # 方法1：显示并恢复窗口
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            
            # 方法2：发送激活消息
            win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_RESTORE, 0)
            
            # 方法3：使用SetWindowPos提升窗口
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            time.sleep(0.1)
            
            # 移除置顶属性
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            
            # 方法4：线程输入附加
            try:
                current_thread = win32api.GetCurrentThreadId()
                window_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
                
                if current_thread != window_thread:
                    win32process.AttachThreadInput(current_thread, window_thread, True)
                    
                    # 设置为前台
                    win32gui.SetForegroundWindow(hwnd)
                    win32gui.BringWindowToTop(hwnd)
                    
                    # 发送激活消息
                    win32gui.SendMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
                    
                    # 分离线程
                    win32process.AttachThreadInput(current_thread, window_thread, False)
                else:
                    win32gui.SetForegroundWindow(hwnd)
                    win32gui.BringWindowToTop(hwnd)
                    
            except Exception as e:
                self.logger.warning(f"线程输入附加失败: {str(e)}")
                # 降级到基本方法
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
            
            # 验证结果
            time.sleep(0.5)
            foreground_hwnd = win32gui.GetForegroundWindow()
            
            if foreground_hwnd == hwnd:
                self.logger.info("窗口强制激活成功")
                return True
            else:
                self.logger.warning(f"窗口强制激活失败：前台窗口是 {foreground_hwnd}，期望 {hwnd}")
                
                # 最后尝试：模拟Alt+Tab切换
                try:
                    # 获取窗口标题
                    title = win32gui.GetWindowText(hwnd)
                    self.logger.info(f"尝试通过窗口标题激活: '{title}'")
                    
                    # 使用键盘模拟（需要pyautogui）
                    import pyautogui
                    pyautogui.hotkey('alt', 'tab')
                    time.sleep(0.2)
                    
                    # 再次验证
                    time.sleep(0.5)
                    if win32gui.GetForegroundWindow() == hwnd:
                        self.logger.info("通过Alt+Tab成功激活窗口")
                        return True
                        
                except Exception as e:
                    self.logger.error(f"Alt+Tab激活失败: {str(e)}")
                
                return False
                
        except Exception as e:
            self.logger.error(f"强制激活窗口失败: {str(e)}")
            return False
    
    def center_window(self, pid):
        """将指定进程的窗口居中显示并激活
        
        Args:
            pid (int): 进程ID
            
        Returns:
            bool: 操作是否成功，同时返回窗口句柄
        """
        # 给进程更多时间创建窗口
        self.logger.info(f"等待PID为 {pid} 的进程创建窗口...")
        hwnd = 0
        
        for attempt in range(1, 11):  # 尝试10次，每次等待1秒
            # 查找窗口
            hwnd = self.find_window_by_pid(pid)
            if hwnd:
                self.logger.info(f"通过PID找到窗口: {hwnd}")
                break
                
            # 尝试使用标题模式查找（英文+数字的模式）
            hwnd = self.find_window_by_title_pattern(r'[a-zA-Z]+\d+')
            if hwnd:
                self.logger.info(f"通过标题模式找到窗口: {hwnd}")
                break
                
            self.logger.info(f"尝试 #{attempt}: 未找到窗口，等待1秒...")
            time.sleep(1)
        
        # 如果上面方法都失败，尝试使用进程名查找
        if not hwnd:
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
                self.logger.info(f"尝试使用进程名查找: {proc_name}")
                
                windows = self.find_all_windows_by_process_name(proc_name)
                if windows:
                    hwnd = windows[0][0]  # 取第一个窗口
                    self.logger.info(f"通过进程名找到窗口: {hwnd}")
            except Exception as e:
                self.logger.error(f"通过进程名查找窗口失败: {str(e)}")
                
        # 如果仍未找到窗口
        if not hwnd:
            self.logger.error("无法找到目标窗口")
            return False
        
        return self.center_window_by_hwnd(hwnd)
    
    def center_window_by_hwnd(self, hwnd):
        """通过窗口句柄将窗口居中显示并激活
        
        Args:
            hwnd (int): 窗口句柄
            
        Returns:
            bool: 操作是否成功
        """
        if not hwnd:
            self.logger.error("无效的窗口句柄")
            return False
            
        try:
            # 确保窗口可见
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # 获取窗口尺寸
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            
            # 获取屏幕尺寸
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            # 计算居中位置
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            
            self.logger.info(f"窗口句柄 {hwnd}: 屏幕尺寸 {screen_width}x{screen_height}, 窗口尺寸 {width}x{height}")
            self.logger.info(f"居中位置: ({x}, {y})")
            
            # 设置窗口位置
            result = self.set_window_position(hwnd, x, y)
            
            # 激活窗口并设为前台
            self.logger.info("尝试激活窗口并设为前台")
            self.activate_window(hwnd)
            
            # 等待窗口激活
            time.sleep(0.5)
            
            # 再次检查窗口是否为前台
            if win32gui.GetForegroundWindow() != hwnd:
                self.logger.warning("窗口未成为前台，再次尝试")
                self.activate_window(hwnd)
            
            return result
        except Exception as e:
            self.logger.error(f"居中窗口失败: {str(e)}")
            return False
    
    def get_foreground_window_info(self):
        """获取前台窗口信息
        
        Returns:
            tuple: (hwnd, title, rect)，失败时返回(0, "", None)
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                self.logger.warning("无法获取前台窗口句柄")
                return (0, "", None)
            
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            
            # 获取进程ID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            self.logger.info(f"前台窗口信息: 句柄={hwnd}, 标题='{title}', PID={pid}, 位置={rect}")
            return (hwnd, title, rect)
        except Exception as e:
            self.logger.error(f"获取前台窗口信息失败: {str(e)}")
            return (0, "", None) 
import os
import time
import logging
import psutil
import win32gui
import win32process
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import keyboard

class CoordinateRecorder(QObject):
    # 信号：记录到新坐标时发出
    coordinate_recorded = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("CoordinateRecorder")
        self.target_process_path = ""
        self.target_hwnd = None
        self.recording = False
        self.recorded_count = 0
        
    def set_target_process(self, process_path):
        """设置目标进程路径
        
        Args:
            process_path (str): 目标进程的可执行文件路径
        """
        self.target_process_path = process_path
        self.logger.info(f"设置目标进程: {process_path}")
        
        # 尝试找到当前运行的目标进程窗口
        self.find_target_window()
    
    def find_target_window(self):
        """查找目标进程的窗口"""
        if not self.target_process_path:
            return
        
        try:
            exe_name = os.path.basename(self.target_process_path)
            self.logger.info(f"查找进程: {exe_name}")
            
            # 查找匹配的进程
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if (exe_name.lower() in proc.info['name'].lower()):
                        pid = proc.info['pid']
                        self.logger.info(f"找到匹配进程: {pid}, {proc.info['name']}")
                        
                        # 查找该进程的窗口
                        hwnd = self.find_window_by_pid(pid)
                        if hwnd:
                            self.target_hwnd = hwnd
                            self.logger.info(f"找到目标窗口句柄: {hwnd}")
                            return
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            self.logger.warning(f"未找到进程 {exe_name} 的窗口")
            
        except Exception as e:
            self.logger.error(f"查找目标窗口时出错: {str(e)}")
    
    def find_window_by_pid(self, pid):
        """根据进程ID查找窗口句柄"""
        result = []
        
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == pid:
                    title = win32gui.GetWindowText(hwnd)
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    if width > 100 and height > 100:  # 只考虑足够大的窗口
                        hwnds.append((hwnd, width * height, title))
            return True
        
        win32gui.EnumWindows(callback, result)
        
        # 按窗口面积排序，取最大的
        if result:
            result.sort(key=lambda x: x[1], reverse=True)
            return result[0][0]
        
        return 0
    
    def start_recording(self):
        """开始监听快捷键"""
        if self.recording:
            return
        
        self.recording = True
        self.recorded_count = 0
        
        # 注册快捷键
        try:
            keyboard.add_hotkey('ctrl+3', self.on_hotkey_pressed)
            self.logger.info("开始监听 Ctrl+3 快捷键")
        except Exception as e:
            self.logger.error(f"注册快捷键失败: {str(e)}")
    
    def stop_recording(self):
        """停止监听快捷键"""
        if not self.recording:
            return
        
        self.recording = False
        
        try:
            keyboard.remove_hotkey('ctrl+3')
            self.logger.info("停止监听快捷键")
        except Exception as e:
            self.logger.error(f"移除快捷键失败: {str(e)}")
    
    def on_hotkey_pressed(self):
        """快捷键按下时的回调"""
        if not self.recording:
            return
        
        try:
            # 获取当前鼠标位置（屏幕绝对坐标）
            import pyautogui
            mouse_x, mouse_y = pyautogui.position()
            
            # 获取当前前台窗口信息（仅用于日志显示）
            try:
                current_hwnd = win32gui.GetForegroundWindow()
                current_title = win32gui.GetWindowText(current_hwnd) if current_hwnd else "未知窗口"
            except:
                current_title = "未知窗口"
            
            self.logger.info(f"📍 鼠标绝对位置: ({mouse_x}, {mouse_y})")
            self.logger.info(f"📍 当前窗口: '{current_title}'")
            self.logger.info(f"✅ 已记录第{self.recorded_count + 1}个坐标: ({mouse_x}, {mouse_y})")
            
            # 发出信号（直接发送屏幕绝对坐标）
            self.coordinate_recorded.emit(mouse_x, mouse_y)
            
            self.recorded_count += 1
            
            # 如果已记录5个坐标，重置状态以便重新记录
            if self.recorded_count >= 5:
                self.logger.info(f"✅ 已记录5个坐标，重置状态等待下次记录")
                self.reset_recording()
                self.logger.info(f"🔄 可以继续使用 Ctrl+3 重新记录坐标")
            else:
                self.logger.info(f"📝 继续记录，还需要 {5 - self.recorded_count} 个坐标")
            
        except Exception as e:
            self.logger.error(f"❌ 记录坐标时出错: {str(e)}")
    
    def get_target_window_position(self):
        """获取目标窗口位置"""
        if self.target_hwnd:
            try:
                rect = win32gui.GetWindowRect(self.target_hwnd)
                return rect[0], rect[1]
            except Exception as e:
                self.logger.error(f"获取目标窗口位置失败: {str(e)}")
        
        # 如果没有目标窗口，使用前台窗口
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                title = win32gui.GetWindowText(hwnd)
                self.logger.info(f"使用前台窗口: {title}")
                return rect[0], rect[1]
        except Exception as e:
            self.logger.error(f"获取前台窗口位置失败: {str(e)}")
        
        return 0, 0
    
    def reset_recording(self):
        """重置记录状态"""
        self.recorded_count = 0
        self.logger.info("🔄 重置坐标记录状态，可重新开始记录")
        
    def restart_recording(self):
        """重新开始记录（清除之前的记录）"""
        self.reset_recording()
        if not self.recording:
            self.start_recording()
        self.logger.info("🆕 重新开始坐标记录")
    
    def __del__(self):
        """析构函数，确保清理快捷键"""
        self.stop_recording() 
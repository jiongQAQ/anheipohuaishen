import time
import logging
import pyautogui
import win32gui
import win32con
import win32api
import win32process
import random
import math

class ClickSequence:
    def __init__(self, click_interval=2.0, enable_trajectory=True):
        self.logger = logging.getLogger("ClickSequence")
        self.coordinates = []
        self.target_hwnd = None
        self.click_interval = click_interval  # 点击间隔时间
        self.enable_trajectory = enable_trajectory  # 是否启用轨迹移动
        
        # 设置pyautogui安全设置
        pyautogui.PAUSE = 0.01  # 减少暂停时间
        pyautogui.FAILSAFE = True
    
    def set_coordinates(self, coordinates):
        """设置点击坐标列表
        
        Args:
            coordinates (list): 坐标列表 [[x1, y1], [x2, y2], ...]
        """
        self.coordinates = coordinates
        self.logger.info(f"设置坐标列表: {coordinates}")
    
    def set_target_window(self, hwnd):
        """设置目标窗口句柄
        
        Args:
            hwnd (int): 窗口句柄
        """
        self.target_hwnd = hwnd
        self.logger.info(f"设置目标窗口句柄: {hwnd}")
    
    def ensure_window_foreground(self):
        """确保目标窗口在前台"""
        if not self.target_hwnd:
            self.logger.error("未设置目标窗口句柄")
            return False
        
        try:
            # 检查窗口是否存在
            if not win32gui.IsWindow(self.target_hwnd):
                self.logger.error("目标窗口已不存在")
                return False
            
            # 使用强制激活方法
            self.logger.info("正在强制激活目标窗口到前台...")
            success = self.force_activate_window(self.target_hwnd)
            
            if success:
                # 等待窗口激活
                time.sleep(0.5)
                
                # 验证窗口是否在前台
                foreground_hwnd = win32gui.GetForegroundWindow()
                if foreground_hwnd == self.target_hwnd:
                    self.logger.info("目标窗口已成功激活到前台")
                    return True
                else:
                    self.logger.warning(f"窗口激活可能失败，前台窗口: {foreground_hwnd}, 目标窗口: {self.target_hwnd}")
                    return True  # 仍然尝试继续
            else:
                self.logger.error("强制激活目标窗口失败")
                return False
                
        except Exception as e:
            self.logger.error(f"激活目标窗口时出错: {str(e)}")
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
                    
                    # 使用键盘模拟
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
    
    def get_window_position(self):
        """获取目标窗口位置"""
        if self.target_hwnd:
            try:
                rect = win32gui.GetWindowRect(self.target_hwnd)
                return rect[0], rect[1]  # 返回左上角坐标
            except Exception as e:
                self.logger.error(f"获取窗口位置失败: {str(e)}")
        
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
    
    def execute(self, username, password):
        """执行点击序列
        
        Args:
            username (str): 用户名
            password (str): 密码
        """
        # 🐛 详细调试信息
        self.logger.info(f"🔍 开始执行调试检查...")
        self.logger.info(f"🔍 用户名类型: {type(username)}, 值: {username}")
        self.logger.info(f"🔍 密码类型: {type(password)}, 值: {'***' if password else None}")
        self.logger.info(f"🔍 坐标列表类型: {type(self.coordinates)}, 长度: {len(self.coordinates) if self.coordinates else 0}")
        self.logger.info(f"🔍 坐标列表内容: {self.coordinates}")
        
        # 检查基本参数
        if username is None:
            raise Exception("用户名为None")
        if password is None:
            raise Exception("密码为None")
        if self.coordinates is None:
            raise Exception("坐标列表为None")
        
        if len(self.coordinates) != 5:
            raise Exception(f"需要设置5个坐标点，当前有{len(self.coordinates)}个")
        
        # 检查每个坐标是否有效
        for i, coord in enumerate(self.coordinates):
            self.logger.info(f"🔍 检查第{i+1}个坐标: {coord}, 类型: {type(coord)}")
            if coord is None:
                raise Exception(f"第{i+1}个坐标为None")
            if not isinstance(coord, (list, tuple)) or len(coord) != 2:
                raise Exception(f"第{i+1}个坐标格式错误: {coord}")
            try:
                x, y = int(coord[0]), int(coord[1])
                self.logger.info(f"🔍 第{i+1}个坐标解析成功: ({x}, {y})")
            except (ValueError, TypeError, IndexError) as e:
                raise Exception(f"第{i+1}个坐标数据错误: {coord}, 错误: {e}")
        
        self.logger.info(f"✅ 所有检查通过，开始执行点击序列")
        self.logger.info(f"开始执行点击序列，用户名: {username}")
        
        try:
            # 执行5个点击操作
            for i, coord in enumerate(self.coordinates):
                self.logger.info(f"准备执行第{i+1}个点击操作")
                
                # 直接使用绝对坐标
                abs_x = coord[0]
                abs_y = coord[1]
                
                self.logger.info(f"点击第{i+1}个坐标: 屏幕绝对坐标({abs_x}, {abs_y})")
                
                # 参考成熟代码的快速移动实现
                self.logger.info(f"🖱️ 快速移动鼠标到目标位置...")
                pyautogui.moveTo(abs_x, abs_y, duration=0.1)  # 0.1秒快速移动
                time.sleep(0.1)  # 短暂停顿确保移动完成
                
                # 验证移动位置
                actual_x, actual_y = pyautogui.position()
                self.logger.info(f"📍 目标位置: ({abs_x}, {abs_y})")
                self.logger.info(f"📍 实际位置: ({actual_x}, {actual_y})")
                
                # 简单直接点击
                pyautogui.click()
                self.logger.info(f"⚡ 快速点击完成")
                self.logger.info(f"✅ 第{i+1}个坐标点击完成")
                
                # 特殊处理第2个和第3个坐标（输入用户名和密码）
                if i == 1:  # 第2个坐标 - 输入用户名
                    self.logger.info("⌨️ 第2次点击后，全选并覆盖为用户名")
                    time.sleep(0.5)  # 等待界面响应
                    self.paste_text(username)
                    self.logger.info(f"✅ 用户名 '{username}' 覆盖完成")
                    
                elif i == 2:  # 第3个坐标 - 输入密码
                    self.logger.info("⌨️ 第3次点击后，全选并覆盖为密码")
                    time.sleep(0.5)  # 等待界面响应
                    self.paste_text(password)
                    self.logger.info("✅ 密码覆盖完成")
                
                # 每次操作后延迟指定时间再进行下一次点击
                if i < len(self.coordinates) - 1:
                    self.logger.info(f"等待{self.click_interval}秒后进行第{i+2}个点击...")
                    time.sleep(self.click_interval)
            
            self.logger.info("点击序列执行完成")
            
        except Exception as e:
            self.logger.error(f"执行点击序列时出错: {str(e)}")
            raise
    
    def test_click(self, coord_index):
        """测试单个坐标点击
        
        Args:
            coord_index (int): 坐标索引（0-4）
        """
        if coord_index >= len(self.coordinates):
            raise Exception(f"坐标索引 {coord_index} 超出范围")
        
        self.logger.info(f"准备测试第{coord_index+1}个坐标")
        
        coord = self.coordinates[coord_index]
        abs_x = coord[0]
        abs_y = coord[1]
        
        self.logger.info(f"测试点击坐标{coord_index+1}: 屏幕绝对坐标({abs_x}, {abs_y})")
        
        # 快速移动鼠标到目标位置
        self.logger.info(f"🖱️ 快速移动鼠标到目标位置...")
        pyautogui.moveTo(abs_x, abs_y, duration=0.1)  # 0.1秒快速移动
        time.sleep(0.1)  # 短暂停顿确保移动完成
        
        # 验证移动位置
        actual_x, actual_y = pyautogui.position()
        self.logger.info(f"📍 目标位置: ({abs_x}, {abs_y})")
        self.logger.info(f"📍 实际位置: ({actual_x}, {actual_y})")
        
        # 检查移动精度
        if abs(actual_x - abs_x) <= 2 and abs(actual_y - abs_y) <= 2:
            self.logger.info(f"✅ 移动精确")
        else:
            self.logger.warning(f"⚠️ 移动偏差: ({actual_x - abs_x}, {actual_y - abs_y})")
        
        # 简单直接点击
        pyautogui.click()
        self.logger.info(f"⚡ 快速点击完成")
        
        self.logger.info(f"坐标{coord_index+1}测试点击完成")
    
    def set_click_interval(self, interval):
        """设置点击间隔时间
        
        Args:
            interval (float): 间隔时间（秒）
        """
        self.click_interval = interval
        self.logger.info(f"设置点击间隔: {interval}秒")
    
    def set_enable_trajectory(self, enable):
        """设置是否启用轨迹移动
        
        Args:
            enable (bool): 是否启用轨迹移动
        """
        self.enable_trajectory = enable
        self.logger.info(f"设置轨迹移动: {'启用' if enable else '禁用'}")
    
    def move_mouse_with_trajectory(self, target_x, target_y, duration=0.5):
        """带轨迹的鼠标移动
        
        Args:
            target_x (int): 目标X坐标
            target_y (int): 目标Y坐标
            duration (float): 移动持续时间
        """
        # 获取当前鼠标位置
        start_x, start_y = pyautogui.position()
        
        # 计算移动距离
        distance = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)
        
        # 如果距离很小，直接移动
        if distance < 10:
            pyautogui.moveTo(target_x, target_y, duration=0.1)
            return
        
        # 计算移动步数（根据距离调整）
        steps = max(10, min(50, int(distance / 10)))
        
        # 生成贝塞尔曲线轨迹点
        trajectory_points = self.generate_bezier_trajectory(
            start_x, start_y, target_x, target_y, steps
        )
        
        # 计算每步的时间间隔
        step_duration = duration / steps
        
        self.logger.info(f"鼠标轨迹移动: ({start_x}, {start_y}) -> ({target_x}, {target_y}), 距离: {distance:.1f}px, 步数: {steps}")
        
        # 沿轨迹移动
        for i, (x, y) in enumerate(trajectory_points):
            # 添加轻微的随机抖动，模拟人手操作
            jitter_x = random.uniform(-1, 1)
            jitter_y = random.uniform(-1, 1)
            
            final_x = int(x + jitter_x)
            final_y = int(y + jitter_y)
            
            pyautogui.moveTo(final_x, final_y)
            
            # 变速移动：开始慢，中间快，结束慢
            if i < steps * 0.2:  # 前20%慢速
                time.sleep(step_duration * 1.5)
            elif i > steps * 0.8:  # 后20%慢速
                time.sleep(step_duration * 1.2)
            else:  # 中间60%正常速度
                time.sleep(step_duration * 0.8)
        
        # 确保最终到达目标位置
        pyautogui.moveTo(target_x, target_y)
        time.sleep(0.1)
    
    def generate_bezier_trajectory(self, start_x, start_y, end_x, end_y, steps):
        """生成贝塞尔曲线轨迹点
        
        Args:
            start_x, start_y: 起始坐标
            end_x, end_y: 结束坐标
            steps: 轨迹点数量
            
        Returns:
            list: 轨迹点列表 [(x1, y1), (x2, y2), ...]
        """
        # 生成控制点，创建自然的曲线
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2
        
        # 添加随机偏移，让轨迹更自然
        offset_range = max(20, min(100, abs(end_x - start_x) * 0.2))
        control1_x = mid_x + random.uniform(-offset_range, offset_range)
        control1_y = mid_y + random.uniform(-offset_range, offset_range)
        
        control2_x = mid_x + random.uniform(-offset_range, offset_range)
        control2_y = mid_y + random.uniform(-offset_range, offset_range)
        
        # 生成贝塞尔曲线点
        points = []
        for i in range(steps + 1):
            t = i / steps
            
            # 三次贝塞尔曲线公式
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * control1_x + 3*(1-t)*t**2 * control2_x + t**3 * end_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * control1_y + 3*(1-t)*t**2 * control2_y + t**3 * end_y
            
            points.append((x, y))
        
        return points
    
    def natural_click(self, x=None, y=None):
        """更自然的点击，包含按下和释放的延迟
        
        Args:
            x, y: 点击坐标，如果为None则在当前位置点击
        """
        if x is not None and y is not None:
            pyautogui.moveTo(x, y)
        
        # 获取当前鼠标位置用于日志
        current_x, current_y = pyautogui.position()
        self.logger.info(f"在位置 ({current_x}, {current_y}) 执行点击")
        
        # 模拟人手点击：按下-短暂停留-释放
        click_duration = random.uniform(0.05, 0.15)  # 随机点击持续时间
        
        pyautogui.mouseDown()
        time.sleep(click_duration)
        pyautogui.mouseUp()
        
        # 点击后短暂停留
        time.sleep(random.uniform(0.1, 0.2))
    
    def paste_text(self, text):
        """使用剪贴板方式粘贴文本，避免调用输入法"""
        try:
            import pyperclip
            
            # 备份当前剪贴板内容
            original_clipboard = ""
            try:
                original_clipboard = pyperclip.paste()
            except:
                pass
            
            # 先全选现有文本
            self.logger.info(f"🔄 全选现有文本...")
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)  # 等待全选完成
            
            # 将文本复制到剪贴板
            pyperclip.copy(text)
            time.sleep(0.1)  # 等待剪贴板更新
            
            # 使用Ctrl+V粘贴（会覆盖已选中的文本）
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.2)  # 等待粘贴完成
            
            # 恢复原剪贴板内容
            if original_clipboard:
                pyperclip.copy(original_clipboard)
            
            self.logger.info(f"📋 已全选并覆盖文本: {text}")
            return True
            
        except ImportError:
            self.logger.warning("pyperclip未安装，使用备用输入方式")
            # 备用方案：使用pyautogui直接输入
            try:
                # 先全选再输入
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.1)
                pyautogui.typewrite(text, interval=0.05)
                return True
            except Exception as e2:
                self.logger.error(f"直接输入也失败: {e2}")
                return False
        except Exception as e:
            self.logger.error(f"剪贴板粘贴失败: {e}，尝试直接输入...")
            # 备用方案：使用pyautogui直接输入
            try:
                # 先全选再输入
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.1)
                pyautogui.typewrite(text, interval=0.05)
                return True
            except Exception as e2:
                self.logger.error(f"直接输入也失败: {e2}")
                return False

    def natural_type(self, text):
        """更自然的文本输入，包含随机的输入速度
        
        Args:
            text (str): 要输入的文本
        """
        for char in text:
            # 随机输入间隔，模拟真实打字速度
            interval = random.uniform(0.03, 0.12)
            pyautogui.typewrite(char, interval=0)
            time.sleep(interval)
            
            # 偶尔添加短暂停顿，模拟思考
            if random.random() < 0.1:  # 10%概率停顿
                time.sleep(random.uniform(0.2, 0.5)) 
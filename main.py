import sys
import os
import json
import time
import logging
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from window_controller import WindowController
from click_sequence import ClickSequence
from account_manager import AccountManager
from process_monitor import ProcessMonitor
from coordinate_recorder import CoordinateRecorder
from runtime_logger import RuntimeLogger

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("自动化任务管理工具")
        self.setGeometry(100, 100, 800, 600)
        
        # 初始化组件
        self.window_controller = WindowController()
        self.click_sequence = ClickSequence()
        self.account_manager = AccountManager()
        self.process_monitor = ProcessMonitor("")
        self.coordinate_recorder = CoordinateRecorder()
        self.runtime_logger = RuntimeLogger("software_b_runtime.log")
        
        # 配置文件路径
        self.config_file = "config.json"
        self.config = self.load_config()
        
        # 任务线程
        self.task_thread = None
        
        # 设置日志
        self.setup_logging()
        
        # 初始化UI
        self.initUI()
        
        # 加载配置到UI
        self.load_config_to_ui()
        
        # 更新组件配置
        self.update_components_config()
        
        # 连接坐标记录器信号
        self.coordinate_recorder.coordinate_recorded.connect(self.add_coordinate)
        
        # 启动坐标记录器
        self.coordinate_recorder.start_recording()
    
    def setup_logging(self):
        """设置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('automation.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("MainWindow")
    
    def initUI(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        central_widget_layout = QVBoxLayout(central_widget)
        central_widget_layout.addWidget(tab_widget)
        
        # 配置页面
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "基础配置")
        
        # 账号管理页面
        account_tab = self.create_account_tab()
        tab_widget.addTab(account_tab, "账号管理")
        
        # 坐标设置页面
        coordinate_tab = self.create_coordinate_tab()
        tab_widget.addTab(coordinate_tab, "坐标设置")
        
        # 任务控制页面
        task_tab = self.create_task_tab()
        tab_widget.addTab(task_tab, "任务控制")
    
    def create_config_tab(self):
        """创建配置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 软件配置组
        software_group = QGroupBox("软件配置")
        software_layout = QGridLayout(software_group)
        
        software_layout.addWidget(QLabel("软件A路径:"), 0, 0)
        self.software_a_path_edit = QLineEdit()
        software_layout.addWidget(self.software_a_path_edit, 0, 1)
        browse_a_btn = QPushButton("浏览")
        browse_a_btn.clicked.connect(self.browse_software_a)
        software_layout.addWidget(browse_a_btn, 0, 2)
        
        software_layout.addWidget(QLabel("软件B进程名:"), 1, 0)
        self.software_b_name_edit = QLineEdit()
        self.software_b_name_edit.setPlaceholderText("例如: Diablo IV.exe")
        software_layout.addWidget(self.software_b_name_edit, 1, 1, 1, 2)
        
        layout.addWidget(software_group)
        
        # 鼠标行为配置组
        mouse_group = QGroupBox("鼠标行为配置")
        mouse_layout = QGridLayout(mouse_group)
        
        self.enable_trajectory_checkbox = QCheckBox("启用鼠标轨迹移动（更自然的鼠标移动）")
        self.enable_trajectory_checkbox.setChecked(True)
        mouse_layout.addWidget(self.enable_trajectory_checkbox, 0, 0, 1, 2)
        
        layout.addWidget(mouse_group)
        
        # Redis配置组
        redis_group = QGroupBox("Redis配置")
        redis_layout = QGridLayout(redis_group)
        
        redis_layout.addWidget(QLabel("主机:"), 0, 0)
        self.redis_host_edit = QLineEdit()
        redis_layout.addWidget(self.redis_host_edit, 0, 1)
        
        redis_layout.addWidget(QLabel("端口:"), 0, 2)
        self.redis_port_edit = QLineEdit("6379")
        redis_layout.addWidget(self.redis_port_edit, 0, 3)
        
        redis_layout.addWidget(QLabel("密码:"), 1, 0)
        self.redis_password_edit = QLineEdit()
        self.redis_password_edit.setEchoMode(QLineEdit.Password)
        redis_layout.addWidget(self.redis_password_edit, 1, 1)
        
        redis_layout.addWidget(QLabel("数据库:"), 1, 2)
        self.redis_db_edit = QLineEdit("0")
        redis_layout.addWidget(self.redis_db_edit, 1, 3)
        
        redis_layout.addWidget(QLabel("账号池键名:"), 2, 0)
        self.account_pool_key_edit = QLineEdit("account_pool_v3")
        redis_layout.addWidget(self.account_pool_key_edit, 2, 1, 1, 3)
        
        test_redis_btn = QPushButton("测试Redis连接")
        test_redis_btn.clicked.connect(self.test_redis_connection)
        redis_layout.addWidget(test_redis_btn, 3, 0, 1, 4)
        
        layout.addWidget(redis_group)
        
        # 保存配置按钮
        save_config_btn = QPushButton("保存配置")
        save_config_btn.clicked.connect(self.save_config)
        layout.addWidget(save_config_btn)
        
        layout.addStretch()
        return widget
    
    def create_account_tab(self):
        """创建账号管理页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 账号列表
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(3)
        self.account_table.setHorizontalHeaderLabels(["用户名", "密码", "状态"])
        self.account_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.account_table)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        add_account_btn = QPushButton("添加账号")
        add_account_btn.clicked.connect(self.add_account)
        button_layout.addWidget(add_account_btn)
        
        edit_account_btn = QPushButton("编辑账号")
        edit_account_btn.clicked.connect(self.edit_account)
        button_layout.addWidget(edit_account_btn)
        
        delete_account_btn = QPushButton("删除账号")
        delete_account_btn.clicked.connect(self.delete_account)
        button_layout.addWidget(delete_account_btn)
        
        refresh_btn = QPushButton("刷新状态")
        refresh_btn.clicked.connect(self.refresh_accounts)
        button_layout.addWidget(refresh_btn)
        
        save_accounts_btn = QPushButton("保存到Redis")
        save_accounts_btn.clicked.connect(self.save_accounts_to_redis)
        button_layout.addWidget(save_accounts_btn)
        
        release_all_btn = QPushButton("一键释放全部")
        release_all_btn.clicked.connect(self.release_all_accounts)
        button_layout.addWidget(release_all_btn)

        dedup_accounts_btn = QPushButton("删除重复账号")
        dedup_accounts_btn.clicked.connect(self.remove_duplicate_accounts)
        button_layout.addWidget(dedup_accounts_btn)

        layout.addLayout(button_layout)
        return widget
    
    def create_coordinate_tab(self):
        """创建坐标设置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 说明文本
        info_label = QLabel("按 Ctrl+3 记录屏幕绝对坐标（可在任意窗口上记录）")
        info_label.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(info_label)
        
        # 坐标列表
        self.coordinate_table = QTableWidget()
        self.coordinate_table.setColumnCount(3)
        self.coordinate_table.setHorizontalHeaderLabels(["序号", "X坐标(绝对)", "Y坐标(绝对)"])
        self.coordinate_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.coordinate_table)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        clear_coordinates_btn = QPushButton("清空坐标")
        clear_coordinates_btn.clicked.connect(self.clear_coordinates)
        button_layout.addWidget(clear_coordinates_btn)
        
        # 【新增】重新记录按钮
        restart_recording_btn = QPushButton("重新记录坐标")
        restart_recording_btn.clicked.connect(self.restart_coordinate_recording)
        restart_recording_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        button_layout.addWidget(restart_recording_btn)
        
        test_software_a_btn = QPushButton("启动软件A并居中（测试用）")
        test_software_a_btn.clicked.connect(self.test_software_a)
        button_layout.addWidget(test_software_a_btn)
        
        # 添加测试坐标按钮
        test_coord_btn = QPushButton("测试坐标点击")
        test_coord_btn.clicked.connect(self.test_coordinates)
        button_layout.addWidget(test_coord_btn)
        
        # 添加显示坐标信息按钮
        show_coord_btn = QPushButton("显示坐标信息")
        show_coord_btn.clicked.connect(self.show_coordinate_info)
        button_layout.addWidget(show_coord_btn)
        
        layout.addLayout(button_layout)
        
        # 更新坐标显示
        self.update_coordinate_display()
        
        return widget
    
    def create_task_tab(self):
        """创建任务控制页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 任务控制按钮
        button_layout = QHBoxLayout()
        
        self.start_task_btn = QPushButton("开始任务")
        self.start_task_btn.clicked.connect(self.start_task)
        button_layout.addWidget(self.start_task_btn)
        
        self.stop_task_btn = QPushButton("停止任务")
        self.stop_task_btn.clicked.connect(self.stop_task)
        self.stop_task_btn.setEnabled(False)
        button_layout.addWidget(self.stop_task_btn)
        
        layout.addLayout(button_layout)
        
        # 日志显示
        log_label = QLabel("任务日志:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        return widget
    
    def load_config(self):
        """加载配置文件"""
        default_config = {
            "software_a_path": "D:/5.12 法师最新版/VCHelper.vmp.exe",
            "software_b_name": "Diablo IV.exe",
            "redis_host": "118.145.197.212",
            "redis_port": 6379,
            "redis_password": "redis_AGZ8Gd",
            "redis_db": 0,
            "account_pool_key": "account_pool_v3",
            "coordinates": [],
            "click_interval": 2.0,
            "monitor_interval": 30.0,
            "max_retries": 5,
            "enable_mouse_trajectory": True
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                self.logger.error(f"加载配置文件失败: {str(e)}")
        
        return default_config
    
    def save_config(self):
        """保存配置"""
        self.config.update({
            "software_a_path": self.software_a_path_edit.text(),
            "software_b_name": self.software_b_name_edit.text(),
            "redis_host": self.redis_host_edit.text(),
            "redis_port": int(self.redis_port_edit.text()),
            "redis_password": self.redis_password_edit.text(),
            "redis_db": int(self.redis_db_edit.text()),
            "account_pool_key": self.account_pool_key_edit.text(),
            "enable_mouse_trajectory": self.enable_trajectory_checkbox.isChecked()
        })
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "保存成功", "配置已保存")
            
            # 更新组件配置
            self.update_components_config()
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存配置时出错: {str(e)}")
    
    def load_config_to_ui(self):
        """将配置加载到UI"""
        self.software_a_path_edit.setText(self.config.get("software_a_path", ""))
        self.software_b_name_edit.setText(self.config.get("software_b_name", ""))
        self.redis_host_edit.setText(self.config.get("redis_host", ""))
        self.redis_port_edit.setText(str(self.config.get("redis_port", 6379)))
        self.redis_password_edit.setText(self.config.get("redis_password", ""))
        self.redis_db_edit.setText(str(self.config.get("redis_db", 0)))
        self.account_pool_key_edit.setText(self.config.get("account_pool_key", "account_pool_v3"))
        self.enable_trajectory_checkbox.setChecked(self.config.get("enable_mouse_trajectory", True))
    
    def update_components_config(self):
        """更新组件配置"""
        # 更新账号管理器配置
        redis_config = {
            "host": self.config.get("redis_host", ""),
            "port": self.config.get("redis_port", 6379),
            "password": self.config.get("redis_password", ""),
            "db": self.config.get("redis_db", 0)
        }
        self.logger.info(f"更新Redis配置: {redis_config['host']}:{redis_config['port']}, DB: {redis_config['db']}")
        
        self.account_manager.update_config(
            host=redis_config["host"],
            port=redis_config["port"],
            password=redis_config["password"],
            db=redis_config["db"]
        )
        
        # 更新进程监控器
        self.process_monitor.set_process_name(self.config["software_b_name"])
        
        # 更新运行时间记录器
        self.runtime_logger.set_process_name(self.config["software_b_name"])
        
        # 更新点击序列配置
        self.click_sequence.set_click_interval(self.config.get("click_interval", 2.0))
        self.click_sequence.set_coordinates(self.config.get("coordinates", []))
        self.click_sequence.set_enable_trajectory(self.config.get("enable_mouse_trajectory", True))
        
        # 更新坐标记录器
        if self.config["software_a_path"]:
            self.coordinate_recorder.set_target_process(self.config["software_a_path"])
    
    def browse_software_a(self):
        """选择软件A路径"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择软件A", "", "可执行文件 (*.exe)")
        if file_path:
            self.software_a_path_edit.setText(file_path)
    
    def test_redis_connection(self):
        """测试Redis连接"""
        try:
            # 临时创建账号管理器测试连接
            temp_manager = AccountManager()
            temp_manager.update_config(
                host=self.redis_host_edit.text(),
                port=int(self.redis_port_edit.text()),
                password=self.redis_password_edit.text(),
                db=int(self.redis_db_edit.text())
            )
            
            if temp_manager.test_connection():
                QMessageBox.information(self, "连接成功", "Redis连接正常")
            else:
                QMessageBox.warning(self, "连接失败", "无法连接到Redis服务器")
        except Exception as e:
            QMessageBox.critical(self, "连接错误", f"连接Redis时出错: {str(e)}")
    
    def add_coordinate(self, x, y):
        """添加坐标"""
        coordinates = self.config.get("coordinates", [])
        if len(coordinates) < 5:
            coordinates.append([x, y])
            self.config["coordinates"] = coordinates
            self.save_config()
            self.update_coordinate_display()
            
            # 参考成熟代码的确认信息
            coord_count = len(coordinates)
            self.log(f"📍 已添加第{coord_count}个坐标: ({x}, {y})")
            self.log(f"✅ 多坐标序列现有 {coord_count} 个坐标")
            
            if coord_count < 5:
                self.log(f"📝 继续按 Ctrl+3 添加坐标，还需要 {5 - coord_count} 个")
            else:
                self.log(f"🎯 已记录完整的5个坐标，可以开始测试")
                
            # 显示确认对话框
            QMessageBox.information(
                self, 
                f"坐标{coord_count}添加成功",
                f"第{coord_count}个坐标已添加!\n\n"
                f"屏幕绝对坐标: ({x}, {y})\n\n"
                f"当前共有 {coord_count} 个坐标\n"
                f"{'按Ctrl+3继续添加' if coord_count < 5 else '可以开始测试点击了'}"
            )
        else:
            QMessageBox.warning(self, "坐标已满", "已记录5个坐标，请先清空再记录新坐标")
    
    def clear_coordinates(self):
        """清空坐标"""
        self.config["coordinates"] = []
        self.save_config()
        self.update_coordinate_display()
        # 重新开始记录状态
        self.coordinate_recorder.restart_recording()
        self.log("已清空所有坐标，可以重新使用Ctrl+3记录")
    
    def update_coordinate_display(self):
        """更新坐标显示"""
        coordinates = self.config.get("coordinates", [])
        self.coordinate_table.setRowCount(len(coordinates))
        
        for i, coord in enumerate(coordinates):
            self.coordinate_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.coordinate_table.setItem(i, 1, QTableWidgetItem(str(coord[0])))
            self.coordinate_table.setItem(i, 2, QTableWidgetItem(str(coord[1])))
    
    def test_software_a(self):
        """测试启动软件A并居中"""
        software_a_path = self.software_a_path_edit.text()
        if not software_a_path or not os.path.exists(software_a_path):
            QMessageBox.warning(self, "配置错误", "软件A路径不存在")
            return
        
        try:
            self.log(f"正在启动软件A: {software_a_path}")
            process_id = self.window_controller.start_process(software_a_path)
            
            # 等待窗口出现
            time.sleep(3)
            
            # 居中窗口
            if self.window_controller.center_window(process_id):
                self.log("软件A已启动并居中，可以开始记录坐标")
                
                # 更新坐标记录器的目标进程
                self.coordinate_recorder.set_target_process(software_a_path)
            else:
                self.log("无法找到软件A窗口")
                
        except Exception as e:
            self.log(f"启动软件A失败: {str(e)}")
    
    def test_coordinates(self):
        """测试坐标点击"""
        coordinates = self.config.get("coordinates", [])
        if not coordinates:
            QMessageBox.warning(self, "没有坐标", "请先记录一些坐标")
            return
        
        reply = QMessageBox.question(self, "测试坐标", 
                                   f"将测试 {len(coordinates)} 个坐标点击，确定继续吗？\n"
                                   "测试将在3秒后开始，请准备好目标窗口。",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log("🎯 开始测试坐标点击...")
            
            # 3秒倒计时
            for i in range(3, 0, -1):
                self.log(f"⏰ 倒计时: {i}秒")
                time.sleep(1)
            
            # 更新点击序列配置
            self.click_sequence.set_coordinates(coordinates)
            
            # 逐个测试坐标
            for i in range(len(coordinates)):
                try:
                    self.log(f"🖱️ 测试第{i+1}个坐标: ({coordinates[i][0]}, {coordinates[i][1]})")
                    
                    # 简单直接的测试点击
                    import pyautogui
                    x, y = coordinates[i][0], coordinates[i][1]
                    
                    # 快速移动并点击
                    pyautogui.moveTo(x, y, duration=0.1)
                    time.sleep(0.1)
                    pyautogui.click()
                    
                    self.log(f"✅ 第{i+1}个坐标测试完成")
                    time.sleep(1)  # 每次测试间隔1秒
                except Exception as e:
                    self.log(f"❌ 测试第{i+1}个坐标失败: {str(e)}")
            
            self.log("🎯 坐标测试完成")
    
    def show_coordinate_info(self):
        """显示坐标信息"""
        coordinates = self.config.get("coordinates", [])
        if not coordinates:
            QMessageBox.information(self, "坐标信息", "当前没有坐标\n\n请先按Ctrl+3记录坐标")
            return
        
        # 参考成熟代码的信息显示格式
        coord_info = []
        for i, coord in enumerate(coordinates):
            info = f"{i+1}. ({coord[0]}, {coord[1]})"
            coord_info.append(info)
        
        info_text = (
            f"当前坐标序列 ({len(coordinates)}个):\n\n" + 
            "\n".join(coord_info) +
            f"\n\n📝 执行说明:\n"
            f"- 第1次点击: 仅点击\n"
            f"- 第2次点击: 点击 + 全选覆盖用户名\n"
            f"- 第3次点击: 点击 + 全选覆盖密码\n"
            f"- 第4次点击: 仅点击\n"
            f"- 第5次点击: 仅点击\n\n"
            f"🎯 按'测试坐标点击'验证\n"
            f"🔄 按'清空坐标'重新设置"
        )
        
        QMessageBox.information(self, "坐标信息", info_text)
        self.log(f"📋 显示坐标信息: {len(coordinates)}个坐标")
    
    def add_account(self):
        """添加账号"""
        dialog = AccountDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            username, password = dialog.get_account_info()
            if username and password:
                row = self.account_table.rowCount()
                self.account_table.insertRow(row)
                self.account_table.setItem(row, 0, QTableWidgetItem(username))
                self.account_table.setItem(row, 1, QTableWidgetItem(password))
                self.account_table.setItem(row, 2, QTableWidgetItem("空闲"))
    
    def edit_account(self):
        """编辑账号"""
        current_row = self.account_table.currentRow()
        if current_row >= 0:
            username = self.account_table.item(current_row, 0).text()
            password = self.account_table.item(current_row, 1).text()
            
            dialog = AccountDialog(self, username, password)
            if dialog.exec_() == QDialog.Accepted:
                new_username, new_password = dialog.get_account_info()
                self.account_table.setItem(current_row, 0, QTableWidgetItem(new_username))
                self.account_table.setItem(current_row, 1, QTableWidgetItem(new_password))
    
    def delete_account(self):
        """删除账号"""
        current_row = self.account_table.currentRow()
        if current_row >= 0:
            self.account_table.removeRow(current_row)
    
    def refresh_accounts(self):
        """刷新账号状态"""
        try:
            pool_key = self.config.get("account_pool_key", "account_pool_v3")
            accounts = self.account_manager.get_all_accounts(pool_key)
            
            self.account_table.setRowCount(len(accounts))
            for i, account in enumerate(accounts):
                self.account_table.setItem(i, 0, QTableWidgetItem(account["username"]))
                self.account_table.setItem(i, 1, QTableWidgetItem(account["password"]))
                status = "占用" if account.get("in_use", False) else "空闲"
                self.account_table.setItem(i, 2, QTableWidgetItem(status))
                
        except Exception as e:
            QMessageBox.warning(self, "刷新失败", f"刷新账号状态失败: {str(e)}")
    
    def save_accounts_to_redis(self):
        """保存账号到Redis"""
        accounts = []
        for row in range(self.account_table.rowCount()):
            username = self.account_table.item(row, 0).text()
            password = self.account_table.item(row, 1).text()
            accounts.append({"username": username, "password": password, "in_use": False})
        
        try:
            pool_key = self.config.get("account_pool_key", "account_pool_v3")
            if self.account_manager.save_accounts(accounts, pool_key):
                QMessageBox.information(self, "保存成功", f"已保存 {len(accounts)} 个账号到Redis")
            else:
                QMessageBox.warning(self, "保存失败", "保存账号到Redis失败")
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存账号时出错: {str(e)}")
    

    def release_all_accounts(self):
        """一键释放所有占用中的账号"""
        try:
            pool_key = self.config.get("account_pool_key", "account_pool_v3")
            released = self.account_manager.release_all_accounts(pool_key)
            if released > 0:
                QMessageBox.information(self, "释放完成", f"已释放 {released} 个账号")
                self.log(f"已释放 {released} 个账号")
            else:
                QMessageBox.information(self, "释放完成", "当前没有正在使用的账号")
                self.log("没有找到正在使用的账号可释放")
            self.refresh_accounts()
        except Exception as e:
            QMessageBox.critical(self, "释放失败", f"释放账号时发生错误: {str(e)}")
            self.logger.error(f"释放账号失败: {str(e)}")
            self.log(f"释放账号失败: {str(e)}")

    def remove_duplicate_accounts(self):
        """删除Redis账号池中的重复账号"""
        try:
            pool_key = self.config.get("account_pool_key", "account_pool_v3")
            result = self.account_manager.remove_duplicate_accounts(pool_key)
            removed = result.get("removed", 0)
            available = result.get("available", 0)
            in_use = result.get("in_use", 0)
            QMessageBox.information(
                self,
                "去重完成",
                f"已清理重复账号 {removed} 个\n可用账号: {available}\n使用中账号: {in_use}",
            )
            self.log(f"清理重复账号 {removed} 个，可用 {available} 个，使用中 {in_use} 个")
            self.refresh_accounts()
        except Exception as e:
            QMessageBox.critical(self, "去重失败", f"删除重复账号时发生错误: {str(e)}")
            self.logger.error(f"删除重复账号失败: {str(e)}")
            self.log(f"删除重复账号失败: {str(e)}")

    def start_task(self):
        """开始任务"""
        # 验证配置
        if not self.validate_config():
            return
        
        # 创建并启动任务线程
        self.task_thread = TaskThread(self, self.config, self.account_manager, 
                                     self.window_controller, self.click_sequence, 
                                     self.process_monitor, self.runtime_logger)
        self.task_thread.log_signal.connect(self.log)
        self.task_thread.finished.connect(self.task_finished)
        self.task_thread.start()
        
        # 更新按钮状态
        self.start_task_btn.setEnabled(False)
        self.stop_task_btn.setEnabled(True)
        
        self.log("任务已启动")
    
    def stop_task(self):
        """停止任务"""
        if self.task_thread:
            self.task_thread.stop()
            self.task_thread.wait()
        
        # 更新按钮状态
        self.start_task_btn.setEnabled(True)
        self.stop_task_btn.setEnabled(False)
        
        self.log("任务已停止")
    
    def task_finished(self):
        """任务完成"""
        self.start_task_btn.setEnabled(True)
        self.stop_task_btn.setEnabled(False)
        self.log("任务已结束")
    
    def validate_config(self):
        """验证配置"""
        if not self.config.get("software_a_path") or not os.path.exists(self.config["software_a_path"]):
            QMessageBox.warning(self, "配置错误", "请配置正确的软件A路径")
            return False
        
        if not self.config.get("software_b_name"):
            QMessageBox.warning(self, "配置错误", "请配置软件B进程名")
            return False
        
        if len(self.config.get("coordinates", [])) != 5:
            QMessageBox.warning(self, "配置错误", "请记录5个坐标点")
            return False
        
        # 测试Redis连接
        if not self.account_manager.test_connection():
            QMessageBox.warning(self, "连接错误", "无法连接到Redis服务器")
            return False
        
        return True
    
    def log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()
        self.logger.info(message)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.task_thread and self.task_thread.isRunning():
            reply = QMessageBox.question(self, "确认退出", "任务正在运行，确定要退出吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.task_thread.stop()
                self.task_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def restart_coordinate_recording(self):
        """重新开始坐标记录"""
        self.config["coordinates"] = []
        self.save_config()
        self.update_coordinate_display()
        self.coordinate_recorder.restart_recording()
        self.log("🔄 重新开始坐标记录，请按Ctrl+3开始记录5个坐标")
    


class AccountDialog(QDialog):
    """账号编辑对话框"""
    
    def __init__(self, parent=None, username="", password=""):
        super().__init__(parent)
        self.setWindowTitle("账号编辑")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.username_edit = QLineEdit(username)
        layout.addRow("用户名:", self.username_edit)
        
        self.password_edit = QLineEdit(password)
        layout.addRow("密码:", self.password_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
    
    def get_account_info(self):
        """获取账号信息"""
        return (self.username_edit.text(), self.password_edit.text())


class TaskThread(QThread):
    """后台任务线程"""
    log_signal = pyqtSignal(str)
    
    def __init__(self, parent, config, account_manager, window_controller, click_sequence, process_monitor, runtime_logger):
        super().__init__(parent)
        self.config = config
        self.account_manager = account_manager
        self.window_controller = window_controller
        self.click_sequence = click_sequence
        self.process_monitor = process_monitor
        self.runtime_logger = runtime_logger
        self.running = True
        self.logger = logging.getLogger("TaskThread")
    
    def run(self):
        """执行新的任务循环"""
        while self.running:
            try:
                # 1. 获取账号
                pool_key = self.config.get("account_pool_key", "account_pool_v3")
                self.log_signal.emit(f"正在从Redis获取账号...")
                account = self.account_manager.acquire_account(pool_key)
                
                if not account:
                    self.log_signal.emit("无可用账号，等待30秒后重试...")
                    time.sleep(30)
                    continue
                
                self.log_signal.emit(f"获取到第1个账号: {account['username']}")
                
                # 2. 启动软件A
                self.log_signal.emit(f"正在启动软件A...")
                software_a_pid = self.window_controller.start_process(self.config["software_a_path"])
                
                # 【修改】等待窗口出现时间：3秒改为5秒
                self.log_signal.emit("等待5秒让软件A窗口出现...")
                time.sleep(5)
                
                if not self.window_controller.center_window(software_a_pid):
                    self.log_signal.emit("无法找到软件A窗口，释放账号并重试...")
                    self.account_manager.release_account(account, pool_key)
                    self.window_controller.terminate_process(software_a_pid)
                    continue
                
                # 3. 获取窗口句柄并设置坐标
                software_a_hwnd = self.window_controller.find_window_by_pid(software_a_pid)
                if software_a_hwnd:
                    self.click_sequence.set_target_window(software_a_hwnd)
                    self.click_sequence.set_coordinates(self.config["coordinates"])
                    self.click_sequence.set_click_interval(self.config.get("click_interval", 2.0))
                
                # 4. 执行首次点击序列（每个账号只尝试1次，失败后无限轮换账号）
                b_started = False
                account_switch_count = 0  # 账号切换计数器
                
                while not b_started and self.running:  # 无限轮换账号
                    retry_count = 0
                    
                    while retry_count < 1 and not b_started and self.running:
                        self.log_signal.emit(f"执行首次点击序列 (尝试 {retry_count+1}/1)...")
                        
                        try:
                            self.click_sequence.execute(account["username"], account["password"])
                        except Exception as e:
                            self.log_signal.emit(f"点击执行失败: {str(e)}")
                            break
                        
                        # 等待20秒检查软件B状态
                        self.log_signal.emit("等待50秒检查软件B状态...")
                        time.sleep(50)
                        
                        b_started = self.process_monitor.is_process_running()
                        if b_started:
                            self.log_signal.emit("软件B已成功启动")

                            # 🕐 记录软件B开始运行时间
                            self.runtime_logger.record_start()
                            time.sleep(20)
                            self.log_signal.emit("等待20再释放账号...")
                        else:
                            self.log_signal.emit("软件B未启动，准备切换账号...")
                            retry_count += 1
                    
                    # 如果1次尝试都失败，释放当前账号，重新开始流程
                    if not b_started and retry_count >= 1:
                        self.account_manager.release_account(account, pool_key)
                        account_switch_count += 1
                        self.log_signal.emit(f"🔄 当前账号1次尝试失败，释放账号并切换到第{account_switch_count + 1}个账号...")
                        
                        # 关闭当前软件A
                        self.log_signal.emit("🚪 关闭当前软件A，准备重新开始...")
                        self.window_controller.terminate_process(software_a_pid)
                        
                        # 等待进程完全关闭
                        self.log_signal.emit("⏳ 等待3秒确保进程完全关闭...")
                        time.sleep(3)
                        
                        # 获取新账号
                        account = self.account_manager.acquire_account(pool_key)
                        if not account:
                            self.log_signal.emit("无可用账号，等待30秒后重试...")
                            time.sleep(30)
                            continue
                        
                        self.log_signal.emit(f"✅ 获取到第{account_switch_count + 1}个账号: {account['username']}")
                        
                        # 重新启动软件A
                        self.log_signal.emit("🚀 重新启动软件A...")
                        software_a_pid = self.window_controller.start_process(self.config["software_a_path"])
                        
                        # 等待窗口出现
                        self.log_signal.emit("⏳ 等待5秒让软件A窗口出现...")
                        time.sleep(5)
                        
                        # 窗口居中
                        if not self.window_controller.center_window(software_a_pid):
                            self.log_signal.emit("❌ 软件A窗口居中失败，释放账号并继续...")
                            self.account_manager.release_account(account, pool_key)
                            continue
                        
                        # 重新获取窗口句柄并设置坐标
                        software_a_hwnd = self.window_controller.find_window_by_pid(software_a_pid)
                        if software_a_hwnd:
                            self.click_sequence.set_target_window(software_a_hwnd)
                            self.click_sequence.set_coordinates(self.config["coordinates"])
                            self.click_sequence.set_click_interval(self.config.get("click_interval", 2.0))
                

                
                # 5. 处理结果
                if b_started:
                    # 释放当前账号
                    self.log_signal.emit("🔓 释放当前账号...")
                    self.account_manager.release_account(account, pool_key)
                    
                    # 【修正】无论首次还是后续，软件B启动后都关闭重启软件A
                    self.log_signal.emit("🚪 软件B已启动，关闭当前软件A...")
                    self.window_controller.terminate_process(software_a_pid)
                    
                    # 等待进程完全关闭
                    self.log_signal.emit("⏳ 等待3秒确保进程完全关闭...")
                    time.sleep(3)
                    
                    # 重新启动软件A
                    self.log_signal.emit("🚀 重新启动软件A...")
                    new_software_a_pid = self.window_controller.start_process(
                        self.config["software_a_path"]
                    )
                    
                    # 等待窗口出现
                    self.log_signal.emit("⏳ 等待5秒让新软件A窗口出现...")
                    time.sleep(5)
                    
                    # 窗口居中
                    if self.window_controller.center_window(new_software_a_pid):
                        # 更新进程ID和窗口句柄
                        software_a_pid = new_software_a_pid
                        software_a_hwnd = self.window_controller.find_window_by_pid(new_software_a_pid)
                        self.log_signal.emit("💤 软件A已重新启动，进入待机监控模式")
                        
                        # 进入待机监控循环
                        self.standby_monitoring_loop(software_a_pid, software_a_hwnd, pool_key)
                        
                        # 待机循环结束，说明需要完全重启
                        self.log_signal.emit("待机监控结束，准备重新启动完整流程...")
                    else:
                        self.log_signal.emit("❌ 软件A重启后窗口居中失败，重新开始流程")
                else:
                    # 首次启动失败，释放账号并重新开始
                    self.log_signal.emit("软件B首次启动失败，释放账号并重新开始...")
                    self.account_manager.release_account(account, pool_key)
                    self.window_controller.terminate_process(software_a_pid)
                    
            except Exception as e:
                self.log_signal.emit(f"任务执行出错: {str(e)}")
                time.sleep(10)
    
    def standby_monitoring_loop(self, software_a_pid, software_a_hwnd, pool_key):
        """软件A待机 + 软件B监控循环"""
        self.log_signal.emit("🔄 开始待机监控循环...")
        check_count = 0  # 检测计数器
        
        while self.running:
            try:
                check_count += 1
                
                # 检查软件B运行状态 (每1分钟)
                if check_count <= 5:
                    # 前5次显示详细日志
                    self.log_signal.emit(f"👁️ 第{check_count}次检查软件B运行状态...")
                elif check_count == 6:
                    # 第6次时显示持续监控提示
                    self.log_signal.emit("🔄 持续监控中...")
                # 超过5次后不再打印检测日志
                
                b_running = self.process_monitor.is_process_running()
                
                if b_running:
                    if check_count <= 5:
                        self.log_signal.emit("✅ 软件B正在运行，软件A继续待机...")
                    # 超过5次后不打印此日志
                    time.sleep(60)  # 等待1分钟后再次检查
                    continue
                else:
                    self.log_signal.emit("🔴 软件B已结束，准备获取账号并执行点击...")
                    
                    # 🕐 记录软件B结束运行时间
                    self.runtime_logger.record_end()
                    
                    # 软件B结束，尝试获取新账号
                    account = self.account_manager.acquire_account(pool_key)
                    
                    if not account:
                        self.log_signal.emit("无可用账号，等待5秒后重试...")
                        time.sleep(5)
                        continue
                    
                    self.log_signal.emit(f"✅ 获取到账号: {account['username']}")
                    
                    # 【新增】激活并居中现有软件A窗口
                    self.log_signal.emit("🎯 激活并居中软件A窗口...")
                    if software_a_hwnd:
                        self.click_sequence.set_target_window(software_a_hwnd)
                        self.click_sequence.ensure_window_foreground()
                        
                        # 重新居中窗口
                        if not self.window_controller.center_window_by_hwnd(software_a_hwnd):
                            self.log_signal.emit("⚠️ 窗口居中失败，但继续执行...")
                        
                        # 等待窗口稳定
                        time.sleep(0.5)
                    
                    # 执行点击序列
                    try:
                        self.log_signal.emit("⚡ 执行点击序列...")
                        self.click_sequence.execute(account["username"], account["password"])
                        
                        # 等待20秒检查软件B是否重新启动
                        self.log_signal.emit("⏱️ 等待50秒检查软件B是否重新启动...")
                        time.sleep(50)
                        
                        b_restarted = self.process_monitor.is_process_running()
                        
                        if b_restarted:
                            self.log_signal.emit("✅ 软件B已重新启动")
                            
                            # 🕐 记录软件B重新开始运行时间
                            self.runtime_logger.record_start()
                            
                            # 释放账号
                            self.account_manager.release_account(account, pool_key)
                            
                            # 【修改】关闭当前软件A并重新启动
                            self.log_signal.emit("🚪 关闭当前软件A...")
                            self.window_controller.terminate_process(software_a_pid)
                            
                            # 【修改】等待进程完全关闭：1秒改为3秒
                            self.log_signal.emit("⏳ 等待3秒确保进程完全关闭...")
                            time.sleep(3)
                            
                            # 重新启动软件A
                            self.log_signal.emit("🚀 重新启动软件A...")
                            new_software_a_pid = self.window_controller.start_process(
                                self.config["software_a_path"]
                            )
                            
                            # 【修改】等待窗口出现：3秒改为5秒
                            self.log_signal.emit("⏳ 等待5秒让新软件A窗口出现...")
                            time.sleep(5)
                            
                            # 窗口居中
                            if self.window_controller.center_window(new_software_a_pid):
                                # 更新进程ID和窗口句柄
                                software_a_pid = new_software_a_pid
                                software_a_hwnd = self.window_controller.find_window_by_pid(new_software_a_pid)
                                self.log_signal.emit("💤 软件A已重新启动，回到待机状态")
                                # 重置检测计数器，重新开始计数
                                check_count = 0
                                continue  # 继续待机循环
                            else:
                                self.log_signal.emit("❌ 软件A重启后窗口居中失败，退出待机模式")
                                return  # 退出待机循环，回到主循环
                        else:
                            self.log_signal.emit("❌ 软件B未能重新启动，任务完成")
                            # 释放账号并关闭软件A
                            self.account_manager.release_account(account, pool_key)
                            self.window_controller.terminate_process(software_a_pid)
                            return  # 退出待机循环，回到主循环
                            
                    except Exception as e:
                        self.log_signal.emit(f"❌ 点击执行失败: {str(e)}")
                        self.account_manager.release_account(account, pool_key)
                        continue
                        
            except Exception as e:
                self.log_signal.emit(f"待机监控出错: {str(e)}")
                time.sleep(10)
    
    def stop(self):
        """停止任务线程"""
        # 如果软件B正在运行且正在记录时间，记录为中断退出
        if self.runtime_logger.is_running():
            self.runtime_logger.record_crash_or_interrupt("用户手动停止任务")
        
        self.running = False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 


from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QTextEdit,
    QProgressBar, QMessageBox, QDoubleSpinBox,
    QFrame, QApplication, QLineEdit  # 添加 QApplication
)
import configparser
import hashlib
import re
import sys
import os
import subprocess
import requests
import json
from datetime import datetime, timedelta
import pytz  # 确保安装 pytz 库
import random
import string

# 常量定义
API_URL = "http://api.1wxyun.com/?type=17"  #卡密登录api
API_GG="http://api.1wxyun.com/?type=1" #公告api
API_GMLJ="http://api.1wxyun.com/?type=5" #购卡链接api
API_XZ="http://api.1wxyun.com/?type=5" #下载地址api
API_JB="http://api.1wxyun.com/?type=14" #解绑api
API_SY="http://api.1wxyun.com/?type=16" #试用api
API_DQ="http://api2.1wxyun.com/?type=24" #到期时间api

key = ""             #软件标识
VERSION = "1.0"                         #版本号

# 读取字符串
# 错误处理函数
def handle_error(msg):
    QMessageBox.critical(None, "错误", msg)

# 获取机器码（CPU序列号）
def get_machine_code():
    try:
        output = subprocess.check_output("wmic cpu get ProcessorId", shell=True, universal_newlines=True)
        processor_id = output.strip()
        return processor_id
    except Exception as e:
        handle_error(f"获取机器码失败: {str(e)}")

# 对机器码进行加密处理
def encrypt_machine_code(machine_code):
    hash_object = hashlib.sha256(machine_code.encode())
    hash_hex = hash_object.hexdigest()
    return hash_hex[:32]

def gonggao():  # 获取软件公告内容
    post_data = {'Softid': key}
    response = requests.post(API_GG, data=post_data)
    if response.status_code == 200:
        return response.text
    else:
        handle_error(f"请求失败，状态码：{response.status_code}")

# 登录方法
def login(card, encrypted_machine_code):
    post_data = {
        "Softid": key,
        "Card": card,
        "Version": VERSION,
        "Mac": encrypted_machine_code
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(API_URL, data=post_data, headers=headers, timeout=10)
        response.raise_for_status()
        if re.match("^[A-Za-z0-9]+$", response.text):
            return response.text  # 返回Token
        else:
            return None  # 返回None表示卡密不正确
    except requests.RequestException as e:
        handle_error(f"API请求失败: {str(e)}")
        return None  # 确保返回None

def save_card_to_config(card):
    """将卡密保存到配置文件中"""
    config = configparser.ConfigParser()
    config['configuration'] = {'Carmine': card}
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def load_card_from_config():
    """从配置文件中加载卡密"""
    config = configparser.ConfigParser()
    if os.path.exists('config.ini'):
        config.read('config.ini')
        if 'configuration' in config and 'Carmine' in config['configuration']:
            return config['configuration']['Carmine']
    return None

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网络验证：卡密登录+解绑+试用功能")
        self.setGeometry(100, 100, 400, 300)
        self.machine_code_file = os.path.join(os.getcwd(), 'machine_code.json')


        # 初始化 token
        self.token = None  # 确保在这里初始化 token

        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 显示公告
        self.announcement_label = QLabel("软件公告内容:")
        layout.addWidget(self.announcement_label)

        # 输入卡密
        self.card_input = QLineEdit()
        self.card_input.setPlaceholderText("请输入卡密")
        layout.addWidget(self.card_input)

        # 加载配置文件中的卡密
        saved_card = load_card_from_config()
        if saved_card:
            self.card_input.setText(saved_card)  # 填入卡密

        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.perform_login)
        layout.addWidget(self.login_button)

        # 解绑按钮
        self.unbind_button = QPushButton("解绑")
        self.unbind_button.clicked.connect(self.perform_unbind)
        layout.addWidget(self.unbind_button)

        # 试用按钮
        self.trial_button = QPushButton("试用")
        self.trial_button.clicked.connect(self.perform_trial)  # 连接到 perform_trial 方法
        layout.addWidget(self.trial_button)

        # 显示公告内容
        self.show_announcement()
    #软件公告
    def show_announcement(self):
        announcement = gonggao()
        self.announcement_label.setText(f"软件公告内容:\n{announcement}")

    def perform_login(self):
        """处理登录逻辑"""
        card_input = self.card_input.text().strip()
        if not card_input:
            handle_error("请输入卡密！")
            return

        machine_code = get_machine_code()
        encrypted_machine_code = encrypt_machine_code(machine_code)  # 加密机器码

        # 进行登录请求
        token = login(card_input, encrypted_machine_code)
        if not token:
            handle_error("卡密不正确，请检查后重试。")  # 显示卡密不正确的错误消息
            return

        # 登录成功后，检查卡密是否到期
        post_data = {
            "Softid": key,        # 软件标识
            "UserName": card_input,  # 使用卡密作为用户名
        }

        try:
            response = requests.post(API_DQ, data=post_data)
            response.raise_for_status()  # 检查请求是否成功
            expiry_status = response.text.strip()  # 获取返回的状态

            if expiry_status == "-83006":
                handle_error("单码卡密已过期，请重新购买！")
                return
            else:
                # 假设返回的内容是到期时间，格式为 "YYYY-MM-DD HH:MM:SS"
                expiry_time = datetime.strptime(expiry_status, "%Y-%m-%d %H:%M:%S")
                message = f"登录成功！您的临时Token是：{token}\n您的卡密到期时间为: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}"
                QMessageBox.information(self, "登录成功", message)
                save_card_to_config(card_input)  # 保存卡密到配置文件
                self.open_main_window()  # 登录成功后打开主窗口
                return True
        except requests.RequestException as e:
            handle_error(f"到期时间验证失败: {str(e)}")


    #解绑功能
    def perform_unbind(self):
        """处理解绑逻辑"""
        card_input = self.card_input.text().strip()
        if not card_input:
            handle_error("请输入卡密以进行解绑！")
            return

        machine_code = get_machine_code()  # 获取机器码
        encrypted_machine_code = encrypt_machine_code(machine_code)  # 加密机器码

        # 发送解绑请求
        post_data = {
            "Softid": key,          # 软件标识
            "UserName": card_input, # 使用卡密作为用户名
            "Type": 1,              # 类型，假设为 1位机器码，2为IP
            "Mac": encrypted_machine_code  # 加密后的机器码
        }

        try:
            response = requests.post(API_JB, data=post_data)
            response.raise_for_status()  # 检查请求是否成功
            QMessageBox.information(self, "解绑成功", "卡密已成功解绑。")
        except requests.RequestException as e:
            handle_error(f"解绑失败: {str(e)}")
    
    #试用功能        
    def get_machine_code(self):
        """获取机器码，并确保长度在6-16位"""
        try:
            output = subprocess.check_output("wmic cpu get ProcessorId", shell=True, universal_newlines=True)
            processor_id = output.strip()
            
            # 使用哈希处理，确保长度在6-16位
            hash_object = hashlib.md5(processor_id.encode())
            machine_code = hash_object.hexdigest()[:12]  # 取12位
            
            return machine_code
        except Exception as e:
            handle_error(f"获取机器码失败: {str(e)}")
            return None

    def perform_trial(self):
        """处理试用功能"""
        try:
            # 获取机器码
            machine_code = self.get_machine_code()
            if not machine_code:
                handle_error("获取机器码失败")
                return None

            # 构建POST数据
            post_data = {
                "Softid": key,        # 软件标识
                "Userid": machine_code,  # 使用机器码作为 Userid
                "Version": VERSION    # 版本号
            }

            # 发送试用请求
            response = requests.post(API_SY, data=post_data)
            response.raise_for_status()
            
            # 打印调试信息
            print(f"试用 API 返回: {response.text}")
            
            # 处理 API 返回
            if response.text == "-85005":
                # 试用已到期
                handle_error("试用已过期，请购买正式版。")
                return False
            
            # 检查是否是16位的字母或数字组合
            if re.match(r'^[a-zA-Z0-9]{16}$', response.text):
                # 试用成功
                QMessageBox.information(None, "试用成功", f"试用成功！您的试用码是：{response.text}")
                
                # 保存机器码信息（可选）
                self.save_machine_code_and_userid(machine_code)
                
                # 打开主窗口
                self.open_main_window()  # 登录成功后打开主窗口
                return True
            
            # 其他未知返回
            handle_error(f"试用失败，返回码：{response.text}")
            return False
        
        except requests.RequestException as e:
            handle_error(f"试用状态验证失败: {str(e)}")
            return None

    def save_machine_code_and_userid(self, machine_code):
        """保存机器码和用户ID到配置文件"""
        try:
            config = configparser.ConfigParser()
            
            # 如果配置文件存在，先读取
            if os.path.exists('config.ini'):
                config.read('config.ini')
            
            # 确保有 Trial 分区
            if 'Trial' not in config:
                config['Trial'] = {}
            
            # 保存机器码和用户ID
            config['Trial']['MachineCode'] = machine_code
            config['Trial']['UserId'] = machine_code
            
            # 写入配置文件
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            
            return True
        
        except Exception as e:
            handle_error(f"保存机器码信息失败: {str(e)}")
            return False

    def open_main_window(self):
# 创建主窗口,将主程序写入此处



if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_window = LoginWindow()#替换或者增加 你自己的主程序窗口即可
    login_window.show()
    sys.exit(app.exec())

    

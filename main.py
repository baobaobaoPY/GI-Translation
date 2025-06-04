"""
多语言对照表：
Mondstadt  // 蒙德
Liyue      // 璃月
Inazuma    // 稻妻
Sumeru     // 须弥
Fontaine   // 枫丹
Natlan     // 纳塔
Other      // 其他

몬드     // 蒙德
리월     // 璃月
이나즈마  // 稻妻
수메르    // 须弥
폰타인    // 枫丹
나타     // 纳塔
기타     // 其他

モンド       // 蒙德
璃月        // 璃月
稲妻        // 稻妻
スメール     // 须弥
フォンテーヌ  // 枫丹
ナタ        // 纳塔
その他       // 其他
"""


import sys
import os
import re
import json
import platform
from PySide6.QtGui import QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import QTimer, QPropertyAnimation


# Windows互斥锁相关导入
if platform.system() == 'Windows':
    import ctypes
    from ctypes import wintypes

    # Windows API函数声明
    kernel32 = ctypes.windll.kernel32

    # 定义常量
    ERROR_ALREADY_EXISTS = 183

    # 函数原型
    CreateMutexW = kernel32.CreateMutexW
    CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    CreateMutexW.restype = wintypes.HANDLE

    GetLastError = kernel32.GetLastError
    GetLastError.restype = wintypes.DWORD

    CloseHandle = kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL


class SingleInstanceChecker:
    """Windows单实例检查器"""
    def __init__(self, mutex_name):
        self.mutex_name = mutex_name
        self.mutex_handle = None

    def is_already_running(self):
        """检查是否已有实例在运行"""
        if platform.system() != 'Windows':
            # 非Windows系统，暂不实现互斥锁
            return False

        try:
            # 创建命名互斥锁
            self.mutex_handle = CreateMutexW(None, True, self.mutex_name)

            if self.mutex_handle:
                # 检查是否因为互斥锁已存在而失败
                last_error = GetLastError()
                if last_error == ERROR_ALREADY_EXISTS:
                    # 互斥锁已存在，说明有其他实例在运行
                    CloseHandle(self.mutex_handle)
                    self.mutex_handle = None
                    return True
                else:
                    # 成功创建互斥锁，当前是第一个实例
                    return False
            else:
                # 创建互斥锁失败
                return False

        except Exception as e:
            print(f"互斥锁检查异常: {e}")
            return False

    def release(self):
        """释放互斥锁"""
        if self.mutex_handle and platform.system() == 'Windows':
            try:
                CloseHandle(self.mutex_handle)
                self.mutex_handle = None
            except Exception as e:
                print(f"释放互斥锁异常: {e}")


class TranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_main_data()
        self.load_sk_main_data()  # 加载SK主数据
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_input)
        self.timer.start(100)  # 每100ms检查输入
        self.last_input = ''
        self.country_data_cache = {}  # One国家数据缓存
        self.sk_country_data_cache = {}  # SK国家数据缓存
        self.setFixedSize(self.size())  # 锁定窗口大小

        # 设置窗口图标（如果文件存在）
        if os.path.exists('Database/hk4e_cn.ico'):
            self.setWindowIcon(QIcon('Database/hk4e_cn.ico'))

        # 初始化动画效果
        self._init_animation()

    def _init_animation(self):
        """初始化动画效果"""
        # 淡入动画
        self.fade_in_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_anim.setDuration(66)
        self.fade_in_anim.setStartValue(0)
        self.fade_in_anim.setEndValue(1)

        # 淡出动画
        self.fade_out_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_anim.setDuration(66)
        self.fade_out_anim.setStartValue(1)
        self.fade_out_anim.setEndValue(0)
        self.fade_out_anim.finished.connect(self._on_fade_out_finished)

        # 关闭标志
        self.is_closing = False

    def initUI(self):
        # 创建界面元素
        layout = QVBoxLayout()

        # 输入框设置
        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("输入需翻译的角色中文名称：")
        self.input_line.setStyleSheet('''
                    QLineEdit {
                        background: #f8f9fa;
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        padding: 6px 12px;
                    }
                ''')

        # 只读输出, 提供可进行复制内容的输入框
        output_layout_1 = QHBoxLayout()
        self.output_edit_1 = QLineEdit(self)
        self.output_edit_1.setReadOnly(True)
        self.output_edit_1.setPlaceholderText("中->英")
        self.output_edit_1.setStyleSheet('''
                    QLineEdit {
                        background: #f8f9fa;
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        padding: 3px 12px;
                    }
                ''')
        # 按钮设置
        self.copy_button_1 = QPushButton("📋复制📋", self)
        self.copy_button_1.setFixedWidth(100)
        self.copy_button_1.setStyleSheet('''
                    QPushButton {
                        padding: 4px 5px;
                    }
                ''')

        output_layout_1.addWidget(self.output_edit_1, 1)
        output_layout_1.addWidget(self.copy_button_1, 0)

        output_layout_2 = QHBoxLayout()
        # 只读输出, 提供可进行复制内容的输入框
        self.output_edit_2 = QLineEdit(self)
        self.output_edit_2.setReadOnly(True)
        self.output_edit_2.setPlaceholderText("中->韩")
        self.output_edit_2.setStyleSheet('''
                    QLineEdit {
                        background: #f8f9fa;
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        padding: 3px 12px;
                    }
                ''')
        # 按钮设置
        self.copy_button_2 = QPushButton("📋复制📋", self)
        self.copy_button_2.setFixedWidth(100)
        self.copy_button_2.setStyleSheet('''
            QPushButton {
                padding: 4px 5px;
            }
        ''')

        output_layout_2.addWidget(self.output_edit_2, 1)
        output_layout_2.addWidget(self.copy_button_2, 0)

        # 布局设置
        layout.addWidget(self.input_line)
        layout.addLayout(output_layout_1)
        layout.addLayout(output_layout_2)
        self.setLayout(layout)

        # 事件绑定
        self.copy_button_1.clicked.connect(lambda: self.copy_to_clipboard(1))
        self.copy_button_2.clicked.connect(lambda: self.copy_to_clipboard(2))

        # 窗口设置
        self.setWindowTitle('V1.0')
        self.resize(360, 140)

    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        self.fade_in_anim.start()  # 窗口显示时执行淡入动画
        self.activateWindow()  # 激活窗口
        self.setFocus()  # 设置焦点

    def closeEvent(self, event):
        """窗口关闭事件"""
        if not self.is_closing:
            # 首次关闭请求，开始淡出动画
            self.is_closing = True
            self.fade_out_anim.start()
            event.ignore()  # 忽略关闭事件，等待动画完成
        else:
            # 动画完成后的真正关闭
            # 释放互斥锁
            if hasattr(self, 'instance_checker'):
                self.instance_checker.release()
            event.accept()

    def _on_fade_out_finished(self):
        """淡出动画完成事件"""
        # 动画完成后真正关闭窗口
        super().close()

    def copy_to_clipboard(self, button_id):
        """复制翻译结果到剪贴板"""
        if button_id == 1:
            text = self.output_edit_1.text()
            button = self.copy_button_1
        else:
            text = self.output_edit_2.text()
            button = self.copy_button_2

        if text:
            QApplication.clipboard().setText(text)
            # 显示复制成功提示（220ms）
            button.setText("✅")
            QTimer.singleShot(220, lambda: button.setText("📋复制📋"))

    def load_main_data(self):
        """加载主数据文件并建立名称映射"""
        try:
            with open('Database/CsOne_main.json', 'r', encoding='utf-8') as f:
                main_data = json.load(f)

            # 建立名称到Country/HID的映射
            self.name_to_info = {}
            for name, info in main_data.items():
                self.name_to_info[name] = {
                    'Country': info['Country'],
                    'HID': info['HID']
                }

                # 处理别名
                exegesis = info.get('exegesis', '')
                # 使用正则进行匹配
                aliases = re.findall('\\{([^}]+)}', exegesis)
                for alias in aliases:
                    self.name_to_info[alias] = {
                        'Country': info['Country'],
                        'HID': info['HID']
                    }
        except Exception as e:
            if hasattr(self, 'output_edit_1'):
                self.output_edit_1.setText(f'加载One主数据时异常：{str(e)}')

    def load_sk_main_data(self):
        """加载主数据文件并建立名称映射"""
        try:
            with open('Database/CsSK_main.json', 'r', encoding='utf-8') as f:
                sk_main_data = json.load(f)

            # 建立名称到Country/HID的映射
            self.sk_name_to_info = {}
            for name, info in sk_main_data.items():
                self.sk_name_to_info[name] = {
                    'Country': info['Country'],
                    'HID': info['HID']
                }

                # 处理别名
                exegesis = info.get('exegesis', '')
                # 使用正则进行匹配
                aliases = re.findall('\\{([^}]+)}', exegesis)
                for alias in aliases:
                    self.sk_name_to_info[alias] = {
                        'Country': info['Country'],
                        'HID': info['HID']
                    }
        except Exception as e:
            if hasattr(self, 'output_edit_2'):
                self.output_edit_2.setText(f'加载SK主数据时异常：{str(e)}')

    def check_input(self):
        """定时检查输入变化"""
        current_text = self.input_line.text()
        if current_text != self.last_input:
            self.last_input = current_text
            self.translate(current_text)

    def translate(self, text):
        """执行翻译逻辑"""
        if not text:
            self.output_edit_1.setText('')
            self.output_edit_2.setText('')
            return

        # (中->英翻译)
        if text in self.name_to_info:
            info = self.name_to_info[text]
            country = info['Country']
            hid = info['HID']

            # 获取国家数据
            country_data = self.get_country_data(country)
            if country_data:
                entry = country_data.get(hid, {})
                translated_name = entry.get('name', 'Unknown')
                self.output_edit_1.setText(translated_name)
            else:
                self.output_edit_1.setText('未找到翻译数据信息')
        else:
            self.output_edit_1.setText("无此翻译结果")

        # (中->韩翻译)
        if text in self.sk_name_to_info:
            info = self.sk_name_to_info[text]
            country = info['Country']
            hid = info['HID']

            # 获取SK中的国家数据
            sk_country_data = self.get_sk_country_data(country)
            if sk_country_data:
                entry = sk_country_data.get(hid, {})
                translated_name = entry.get('name', 'Unknown')
                self.output_edit_2.setText(translated_name)
            else:
                self.output_edit_2.setText('未找到翻译数据信息')
        else:
            self.output_edit_2.setText("无此翻译结果")

    def get_country_data(self, country):
        """获取国家数据(进行缓存)"""
        if country in self.country_data_cache:
            return self.country_data_cache[country]

        file_path = f'Database/Cs{country}.json'
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.country_data_cache[country] = data
                return data
            return None
        except Exception as e:
            print(f"加载[{country}]数据时异常：{str(e)}")
            return None

    def get_sk_country_data(self, country):
        """获取SK国家数据（进行缓存）"""
        if country in self.sk_country_data_cache:
            return self.sk_country_data_cache[country]

        file_path = f'Database/Cs{country}.json'
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.sk_country_data_cache[country] = data
                return data
            return None
        except Exception as e:
            print(f"加载 \x1b[94mCs{country}.json\x1b[0m 数据时异常：\x1b[91m{str(e)}\x1b[0m")
            return None


def main():
    # 定义互斥锁名称(使用main.py唯一哈希值作为名称)
    mutex_name = "HasH:f779f715c97adc71b504df78a8bbfd9120d0da9eaf70c51521b3b7d963d95e1f"

    # 创建单实例检查器
    instance_checker = SingleInstanceChecker(mutex_name)

    # 检查是否已有实例在运行
    if instance_checker.is_already_running():
        app = QApplication(sys.argv)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("来自Windows的程序运行警告!")
        msg.setInformativeText("此程序已有窗口实例正在您的Windows中运行，您无法为此程序启动一个新的窗口实例！")
        msg.exec()
        return 1

    try:
        # 创建应用程序
        app = QApplication(sys.argv)

        # 创建翻译器窗口
        translator = TranslatorApp()

        # 将instance_checker传递给窗口，以便在关闭时释放
        translator.instance_checker = instance_checker

        # 显示窗口
        translator.show()

        # 运行应用程序
        result = app.exec()

        # 程序结束时释放互斥锁
        instance_checker.release()

        return result

    except Exception as e:
        print(f"程序运行异常: {e}")
        # 确保释放互斥锁
        instance_checker.release()
        return 1


if __name__ == '__main__':
    sys.exit(main())

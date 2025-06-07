import sys
import os
try:
    local_path = sys._MEIPASS
    ffpeg_path = os.path.join(local_path, r"ffmpeg\ffmpeg.exe")
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = ffpeg_path
except:
    pass
import cv2
try:
    # 设置 FFmpeg 路径（仅在某些 OpenCV 版本有效）
    cv2.set(cv2.CAP_PROP_FFMPEG_PATH, "C:\\ffmpeg\\bin\\ffmpeg.exe")
except:
    pass
import numpy as np
import subprocess
import math
import re
import shutil
import time
import tempfile
import threading
import json
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QTime, QObject
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QProgressBar, QMessageBox, QFileDialog, 
                            QGroupBox, QFormLayout, QLineEdit)
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QIntValidator, QIcon

import traceback
def handle_exception(exc_type, exc_value, exc_traceback):
    # 打印错误信息
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    # 暂停程序（等待用户输入）
    input("按 Enter 键退出...")
    sys.exit(1)

# 设置全局异常钩子
sys.excepthook = handle_exception




# 世界


# 工作区管理器
class Workspace:
    def __init__(self, root_path=None, xlog=lambda *args, **kwargs: None):
        if root_path is None:
            root_path = os.getcwd()
            print(f"警告！！！工作区未指定，可能损坏原有文件，使用默认路径: {root_path}\n")
        """初始化工作区，设置根目录和自定义日志"""
        self.root_path = os.path.abspath(root_path)
        if not os.path.exists(self.root_path):
            os.makedirs(self.root_path, exist_ok=True)
        os.chdir(self.root_path)
        self.current_path = self.root_path
        self.previous_path = self.root_path
        self.xlog = xlog or self._default_logger
        
        self.log(f"工作区已初始化: {self.root_path}", color=(0, 255, 0, 255), level=0)
    
    def log(self, content, color=(255, 255, 255, 255), level=0):
        """统一日志记录接口"""
        self.xlog(content=content, color=color, level=level)

    def _default_logger(self, content, color, level):
        """默认日志实现（当未提供Xlog时使用）"""
        level_names = {0: "信息", 1: "警告", 2: "严重警告", 3: "错误"}
        r, g, b, a = color
        # 创建ANSI颜色代码
        color_code = f"\033[38;2;{r};{g};{b}m"
        print(f"{color_code}[{level_names[level]}] {content}\033[0m")

    def is_valid_folder_name(self, name):
        """
        检查文件夹名称是否符合系统命名规则
        
        参数:
            name (str): 要检查的文件夹名称
            
        返回:
            bool: 如果名称有效返回True，否则返回False
        """
        # 检查空名称
        if not name or name.isspace():
            return False
        
        # 检查长度限制
        if len(name) > 255:
            return False
        
        # 检查非法字符（Windows和Unix/Linux/MacOS的常见非法字符）
        illegal_chars = r'[<>:"/\\|?*\x00-\x1F]'
        if re.search(illegal_chars, name):
            return False
        
        # 检查保留名称（Windows保留名称）
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        if name.upper() in reserved_names:
            return False
        
        # 检查开头或结尾的空格或点
        if name.startswith(' ') or name.endswith(' ') or \
           name.startswith('.') or name.endswith('.'):
            return False
        
        # 检查路径分隔符（防止路径注入）
        if os.path.sep in name or (os.path.altsep and os.path.altsep in name):
            return False
        
        return True

    def get_file_size(self, file_path=None):
        """
        获取文件大小并转换为最佳单位（B/KB/MB/GB/TB）
        
        参数:
            file_path (str): 文件路径（绝对路径或相对于当前工作目录的路径）
            
        返回:
            str: 带单位的文件大小字符串
        """
        if not file_path:
            file_path = self.current_path
            
        if os.path.isdir(file_path):
            return "文件夹"
            
        # 处理相对路径
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.current_path, file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return "文件不存在"
        
        size_bytes = os.path.getsize(file_path)
        if size_bytes == 0:
            return "0 B"
        
        # 计算最佳单位
        size_units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        unit_index = min(int(math.floor(math.log(size_bytes, 1024))), len(size_units) - 1)
        size_converted = size_bytes / (1024 ** unit_index)
        
        # 格式化输出
        if size_converted.is_integer():
            return f"{int(size_converted)} {size_units[unit_index]}"
        return f"{size_converted:.2f} {size_units[unit_index]}"
    
    def get_folder_size(self, folder_path=None, return_bytes=False):
        """
        获取文件夹大小（包括所有子文件夹和文件）
        
        参数:
            folder_path (str): 文件夹路径（绝对路径或相对于当前工作目录的路径）
            return_bytes (bool): 是否返回字节数而非格式化字符串
            
        返回:
            int | str: 如果return_bytes为True则返回字节数，否则返回带单位的字符串
        """
        if folder_path is None:
            folder_path = self.current_path
            
        # 处理相对路径
        if not os.path.isabs(folder_path):
            folder_path = os.path.join(self.current_path, folder_path)
        
        # 检查路径是否存在
        if not os.path.exists(folder_path):
            return "路径不存在" if not return_bytes else 0
        
        # 确保指定的是文件夹
        if not os.path.isdir(folder_path):
            return "指定路径不是文件夹" if not return_bytes else 0
        
        # 递归计算文件夹大小（返回字节数）
        total_size = self._calculate_folder_size(folder_path)
        
        # 如果需要返回字节数
        if return_bytes:
            return total_size
        
        # 转换为易读格式
        return self._format_size(total_size)

    def _calculate_folder_size(self, folder_path):
        """内部方法：递归计算文件夹大小（字节）"""
        total_size = 0
        for entry in os.scandir(folder_path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total_size += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total_size += self._calculate_folder_size(entry.path)
                elif entry.is_symlink():
                    self.log(f"跳过符号链接: {entry.path}", color=(255, 165, 0, 255), level=1)
            except (PermissionError, OSError) as e:
                self.log(f"无法访问: {entry.path} ({e})", color=(255, 0, 0, 255), level=2)
        return total_size

    def _format_size(self, size_bytes):
        """内部方法：将字节数格式化为易读字符串"""
        if size_bytes == 0:
            return "0 B"
        
        size_units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        unit_index = min(int(math.floor(math.log(size_bytes, 1024))), len(size_units) - 1)
        size_converted = size_bytes / (1024 ** unit_index)
        
        if size_converted.is_integer():
            return f"{int(size_converted)} {size_units[unit_index]}"
        return f"{size_converted:.2f} {size_units[unit_index]}"
    
    def get_current_path(self):
        """返回当前工作目录"""
        return self.current_path
    
    def is_safe_path(self, target_path):
        """检查目标路径是否在根目录内（防止越界）"""
        target_abs = os.path.abspath(target_path)
        return os.path.commonpath([self.root_path]) == os.path.commonpath([self.root_path, target_abs])
    
    def cd(self, path):
        """
        安全切换目录（自动创建不存在的目录）
        
        参数:
            path (str): 目标路径，支持相对路径和特殊符号:
                        "." - 当前目录
                        ".." - 上一级目录
                        "-" - 上一次访问的目录
                        其他 - 子目录（如不存在会自动创建）
        """
        # 特殊路径处理
        if path == ".":
            new_path = self.current_path
        elif path == "-":
            new_path = self.previous_path
        else:
            new_path = os.path.join(self.current_path, path)
        
        # 规范化路径
        new_abs_path = os.path.normpath(os.path.abspath(new_path))
        
        # 路径安全检查
        if not self.is_safe_path(new_abs_path):
            raise PermissionError(f"安全限制: 不能访问根目录之外的位置 [{new_abs_path}]")
        
        # 记录上一次路径（实现cd -功能）
        self.previous_path = self.current_path
        
        # 创建不存在的目录
        os.makedirs(new_abs_path, exist_ok=True)
        
        # 切换目录
        os.chdir(new_abs_path)
        self.current_path = new_abs_path
        self.log(f"当前目录: {self.current_path}")
        
        print(f"当前目录已切换到: {self.current_path}")
    
    def return_to_root(self):
        """一键返回根目录"""
        os.chdir(self.root_path)
        self.current_path = self.root_path
        self.previous_path = self.root_path
        self.log(f"已返回根目录: {self.current_path}")
        
        print(f"当前目录已回到根目录: {self.root_path}")
    
    def create_folder(self, folder_name, del_existing=False):
        """
        在当前目录创建新文件夹
        
        参数:
            folder_name (str): 要创建的文件夹名称
            del_existing (bool): 是否删除已存在的同名文件夹及其内容
        """
        # 验证文件夹名称
        if not self.is_valid_folder_name(folder_name):
            error_msg = f"无效的文件夹名称: {folder_name}"
            self.log(error_msg, color=(255, 0, 0, 255), level=3)
            raise ValueError(error_msg)
        
        # 构建完整路径并确保安全
        full_path = os.path.join(self.current_path, folder_name)
        if not self.is_safe_path(full_path):
            error_msg = f"安全限制: 不能在工作区外创建文件夹 [{full_path}]"
            self.log(error_msg, color=(255, 0, 0, 255), level=3)
            raise PermissionError(error_msg)
        
        try:
            # 处理已存在文件夹
            if os.path.exists(full_path):
                if del_existing:
                    # 安全删除整个文件夹及其内容
                    shutil.rmtree(full_path)
                    self.log(f"已删除现有文件夹: {folder_name}（包含所有内容）", 
                            color=(255, 165, 0, 255), level=1)
                    print(f"已删除现有文件夹: {folder_name}（包含所有内容）")
                else:
                    self.log(f"文件夹已存在: {folder_name}，跳过创建", 
                            color=(255, 255, 0, 255), level=1)
                    return
            
            # 创建文件夹
            os.mkdir(full_path)
            self.log(f"已创建文件夹: {folder_name}", 
                    color=(0, 255, 0, 255), level=0)
        
        except Exception as e:
            error_msg = f"创建文件夹失败: {folder_name}, 错误: {e}"
            self.log(error_msg, color=(255, 0, 0, 255), level=3)
            raise RuntimeError(error_msg) from e
    
    def create_file(self, file_name, content="", encoding='utf-8', overwrite=True):
        """
        在当前目录创建新文件
        
        参数:
            file_name (str): 要创建的文件名称
            content (str): 文件内容，默认为空
            encoding (str): 文件编码，默认为utf-8
            overwrite (bool): 是否覆盖已存在的文件
        """
        # 验证文件名
        if not self.is_valid_folder_name(os.path.splitext(file_name)[0]):
            error_msg = f"无效的文件名: {file_name}"
            self.log(error_msg, color=(255, 0, 0, 255), level=3)
            raise ValueError(error_msg)
        
        # 构建完整路径并确保安全
        full_path = os.path.join(self.current_path, file_name)
        if not self.is_safe_path(full_path):
            error_msg = f"安全限制: 不能在工作区外创建文件 [{full_path}]"
            self.log(error_msg, color=(255, 0, 0, 255), level=3)
            raise PermissionError(error_msg)
        
        try:
            # 检查文件是否存在
            if os.path.exists(full_path):
                if overwrite:
                    self.log(f"覆盖已存在的文件: {file_name}", 
                            color=(255, 165, 0, 255), level=1)
                else:
                    self.log(f"文件已存在: {file_name}，跳过创建", 
                            color=(255, 255, 0, 255), level=1)
                    return
            
            # 创建文件并写入内容
            with open(full_path, 'w', encoding=encoding) as f:
                f.write(content)
            file_size = self.get_file_size(full_path)
            self.log(f"已创建文件: {file_name} ({file_size})", 
                    color=(0, 255, 0, 255), level=0)
        except Exception as e:
            error_msg = f"创建文件失败: {file_name}, 错误: {e}"
            self.log(error_msg, color=(255, 0, 0, 255), level=3)
            raise RuntimeError(error_msg) from e
    
    def append_to_file(self, file_path, content, mode='a'):
        """
        向文件中添加内容
        
        参数:
            file_path (str): 文件路径
            content (str): 要写入的内容
            mode (str): 文件打开模式，默认为追加模式('a')
                    'w' - 覆盖写入
                    'a' - 追加写入
        """
        try:
            with open(file_path, mode, encoding='utf-8') as file:
                file.write(content)
            self.log(f"内容已成功写入文件: {file_path}")
        except IOError as e:
            self.log(f"写入文件时出错: {e}")
    
    def list_directory(self, details=True):
        """
        列出当前目录内容
        
        参数:
            details (bool): 是否显示详细信息（大小/类型）
        """
        print(f"\n目录内容: {self.current_path}")
        print(f"{'名称':<30}{'类型':<10}{'大小':>10}" if details else "文件夹和文件列表:")
        
        items = []
        # 添加父目录（除非在根目录）
        if self.current_path != self.root:
            items.append(("..", "文件夹", ""))
        
        # 添加当前目录内容
        for item in os.listdir(self.current_path):
            item_path = os.path.join(self.current_path, item)
            
            if os.path.isdir(item_path):
                item_type = "文件夹"
                size = ""
            else:
                item_type = "文件"
                size = self.get_file_size(item_path)
            
            items.append((item, item_type, size))
        
        # 排序：文件夹优先
        items.sort(key=lambda x: (not x[1].startswith("文件夹"), x[0].lower()))
        
        # 显示结果
        for name, item_type, size in items:
            if details:
                print(f"{name:<30}{item_type:<10}{size:>10}")
            else:
                print(name)
    
    def delete(self, name, recursive=True):
        """
        删除文件或文件夹（安全删除，仅在当前工作区内）
        
        参数:
            name (str): 要删除的文件或文件夹名称
            recursive (bool): 是否递归删除文件夹及其内容
        """
        target = os.path.join(self.current_path, name)
        
        # 安全检查
        if not self.is_safe_path(target):
            error_msg = f"安全限制: 不能删除工作区外的项目 [{target}]"
            self.log(error_msg, color=(255, 0, 0, 255), level=3)
            raise PermissionError(error_msg)
        
        if not os.path.exists(target):
            self.log(f"未找到: {name}", color=(255, 255, 0, 255), level=1)
            return
        
        try:
            if os.path.isdir(target):
                # 安全删除文件夹
                if recursive:
                    shutil.rmtree(target)
                    self.log(f"已递归删除文件夹: {name}（包含所有内容）", 
                            color=(220, 20, 60, 255), level=2)
                else:
                    if not os.listdir(target):
                        os.rmdir(target)
                        self.log(f"已删除空文件夹: {name}", 
                                color=(255, 165, 0, 255), level=1)
                    else:
                        warning = f"拒绝删除: 文件夹 '{name}' 不为空（使用recursive=True强制删除）"
                        self.log(warning, color=(255, 215, 0, 255), level=2)
            else:
                os.remove(target)
                self.log(f"已删除文件: {name}", 
                        color=(255, 165, 0, 255), level=1)
        except Exception as e:
            error_msg = f"删除失败: {name}, 错误: {e}"
            self.log(error_msg, color=(255, 0, 0, 255), level=3)
            raise

    def path_exists(self, name):
        """
        判断指定路径（文件或文件夹）是否存在
        
        参数:
            name (str): 目标路径（绝对路径或相对于当前目录的相对路径）
        
        返回:
            bool: 如果路径存在且在工作区内返回True，否则返回False
        """
        try:
            # 处理绝对路径
            if os.path.isabs(name):
                full_path = os.path.normpath(name)
            # 处理相对路径
            else:
                full_path = os.path.normpath(os.path.join(self.current_path, name))
            
            # 安全检查：目标路径必须在工作区根目录内
            if not self.is_safe_path(full_path):
                self.log(f"安全警告：尝试访问受限路径 {full_path}", 
                        color=(255, 165, 0, 255), level=2)
                return False
                
            return os.path.exists(full_path)
        except Exception as e:
            self.log(f"路径检查失败: {name}, 错误: {e}", 
                    color=(255, 0, 0, 255), level=3)
            return False
    
    def create_dir(self, dir_name):
        """在当前目录创建文件夹"""
        dir_path = os.path.join(self.current_path, dir_name)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def tree(self, directory=None, padding='', in_workspace = True, is_last=True, print_size=False):
        """
        以树状图形式打印目录结构
        
        参数:
            directory (str): 起始目录（默认为当前目录）
            padding (str): 内部递归使用的缩进格式
            is_last (bool): 是否当前层级的最后一项
            print_size (bool): 是否显示文件/文件夹大小
        """
        # 设置默认起始目录
        if directory is None:
            directory = self.current_path
        
        # 安全检查
        if in_workspace:
            if not self.is_safe_path(directory):
                self.log(f"安全限制: 试图访问工作区之外的路径 {directory}", 
                        color=(255, 0, 0, 255), level=3)
                return
        
        # 处理符号连接
        if os.path.islink(directory):
            target = os.readlink(directory)
            print(f"{padding}{'└── ' if is_last else '├── '}{os.path.basename(directory)} -> {target}")
            return
        
        # 打印当前目录名（带大小信息）
        base_name = os.path.basename(directory) or os.path.basename(self.root_path)
        prefix = padding + ('└── ' if is_last else '├── ')
        display_text = f"{prefix}{base_name}/"
        
        # 添加文件夹大小信息（如果启用了大小显示）
        if print_size and os.path.isdir(directory):
            display_text += f" [目录大小: {self.get_folder_size(directory)}]"
        
        print(display_text)
        
        # 准备新的缩进层级
        extension = '    ' if is_last else '│   '
        new_padding = padding + extension
        
        try:
            # 获取目录内容并排序
            entries = sorted(os.listdir(directory), key=lambda s: s.lower())
            if not entries:  # 空目录
                return
                
            # 分离目录和文件
            dirs = []
            files = []
            for entry in entries:
                full_path = os.path.join(directory, entry)
                if os.path.isdir(full_path) or os.path.islink(full_path):
                    dirs.append(entry)
                else:
                    files.append(entry)
            
            # 处理目录
            dirs_count = len(dirs)
            for i, entry in enumerate(dirs):
                is_last_dir = (i == dirs_count - 1 and not files)
                full_path = os.path.join(directory, entry)
                self.tree(full_path, new_padding, is_last_dir, print_size)
            
            # 处理文件
            files_count = len(files)
            for i, entry in enumerate(files):
                is_last_file = (i == files_count - 1)
                full_path = os.path.join(directory, entry)
                file_text = f"{new_padding}{'└── ' if is_last_file else '├── '}{entry}"
                
                # 添加文件大小信息（如果启用了大小显示）
                if print_size and os.path.isfile(full_path):
                    try:
                        size_str = self.get_file_size(full_path)
                        file_text += f" [大小: {size_str}]"
                    except OSError as e:
                        file_text += f" [错误: {str(e)}]"
                
                print(file_text)
        
        except PermissionError:
            print(f"{new_padding}└── [错误: 无权限访问此目录]")

_ws_ = Workspace(os.path.dirname(os.path.abspath(__file__)))

class FFmpegWorker(QObject):
    """单独的FFmpeg处理线程"""
    finished = pyqtSignal(bool, str)  # 成功状态，消息
    progress = pyqtSignal(int, str)  # 进度百分比，消息
    output_received = pyqtSignal(str)  # 接收输出

    def __init__(self, command, output_path):
        super().__init__()
        self.command = command
        self.output_path = output_path
        self._is_cancelled = False
        self.process = None
        
    def run(self):
        
        try:
            # 添加PATH设置
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
                ffmpeg_path = self.command[0]
                
                if ffmpeg_path:
                    bin_dir = os.path.dirname(ffmpeg_path)
                    current_path = os.environ['PATH']
                    
                    # 添加FFmpeg的bin目录到PATH
                    if bin_dir not in current_path:
                        os.environ['PATH'] = bin_dir + os.pathsep + current_path
                        print(f"Added FFmpeg bin directory to PATH: {bin_dir}")
        
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "audio_output.ogg")
            
            # 替换输出路径为临时文件
            modified_cmd = []
            for arg in self.command:
                if arg == self.output_path:
                    modified_cmd.append(temp_file)
                else:
                    modified_cmd.append(arg)
                    
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                
            # 启动进程
            self.progress.emit(1, "正在启动音频提取...")
            self.process = subprocess.Popen(
                modified_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                startupinfo=startupinfo,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 读取输出线程
            def read_output():
                while True:
                    if not self.process.stdout:
                        break
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    self.output_received.emit(line.strip())
            
            output_thread = threading.Thread(target=read_output)
            output_thread.daemon = True
            output_thread.start()
            
            # 等待进程完成
            return_code = self.process.wait()
            
            if self._is_cancelled:
                self.progress.emit(0, "音频提取已取消")
                self.finished.emit(False, "操作已取消")
                return
            
            if return_code != 0:
                self.progress.emit(0, f"音频提取失败，错误码: {return_code}")
                self.finished.emit(False, f"FFmpeg返回错误码: {return_code}")
                return
                
            # 将临时文件移动到最终位置
            try:
                if os.path.exists(temp_file):
                    # 确保目标目录存在
                    output_dir = os.path.dirname(self.output_path)
                    if output_dir and not os.path.exists(output_dir):
                        os.makedirs(output_dir, exist_ok=True)
                        
                    shutil.move(temp_file, self.output_path)
                    self.progress.emit(100, "音频提取完成")
                    self.finished.emit(True, "音频提取成功")
                else:
                    self.progress.emit(0, "音频提取失败，没有生成输出文件")
                    self.finished.emit(False, "没有生成输出文件")
            except Exception as e:
                self.progress.emit(0, f"移动文件出错: {str(e)}")
                self.finished.emit(False, f"移动文件出错: {str(e)}")
        except Exception as e:
            self.progress.emit(0, f"音频提取出错: {str(e)}")
            self.finished.emit(False, f"音频提取出错: {str(e)}")
        finally:
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            
    def cancel(self):
        """取消进程"""
        self._is_cancelled = True
        if self.process and self.process.poll() is None:
            self.process.terminate()
            

class VideoProcessor(QThread):
    # 定义信号用于更新进度和状态
    progress_updated = pyqtSignal(int, str)  # (进度百分比, 状态消息)
    processing_frame = pyqtSignal(int, int)   # (当前帧, 总帧数)
    finished_processing = pyqtSignal(bool, str)  # (成功, 消息)

    def __init__(self, video_path, ogg_path, ws, screen, app, game_dir, world_dir):
        super().__init__()
        self.video_path = video_path
        self.ogg_path = ogg_path
        self.ws = ws  # 世界目录的工作区
        self.screen = screen
        self._is_running = True
        self.app = app
        self.ffmpeg_worker = None
        self.game_dir = game_dir
        self.world_dir = world_dir
        self.total_frames = 0
        self.processed_frames = 0
        self.tick_count = 0
        self.temp_dir = None
        self.cleanup_func = None

    def run(self):
        try:
            # 0. 帧率检查与转换
            self.progress_updated.emit(0, "正在检查视频帧率...")
            if not self.check_and_convert_fps():
                self.finished_processing.emit(False, "视频帧率转换失败")
                return
                
            # 1. 创建数据包结构
            self.progress_updated.emit(0, "正在创建数据包结构...")
            if not self.create_datapack_structure():
                self.finished_processing.emit(False, "创建数据包结构失败")
                return
            
            # 2. 提取音频 (使用单独的线程处理)
            self.progress_updated.emit(5, "正在提取音频...")
            
            # 获取FFmpeg路径
            ffmpeg_path = VideoProcessor(video_path=None, ogg_path=None, ws=_ws_, screen=None, app=None, game_dir=None, world_dir=None).find_ffmpeg()
            if not ffmpeg_path:
                self.progress_updated.emit(0, "找不到FFmpeg")
                self.finished_processing.emit(False, "无法找到FFmpeg")
                return
            
            # 构建FFmpeg命令
            command = [
                ffmpeg_path,
                '-y',
                '-i', self.video_path,
                '-vn',
                '-ac', '1',
                '-acodec', 'libvorbis',
                '-ar', '44100',
                self.ogg_path
            ]
            
            # 创建并启动FFmpeg工作线程
            self.ffmpeg_worker = FFmpegWorker(command, self.ogg_path)
            
            # 连接信号
            self.ffmpeg_worker.progress.connect(self.handle_ffmpeg_progress)
            self.ffmpeg_worker.output_received.connect(self.handle_ffmpeg_output)
            self.ffmpeg_worker.finished.connect(self.handle_ffmpeg_finished)
            
            # 在单独的线程中运行FFmpeg工作线程
            ffmpeg_thread = threading.Thread(target=self.ffmpeg_worker.run)
            ffmpeg_thread.start()
            
            # 等待FFmpeg完成或用户取消
            ffmpeg_thread.join(1)  # 给一点时间启动
            while ffmpeg_thread.is_alive() and self._is_running:
                self.app.processEvents()  # 保持UI响应
                time.sleep(0.1)
            
            # 检查是否成功提取音频
            if not os.path.exists(self.ogg_path) or os.path.getsize(self.ogg_path) < 1024:
                self.finished_processing.emit(False, "音频提取失败")
                return
            
            # 3. 处理视频帧
            self.progress_updated.emit(25, "正在打开视频文件...")
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.finished_processing.emit(False, "无法打开视频文件")
                return
            
            # 获取视频参数
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            original_fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.total_frames = frame_count
            
            # 计算缩放比例
            target_ratio, screen_size, particle_size = self.screen
            scale = max(width, height) / (target_ratio[0] if width > height else target_ratio[1])
            new_width = int(width / scale)
            new_height = int(height / scale)
            
            # 设置新视频帧率
            target_fps = 20
            frame_interval = max(1, int(round(original_fps / target_fps)))
            
            # 创建必要的目录结构
            vd_functions_dir = os.path.join(self.datapack_dir, "data", "vd", "functions")
            os.makedirs(vd_functions_dir, exist_ok=True)
            self.ws.cd(vd_functions_dir)
            
            # 处理每帧
            self.tick_count = 0
            frame_num = 0
            self.processed_frames = 0
            s = screen_size / new_width
            
            # 进度参数（音频提取占5%，帧处理占70%）
            progress_per_frame = 70.0 / math.ceil(frame_count / frame_interval)
            
            while self._is_running:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 跳过帧以实现目标FPS
                if frame_num % frame_interval != 0:
                    frame_num += 1
                    continue
                
                # 调整帧大小
                resized_frame = cv2.resize(frame, (new_width, new_height))
                
                # 生成粒子命令
                txt = f'title @a actionbar \"tick:{self.tick_count}\"\n'
                for y in range(new_height):
                    for x in range(new_width):
                        b, g, r = resized_frame[y, x]
                        txt += f'particle minecraft:dust {r/255:.3f} {g/255:.3f} {b/255:.3f} {particle_size:.2f} ~{x*s:.3f} ~{-y*s:.3f} ~ 0 0 0 3000 1 force\n'
                txt += f"schedule function vd:vd{self.tick_count+1} 1"
                
                # 创建命令文件
                self.ws.create_file(f"vd{self.tick_count}.mcfunction", txt)
                
                self.processed_frames += 1
                if frame_interval > 0:
                    progress = 25 + int(self.processed_frames * progress_per_frame)
                    self.progress_updated.emit(progress, "正在生成命令...")
                    self.processing_frame.emit(self.processed_frames, math.ceil(frame_count / frame_interval))
                
                self.tick_count += 1
                frame_num += 1
                
                # 保持UI响应
                self.app.processEvents()
                
                # 定期检查是否取消
                if not self._is_running:
                    break
            
            cap.release()
            
            if not self._is_running:
                self.finished_processing.emit(False, "操作已取消")
                return
                
            # 4. 创建初始化函数
            self.progress_updated.emit(95, "正在创建初始化函数...")
            if not self.create_init_functions(self.tick_count):
                self.finished_processing.emit(False, "创建初始化函数失败")
                return
            
            # 5. 创建数据包描述文件
            self.create_datapack_description()
            
            self.progress_updated.emit(100, "处理完成")
            self.finished_processing.emit(True, "视频处理完成!")
                
        except Exception as e:
            self.finished_processing.emit(False, f"处理错误: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理临时文件
            if self.cleanup_func:
                self.cleanup_func()
                self.progress_updated.emit(100, "已清理临时文件")

    def check_and_convert_fps(self):
        """检查帧率并转换到20FPS"""
        try:
            # 打开视频检查帧率
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.progress_updated.emit(1, "无法打开视频文件检查帧率")
                return False
                
            original_fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            
            # 检查是否是20的倍数
            valid_fps = [20, 40, 60, 120]
            if original_fps in valid_fps:
                self.progress_updated.emit(1, f"视频帧率{original_fps}有效，无需转换")
                return True
                
            # 需要转换帧率
            self.progress_updated.emit(1, f"视频帧率{original_fps}，需要转换为20FPS...")
            
            # 创建临时目录
            self.temp_dir, self.cleanup_func = self.create_manual_temp_dir(
                prefix="mc_video_",
                suffix="_tmp",
                dir=os.path.dirname(self.video_path))
            
            temp_video_path = os.path.join(self.temp_dir, "converted_video.mp4")
            
            # 转换帧率 - 使用更可靠的方法
            success = self.convert_fps_reliable(self.video_path, temp_video_path, 20)
            if not success:
                self.progress_updated.emit(1, "帧率转换失败")
                return False
                
            # 使用转换后的视频
            self.video_path = temp_video_path
            self.progress_updated.emit(2, f"已转换帧率: {self.video_path}")
            return True
            
        except Exception as e:
            self.progress_updated.emit(1, f"帧率检查错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def convert_fps_reliable(self, input_path, output_path, fps=20):
        """使用FFmpeg将视频帧率调整为指定FPS - 更可靠的方法"""
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        if not os.path.exists(input_path):
            self.progress_updated.emit(1, f"输入文件不存在: {input_path}")
            return False
        
        # 获取FFmpeg路径
        ffmpeg_path = self.find_ffmpeg()
        if not ffmpeg_path:
            self.progress_updated.emit(1, "FFmpeg不可用")
            return False
        
        # 方法1: 尝试使用简单的帧率转换
        if not self._try_simple_fps_conversion(ffmpeg_path, input_path, output_path, fps):
            # 方法1失败，尝试方法2: 使用过滤器
            self.progress_updated.emit(1, "简单转换失败，尝试使用过滤器方法...")
            if not self._try_filter_fps_conversion(ffmpeg_path, input_path, output_path, fps):
                # 方法2失败，尝试方法3: 使用解码+编码
                self.progress_updated.emit(1, "过滤器方法失败，尝试完全重编码...")
                return self._try_full_reencode_fps_conversion(ffmpeg_path, input_path, output_path, fps)
        return True

    def _try_simple_fps_conversion(self, ffmpeg_path, input_path, output_path, fps):
        """尝试简单的帧率转换方法"""
        try:
            # 构建转换命令 - 简单方法
            command = [
                ffmpeg_path,
                '-y',  # 覆盖输出文件
                '-i', input_path,
                '-r', str(fps),  # 设置输出帧率
                '-c:v', 'copy',  # 尝试复制视频流
                '-c:a', 'copy',  # 尝试复制音频流
                output_path
            ]
            
            return self._run_ffmpeg_command(command, "简单帧率转换")
        except Exception as e:
            print(1, f"简单转换失败: {str(e)}")
            return False

    def _try_filter_fps_conversion(self, ffmpeg_path, input_path, output_path, fps):
        """使用过滤器方法转换帧率"""
        try:
            # 构建转换命令 - 使用fps过滤器
            command = [
                ffmpeg_path,
                '-y',  # 覆盖输出文件
                '-i', input_path,
                '-filter:v', f'fps=fps={fps}',  # 使用fps过滤器
                '-c:v', 'libx264',  # H.264视频编码
                '-preset', 'fast',  # 快速预设
                '-crf', '23',  # 质量参数
                '-c:a', 'copy',  # 复制音频流
                output_path
            ]
            
            return self._run_ffmpeg_command(command, "过滤器帧率转换")
        except Exception as e:
            print(1, f"过滤器转换失败: {str(e)}")
            return False

    def _try_full_reencode_fps_conversion(self, ffmpeg_path, input_path, output_path, fps):
        """使用完全重编码方法转换帧率"""
        try:
            # 构建转换命令 - 完全重编码
            command = [
                ffmpeg_path,
                '-y',  # 覆盖输出文件
                '-i', input_path,
                '-r', str(fps),  # 设置输出帧率
                '-c:v', 'libx264',  # H.264视频编码
                '-preset', 'fast',  # 快速预设
                '-crf', '23',  # 质量参数
                '-c:a', 'aac',  # AAC音频编码
                '-b:a', '192k',  # 音频比特率
                output_path
            ]
            
            return self._run_ffmpeg_command(command, "完全重编码帧率转换", output_path)
        except Exception as e:
            self.progress_updated.emit(1, f"完全重编码失败: {str(e)}")
            return False

    def _run_ffmpeg_command(self, command, method_name, output_path=None):
        """执行FFmpeg命令并处理输出"""
        self.progress_updated.emit(1, f"开始{method_name}...")
        
        # 调试信息
        cmd_str = ' '.join(command)
        self.progress_updated.emit(1, f"FFmpeg命令: {cmd_str}")
        
        # 创建日志文件 - 使用UTF-8编码
        log_path = os.path.join(self.temp_dir, "ffmpeg_log.txt")
        
        try:
            # 跨平台的FFmpeg执行方式
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # 隐藏窗口
            
            # 执行FFmpeg命令 - 使用二进制模式读取
            with open(log_path, 'w', encoding='utf-8') as log_file:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    startupinfo=startupinfo,
                    bufsize=1
                )
                
                # 读取输出并实时更新状态
                output_lines = []
                while True:
                    # 使用二进制模式读取一行
                    raw_line = process.stdout.readline()
                    if not raw_line:
                        break
                    
                    try:
                        # 尝试UTF-8解码
                        line = raw_line.decode('utf-8', errors='replace').strip()
                    except UnicodeDecodeError:
                        # 如果UTF-8失败，尝试使用系统默认编码
                        try:
                            line = raw_line.decode(sys.getdefaultencoding(), errors='replace').strip()
                        except:
                            # 如果都失败，使用占位符
                            line = "[无法解码的输出行]"
                    
                    output_lines.append(line)
                    log_file.write(line + "\n")
                    log_file.flush()
                    
                    # 定期更新状态
                    if len(output_lines) % 10 == 0:
                        status = f"{method_name}中... 已读取{len(output_lines)}行"
                        self.progress_updated.emit(1, status)
                    
                    # 检查是否取消
                    if not self._is_running:
                        process.terminate()
                        self.progress_updated.emit(1, f"{method_name}已取消")
                        return False
            
            # 等待进程完成
            return_code = process.wait()
            
            if return_code != 0:
                # 收集错误信息 - 使用安全的字符串处理
                error_output = ''.join(output_lines[-200:])  # 取最后200行
                
                # 创建安全的错误消息（避免编码问题）
                safe_error = self.make_safe_string(f"{method_name}失败，错误码: {return_code}\n{error_output[:500]}")
                self.progress_updated.emit(1, safe_error)
                
                safe_log_path = self.make_safe_string(f"完整日志: {log_path}")
                self.progress_updated.emit(1, safe_log_path)
                return False
            
            # 检查输出文件是否存在
            if not os.path.exists(output_path):
                self.progress_updated.emit(1, f"输出文件未创建: {output_path}")
                return False
                
            # 检查文件大小
            file_size = os.path.getsize(output_path)
            if file_size < 1024:
                self.progress_updated.emit(1, f"输出文件过小: {file_size}字节")
                return False
                
            self.progress_updated.emit(2, f"{method_name}成功!")
            return True
            
        except Exception as e:
            # 创建安全的错误消息
            safe_error = self.make_safe_string(f"{method_name}过程中出错: {str(e)}")
            self.progress_updated.emit(1, safe_error)
            return False
        finally:
            # 确保进程终止
            if 'process' in locals() and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    pass

    # 添加辅助方法处理字符串安全
    def make_safe_string(self, text):
        """创建安全的字符串，避免编码问题"""
        try:
            # 尝试UTF-8编码
            return text.encode('utf-8', 'replace').decode('utf-8')
        except:
            try:
                # 尝试系统默认编码
                return text.encode(sys.getdefaultencoding(), 'replace').decode(sys.getdefaultencoding())
            except:
                # 最后手段：移除非ASCII字符
                return ''.join([c if ord(c) < 128 else '?' for c in text])

    def create_manual_temp_dir(self, prefix='tmp_', suffix='', dir=None):
        """
        创建一个手动删除的临时目录
        
        参数:
            prefix (str): 目录名前缀
            suffix (str): 目录名后缀
            dir (str): 指定父目录（如不指定则使用系统默认临时目录）
        
        返回:
            tuple: (目录路径, 清理函数)
        """
        # 确保临时目录存在
        temp_root = dir or tempfile.gettempdir()
        os.makedirs(temp_root, exist_ok=True)
        
        # 创建唯一命名的临时目录
        temp_path = tempfile.mkdtemp(prefix=prefix, suffix=suffix, dir=temp_root)
        self.progress_updated.emit(1, f"创建临时目录: {temp_path}")
        
        # 确保临时目录可写
        test_file = os.path.join(temp_path, "test_write.txt")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            self.progress_updated.emit(1, f"临时目录不可写: {str(e)}")
            return None, None
        
        def clean_up():
            """删除整个临时目录（包括所有内容）"""
            nonlocal temp_path
            if os.path.exists(temp_path):
                try:
                    # 确保所有文件可写
                    for root, dirs, files in os.walk(temp_path):
                        for name in files:
                            file_path = os.path.join(root, name)
                            try:
                                os.chmod(file_path, 0o777)
                            except:
                                pass
                        for name in dirs:
                            dir_path = os.path.join(root, name)
                            try:
                                os.chmod(dir_path, 0o777)
                            except:
                                pass
                    
                    shutil.rmtree(temp_path, ignore_errors=True)
                    self.progress_updated.emit(2, f"已清理临时目录: {temp_path}")
                    return True
                except Exception as e:
                    self.progress_updated.emit(1, f"清理失败: {e}")
                    return False
            else:
                self.progress_updated.emit(1, "临时目录不存在，无需清理")
                return False
        
        return temp_path, clean_up

    def create_datapack_structure(self):
        """创建完整的数据包结构"""
        try:
            # 创建数据包根目录
            self.datapack_dir = os.path.join(self.world_dir, "datapacks", "video_play")
            ws_datapack = Workspace(self.datapack_dir)
            ws_datapack.create_dir("")
            
            # 创建pack.mcmeta文件（初步创建，后续会更新完整版）
            pack_meta = {
                "pack": {
                    "pack_format": 10,
                    "description": "Minecraft Video Player"
                }
            }
            ws_datapack.create_file("pack.mcmeta", json.dumps(pack_meta, indent=2))
            
            # 创建vd命名空间
            vd_dir = os.path.join(self.datapack_dir, "data", "vd", "functions")
            os.makedirs(vd_dir, exist_ok=True)
            
            # 创建init命名空间
            init_dir = os.path.join(self.datapack_dir, "data", "000init", "functions")
            os.makedirs(init_dir, exist_ok=True)
            
            
            return True
        except Exception as e:
            print(f"创建数据包结构失败: {str(e)}")
            return False
            
    def create_init_functions(self, tick_count):
        """创建初始化函数"""
        try:
            init_dir = os.path.join(self.datapack_dir, "data", "000init", "functions")
            ws_init = Workspace(init_dir)
            
            # 创建init.mcfunction
            init_content = (
                'say initizing\nkill @e[type=armor_stand,tag=origin]\nsummon minecraft:armor_stand ~ ~ ~ {Invisible:0b,Tags:[\'origin\'],Silent:1b,NoGravity:1b,CustomName:"{\\"text\\":\\"Origin\\"}",CustomNameVisible:1b,Marker:1b,Invulnerable:1b,NoBasePlate:1b,Small:1b,NoAI:1b,DisabledSlots:0}'
            )
            ws_init.create_file("init.mcfunction", init_content)
            
            # 创建load.mcfunction
            load_content = (
                'say loading\nexecute as @e[tag=origin,limit=1] at @s run setworldspawn ~ ~ ~\nplaysound minecraft:video_sound record @a ~ ~ ~\nexecute as @e[tag=origin,limit=1] at @s run function vd:vd0\n'
            )
            ws_init.create_file("load.mcfunction", load_content)
            
            del_content = (
                'kill @e[type=armor_stand,tag=origin]'
            )
            ws_init.create_file("del.mcfunction", del_content)
            
            # 在vd命名空间中创建结束函数
            vd_dir = os.path.join(self.datapack_dir, "data", "vd", "functions")
            ws_vd = Workspace(vd_dir)
            end_content = "# 视频结束\nsay 视频播放完成！"
            ws_vd.create_file(f"vd{self.tick_count+1}.mcfunction", end_content)
            
            return True
        except Exception as e:
            print(f"创建初始化函数失败: {str(e)}")
            return False
            
    def create_datapack_description(self):
        """创建完整的数据包描述文件"""
        try:
            pack_meta = {
                "pack": {
                    "pack_format": 10,
                    "description": f"Minecraft Video Player ({self.processed_frames}帧视频)"
                },
                "video_metadata": {
                    "original_file": os.path.basename(self.video_path),
                    "frames": self.processed_frames,
                    "ticks": self.tick_count,
                    "screen_width": self.screen[0][0],
                    "screen_height": self.screen[0][1],
                    "screen_size": self.screen[1],
                    "creation_date": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            
            meta_path = os.path.join(self.datapack_dir, "pack.mcmeta")
            with open(meta_path, 'w') as f:
                json.dump(pack_meta, f, indent=2)
                
            # 同时创建一个README文件
            readme_content = (
                f"Minecraft Video Player Datapack\n"
                f"Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Original Video: {os.path.basename(self.video_path)}\n"
                f"Resolution: {self.screen[0][0]}x{self.screen[0][1]}\n"
                f"Frames: {self.processed_frames}\n\n"
                "Usage:\n"
                "1. In-game, run: /function 000init:init\n"
                "2. Then run: /function 000init:load\n"
                "3. To stop: /function 000init:stop\n"
            )
            
            readme_path = os.path.join(self.datapack_dir, "README.txt")
            with open(readme_path, 'w') as f:
                f.write(readme_content)
                
            return True
        except Exception as e:
            print(f"创建数据包描述失败: {str(e)}")
            return False

    def handle_ffmpeg_progress(self, progress, message):
        """处理FFmpeg进度更新"""
        # 将FFmpeg进度映射到5-25%的范围
        mapped_progress = 5 + int(progress * 0.2)
        self.progress_updated.emit(mapped_progress, message)
        
    def handle_ffmpeg_output(self, output):
        """处理FFmpeg输出"""
        # 可以在此处添加日志记录
        # print(output)
        pass
        
    def handle_ffmpeg_finished(self, success, message):
        """处理FFmpeg完成信号"""
        if not success:
            self.progress_updated.emit(0, f"音频提取失败: {message}")
            self._is_running = False

    def find_ffmpeg(self, ws = None):
        """尝试在多个位置查找FFmpeg可执行文件"""
        # 1. 优先检查打包后的应用路径 (Sys._MEIPASS)
        if getattr(sys, 'frozen', False):
            try:
                base_path = sys._MEIPASS
                exe_name = 'ffmpeg.exe'
                
                # 尝试在多个可能的子目录中查找
                possible_paths = [
                    os.path.join(base_path, 'ffmpeg', exe_name),
                    os.path.join(base_path, 'ffmpeg', 'bin', exe_name),
                    os.path.join(base_path, 'ffmpeg', 'usr', 'bin', exe_name),
                    os.path.join(base_path, exe_name)
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        print(f"Found FFmpeg in bundle: {path}")
                        return path
            except AttributeError:
                pass
        
        # 2. 检查当前应用目录
        app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        exe_name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
        app_path = os.path.join(app_dir, 'ffmpeg', 'bin', exe_name)
        if os.path.exists(app_path):
            return app_path
        
        # 3. 检查系统PATH
        if shutil.which('ffmpeg'):
            return shutil.which('ffmpeg')
        
        # 4. 检查常见安装路径 (Windows)
        if sys.platform == 'win32':
            program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            possible_paths = [
                os.path.join(program_files, 'FFmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(program_files, 'ffmpeg', 'bin', 'ffmpeg.exe')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return path
        
        return None

    def stop(self):
        """停止处理"""
        self._is_running = False
        if self.ffmpeg_worker:
            self.ffmpeg_worker.cancel()


class VideoConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft 视频转换工具（由@boring_xia制作，使用制作视频需标注原作者）")
        self.setGeometry(100, 100, 800, 650)
        self.video_path = None
        self.target_game_dir = None
        self.target_world_dir = None
        self.width_input = None
        self.height_input = None
        self.screen_size_input = None
        self.particle_size_input = None
        self.processing_thread = None
        self.elapsed_timer = None
        
        icon_path = self.get_icon_path()
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setup_ui()
        self.center_on_screen()
    
    def get_icon_path(self):
        """获取图标文件路径（适应开发环境和打包环境）"""
        # 优先尝试使用相对路径
        paths_to_try = [
            "app_icon.ico",
            "icons/app_icon.ico",
            "resources/app_icon.ico"
        ]
        
        # 如果是打包环境，尝试从临时目录加载
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            paths_to_try.insert(0, os.path.join(base_path, "app_icon.ico"))
            paths_to_try.insert(0, os.path.join(base_path, "resources", "app_icon.ico"))
        
        for path in paths_to_try:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        return None
    
    def center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center() - self.rect().center())
        
    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 视频文件拖放区
        video_group = QGroupBox("1. 导入视频文件")
        video_layout = QVBoxLayout(video_group)
        video_layout.setContentsMargins(15, 15, 15, 15)
        
        self.drop_area = DropArea()
        self.drop_area.dropAccepted.connect(self.video_dropped)
        video_layout.addWidget(self.drop_area)
        
        # 目标目录选择区
        dir_group = QGroupBox("2. 选择目标目录")
        dir_layout = QFormLayout(dir_group)
        dir_layout.setContentsMargins(15, 15, 15, 15)
        dir_layout.setVerticalSpacing(10)
        dir_layout.setHorizontalSpacing(15)
        
        self.game_dir_btn = QPushButton("选择版本目录")
        self.game_dir_btn.setFixedWidth(120)
        self.game_dir_btn.clicked.connect(self.choose_game_dir)
        self.game_dir_label = QLabel("未选择")
        self.game_dir_label.setWordWrap(True)
        dir_layout.addRow(self.game_dir_btn, self.game_dir_label)
        
        self.world_dir_btn = QPushButton("选择存档目录")
        self.world_dir_btn.setFixedWidth(120)
        self.world_dir_btn.clicked.connect(self.choose_world_dir)
        self.world_dir_label = QLabel("未选择")
        self.world_dir_label.setWordWrap(True)
        dir_layout.addRow(self.world_dir_btn, self.world_dir_label)
        
        # 屏幕参数输入区
        screen_group = QGroupBox("3. 设置屏幕参数")
        screen_layout = QVBoxLayout(screen_group)
        screen_layout.setContentsMargins(15, 15, 15, 15)
        
        help_text = QLabel("请设置屏幕的4个参数:")
        help_text.setFont(QFont("Arial", 9, QFont.Bold))
        screen_layout.addWidget(help_text)
        
        # 三个输入框
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)
        
        self.width_input = QLineEdit()
        self.width_input.setPlaceholderText("例如: 40")
        self.width_input.setValidator(QIntValidator(1, 1000))
        self.width_input.textChanged.connect(self.check_screen_settings)
        form_layout.addRow("宽度 (像素数):", self.width_input)
        
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("例如: 22")
        self.height_input.setValidator(QIntValidator(1, 1000))
        self.height_input.textChanged.connect(self.check_screen_settings)
        form_layout.addRow("高度 (像素数):", self.height_input)
        
        self.screen_size_input = QLineEdit()
        self.screen_size_input.setPlaceholderText("例如: 10")
        self.screen_size_input.setValidator(QIntValidator(1, 100))
        self.screen_size_input.textChanged.connect(self.check_screen_settings)
        form_layout.addRow("屏幕尺寸 (方块大小):", self.screen_size_input)
        
        self.particle_size_input = QLineEdit()
        self.particle_size_input.setPlaceholderText("例如: 80 %")
        self.particle_size_input.setValidator(QIntValidator(0, 400))
        self.particle_size_input.textChanged.connect(self.check_screen_settings)
        form_layout.addRow("粒子尺寸:", self.particle_size_input)
        
        screen_layout.addLayout(form_layout)
        
        # 进度条区
        progress_group = QGroupBox("4. 转换进度")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(15, 15, 15, 15)
        
        # 帧进度标签
        self.frame_progress_label = QLabel()
        self.frame_progress_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.frame_progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(30)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.status_label)
        
        # 添加音频信息标签
        self.audio_status_label = QLabel()
        self.audio_status_label.setAlignment(Qt.AlignCenter)
        self.audio_status_label.setVisible(False)
        self.audio_status_label.setObjectName("audioStatus")
        progress_layout.addWidget(self.audio_status_label)
        
        # 操作按钮区
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 10, 0, 0)
        buttons_layout.setSpacing(20)
        
        self.convert_btn = QPushButton("请先完成所有设置")
        self.convert_btn.setEnabled(False)
        self.convert_btn.setFixedHeight(40)
        self.convert_btn.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #CCCCCC; color: #666666;")
        self.convert_btn.clicked.connect(self.start_conversion)
        buttons_layout.addWidget(self.convert_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedHeight(35)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_processing)
        buttons_layout.addWidget(self.cancel_btn)
        
        reset_btn = QPushButton("重置")
        reset_btn.setFixedHeight(35)
        reset_btn.clicked.connect(self.reset_form)
        buttons_layout.addWidget(reset_btn)
        
        # 添加到主布局
        layout.addWidget(video_group)
        layout.addWidget(dir_group)
        layout.addWidget(screen_group)
        layout.addWidget(progress_group)
        layout.addLayout(buttons_layout)
        
    def choose_game_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择Minecraft游戏目录", "C:/")
        if directory:
            self.target_game_dir = directory
            self.game_dir_label.setText(os.path.normpath(directory))
            self.update_status("游戏目录已设置: " + os.path.normpath(directory))
            self.check_ready()

    def choose_world_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择Minecraft世界目录", "C:/")
        if directory:
            self.target_world_dir = directory
            self.world_dir_label.setText(os.path.normpath(directory))
            self.update_status("世界目录已设置: " + os.path.normpath(directory))
            self.check_ready()

    def video_dropped(self, file_path):
        if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
            self.video_path = file_path
            self.drop_area.set_file_info(file_path)
            self.update_status(f"已选择视频: {os.path.basename(file_path)}")
            self.check_ready()
        else:
            QMessageBox.warning(self, "不支持的格式", 
                               "只支持以下视频格式: MP4, AVI, MOV, MKV, FLV, WMV")
            self.drop_area.clear()

    def check_screen_settings(self):
        # 检查所有三个输入框是否都已填写
        self.check_ready()

    def validate_screen_settings(self):
        # 验证屏幕参数
        try:
            width = int(self.width_input.text().strip())
            height = int(self.height_input.text().strip())
            screen_size = int(self.screen_size_input.text().strip())
            particle_size = int(self.particle_size_input.text().strip())
            
            if width <= 0 or height <= 0 or screen_size <= 0 or particle_size <= 0:
                QMessageBox.warning(self, "数值错误", "所有值必须大于零")
                return None
            
            return ((width, height), screen_size, particle_size/100)
        except ValueError:
            QMessageBox.warning(self, "数值错误", "请输入有效的数")
            return None

    def check_ready(self):
        # 检查所有必要设置是否完成
        video_ok = self.video_path is not None
        game_dir_ok = self.target_game_dir is not None
        world_dir_ok = self.target_world_dir is not None
        screen_ok = all([
            self.width_input.text().strip() != "",
            self.height_input.text().strip() != "",
            self.screen_size_input.text().strip() != ""
        ])
        
        all_ok = video_ok and game_dir_ok and world_dir_ok and screen_ok
        
        if all_ok:
            self.convert_btn.setEnabled(True)
            self.convert_btn.setText("开始转换")
            self.convert_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText("请先完成所有设置")
            self.convert_btn.setStyleSheet("""
                QPushButton {
                    background-color: #CCCCCC;
                    color: #666666;
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
        
        return all_ok

    def start_conversion(self):
        if not self.check_ready():
            QMessageBox.warning(self, "信息不完整", "请完成所有设置后再开始转换")
            return
        
        # 验证屏幕设置
        screen_settings = self.validate_screen_settings()
        if not screen_settings:
            return
        
        # 显示音频状态标签
        self.audio_status_label.setVisible(True)
        
        try:
            # 准备FFmpeg路径
            if not self.is_ffmpeg_available():
                QMessageBox.warning(self, "缺少依赖", 
                                   "未找到FFmpeg，请确保FFmpeg已安装并添加到系统PATH中。\n"
                                   "您可以从https://ffmpeg.org下载FFmpeg。")
                return
            
            # 创建工作区
            ws_g = Workspace(self.target_game_dir)
            ws_w = Workspace(self.target_world_dir)
            ws_r = Workspace(os.path.join(self.target_game_dir, "resourcepacks"))
            
            # 准备OGG文件路径
            ogg_path = self.resource_pack(ws_r)
            
            # 初始化UI状态
            self.set_ui_enabled(False)
            self.progress_bar.setValue(0)
            self.convert_btn.setVisible(False)
            self.cancel_btn.setVisible(True)
            self.status_label.setText("准备开始处理...")
            self.frame_progress_label.setText("")
            
            # 创建并启动处理线程
            self.processing_thread = VideoProcessor(
                self.video_path, 
                ogg_path, 
                ws_w,
                screen_settings,
                QApplication.instance(),
                self.target_game_dir,
                self.target_world_dir
            )
            
            # 连接信号
            self.processing_thread.progress_updated.connect(self.update_progress)
            self.processing_thread.processing_frame.connect(self.update_frame_progress)
            self.processing_thread.finished_processing.connect(self.handle_processing_complete)
            
            # 启动计时器
            self.elapsed_timer = QTime(0, 0)
            self.elapsed_timer.start()
            
            # 启动处理线程
            self.processing_thread.start()
            
        except Exception as e:
            self.update_status(f"初始化错误: {str(e)}")
            self.set_ui_enabled(True)
            import traceback
            traceback.print_exc()
    
    def is_ffmpeg_available(self):
        """检查FFmpeg是否可用"""
        try:
            # 在后台运行ffmpeg -version命令
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                
            process = subprocess.Popen(
                [r'ffmpeg\ffmpeg.exe', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            process.wait(1)  # 等待最多1秒
            return process.returncode == 0
        except:
            return False
    
    def resource_pack(self, ws):
        """创建资源包并返回OGG文件路径"""
        try:
            ws.return_to_root()
            ws.cd("video_music")
            ws.create_file("pack.mcmeta", '{"pack":{"pack_format":15,"description":"Video Music Pack"}}')
            
            ws.cd(r"assets\minecraft")
            ws.create_file("sounds.json", json.dumps({
                "video_sound": {
                    "category": "record",
                    "sounds": [{
                        "name": "video_music/audio",
                        "stream": True
                    }]
                }
            }, indent=2))
            
            ws.cd("sounds")
            ws.cd("video_music")
            return os.path.join(ws.current_path, "audio.ogg")
        except Exception as e:
            self.audio_status_label.setText(f"创建资源包失败: {str(e)}")
            raise RuntimeError(f"创建资源包失败: {str(e)}")
    
    def update_progress(self, value, message):
        """更新进度条和状态消息"""
        self.progress_bar.setValue(value)
        status_text = f"{message} ({self.elapsed_timer.elapsed()/1000:.1f}秒)"
        self.status_label.setText(status_text)
        
        # 如果是音频相关状态，更新特定标签
        if "音频" in message:
            self.audio_status_label.setText(status_text)
    
    def update_frame_progress(self, current_frame, total_frames):
        """更新帧处理进度"""
        if total_frames > 0:
            frame_percent = current_frame / total_frames * 100
            self.frame_progress_label.setText(f"帧处理进度: {current_frame}/{total_frames} ({frame_percent:.1f}%)")
        
    def handle_processing_complete(self, success, message):
        """处理完成信号"""
        elapsed = self.elapsed_timer.elapsed() / 1000.0
        
        # 隐藏音频状态标签
        self.audio_status_label.setVisible(False)
        
        # 恢复UI状态
        self.set_ui_enabled(True)
        self.convert_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        
        if self.processing_thread:
            self.processing_thread = None
        
        if success:
            self.status_label.setText(f"处理完成! 耗时: {elapsed:.1f}秒")
            self.progress_bar.setValue(100)
            
            # 显示结果对话框
            details = self.get_success_details(elapsed)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("转换成功")
            msg_box.setText(f"视频转换已完成，耗时 {elapsed:.1f}秒")
            msg_box.setInformativeText(details)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStyleSheet("QLabel{min-width: 400px;}")
            msg_box.exec()
            
            # 打开数据包目录
            try:
                if sys.platform == "win32":
                    os.startfile(os.path.join(self.target_world_dir, "datapacks", "video_play"))
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", os.path.join(self.target_world_dir, "datapacks", "video_play")])
                else:
                    subprocess.Popen(["xdg-open", os.path.join(self.target_world_dir, "datapacks", "video_play")])
            except:
                pass
        else:
            self.status_label.setText(f"处理失败: {message}")
            QMessageBox.critical(self, "转换失败", f"视频处理过程中出错:\n{message}")
    
    def get_success_details(self, elapsed):
        """构建成功信息"""
        width = self.width_input.text().strip()
        height = self.height_input.text().strip()
        size = self.screen_size_input.text().strip()
        p_size = self.particle_size_input.text().strip()
        
        return f"""
<b>视频文件:</b> {os.path.basename(self.video_path)}<br>
<b>屏幕参数:</b> 宽度={width}px, 高度={height}px, 尺寸={size}方块, 粒子大小={p_size}<br>
<b>游戏目录:</b> {self.target_game_dir}<br>
<b>世界目录:</b> {self.target_world_dir}<br><br>
已创建:<br>
• 资源包在 resourcepacks/video_music<br>
• 数据包在世界目录的 datapacks/video_play<br><br>
<b>启动游戏后，在聊天框依次输入命令:</b><br>
1. <code>/function 000init:init</code> - 初始化环境<br>
2. <code>/function 000init:load</code> - 开始播放<br>
3. <code>/function 000init:del</code> - 清除环境<br><br>
"""
    
    def cancel_processing(self):
        """取消正在进行的处理"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.status_label.setText("正在取消操作...")
            self.audio_status_label.setText("正在停止音频处理...")
            self.processing_thread.stop()
            # 等待线程安全退出
            self.processing_thread.wait(2000)
            self.audio_status_label.setVisible(False)
            self.status_label.setText("操作已取消")
            self.set_ui_enabled(True)
            self.convert_btn.setVisible(True)
            self.cancel_btn.setVisible(False)
            
    def update_status(self, message):
        """更新状态标签"""
        self.status_label.setText(message)
        self.status_label.repaint()

    def reset_form(self):
        """重置所有表单"""
        # 如果有处理在进行，先取消
        if self.processing_thread and self.processing_thread.isRunning():
            self.cancel_processing()
        
        self.video_path = None
        self.target_game_dir = None
        self.target_world_dir = None
        
        self.drop_area.clear()
        self.game_dir_label.setText("未选择")
        self.world_dir_label.setText("未选择")
        self.width_input.clear()
        self.height_input.clear()
        self.screen_size_input.clear()
        self.particle_size_input.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("就绪")
        self.frame_progress_label.setText("")
        self.audio_status_label.setVisible(False)
        
        # 重置按钮状态
        self.convert_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        
        self.check_ready()
    
    def set_ui_enabled(self, enabled):
        """设置UI组件的启用状态"""
        self.drop_area.setEnabled(enabled)
        self.game_dir_btn.setEnabled(enabled)
        self.world_dir_btn.setEnabled(enabled)
        self.width_input.setEnabled(enabled)
        self.height_input.setEnabled(enabled)
        self.screen_size_input.setEnabled(enabled)
        self.particle_size_input.setEnabled(enabled)
        self.convert_btn.setEnabled(enabled)
        
        alpha = 1.0 if enabled else 0.6
        self.drop_area.setStyleSheet(f"background-color: rgba(240, 240, 240, {alpha})")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 如果有处理在进行，先取消
        if self.processing_thread and self.processing_thread.isRunning():
            reply = QMessageBox.question(
                self, '确认退出',
                '转换正在进行中，确定要退出吗？',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.cancel_processing()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class DropArea(QLabel):
    dropAccepted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(150)
        self.clear()
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.dropAccepted.emit(file_path)
    
    def clear(self):
        self.setText("拖放视频文件到这里\n(或点击选择文件)")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 20px;
                background-color: #f0f0f0;
                font-size: 16px;
                color: #666666;
            }
        """)
    
    def set_file_info(self, file_path):
        name = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        size_str = f"{size/(1024 * 1024):.2f} MB" if size > 1024 * 1024 else f"{size/1024:.2f} KB"
        
        self.setText(f"""
            <div style="font-weight: bold; font-size: 16px;">{name}</div>
            <div style="font-size: 14px; margin-top: 8px;">{size_str}</div>
            <div style="font-size: 12px; margin-top: 8px; color: #666;">
                {os.path.dirname(file_path)}
            </div>
        """)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #4CAF50;
                border-radius: 10px;
                padding: 15px;
                background-color: #f0fff0;
                font-size: 14px;
            }
        """)


if __name__ == "__main__":
    
    os.chdir(r"C:")
    
    
    # def tree(directory, padding=''):
    #     print(padding[:-1] + '└── ' + os.path.basename(directory) + '/')
    #     padding += '    '
    #     files = []
    #     for f in os.listdir(directory):
    #         path = os.path.join(directory, f)
    #         if os.path.isdir(path):
    #             tree(path, padding + '│   ')
    #         else:
    #             files.append(f)
    #     for f in files:
    #         print(padding + '└── ' + f)
    
    
    # ws = Workspace()
    # print(VideoProcessor.find_ffmpeg(None))
    # print(_ws_.path_exists(VideoProcessor.find_ffmpeg(None)))
    
    # path = sys._MEIPASS
    
    # print(tree(path))
    # time.sleep(1000)
    print("cv2-ffmpeg: " + str(cv2.getBuildInformation())) 
    
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置全局字体
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    
    # 设置CSS样式
    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 1px solid #d0d0d0;
            border-radius: 8px;
            margin-top: 1.5em;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }
        QPushButton {
            padding: 5px 15px;
            border-radius: 4px;
            background-color: #f0f0f0;
            border: 1px solid #c0c0c0;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        QLineEdit {
            padding: 5px;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
        }
        QProgressBar {
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 3px;
        }
        QLabel {
            color: #444444;
        }
        #audioStatus {
            font-style: italic;
            color: #0088cc;
            font-weight: bold;
        }
    """)
    
    window = VideoConverterApp()
    window.show()
    sys.exit(app.exec_())
# -*- coding: utf-8 -*-
"""
GitHub 同步对话框
处理 GitHub 同步的用户界面
"""

import os
import sys
import subprocess
import threading
from datetime import datetime
from pathlib import Path

try:
    from PySide2.QtCore import QThread, Signal, QObject
    try:
        from shiboken2 import isValid as qt_object_is_valid
    except ImportError:
        qt_object_is_valid = None
except ImportError:
    try:
        from PySide6.QtCore import QThread, Signal, QObject
        try:
            from shiboken6 import isValid as qt_object_is_valid
        except ImportError:
            qt_object_is_valid = None
    except ImportError:
        QThread = threading.Thread
        qt_object_is_valid = None
        class Signal:
            def __init__(self, *args): pass
            def connect(self, func): pass
            def emit(self, *args): pass
        class QObject: pass


def check_and_install_requests():
    """
    检查并安装 requests 库
    如果未安装则自动安装
    """
    try:
        import requests
        return True
    except ImportError:
        print("未找到 requests 库，正在自动安装...")
        try:
            # 使用 pip 安装 requests
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
            print("requests 库安装成功！")
            return True
        except subprocess.CalledProcessError as e:
            print(f"安装 requests 库失败: {str(e)}")
            return False


# 检查并安装 requests 库
check_and_install_requests()

# 确保重新加载 github_service 模块
import importlib
import core.services.github_service
importlib.reload(core.services.github_service)

from core.utils.qt_compat import *
from core.services.github_service import GitHubService


class UploadWorker(QThread):
    """后台上传工作线程"""
    progress = Signal(int, str)  # 进度百分比, 当前文件名
    finished = Signal(bool, dict)  # 是否成功, 结果信息
    error = Signal(str)  # 错误信息
    
    def __init__(self, github_service, repo_name, files_info, branch_name, use_git=True):
        super().__init__()
        self.github_service = github_service
        self.repo_name = repo_name
        self.files_info = files_info
        self.branch_name = branch_name
        self.use_git = use_git
        self._is_running = True
    
    def run(self):
        try:
            if self.use_git:
                self._run_git_upload()
            else:
                self._run_api_upload()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False, {})
    
    def _run_git_upload(self):
        """使用 Git 方式上传"""
        self.progress.emit(0, "正在准备 Git 仓库...")
        result = self.github_service.upload_files_with_git(
            self.repo_name,
            self.files_info,
            self.branch_name
        )
        self.progress.emit(100, "上传完成!")
        self.finished.emit(True, result)
    
    def _run_api_upload(self):
        """使用 API 方式上传"""
        result = {
            "success": 0,
            "failed": 0,
            "failed_files": []
        }
        
        total_files = len(self.files_info)
        for idx, (file_path, repo_path) in enumerate(self.files_info):
            if not self._is_running:
                break
            
            # 更新进度
            filename = os.path.basename(file_path)
            self.progress.emit(int((idx / total_files) * 100), filename)
            
            # 上传单个文件
            if self.github_service.upload_file(self.repo_name, file_path, repo_path, self.branch_name):
                result["success"] += 1
            else:
                result["failed"] += 1
                result["failed_files"].append(file_path)
        
        # 最后的进度更新
        if self._is_running:
            self.progress.emit(100, "完成!")
        
        self.finished.emit(True, result)
    
    def stop(self):
        """停止上传"""
        self._is_running = False


class GitHubSyncDialog:
    """GitHub 同步对话框"""
    
    def __init__(self, *args, **kwargs):
        """
        初始化 GitHub 同步对话框
        
        参数:
            parent_window: 父窗口（位置参数或关键字参数）
            config_path: GitHub 配置文件路径（位置参数或关键字参数）
        """
        print(f"[GitHubSyncDebug] 初始化 GitHubSyncDialog，参数: args={args}, kwargs={kwargs}")
        
        # 解析参数
        self.parent = kwargs.get('parent_window')
        self.config_path = kwargs.get('config_path')
        
        if len(args) >= 1:
            self.parent = args[0]
        if len(args) >= 2:
            self.config_path = args[1]
        
        # 如果没有提供 config_path，提供默认值
        if self.config_path is None and self.parent is not None:
            try:
                from pathlib import Path
                config_dir = Path(self.parent.root_dir) / "core" / "utils" / "configuration"
                self.config_path = config_dir / "github_config.json"
                print(f"[GitHubSyncDebug] 使用默认 config_path: {self.config_path}")
            except Exception as e:
                print(f"[GitHubSyncDebug] 无法获取默认 config_path: {e}")
        
        self.dialog = None
        self.github_service = GitHubService(self.config_path) if self.config_path else None
        self.selected_files = []
        self.repo_list = []
        self.branch_list = []
        self.current_repo_name = ""
        self.current_branch = ""
        
        # UI 组件
        self.token_input = None
        self.user_label = None
        self.repo_combo = None
        self.repo_name_input = None
        self.branch_combo = None
        self.branch_name_input = None
        self.file_list_widget = None
        self.upload_mode_combo = None
        self.status_label = None
        self.progress_bar = None
        self.upload_btn = None
        self.cancel_btn = None
        
        # 上传相关
        self.upload_worker = None
        self.git_installed = False
        self._dialog_closing = False
        self._current_repo_name = ""
        self._current_branch_name = ""
    
    def check_git_installed(self):
        """检查是否安装了 Git"""
        try:
            subprocess.check_output(["git", "--version"], stderr=subprocess.STDOUT)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            return False
    
    def open_git_download(self):
        """打开 Git 下载页面"""
        import webbrowser
        webbrowser.open("https://git-scm.com/downloads")
    
    def show_dialog(self):
        """显示 GitHub 同步对话框"""
        self.dialog = QDialog(self.parent)
        self._dialog_closing = False
        
        # 检查 Git 是否已安装
        self.git_installed = self.check_git_installed()
        self.dialog.setWindowTitle("GitHub 同步")
        self.dialog.setFixedWidth(600)
        self.dialog.setMinimumHeight(500)
        self.dialog.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QLineEdit, QComboBox {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                color: #E0E0E0;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:disabled {
                background-color: #444444;
                color: #888888;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
                color: #E0E0E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #E0E0E0;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        
        layout = QVBoxLayout(self.dialog)
        layout.setSpacing(15)
        
        # GitHub 认证组
        auth_group = QGroupBox("GitHub 认证")
        auth_group_layout = QVBoxLayout(auth_group)
        
        # 令牌输入
        token_layout = QHBoxLayout()
        token_label = QLabel("访问令牌:")
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        if self.github_service.token:
            self.token_input.setText("************")  # 不显示实际令牌
        verify_btn = QPushButton("验证")
        verify_btn.clicked.connect(self.verify_token)
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.token_input)
        token_layout.addWidget(verify_btn)
        auth_group_layout.addLayout(token_layout)
        
        # 用户信息显示
        self.user_label = QLabel("用户: 未验证")
        self.user_label.setStyleSheet("color: #AAAAAA;")
        auth_group_layout.addWidget(self.user_label)
        
        # 显示当前用户（如果已配置）
        if self.github_service.repo_owner:
            self.user_label.setText(f"用户: {self.github_service.repo_owner}")
        
        layout.addWidget(auth_group)
        
        # Git 安装提示组
        git_info_group = QGroupBox("Git 状态")
        git_info_layout = QHBoxLayout(git_info_group)
        
        if self.git_installed:
            git_status_label = QLabel("✓ Git 已安装，推荐使用 Git 方式上传（更快！）")
            git_status_label.setStyleSheet("color: #4ECDC4; font-weight: bold;")
            git_info_layout.addWidget(git_status_label)
        else:
            git_status_label = QLabel("✗ Git 未安装，当前使用 API 方式上传")
            git_status_label.setStyleSheet("color: #FF6B6B;")
            git_info_layout.addWidget(git_status_label)
            
            install_git_btn = QPushButton("安装 Git")
            install_git_btn.setStyleSheet("background-color: #555555; color: #4ECDC4; font-weight: bold;")
            install_git_btn.clicked.connect(self.open_git_download)
            git_info_layout.addWidget(install_git_btn)
        
        layout.addWidget(git_info_group)
        
        # 仓库管理组
        repo_group = QGroupBox("仓库管理")
        repo_group_layout = QVBoxLayout(repo_group)
        
        # 仓库选择或创建
        repo_select_layout = QHBoxLayout()
        repo_label = QLabel("选择仓库:")
        self.repo_combo = QComboBox()
        self.repo_combo.setEditable(True)
        refresh_repo_btn = QPushButton("刷新")
        refresh_repo_btn.clicked.connect(self.refresh_repos)
        repo_select_layout.addWidget(repo_label)
        repo_select_layout.addWidget(self.repo_combo, 1)
        repo_select_layout.addWidget(refresh_repo_btn)
        repo_group_layout.addLayout(repo_select_layout)
        
        # 分支管理
        branch_layout = QHBoxLayout()
        branch_label = QLabel("选择分支:")
        self.branch_combo = QComboBox()
        self.branch_combo.setEditable(True)
        refresh_branch_btn = QPushButton("刷新")
        refresh_branch_btn.clicked.connect(self.refresh_branches)
        branch_layout.addWidget(branch_label)
        branch_layout.addWidget(self.branch_combo, 1)
        branch_layout.addWidget(refresh_branch_btn)
        repo_group_layout.addLayout(branch_layout)
        
        # 上传模式
        mode_layout = QHBoxLayout()
        mode_label = QLabel("仓库已存在时:")
        self.upload_mode_combo = QComboBox()
        self.upload_mode_combo.addItems(["创建新分支", "覆盖现有分支"])
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.upload_mode_combo)
        repo_group_layout.addLayout(mode_layout)
        
        # 上传方式选择
        upload_method_layout = QHBoxLayout()
        method_label = QLabel("上传方式:")
        self.upload_method_combo = QComboBox()
        
        if self.git_installed:
            self.upload_method_combo.addItems(["Git 命令 (推荐，更快)", "GitHub API"])
            self.upload_method_combo.setCurrentIndex(0)
        else:
            self.upload_method_combo.addItems(["GitHub API (Git 未安装)"])
            self.upload_method_combo.setCurrentIndex(0)
            self.upload_method_combo.setEnabled(False)
        
        upload_method_layout.addWidget(method_label)
        upload_method_layout.addWidget(self.upload_method_combo)
        repo_group_layout.addLayout(upload_method_layout)
        
        layout.addWidget(repo_group)
        
        # 文件选择组
        file_group = QGroupBox("文件选择")
        file_group_layout = QVBoxLayout(file_group)
        
        # 操作按钮
        file_btn_layout = QHBoxLayout()
        add_file_btn = QPushButton("添加文件")
        add_file_btn.clicked.connect(self.add_files)
        add_folder_btn = QPushButton("添加文件夹")
        add_folder_btn.clicked.connect(self.add_folder)
        remove_btn = QPushButton("移除选中")
        remove_btn.clicked.connect(self.remove_selected)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_files)
        file_btn_layout.addWidget(add_file_btn)
        file_btn_layout.addWidget(add_folder_btn)
        file_btn_layout.addWidget(remove_btn)
        file_btn_layout.addWidget(clear_btn)
        file_group_layout.addLayout(file_btn_layout)
        
        # 文件列表
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        file_group_layout.addWidget(self.file_list_widget)
        
        layout.addWidget(file_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                color: #E0E0E0;
            }
            QProgressBar::chunk {
                background-color: #3A6EA5;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 状态显示
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #AAAAAA;")
        layout.addWidget(self.status_label)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.upload_btn = QPushButton("上传到 GitHub")
        self.upload_btn.clicked.connect(self.upload_to_github)
        button_layout.addWidget(self.upload_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_upload)
        self.cancel_btn.setVisible(False)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.dialog.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 初始刷新仓库列表
        if self.github_service.token and self.github_service.repo_owner:
            self.refresh_repos()

        self.dialog.finished.connect(self.on_dialog_finished)
        
        self.dialog.show()

    def _is_qt_object_alive(self, obj):
        """检查 Qt 对象是否仍然有效。"""
        if obj is None:
            return False
        if qt_object_is_valid is not None:
            try:
                return qt_object_is_valid(obj)
            except Exception:
                return False
        try:
            obj.objectName()
            return True
        except RuntimeError:
            return False

    def _is_ui_alive(self):
        """UI 是否还可安全访问。"""
        if self._dialog_closing:
            return False
        widgets = [
            self.dialog,
            self.progress_bar,
            self.status_label,
            self.upload_btn,
            self.cancel_btn,
            self.token_input,
            self.repo_combo,
            self.branch_combo,
            self.upload_mode_combo,
            self.upload_method_combo,
            self.file_list_widget,
        ]
        return all(self._is_qt_object_alive(widget) for widget in widgets)

    def _disconnect_worker_signals(self):
        """断开上传线程信号，防止窗口关闭后继续回调 UI。"""
        if not self.upload_worker:
            return
        for signal, handler in (
            (self.upload_worker.progress, self.on_upload_progress),
            (self.upload_worker.finished, self.on_upload_finished),
            (self.upload_worker.error, self.on_upload_error),
        ):
            try:
                signal.disconnect(handler)
            except (RuntimeError, TypeError):
                pass

    def _cleanup_worker(self):
        """清理上传线程引用。"""
        worker = self.upload_worker
        self.upload_worker = None
        if worker and hasattr(worker, "deleteLater"):
            try:
                worker.deleteLater()
            except RuntimeError:
                pass

    def on_dialog_finished(self, _result):
        """对话框关闭时停止后台回调。"""
        self._dialog_closing = True
        self._disconnect_worker_signals()
        worker = self.upload_worker
        if worker:
            try:
                worker.stop()
            except Exception:
                pass
    
    def verify_token(self):
        """验证 GitHub 令牌"""
        token = self.token_input.text().strip()
        
        if not token:
            self.user_label.setText("用户: 未输入令牌")
            self.user_label.setStyleSheet("color: #FF6B6B;")
            return
        
        # 如果显示的是占位符，使用已保存的令牌
        if token == "************" and self.github_service.token:
            pass
        else:
            self.github_service.set_token(token)
        
        user_info = self.github_service.get_user_info()
        
        if user_info:
            self.user_label.setText(f"用户: {user_info.get('login', '未知')}")
            self.user_label.setStyleSheet("color: #4ECDC4;")
            self.refresh_repos()
        else:
            self.user_label.setText("用户: 验证失败，请检查令牌")
            self.user_label.setStyleSheet("color: #FF6B6B;")
    
    def refresh_repos(self):
        """刷新仓库列表"""
        self.repo_combo.clear()
        
        self.repo_list = self.github_service.list_repos()
        
        for repo in self.repo_list:
            self.repo_combo.addItem(repo)
        
        # 设置默认仓库名
        date_str = datetime.now().strftime("%Y%m%d")
        default_repo = f"maya-scripts-{date_str}"
        self.repo_combo.setEditText(default_repo)
        
        if self.repo_list:
            self.status_label.setText(f"已加载 {len(self.repo_list)} 个仓库")
        else:
            self.status_label.setText("无仓库或未验证")
    
    def refresh_branches(self):
        """刷新分支列表"""
        repo_name = self.repo_combo.currentText().strip()
        
        if not repo_name:
            return
        
        self.branch_combo.clear()
        
        if self.github_service.repo_exists(repo_name):
            self.branch_list = self.github_service.list_branches(repo_name)
            
            for branch in self.branch_list:
                self.branch_combo.addItem(branch)
            
            # 设置默认分支
            default_branch = self.github_service.get_default_branch(repo_name)
            index = self.branch_combo.findText(default_branch)
            if index >= 0:
                self.branch_combo.setCurrentIndex(index)
            
            self.status_label.setText(f"已加载 {len(self.branch_list)} 个分支")
        else:
            # 新仓库默认分支
            self.branch_combo.addItem("main")
            self.branch_combo.setCurrentIndex(0)
            self.status_label.setText("新仓库，将创建 main 分支")
    
    def add_files(self):
        """添加文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.dialog,
            "选择要上传的文件",
            "",
            "所有文件 (*.*)"
        )
        
        if file_paths:
            count = 0
            for file_path in file_paths:
                if file_path not in self.selected_files:
                    self.selected_files.append(file_path)
                    self.file_list_widget.addItem(file_path)
                    count += 1
            
            self.status_label.setText(f"已添加 {count} 个文件，共 {len(self.selected_files)} 个项目")
    
    def add_folder(self):
        """添加文件夹（只添加文件夹本身）"""
        folder_path = QFileDialog.getExistingDirectory(
            self.dialog,
            "选择文件夹"
        )
        
        if folder_path and folder_path not in self.selected_files:
            self.selected_files.append(folder_path)
            self.file_list_widget.addItem(folder_path)
            self.status_label.setText(f"已添加文件夹，共 {len(self.selected_files)} 个项目")
    
    def remove_selected(self):
        """移除选中的项目"""
        selected_items = self.file_list_widget.selectedItems()
        
        for item in selected_items:
            file_path = item.text()
            if file_path in self.selected_files:
                self.selected_files.remove(file_path)
            row = self.file_list_widget.row(item)
            self.file_list_widget.takeItem(row)
        
        self.status_label.setText(f"共 {len(self.selected_files)} 个项目")
    
    def clear_files(self):
        """清空项目列表"""
        self.selected_files = []
        self.file_list_widget.clear()
        self.status_label.setText("已清空")
    
    def upload_to_github(self):
        """上传文件到 GitHub"""
        # 验证
        if not self.github_service.token:
            QMessageBox.warning(self.dialog, "警告", "请先验证 GitHub 令牌")
            return
        
        if not self.github_service.repo_owner:
            QMessageBox.warning(self.dialog, "警告", "请先验证 GitHub 令牌")
            return
        
        repo_name = self.repo_combo.currentText().strip()
        if not repo_name:
            QMessageBox.warning(self.dialog, "警告", "请输入仓库名称")
            return
        
        if not self.selected_files:
            QMessageBox.warning(self.dialog, "警告", "请选择要上传的文件")
            return
        
        # 获取分支信息
        branch_name = self.branch_combo.currentText().strip()
        if not branch_name:
            branch_name = "main"
        
        # 检查仓库是否存在
        repo_exists = self.github_service.repo_exists(repo_name)
        
        if repo_exists:
            # 仓库已存在，处理分支
            mode = self.upload_mode_combo.currentText()
            
            if mode == "创建新分支":
                # 生成带日期的分支名
                date_str = datetime.now().strftime("%Y%m%d")
                base_branch_name = branch_name
                new_branch_name = f"{base_branch_name}-{date_str}"
                counter = 1
                existing_branches = self.github_service.list_branches(repo_name)
                
                # 确保分支名唯一
                while new_branch_name in existing_branches:
                    new_branch_name = f"{base_branch_name}-{date_str}-{counter}"
                    counter += 1
                
                # 创建新分支
                if not self.github_service.create_branch(repo_name, new_branch_name):
                    QMessageBox.critical(self.dialog, "错误", f"创建分支 {new_branch_name} 失败")
                    return
                
                branch_name = new_branch_name
                self.status_label.setText(f"已创建分支: {branch_name}")
        else:
            # 创建新仓库
            self.status_label.setText(f"正在创建仓库: {repo_name}")
            if not self.github_service.create_repo(repo_name):
                QMessageBox.critical(self.dialog, "错误", f"创建仓库 {repo_name} 失败")
                return
            
            branch_name = "main"
            self.status_label.setText(f"已创建仓库: {repo_name}")
        
        # 准备文件信息（展开文件夹）
        files_info = []
        
        # 先处理单独添加的文件和文件夹，分别处理以保持结构
        all_items = []
        
        for item in self.selected_files:
            if os.path.isdir(item):
                # 如果是文件夹，以该文件夹为基础路径
                folder_name = os.path.basename(item)
                for root, _, files in os.walk(item):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 计算相对于选中文件夹的路径
                        rel_path = os.path.relpath(file_path, item)
                        # 拼接文件夹名作为仓库中的路径
                        repo_path = os.path.join(folder_name, rel_path)
                        repo_path = repo_path.replace("\\", "/")
                        all_items.append((file_path, repo_path))
            else:
                # 如果是文件，直接放在仓库根目录
                repo_path = os.path.basename(item)
                repo_path = repo_path.replace("\\", "/")
                all_items.append((item, repo_path))
        
        if not all_items:
            QMessageBox.warning(self.dialog, "警告", "没有可上传的文件")
            return
        
        files_info = all_items
        
        # 开始后台上传
        self.start_upload(repo_name, files_info, branch_name)
    
    def start_upload(self, repo_name, files_info, branch_name):
        """启动后台上传"""
        self._dialog_closing = False
        # 禁用 UI
        self.set_ui_enabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        
        # 确定上传方式
        use_git = self.git_installed and (self.upload_method_combo.currentIndex() == 0)
        
        # 创建并启动上传线程
        self.upload_worker = UploadWorker(
            self.github_service,
            repo_name,
            files_info,
            branch_name,
            use_git
        )
        
        # 连接信号
        self.upload_worker.progress.connect(self.on_upload_progress)
        self.upload_worker.finished.connect(self.on_upload_finished)
        self.upload_worker.error.connect(self.on_upload_error)
        
        # 保存仓库名用于提示
        self._current_repo_name = repo_name
        self._current_branch_name = branch_name
        
        # 开始上传
        if use_git:
            self.status_label.setText("正在使用 Git 准备上传...")
        else:
            self.status_label.setText("正在准备上传...")
        self.upload_worker.start()
    
    def on_upload_progress(self, percentage, filename):
        """处理进度更新"""
        if not self._is_ui_alive():
            return
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"正在上传: {filename} ({percentage}%)")
    
    def on_upload_finished(self, success, result):
        """处理上传完成"""
        if not self._is_ui_alive():
            self._cleanup_worker()
            return
        self.set_ui_enabled(True)
        
        if success:
            self.status_label.setText(f"上传成功！共 {result['success']} 个文件")
            cmds.inViewMessage(
                message=f"GitHub 上传成功: {result['success']} 个文件到 {self._current_repo_name}/{self._current_branch_name}",
                pos='midCenter',
                fade=True
            )
            
            if result["failed"] > 0:
                msg = f"上传完成。成功: {result['success']}, 失败: {result['failed']}"
                QMessageBox.warning(self.dialog, "上传完成", msg)
                cmds.inViewMessage(message=msg, pos='midCenter', fade=True)
        else:
            self.status_label.setText("上传失败")
        
        # 隐藏进度条
        QTimer.singleShot(2000, self.hide_progress_bar)
        self._cleanup_worker()
    
    def on_upload_error(self, error_msg):
        """处理上传错误"""
        if not self._is_ui_alive():
            self._cleanup_worker()
            return
        self.set_ui_enabled(True)
        self.status_label.setText(f"上传出错: {error_msg}")
        QMessageBox.critical(self.dialog, "上传错误", f"上传过程中出错: {error_msg}")
        self.hide_progress_bar()
        self._cleanup_worker()
    
    def cancel_upload(self):
        """取消上传"""
        if self.upload_worker and hasattr(self.upload_worker, "isRunning") and self.upload_worker.isRunning():
            self.upload_worker.stop()
            if self._is_ui_alive():
                self.status_label.setText("正在取消...")
                self.cancel_btn.setEnabled(False)
    
    def hide_progress_bar(self):
        """隐藏进度条"""
        if not self._is_qt_object_alive(self.progress_bar):
            return
        self.progress_bar.setVisible(False)
    
    def set_ui_enabled(self, enabled):
        """设置 UI 是否可用"""
        if not self._is_ui_alive():
            return
        # 禁用/启用按钮
        self.upload_btn.setEnabled(enabled)
        self.cancel_btn.setVisible(not enabled)
        
        # 禁用/启用其他组件
        self.token_input.setEnabled(enabled)
        self.repo_combo.setEnabled(enabled)
        self.branch_combo.setEnabled(enabled)
        self.upload_mode_combo.setEnabled(enabled)
        self.upload_method_combo.setEnabled(enabled)
        self.file_list_widget.setEnabled(enabled)
        
        # 重新启用状态标签
        self.status_label.setEnabled(True)

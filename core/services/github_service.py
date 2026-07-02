# -*- coding: utf-8 -*-
"""
GitHub 同步服务
处理 GitHub API 交互、仓库管理、文件上传等功能
"""

import os
import sys
import subprocess
import json
import base64
from datetime import datetime
from pathlib import Path


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
if check_and_install_requests():
    import requests
else:
    raise ImportError("需要安装 requests 库才能使用 GitHub 同步功能")


def build_git_basic_auth_header(token):
    """构建 Git HTTPS 认证头，避免将 token 直接拼进 URL。"""
    credentials = f"x-access-token:{token}".encode("utf-8")
    encoded = base64.b64encode(credentials).decode("ascii")
    return f"AUTHORIZATION: basic {encoded}"


class GitHubService:
    """GitHub 同步服务"""
    
    def __init__(self, config_path=None):
        """
        初始化 GitHub 服务
        
        参数:
            config_path: GitHub 配置文件路径（可选）
        """
        print(f"[GitHubServiceDebug] 初始化 GitHubService，config_path={config_path}")
        
        # 如果没有提供 config_path，使用默认路径
        if config_path is None:
            try:
                import os
                script_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(os.path.dirname(script_dir))
                config_path = os.path.join(root_dir, "core", "utils", "configuration", "github_config.json")
                print(f"[GitHubServiceDebug] 使用默认 config_path: {config_path}")
            except Exception as e:
                print(f"[GitHubServiceDebug] 无法获取默认 config_path: {e}")
                # 使用当前目录作为备选
                config_path = "github_config.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.token = self.config.get("token", "")
        self.repo_owner = self.config.get("repo_owner", "")
        self.session = None
        self._init_session()
    
    def _load_config(self):
        """加载配置文件"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_config(self):
        """保存配置文件"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
    
    def _init_session(self):
        """初始化请求会话"""
        self.session = requests.Session()
        
        # 优化会话配置，提升性能
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=3
        )
        self.session.mount('https://', adapter)
        
        # 设置超时
        self.session.timeout = 30
        
        if self.token:
            self.session.headers.update({
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Maya-Scripts-Box"
            })
    
    def set_token(self, token):
        """
        设置 GitHub 访问令牌
        
        参数:
            token: GitHub Personal Access Token
        """
        self.token = token
        self.config["token"] = token
        self._init_session()
        self._save_config()
    
    def get_user_info(self):
        """
        获取用户信息（验证令牌有效性）
        
        返回:
            dict: 用户信息，失败返回 None
        """
        if not self.token:
            return None
        
        try:
            response = self.session.get("https://api.github.com/user")
            if response.status_code == 200:
                user_data = response.json()
                self.repo_owner = user_data.get("login", "")
                self.config["repo_owner"] = self.repo_owner
                self._save_config()
                return user_data
            return None
        except Exception as e:
            print(f"获取用户信息失败: {str(e)}")
            return None
    
    def list_repos(self):
        """
        获取用户的仓库列表
        
        返回:
            list: 仓库名称列表
        """
        if not self.token or not self.repo_owner:
            return []
        
        try:
            response = self.session.get(f"https://api.github.com/user/repos")
            if response.status_code == 200:
                repos = response.json()
                return [repo["name"] for repo in repos]
            return []
        except Exception as e:
            print(f"获取仓库列表失败: {str(e)}")
            return []
    
    def repo_exists(self, repo_name):
        """
        检查仓库是否存在
        
        参数:
            repo_name: 仓库名称
            
        返回:
            bool: 是否存在
        """
        if not self.token or not self.repo_owner:
            return False
        
        try:
            response = self.session.get(f"https://api.github.com/repos/{self.repo_owner}/{repo_name}")
            return response.status_code == 200
        except Exception as e:
            print(f"检查仓库失败: {str(e)}")
            return False
    
    def create_repo(self, repo_name, description="Maya scripts repository"):
        """
        创建新的公开仓库
        
        参数:
            repo_name: 仓库名称
            description: 仓库描述
            
        返回:
            bool: 是否成功
        """
        if not self.token or not self.repo_owner:
            return False
        
        try:
            data = {
                "name": repo_name,
                "description": description,
                "private": False,
                "auto_init": True
            }
            response = self.session.post("https://api.github.com/user/repos", json=data)
            return response.status_code in (201, 200)
        except Exception as e:
            print(f"创建仓库失败: {str(e)}")
            return False
    
    def list_branches(self, repo_name):
        """
        获取仓库的分支列表
        
        参数:
            repo_name: 仓库名称
            
        返回:
            list: 分支名称列表
        """
        if not self.token or not self.repo_owner:
            return []
        
        try:
            response = self.session.get(f"https://api.github.com/repos/{self.repo_owner}/{repo_name}/branches")
            if response.status_code == 200:
                branches = response.json()
                return [branch["name"] for branch in branches]
            return []
        except Exception as e:
            print(f"获取分支列表失败: {str(e)}")
            return []
    
    def get_default_branch(self, repo_name):
        """
        获取仓库的默认分支
        
        参数:
            repo_name: 仓库名称
            
        返回:
            str: 默认分支名称，失败返回 main
        """
        if not self.token or not self.repo_owner:
            return "main"
        
        try:
            response = self.session.get(f"https://api.github.com/repos/{self.repo_owner}/{repo_name}")
            if response.status_code == 200:
                repo_data = response.json()
                return repo_data.get("default_branch", "main")
            return "main"
        except Exception as e:
            print(f"获取默认分支失败: {str(e)}")
            return "main"
    
    def create_branch(self, repo_name, branch_name, from_branch=None):
        """
        创建新分支
        
        参数:
            repo_name: 仓库名称
            branch_name: 新分支名称
            from_branch: 源分支（默认使用默认分支）
            
        返回:
            bool: 是否成功
        """
        if not self.token or not self.repo_owner:
            return False
        
        if from_branch is None:
            from_branch = self.get_default_branch(repo_name)
        
        try:
            # 获取源分支的 SHA
            ref_response = self.session.get(
                f"https://api.github.com/repos/{self.repo_owner}/{repo_name}/git/ref/heads/{from_branch}"
            )
            if ref_response.status_code != 200:
                return False
            
            ref_data = ref_response.json()
            sha = ref_data["object"]["sha"]
            
            # 创建新分支
            data = {
                "ref": f"refs/heads/{branch_name}",
                "sha": sha
            }
            create_response = self.session.post(
                f"https://api.github.com/repos/{self.repo_owner}/{repo_name}/git/refs",
                json=data
            )
            return create_response.status_code in (201, 200)
        except Exception as e:
            print(f"创建分支失败: {str(e)}")
            return False
    
    def upload_file(self, repo_name, file_path, repo_path, branch="main", message=None):
        """
        上传文件到仓库
        
        参数:
            repo_name: 仓库名称
            file_path: 本地文件路径
            repo_path: 仓库中的路径
            branch: 分支名称
            message: 提交信息
            
        返回:
            bool: 是否成功
        """
        if not self.token or not self.repo_owner:
            return False
        
        try:
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Base64 编码
            content_b64 = base64.b64encode(content).decode('utf-8')
            
            # 准备提交信息
            if message is None:
                filename = os.path.basename(file_path)
                message = f"Add {filename}"
            
            # 检查文件是否已存在
            sha = None
            get_response = self.session.get(
                f"https://api.github.com/repos/{self.repo_owner}/{repo_name}/contents/{repo_path}",
                params={"ref": branch}
            )
            if get_response.status_code == 200:
                file_data = get_response.json()
                sha = file_data.get("sha")
            
            # 上传文件
            data = {
                "message": message,
                "content": content_b64,
                "branch": branch
            }
            if sha:
                data["sha"] = sha
            
            response = self.session.put(
                f"https://api.github.com/repos/{self.repo_owner}/{repo_name}/contents/{repo_path}",
                json=data
            )
            return response.status_code in (201, 200)
        except Exception as e:
            print(f"上传文件失败: {str(e)}")
            return False
    
    def upload_files(self, repo_name, files_info, branch="main"):
        """
        批量上传文件
        
        参数:
            repo_name: 仓库名称
            files_info: 文件信息列表，每个元素为 (本地路径, 仓库路径)
            branch: 分支名称
            
        返回:
            dict: {成功数量, 失败数量, 失败文件列表}
        """
        success = 0
        failed = 0
        failed_files = []
        
        date_str = datetime.now().strftime("%Y%m%d")
        commit_message = f"Update {date_str}"
        
        for local_path, repo_path in files_info:
            if self.upload_file(repo_name, local_path, repo_path, branch, commit_message):
                success += 1
            else:
                failed += 1
                failed_files.append(local_path)
        
        return {
            "success": success,
            "failed": failed,
            "failed_files": failed_files
        }
    
    def upload_files_with_git(self, repo_name, files_info, branch="main"):
        """
        使用 Git 命令批量上传文件（速度更快，适合中国用户）
        
        参数:
            repo_name: 仓库名称
            files_info: 文件信息列表，每个元素为 (本地路径, 仓库路径)
            branch: 分支名称
            
        返回:
            dict: {成功数量, 失败数量, 失败文件列表}
        """
        import tempfile
        import shutil
        
        success = 0
        failed = 0
        failed_files = []
        original_cwd = os.getcwd()
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="maya_scripts_sync_")
        
        try:
            # 检查 Git 是否可用
            try:
                subprocess.check_output(["git", "--version"], stderr=subprocess.STDOUT)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Git 不可用，回退到 API 上传方式")
                return self.upload_files(repo_name, files_info, branch)
            
            repo_url = f"https://github.com/{self.repo_owner}/{repo_name}.git"
            auth_header = build_git_basic_auth_header(self.token)
            
            # 首先确保仓库存在
            if not self.repo_exists(repo_name):
                print(f"仓库 {repo_name} 不存在，正在创建...")
                if not self.create_repo(repo_name):
                    print("创建仓库失败，回退到 API 上传方式")
                    return self.upload_files(repo_name, files_info, branch)
            
            # 克隆仓库
            print(f"正在克隆仓库: {repo_name}")
            repo_cloned = False
            try:
                self._run_git_command(
                    ["clone", "--depth", "1", "-b", branch, repo_url, temp_dir],
                    auth_header=auth_header
                )
                repo_cloned = True
            except subprocess.CalledProcessError:
                # 尝试用默认分支克隆
                try:
                    self._run_git_command(
                        ["clone", "--depth", "1", repo_url, temp_dir],
                        auth_header=auth_header
                    )
                    repo_cloned = True
                    # 切换到目标分支或创建新分支
                    os.chdir(temp_dir)
                    try:
                        subprocess.check_output(["git", "checkout", branch], stderr=subprocess.STDOUT)
                    except subprocess.CalledProcessError:
                        subprocess.check_output(["git", "checkout", "-b", branch], stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as exc:
                    print(f"克隆仓库失败: {self._format_git_error(exc)}")
                    print("回退到 API 方式")
                    return self.upload_files(repo_name, files_info, branch)
            
            if not repo_cloned:
                return self.upload_files(repo_name, files_info, branch)
            
            if repo_cloned and not os.getcwd() == temp_dir:
                os.chdir(temp_dir)
            
            # 复制文件
            for local_path, repo_path in files_info:
                try:
                    dest_path = os.path.join(temp_dir, repo_path)
                    dest_dir = os.path.dirname(dest_path)
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(local_path, dest_path)
                    success += 1
                    print(f"已添加文件: {repo_path}")
                except Exception as e:
                    failed += 1
                    failed_files.append(local_path)
                    print(f"添加文件失败: {local_path}, 错误: {e}")
            
            # 提交并推送
            try:
                date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                commit_msg = f"Update {date_str} from Maya Scripts Box"
                
                # 检查是否有变更
                status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                if not status_result.stdout.strip():
                    print("没有文件变更，跳过提交")
                else:
                    subprocess.check_output(["git", "add", "-A"], stderr=subprocess.STDOUT)
                    subprocess.check_output(["git", "config", "user.name", "Maya Scripts Box"], stderr=subprocess.STDOUT)
                    subprocess.check_output(["git", "config", "user.email", "maya@scripts.box"], stderr=subprocess.STDOUT)
                    subprocess.check_output(["git", "commit", "-m", commit_msg], stderr=subprocess.STDOUT)
                
                # 确保远程仓库正确
                try:
                    # 先检查是否已有 origin
                    remote_result = subprocess.run(["git", "remote"], capture_output=True, text=True)
                    if "origin" not in remote_result.stdout:
                        subprocess.check_output(["git", "remote", "add", "origin", repo_url], stderr=subprocess.STDOUT)
                    else:
                        # 更新远程 URL
                        subprocess.check_output(["git", "remote", "set-url", "origin", repo_url], stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError:
                    pass
                
                # 推送
                print("正在推送到 GitHub...")
                push_strategies = [
                    ("普通推送", ["push", "-u", "origin", branch]),
                    ("拉取后推送", lambda: self._pull_and_push(temp_dir, auth_header, branch)),
                    ("创建新分支", lambda: self._create_and_push_new_branch(temp_dir, auth_header, branch)),
                    ("强制推送", ["push", "-u", "-f", "origin", branch])
                ]
                
                push_success = False
                last_error = None
                
                for strategy_name, strategy in push_strategies:
                    try:
                        print(f"尝试策略: {strategy_name}")
                        if callable(strategy):
                            strategy()
                        else:
                            self._run_git_command(
                                strategy,
                                cwd=temp_dir,
                                auth_header=auth_header
                            )
                        push_success = True
                        print(f"策略 {strategy_name} 成功！")
                        break
                    except subprocess.CalledProcessError as exc:
                        last_error = exc
                        print(f"策略 {strategy_name} 失败: {self._format_git_error(exc)}")
                        continue
                
                if not push_success:
                    raise last_error or Exception("所有推送策略均失败")
                
                print("推送成功！")
                
            except subprocess.CalledProcessError as e:
                print(f"Git 操作失败: {self._format_git_error(e)}")
                # 回退到 API 方式
                print("回退到 API 上传方式...")
                return self.upload_files(repo_name, files_info, branch)
                
        except Exception as e:
            print(f"Git 上传方式失败: {e}")
            import traceback
            traceback.print_exc()
            # 回退到 API 方式
            print("回退到 API 上传方式...")
            return self.upload_files(repo_name, files_info, branch)
        finally:
            # 清理临时目录
            try:
                os.chdir(original_cwd)
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        
        return {
            "success": success,
            "failed": failed,
            "failed_files": failed_files
        }
    
    def _pull_and_push(self, temp_dir, auth_header, branch):
        """先拉取远程变更再推送"""
        print("正在拉取远程变更...")
        try:
            self._run_git_command(["pull", "--rebase", "origin", branch], cwd=temp_dir, auth_header=auth_header)
        except subprocess.CalledProcessError:
            print("拉取失败，尝试重置到远程分支状态...")
            self._run_git_command(["reset", "--hard", f"origin/{branch}"], cwd=temp_dir, auth_header=auth_header)
            # 重新应用我们的变更
            self._run_git_command(["cherry-pick", "HEAD"], cwd=temp_dir, auth_header=auth_header)
        
        print("拉取完成，正在推送...")
        self._run_git_command(["push", "-u", "origin", branch], cwd=temp_dir, auth_header=auth_header)
    
    def _create_and_push_new_branch(self, temp_dir, auth_header, base_branch):
        """
        创建新分支并推送，用于绕过分支保护规则
        """
        import datetime
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_branch = f"update-{date_str}"
        
        print(f"创建新分支: {new_branch}")
        self._run_git_command(["checkout", "-b", new_branch], cwd=temp_dir, auth_header=auth_header)
        self._run_git_command(["push", "-u", "origin", new_branch], cwd=temp_dir, auth_header=auth_header)
        print(f"新分支 {new_branch} 已推送，请在 GitHub 上创建 Pull Request 合并到 {base_branch}")

    def _run_git_command(self, args, cwd=None, auth_header=None):
        """运行带认证头的 Git 命令。"""
        command = ["git"]
        if auth_header:
            command.extend(["-c", f"http.extraheader={auth_header}"])
        command.extend(args)
        return subprocess.check_output(command, cwd=cwd, stderr=subprocess.STDOUT)

    def _format_git_error(self, error):
        """提取 Git 命令的标准输出，便于定位失败原因。"""
        output = getattr(error, "output", b"") or b""
        if isinstance(output, bytes):
            text = output.decode("utf-8", errors="ignore").strip()
        else:
            text = str(output).strip()
        return text or str(error)

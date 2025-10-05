from pathlib import Path
import os
from typing import Optional, Dict, List, Union  # 导入类型提示工具

class FileTool:
    """文件操作工具类
    
    提供安全的文件系统操作，限制在指定的根目录内，防止越权访问。
    支持目录切换、文件读写、目录创建等常用操作。
    """
    
    def __init__(self, root_path: str = '.'):
        """初始化文件工具
        
        Args:
            root_path: 根目录路径，所有操作将限制在该目录内
        """
        self.root_path: Path = Path(root_path).resolve()  # 解析为绝对路径
        self.current_dir: Path = self.root_path  # 当前工作目录，初始为根目录

    def _resolve_path(self, location: str) -> Optional[Path]:
        """解析路径并验证权限（内部方法）
        
        将输入路径解析为绝对路径，并确保它位于根目录范围内，
        防止访问根目录以外的内容。
        
        Args:
            location: 要解析的路径（相对路径或绝对路径）
            
        Returns:
            解析后的Path对象，如果超出根目录范围则返回None
        """
        # 将输入路径转换为Path对象
        target_path = Path(location)
        
        # 处理绝对路径：将其转换为相对于根目录的路径
        if target_path.is_absolute():
            # 去除绝对路径的根部分，与当前根目录拼接
            relative_part = target_path.relative_to(target_path.root)
            resolved_path = self.root_path / relative_part
        else:
            # 处理相对路径：基于当前工作目录解析
            resolved_path = self.current_dir / target_path
        
        # 确保解析后的路径在根目录范围内
        # 规范化路径，处理".."等情况
        resolved_path = resolved_path.resolve()
        
        # 检查是否在根目录范围内
        is_within_root = (self.root_path in resolved_path.parents 
                         or self.root_path.samefile(resolved_path))
        
        return resolved_path if is_within_root else None

    def get_directory_tree(self, directory: str) -> Dict[Path, str]:
        """获取目录树结构
        
        遍历指定目录及其所有子目录，返回所有文件和目录的结构。
        
        Args:
            directory: 要遍历的目录路径
            
        Returns:
            字典，键为相对于根目录的路径，值为该路径下的文件和目录列表
        """
        resolved_dir = self._resolve_path(directory)
        
        # 检查路径是否有效
        if resolved_dir is None:
            return {"error": "路径超出根目录范围"}
        
        if not resolved_dir.exists():
            return {"error": f"目录不存在: {directory}"}
            
        if not resolved_dir.is_dir():
            return {"error": f"{directory} 不是一个目录"}

        # 存储目录树结果
        tree_result = {}
        
        # 遍历目录
        for dirname, subdirs, files in os.walk(
            str(resolved_dir), 
            topdown=True, 
            followlinks=True
        ):
            # 计算相对于根目录的路径
            relative_path = Path(dirname).relative_to(self.root_path)
            
            # 格式化文件和目录列表
            file_list = "\n".join(files)
            dir_list = "\n".join([f"{d} (目录)" for d in subdirs])
            tree_result[relative_path] = f"{file_list}\n{dir_list}".strip()
            
        return tree_result

    def exists(self, path: str) -> str:
        """检查文件或目录是否存在
        
        Args:
            path: 要检查的文件或目录路径
            
        Returns:
            字符串说明，指示文件是否存在或访问被拒绝
        """
        resolved_path = self._resolve_path(path)
        
        if resolved_path is None:
            return "访问被拒绝：路径超出根目录范围"
            
        return "文件/目录存在" if resolved_path.exists() else "文件/目录不存在"

    def get_current_directory(self) -> str:
        """获取当前工作目录
        
        Returns:
            当前工作目录相对于根目录的路径字符串
        """
        relative_path = self.current_dir.relative_to(self.root_path)
        return f"/{relative_path}"

    def change_directory(self, location: str) -> str:
        """切换当前工作目录
        
        Args:
            location: 要切换到的目录路径
            
        Returns:
            切换结果说明
        """
        resolved_path = self._resolve_path(location)
        
        if resolved_path is None:
            return "访问被拒绝：路径超出根目录范围"
            
        if not resolved_path.exists():
            return f"切换失败：目录不存在 - {location}"
            
        if not resolved_path.is_dir():
            return f"切换失败：{location} 不是一个目录"
        
        # 更新当前工作目录
        self.current_dir = resolved_path
        return f"已切换到: {self.get_current_directory()}"

    def list_contents(self) -> Dict[str, str]:
        """列出当前目录下的所有内容
        
        Returns:
            包含文件列表和计数的字典
        """
        # 检查当前目录有效性
        if not self.current_dir.exists():
            return {"error": "当前目录不存在"}
            
        if not self.current_dir.is_dir():
            return {"error": "当前路径不是一个目录"}

        # 列出目录内容
        contents = []
        for item in os.listdir(str(self.current_dir)):
            item_path = self.current_dir / item
            item_type = "目录" if item_path.is_dir() else "文件"
            contents.append(f'"{item}" ({item_type})')

        return {
            "files": "\n".join(contents),
            "count": str(len(contents))
        }

    def make_directory(self, directory: str) -> str:
        """创建目录
        
        Args:
            directory: 要创建的目录路径
            
        Returns:
            创建结果说明
        """
        resolved_path = self._resolve_path(directory)
        
        if resolved_path is None:
            return "访问被拒绝：路径超出根目录范围"

        try:
            # 创建目录，包括必要的父目录，权限为0o700
            resolved_path.mkdir(
                mode=0o0700,
                parents=True,
                exist_ok=True  # 目录已存在时不报错
            )
            relative_path = resolved_path.relative_to(self.root_path)
            return f"已创建目录: {relative_path}"
        except Exception as e:
            relative_path = resolved_path.relative_to(self.root_path)
            return f"创建目录失败: {relative_path}，错误: {str(e)}"

    def write_file(self, file_path: str, content: str) -> str:
        """写入文件内容
        
        注意：会覆盖已有文件，请确保写入完整内容
        
        Args:
            file_path: 要写入的文件路径
            content: 要写入的文件内容
            
        Returns:
            写入结果说明
        """
        resolved_path = self._resolve_path(file_path)
        
        if resolved_path is None:
            return "访问被拒绝：路径超出根目录范围"

        try:
            # 确保父目录存在
            resolved_path.parent.mkdir(
                mode=0o0700,
                parents=True,
                exist_ok=True
            )
            
            # 编码为UTF-8字节并写入
            content_bytes = content.encode('utf-8')
            resolved_path.write_bytes(content_bytes)
            
            relative_path = resolved_path.relative_to(self.root_path)
            return f"已写入文件: {relative_path}\n大小: {len(content_bytes)} 字节"
        except Exception as e:
            return f"写入文件失败: {str(e)}"

    def read_file(self, file_path: str) -> Dict[str, str]:
        """读取文件内容
        
        Args:
            file_path: 要读取的文件路径
            
        Returns:
            包含读取状态、路径和内容的字典
        """
        resolved_path = self._resolve_path(file_path)
        
        # 计算相对路径用于返回信息
        if resolved_path:
            relative_path = f"/{resolved_path.relative_to(self.root_path)}"
        else:
            relative_path = file_path

        # 检查路径有效性
        if resolved_path is None:
            return {
                'state': 'error',
                'reason': "访问被拒绝：路径超出根目录范围",
                'path': relative_path
            }
            
        if resolved_path.is_dir():
            return {
                'state': 'error',
                'reason': "无法读取目录内容",
                'path': relative_path
            }
            
        if not resolved_path.exists():
            return {
                'state': 'error',
                'reason': "文件不存在",
                'path': relative_path
            }

        try:
            # 读取文件内容（UTF-8编码）
            content = resolved_path.read_text(encoding='utf-8')
            return {
                'state': 'ok',
                'path': relative_path,
                'file_content': content
            }
        except Exception as e:
            return {
                'state': 'error',
                'path': relative_path,
                'reason': f"读取文件失败: {str(e)}"
            }

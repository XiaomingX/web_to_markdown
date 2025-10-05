import os.path
from typing import Optional
import codecs

# 导入相关模块
from .filetool import FileTool  # 用于文件操作的工具类
from .. import Agent, Config, Identity  # 代理、配置和身份相关类


class CodeBase:
    """代码库管理类
    
    用于分析代码文件、存储并管理文件的解释信息，提供查询功能。
    支持通过文件工具读取文件或直接读取本地文件，通过代理(Agent)分析代码内容。
    """
    
    def __init__(self, 
                 file_tool: Optional[FileTool] = None, 
                 override_agent_config: Optional[Config] = None):
        """初始化CodeBase实例
        
        参数:
            file_tool: 可选的文件工具实例，用于读取文件（若为None则直接读取本地文件）
            override_agent_config: 可选的代理配置，用于覆盖默认的Agent配置
        """
        # 存储代码文件及其解释的字典，键为文件名，值为包含解释的字典
        self.codebase = {}
        # 保存文件工具实例
        self.file_tool = file_tool
        # 保存代理配置
        self.override_agent_config = override_agent_config

    def list(self):
        """列出所有已分析的文件
        
        返回:
            字典，包含一个'files'键，其值为所有已分析文件的文件名列表
        """
        return {'files': list(self.codebase.keys())}

    def get_explanation(self, file_name: str):
        """获取指定文件的代码解释
        
        参数:
            file_name: 要查询的文件名
        
        返回:
            若文件已分析，则返回包含文件信息和解释的字典；否则返回None
        """
        # 检查文件是否在代码库中
        if file_name not in self.codebase:
            return None
        return self.codebase[file_name]

    def analyze_and_add(self, file_name: str):
        """分析指定文件并将其解释添加到代码库
        
        步骤:
        1. 规范化文件名（处理路径格式）
        2. 若文件已分析，则直接返回已有解释
        3. 读取文件内容（通过file_tool或直接读取本地文件）
        4. 格式化文件内容（添加行号标记）
        5. 创建代码分析代理，获取分析结果
        6. 存储分析结果并返回
        
        参数:
            file_name: 要分析的文件名
        
        返回:
            包含文件信息和分析解释的字典；若读取文件失败，返回包含错误信息的字典
        """
        # 规范化文件名，处理不同操作系统的路径格式差异
        file_name = os.path.normpath(file_name)
        
        # 若文件已在代码库中，直接返回已有解释
        if file_name in self.codebase:
            return self.codebase[file_name]

        # 读取文件内容
        try:
            if self.file_tool is None:
                # 无file_tool时，直接读取本地文件（使用utf-8编码）
                with codecs.open(file_name, 'r', 'utf-8') as f:
                    lines = f.readlines()
            else:
                # 使用file_tool读取文件
                file_obj = self.file_tool._resolve(file_name)
                if file_obj is None:
                    # 文件无法访问时返回错误信息
                    return {'ok': False, 'error': '文件访问被拒绝！'}
                # 读取文件内容并按行分割
                lines = file_obj.read_text(encoding='utf-8').split('\n')
        except Exception as e:
            return {'ok': False, 'error': f'读取文件失败: {str(e)}'}

        # 为每一行添加行号标记（格式：#L0001>行内容）
        formatted_lines = [f"#L%04d>%s" % (i, line) for i, line in enumerate(lines)]

        # 创建代码分析代理
        analyzer_agent = Agent(
            config=self.override_agent_config,
            identity=Identity(
                name="代码分析器",
                peer="代码库管理器",
                purpose="分析给定的代码并生成该文件功能的简短报告。"
            )
        )

        # 发送格式化的代码内容给代理，获取分析结果
        analysis_result = analyzer_agent.chat("\n".join(formatted_lines))

        # 整理分析结果数据
        file_data = {
            'file': file_name,
            'explanation': analysis_result,
        }

        # 将结果存入代码库并返回
        self.codebase[file_name] = file_data
        return file_data
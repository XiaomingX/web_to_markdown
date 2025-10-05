# 导入核心Agent类和身份标识类
from coreagent import Agent, Identity

# 尝试导入网页转markdown的工具（依赖selenium）
try:
    # 从当前包导入网页转markdown功能
    from .selenium_browser import web_to_markdown
    # 标记web功能可用
    _toolgen_web_support = True
    print("[ToolGen] Selenium已找到并加载。")
except:
    # 若导入失败，标记web功能不可用并提示
    print("未找到Selenium，ToolGen将无法浏览网页。")
    _toolgen_web_support = False


class ToolGen:
    """工具生成器类，用于根据需求生成Python工具类并安装到Agent中"""
    
    def __init__(self, agent: Agent):
        """
        初始化ToolGen实例
        
        参数:
            agent: 关联的Agent实例，工具将被安装到该Agent中
        """
        self.agent: Agent = agent  # 保存关联的Agent引用

    def generate_tool(self, requirements: str, web_links: str, should_auto_install_as_tool_name: str):
        """
        根据需求生成工具类代码，支持从网页获取文档
        
        参数:
            requirements: 工具需求描述（例如："实现一个读取文件的工具"）
            web_links: 用于获取文档的URL，多个URL用换行符('\n')分隔
            should_auto_install_as_tool_name: 
                若不为空字符串，生成后自动安装为指定名称的工具（不返回代码）
                若为空字符串，仅返回生成的工具代码
        
        返回:
            生成的工具代码（字符串）或安装结果（字典）
        """
        # 处理网页链接（若提供）
        if web_links.strip() != "":
            # 检查web功能是否可用
            if not _toolgen_web_support:
                return {
                    'ok': 'no', 
                    'error': "不支持网页浏览，请清空'web_links'参数，并在'requirements'中提供所有信息。"
                }
            
            # 存储每个链接的文档内容
            documentations = {}
            # 遍历每个链接并获取文档
            for link in web_links.split("\n"):
                if link.strip() != "":  # 跳过空链接
                    # 调用网页转markdown工具，获取文档内容
                    documentations[link] = web_to_markdown(
                        self.agent.config.llm, 
                        self.agent.config.model, 
                        link
                    )
            
            # 将所有文档组合成字符串（格式：链接 + markdown内容）
            documentations_combined = "\n".join([
                f"{link}\n```markdown\n{md}\n```\n" 
                for link, md in documentations.items()
            ])
            
            # 将网页文档添加到需求描述中
            requirements += f"\n\n从互联网获取的信息\n========\n{documentations_combined}"

        # 创建一个临时Agent，用于生成工具代码
        tool_writer_agent = Agent(
            Identity(
                name="工具编写者",
                peer="ISYS工具管理系统",
                purpose="""
                你的任务是输出专业的Python代码作为响应。
                代码必须包含一个名为GeneratedTool的单一类。
                
                该类的每个成员方法都是一个工具，共享GeneratedTool实例的状态。
                每个工具方法应返回字符串或字符串字典。
                每个方法必须有YAML格式的文档字符串：
                    - 以"#"开头的行作为工具描述
                    - 其他条目为参数说明
                
                工具类示例：
                from pathlib import Path 
                class GeneratedTool:
                    def __init__(self):
                        self.counter: int = 0  # 共享状态变量
                    
                    def get_file(self, str_path: str) -> str|typing.Dict[str, str]:
                        \"\"\"
                        # 读取指定路径文件的内容
                        str_path: "文件的路径字符串"
                        \"\"\"
                        return {'ok': 'yes', 'content': Path(str_path).read_text()}
                    
                    def get_counter(self) -> str:
                        \"\"\"
                        # 获取当前计数器的值
                        \"\"\"
                        return f"当前计数器: {self.counter}"
                    
                    def increase_counter(self) -> str:
                        \"\"\"
                        # 将计数器加1
                        \"\"\"
                        self.counter += 1
                        return "操作完成！"
                """,
                # 响应格式约束：必须是Python代码块
                respond_gbnf="""
                respond-format ::= "```python\\n" (text-line)+ "```"
                """
            ),
            self.agent.config  # 复用主Agent的配置
        )

        # 向临时Agent发送请求，生成工具代码
        generated_code = tool_writer_agent.chat(f"请编写一个工具类实现以下需求：\n{requirements}")

        # 决定是自动安装还是返回代码
        if should_auto_install_as_tool_name.strip() != '':
            return self.install_tool(should_auto_install_as_tool_name.strip(), generated_code)
        else:
            return generated_code

    def install_tool(self, instance_name: str, tool_code: str):
        """
        将生成的工具代码安装到Agent中
        
        参数:
            instance_name: 工具实例名称（例如："file_tool_1"）
            tool_code: 工具源代码（必须包含GeneratedTool类，不能有```标记）
        
        返回:
            安装结果字典（包含'ok'状态和消息/错误信息）
        """
        # 校验工具代码合法性
        if 'GeneratedTool' not in tool_code:
            return {'ok': 'no', 'error': "工具源代码必须包含GeneratedTool类。"}
        
        if instance_name in self.agent.tools:
            return {'ok': 'no', 'error': "工具实例名称已存在，请选择其他名称。"}
        
        if '```' in tool_code:
            return {'ok': 'no', 'error': "工具源代码不能包含```等代码块标记。"}

        # 危险操作：执行用户提供的代码前必须确认
        print("=====================")
        print("即将执行的工具代码：")
        print(tool_code)
        print("=====================")
        
        # 获取用户确认
        user_confirm = input("确认执行以上代码？输入YES继续，其他键取消：")
        if user_confirm != "YES":
            return {'ok': 'no', 'error': "系统拒绝访问，代码未执行。"}
        
        print("=====================")

        # 执行工具代码并获取类定义
        execution_scope = {}
        try:
            # 在隔离的作用域中执行代码
            exec(tool_code, execution_scope)
        except Exception as e:
            return {'ok': 'no', 'error': f'代码执行错误：\n{e}'}

        # 再次校验GeneratedTool是否存在
        if 'GeneratedTool' not in execution_scope:
            return {'ok': 'no', 'error': "工具源代码必须包含GeneratedTool类。"}

        # 实例化工具类并注册到Agent
        registered_method_names = self.agent.register_tool(
            execution_scope['GeneratedTool'](),  # 创建工具实例
            instance_name  # 工具实例名称
        )

        # 返回成功信息
        return {
            'ok': 'yes', 
            'message': f'工具安装成功，包含以下方法：\n' + "\n".join(registered_method_names)
        }
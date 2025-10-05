import subprocess

class SafeShellExecutor:
    """
    安全的Shell命令执行工具
    
    功能：执行用户提供的Shell命令，但会先进行安全检查
    安全限制：禁止执行任何可能删除文件或目录的命令（如rm、del等）
    操作流程：
    1. 检查命令是否为空
    2. 验证命令是否属于禁止执行的危险命令
    3. 请求用户确认是否执行该命令
    4. 仅在用户确认后执行命令并返回结果
    """
    
    def execute_command(self, command: str) -> str:
        """
        执行Shell命令（包含安全检查和用户确认）
        
        参数:
            command: 要执行的Shell命令字符串
            
        返回:
            命令执行成功后的标准输出(stdout)字符串
            
        异常:
            ValueError: 当提供的命令为空时抛出
            PermissionError: 当命令是被禁止的危险命令时抛出
            InterruptedError: 当用户取消执行命令时抛出
            subprocess.CalledProcessError: 当命令执行失败（返回非0状态码）时抛出
            FileNotFoundError: 当命令不存在或无法找到时抛出
            RuntimeError: 当获取用户输入时发生错误（如输入流关闭）时抛出
        """
        # 定义禁止执行的危险命令（主要是删除相关命令）
        # 这些命令可能导致文件或目录被删除，存在安全风险
        FORBIDDEN_COMMANDS = ['rm', 'del', 'rd', 'rmdir']
        
        # 清理命令字符串（去除首尾空白字符）
        stripped_command = command.strip()
        
        # 检查命令是否为空
        if not stripped_command:
            error_msg = "错误：提供的命令为空！"
            print(error_msg)
            raise ValueError(error_msg)
        
        # 解析命令的第一个部分（判断是否为危险命令）
        # 拆分命令并取第一个部分（忽略大小写）
        command_components = stripped_command.split()
        first_command_part = command_components[0].lower()
        
        # 检查是否为禁止执行的命令
        if first_command_part in FORBIDDEN_COMMANDS:
            error_msg = f"错误：禁止执行危险命令 '{first_command_part}'！"
            print(error_msg)
            raise PermissionError(error_msg)
        
        # 显示命令信息并请求用户确认
        print("-" * 40)
        print("即将执行以下命令：")
        print(f"  '{stripped_command}'")
        print("-" * 40)
        
        # 获取用户确认（处理可能的输入流关闭错误）
        try:
            user_confirm = input("确定要执行这个命令吗？(yes/no): ").lower().strip()
        except EOFError:
            error_msg = "\n错误：输入流已关闭，无法获取用户确认。"
            print(error_msg)
            raise RuntimeError(error_msg)
        
        # 如果用户未确认，取消执行
        if user_confirm not in ['yes', 'y']:
            print("命令执行已被用户取消。")
            raise InterruptedError("命令执行被用户取消")
        
        # 执行用户确认后的命令
        print(f"\n用户已确认，正在执行命令：{stripped_command}")
        try:
            # 执行命令并捕获输出
            # shell=True：允许执行shell命令
            # capture_output=True：捕获标准输出和错误
            # text=True：返回字符串类型结果（而非字节）
            # check=True：当命令返回非0状态码时抛出异常
            result = subprocess.run(
                stripped_command,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                errors='replace'
            )
            
            print("命令执行成功。")
            return result.stdout
        
        # 处理命令执行失败的情况（返回非0状态码）
        except subprocess.CalledProcessError as e:
            error_msg = f"命令执行失败: '{stripped_command}'"
            print(error_msg)
            print(f"返回状态码: {e.returncode}")
            print(f"错误输出: {e.stderr}")
            raise e
        
        # 处理命令不存在的情况
        except FileNotFoundError:
            error_msg = f"错误：找不到命令 '{command_components[0]}'"
            print(error_msg)
            raise FileNotFoundError(error_msg)
        
        # 处理其他未预料到的错误
        except Exception as e:
            error_msg = f"执行命令时发生意外错误: {str(e)}"
            print(error_msg)
            raise e

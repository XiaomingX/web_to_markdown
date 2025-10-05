import mysql.connector
from mysql.connector.cursor import CursorBase


class MySQLTool:
    """
    MySQL数据库操作工具类
    
    提供数据库连接管理、SQL语句执行和结果格式化功能，
    简化MySQL数据库的基本操作流程。
    """
    
    def __init__(self, host: str, user: str, password: str, database: str):
        """
        初始化数据库连接
        
        参数:
            host: 数据库主机地址
            user: 数据库登录用户名
            password: 数据库登录密码
            database: 要连接的数据库名称
        """
        self.connection = None  # 数据库连接对象
        try:
            # 建立数据库连接，指定UTF-8编码排序规则
            self.connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                collation='utf8mb4_general_ci',
            )
            print("数据库连接成功")
        except mysql.connector.Error as err:
            print(f"数据库连接失败: {err}")
            self.connection = None

    def execute(self, sql_query: str) -> dict:
        """
        执行SQL查询并返回格式化结果
        
        参数:
            sql_query: 要执行的SQL语句字符串
            
        返回:
            字典类型结果:
                - 成功时: {'query': 执行的SQL, 'results': 格式化结果, 'count': 影响行数}
                - 失败时: {'ok': False, 'error': 错误信息}
        """
        # 检查连接状态
        if not self.connection or not self.connection.is_connected():
            return {'ok': False, 'error': '未建立数据库连接或连接已断开'}

        cursor = None  # 数据库游标对象
        try:
            # 创建游标对象，buffered=True确保能读取所有结果
            cursor: CursorBase = self.connection.cursor(buffered=True)
            cursor.execute(sql_query)

            # 处理查询结果（SELECT类语句会有返回结果）
            if cursor.description:  # cursor.description不为空表示有查询结果
                # 获取所有行数据
                results = cursor.fetchall()
                # 提取列名
                column_names = [column[0] for column in cursor.description]
                
                # 格式化结果为表格形式
                # 1. 格式化每行数据为"值1|值2|值3"形式
                formatted_rows = "\n".join([
                    "|".join(map(str, row)) for row in results
                ])
                # 2. 生成表头
                header = " | ".join(column_names)
                # 3. 生成表头分隔线（每个列名长度的横线）
                separator = "-|-".join(['-' * len(col) for col in column_names])
                # 4. 组合完整结果
                formatted_results = f"{header}\n{separator}\n{formatted_rows}"
            else:  # 非查询语句（如INSERT/UPDATE/DELETE）无返回结果
                formatted_results = "(无返回行)"

            # 准备返回数据
            return {
                'query': sql_query,
                'results': formatted_results,
                'count': cursor.rowcount  # 受影响的行数
            }

        except mysql.connector.Error as err:
            return {'ok': False, 'error': f"SQL执行错误: {err}"}
        finally:
            # 确保游标被关闭（避免资源泄露）
            if cursor:
                cursor.close()
                # 注意：此处不关闭连接，以便工具实例可执行多次查询
                # 连接关闭应由用户在工具不再使用时调用close_connection()

    def close_connection(self) -> None:
        """关闭数据库连接
        
        当工具类实例不再使用时，应调用此方法释放数据库连接资源
        """
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("数据库连接已关闭")

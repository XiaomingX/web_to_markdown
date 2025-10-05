import os
import sys
from openai import Client as OpenAIClient, OpenAIError
from selenium.webdriver.common.by import By
from seleniumbase import SB
from seleniumbase.common.exceptions import WebDriverException


def web_to_markdown(openai_client: OpenAIClient, model_name: str, webpage_url: str) -> str:
    """
    将指定网页内容转换为Markdown格式
    
    参数:
        openai_client: OpenAI客户端实例，用于调用转换API
        model_name: 要使用的OpenAI模型名称（如gpt-4）
        webpage_url: 需要转换的网页URL
        
    返回:
        转换后的Markdown文本
    """
    # 使用SeleniumBase打开网页并提取内容
    # uc=True: 启用undetected_chromedriver，避免被网站检测为自动化工具
    # incognito=True: 使用无痕模式浏览
    try:
        with SB(uc=True, incognito=True) as browser:
            # 打开目标网页
            browser.get(webpage_url)
            # 定位网页的body标签（包含所有可见内容）
            body_element = browser.find_element(By.TAG_NAME, "body")
            # 提取body中的纯文本内容
            page_text = body_element.text
            print(f"成功提取 {webpage_url} 的网页内容")
    except WebDriverException as e:
        raise RuntimeError(f"网页访问或内容提取失败: {str(e)}")

    # 调用OpenAI API将提取的文本转换为Markdown
    try:
        api_response = openai_client.chat.completions.create(
            model=model_name,  # 指定使用的模型
            messages=[
                # 系统提示：告诉AI它的角色和任务
                {
                    "role": "system",
                    "content": (
                        "你是一个文本转Markdown的转换器。输入是从网页爬取的纯文本，"
                        "你的任务是将其转换为结构清晰的Markdown格式。输出直接是Markdown内容，"
                        "不需要包裹在Markdown代码块中，但如果原网页有代码，你可以在输出中使用代码块。"
                    )
                },
                # 用户输入：网页提取的文本
                {"role": "user", "content": page_text}
            ],
            temperature=0.6,  # 控制输出随机性（0-1），值越低越确定
            top_p=0.9,  # 控制token选择的累积概率，0.9表示选择概率和为90%的最可能token
            max_tokens=8192,  # 最大输出token数
        )
        print(f"成功使用 {model_name} 模型完成Markdown转换")
        return api_response.choices[0].message.content
    except OpenAIError as e:
        raise RuntimeError(f"OpenAI API调用失败: {str(e)}")


class SeleniumBrowser:
    """
    网页浏览与Markdown转换工具类
    封装了网页内容获取和通过OpenAI转换为Markdown的功能
    """
    
    def __init__(self, openai_client: OpenAIClient, llm_model: str):
        """
        初始化浏览器工具
        
        参数:
            openai_client: OpenAI客户端实例
            llm_model: 要使用的大语言模型名称
        """
        self.openai_client = openai_client  # 保存OpenAI客户端
        self.llm_model = llm_model  # 保存要使用的模型名称

    def browse_web_get_markdown(self, url: str) -> dict:
        """
        打开指定URL的网页，并将其内容转换为结构化Markdown格式
        
        参数:
            url: 要访问的网页URL
            
        返回:
            包含原始URL和转换后Markdown的字典，格式: {"url": url, "markdown": 转换结果}
        """
        # 调用转换函数，并返回包含URL和结果的字典
        return {
            'url': url,
            'markdown': web_to_markdown(self.openai_client, self.llm_model, url)
        }


def main():
    """
    程序主函数：处理命令行参数，执行网页转Markdown操作
    用法: python web_to_markdown.py <网页URL> [模型名称]
    示例: python web_to_markdown.py https://example.com gpt-3.5-turbo
    """
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python web_to_markdown.py <网页URL> [模型名称，可选，默认gpt-3.5-turbo]")
        sys.exit(1)

    # 获取命令行参数
    target_url = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "gpt-3.5-turbo"

    # 从环境变量获取OpenAI API密钥
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("错误: 未找到OPENAI_API_KEY环境变量，请先设置")
        sys.exit(1)

    try:
        # 初始化OpenAI客户端
        openai_client = OpenAIClient(api_key=openai_api_key)
        
        # 创建浏览器工具实例
        browser = SeleniumBrowser(openai_client, model_name)
        
        # 执行网页浏览和转换
        result = browser.browse_web_get_markdown(target_url)
        
        # 输出结果（可以根据需要保存到文件）
        print("\n转换后的Markdown内容:\n")
        print(result["markdown"])
        
        # 可选：将结果保存到文件
        filename = f"output_{target_url.split('//')[-1].replace('/', '_')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result["markdown"])
        print(f"\nMarkdown内容已保存到 {filename}")
        
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        sys.exit(1)


# 当直接运行脚本时执行main函数
if __name__ == "__main__":
    main()

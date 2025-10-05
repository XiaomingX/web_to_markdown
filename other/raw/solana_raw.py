# 加密货币数据监控机器人
# 功能：从Dexscreener爬取Solana链上代币数据，分析安全性，
#       通过Telegram机器人发送符合条件的代币信息，并响应用户命令

# 标准库导入
from dataclasses import replace
from os import getenv
from pathlib import Path
from threading import Thread
from time import sleep

# 第三方库导入
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from seleniumbase import SB  # SeleniumBase用于网页自动化爬取
from telebot import TeleBot  # 用于创建Telegram机器人

# 本地模块导入
from birdeye import check_security_risks, should_post_token  # 安全风险检查相关
from gemini.assistant import CryptoAIProcessor  # Gemini AI处理相关
from models import PairData  # 代币对数据模型
from utils import (  # 工具函数
    transform_token, string_to_number, as_number, get_solana_address, 
    to_minutes, wait_for_url_change, calculate_token_score, 
    format_telegram_message, handle_command
)

# 加载环境变量配置
# 从项目根目录的.env文件中读取配置信息
dotenv_path = Path(r"..\..\.env")
load_dotenv(dotenv_path=dotenv_path)

# 从环境变量获取关键配置
BOT_TOKEN = getenv("BOT_TOKEN")  # Telegram机器人令牌
channel_id = getenv("CHANNEL_ID")  # 要发送消息的Telegram频道ID
user_data_dir = getenv("USER_DATA_DIR")  # 用户数据目录（Selenium使用）
gemini_api_key = getenv("GEMINI_API_KEY")  # Gemini AI的API密钥

# 初始化核心组件
bot = TeleBot(BOT_TOKEN)  # 创建Telegram机器人实例
crypto_ai = CryptoAIProcessor(  # 初始化AI处理器
    model_name="models/gemini-2.0-flash-thinking-exp-01-21",
    api_key=gemini_api_key,
    database_path="data/crypto_pairs.csv"  # 存储代币数据的CSV文件路径
)

# 常量定义
MAX_ON_PAGE = 100  # 每页最多处理的代币对数量


def scrape_dexscreener_data(sb, url="https://dexscreener.com/solana?rankBy=pairAge&order=asc&minLiq=2000&minAge=3"):
    """
    从Dexscreener网站爬取Solana链上的代币对数据
    
    参数:
        sb: SeleniumBase实例，用于网页操作
        url: 要爬取的Dexscreener页面URL，默认筛选条件为：
             按代币对年龄排序、升序、最低流动性2000、最低年龄3
    
    返回:
        包含PairData对象的集合，每个对象代表一个代币对的详细数据
    """
    # 访问目标网页
    sb.driver.get(url)
    # 等待页面加载完成（URL中包含"solana"）
    wait_for_url_change(sb, "solana", timeout=10)

    # 存储爬取的代币对数据（使用set避免重复）
    pairs_data = set()
    
    # 循环处理页面上的代币对（此处临时限制为3个用于测试，可修改）
    for i in range(MAX_ON_PAGE):
        if i == 3:  # 临时调试用，实际使用时可删除此条件
            break
            
        print(f"处理第 {i + 1}/{MAX_ON_PAGE} 个代币对")
        try:
            # 获取当前代币对的行元素
            pair = sb.find_elements("a.ds-dex-table-row")[i]
            # 获取行中的所有数据单元格
            columns = pair.find_elements(By.CSS_SELECTOR, "div.ds-table-data-cell")

            # 检查数据是否完整（至少需要13个字段）
            if not columns or len(columns) < 13:
                continue

            # 解析代币名称和描述
            token, description = transform_token(columns[0].text)
            
            # 构建代币对数据对象（字段对应Dexscreener表格列）
            pair_data = PairData(
                token=token,  # 代币名称
                description=description,  # 代币描述
                address=get_solana_address(pair.get_attribute("href")),  # 从链接中提取Solana地址
                price=string_to_number(columns[1].text),  # 价格
                age=to_minutes(columns[2].text),  # 存在时间（转换为分钟）
                buys=as_number(columns[3].text),  # 买入次数
                sells=as_number(columns[4].text),  # 卖出次数
                volume=string_to_number(columns[5].text),  # 交易量
                makers=as_number(columns[6].text),  # 做市商数量
                # 价格变化百分比（处理可能的空值）
                five_min_change=string_to_number(columns[7].text) if len(columns[7].text) > 1 else None,
                one_hour_change=string_to_number(columns[8].text) if len(columns[8].text) > 1 else None,
                six_hour_change=string_to_number(columns[9].text) if len(columns[9].text) > 1 else None,
                twenty_four_hour_change=string_to_number(columns[10].text) if len(columns[10].text) > 1 else None,
                liquidity=string_to_number(columns[11].text),  # 流动性
                market_cap=string_to_number(columns[12].text),  # 市值
            )
            pairs_data.add(pair_data)
            
        except (ValueError, IndexError) as e:
            print(f"处理代币对时出错: {e}")
            continue  # 出错时跳过当前代币对，继续处理下一个

    return pairs_data


def main():
    """主函数：执行一次完整的爬取、分析和发送流程"""
    # 初始化SeleniumBase浏览器实例（uc模式模拟真实浏览器，非无头模式便于调试）
    with SB(uc=True, headless=False) as sb:
        try:
            # 1. 爬取Dexscreener数据
            pairs_data = scrape_dexscreener_data(sb)

            # 2. 保存爬取的代币数据到CSV
            crypto_ai.save_pair_data(pairs_data)

            # 3. 逐个分析代币并发送符合条件的到Telegram
            for pair_data in pairs_data:
                # 检查代币安全性风险
                security_data = check_security_risks(sb, pair_data.token)
                # 计算代币评分
                score = calculate_token_score(security_data)
                # 更新代币数据中的安全信息
                pair_data = replace(pair_data, security=replace(security_data, score=score))

                # 如果代币符合发布条件，则发送到Telegram频道
                if should_post_token(pair_data.security):
                    msg = format_telegram_message(pair_data)  # 格式化消息
                    bot.send_message(channel_id, msg, parse_mode="HTML")  # 发送消息
                    
        finally:
            # 无论是否出错，都会执行的清理操作（目前为空）
            pass


@bot.message_handler(commands=["start", "help", "info", "trends", "support"])
def handle_commands(message):
    """
    处理Telegram机器人的命令消息
    
    支持的命令：/start, /help, /info, /trends, /support
    功能：通过AI助手生成命令响应并回复用户
    """
    # 提取命令（去除开头的"/"）
    command = message.text[1:]
    # 获取命令响应
    response = handle_command(command)
    # 发送响应给用户（使用HTML格式解析）
    bot.send_message(message.chat.id, response, parse_mode="HTML")


@bot.message_handler()
def handle_messages(message):
    """
    处理用户的普通文本消息
    
    功能：通过AI助手进行两阶段处理（技术分析和用户友好响应）
    """
    # 处理消息，获取技术分析结果和用户响应
    technical_output, user_response = crypto_ai.process_message(message.text)

    # 如果生成了用户响应，则回复用户
    if user_response:
        bot.reply_to(message, user_response)


def main_loop():
    """循环执行主函数，按固定间隔重复爬取和发送流程"""
    while True:
        print("开始新一轮数据爬取和发送...")
        main()  # 执行一次完整流程
        print("本轮处理完成，等待下一轮...")
        sleep(30 * 60)  # 等待30分钟（30*60秒）


if __name__ == "__main__":
    """程序入口：启动机器人和后台爬取线程"""
    print("启动数据爬取和发送机器人...")

    # 启动后台爬取线程（daemon=True表示主线程退出时自动结束）
    channel_thread = Thread(target=main_loop, daemon=True)
    channel_thread.start()

    print("机器人已在后台运行。按Ctrl+C停止。")
    try:
        # 启动Telegram机器人的消息监听
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        # 处理用户中断（Ctrl+C）
        print("正在停止机器人...")
        bot.stop_polling()
        print("机器人已停止。")

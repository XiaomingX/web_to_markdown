# 股票信息查询应用
# 注意：使用此代码会产生OpenAI API费用
# 若不想产生费用，请更换为其他LLM模型

# ----------------------------
# 导入所需库（按功能分组）
# ----------------------------
# Web应用框架
import streamlit as st
# 数据处理
import pandas as pd
# 图像处理
from PIL import Image
# 股票数据获取
import yfinance as yf
from yahooquery import Ticker
# 日期处理
from datetime import datetime, timedelta
# EDGAR数据库（美国SEC filings）
from edgar import Company, TXTML
# 环境变量管理
from dotenv import load_dotenv
import os
# LangChain相关（用于AI问答和文档处理）
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter, PythonCodeTextSplitter


# ----------------------------
# 初始化配置
# ----------------------------
# 加载环境变量（包含API密钥等敏感信息）
load_dotenv()
# 获取OpenAI API密钥
openai_api_key = os.getenv("OPENAI_API_KEY")


# ----------------------------
# 工具函数
# ----------------------------
def format_large_number(num):
    """
    将大额数字格式化为易读形式（万亿、十亿、百万等）
    
    参数:
        num: 需要格式化的数字
        
    返回:
        格式化后的字符串（如"$1.23B"表示12.3亿美元）
    """
    if abs(num) >= 1_000_000_000_000:  # 万亿级别
        return f"${num / 1_000_000_000_000:.2f}T"
    elif abs(num) >= 1_000_000_000:  # 十亿级别
        return f"${num / 1_000_000_000:.2f}B"
    elif abs(num) >= 1_000_000:  # 百万级别
        return f"${num / 1_000_000:.2f}M"
    else:  # 其他较小数字
        return str(num)


# ----------------------------
# 股票数据字典
# 包含支持查询的股票信息：公司名称、股票代码、SEC的CIK编号（用于获取财报）
# ----------------------------
stocks = {
    "Apple - 'AAPL'": {
        "name": "APPLE INC", 
        "symbol": "AAPL", 
        "cik": "0000320193"  # CIK: 美国SEC分配的公司唯一标识
    },
    "Alphabet - 'GOOG'": {
        "name": "Alphabet Inc.", 
        "symbol": "GOOG", 
        "cik": "0001652044"
    },
    "Facebook - 'META'": {
        "name": "META PLATFORMS INC", 
        "symbol": "META", 
        "cik": "0001326801"
    },
    "Amazon - 'AMZN'": {
        "name": "AMAZON COM INC", 
        "symbol": "AMZN", 
        "cik": "0001018724"
    },
    "Netflix - 'NFLX'": {
        "name": "NETFLIX INC", 
        "symbol": "NFLX", 
        "cik": "0001065280"
    },
    "Microsoft - 'MSFT'": {
        "name": "MICROSOFT CORP", 
        "symbol": "MSFT", 
        "cik": "0000789019"
    },
    "Tesla - 'TSLA'": {
        "name": "TESLA INC", 
        "symbol": "TSLA", 
        "cik": "0001318605"
    },
}


# ----------------------------
# AI分析函数
# ----------------------------
def get_recommendation(stock_info, question):
    """
    基于公司10-K财报文档，使用AI回答关于公司的问题
    
    参数:
        stock_info: 股票信息字典（包含公司名称、CIK等）
        question: 需要AI回答的问题
        
    返回:
        AI生成的回答（已移除Markdown格式符号）
    """
    # 1. 从EDGAR数据库获取公司10-K年报（美国上市公司年度报告）
    company = Company(stock_info["name"], stock_info["cik"])
    doc = company.get_10K()  # 获取最新10-K文档
    text = TXTML.parse_full_10K(doc)  # 解析文档为纯文本
    
    # 2. 初始化OpenAI大语言模型（温度参数控制输出随机性，0.15表示较低随机性）
    llm = OpenAI(temperature=0.15, openai_api_key=openai_api_key)
    
    # 3. 处理文本：取文档中间三分之一内容（避免文档过长导致处理缓慢）
    third_length = int(len(text) / 3)
    two_thirds_length = int(third_length * 2)
    text_segment = text[third_length:two_thirds_length]  # 取中间部分
    
    # 4. 分割文本：将长文本分成适合模型处理的小块
    text_splitter = PythonCodeTextSplitter(
        chunk_size=3000,    # 每个文本块的大小
        chunk_overlap=300   # 块之间的重叠部分（保持上下文连贯性）
    )
    docs = text_splitter.create_documents([text_segment])  # 创建文档对象列表
    
    # 5. 创建文本嵌入（将文本转换为向量，用于后续检索）
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    
    # 6. 构建向量数据库（用于高效检索相关文本片段）
    docsearch = FAISS.from_documents(docs, embeddings)
    
    # 7. 创建检索式问答链（结合检索和LLM生成回答）
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # 将检索到的文档"填充"到提示中
        retriever=docsearch.as_retriever()  # 检索器
    )
    
    # 8. 执行查询并返回结果（移除Markdown格式符号）
    analysis = qa_chain.run(question)
    return analysis.translate(str.maketrans("", "", "_*"))  # 移除下划线和星号


# ----------------------------
# Streamlit页面布局与内容
# ----------------------------
# 设置页面配置
st.set_page_config(
    page_title="Stock Information",  # 页面标题
    layout="wide",  # 宽布局
    initial_sidebar_state="collapsed",  # 初始侧边栏状态
    page_icon="Color Logo.png"  # 页面图标（需确保该文件存在）
)

# 创建两列布局（左侧窄列：数据展示；右侧宽列：详细信息）
col1, col2 = st.columns((1, 3))

# 左侧列：显示logo和股票选择器
with col1:
    # 显示应用logo
    try:
        icon = Image.open("Colour Logo.png")  # 尝试打开logo图片
        col1.image(icon, width=100)
    except FileNotFoundError:
        st.warning("Logo图片未找到，使用默认标题")
        st.subheader("Stock Analyzer")
    
    # 股票选择下拉框
    selected_stock = col1.selectbox(
        "选择股票", 
        options=list(stocks.keys()), 
        index=0  # 默认选择第一个（Apple）
    )


# ----------------------------
# 获取并展示股票数据
# ----------------------------
# 获取选中股票的信息
selected_stock_info = stocks[selected_stock]

# 1. 股票历史价格（使用yfinance）
with col1:
    # 初始化yfinance的ticker对象
    yf_ticker = yf.Ticker(selected_stock_info["symbol"])
    
    # 计算时间范围（近360天）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=360)
    
    # 获取历史数据并提取收盘价
    historical_data = yf_ticker.history(start=start_date, end=end_date)
    closing_prices = historical_data["Close"]
    
    # 绘制收盘价折线图
    st.subheader("近1年收盘价走势")
    col1.line_chart(closing_prices, use_container_width=True)


# 2. 公司概述
with col2:
    st.title("公司概述")
    # 获取公司业务摘要并显示
    company_summary = yf_ticker.info.get("longBusinessSummary", "暂无公司概述信息")
    col2.write(company_summary)


# 3. 年度财务数据（收入和收益）
with col1:
    st.subheader("年度财务摘要")
    # 使用yahooquery获取财务数据
    yq_ticker = Ticker(selected_stock_info["symbol"])
    earnings_data = yq_ticker.earnings  # 获取收益数据
    
    # 提取年度财务图表数据
    financials_data = earnings_data[selected_stock_info["symbol"]]['financialsChart']['yearly']
    
    # 转换为DataFrame并格式化
    df_financials = pd.DataFrame(financials_data)
    df_financials = df_financials.rename(
        columns={'earnings': '年度收益', 'revenue': '年度收入', 'date': '年份'}
    )
    
    # 格式化数值列（转换为易读格式）
    numeric_cols = ['年度收益', '年度收入']
    df_financials[numeric_cols] = df_financials[numeric_cols].applymap(format_large_number)
    
    # 处理日期列并设置索引
    df_financials['年份'] = df_financials['年份'].astype(str)
    df_financials.set_index('年份', inplace=True)
    
    # 显示财务数据表格
    col1.dataframe(df_financials, use_container_width=True)


# 4. 关键股票指标
with col1:
    st.subheader("关键指标")
    # 获取详细摘要数据
    summary_detail = yq_ticker.summary_detail[selected_stock_info["symbol"]]
    
    # 提取并格式化各项指标
    stock_metrics = {
        "市盈率 (P/E)": f'{summary_detail.get("trailingPE", "N/A"):.2f}' if summary_detail.get("trailingPE") else "N/A",
        "52周最低价": summary_detail.get("fiftyTwoWeekLow", "N/A"),
        "52周最高价": summary_detail.get("fiftyTwoWeekHigh", "N/A"),
        "市值": format_large_number(summary_detail.get("marketCap", 0)),
        "EBITDA": format_large_number(yf_ticker.info.get("ebitda", 0)),
        "目标高价": yf_ticker.info.get("targetHighPrice", "N/A"),
        "投资建议": yf_ticker.info.get("recommendationKey", "N/A").upper()
    }
    
    # 显示各项指标
    for metric, value in stock_metrics.items():
        col1.write(f"**{metric}**: {value}")


# ----------------------------
# AI分析结果展示
# ----------------------------
st.title("Lucidate 研究演示 (基于LangChain 🦜🔗)")

with col2:
    st.subheader("投资者关注点分析")
    
    # 显示AI对三个关键问题的分析
    st.write("**1. 公司主要产品和服务是什么？**")
    st.write(get_recommendation(selected_stock_info, "What are this firm's key products and services?"))
    
    st.write("\n**2. 公司的新产品、增长机会和独特优势是什么？**")
    st.write(get_recommendation(
        selected_stock_info, 
        "What are the new products and growth opportunities for this firm. What are its unique strengths?"
    ))
    
    st.write("\n**3. 公司的主要竞争对手和面临的威胁是什么？**")
    st.write(get_recommendation(
        selected_stock_info, 
        "Who are this firms key competitors? What are the principal threats?"
    ))

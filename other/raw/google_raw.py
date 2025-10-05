import os
import sys
import time
import re
import random
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from seleniumbase import Driver

# 路径设置 - 将项目根目录添加到系统路径，以便导入自定义模块
# 获取当前脚本的绝对路径
current_script_path = os.path.abspath(__file__)
# 获取脚本所在目录
script_directory = os.path.dirname(current_script_path)
# 获取项目根目录（脚本目录的父目录）
project_root = os.path.dirname(script_directory)

# 如果项目根目录不在系统路径中，则添加进去
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入自定义库（注意：原代码中libs.sources未提供具体实现）
from libs.sources import *


def run_google_de_scraper(query, limit, headless=True):
    """
    运行Google德国版搜索引擎爬虫，获取指定查询的搜索结果
    
    Args:
        query (str): 搜索关键词
        limit (int): 最大获取结果数量
        headless (bool): 是否以无头模式运行浏览器（不显示界面）
    
    Returns:
        list: 搜索结果列表，每个元素包含一个URL；若遇到验证码则返回-1
    """
    try:
        # 搜索引擎配置参数
        # Google德国版搜索URL（预设语言为德语，地区为德国）
        BASE_SEARCH_URL = "https://www.google.de/webhp?hl=de&gl=DE&&uule=w+CAIQICIHR2VybWFueQ=="
        # 搜索框的HTML名称属性
        SEARCH_BOX_NAME = "q"
        # 验证码识别关键词
        CAPTCHA_INDICATOR = "g-recaptcha"
        # 分页导航的XPath模板
        NEXT_PAGE_XPATH = "//a[@aria-label='{}']"
        # 滚动加载的XPath
        NEXT_SCROLL_XPATH = "//span[@class='RVQdVd']"
        # 完整搜索URL模板
        FULL_SEARCH_URL_TEMPLATE = "https://www.google.de/search?q="
        # 语言和地区参数
        LANGUAGE_PARAMS = "&hl=de&gl=DE"
        
        # 初始化变量
        results_count = 0  # 已获取结果数量
        current_page = 1   # 当前页码
        search_results = []  # 存储搜索结果
        
        # ------------------------------
        # 辅助函数定义
        # ------------------------------
        
        def has_pagination(source_code):
            """检查搜索结果页面是否有分页导航"""
            soup = BeautifulSoup(source_code, features="lxml")
            # 通过特定CSS类判断是否存在分页
            return bool(soup.find("span", class_=["SJajHc NVbCr"]))
        
        
        def extract_search_results(driver, page_num):
            """
            从当前页面提取搜索结果
            
            Args:
                driver: Selenium浏览器驱动
                page_num: 当前页码
                
            Returns:
                list: 提取到的结果列表，每个元素为[URL]
            """
            extracted_results = []
            
            # 获取页面源代码并解析
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, features="lxml")
            
            # 移除不需要的元素（广告、推荐等）
            for element in soup.find_all("div", class_="d4rhi"):
                element.extract()
            for element in soup.find_all("div", class_="Wt5Tfe"):
                element.extract()
            for element in soup.find_all("div", class_="UDZeY fAgajc OTFaAf"):
                element.extract()
            
            # 提取搜索结果（主要结果容器的CSS类）
            for result in soup.find_all("div", class_=["tF2Cxc", "dURPMd"]):
                result_url = "N/A"
                url_list = []
                
                # 提取标题（如果存在）
                try:
                    title_element = result.find("h3", class_=["LC20lb MBeuO DKV0Md"])
                    result_title = title_element.text.strip() if title_element else "N/A"
                except:
                    result_title = "N/A"
                
                # 提取描述（如果存在）
                try:
                    desc_element = result.find("div", class_=re.compile("VwiC3b", re.I))
                    result_desc = desc_element.text.strip() if desc_element else "N/A"
                except:
                    result_desc = "N/A"
                
                # 提取URL（如果存在）
                try:
                    for link in result.find_all("a"):
                        url = link.attrs.get('href', '')
                        # 处理可能的跳转链接（如Bing的跳转）
                        if "bing." in url:
                            url = get_real_url(url)  # 注意：get_real_url函数未在代码中实现
                        url_list.append(url)
                    
                    # 取第一个有效的URL
                    if url_list:
                        result_url = url_list[0]
                except:
                    result_url = "N/A"
                
                # 只添加有效的HTTP URL
                if result_url != "N/A" and "http" in result_url:
                    extracted_results.append([result_url])
            
            return extracted_results
        
        
        def is_captcha_present(driver):
            """检查页面是否出现验证码"""
            page_source = driver.page_source
            return CAPTCHA_INDICATOR in page_source
        
        
        def remove_duplicate_results(results):
            """移除结果列表中的重复URL"""
            cleaned_results = []
            seen_urls = {}  # 用于跟踪已见过的URL及其索引
            
            for index, result in enumerate(results):
                url = result[0]
                if url not in seen_urls:
                    seen_urls[url] = index
            
            # 保留首次出现的URL
            for url, index in seen_urls.items():
                cleaned_results.append(results[index])
            
            return cleaned_results
        
        # ------------------------------
        # 初始化Selenium浏览器驱动
        # ------------------------------
        # 注意：原代码中的ext_path未定义，可能需要根据实际情况设置
        driver = Driver(
            browser="chrome",
            wire=True,
            uc=True,  # 使用undetected-chromedriver模式
            headless2=headless,  # 无头模式
            incognito=False,  # 不使用隐身模式
            agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            do_not_track=True,
            undetectable=True,  # 避免被检测为自动化工具
            extension_dir=None,  # 原代码中ext_path未定义，暂设为None
            locale_code="de",  # 语言设置为德语
            no_sandbox=True,
        )
        
        # 设置超时参数
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(30)
        
        # 访问Google德国首页
        driver.get(BASE_SEARCH_URL)
        
        # 随机等待1-2秒，模拟人类行为，避免被检测
        random_sleep = random.randint(1, 2)
        time.sleep(random_sleep)
        
        # ------------------------------
        # 检查验证码并执行搜索
        # ------------------------------
        if not is_captcha_present(driver):
            # 找到搜索框并输入查询
            search_box = driver.find_element(By.NAME, SEARCH_BOX_NAME)
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)  # 模拟回车键提交搜索
            
            # 随机等待
            random_sleep = random.randint(1, 2)
            time.sleep(random_sleep)
            
            # 提取第一页的搜索结果
            search_results = extract_search_results(driver, current_page)
            search_results = remove_duplicate_results(search_results)
            results_count = len(search_results)
            
            print(f"首次获取结果数量 ({query}): {results_count}")
            
            # 如果没有获取到结果，尝试重新初始化浏览器
            if results_count == 0:
                driver.quit()
                time.sleep(random.randint(1, 2))
                
                # 重新初始化浏览器（强制无头模式）
                driver = Driver(
                    browser="chrome",
                    wire=True,
                    uc=True,
                    headless2=True,
                    incognito=False,
                    agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    do_not_track=True,
                    undetectable=True,
                    extension_dir=None,  # 原代码中ext_path未定义
                    locale_code="de",
                    no_sandbox=True
                )
            
            # ------------------------------
            # 处理分页，获取更多结果
            # ------------------------------
            if results_count < limit:
                continue_scraping = True
                pagination_exists = has_pagination(driver.page_source)
                
                if pagination_exists:
                    print("检测到分页导航，开始多页抓取")
                    
                    # 当结果数量不足且页数未达上限时，继续抓取
                    while (results_count <= limit) or (current_page <= (limit / 10)) and continue_scraping:
                        if not is_captcha_present(driver):
                            time.sleep(random.randint(1, 2))
                            current_page += 1
                            page_label = f"Page {current_page}"
                            
                            # 滚动到页面底部
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            
                            try:
                                # 点击下一页
                                next_page_button = driver.find_element(By.XPATH, NEXT_PAGE_XPATH.format(page_label))
                                next_page_button.click()
                                
                                # 提取新页面的结果并去重
                                search_results += extract_search_results(driver, current_page)
                                search_results = remove_duplicate_results(search_results)
                                results_count = len(search_results)
                                
                            except:
                                # 无法找到下一页按钮，停止抓取
                                continue_scraping = False
                        else:
                            # 遇到验证码，停止抓取
                            continue_scraping = False
                            search_results = -1
                    
                    # 关闭浏览器并返回结果
                    driver.quit()
                    return search_results
                
                else:
                    print("未检测到分页导航，使用URL参数分页")
                    SCROLL_PAUSE_TIME = 1
                    start_index = 0  # 结果起始索引（Google每页10条结果）
                    formatted_query = query.lower().replace(" ", "+")  # 格式化查询关键词
                    search_results = []
                    results_count = 0
                    
                    # 通过修改URL参数实现分页
                    while (results_count <= limit and start_index <= limit) and continue_scraping:
                        if not is_captcha_present(driver):
                            try:
                                # 构建带分页参数的搜索URL
                                paginated_url = f"{FULL_SEARCH_URL_TEMPLATE}{formatted_query}{LANGUAGE_PARAMS}&start={start_index}"
                                print(f"访问分页URL: {paginated_url}")
                                
                                # 访问分页URL
                                driver.set_page_load_timeout(120)
                                driver.implicitly_wait(60)
                                driver.get(paginated_url)
                                
                                # 随机等待2-4秒
                                time.sleep(random.randint(2, 4))
                                
                                current_page += 1
                                start_index += 10  # 每次增加10，获取下一页
                                
                                # 提取当前页结果
                                new_results = extract_search_results(driver, current_page)
                                print(f"当前页提取结果数量: {len(new_results)}")
                                
                                if new_results:
                                    search_results += new_results
                                    search_results = remove_duplicate_results(search_results)
                                    results_count = len(search_results)
                                else:
                                    # 没有新结果，停止抓取
                                    continue_scraping = False
                                    
                            except Exception as e:
                                print(f"分页抓取出错: {str(e)}")
                                continue_scraping = False
                        else:
                            # 遇到验证码，停止抓取
                            continue_scraping = False
                            search_results = -1
                    
                    # 关闭浏览器并返回结果
                    driver.quit()
                    return search_results
            
            else:
                # 结果数量已满足要求，返回结果
                driver.quit()
                return search_results
        
        else:
            # 检测到验证码，返回-1
            search_results = -1
            driver.quit()
            return search_results
    
    except Exception as e:
        print(f"爬虫执行出错: {str(e)}")
        # 确保浏览器被关闭
        try:
            driver.quit()
        except:
            pass
        return -1

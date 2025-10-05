from typing import Optional
from .filetool import FileTool
import requests
import feedparser

# 注意：使用此工具需要先安装 feedparser 库（可通过 pip install feedparser 安装）


class ArxivTool:
    """
    Arxiv论文查询与下载工具
    
    提供通过Arxiv API查询学术论文，以及下载论文PDF的功能。
    可配合FileTool使用以规范文件保存路径，也可独立使用。
    """
    def __init__(self, file_tool: Optional[FileTool] = None, enable_download: bool = True):
        """
        初始化Arxiv工具
        
        参数:
            file_tool: 可选的FileTool实例。如果提供，下载PDF时会使用该工具的根目录作为基准路径
            enable_download: 是否允许下载功能。设为False时将禁用PDF下载
        """
        self._file_tool = file_tool  # 用于路径处理的文件工具
        self._enable_download = enable_download  # 下载功能开关

    def arxiv_api_query(self, search_query: str, start: int, max_results: int) -> dict:
        """
        通过Arxiv API查询符合条件的论文
        
        调用Arxiv的开放API获取论文列表，支持分页查询。
        
        参数:
            search_query: 搜索关键词字符串（需要进行URL编码处理）
            start: 起始索引，用于分页（从0开始）
            max_results: 最大返回结果数量
            
        返回:
            包含查询结果的字典，结构如下:
                - entries: 论文列表，每个元素包含title(标题)、summary(摘要)、link(链接)、
                           arxiv_id(论文ID)、categories(分类)、published(发布时间)
                - total_results: 符合条件的总论文数
                - start_index: 当前起始索引
                - items_per_page: 本页返回数量
                - 若发生错误，返回 {'error': 错误信息字符串}
        """
        # Arxiv API的基础URL
        base_url = 'http://export.arxiv.org/api/query'
        
        # 构建请求参数
        params = {
            'search_query': search_query,
            'start': start,
            'max_results': max_results
        }
        
        try:
            # 发送GET请求
            response = requests.get(base_url, params=params)
            # 检查请求是否成功（状态码200）
            response.raise_for_status()
            
            # 解析API返回的XML格式数据
            feed = feedparser.parse(response.text)
            
            # 构建返回结果字典
            results = {
                'entries': [],
                'total_results': int(feed.feed.opensearch_totalresults),
                'start_index': int(feed.feed.opensearch_startindex),
                'items_per_page': int(feed.feed.opensearch_itemsperpage)
            }
            
            # 提取每篇论文的关键信息
            for entry in feed.entries:
                results['entries'].append({
                    'title': entry.title,                  # 论文标题
                    'summary': entry.summary,              # 论文摘要
                    'link': entry.link,                    # 论文详情页链接
                    'arxiv_id': entry.id.split('/abs/')[-1],  # 提取论文ID
                    'categories': [cat.term for cat in entry.tags],  # 论文分类
                    'published': entry.published           # 发布时间
                })
                
            return results
            
        except requests.exceptions.RequestException as e:
            # 捕获所有请求相关的异常（网络错误、超时等）
            return {'error': f'查询失败: {str(e)}'}

    def download_arxiv_paper_pdf(self, arxiv_id: str, save_path: str) -> dict:
        """
        下载Arxiv论文的PDF文件
        
        根据论文ID从Arxiv下载PDF，并保存到指定路径。
        
        参数:
            arxiv_id: 论文ID（可从arxiv_api_query方法的返回结果中获取）
            save_path: 保存文件的路径（含文件名）
            
        返回:
            成功时: {'message': 成功信息字符串}
            失败时: {'error': 错误信息字符串}
        """
        # 检查下载功能是否启用
        if not self._enable_download:
            return {'error': '下载功能已被禁用'}
            
        try:
            # 构建PDF下载URL（Arxiv的PDF链接格式为 https://arxiv.org/pdf/[论文ID]）
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
            response = requests.get(pdf_url)
            # 检查请求是否成功
            response.raise_for_status()
            
            # 如果提供了FileTool，使用其路径解析方法处理保存路径
            if self._file_tool is not None:
                resolved_path = self._file_tool._resolve(save_path)
                # 检查路径是否有效
                if resolved_path is None:
                    return {'error': f'保存路径 {save_path} 不被允许访问'}
                save_path = resolved_path
            
            # 写入文件（二进制模式）
            with open(save_path, 'wb') as file:
                file.write(response.content)
                
            return {'message': f'论文 {arxiv_id} 已成功下载至 {save_path}'}
            
        except requests.exceptions.RequestException as e:
            # 捕获网络请求相关错误
            return {'error': f'下载失败: {str(e)}'}
        except IOError as e:
            # 捕获文件写入相关错误
            return {'error': f'文件保存失败: {str(e)}'}
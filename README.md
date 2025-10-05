# web_to_markdown
基于 Selenium + OpenAI API 的网页内容自动提取与 Markdown 转换工具，可快速将任意网页的文本内容转化为结构化、易阅读的 Markdown 格式，并自动保存本地文件。


## 🌟 核心特性
- **智能网页提取**：使用 SeleniumBase 无痕模式（Incognito）+ 反检测驱动（undetected_chromedriver），规避多数网站反爬机制，稳定提取网页正文。
- **LLM 驱动转换**：通过 OpenAI 大模型（默认 `gpt-3.5-turbo`）自动梳理文本结构，生成符合规范的 Markdown（支持代码块、标题层级等）。
- **开箱即用**：命令行直接调用，无需复杂配置，转换结果自动保存为 MD 文件。
- **灵活配置**：支持自定义 LLM 模型（如 `gpt-4`）、API 参数（随机性、输出长度）及浏览器行为。


## 📋 前置条件
在使用前，请确保满足以下环境要求：
1. **Python 版本**：≥ 3.8（推荐 3.10+）
2. **OpenAI API 密钥**：需从 [OpenAI 控制台](https://platform.openai.com/api-keys) 获取（用于调用 Markdown 转换接口）。
3. **浏览器**：本地安装 Chrome 浏览器（SeleniumBase 依赖 Chrome 驱动，将自动安装匹配版本）。


## 🚀 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/xiaomingx/web_to_markdown.git
cd web_to_markdown
```

### 2. 安装依赖
使用 `pip` 安装所需 Python 包：
```bash
pip install -r requirements.txt
```

#### 依赖说明（`requirements.txt` 内容）
```txt
openai>=1.0.0          # OpenAI API 官方 SDK
seleniumbase>=4.20.0   # 网页自动化与反爬工具
```

### 3. 配置 OpenAI API 密钥
将 API 密钥设置为环境变量（避免硬编码泄露）：
- **Linux / macOS**：
  ```bash
  export OPENAI_API_KEY="你的OpenAI密钥"
  ```
- **Windows（CMD）**：
  ```cmd
  set OPENAI_API_KEY="你的OpenAI密钥"
  ```
- **Windows（PowerShell）**：
  ```powershell
  $env:OPENAI_API_KEY="你的OpenAI密钥"
  ```


## 📖 使用方法
通过命令行直接运行脚本，支持自定义目标 URL 和 LLM 模型。

### 基础用法（默认模型 `gpt-3.5-turbo`）
```bash
python web_to_markdown.py https://example.com
```

### 进阶用法（指定模型，如 `gpt-4`）
```bash
python web_to_markdown.py https://example.com gpt-4
```

### 输出说明
- 转换结果会**实时打印到控制台**，方便快速查看。
- 同时自动保存为 Markdown 文件，文件名规则：`output_目标域名_路径.md`（例如访问 `https://example.com/docs` 会生成 `output_example.com_docs.md`）。


## ⚙️ 配置参数
可根据需求修改脚本中的核心参数（位于 `web_to_markdown.py`）：

| 参数                | 说明                                                                 | 默认值       |
|---------------------|----------------------------------------------------------------------|--------------|
| `temperature`       | 控制 LLM 输出随机性（0=确定性强，1=创造性强）                        | 0.6          |
| `top_p`             | 控制 token 选择的累积概率（0.9 表示仅选择概率和为 90% 的最可能 token） | 0.9          |
| `max_tokens`        | LLM 最大输出 token 数（需根据模型支持范围调整，如 `gpt-3.5-turbo` 支持 4096） | 8192         |
| `uc=True`           | 是否启用反检测驱动（规避网站对自动化工具的拦截）                     | True         |
| `incognito=True`    | 是否使用无痕模式（避免缓存影响网页内容）                             | True         |


## ❌ 常见问题与解决方法
| 问题现象                          | 可能原因                                  | 解决办法                                  |
|-----------------------------------|-------------------------------------------|-------------------------------------------|
| 提示“未找到 OPENAI_API_KEY”       | 未设置环境变量或变量名错误                | 重新执行“配置 OpenAI API 密钥”步骤        |
| 网页无法加载（WebDriverException）| Chrome 未安装或驱动版本不匹配              | 执行 `sb install chromedriver` 自动安装驱动 |
| API 调用失败（OpenAIError）       | 密钥无效、余额不足或模型名错误            | 检查密钥有效性，确认模型支持（如 `gpt-4` 需付费账户） |
| 提取内容为空                      | 网页需登录或内容动态加载（JS 渲染）       | 需手动补充登录逻辑（参考 SeleniumBase 文档） |


## 📂 项目结构
```
web_to_markdown/
├── web_to_markdown.py  # 主脚本（核心逻辑、命令行入口）
├── requirements.txt    # 依赖清单
└── README.md           # 项目说明（本文档）
```


## 🤝 贡献指南
1. Fork 本仓库
2. 创建特性分支（`git checkout -b feature/xxx`）
3. 提交代码（`git commit -m "add: 新增xxx功能"`）
4. 推送分支（`git push origin feature/xxx`）
5. 提交 Pull Request


## 📄 许可证
本项目基于 [MIT 许可证](https://opensource.org/licenses/MIT) 开源，可自由使用、修改和分发，需保留原作者版权声明。


## ⚠️ 注意事项
- 请遵守目标网站的 `robots.txt` 协议，勿用于爬取敏感或受限内容。
- 调用 OpenAI API 会产生费用，建议根据需求调整 `max_tokens` 以控制成本。
- 动态渲染网页（如 Vue/React 构建）可能需要增加 `time.sleep(2)` 等待内容加载（可在 `sb.get(url)` 后添加）。

要不要我帮你生成一份配套的 **requirements.txt** 文件，直接复制就能用？
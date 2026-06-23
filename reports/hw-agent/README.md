# 通用问题优化智能体

这是一个用于课程作业的完整 Web 项目。用户输入原始问题后，系统会调用阿里云百炼中的 `qwen3.7-plus` 模型，先通过提示词工程生成问题类型判断、原问题不足分析、优化后的问题、最终 Prompt、优化理由和输出格式建议，再基于优化后的 Prompt 对问题进行求解，最后自动生成包含优化过程、求解过程和最终答案的 PDF 报告。

## 项目结构

```text
hw-agent/
├── app.py
├── streamlit_app.py
├── runtime.txt
├── requirements.txt
├── README.md
├── .streamlit/
│   └── secrets.toml.example
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
└── reports/
    └── .gitkeep
```

## 本地运行

本项目同时支持 Streamlit 页面和 Flask 页面。若你的目标是公开访问和录屏演示，推荐使用 Streamlit。

## Streamlit 本地运行

1. 进入项目目录：

```bash
cd hw-agent
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 创建本地 Secrets 文件：

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

4. 编辑 `.streamlit/secrets.toml`，填入你的阿里云百炼 API Key：

```toml
DASHSCOPE_API_KEY = "你的阿里云百炼 API Key"
BAILIAN_MODEL = "qwen3.7-plus"
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

`.streamlit/secrets.toml` 已加入 `.gitignore`，不要提交真实 Key。

5. 启动 Streamlit：

```bash
streamlit run streamlit_app.py
```

浏览器访问终端显示的本地地址，一般是：

```text
http://localhost:8501
```

## Streamlit 公开部署

推荐使用 Streamlit Community Cloud：

1. 将 `hw-agent` 项目上传到 GitHub。
2. 在 Streamlit Community Cloud 新建 App。
3. Main file path 填写：

```text
streamlit_app.py
```

如果你把项目放在仓库子目录中，请填写实际路径，例如：

```text
hw-agent/streamlit_app.py
```

如果你的 GitHub 子目录名是 `agent-optimization`，则填写：

```text
agent-optimization/streamlit_app.py
```

4. 在 App 的 Secrets 中添加：

```toml
DASHSCOPE_API_KEY = "你的阿里云百炼 API Key"
BAILIAN_MODEL = "qwen3.7-plus"
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

5. 部署成功后，Streamlit 会生成一个公开可访问链接，可作为作业提交链接。

配置一次 Secrets 后，公开页面即可直接调用阿里云百炼接口，不需要每次本地运行。

项目包含 `runtime.txt`，用于让 Streamlit Cloud 使用 Python 3.11，避免在 Python 3.14 环境中构建 Pillow 失败。

## Flask 本地运行

1. 进入项目目录：

```bash
cd hw-agent
```

2. 创建并激活虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell 可使用：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 配置阿里云百炼 API Key：

```bash
export DASHSCOPE_API_KEY="你的阿里云百炼 API Key"
```

Windows PowerShell 可使用：

```powershell
$env:DASHSCOPE_API_KEY="你的阿里云百炼 API Key"
```

可选：指定模型，默认使用 `qwen3.7-plus`。

```bash
export BAILIAN_MODEL="qwen3.7-plus"
```

可选：指定百炼 OpenAI 兼容接口地址，默认使用北京地域：

```bash
export BAILIAN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

5. 启动项目：

```bash
python app.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

## 功能说明

Streamlit 页面对应文件为 `streamlit_app.py`，提供完整的“优化问题 -> 基于 Prompt 求解 -> 生成 PDF -> 下载 PDF”演示流程。

Flask 接口如下：

- `GET /`：返回首页。
- `POST /optimize`：接收用户原始问题，调用阿里云百炼 OpenAI 兼容接口，返回 JSON 格式优化结果。
- `POST /solve`：接收优化结果中的最终 Prompt，调用模型完成问题求解，返回求解过程、最终答案和自检说明。
- `POST /generate_pdf`：接收优化结果和求解结果，生成 PDF 求解报告。
- `GET /download/<filename>`：下载生成的 PDF 文档。

项目不是普通问答机器人，而是分两步工作：先由“通用问题优化智能体”分析并优化问题，再由“问题求解智能体”基于优化后的 Prompt 完成求解。

## PDF 文档内容

PDF 报告包含：

- 标题：通用问题优化智能体求解报告
- 原始问题
- 智能体工作流程
- 问题类型判断
- 原问题不足分析
- 优化后的问题
- 最终 Prompt
- 优化理由
- 输出格式建议
- 基于优化 Prompt 的求解过程
- 最终答案
- 自检与结果说明
- 总结

生成的 PDF 会保存在 `reports/` 目录中，并在页面上提供下载链接。

## 部署到 Render

1. 将项目上传到 GitHub。
2. 在 Render 创建 Web Service。
3. Build Command 填写：

```bash
pip install -r requirements.txt
```

4. Start Command 填写：

```bash
gunicorn app:app
```

5. 在 Environment Variables 中添加：

```text
DASHSCOPE_API_KEY=你的阿里云百炼 API Key
BAILIAN_MODEL=qwen3.7-plus
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

6. 部署完成后，Render 会提供一个公开可访问链接，可作为作业提交链接。

## 部署到 Railway

1. 在 Railway 新建项目并连接 GitHub 仓库。
2. 添加环境变量 `DASHSCOPE_API_KEY`。
3. Railway 会自动安装依赖，也可以在设置中指定启动命令：

```bash
gunicorn app:app
```

4. 生成公网域名后即可访问。

## 关于 Vercel

本项目是 Flask 后端项目，更推荐部署到 Render 或 Railway。若要部署到 Vercel，需要额外改造成 serverless 结构。

## MP4 录屏建议

录屏时可以展示以下流程：

1. 打开公开访问链接或本地地址。
2. 在输入框输入一个需要解决的问题，例如“帮我写一篇关于人工智能的论文”。
3. 点击“优化问题”。
4. 展示页面返回的问题类型、问题分析、优化后的问题和最终 Prompt。
5. 点击“基于 Prompt 求解”，展示模型基于优化 Prompt 得到的求解过程和最终答案。
6. 点击“生成 PDF 文档”。
7. 点击“下载 PDF”，打开 PDF 展示优化过程、求解过程和最终答案。
8. 录屏导出为 MP4，和 PDF 文档、访问链接一起提交。

可使用 OBS Studio、Windows Xbox Game Bar、macOS 自带录屏或浏览器录屏插件完成 MP4 录制。

## 注意事项

- 请确保 `DASHSCOPE_API_KEY` 已正确配置。代码也兼容读取 `BAILIAN_API_KEY`。
- 本项目使用阿里云百炼公开 API 的 OpenAI 兼容模式，不包含任何内部未公开模型。
- 如果服务器缺少中文字体，PDF 仍可生成，但中文显示效果取决于部署环境字体支持。
# general-question-solver

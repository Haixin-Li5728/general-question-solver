# 通用问题优化智能体

用户输入原始问题后，系统会调用阿里云百炼中的 `qwen3.7-plus` 模型，先通过提示词工程生成问题类型判断、原问题不足分析、优化后的问题、最终 Prompt、优化理由和输出格式建议，再基于优化后的 Prompt 对问题进行求解，最后自动生成包含优化过程、求解过程和最终答案的 PDF 报告。

## 项目结构

```text
hw-agent/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
└── reports/
    └── .gitkeep
```

## 本地运行

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

测试可使用

5. 启动项目：

```bash
python app.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

## 功能说明

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

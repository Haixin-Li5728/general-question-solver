import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from openai import OpenAI
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)


SYSTEM_PROMPT = """
你是一个“通用问题优化智能体”，你的任务不是直接回答用户问题，而是帮助用户把模糊、宽泛、不完整的问题优化成更清晰、更具体、更适合大模型回答的问题。你需要分析问题类型、指出原问题不足、补充必要约束、明确输出格式，并生成最终可直接提交给大模型的高质量 Prompt。

请严格遵守以下要求：
1. 不要回答用户的原始问题，只能优化问题。
2. 按照“任务类型判断 -> 原问题不足分析 -> 优化问题 -> 生成最终 Prompt -> 给出优化理由 -> 建议输出格式”的流程工作。
3. 输出必须是合法 JSON，不要使用 Markdown 代码块，不要添加 JSON 之外的解释。
4. JSON 必须包含以下字段：
{
  "task_type": "任务类型",
  "problem_analysis": "原问题存在的问题分析",
  "optimized_question": "优化后的问题",
  "final_prompt": "最终可直接使用的 Prompt",
  "optimization_reason": "优化理由",
  "output_format_suggestion": "输出格式建议"
}
""".strip()


SOLVER_SYSTEM_PROMPT = """
你是一个“问题求解智能体”。你会收到一个已经优化过的高质量 Prompt，你的任务是严格基于该 Prompt 对问题进行求解。

请严格遵守以下要求：
1. 需要给出可展示给用户的求解过程，但不要暴露不可验证的内部思维链。
2. 求解过程应体现：理解任务、拆解步骤、依据或方法、关键推导、最终结论。
3. 如果问题缺少必要信息，请说明合理假设，并在答案中标注假设。
4. 输出必须是合法 JSON，不要使用 Markdown 代码块，不要添加 JSON 之外的解释。
5. JSON 必须包含以下字段：
{
  "solution_process": "面向用户的详细求解过程",
  "final_answer": "最终答案",
  "verification_summary": "自检与结果说明"
}
""".strip()


def get_bailian_client():
    """Create an OpenAI-compatible client for Alibaba Cloud Bailian / DashScope."""
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")
    if not api_key:
        raise RuntimeError("未检测到 DASHSCOPE_API_KEY 或 BAILIAN_API_KEY，请先配置阿里云百炼 API Key。")
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )


def extract_json(text):
    """Parse model output as JSON, with a fallback for accidental surrounding text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_result(data):
    """Ensure all required keys exist so the frontend and PDF generator are predictable."""
    required_fields = {
        "task_type": "未识别",
        "problem_analysis": "模型未返回该字段。",
        "optimized_question": "模型未返回该字段。",
        "final_prompt": "模型未返回该字段。",
        "optimization_reason": "模型未返回该字段。",
        "output_format_suggestion": "模型未返回该字段。",
    }
    return {key: str(data.get(key, default)).strip() for key, default in required_fields.items()}


def normalize_solution(data):
    """Ensure solution fields exist before rendering or writing the report."""
    required_fields = {
        "solution_process": "模型未返回求解过程。",
        "final_answer": "模型未返回最终答案。",
        "verification_summary": "模型未返回自检说明。",
    }
    return {key: str(data.get(key, default)).strip() for key, default in required_fields.items()}


def register_pdf_font():
    """Register a common Chinese font if available; otherwise use Helvetica as fallback."""
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for font_path in candidates:
        if Path(font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont("ChineseFont", font_path))
                return "ChineseFont"
            except Exception:
                continue
    return "Helvetica"


PDF_FONT = register_pdf_font()


def paragraph(text, style):
    """Convert newlines to PDF-friendly line breaks."""
    safe_text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe_text.replace("\n", "<br/>"), style)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/optimize", methods=["POST"])
def optimize():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()

    if not question:
        return jsonify({"error": "请输入需要优化的原始问题。"}), 400

    try:
        client = get_bailian_client()
        response = client.chat.completions.create(
            model=os.getenv("BAILIAN_MODEL", "qwen3.7-plus"),
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"请优化下面这个原始问题，并严格返回 JSON：\n\n{question}",
                },
            ],
        )

        model_text = response.choices[0].message.content
        result = normalize_result(extract_json(model_text))
        result["original_question"] = question
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"问题优化失败：{exc}"}), 500


@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    data = request.get_json(silent=True) or {}
    original_question = (data.get("original_question") or "").strip()

    if not original_question:
        return jsonify({"error": "缺少原始问题，无法生成 PDF。"}), 400

    result = normalize_result(data)
    solution = normalize_solution(data)
    filename = f"question_optimizer_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = REPORT_DIR / filename

    try:
        build_pdf(filepath, original_question, result, solution)
        return jsonify({"download_url": f"/download/{filename}", "filename": filename})
    except Exception as exc:
        return jsonify({"error": f"PDF 生成失败：{exc}"}), 500


@app.route("/solve", methods=["POST"])
def solve():
    data = request.get_json(silent=True) or {}
    final_prompt = (data.get("final_prompt") or "").strip()

    if not final_prompt:
        return jsonify({"error": "缺少最终 Prompt，无法求解问题。"}), 400

    try:
        client = get_bailian_client()
        response = client.chat.completions.create(
            model=os.getenv("BAILIAN_MODEL", "qwen3.7-plus"),
            temperature=0.3,
            messages=[
                {"role": "system", "content": SOLVER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"请基于下面的最终 Prompt 完成问题求解，并严格返回 JSON：\n\n{final_prompt}",
                },
            ],
        )

        model_text = response.choices[0].message.content
        solution = normalize_solution(extract_json(model_text))
        return jsonify(solution)
    except Exception as exc:
        return jsonify({"error": f"问题求解失败：{exc}"}), 500


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(REPORT_DIR, filename, as_attachment=True)


def build_pdf(filepath, original_question, result, solution):
    """Generate a detailed report that shows optimization and final solving process."""
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="通用问题优化智能体求解报告",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ChineseTitle",
        parent=styles["Title"],
        fontName=PDF_FONT,
        fontSize=22,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#172554"),
        spaceAfter=18,
    )
    heading_style = ParagraphStyle(
        "ChineseHeading",
        parent=styles["Heading2"],
        fontName=PDF_FONT,
        fontSize=14,
        leading=20,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=12,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "ChineseBody",
        parent=styles["BodyText"],
        fontName=PDF_FONT,
        fontSize=10.5,
        leading=17,
        alignment=TA_LEFT,
        spaceAfter=8,
    )

    story = [
        Paragraph("通用问题优化智能体求解报告", title_style),
        paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style),
        Spacer(1, 0.2 * cm),
        Paragraph("一、原始问题", heading_style),
        paragraph(original_question, body_style),
        Paragraph("二、智能体工作流程", heading_style),
    ]

    workflow_rows = [
        ["步骤", "说明"],
        ["1. 输入接收", "接收用户提交的原始问题，并检查问题是否为空。"],
        ["2. 任务类型判断", "判断问题属于写作、编程、学习、分析、计划、翻译等哪类任务。"],
        ["3. 不足分析", "识别目标不清、背景不足、约束不足、输出格式不明确等问题。"],
        ["4. 问题优化", "补充必要背景、约束、目标和评价标准，形成更清晰的问题。"],
        ["5. Prompt 生成", "生成可直接复制给大模型使用的最终 Prompt。"],
        ["6. 基于 Prompt 求解", "将优化后的 Prompt 交给问题求解智能体，生成求解过程和最终答案。"],
        ["7. 报告生成", "将优化过程、求解过程、最终答案和自检说明整理为 PDF 文档。"],
    ]
    table = Table(workflow_rows, colWidths=[3.4 * cm, 11.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#172554")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bfdbfe")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([table, Spacer(1, 0.2 * cm)])

    sections = [
        ("三、问题类型判断", result["task_type"]),
        ("四、原问题不足分析", result["problem_analysis"]),
        ("五、优化后的问题", result["optimized_question"]),
        ("六、最终 Prompt", result["final_prompt"]),
        ("七、优化理由", result["optimization_reason"]),
        ("八、输出格式建议", result["output_format_suggestion"]),
        ("九、基于优化 Prompt 的求解过程", solution["solution_process"]),
        ("十、最终答案", solution["final_answer"]),
        ("十一、自检与结果说明", solution["verification_summary"]),
        (
            "十二、总结",
            "本报告展示了智能体从原始问题输入、问题优化、最终 Prompt 生成，到基于优化 Prompt 完成求解并输出答案的完整过程。该流程体现了提示词工程与轻量工具调用结合的智能体工作方式。",
        ),
    ]

    for heading, content in sections:
        story.append(Paragraph(heading, heading_style))
        story.append(paragraph(content, body_style))

    doc.build(story)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)

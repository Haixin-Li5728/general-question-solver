import os
import uuid
from datetime import datetime

import streamlit as st

from app import (
    REPORT_DIR,
    SOLVER_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_pdf,
    extract_json,
    get_bailian_client,
    normalize_result,
    normalize_solution,
)


st.set_page_config(
    page_title="通用问题优化智能体",
    layout="wide",
)


def load_runtime_config():
    """Load deployment secrets once from Streamlit Secrets into environment variables."""
    secret_names = ["DASHSCOPE_API_KEY", "BAILIAN_API_KEY", "BAILIAN_MODEL", "BAILIAN_BASE_URL"]
    for name in secret_names:
        if name in st.secrets and not os.getenv(name):
            os.environ[name] = str(st.secrets[name])


def optimize_question(question):
    """Call Bailian to optimize the original question into a high-quality prompt."""
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
    result = normalize_result(extract_json(response.choices[0].message.content))
    result["original_question"] = question
    return result


def solve_with_prompt(final_prompt):
    """Call Bailian again to solve the problem based on the optimized prompt."""
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
    return normalize_solution(extract_json(response.choices[0].message.content))


def create_pdf_report(result):
    """Build the report and return the filename plus PDF bytes for Streamlit download."""
    filename = f"question_optimizer_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = REPORT_DIR / filename
    build_pdf(filepath, result["original_question"], result, result)
    return filename, filepath.read_bytes()


def render_result(result):
    st.subheader("一、问题优化结果")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**原始问题**")
        st.info(result["original_question"])
        st.markdown("**问题类型**")
        st.write(result["task_type"])
        st.markdown("**输出格式建议**")
        st.write(result["output_format_suggestion"])
    with col2:
        st.markdown("**原问题不足分析**")
        st.write(result["problem_analysis"])
        st.markdown("**优化理由**")
        st.write(result["optimization_reason"])

    st.markdown("**优化后的问题**")
    st.success(result["optimized_question"])
    st.markdown("**最终 Prompt**")
    st.code(result["final_prompt"], language="markdown")


def render_solution(result):
    st.subheader("二、基于优化 Prompt 的求解结果")
    st.markdown("**求解过程**")
    st.write(result["solution_process"])
    st.markdown("**最终答案**")
    st.success(result["final_answer"])
    st.markdown("**自检与结果说明**")
    st.write(result["verification_summary"])


load_runtime_config()

st.title("通用问题优化智能体")
st.caption("阿里云百炼 qwen3.7-plus | 问题优化 | 基于优化 Prompt 求解 | PDF 求解报告")

with st.sidebar:
    st.header("演示流程")
    st.write("1. 输入原始问题")
    st.write("2. 点击优化并求解")
    st.write("3. 查看优化 Prompt、求解过程和最终答案")
    st.write("4. 生成并下载 PDF 报告")
    st.divider()
    st.markdown("**当前模型**")
    st.code(os.getenv("BAILIAN_MODEL", "qwen3.7-plus"))
    st.markdown("**API Key 状态**")
    if os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY"):
        st.success("已配置")
    else:
        st.error("未配置")

question = st.text_area(
    "请输入原始问题",
    height=180,
    placeholder="例如：帮我写一篇关于人工智能的论文",
)

run_button = st.button("优化问题并求解", type="primary", use_container_width=True)

if run_button:
    if not question.strip():
        st.warning("请先输入一个原始问题。")
    else:
        try:
            with st.spinner("智能体正在优化问题，生成最终 Prompt..."):
                st.session_state["agent_result"] = optimize_question(question.strip())

            with st.spinner("智能体正在基于优化 Prompt 求解问题..."):
                solution = solve_with_prompt(st.session_state["agent_result"]["final_prompt"])
                st.session_state["agent_result"].update(solution)

            st.success("优化与求解完成，可以生成 PDF 报告。")
        except Exception as exc:
            st.error(f"执行失败：{exc}")

result = st.session_state.get("agent_result")
if result:
    render_result(result)
    render_solution(result)

    st.subheader("三、PDF 求解报告")
    if st.button("生成 PDF 文档", use_container_width=True):
        try:
            filename, pdf_bytes = create_pdf_report(result)
            st.session_state["pdf_filename"] = filename
            st.session_state["pdf_bytes"] = pdf_bytes
            st.success(f"PDF 已生成：{filename}")
        except Exception as exc:
            st.error(f"PDF 生成失败：{exc}")

    if "pdf_bytes" in st.session_state:
        st.download_button(
            "下载 PDF 报告",
            data=st.session_state["pdf_bytes"],
            file_name=st.session_state["pdf_filename"],
            mime="application/pdf",
            use_container_width=True,
        )

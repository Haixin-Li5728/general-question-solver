const questionInput = document.querySelector("#questionInput");
const optimizeBtn = document.querySelector("#optimizeBtn");
const solveBtn = document.querySelector("#solveBtn");
const pdfBtn = document.querySelector("#pdfBtn");
const copyBtn = document.querySelector("#copyBtn");
const message = document.querySelector("#message");
const resultPanel = document.querySelector("#resultPanel");
const downloadLink = document.querySelector("#downloadLink");

let latestResult = null;

function setMessage(text, type = "") {
  message.textContent = text;
  message.className = `message ${type}`.trim();
}

function setLoading(isLoading) {
  optimizeBtn.disabled = isLoading;
  optimizeBtn.textContent = isLoading ? "正在优化..." : "优化问题";
}

function setSolving(isSolving) {
  solveBtn.disabled = isSolving || !latestResult;
  solveBtn.textContent = isSolving ? "正在求解..." : "基于 Prompt 求解";
}

function renderResult(result) {
  latestResult = result;
  resultPanel.classList.remove("hidden");
  solveBtn.disabled = false;
  pdfBtn.disabled = true;
  downloadLink.classList.add("hidden");

  document.querySelector("#originalQuestion").textContent = result.original_question || "";
  document.querySelector("#taskType").textContent = result.task_type || "";
  document.querySelector("#problemAnalysis").textContent = result.problem_analysis || "";
  document.querySelector("#optimizedQuestion").textContent = result.optimized_question || "";
  document.querySelector("#finalPrompt").textContent = result.final_prompt || "";
  document.querySelector("#optimizationReason").textContent = result.optimization_reason || "";
  document.querySelector("#outputFormat").textContent = result.output_format_suggestion || "";

  document.querySelector("#solutionProcessCard").classList.add("hidden");
  document.querySelector("#finalAnswerCard").classList.add("hidden");
  document.querySelector("#verificationCard").classList.add("hidden");
}

function renderSolution(solution) {
  latestResult = { ...latestResult, ...solution };
  pdfBtn.disabled = false;

  document.querySelector("#solutionProcess").textContent = solution.solution_process || "";
  document.querySelector("#finalAnswer").textContent = solution.final_answer || "";
  document.querySelector("#verificationSummary").textContent = solution.verification_summary || "";

  document.querySelector("#solutionProcessCard").classList.remove("hidden");
  document.querySelector("#finalAnswerCard").classList.remove("hidden");
  document.querySelector("#verificationCard").classList.remove("hidden");
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败，请稍后重试。");
  }
  return data;
}

optimizeBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) {
    setMessage("请输入一个原始问题。", "error");
    return;
  }

  setLoading(true);
  solveBtn.disabled = true;
  pdfBtn.disabled = true;
  downloadLink.classList.add("hidden");
  setMessage("智能体正在分析问题类型、补充约束并生成最终 Prompt...");

  try {
    const result = await postJson("/optimize", { question });
    renderResult(result);
    setMessage("优化完成。请点击“基于 Prompt 求解”，生成最终答案后再导出 PDF。", "success");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    setLoading(false);
  }
});

solveBtn.addEventListener("click", async () => {
  if (!latestResult) {
    setMessage("请先完成问题优化。", "error");
    return;
  }

  setSolving(true);
  pdfBtn.disabled = true;
  downloadLink.classList.add("hidden");
  setMessage("智能体正在基于优化后的最终 Prompt 求解原问题...");

  try {
    const solution = await postJson("/solve", latestResult);
    renderSolution(solution);
    setMessage("求解完成，可以生成包含完整过程的 PDF 文档。", "success");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    setSolving(false);
  }
});

pdfBtn.addEventListener("click", async () => {
  if (!latestResult) {
    setMessage("请先完成问题优化。", "error");
    return;
  }

  pdfBtn.disabled = true;
  pdfBtn.textContent = "正在生成 PDF...";
  setMessage("正在整理问题优化过程、模型求解过程和最终答案并生成 PDF 报告...");

  try {
    const data = await postJson("/generate_pdf", latestResult);
    downloadLink.href = data.download_url;
    downloadLink.classList.remove("hidden");
    setMessage(`PDF 已生成：${data.filename}`, "success");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    pdfBtn.disabled = false;
    pdfBtn.textContent = "生成 PDF 文档";
  }
});

copyBtn.addEventListener("click", async () => {
  const text = document.querySelector("#finalPrompt").textContent;
  if (!text) {
    return;
  }

  await navigator.clipboard.writeText(text);
  setMessage("最终 Prompt 已复制到剪贴板。", "success");
});

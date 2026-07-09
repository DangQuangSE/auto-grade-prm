document.addEventListener("DOMContentLoaded", () => {
    const gradeForm = document.getElementById("gradeForm");
    const customCriteria = document.getElementById("customCriteria");
    const criteriaFile = document.getElementById("criteriaFile");
    const welcomeView = document.getElementById("welcomeView");
    const loadingView = document.getElementById("loadingView");
    const resultsView = document.getElementById("resultsView");
    const logTerminalContent = document.getElementById("logTerminalContent");
    const scoreVal = document.getElementById("scoreVal");
    const aiSummaryText = document.getElementById("aiSummaryText");
    const resultRepoTitle = document.getElementById("resultRepoTitle");
    const resultRepoType = document.getElementById("resultRepoType");
    const criteriaList = document.getElementById("criteriaList");
    const warningsList = document.getElementById("warningsList");
    const exportMdBtn = document.getElementById("exportMdBtn");
    const printBtn = document.getElementById("printBtn");
    const submitBtn = document.getElementById("submitBtn");
    const criteriaHint = document.getElementById("criteriaHint");
    const providerStatus = document.getElementById("providerStatus");
    const providerStatusText = document.getElementById("providerStatusText");

    let currentReport = null;
    let providerInfo = null;

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function validateCriteria() {
        const hasContent = customCriteria.value.trim() !== "";
        submitBtn.disabled = !hasContent;
        if (!hasContent) {
            criteriaHint.textContent = "Please enter or upload criteria before grading.";
            criteriaHint.style.color = "var(--margin-red)";
            criteriaHint.style.fontWeight = "bold";
        } else {
            criteriaHint.textContent = "Criteria is ready. You can edit it before grading.";
            criteriaHint.style.color = "var(--graphite)";
            criteriaHint.style.fontWeight = "normal";
        }
    }

    function switchView(viewName) {
        welcomeView.classList.add("hidden");
        loadingView.classList.add("hidden");
        resultsView.classList.add("hidden");

        if (viewName === "welcome") welcomeView.classList.remove("hidden");
        if (viewName === "loading") loadingView.classList.remove("hidden");
        if (viewName === "results") resultsView.classList.remove("hidden");
    }

    function clearLogs() {
        logTerminalContent.innerHTML = "";
    }

    function addLog(text, type = "info") {
        const p = document.createElement("p");
        p.className = `log-line ${type}`;
        p.innerText = `> ${text}`;
        logTerminalContent.appendChild(p);
        logTerminalContent.scrollTop = logTerminalContent.scrollHeight;
    }

    function arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = "";
        const chunkSize = 0x8000;
        for (let i = 0; i < bytes.length; i += chunkSize) {
            const chunk = bytes.subarray(i, i + chunkSize);
            binary += String.fromCharCode.apply(null, chunk);
        }
        return btoa(binary);
    }

    async function extractCriteriaFile(file) {
        const contentBase64 = arrayBufferToBase64(await file.arrayBuffer());
        const response = await fetch("/api/criteria/extract", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filename: file.name,
                content_base64: contentBase64
            })
        });
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Could not read the criteria file.");
        }
        const data = await response.json();
        return data.criteria || "";
    }

    async function loadProviderInfo() {
        try {
            const response = await fetch("/api/provider");
            providerInfo = await response.json();
            providerStatus.classList.toggle("configured", providerInfo.api_key_configured);
            providerStatus.classList.toggle("missing", !providerInfo.api_key_configured);
            providerStatusText.textContent = `${providerInfo.provider}: ${providerInfo.model} ${
                providerInfo.api_key_configured ? "(configured)" : "(missing API key)"
            }`;
        } catch (error) {
            providerStatus.classList.add("missing");
            providerStatusText.textContent = "AI provider: unavailable";
        }
    }

    customCriteria.addEventListener("input", validateCriteria);

    criteriaFile.addEventListener("change", async () => {
        const file = criteriaFile.files && criteriaFile.files[0];
        if (!file) return;
        const lowerName = file.name.toLowerCase();
        const validName = lowerName.endsWith(".docx") || lowerName.endsWith(".md") || lowerName.endsWith(".txt");
        if (!validName) {
            alert("Only .docx, .md, and .txt criteria files are supported.");
            criteriaFile.value = "";
            return;
        }
        try {
            criteriaHint.textContent = "Reading criteria file...";
            customCriteria.value = await extractCriteriaFile(file);
            validateCriteria();
        } catch (error) {
            alert(`Could not read criteria file: ${error.message}`);
            criteriaFile.value = "";
            validateCriteria();
        }
    });

    fetch("/api/criteria")
        .then(res => res.json())
        .then(data => {
            customCriteria.value = data.criteria || "";
            validateCriteria();
        })
        .catch(err => {
            console.error("Could not load default criteria:", err);
            validateCriteria();
        });

    loadProviderInfo();

    gradeForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const githubUrl = document.getElementById("githubUrl").value.trim();
        const criteria = customCriteria.value.trim();

        switchView("loading");
        clearLogs();
        addLog("Preparing grading request...", "info");
        addLog(githubUrl.startsWith("http") || githubUrl.startsWith("git@")
            ? `Cloning repository: ${githubUrl}`
            : `Using local directory: ${githubUrl}`, "info");

        try {
            addLog("Running static Flutter analysis...", "info");
            addLog("Sending analyzer evidence and criteria to the configured AI provider...", "info");

            const response = await fetch("/api/grade", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    github_url: githubUrl,
                    criteria_text: criteria || null
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "The grading request failed.");
            }

            const report = await response.json();
            currentReport = report;

            if (report.grading_mode === "heuristic" && report.provider_error) {
                addLog(`AI provider failed; heuristic fallback used: ${report.provider_error}`, "error");
            } else {
                addLog("AI grading completed.", "success");
            }
            addLog("Rendering report...", "success");

            setTimeout(() => {
                renderReport(report);
                switchView("results");
            }, 400);
        } catch (error) {
            addLog(`ERROR: ${error.message}`, "error");
            alert(`Error: ${error.message}`);
            switchView("welcome");
        }
    });

    function renderReport(report) {
        resultRepoTitle.innerText = report.repository;
        const mode = report.grading_mode === "ai" ? "AI" : "Heuristic fallback";
        resultRepoType.innerText = `${report.is_local ? "Local Directory" : "Git Repository"} / ${mode}`;

        const score = Number(report.overall_score || 0);
        scoreVal.innerText = score.toFixed(1);

        const stampCircle = document.querySelector(".stamp-circle");
        if (stampCircle) {
            stampCircle.className = "stamp-circle";
            if (score >= 8.0) stampCircle.classList.add("high");
            else if (score >= 5.0) stampCircle.classList.add("mid");
            else stampCircle.classList.add("low");
        }

        const providerLine = report.provider
            ? `<br><small>Provider: ${escapeHtml(report.provider)} / ${escapeHtml(report.model || "not configured")} / ${escapeHtml(report.grading_mode || "unknown")}</small>`
            : "";
        const errorLine = report.provider_error
            ? `<br><small>Provider error: ${escapeHtml(report.provider_error)}</small>`
            : "";
        aiSummaryText.innerHTML = `${escapeHtml(report.summary || "").replace(/\n/g, "<br>")}${providerLine}${errorLine}`;

        criteriaList.innerHTML = "";
        Object.entries(report.criteria_breakdown || {}).forEach(([name, data]) => {
            const item = document.createElement("div");
            item.className = "criterion-item";
            const itemScore = Number(data.score || 0);
            let scoreClass = "low";
            if (itemScore >= 8.0) scoreClass = "high";
            else if (itemScore >= 5.0) scoreClass = "mid";

            item.innerHTML = `
                <div class="criterion-header">
                    <span class="criterion-title">${escapeHtml(name)}</span>
                    <span class="criterion-score-badge ${scoreClass}">${itemScore.toFixed(1)}/10</span>
                </div>
                <div class="criterion-body hidden">
                    <p>${escapeHtml(data.feedback || "")}</p>
                </div>
            `;
            item.querySelector(".criterion-header").addEventListener("click", () => {
                item.querySelector(".criterion-body").classList.toggle("hidden");
            });
            criteriaList.appendChild(item);
        });

        warningsList.innerHTML = "";
        const warnings = report.warnings || [];
        if (warnings.length > 0) {
            warnings.forEach(warn => {
                const item = document.createElement("div");
                if (typeof warn === "string") {
                    item.className = "warning-item";
                    item.innerHTML = `<p>${escapeHtml(warn)}</p>`;
                } else {
                    item.className = "warning-item error-type";
                    item.innerHTML = `
                        <span class="warning-file">${escapeHtml(warn.file || "General")}</span>
                        <p>${escapeHtml(warn.message || warn.error || "Issue detected.")}</p>
                    `;
                }
                warningsList.appendChild(item);
            });
        } else {
            warningsList.innerHTML = `
                <div class="warning-item" style="border-left-color: var(--success); background: rgba(16, 185, 129, 0.05);">
                    <p>No serious warnings were detected by static analysis.</p>
                </div>
            `;
        }
    }

    exportMdBtn.addEventListener("click", () => {
        if (!currentReport) return;

        let md = "# Flutter Project Grading Report\n";
        md += `**Project**: ${currentReport.repository}\n`;
        md += `**Score**: ${Number(currentReport.overall_score || 0).toFixed(1)}/10\n`;
        md += `**Mode**: ${currentReport.grading_mode || "unknown"}\n`;
        md += `**Provider**: ${currentReport.provider || "unknown"} / ${currentReport.model || "not configured"}\n\n`;
        if (currentReport.provider_error) {
            md += `**Provider error**: ${currentReport.provider_error}\n\n`;
        }
        md += `## Summary\n${currentReport.summary || ""}\n\n`;
        md += "## Criteria Breakdown\n";

        Object.entries(currentReport.criteria_breakdown || {}).forEach(([name, data]) => {
            md += `### ${name}: **${Number(data.score || 0).toFixed(1)}/10**\n`;
            md += `${data.feedback || ""}\n\n`;
        });

        md += "## Warnings\n";
        if (currentReport.warnings && currentReport.warnings.length > 0) {
            currentReport.warnings.forEach(w => {
                if (typeof w === "string") {
                    md += `- [ ] ${w}\n`;
                } else {
                    md += `- [ ] **${w.file || "General"}**: ${w.message || w.error}\n`;
                }
            });
        } else {
            md += "No warnings.\n";
        }

        const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `grade_report_${Date.now()}.md`;
        a.click();
        URL.revokeObjectURL(url);
    });

    printBtn.addEventListener("click", () => {
        document.querySelectorAll(".criterion-body").forEach(body => {
            body.classList.remove("hidden");
        });
        window.print();
    });
});

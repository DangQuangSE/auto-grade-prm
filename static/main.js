document.addEventListener("DOMContentLoaded", () => {
    const gradeForm = document.getElementById("gradeForm");
    const customCriteria = document.getElementById("customCriteria");
    const welcomeView = document.getElementById("welcomeView");
    const loadingView = document.getElementById("loadingView");
    const resultsView = document.getElementById("resultsView");
    const logTerminalContent = document.getElementById("logTerminalContent");
    const scoreVal = document.getElementById("scoreVal");
    const gaugeScoreFill = document.getElementById("gaugeScoreFill");
    const aiSummaryText = document.getElementById("aiSummaryText");
    const resultRepoTitle = document.getElementById("resultRepoTitle");
    const resultRepoType = document.getElementById("resultRepoType");
    const criteriaList = document.getElementById("criteriaList");
    const warningsList = document.getElementById("warningsList");
    const exportMdBtn = document.getElementById("exportMdBtn");
    const printBtn = document.getElementById("printBtn");

    let currentReport = null;

    // Load default criteria on start
    fetch("/api/criteria")
        .then(res => res.json())
        .then(data => {
            customCriteria.value = data.criteria;
        })
        .catch(err => {
            console.error("Không thể lấy tiêu chí mặc định:", err);
        });

    // Handle Form Submit
    gradeForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const githubUrl = document.getElementById("githubUrl").value.trim();
        const geminiKey = document.getElementById("geminiKey").value.trim();
        const criteria = customCriteria.value.trim();

        // Switch to loading view
        switchView("loading");
        clearLogs();
        addLog("Khởi tạo yêu cầu chấm điểm...", "info");
        
        if (githubUrl.startsWith("http") || githubUrl.startsWith("git@")) {
            addLog(`Đang thực hiện Clone repository: ${githubUrl} ...`, "info");
        } else {
            addLog(`Đang kết nối thư mục cục bộ: ${githubUrl} ...`, "info");
        }

        try {
            addLog("Đang chạy phân tích tĩnh (Static Analysis) cấu trúc Flutter...", "info");
            
            const response = await fetch("/api/grade", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    github_url: githubUrl,
                    gemini_key: geminiKey || null,
                    custom_criteria: criteria || null
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Có lỗi xảy ra trong quá trình xử lý.");
            }

            addLog("Đang chạy đánh giá tiêu chí...", "info");
            const report = await response.json();
            currentReport = report;

            addLog("Đã tính toán điểm số thành công!", "success");
            addLog("Đang tải giao diện báo cáo...", "success");

            setTimeout(() => {
                renderReport(report);
                switchView("results");
            }, 800);

        } catch (error) {
            addLog(`LỖI: ${error.message}`, "error");
            alert(`Lỗi: ${error.message}`);
            switchView("welcome");
        }
    });

    // Helper functions
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

    // Render grading report
    function renderReport(report) {
        resultRepoTitle.innerText = report.repository;
        resultRepoType.innerText = report.is_local ? "Local Directory" : "GitHub Repository";

        // Score Gauge
        const score = report.overall_score;
        scoreVal.innerText = score.toFixed(1);
        
        // Gauge stroke offset calculation
        // stroke-dasharray = 283 (approx 2 * pi * 45)
        const offset = 283 - (283 * (score / 10));
        gaugeScoreFill.style.strokeDashoffset = offset;

        // Apply gradient or color based on score
        let strokeColor = "var(--error)";
        if (score >= 8.0) strokeColor = "var(--success)";
        else if (score >= 5.0) strokeColor = "var(--warning)";
        gaugeScoreFill.style.stroke = strokeColor;

        // AI Summary
        aiSummaryText.innerHTML = report.summary.replace(/\n/g, "<br>");

        // Clean & Render Criteria Breakdown
        criteriaList.innerHTML = "";
        for (const [name, data] of Object.entries(report.criteria_breakdown)) {
            const item = document.createElement("div");
            item.className = "criterion-item";

            // Score classification
            let scoreClass = "low";
            if (data.score >= 8.0) scoreClass = "high";
            else if (data.score >= 5.0) scoreClass = "mid";

            item.innerHTML = `
                <div class="criterion-header">
                    <span class="criterion-title">${name}</span>
                    <span class="criterion-score-badge ${scoreClass}">${data.score.toFixed(1)}/10</span>
                </div>
                <div class="criterion-body hidden">
                    <p>${data.feedback}</p>
                </div>
            `;

            // Accordion toggle
            item.querySelector(".criterion-header").addEventListener("click", () => {
                const body = item.querySelector(".criterion-body");
                body.classList.toggle("hidden");
            });

            criteriaList.appendChild(item);
        }

        // Clean & Render Warnings
        warningsList.innerHTML = "";
        if (report.warnings && report.warnings.length > 0) {
            report.warnings.forEach(warn => {
                const item = document.createElement("div");
                
                // If it's a string, or detailed object
                if (typeof warn === 'string') {
                    item.className = "warning-item";
                    item.innerHTML = `<p>${warn}</p>`;
                } else {
                    // Check warning vs error types
                    const isNaming = warn.error && warn.error.includes("convention");
                    item.className = `warning-item ${isNaming ? "" : "error-type"}`;
                    item.innerHTML = `
                        <span class="warning-file">${warn.file || "Quy tắc chung"}</span>
                        <p>${warn.message || warn.error || "Phát hiện Anti-pattern."}</p>
                    `;
                }
                warningsList.appendChild(item);
            });
        } else {
            warningsList.innerHTML = `
                <div class="warning-item" style="border-left-color: var(--success); background: rgba(16, 185, 129, 0.05);">
                    <p>🎉 Tuyệt vời! Không phát hiện cảnh báo nghiêm trọng nào từ phân tích tĩnh.</p>
                </div>
            `;
        }
    }

    // Export Markdown Report
    exportMdBtn.addEventListener("click", () => {
        if (!currentReport) return;

        let md = `# BÁO CÁO ĐÁNH GIÁ DỰ ÁN FLUTTER\n`;
        md += `**Dự án**: ${currentReport.repository}\n`;
        md += `**Điểm tổng hợp**: ${currentReport.overall_score.toFixed(1)}/10\n\n`;
        md += `## 1. Nhận xét tổng quát\n${currentReport.summary}\n\n`;
        md += `## 2. Chi tiết 15 tiêu chí chấm điểm\n`;

        for (const [name, data] of Object.entries(currentReport.criteria_breakdown)) {
            md += `### - ${name}: **${data.score.toFixed(1)}/10**\n`;
            md += `*Nhận xét*: ${data.feedback}\n\n`;
        }

        md += `## 3. Danh sách lỗi/Cảnh báo cần khắc phục\n`;
        if (currentReport.warnings && currentReport.warnings.length > 0) {
            currentReport.warnings.forEach(w => {
                if (typeof w === 'string') {
                    md += `- [ ] ${w}\n`;
                } else {
                    md += `- [ ] **${w.file || "Chung"}**: ${w.message || w.error}\n`;
                }
            });
        } else {
            md += `Không có cảnh báo nào.\n`;
        }

        const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `grade_report_${Date.now()}.md`;
        a.click();
    });

    // Print Report
    printBtn.addEventListener("click", () => {
        // Expand all criteria sections before printing
        document.querySelectorAll(".criterion-body").forEach(body => {
            body.classList.remove("hidden");
        });
        window.print();
    });
});

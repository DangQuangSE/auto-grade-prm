document.addEventListener("DOMContentLoaded", () => {
    const gradeForm = document.getElementById("gradeForm");
    const customCriteria = document.getElementById("customCriteria");
    const criteriaFile = document.getElementById("criteriaFile");
    const welcomeView = document.getElementById("welcomeView");
    const loadingView = document.getElementById("loadingView");
    const errorView = document.getElementById("errorView");
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
    const langSwitch = document.getElementById("langSwitch");
    const retryGradeBtn = document.getElementById("retryGradeBtn");
    const toastContainer = document.getElementById("toastContainer");

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

    function applyStaticTranslations() {
        document.documentElement.lang = currentLang;
        document.querySelectorAll("[data-i18n]").forEach(el => {
            el.textContent = t(el.dataset.i18n);
        });
        document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
            el.placeholder = t(el.dataset.i18nPlaceholder);
        });
        document.querySelectorAll("[data-i18n-title]").forEach(el => {
            el.title = t(el.dataset.i18nTitle);
        });
        langSwitch.querySelectorAll(".lang-btn").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.lang === currentLang);
        });
    }

    function setLang(lang) {
        currentLang = lang;
        localStorage.setItem("lang", lang);
        applyStaticTranslations();
        renderProviderStatus();
        validateCriteria();
        if (currentReport) {
            renderReport(currentReport);
        }
    }

    langSwitch.addEventListener("click", (e) => {
        const btn = e.target.closest(".lang-btn");
        if (!btn) return;
        setLang(btn.dataset.lang);
    });

    function validateCriteria() {
        const hasContent = customCriteria.value.trim() !== "";
        submitBtn.disabled = !hasContent;
        if (!hasContent) {
            criteriaHint.textContent = t("hint_criteria_missing");
            criteriaHint.style.color = "var(--margin-red)";
            criteriaHint.style.fontWeight = "bold";
        } else {
            criteriaHint.textContent = t("hint_criteria_ready");
            criteriaHint.style.color = "var(--graphite)";
            criteriaHint.style.fontWeight = "normal";
        }
    }

    function switchView(viewName) {
        welcomeView.classList.add("hidden");
        loadingView.classList.add("hidden");
        errorView.classList.add("hidden");
        resultsView.classList.add("hidden");

        if (viewName === "welcome") welcomeView.classList.remove("hidden");
        if (viewName === "loading") loadingView.classList.remove("hidden");
        if (viewName === "error") errorView.classList.remove("hidden");
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

    function showToast(message, type = "error", duration = null) {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.setAttribute("role", type === "error" ? "alert" : "status");

        const text = document.createElement("span");
        text.className = "toast-message";
        text.textContent = message;

        const closeButton = document.createElement("button");
        closeButton.type = "button";
        closeButton.className = "toast-close";
        closeButton.setAttribute("aria-label", t("toast_close"));
        closeButton.textContent = "×";

        let removed = false;
        let timerId = null;
        let startedAt = 0;
        let remaining = duration ?? (type === "error" ? 10000 : 6000);

        const removeToast = () => {
            if (removed) return;
            removed = true;
            if (timerId !== null) window.clearTimeout(timerId);
            toast.classList.add("toast-leaving");
            const fallbackId = window.setTimeout(() => toast.remove(), 300);
            toast.addEventListener("animationend", () => {
                window.clearTimeout(fallbackId);
                toast.remove();
            }, { once: true });
        };
        const scheduleRemoval = () => {
            if (removed || remaining <= 0) return removeToast();
            startedAt = Date.now();
            timerId = window.setTimeout(removeToast, remaining);
        };
        const pauseRemoval = () => {
            if (timerId === null) return;
            window.clearTimeout(timerId);
            timerId = null;
            remaining = Math.max(0, remaining - (Date.now() - startedAt));
        };
        const resumeRemoval = () => {
            if (toast.matches(":hover") || toast.contains(document.activeElement)) return;
            scheduleRemoval();
        };

        closeButton.addEventListener("click", removeToast);
        toast.addEventListener("mouseenter", pauseRemoval);
        toast.addEventListener("mouseleave", resumeRemoval);
        toast.addEventListener("focusin", pauseRemoval);
        toast.addEventListener("focusout", resumeRemoval);
        toast.append(text, closeButton);
        toastContainer.appendChild(toast);
        scheduleRemoval();
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
        const data = await readApiResponse(response, "Could not read the criteria file.");
        if (!response.ok) throw new Error(data.detail || "Could not read the criteria file.");
        return data.criteria || "";
    }

    async function readApiResponse(response, fallbackMessage) {
        const body = await response.text();
        if (!body) throw new Error(fallbackMessage);
        try {
            return JSON.parse(body);
        } catch (_) {
            throw new Error(body.trim() || fallbackMessage);
        }
    }

    function renderProviderStatus() {
        if (!providerInfo) {
            providerStatus.classList.add("missing");
            providerStatusText.textContent = t("provider_unavailable");
            return;
        }
        const primaryConfigured = providerInfo.api_key_configured;
        const fallbackConfigured = providerInfo.fallback_api_key_configured;
        const available = primaryConfigured || fallbackConfigured;
        providerStatus.classList.toggle("configured", available);
        providerStatus.classList.toggle("missing", !available);
        if (!primaryConfigured && fallbackConfigured) {
            providerStatusText.textContent = `${providerInfo.fallback_provider}: ${providerInfo.fallback_model} ${t("provider_configured_suffix")} ${t("provider_fallback_suffix")}`;
        } else {
            const suffix = primaryConfigured ? t("provider_configured_suffix") : t("provider_missing_suffix");
            providerStatusText.textContent = `${providerInfo.provider}: ${providerInfo.model} ${suffix}`;
        }
    }

    async function loadProviderInfo() {
        try {
            const response = await fetch("/api/provider");
            providerInfo = await readApiResponse(response, t("provider_unavailable"));
        } catch (error) {
            providerInfo = null;
        }
        renderProviderStatus();
    }

    customCriteria.addEventListener("input", validateCriteria);

    criteriaFile.addEventListener("change", async () => {
        const file = criteriaFile.files && criteriaFile.files[0];
        if (!file) return;
        const lowerName = file.name.toLowerCase();
        const validName = lowerName.endsWith(".docx") || lowerName.endsWith(".md") || lowerName.endsWith(".txt");
        if (!validName) {
            showToast(t("alert_invalid_file"));
            criteriaFile.value = "";
            return;
        }
        try {
            criteriaHint.textContent = t("hint_reading_file");
            customCriteria.value = await extractCriteriaFile(file);
            validateCriteria();
        } catch (error) {
            showToast(t("alert_read_file_error", { message: error.message }));
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

    applyStaticTranslations();
    loadProviderInfo();

    retryGradeBtn.addEventListener("click", () => {
        gradeForm.requestSubmit();
    });

    gradeForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const githubUrl = document.getElementById("githubUrl").value.trim();
        const criteria = customCriteria.value.trim();

        switchView("loading");
        clearLogs();
        addLog(t("log_preparing"), "info");
        addLog(
            githubUrl.startsWith("http") || githubUrl.startsWith("git@")
                ? t("log_cloning", { url: githubUrl })
                : t("log_local", { url: githubUrl }),
            "info"
        );

        try {
            addLog(t("log_analysis"), "info");
            addLog(t("log_sending"), "info");

            const response = await fetch("/api/grade", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    github_url: githubUrl,
                    criteria_text: criteria || null
                })
            });

            if (response.status === 503 || response.status === 504) {
                addLog(t("log_ai_unavailable"), "error");
                switchView("error");
                errorView.focus();
                return;
            }

            const report = await readApiResponse(response, "The grading request failed.");
            if (!response.ok) {
                throw new Error(report.detail || "The grading request failed.");
            }
            currentReport = report;

            addLog(t("log_ai_done"), "success");
            addLog(t("log_rendering"), "success");

            setTimeout(() => {
                renderReport(report);
                switchView("results");
            }, 400);
        } catch (error) {
            addLog(t("log_error_prefix", { message: error.message }), "error");
            showToast(t("alert_grade_error", { message: error.message }));
            switchView("welcome");
        }
    });

    function renderReport(report) {
        resultRepoTitle.innerText = report.repository;
        const mode = report.grading_mode === "ai" ? t("mode_ai") : t("mode_heuristic");
        const repoType = report.is_local ? t("repo_local") : t("repo_git");
        resultRepoType.innerText = `${repoType} / ${mode}`;

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
            ? `<br><small>${escapeHtml(t("provider_line", {
                provider: report.provider,
                model: report.model || t("model_not_configured"),
                mode: report.grading_mode || t("mode_unknown"),
            }))}</small>`
            : "";
        const errorLine = report.provider_error
            ? `<br><small>${escapeHtml(t("provider_error_line", { error: report.provider_error }))}</small>`
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

            const suggestionHtml = data.suggestion
                ? `<div class="criterion-suggestion"><span class="suggestion-label">${escapeHtml(t("label_suggestion"))}</span><p>${escapeHtml(data.suggestion).replace(/\n/g, "<br>")}</p></div>`
                : "";
            item.innerHTML = `
                <div class="criterion-header">
                    <span class="criterion-title">${escapeHtml(name)}</span>
                    <span class="criterion-score-badge ${scoreClass}">${itemScore.toFixed(1)}/10</span>
                </div>
                <div class="criterion-body hidden">
                    <p>${escapeHtml(data.feedback || "")}</p>
                    ${suggestionHtml}
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
                        <span class="warning-file">${escapeHtml(warn.file || t("general_file"))}</span>
                        <p>${escapeHtml(warn.message || warn.error || "Issue detected.")}</p>
                    `;
                }
                warningsList.appendChild(item);
            });
        } else {
            warningsList.innerHTML = `
                <div class="warning-item" style="border-left-color: var(--success); background: rgba(16, 185, 129, 0.05);">
                    <p>${escapeHtml(t("no_warnings"))}</p>
                </div>
            `;
        }
    }

    exportMdBtn.addEventListener("click", () => {
        if (!currentReport) return;

        const mode = currentReport.grading_mode || t("mode_unknown");
        const model = currentReport.model || t("model_not_configured");

        let md = `${t("md_title")}\n`;
        md += `${t("md_project")} ${currentReport.repository}\n`;
        md += `${t("md_score")} ${Number(currentReport.overall_score || 0).toFixed(1)}/10\n`;
        md += `${t("md_mode")} ${mode}\n`;
        md += `${t("md_provider")} ${currentReport.provider || t("mode_unknown")} / ${model}\n\n`;
        if (currentReport.provider_error) {
            md += `${t("md_provider_error")} ${currentReport.provider_error}\n\n`;
        }
        md += `${t("md_summary_heading")}\n${currentReport.summary || ""}\n\n`;
        md += `${t("md_breakdown_heading")}\n`;

        Object.entries(currentReport.criteria_breakdown || {}).forEach(([name, data]) => {
            md += `### ${name}: **${Number(data.score || 0).toFixed(1)}/10**\n`;
            md += `${data.feedback || ""}\n\n`;
            if (data.suggestion) {
                md += `${t("md_suggestion_label")}\n${data.suggestion}\n\n`;
            }
        });

        md += `${t("md_warnings_heading")}\n`;
        if (currentReport.warnings && currentReport.warnings.length > 0) {
            currentReport.warnings.forEach(w => {
                if (typeof w === "string") {
                    md += `- [ ] ${w}\n`;
                } else {
                    md += `- [ ] **${w.file || t("general_file")}**: ${w.message || w.error}\n`;
                }
            });
        } else {
            md += `${t("md_no_warnings")}\n`;
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

    // Resizable Sidebar logic
    const sidebar = document.querySelector(".sidebar");
    const resizer = document.getElementById("sidebarResizer");

    if (sidebar && resizer) {
        // Load saved sidebar width
        const savedWidth = localStorage.getItem("sidebarWidth");
        if (savedWidth) {
            sidebar.style.width = savedWidth + "px";
        }

        resizer.addEventListener("mousedown", (e) => {
            e.preventDefault();
            resizer.classList.add("active");
            document.body.style.cursor = "col-resize";

            function onMouseMove(e) {
                let newWidth = e.clientX;
                // Constraints check
                if (newWidth >= 280 && newWidth <= 600) {
                    sidebar.style.width = newWidth + "px";
                    localStorage.setItem("sidebarWidth", newWidth);
                }
            }

            function onMouseUp() {
                resizer.classList.remove("active");
                document.body.style.cursor = "";
                document.removeEventListener("mousemove", onMouseMove);
                document.removeEventListener("mouseup", onMouseUp);
            }

            document.addEventListener("mousemove", onMouseMove);
            document.addEventListener("mouseup", onMouseUp);
        });
    }
});

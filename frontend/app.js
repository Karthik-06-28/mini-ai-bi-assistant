/**
 * app.js — Frontend Application Logic for Mini AI BI Assistant
 * 
 * Features:
 * - Real-time health check & status pill
 * - Chat message history & auto-scroll
 * - Dynamic Chart.js rendering (bar, line, doughnut)
 * - Collapsible reasoning steps, SQL display with copy, and source attribution
 * - Supporting data table with scroll & clean formatting
 * - Zero-hallucination indicators and out-of-scope question handling
 */

let activeChart = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    checkHealth();
    setupEventListeners();
});

/**
 * Health check on backend server and database
 */
async function checkHealth() {
    const statusText = document.getElementById("status-text");
    const statusDot = document.querySelector(".status-dot");

    try {
        const response = await fetch("/api/health");
        const data = await response.json();

        if (data.status === "healthy" && data.database_loaded) {
            statusText.textContent = `Online (${data.row_count} transactions)`;
            statusDot.classList.add("connected");
        } else {
            statusText.textContent = "DB Not Loaded";
            statusDot.style.background = "var(--accent-amber)";
        }
    } catch (err) {
        statusText.textContent = "Offline";
        statusDot.style.background = "var(--accent-rose)";
    }
}

/**
 * Setup keyboard and click listeners
 */
function setupEventListeners() {
    const input = document.getElementById("question-input");
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendQuestion();
        }
    });
}

/**
 * Click handler for suggestion buttons on the welcome screen
 */
function askSuggestion(button) {
    const textSpan = button.querySelector("span:last-child");
    const questionText = textSpan ? textSpan.innerText : button.innerText;
    document.getElementById("question-input").value = questionText;
    sendQuestion();
}

/**
 * Send the user question to the backend /api/ask endpoint
 */
async function sendQuestion() {
    const input = document.getElementById("question-input");
    const sendBtn = document.getElementById("send-btn");
    const question = input.value.trim();

    if (!question) return;

    // Clear input & disable button
    input.value = "";
    input.disabled = true;
    sendBtn.disabled = true;

    // Hide welcome card on first question
    const welcomeCard = document.getElementById("welcome-card");
    if (welcomeCard) {
        welcomeCard.style.display = "none";
    }

    const messagesContainer = document.getElementById("chat-messages");

    // Append User Message Bubble
    appendUserMessage(question);

    // Append Loading State Card
    const loadingCardId = "loading-" + Date.now();
    appendLoadingCard(loadingCardId);
    scrollToBottom();

    try {
        const response = await fetch("/api/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        // Remove loading card
        removeElementById(loadingCardId);

        if (response.ok && data.success) {
            appendAssistantResponse(data);
        } else if (data.is_answerable === false) {
            appendOutOfScopeCard(data);
        } else {
            appendErrorCard(data.error || "An unexpected error occurred.", data.step_failed, data.sql_query);
        }
    } catch (err) {
        removeElementById(loadingCardId);
        appendErrorCard("Failed to communicate with server. Please check if backend is running.", "Network Connection");
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
        scrollToBottom();
    }
}

/**
 * Append user message bubble to chat
 */
function appendUserMessage(text) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-message user-message";
    div.innerHTML = `<div class="user-bubble">${escapeHtml(text)}</div>`;
    container.appendChild(div);
}

/**
 * Append temporary loading card while awaiting AI + SQL execution
 */
function appendLoadingCard(id) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.id = id;
    div.className = "chat-message loading-card";
    div.innerHTML = `
        <div class="loading-dots">
            <div class="dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <span class="loading-text">Analyzing query with Gemini & running deterministic SQL...</span>
        </div>
    `;
    container.appendChild(div);
}

/**
 * Remove an element by its ID
 */
function removeElementById(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

/**
 * Append complete Assistant response with Answer, Reasoning, SQL, Source, Table & Chart
 */
function appendAssistantResponse(data) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-message response-card";

    const responseId = "resp-" + Date.now();

    // Subtle side Source pill
    const source = data.source || {};
    const rowCount = source.rows_returned !== undefined ? source.rows_returned : (data.data ? data.data.length : 1);
    const sourceBadgeHtml = `
        <div class="source-side-badge">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/>
            </svg>
            <span>Source: <strong>${escapeHtml(source.database || "SQLite")}</strong> &bull; Table: <strong>${escapeHtml(source.table || "sales_data")}</strong> (${rowCount} row${rowCount === 1 ? '' : 's'})</span>
        </div>
    `;

    // Chart container (only when multi-row comparisons or trends)
    let chartContainerHtml = "";
    const shouldRenderChart = canRenderChart(data);
    if (shouldRenderChart) {
        chartContainerHtml = `
            <div class="chart-container" style="margin-top: 14px;">
                <canvas id="chart-${responseId}"></canvas>
            </div>
        `;
    }

    // Clean, executive UI: Answer + Source side badge
    div.innerHTML = `
        <div class="response-header-bar">
            ${sourceBadgeHtml}
        </div>
        <div class="answer-text">${formatMarkdownText(data.answer)}</div>
        ${chartContainerHtml}
    `;

    container.appendChild(div);

    // Render Chart.js if multi-row trend
    if (shouldRenderChart) {
        renderChart(`chart-${responseId}`, data);
    }
}

/**
 * Append out-of-scope / unanswerable notification card
 */
function appendOutOfScopeCard(data) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-message not-answerable-card";

    let stepsHtml = "";
    if (data.reasoning_steps) {
        stepsHtml = `
            <ul class="reasoning-steps" style="margin-top: 10px;">
                ${data.reasoning_steps.map(s => `<li>${escapeHtml(s)}</li>`).join("")}
            </ul>
        `;
    }

    div.innerHTML = `
        <div class="na-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            Data Not Found in Sales Records
        </div>
        <div class="na-reason">${escapeHtml(data.reason || "The question cannot be answered from the available sales dataset.")}</div>
        ${stepsHtml}
        <div class="na-suggestion">
            <strong>💡 Suggestion:</strong> ${escapeHtml(data.suggestion || "Try asking about revenue, products, regions, or monthly trends.")}
        </div>
    `;

    container.appendChild(div);
}

/**
 * Append validation or execution error card
 */
function appendErrorCard(message, stepFailed, sql) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-message error-card";

    let sqlBlock = "";
    if (sql) {
        sqlBlock = `
            <div style="margin-top: 10px;">
                <pre class="sql-code"><code>${escapeHtml(sql)}</code></pre>
            </div>
        `;
    }

    div.innerHTML = `
        <div class="error-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            ${escapeHtml(stepFailed ? `Safety/Execution Check: ${stepFailed}` : "Query Execution Stopped")}
        </div>
        <div class="error-message">${escapeHtml(message)}</div>
        ${sqlBlock}
        <div class="suggestion">
            <strong>Safe Operation Enforcement:</strong> Destructive operations (DROP, DELETE, UPDATE) and non-existent schemas are strictly blocked to protect data integrity.
        </div>
    `;

    container.appendChild(div);
}

/**
 * Determine if results should have an interactive Chart.js chart
 */
function canRenderChart(data) {
    if (!data.data || data.data.length < 2) return false;
    const chartType = (data.chart_type || "").toLowerCase();
    return ["bar", "line", "pie", "doughnut"].includes(chartType) || data.data.length >= 2;
}

/**
 * Render Chart.js chart based on query results
 */
function renderChart(canvasId, responseData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const data = responseData.data;
    const keys = Object.keys(data[0]);

    if (keys.length < 2) return;

    // Detect label key (string) and value key (numeric)
    let labelKey = keys[0];
    let valueKey = keys[1];

    for (let k of keys) {
        if (typeof data[0][k] === "number") {
            valueKey = k;
        } else {
            labelKey = k;
        }
    }

    const labels = data.map(item => String(item[labelKey]));
    const values = data.map(item => Number(item[valueKey]) || 0);

    let chartType = responseData.chart_type || "bar";
    if (chartType === "table" || chartType === "number") {
        chartType = labels.length <= 6 ? "bar" : "line";
    }

    // Modern color palette
    const bgColors = [
        "rgba(59, 130, 246, 0.75)",
        "rgba(139, 92, 246, 0.75)",
        "rgba(16, 185, 129, 0.75)",
        "rgba(245, 158, 11, 0.75)",
        "rgba(244, 63, 94, 0.75)",
        "rgba(14, 165, 233, 0.75)",
        "rgba(168, 85, 247, 0.75)"
    ];

    const borderColors = [
        "#3b82f6",
        "#8b5cf6",
        "#10b981",
        "#f59e0b",
        "#f43f5e",
        "#0ea5e9",
        "#a855f7"
    ];

    try {
        new Chart(canvas, {
            type: chartType === "pie" ? "doughnut" : chartType,
            data: {
                labels: labels,
                datasets: [{
                    label: formatHeader(valueKey),
                    data: values,
                    backgroundColor: chartType === "doughnut" || chartType === "pie" ? bgColors : "rgba(59, 130, 246, 0.65)",
                    borderColor: chartType === "doughnut" || chartType === "pie" ? borderColors : "#3b82f6",
                    borderWidth: 2,
                    borderRadius: chartType === "bar" ? 6 : 0,
                    tension: 0.35,
                    fill: chartType === "line"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: chartType === "doughnut" || chartType === "pie",
                        labels: { color: "#94a3b8", font: { family: "Inter", size: 12 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let val = context.raw;
                                if (valueKey.toLowerCase().includes("revenue") || valueKey.toLowerCase().includes("price") || valueKey.toLowerCase().includes("sales")) {
                                    return ` ₹${Number(val).toLocaleString("en-IN")}`;
                                }
                                return ` ${val.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: (chartType === "doughnut" || chartType === "pie") ? {} : {
                    x: {
                        ticks: { color: "#94a3b8", font: { family: "Inter" } },
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    },
                    y: {
                        ticks: {
                            color: "#94a3b8",
                            font: { family: "Inter" },
                            callback: function(val) {
                                if (valueKey.toLowerCase().includes("revenue") || valueKey.toLowerCase().includes("price")) {
                                    return `₹${val.toLocaleString("en-IN")}`;
                                }
                                return val;
                            }
                        },
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    }
                }
            }
        });
    } catch (e) {
        console.warn("Chart render skipped:", e);
    }
}

/**
 * Toggle collapsible section
 */
function toggleCollapsible(header) {
    header.classList.toggle("open");
    const body = header.nextElementSibling;
    if (body) {
        body.classList.toggle("open");
    }
}

/**
 * Copy SQL to clipboard
 */
function copySql(btn, sql) {
    navigator.clipboard.writeText(sql).then(() => {
        const originalText = btn.innerText;
        btn.innerText = "Copied! ✓";
        setTimeout(() => { btn.innerText = originalText; }, 2000);
    });
}

/**
 * Utilities for formatting numbers and text
 */
function formatCellValue(colName, value) {
    if (value === null || value === undefined) return '<span style="color: #64748b;">NULL</span>';
    if (typeof value === "number") {
        if (colName.toLowerCase().includes("revenue") || colName.toLowerCase().includes("price") || colName.toLowerCase().includes("discount") || colName.toLowerCase().includes("sales")) {
            return `₹${value.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
        }
        return value.toLocaleString();
    }
    return escapeHtml(String(value));
}

function formatHeader(col) {
    return col.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

function formatMarkdownText(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);
    // Bold **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Bullet lists
    formatted = formatted.replace(/\n\s*•\s*/g, "<br>• ");
    formatted = formatted.replace(/\n\s*-\s*/g, "<br>• ");
    return formatted.replace(/\n/g, "<br>");
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function escapeForAttribute(str) {
    if (!str) return "";
    return str.replace(/'/g, "\\'").replace(/"/g, "&quot;").replace(/\n/g, " ");
}

function scrollToBottom() {
    const chatArea = document.getElementById("chat-area");
    setTimeout(() => {
        chatArea.scrollTop = chatArea.scrollHeight;
    }, 100);
}

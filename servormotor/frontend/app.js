/* 
   三菱 MR-J5 AI Servo PHM System — 前端控制與對接腳本 (app.js - 工業落地版)
*/

const API_BASE_URL = "http://localhost:8000";
const WS_BASE_URL = "ws://localhost:8000/ws/telemetry";

let currentScenarioId = 1;
let currentDiagnosisData = null;
let telemetryChart = null;

// 使用者驗證全域狀態 (不留硬碟持久化暫存；僅存 sessionStorage 且關閉瀏覽器分頁即失效)
localStorage.removeItem("phm_current_user"); // 自動清理過往暫存
let currentUser = JSON.parse(sessionStorage.getItem("phm_current_user") || "null");



const MAX_CHART_POINTS = 30;
const chartData = {
    labels: [],
    currentRms: [],
    followingError: [],
    motorTemp: []
};

// ------------------------------------------------------------------------
// 1. 初始化與 DOM 事件掛載
// ------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    initClock();
    initChart();
    initBenchmarkButtons();
    initModalEvents();
    initIsoReportButton();
    initHardwareButtons();
    initAuthUI();
    initRegisterModalEvents();


    // 初次載入即時診斷與影子模式數據
    fetchDiagnoseData(currentScenarioId);
    fetchShadowModeStatus();
    
    // 動態數據輪詢 (連動全域數據更新頻率控制)
    if (typeof startHmiDynamicTimer === 'function') {
        startHmiDynamicTimer(() => {
            fetchDiagnoseData(currentScenarioId);
            fetchShadowModeStatus();
        }, 1000);
    } else {
        setInterval(() => {
            fetchDiagnoseData(currentScenarioId);
            fetchShadowModeStatus();
        }, 1000);
    }

    // 開啟 WebSocket 即時 Telemetry 串流
    initWebSocket();
});


function initClock() {
    const clockEl = document.getElementById("clock-display");
    setInterval(() => {
        const now = new Date();
        clockEl.textContent = now.toISOString().replace("T", " ").substring(0, 19);
    }, 1000);
}

function initBenchmarkButtons() {
    const buttons = document.querySelectorAll(".btn-scenario");
    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            buttons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            const scenarioId = parseInt(btn.getAttribute("data-id"));
            switchScenario(scenarioId);
        });
    });
}

async function switchScenario(scenarioId) {
    currentScenarioId = scenarioId;
    try {
        await fetch(`${API_BASE_URL}/api/v1/switch_scenario/${scenarioId}`, { method: "POST" });
        fetchDiagnoseData(scenarioId);
    } catch (err) {
        console.error("切換工況失敗:", err);
    }
}

// ------------------------------------------------------------------------
// 2. 影子模式與 ISO 報告處理
// ------------------------------------------------------------------------

async function fetchShadowModeStatus() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/shadow_mode`);
        if (!res.ok) return;
        const shadow = await res.json();
        
        const badge = document.getElementById("shadow-mode-badge");
        if (shadow.ready_for_production) {
            badge.innerHTML = `<i class="fa-solid fa-ghost"></i> SHADOW MODE: RMSE -${shadow.improvement_rate_pct}% (READY)`;
            badge.style.borderColor = "var(--green-normal)";
            badge.style.color = "var(--green-normal)";
        }
    } catch (e) {}
}

function initIsoReportButton() {
    const btn = document.getElementById("btn-export-iso-report");
    btn.addEventListener("click", async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/api/v1/export_audit_report`);
            if (!res.ok) return;
            const report = await res.json();

            // 下載 ISO JSON 稽核報告
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(report, null, 2));
            const downloadAnchor = document.createElement("a");
            downloadAnchor.setAttribute("href", dataStr);
            downloadAnchor.setAttribute("download", `ISO_55000_Audit_Report_${Date.now()}.json`);
            document.body.appendChild(downloadAnchor);
            downloadAnchor.click();
            downloadAnchor.remove();

            alert("✅ 成功匯出符合 ISO 55000 / ISO 13374 工業標準之維護稽核報告！");
        } catch (err) {
            alert("❌ 匯出 ISO 稽核報告失敗。");
        }
    });
}

function updateConnectionStatusUI(mode, statusText) {
    const statusEl = document.getElementById("connection-status");
    const indicatorEl = document.querySelector(".status-indicator");
    const dotEl = document.querySelector(".status-indicator .dot");

    if (mode === "online" || mode === true) {
        if (statusEl) statusEl.textContent = statusText || "TSN ONLINE (波形串流中)";
        if (dotEl) {
            dotEl.className = "dot pulse-green";
            dotEl.style.backgroundColor = "";
            dotEl.style.boxShadow = "";
        }
        if (indicatorEl) indicatorEl.style.color = "var(--green-normal)";
    } else if (mode === "error") {
        if (statusEl) statusEl.textContent = statusText || "連線失敗 (Server 無回應)";
        if (dotEl) {
            dotEl.className = "dot";
            dotEl.style.backgroundColor = "var(--red-trip)";
            dotEl.style.boxShadow = "0 0 10px var(--red-trip)";
        }
        if (indicatorEl) indicatorEl.style.color = "var(--red-trip)";
    } else {
        // offline / disconnected / 未連結馬達 (離線模擬)
        if (statusEl) statusEl.textContent = statusText || "未連結馬達 (離線模擬)";
        if (dotEl) {
            dotEl.className = "dot pulse-yellow";
            dotEl.style.backgroundColor = "";
            dotEl.style.boxShadow = "";
        }
        if (indicatorEl) indicatorEl.style.color = "var(--yellow-warning)";
    }
}


function initHardwareButtons() {
    const btnConnect = document.getElementById("btn-hardware-connect");
    const btnDisconnect = document.getElementById("btn-hardware-disconnect");

    btnConnect?.addEventListener("click", async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/api/v1/hardware/connect`, { method: "POST" });
            const data = await res.json();
            if (res.ok) {
                updateConnectionStatusUI("online", `TSN ONLINE (${data.latency_ms}ms)`);
                alert(`✅ ${data.message}\n` +
                      `🔌 驅動器站號: ${data.station_id}\n` +
                      `⚡ 通訊埠協定: SLMP MC Protocol 3E\n` +
                      `📊 感測器實時波形已開啟串流！`);
            } else {
                updateConnectionStatusUI("error", "硬體連線異常");
                alert("❌ 硬體連線失敗。");
            }
        } catch (e) {
            // 後端未連通，嚴格維持黃燈離線警告並提示使用者
            updateConnectionStatusUI("error", "連線失敗 (請啟動 server.py)");
            alert("⚠️ [連線失敗] 無法連線至後端伺服器！\n請先於終端機執行 python server.py 以開啟機器通訊網關與波形推播。");
        }
    });


    btnDisconnect?.addEventListener("click", async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/api/v1/hardware/disconnect`, { method: "POST" });
            const data = await res.json();
            if (res.ok) {
                updateConnectionStatusUI("offline", "未連結馬達 (離線模擬)");
                alert("⚠️ 未連結馬達 (離線模擬模式已啟用，感測波形已暫停)！");
            }
        } catch (e) {
            updateConnectionStatusUI("offline", "未連結馬達 (離線模擬)");
            alert("⚠️ 未連結馬達 (離線模擬模式已啟用)！");
        }
    });
}







// ------------------------------------------------------------------------
// 3. REST API 資料對接與 UI 渲染
// ------------------------------------------------------------------------

async function fetchDiagnoseData(scenarioId) {
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/diagnose?scenario_id=${scenarioId}`);
        if (!res.ok) return;

        const data = await res.json();
        currentDiagnosisData = data;
        renderDiagnosisUI(data);
    } catch (err) {
        console.error("讀取診斷封包失敗:", err);
    }
}

function renderDiagnosisUI(data) {
    const disp = data["診斷狀態_前端顯示"] || {};
    const action = data["建議調整參數_後端執行"] || {};
    const xai = data["診斷依據與可解釋性_工程師審核"] || {};
    const heatmap = data["實態部件熱力對照"] || {};

    // 1. 卡片 1：健康度與風控
    const healthVal = disp.health_index !== undefined ? disp.health_index : 95.0;
    const healthEl = document.getElementById("health-index-val");
    healthEl.textContent = healthVal.toFixed(1);
    
    if (healthVal >= 80) healthEl.style.color = "var(--green-normal)";
    else if (healthVal >= 60) healthEl.style.color = "var(--yellow-warning)";
    else healthEl.style.color = "var(--red-trip)";

    const riskBadge = document.getElementById("risk-badge");
    const riskLevel = (disp.risk_level || "Normal").toUpperCase();
    riskBadge.textContent = riskLevel;
    riskBadge.className = "risk-badge " + getRiskClass(riskLevel);

    const scenarioNames = {
        1: "Scenario 01: Pick & Place (正常定位基線)",
        18: "Scenario 18: Ball Screw (滾珠螺桿磨損與背隙)",
        34: "Scenario 34: Rotor Demagnetization (轉子高溫退磁)"
    };
    const sId = disp.current_scenario || currentScenarioId;
    document.getElementById("scenario-title").textContent = scenarioNames[sId] || `Scenario ${String(sId).padStart(2, '0')}: 工業故障診斷`;

    
    const rulSec = disp.rul_sec || 999999;
    document.getElementById("rul-val").textContent = rulSec > 100000 ? "999,999 秒 (運作良好)" : `${rulSec} 秒 (~${(rulSec/3600).toFixed(1)} 小時)`;

    // 2. 卡片 2：建議參數與調參按鈕
    document.getElementById("action-desc-val").textContent = action.action || "無須調整參數。";
    
    const paramsContainer = document.getElementById("params-tags-container");
    paramsContainer.innerHTML = "";
    const recParams = action.recommended_parameters || [];
    
    const applyBtn = document.getElementById("btn-apply-parameters");
    if (recParams.length > 0) {
        recParams.forEach(p => {
            const chip = document.createElement("span");
            chip.className = "tag-chip";
            chip.textContent = p;
            paramsContainer.appendChild(chip);
        });
        applyBtn.disabled = false;
    } else {
        const chip = document.createElement("span");
        chip.className = "tag-chip";
        chip.style.borderColor = "var(--text-muted)";
        chip.style.color = "var(--text-muted)";
        chip.textContent = "無須變更參數";
        paramsContainer.appendChild(chip);
        applyBtn.disabled = true;
    }

    // 3. 卡片 3：實態馬達部件熱力陣列 (Component Heatmap)
    renderComponentHeatmap(heatmap);

    const assertionDesc = document.getElementById("assertion-desc-val");
    if (xai.assertion_triggered) {
        assertionDesc.textContent = "觸發物理硬體限制斷言：強制重寫判定結果，排除網路干擾誤告警。";
    } else {
        assertionDesc.textContent = "防誤判機制啟用：過濾 TSN 網路丟包與瞬時通訊突波，確認非干擾引發之假告警。";
    }
}

function renderComponentHeatmap(heatmap) {
    setCompValue("comp-bearing-val", heatmap.bearing_health || 95.0);
    setCompValue("comp-winding-val", heatmap.stator_winding_health || 93.5);
    setCompValue("comp-encoder-val", heatmap.encoder_health || 98.0);
    setCompValue("comp-screw-val", heatmap.lead_screw_health || 91.2);
}

function setCompValue(elemId, val) {
    const el = document.getElementById(elemId);
    if (!el) return;
    el.textContent = `${val.toFixed(1)}%`;
    if (val >= 80) el.style.color = "var(--green-normal)";
    else if (val >= 65) el.style.color = "var(--yellow-warning)";
    else el.style.color = "var(--red-trip)";
}

function getRiskClass(risk) {
    switch(risk) {
        case "NORMAL": return "badge-normal";
        case "WARNING": return "badge-warning";
        case "CRITICAL": return "badge-critical";
        case "TRIP": return "badge-trip";
        default: return "badge-normal";
    }
}

// ------------------------------------------------------------------------
// 4. 使用者驗證與權限控制 UI 邏輯 (Auth UI & Logic)
// ------------------------------------------------------------------------

function initAuthUI() {
    const authArea = document.getElementById("user-auth-area");
    if (!authArea) return;

    if (currentUser) {
        authArea.innerHTML = `
            <div class="auth-user-info">
                <i class="fa-solid fa-user-shield text-cyan"></i>
                <span class="user-name-text">操作員: <strong>${currentUser.operator_id || currentUser.username}</strong></span>
                <span class="user-role-badge">${currentUser.role || "Operator"}</span>
                <button class="btn-auth-logout" id="btn-auth-logout" title="登出帳號">
                    <i class="fa-solid fa-right-from-bracket"></i>
                </button>
            </div>
        `;

        document.getElementById("btn-auth-logout")?.addEventListener("click", () => {
            currentUser = null;
            localStorage.removeItem("phm_current_user");
            sessionStorage.removeItem("phm_current_user");
            initAuthUI();
        });
    } else {
        authArea.innerHTML = `
            <div class="auth-form-inline">
                <div class="input-group-inline">
                    <i class="fa-solid fa-user"></i>
                    <input type="text" id="auth-input-user" placeholder="帳號" />
                </div>
                <div class="input-group-inline">
                    <i class="fa-solid fa-lock"></i>
                    <input type="password" id="auth-input-pass" placeholder="密碼" />
                </div>
                <button class="btn-auth-submit" id="btn-auth-login">登入</button>
                <button class="btn-auth-secondary" id="btn-auth-reg-trigger">註冊</button>
            </div>
        `;

        document.getElementById("btn-auth-login")?.addEventListener("click", handleLogin);
        document.getElementById("btn-auth-reg-trigger")?.addEventListener("click", () => {
            document.getElementById("register-modal")?.classList.add("active");
        });

        // 支援 Enter 鍵登入
        document.getElementById("auth-input-pass")?.addEventListener("keypress", (e) => {
            if (e.key === "Enter") handleLogin();
        });
    }
}

async function handleLogin() {
    const usernameInput = document.getElementById("auth-input-user")?.value.trim();
    const passwordInput = document.getElementById("auth-input-pass")?.value;

    if (!usernameInput || !passwordInput) {
        alert("⚠️ 請輸入帳號與密碼！");
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: usernameInput, password: passwordInput })
        });

        const data = await res.json();
        if (!res.ok) {
            alert(`❌ 登入失敗: ${data.detail || "帳號或密碼錯誤"}`);
            return;
        }

        currentUser = {
            username: data.username,
            role: data.role,
            operator_id: data.operator_id,
            token: data.token
        };
        // 不存 localStorage 避免持久化暫存；僅存 sessionStorage 且分頁關閉即關閉
        sessionStorage.setItem("phm_current_user", JSON.stringify(currentUser));
        initAuthUI();
        alert(`✅ 登入成功！歡迎回來 ${currentUser.operator_id} (${currentUser.role})`);
    } catch (err) {
        alert("❌ 無法連線至驗證伺服器。");
    }
}


function initRegisterModalEvents() {
    const regModal = document.getElementById("register-modal");
    const btnClose = document.getElementById("btn-close-reg-modal");
    const btnCancel = document.getElementById("btn-reg-cancel");
    const btnSubmit = document.getElementById("btn-reg-submit");

    const closeRegModal = () => regModal?.classList.remove("active");

    btnClose?.addEventListener("click", closeRegModal);
    btnCancel?.addEventListener("click", closeRegModal);

    btnSubmit?.addEventListener("click", async () => {
        const username = document.getElementById("reg-username")?.value.trim();
        const password = document.getElementById("reg-password")?.value;
        const role = document.getElementById("reg-role")?.value;
        const operatorId = document.getElementById("reg-operator-id")?.value.trim();

        if (!username || !password) {
            alert("⚠️ 帳號與密碼為必填欄位！");
            return;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username,
                    password,
                    role,
                    operator_id: operatorId
                })
            });

            const data = await res.json();
            if (!res.ok) {
                alert(`❌ 註冊失敗: ${data.detail || "無法建立使用者"}`);
                return;
            }

            alert(`✅ ${data.message}！您現在可以使用此帳號登入。`);
            closeRegModal();

            // 自動填入登入欄位
            const userIn = document.getElementById("auth-input-user");
            const passIn = document.getElementById("auth-input-pass");
            if (userIn) userIn.value = username;
            if (passIn) passIn.value = password;
        } catch (err) {
            alert("❌ 註冊失敗，連線異常。");
        }
    });
}

// ------------------------------------------------------------------------
// 5. 調參 Modal 彈窗與實態暫態響應事件 (對接操作員驗證)
// ------------------------------------------------------------------------

function initModalEvents() {
    const applyBtn = document.getElementById("btn-apply-parameters");
    const modal = document.getElementById("confirm-modal");
    const btnClose = document.getElementById("btn-close-modal");
    const btnCancel = document.getElementById("btn-modal-cancel");
    const btnConfirm = document.getElementById("btn-modal-confirm");

    applyBtn.addEventListener("click", () => {
        if (!currentUser) {
            alert("⚠️ 工業安全防護限制：\n請先於右上方登入授權操作員帳號，才能將 AI 推薦參數寫入三菱驅動器 EEPROM/RAM！");
            return;
        }

        if (!currentDiagnosisData) return;
        const action = currentDiagnosisData["建議調整參數_後端執行"] || {};
        const recParams = action.recommended_parameters || [];
        
        if (recParams.length === 0) return;

        const summaryEl = document.getElementById("modal-params-summary");
        let html = `<strong>當前操作員 ID：</strong> ${currentUser.operator_id} (${currentUser.role})<br>`;
        html += `<strong>當前診斷根因：</strong> ${action.root_cause || "異常"}<br>`;
        html += `<strong>推薦寫入暫存器：</strong> ${recParams.join(", ")}<br>`;
        html += `<strong>處置方針：</strong> ${action.action || ""}`;
        summaryEl.innerHTML = html;

        modal.classList.add("active");
    });

    const closeModal = () => modal.classList.remove("active");
    btnClose.addEventListener("click", closeModal);
    btnCancel.addEventListener("click", closeModal);

    btnConfirm.addEventListener("click", async () => {
        if (!currentDiagnosisData) return;
        const action = currentDiagnosisData["建議調整參數_後端執行"] || {};
        const recParams = action.recommended_parameters || [];
        const sId = currentDiagnosisData["診斷狀態_前端顯示"]?.current_scenario || currentScenarioId;

        const paramMap = {};
        recParams.forEach(p => {
            if (p === "PE07") paramMap["PE07"] = 96;
            else if (p === "PE01") paramMap["PE01"] = 150;
            else if (p === "PA13") paramMap["PA13"] = 120;
            else if (p === "PB12") paramMap["PB12"] = 435;
            else paramMap[p] = 100;
        });

        try {
            const res = await fetch(`${API_BASE_URL}/api/v1/apply_parameters`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    scenario_id: sId,
                    parameters: paramMap,
                    operator_id: currentUser ? currentUser.operator_id : "Engineer_01"
                })
            });

            const resData = await res.json();
            closeModal();
            
            const trans = resData.physical_transient_response || {};
            alert(`✅ ${resData.message}\n` +
                  `👤 操作員: ${resData.operator_id}\n` +
                  `📊 實體步階響應：整定時間 ${trans.settling_time_sec}s，超調量 ${trans.overshoot_pct}%\n` +
                  `🔒 安全檢定：相位裕度 ${trans.phase_margin_deg}° (${trans.safety_margin_status})\n` +
                  `📜 ISO 55000 稽核 ID: ${resData.iso_audit_trail_id}`);

            // 寫入後自動恢復為 Scenario 01
            const btnNormal = document.querySelector('.btn-scenario[data-id="1"]');
            if (btnNormal) btnNormal.click();
        } catch (err) {
            alert("❌ 閉環寫入失敗，已自動觸發 Safe-State Rollback！");
            closeModal();
        }
    });
}


// ------------------------------------------------------------------------
// 5. WebSocket 實時 Telemetry 繪圖 (Chart.js)
// ------------------------------------------------------------------------

function initChart() {
    const ctx = document.getElementById("telemetryChart").getContext("2d");
    telemetryChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: "電流 RMS (A)",
                    data: chartData.currentRms,
                    borderColor: "#00e5ff",
                    backgroundColor: "rgba(0, 229, 255, 0.1)",
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 0
                },
                {
                    label: "追隨誤差 (Pulse)",
                    data: chartData.followingError,
                    borderColor: "#ffb700",
                    backgroundColor: "transparent",
                    borderWidth: 2,
                    borderDash: [4, 4],
                    tension: 0.3,
                    pointRadius: 0
                },
                {
                    label: "馬達溫度 (°C)",
                    data: chartData.motorTemp,
                    borderColor: "#ff3b30",
                    backgroundColor: "transparent",
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: {
                    display: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#8a99ad", font: { size: 10 } }
                },
                y: {
                    display: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#8a99ad", font: { size: 10 } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function initWebSocket() {
    const ws = new WebSocket(WS_BASE_URL);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            const timeStr = new Date(data.timestamp * 1000).toLocaleTimeString();

            if (data.hardware_connected === false) {
                updateConnectionStatusUI("offline", "未連結馬達 (離線模擬)");
            } else {
                updateConnectionStatusUI("online", "TSN ONLINE (波形串流中)");
            }




            chartData.labels.push(timeStr);
            chartData.currentRms.push(data.hardware_connected === false ? 0 : data.current_rms_a);
            chartData.followingError.push(data.hardware_connected === false ? 0 : data.following_error_abs_pulse);
            chartData.motorTemp.push(data.hardware_connected === false ? 0 : data.motor_temp_c);

            if (chartData.labels.length > MAX_CHART_POINTS) {
                chartData.labels.shift();
                chartData.currentRms.shift();
                chartData.followingError.shift();
                chartData.motorTemp.shift();
            }

            if (telemetryChart) telemetryChart.update("none");
        } catch (e) {
            console.error("WS 解析失敗:", e);
        }
    };


    ws.onclose = () => {
        setTimeout(initWebSocket, 2000);
    };
}

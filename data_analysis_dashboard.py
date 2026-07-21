import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Set page configuration with a premium look
st.set_page_config(
    page_title="伺服馬達預測性維護 (PHM) 數據儀表板",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark theme/glassmorphism vibe)
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1f4068, #162447, #e43f5a);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #6c757d;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-left: 5px solid #1f4068;
        padding: 1.2rem;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Add local libraries to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "02_專案實作與驗證", "AI_SERVO_V5_PART_5_SCENARIOS_25_30"))

try:
    from dsp_analytics import TimeDomainFeatureExtractor, BodeResponseAnalyzer
except ImportError:
    # Fallback in case of path differences
    class TimeDomainFeatureExtractor:
        @staticmethod
        def kurtosis(x): return float(np.sum((x - np.mean(x))**4)/len(x)/(np.var(x)**2)) if np.var(x) > 1e-15 else 3.0
        @staticmethod
        def crest_factor(x): return float(np.max(np.abs(x))/np.sqrt(np.mean(x**2))) if np.mean(x**2) > 1e-15 else 1.0
        @staticmethod
        def margin_factor(x): return float(np.max(np.abs(x))/((np.mean(np.sqrt(np.abs(x))))**2)) if np.mean(np.sqrt(np.abs(x))) > 1e-15 else 1.0

# Title
st.markdown('<div class="main-title">⚙️ 伺服馬達預測性維護數據儀表板</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">針對早期退化 (LO) 狀態的高頻運動與共振特徵深度分析</div>', unsafe_allow_html=True)

# Cache data loading
@st.cache_data
def load_data():
    csv_path = os.path.join("Sup data", "train_noisy_1e_m15_200x5LO-6SEC.csv")
    meta_path = os.path.join("Sup data", "test_load0_1e_m15_200x5_lite2_utf8.csv")
    
    # Check fallback encoding if utf-8 meta doesn't exist yet
    if not os.path.exists(meta_path):
        raw_meta = os.path.join("Sup data", "test_load0_1e_m15_200x5_lite2.csv")
        if os.path.exists(raw_meta):
            with open(raw_meta, 'r', encoding='cp950', errors='ignore') as rf:
                content = rf.read()
            with open(meta_path, 'w', encoding='utf-8') as wf:
                wf.write(content)
                
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    df_meta = pd.read_csv(meta_path, encoding='utf-8')
    return df, df_meta

try:
    df, df_meta = load_data()
except Exception as e:
    st.error(f"Error loading datasets: {e}")
    st.stop()

# Sidebar options
st.sidebar.header("📁 資料選擇與設定")
transition_select = st.sidebar.selectbox(
    "選擇運動切換區間 (Transition):",
    options=sorted(df['transitions'].unique()),
    index=0
)

# Filter data
segment = df[df['transitions'] == transition_select].copy()
segment['time_rel'] = (segment['time'] - segment['time'].min()) * 1000  # Relative ms

# Tabs for different analyses
tab1, tab2, tab3 = st.tabs(["📊 資料概覽與對齊說明", "📉 步階響應與時序探索", "🌀 頻域與共振分析 (Bode)"])

# Tab 1: Overview
with tab1:
    st.header("📋 資料集與欄位說明")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h4>📊 數據集維度</h4>
            <p style="font-size: 1.8rem; font-weight: 700; color: #1f4068;">{df.shape[0]:,} 筆行數</p>
            <p>15 個特徵欄位</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h4>⚡ 採樣規格</h4>
            <p style="font-size: 1.8rem; font-weight: 700; color: #1f4068;">50 kHz 採樣頻率</p>
            <p>取樣週期：20 微秒</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h4>🧪 馬達劣化狀態</h4>
            <p style="font-size: 1.8rem; font-weight: 700; color: #e43f5a;">LO (早期退化)</p>
            <p>劣化指數 (DV): 270.19</p>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("欄位定義對照表")
    # Clean meta columns to display nicely
    df_meta_clean = df_meta.iloc[:, [0, 1, 2, 12, 13]].copy()
    df_meta_clean.columns = ["欄位名稱", "中文名稱", "物理工程說明", "AI/推導適合度", "AI 推薦度"]
    df_meta_clean = df_meta_clean[df_meta_clean["欄位名稱"].isin(df.columns)]
    st.dataframe(df_meta_clean, use_container_width=True)

# Tab 2: Step Response & Time Domain
with tab2:
    st.header(f"📈 Transition {transition_select} 步階響應與控制特性")
    
    # Calculate response metrics
    cmd_pos = segment['rod_demand_pos'].iloc[0]
    first_act = segment['rod_actual_pos'].iloc[0]
    last_act = segment['rod_actual_pos'].iloc[-1]
    step_size = cmd_pos - first_act
    
    # Peak speed and torque
    max_speed = segment['rotor_speed'].max()
    min_speed = segment['rotor_speed'].min()
    abs_max_speed = max(abs(max_speed), abs(min_speed))
    
    max_torque = segment['torque'].max()
    min_torque = segment['torque'].min()
    abs_max_torque = max(abs(max_torque), abs(min_torque))
    
    # Overshoot
    actual_traj = segment['rod_actual_pos'].values
    if abs(step_size) > 1e-3:
        if step_size > 0:
            overshoot_val = (np.max(actual_traj) - cmd_pos) / step_size
        else:
            overshoot_val = (cmd_pos - np.min(actual_traj)) / (-step_size)
        overshoot_pct = max(0.0, overshoot_val) * 100.0
    else:
        overshoot_pct = 0.0
        
    # Rise time (time to 90% of the step)
    target_90 = first_act + 0.9 * step_size
    cross_indices = []
    if step_size > 0:
        cross_indices = np.where(actual_traj >= target_90)[0]
    elif step_size < 0:
        cross_indices = np.where(actual_traj <= target_90)[0]
    rise_time_ms = cross_indices[0] * 0.02 if len(cross_indices) > 0 else np.nan
    
    # Settling time (2% band)
    tolerance = 0.02 * abs(step_size) if abs(step_size) > 1e-3 else 0.5
    dev_from_target = np.abs(actual_traj - cmd_pos)
    within_tolerance = dev_from_target <= tolerance
    outside_indices = np.where(~within_tolerance)[0]
    settling_time_ms = (outside_indices[-1] + 1) * 0.02 if len(outside_indices) > 0 else 0.0
    
    # Steady state error
    ss_error = cmd_pos - last_act
    
    # DSP features in steady state
    ss_start_idx = int(len(segment) * 0.8)
    ss_torque = segment['torque'].values[ss_start_idx:]
    ss_speed = segment['rotor_speed'].values[ss_start_idx:]
    torque_kurt = TimeDomainFeatureExtractor.kurtosis(ss_torque)
    torque_cf = TimeDomainFeatureExtractor.crest_factor(ss_torque)
    torque_std = np.std(ss_torque)
    
    # Metrics layout
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("步階跨度 (Step Size)", f"{step_size:.4f}")
    m_col2.metric("上升時間 (Rise Time)", f"{rise_time_ms:.2f} ms" if not np.isnan(rise_time_ms) else "N/A")
    m_col3.metric("整定時間 (Settling Time)", f"{settling_time_ms:.2f} ms")
    m_col4.metric("最大超調量 (Overshoot)", f"{overshoot_pct:.2f}%")
    
    m_col5, m_col6, m_col7, m_col8 = st.columns(4)
    m_col5.metric("穩態誤差 (SS Error)", f"{ss_error:.6f}")
    m_col6.metric("最大轉矩 (Max Torque)", f"{abs_max_torque:.2f} Nm")
    m_col7.metric("轉矩穩態標準差 (STD)", f"{torque_std:.6f}")
    m_col8.metric("轉矩穩態峭度 (Kurtosis)", f"{torque_kurt:.4f}")

    # Plot position trajectory (Interactive Altair Chart)
    st.subheader("位置指令與實際位置響應曲線")
    
    # Sample data for plotting to keep performance high
    sample_rate = 10
    plot_df = segment.iloc[::sample_rate].copy()
    
    # Melt for altair
    plot_df_melted = plot_df.melt(
        id_vars=['time_rel'], 
        value_vars=['rod_demand_pos', 'rod_actual_pos'],
        var_name='位置類型', 
        value_name='位置值 (脈衝)'
    )
    
    chart_pos = alt.Chart(plot_df_melted).mark_line().encode(
        x=alt.X('time_rel:Q', title='時間 (毫秒)'),
        y=alt.Y('位置值 (脈衝):Q', scale=alt.Scale(zero=False)),
        color=alt.Color('位置類型:N', scale=alt.Scale(domain=['rod_demand_pos', 'rod_actual_pos'], range=['#e43f5a', '#1f4068']))
    ).properties(height=400).interactive()
    
    st.altair_chart(chart_pos, use_container_width=True)
    
    # Plot Speed and Torque
    st.subheader("速度與轉矩響應曲線")
    col_plot1, col_plot2 = st.columns(2)
    with col_plot1:
        chart_speed = alt.Chart(plot_df).mark_line(color='#0f4c81').encode(
            x=alt.X('time_rel:Q', title='時間 (毫秒)'),
            y=alt.Y('rotor_speed:Q', title='轉子速度 (RPM)')
        ).properties(height=300).interactive()
        st.altair_chart(chart_speed, use_container_width=True)
    with col_plot2:
        chart_torque = alt.Chart(plot_df).mark_line(color='#ff6f61').encode(
            x=alt.X('time_rel:Q', title='時間 (毫秒)'),
            y=alt.Y('torque:Q', title='電磁轉矩 (Nm)')
        ).properties(height=300).interactive()
        st.altair_chart(chart_torque, use_container_width=True)

# Tab 3: Frequency Domain
with tab3:
    st.header(f"🌀 Transition {transition_select} 頻域與機械共振分析")
    
    # Calculate Bode
    analyzer = BodeResponseAnalyzer(sampling_rate_hz=50000)
    bode_res = analyzer.analyze(segment['rod_demand_pos'].values, segment['rod_actual_pos'].values)
    
    if bode_res['status'] == 'success':
        f_col1, f_col2, f_col3 = st.columns(3)
        f_col1.metric("共振峰頻率 (Peak Freq)", f"{bode_res['resonance_peak_freq_hz']:.2f} Hz")
        f_col2.metric("共振峰突出度 (Peak Prominence)", f"{bode_res['resonance_prominence_db']:.2f} dB")
        f_col3.metric("側頻共振帶能量比 (Sideband Energy)", f"{bode_res['sideband_resonance_energy_ratio']:.8f}")
        
        # Plot Bode Magnitude Response
        freqs = np.array(bode_res['frequencies'])
        mags = np.array(bode_res['magnitude_db'])
        
        # Filter for plotting frequencies between 10Hz and 1000Hz to focus on resonance
        idx_plot = (freqs >= 10.0) & (freqs <= 1000.0)
        bode_df = pd.DataFrame({
            'Frequency': freqs[idx_plot],
            'Magnitude': mags[idx_plot]
        })
        
        chart_bode = alt.Chart(bode_df).mark_line(color='#e43f5a').encode(
            x=alt.X('Frequency:Q', title='頻率 (Hz)', scale=alt.Scale(type='log')),
            y=alt.Y('Magnitude:Q', title='幅頻響應 (dB)')
        ).properties(height=400, title='Bode 幅頻響應圖 (10Hz - 1000Hz)').interactive()
        
        st.altair_chart(chart_bode, use_container_width=True)
        
        st.info("💡 **共振峰物理診斷說明**：系統在約 100.8 Hz 處出現了明顯的幅頻響應抬升（共振峰），且突出度極大。建議向三菱電機 MR-Configurator2 軟體寫入相關 Notch Filter 參數，對該特定頻點實施抑制濾波。")
    else:
        st.error(f"Bode analysis failed: {bode_res['message']}")

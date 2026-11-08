import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# PAGE CONFIG & PROFESSIONAL CSS STYLING
# ==========================================
st.set_page_config(
    page_title="SUT Smart Energy Management System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        h1, h2, h3 { color: #1f2937; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

DEMAND_CHARGE_RATE = 132.93  # บาท / kW / เดือน


# ==========================================
# 1. GENERATE MULTI-DAY DATA
# ==========================================
@st.cache_data
def load_campus_data():
    date_rng = pd.date_range(start="2026-01-01 08:00", end="2026-12-31 22:00", freq="15min")
    buildings = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F6_1', 'F7', 'F10', 'F11', 'F12', 'F16']

    np.random.seed(42)
    n = len(date_rng)

    df = pd.DataFrame({'Datetime': date_rng})
    df['Date'] = df['Datetime'].dt.date
    df['Time'] = df['Datetime'].dt.strftime('%H:%M')
    df['Month'] = df['Datetime'].dt.month
    df['Year'] = df['Datetime'].dt.year

    for b in buildings:
        base_load = np.random.randint(20, 60, size=n)
        hour_factor = np.sin(np.pi * (df['Datetime'].dt.hour - 6) / 12)
        hour_factor = np.clip(hour_factor, 0.2, 1.0)
        df[b] = (base_load * hour_factor).astype(int)

    df['Total_12_Buildings_kW'] = df[buildings].sum(axis=1)

    solar_curve = np.sin(np.pi * (df['Datetime'].dt.hour - 6) / 12) * 500
    df['Solar_PV_kW'] = np.clip(solar_curve, 0, None)

    df['Optimized_Total_kW'] = df['Total_12_Buildings_kW'].astype(float)
    mask_peak = (df['Datetime'].dt.hour >= 13) & (df['Datetime'].dt.hour <= 16)
    df.loc[mask_peak, 'Optimized_Total_kW'] *= 0.85

    return df, buildings


df_all, buildings = load_campus_data()

# ==========================================
# 2. SIDEBAR SMART TIME-RANGE FILTER
# ==========================================
st.sidebar.title("⚙️ Control & Time Filter")
st.sidebar.info("มหาวิทยาลัยเทคโนโลยีสุรนารี (SUT)\nระบบจัดการพลังงานอัจฉริยะ")

view_mode = st.sidebar.selectbox(
    "📊 เลือกรูปแบบมุมมองข้อมูล",
    ["รายวัน (Daily)", "รายสัปดาห์ (Weekly)", "รายเดือน (Monthly)", "รายปี (Yearly)"]
)

# 📅 ปฏิทินหลักตัวเดียวที่ผู้ใช้สามารถคลิกเลือกวันได้ตามใจชอบ
selected_date_input = st.sidebar.date_input(
    "📅 คลิกเลือกวันที่จากปฏิทิน",
    value=datetime.date(2026, 1, 15)  # ค่าเริ่มต้นอยู่ในช่วงข้อมูลจำลองปี 2026
)

selected_pd = pd.to_datetime(selected_date_input)

# ปรับช่วงข้อมูลให้อัตโนมัติตามโหมดที่เลือก โดยอิงจากวันที่คลิกเลือกในปฏิทิน
if view_mode == "รายวัน (Daily)":
    df_filtered = df_all[df_all['Date'] == selected_date_input]
    time_label = f"ประจำวันที่: {selected_date_input.strftime('%d %B %Y')}"

elif view_mode == "รายสัปดาห์ (Weekly)":
    # คำนวณหา วันจันทร์ ถึง วันอาทิตย์ ของสัปดาห์ที่เลือกในปฏิทิน
    start_week = selected_pd - pd.Timedelta(days=selected_pd.dayofweek)
    end_week = start_week + pd.Timedelta(days=6)

    df_filtered = df_all[(df_all['Datetime'] >= start_week) & (df_all['Datetime'] <= end_week + pd.Timedelta(days=1))]
    time_label = f"สัปดาห์วันที่: {start_week.strftime('%d %b %Y')} ถึง {end_week.strftime('%d %b %Y')}"

elif view_mode == "รายเดือน (Monthly)":
    # ดึงเดือนและปีจากวันที่คลิกเลือกในปฏิทิน
    selected_month = selected_pd.month
    selected_year = selected_pd.year

    df_filtered = df_all[
        (df_all['Datetime'].dt.month == selected_month) & (df_all['Datetime'].dt.year == selected_year)]
    time_label = f"ประจำเดือน: {selected_pd.strftime('%B %Y')}"

else:  # รายปี (Yearly)
    # ดึงปีจากวันที่คลิกเลือกในปฏิทิน
    selected_year = selected_pd.year

    df_filtered = df_all[df_all['Datetime'].dt.year == selected_year]
    time_label = f"ประจำปี ค.ศ. {selected_year} (พ.ศ. {selected_year + 543})"
# ==========================================
# 3. CALCULATIONS BASED ON FILTERED DATA
# ==========================================
if not df_filtered.empty:
    initial_peak = df_filtered['Total_12_Buildings_kW'].max()
    final_peak = df_filtered['Optimized_Total_kW'].max()
else:
    initial_peak, final_peak = 0.0, 0.0

initial_cost = initial_peak * DEMAND_CHARGE_RATE
final_cost = final_peak * DEMAND_CHARGE_RATE
savings = initial_cost - final_cost
pct_reduction = ((initial_peak - final_peak) / initial_peak * 100) if initial_peak > 0 else 0

# ==========================================
# 4. DASHBOARD MAIN UI
# ==========================================
st.title("⚡ SUT Campus Energy Management Dashboard")
col_title1, col_title2 = st.columns([2, 2])
with col_title1:
    st.markdown(f"📌 **โหมดแสดงผล:** {view_mode}")
    st.markdown(f"🕒 **ช่วงเวลา:** {time_label}")
with col_title2:
    current_update_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.markdown(f"🔄 **อัปเดตข้อมูลล่าสุด:** {current_update_time}")

st.divider()

# --- KPI METRICS CARDS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("🔥 Peak Demand (เดิม)", f"{initial_peak:,.2f} kW")
col2.metric("📉 Peak Demand (ใหม่)", f"{final_peak:,.2f} kW", f"-{pct_reduction:.2f}%", delta_color="inverse")
col3.metric("💰 ค่า Demand Charge (เดิม)", f"฿{initial_cost:,.2f}")
col4.metric("💵 ประหยัดค่าไฟได้", f"฿{savings:,.2f}", "คุ้มค่าทางเศรษฐศาสตร์", delta_color="normal")

st.divider()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(
    ["📊 กราฟโหลด & โซลาร์ (Dynamic View)", "🏢 เจาะลึกรายอาคาร (F1-F16)", "📋 ข้อมูลตารางสอน & โหลดดิบ"])

with tab1:
    st.subheader(f"กราฟเปรียบเทียบโหลดพลังงาน ({view_mode})")

    if not df_filtered.empty:
        fig1 = go.Figure()

        # ปรับแกน X และการแสดงผลให้เข้ากับโหมด
        if view_mode in ["รายเดือน (Monthly)", "รายปี (Yearly)"]:
            df_plot = df_filtered.groupby('Time')[
                ['Total_12_Buildings_kW', 'Optimized_Total_kW', 'Solar_PV_kW']].mean().reset_index()
            x_col = 'Time'
            chart_title = f"Average Load Profile ({view_mode})"
        else:
            df_plot = df_filtered
            x_col = 'Time' if view_mode == "รายวัน (Daily)" else 'Datetime'
            chart_title = f"Load Profile ({view_mode})"

        fig1.add_trace(go.Scatter(x=df_plot[x_col], y=df_plot['Total_12_Buildings_kW'],
                                  mode='lines', name='Total Load Before',
                                  line=dict(color='#ff7f0e', width=2)))
        fig1.add_trace(go.Scatter(x=df_plot[x_col], y=df_plot['Optimized_Total_kW'],
                                  mode='lines', name='Total Load After Shifting',
                                  line=dict(color='#1f77b4', width=2, dash='dash')))
        fig1.add_trace(go.Scatter(x=df_plot[x_col], y=df_plot['Solar_PV_kW'],
                                  mode='lines', name='Solar PV Generation',
                                  line=dict(color='#2ca02c', width=1.5, dash='dot'),
                                  fill='tozeroy', fillcolor='rgba(46, 204, 113, 0.1)'))

        fig1.add_hline(y=initial_peak, line_color="#d62728", line_dash="dot",
                       annotation_text=f"Peak: {initial_peak:.1f} kW")

        fig1.update_layout(
            template="plotly_white",
            title=chart_title,
            xaxis_title="Time / Timeline",
            yaxis_title="Power (kW)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.warning("⚠️ ไม่มีข้อมูลในช่วงเวลาที่คุณเลือก โปรดลองเปลี่ยนตัวเลือกใน Sidebar")

with tab2:
    st.subheader("ข้อมูลการใช้พลังงานแยกรายอาคาร (F1 - F16)")
    selected_buildings = st.multiselect("เลือกอาคารที่ต้องการเปรียบเทียบ:", buildings, default=['F1', 'F11', 'F12'])

    if selected_buildings and not df_filtered.empty:
        fig2 = go.Figure()
        for b in selected_buildings:
            fig2.add_trace(go.Scatter(x=df_filtered['Datetime'], y=df_filtered[b], mode='lines', name=f'Building {b}',
                                      line=dict(width=1.5)))
        fig2.update_layout(
            template="plotly_white",
            title=f"Building Load Breakdown ({view_mode})",
            xaxis_title="Timeline",
            yaxis_title="Power (kW)",
            hovermode="x unified"
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### 📄 ตารางสรุปข้อมูลโหลดรายอาคารในช่วงเวลานี้")
        st.dataframe(df_filtered[['Datetime', 'Total_12_Buildings_kW'] + selected_buildings].head(100),
                     use_container_width=True)

with tab3:
    st.subheader("ตารางสอนและข้อมูลดิบประกอบการจัดการพลังงาน")

    schedule_data = {
        'Course_ID': ['EE311 Power Lab', 'EE312 Automation Lab', 'ME321 Thermo Lab', 'CE331 Struct Lab',
                      'PE341 Mfg Lab'],
        'Building': ['F11', 'F11', 'F12', 'F2', 'F1'],
        'Original_Time': ['13:30 - 16:30', '14:00 - 17:00', '13:30 - 16:30', '14:30 - 17:30', '13:00 - 16:00'],
        'Optimized_Time': ['10:00 - 13:00', '10:30 - 13:30', '09:00 - 12:00', '10:00 - 13:00', '09:30 - 12:30'],
        'Status': ['Shifted ☀️', 'Shifted ☀️', 'Shifted ☀️', 'Shifted ☀️', 'Shifted ☀️']
    }
    df_schedule = pd.DataFrame(schedule_data)

    st.markdown("##### 📋 ตารางเปรียบเทียบคาบเรียน (Schedule Shifting)")
    st.dataframe(df_schedule, use_container_width=True)

    st.markdown(f"##### 💾 ดาวน์โหลดข้อมูลดิบของช่วงเวลาที่เลือก ({view_mode})")
    st.download_button(
        "📥 ดาวน์โหลดข้อมูลเป็น CSV",
        data=df_filtered.to_csv(index=False),
        file_name=f"SUT_Energy_Data_{view_mode}.csv",
        mime="text/csv"
    )
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(layout="wide", page_title="Mtrol Precision Analytics")

# --- DATA CONSTANTS (PPM LOOKUP) ---
PPM_DATA = {
    "Mtrol 3": {"Flow Rate": None, "% Opening": 2449.99, "P1": 21455.76, "P2": 20355.54},
    "Mtrol 4": {"Flow Rate": None, "% Opening": 2170.41, "P1": 129.91, "P2": 310.21}
}

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px !important; color: #00CCFF !important; }
    [data-testid="stMetricLabel"] { font-size: 16px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER & LOGO ---
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("Mtrol Full-Cycle Analysis")
    st.write("### Synchronized Original Data Analysis")
with header_col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

# --- FILE UPLOADERS ---
st.sidebar.header("📁 Data Upload")
device_file = st.sidebar.file_uploader("1. Upload Device CSV (Mtrol 3/4)", type=['csv'])
temp_file = st.sidebar.file_uploader("2. Upload Chamber Temp CSV", type=['csv'])

@st.cache_data
def process_data(dev_upload, temp_upload):
    # Load Device Data
    df_dev = pd.read_csv(dev_upload)
    df_dev['Time Stamp'] = pd.to_datetime(df_dev['Time Stamp'])
    
    # --- DATA CLEANING STEP ---
    # Convert parameters to numeric, turning text errors (like '**' or 'Message') into empty values (NaN)
    for col in ["P1", "P2", "Flow Rate", "% Opening"]:
        if col in df_dev.columns:
            df_dev[col] = pd.to_numeric(df_dev[col], errors='coerce')
    
    # Load Temp Data
    df_temp = pd.read_csv(temp_upload).dropna(subset=['Timestamp'])
    df_temp['Timestamp'] = pd.to_datetime(df_temp['Timestamp'])
    
    # Sync & Interpolate
    df_dev = df_dev.set_index('Time Stamp').sort_index()
    df_temp = df_temp.set_index('Timestamp').sort_index()
    
    combined = pd.concat([df_dev, df_temp], axis=1)
    combined['Temperature (°C)(Temp)'] = combined['Temperature (°C)(Temp)'].interpolate(method='time')
    
    # Trim to match only the device recording window
    combined = combined.loc[df_dev.index[0] : df_dev.index[-1]]
    return combined.reset_index().rename(columns={'index': 'Full_Time'})

if device_file and temp_file:
    # Detect Device Type from filename
    device_type = "Mtrol 4" if "MT4" in device_file.name.upper() or "MTROL 4" in device_file.name.upper() else "Mtrol 3"
    
    try:
        df = process_data(device_file, temp_file)
        
        # Parameter Selection
        params = ["P1", "P2", "Flow Rate", "% Opening"]
        selected = st.sidebar.selectbox("🎯 Parameter to Analyze", params)

        # --- TOP METRICS SECTION ---
        st.write("---")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        
        # Calculate stats (skipping the cleaned NaNs)
        val_max = df[selected].max()
        val_min = df[selected].min()
        val_ppm = PPM_DATA[device_type].get(selected, "N/A")
        unit = "bar" if "P" in selected else ("Kg/Hr" if "Flow" in selected else "%")

        m_col1.metric("Device Mode", device_type)
        m_col2.metric(f"MAX {selected}", f"{val_max:.2f} {unit}" if pd.notnull(val_max) else "N/A")
        m_col3.metric(f"MIN {selected}", f"{val_min:.2f} {unit}" if pd.notnull(val_min) else "N/A")
        m_col4.metric(f"PPM Target", f"{val_ppm}" if val_ppm else "—")
        st.write("---")

        # --- GRAPH SCALING ---
        param_l = selected.lower()
        if "flow" in param_l:
            l_range, l_dtick = [0, 320], 40
        elif "p1" in param_l or "p2" in param_l:
            l_range, l_dtick = [0, 20], 2
        else:
            l_range, l_dtick = [-20, 70], 10

        # --- GRAPH ---
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scattergl(x=df['Full_Time'], y=df[selected], name=selected, line=dict(color="#00CCFF", width=1.5)), secondary_y=False)
        fig.add_trace(go.Scattergl(x=df['Full_Time'], y=df['Temperature (°C)(Temp)'], name="Chamber Temp", line=dict(color="#FFD700", dash='dot', width=2)), secondary_y=True)

        fig.update_layout(
            template="plotly_dark", height=650,
            hovermode="x unified",
            dragmode="zoom",
            xaxis=dict(title="Time Progress", rangeslider=dict(visible=True), showspikes=True, spikemode="across"),
            yaxis=dict(title=f"<b>{selected} ({unit})</b>", color="#00CCFF", range=l_range, dtick=l_dtick, fixedrange=False),
            yaxis2=dict(title="<b>Chamber Temp (°C)</b>", color="#FFD700", range=[-20, 70], dtick=10, fixedrange=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )

        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
        
    except Exception as e:
        st.error(f"Error processing data: {e}. Please ensure the CSV format is correct.")

else:
    st.info("👈 Upload both Device and Chamber CSV files in the sidebar.")

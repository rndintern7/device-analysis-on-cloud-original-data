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

# --- CUSTOM CSS FOR METRICS ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; color: #00CCFF; }
    [data-testid="stMetricLabel"] { font-size: 16px; font-weight: bold; }
    </style>
    """, unsafe_allow_y_axis=True)

# --- HEADER & LOGO ---
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("Mtrol Full-Cycle Analysis")
    st.write("### Upload Original Data for 1s Synchronized Analysis")
with header_col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

# --- FILE UPLOADERS ---
st.sidebar.header("📁 Data Upload")
device_file = st.sidebar.file_uploader("Upload Device CSV (Mtrol 3/4)", type=['csv'])
temp_file = st.sidebar.file_uploader("Upload Chamber Temp CSV", type=['csv'])

@st.cache_data
def process_data(dev_upload, temp_upload):
    # Load Device Data
    df_dev = pd.read_csv(dev_upload)
    df_dev['Time Stamp'] = pd.to_datetime(df_dev['Time Stamp'])
    
    # Load Temp Data
    df_temp = pd.read_csv(temp_upload).dropna(subset=['Timestamp'])
    df_temp['Timestamp'] = pd.to_datetime(df_temp['Timestamp'])
    
    # Sync & Interpolate
    df_dev = df_dev.set_index('Time Stamp').sort_index()
    df_temp = df_temp.set_index('Timestamp').sort_index()
    
    combined = pd.concat([df_dev, df_temp], axis=1)
    combined['Temperature (°C)(Temp)'] = combined['Temperature (°C)(Temp)'].interpolate(method='time')
    
    # Trim to device window
    combined = combined.loc[df_dev.index[0] : df_dev.index[-1]]
    return combined.reset_index().rename(columns={'index': 'Full_Time'})

if device_file and temp_file:
    # Detect Device Type from filename
    device_type = "Mtrol 4" if "MT4" in device_file.name.upper() or "MTROL 4" in device_file.name.upper() else "Mtrol 3"
    
    df = process_data(device_file, temp_file)
    
    # --- PARAMETER SELECTION ---
    available_params = [c for c in df.columns if c in ["P1", "P2", "Flow Rate", "% Opening"]]
    selected = st.sidebar.selectbox("🎯 Parameter to Analyze", available_params)

    # --- TOP METRICS SECTION ---
    st.write("---")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    val_max = df[selected].max()
    val_min = df[selected].min()
    val_ppm = PPM_DATA[device_type].get(selected, "N/A")
    unit = "bar" if "P" in selected else ("Kg/Hr" if "Flow" in selected else "%")

    m_col1.metric("Selected Parameter", f"{selected}")
    m_col2.metric(f"MAX {selected}", f"{val_max:.2f} {unit}")
    m_col3.metric(f"MIN {selected}", f"{val_min:.2f} {unit}")
    m_col4.metric(f"PPM ({device_type})", f"{val_ppm}" if val_ppm else "—")
    st.write("---")

    # --- DYNAMIC SCALING ---
    param_l = selected.lower()
    if "flow" in param_l:
        l_range, l_dtick = [0, 320], 40
    elif "p1" in param_l or "p2" in param_l:
        l_range, l_dtick = [0, 20], 2
    else:
        l_range, l_dtick = [-20, 70], 10

    # --- SYNCHRONIZED GRAPH ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Left Y: Parameter
    fig.add_trace(go.Scattergl(
        x=df['Full_Time'], y=df[selected],
        name=selected, line=dict(color="#00CCFF", width=1.5)
    ), secondary_y=False)

    # Right Y: Chamber Temp
    fig.add_trace(go.Scattergl(
        x=df['Full_Time'], y=df['Temperature (°C)(Temp)'],
        name="Chamber Temp", line=dict(color="#FFD700", dash='dot', width=2)
    ), secondary_y=True)

    fig.update_layout(
        template="plotly_dark", height=600,
        hovermode="x unified",
        dragmode="zoom",
        xaxis=dict(title="Time Progress", rangeslider=dict(visible=True), showspikes=True, spikemode="across"),
        yaxis=dict(title=f"<b>{selected} ({unit})</b>", range=l_range, dtick=l_dtick, fixedrange=False),
        yaxis2=dict(title="<b>Chamber Temp (°C)</b>", range=[-20, 70], dtick=10, fixedrange=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    # Data Explorer
    with st.expander("See Synchronized Table"):
        st.dataframe(df, use_container_width=True)

else:
    st.info("👈 Please upload both the Device Data and Chamber Temp CSV files in the sidebar.")

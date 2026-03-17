import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Page Config
st.set_page_config(layout="wide", page_title="Mtrol Precision Analytics")

# --- HEADER & LOGO ---
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("Mtrol Full-Cycle Analysis")
    st.write("### Synchronized Original Data (1s Resolution)")
with header_col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

# --- DATA LOADING & SYNC LOGIC ---
@st.cache_data
def load_and_sync_data(device_file, temp_file):
    # 1. Load Device Data (starts 10:20:53 or 10:21:05)
    df_dev = pd.read_csv(device_file)
    df_dev['Time Stamp'] = pd.to_datetime(df_dev['Time Stamp'])
    
    # 2. Load Chamber Temp (starts 10:20, every 2 mins)
    df_temp = pd.read_csv(temp_file).dropna(subset=['Timestamp'])
    df_temp['Timestamp'] = pd.to_datetime(df_temp['Timestamp'])
    
    # 3. Synchronize
    df_dev = df_dev.set_index('Time Stamp').sort_index()
    df_temp = df_temp.set_index('Timestamp').sort_index()
    
    # Merge and interpolate the 2-minute temperature gaps into 1-second steps
    combined = pd.concat([df_dev, df_temp], axis=1)
    combined['Temperature (°C)(Temp)'] = combined['Temperature (°C)(Temp)'].interpolate(method='time')
    
    # Filter back to only the device timeframe
    combined = combined.loc[df_dev.index[0] : df_dev.index[-1]]
    return combined.reset_index().rename(columns={'index': 'Full_Time'})

# --- FILENAMES ---
files = {
    "Mtrol 3": "Mtrol 3 11-13 march - Mtrol 3 original data.csv",
    "Mtrol 4": "Mtrol 4 11-13 march - Mtrol 4 original_data .csv",
    "Chamber": "Mtrol 3 and 4 11-13 march - Chamber temp data.csv"
}

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Settings")
device_mode = st.sidebar.radio("Choose Device", ["Mtrol 3", "Mtrol 4"])
selected_param = st.sidebar.selectbox("Select Parameter", ["P1", "P2", "Flow Rate", "% Opening"])

if all(os.path.exists(f) for f in [files[device_mode], files["Chamber"]]):
    df = load_and_sync_data(files[device_mode], files["Chamber"])
    
    # --- DYNAMIC SCALING LOGIC ---
    param_l = selected_param.lower()
    if "flow" in param_l:
        l_range, l_dtick = [0, 320], 40
    elif "p1" in param_l or "p2" in param_l:
        l_range, l_dtick = [0, 20], 2
    else: # % Opening and others
        l_range, l_dtick = [-20, 70], 10

    # --- GRAPHING ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Left Y-Axis: Device Parameter
    fig.add_trace(go.Scattergl(
        x=df['Full_Time'], y=df[selected_param],
        name=f"{device_mode} {selected_param}",
        line=dict(color="#00CCFF", width=1.5)
    ), secondary_y=False)

    # Right Y-Axis: Interpolated Chamber Temp
    fig.add_trace(go.Scattergl(
        x=df['Full_Time'], y=df['Temperature (°C)(Temp)'],
        name="Chamber Temp (Sync)",
        line=dict(color="#FFD700", dash='dot', width=2)
    ), secondary_y=True)

    fig.update_layout(
        template="plotly_dark", height=700,
        hovermode="x unified",
        dragmode="zoom",
        xaxis=dict(
            title="Time Progress (1s Res)",
            rangeslider=dict(visible=True),
            showspikes=True, spikemode="across"
        ),
        yaxis=dict(title=f"<b>{selected_param}</b>", range=l_range, dtick=l_dtick, fixedrange=False),
        yaxis2=dict(title="<b>Chamber Temp (°C)</b>", range=[-20, 70], dtick=10, fixedrange=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
    
    # Show Raw Data
    st.subheader("Synchronized Data Explorer")
    st.write(f"Displaying rows for {device_mode} start time onwards.")
    st.dataframe(df, use_container_width=True)

else:
    st.error("One or more files missing in GitHub. Check filenames.")

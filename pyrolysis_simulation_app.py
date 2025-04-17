import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Pyrolysis Simulation Tool", layout="wide")
st.title("🛢️ Pyrolysis Simulation Tool – Pavitra India")

st.sidebar.header("Input Parameters")

# Feedstock Selection
feedstock_type = st.sidebar.selectbox("Feedstock Type", ["HDPE", "LDPE", "PP", "Mixed"])
batch_size = st.sidebar.slider("Batch Size (kg)", 5000, 20000, 10000, step=500)

# Mixed Plastic Ratios
if feedstock_type == "Mixed":
    st.sidebar.subheader("Plastic Mix (%)")
    mix_hdpe = st.sidebar.slider("HDPE (%)", 0, 100, 40)
    mix_ldpe = st.sidebar.slider("LDPE (%)", 0, 100, 30)
    mix_pp = st.sidebar.slider("PP (%)", 0, 100, 30)
    if mix_hdpe + mix_ldpe + mix_pp != 100:
        st.sidebar.error("Total must be 100%")

# Reactor Conditions
reactor_temp = st.sidebar.slider("Reactor Temperature (°C)", 400, 550, 450)
reactor_pressure = st.sidebar.slider("Reactor Pressure (atm)", 0.8, 1.5, 1.0, step=0.05)

# Catalyst System
catalyst_type = st.sidebar.selectbox("Catalyst Type", ["ZSM-5", "Alumina", "Clay", "Bentonite", "FCC Catalyst", "None"])
catalyst_qty = st.sidebar.slider("Catalyst Quantity (kg)", 0, 1000, 500, step=50)
catalyst_eff = st.sidebar.slider("Catalyst Efficiency (%)", 50, 100, 90)

# Equipment Configuration
st.sidebar.subheader("Process Layout")
config = st.sidebar.selectbox("Configuration", ["S1: Basic", "S2: Cat Only", "S3: Tar+Cat", "S4: Optimized", "S5: Bypass Test", "S6: Heavy Oil Recycle"])
condenser_stages = st.sidebar.selectbox("Number of Condensers", [1, 2, 3])

# Wax Recirculation
enable_recycle = st.sidebar.checkbox("Enable Wax Recirculation")
if enable_recycle:
    max_recycles = st.sidebar.number_input("Max Recycles", min_value=1, max_value=3, value=2)
    enable_precracker = st.sidebar.checkbox("Include Pre-Cracker")
    if enable_precracker:
        precracker_temp = st.sidebar.slider("Pre-Cracker Temp (°C)", 350, 500, 420)
        catalyst_boost = st.sidebar.slider("Pre-Cracker Catalyst Multiplier", 1.0, 2.0, 1.2)

# Vacuum System
vacuum_config = st.sidebar.radio("Vacuum Pump Setup", ["2 Pumps", "3 Pumps"])

# Economic Inputs
st.sidebar.subheader("Economics")
feed_cost = st.sidebar.number_input("Feedstock Cost (₹/kg)", value=10.0)
energy_cost = st.sidebar.number_input("Energy Cost (₹/kg feed)", value=1.5)
catalyst_cost = st.sidebar.number_input("Catalyst Cost (₹/kg)", value=45.0)
catalyst_life = st.sidebar.number_input("Catalyst Life (Batches)", value=20)
ldo_cost = st.sidebar.number_input("LDO Cost (₹/ltr)", value=52.0)
labor_cost = st.sidebar.number_input("Labor Cost (₹/hr)", value=70.0)
ncg_saving = st.sidebar.number_input("NCG Reuse Bonus (₹/kg saved)", value=15.0)
oil_price = st.sidebar.number_input("Oil Price (₹/ltr)", value=60.0)

if st.button("🚀 Run Simulation"):
    base_yield_map = {
        "HDPE": {"oil": 75, "wax": 5, "char": 10, "ncg": 10},
        "LDPE": {"oil": 78, "wax": 4, "char": 8, "ncg": 10},
        "PP": {"oil": 70, "wax": 6, "char": 10, "ncg": 14}
    }

    if feedstock_type == "Mixed":
        oil_yield = (mix_hdpe * base_yield_map["HDPE"]["oil"] + mix_ldpe * base_yield_map["LDPE"]["oil"] + mix_pp * base_yield_map["PP"]["oil"]) / 100
        wax_yield = (mix_hdpe * base_yield_map["HDPE"]["wax"] + mix_ldpe * base_yield_map["LDPE"]["wax"] + mix_pp * base_yield_map["PP"]["wax"]) / 100
        char_yield = (mix_hdpe * base_yield_map["HDPE"]["char"] + mix_ldpe * base_yield_map["LDPE"]["char"] + mix_pp * base_yield_map["PP"]["char"]) / 100
        ncg_yield = 100 - oil_yield - wax_yield - char_yield
    else:
        yields = base_yield_map[feedstock_type]
        oil_yield = yields["oil"]
        wax_yield = yields["wax"]
        char_yield = yields["char"]
        ncg_yield = yields["ncg"]

    temp_boost = np.interp(reactor_temp, [400, 470, 500], [0, 6, -2])
    catalyst_multiplier_by_type = {"ZSM-5": 1.2, "Alumina": 1.0, "Clay": 0.9, "Bentonite": 0.85, "FCC Catalyst": 1.1, "None": 0.0}
    catalyst_bonus = catalyst_eff / 100 * (catalyst_qty / 1000) * catalyst_multiplier_by_type[catalyst_type] * 10

    sequence_bonus = {
        "S1: Basic": {"oil": 0, "wax": 0},
        "S2: Cat Only": {"oil": 3, "wax": -2},
        "S3: Tar+Cat": {"oil": 5, "wax": -4},
        "S4: Optimized": {"oil": 7, "wax": -5},
        "S5: Bypass Test": {"oil": -2, "wax": 2},
        "S6: Heavy Oil Recycle": {"oil": 8, "wax": -5}
    }

    oil_yield += temp_boost + catalyst_bonus + sequence_bonus[config]["oil"]
    wax_yield += sequence_bonus[config]["wax"]

    if enable_recycle:
        wax_recovery = 0.5 * wax_yield * min(max_recycles, 2)
        oil_yield += wax_recovery
        wax_yield -= wax_recovery
        if enable_precracker:
            oil_yield += 0.5 * wax_recovery * (catalyst_boost - 1.0)

    total = oil_yield + wax_yield + char_yield + ncg_yield
    oil_yield = oil_yield / total * 100
    wax_yield = wax_yield / total * 100
    char_yield = char_yield / total * 100
    ncg_yield = 100 - oil_yield - wax_yield - char_yield

    oil_kg = batch_size * oil_yield / 100
    wax_kg = batch_size * wax_yield / 100
    char_kg = batch_size * char_yield / 100
    ncg_kg = batch_size * ncg_yield / 100

    oil_volume_ltr = oil_kg / 0.806
    light_frac = 0.25 * oil_kg
    mid_frac = 0.5 * oil_kg
    heavy_frac = 0.25 * oil_kg
    light_vol = light_frac / 0.715
    mid_vol = mid_frac / 0.82
    heavy_vol = heavy_frac / 0.885

    revenue = oil_volume_ltr * oil_price + ncg_kg * ncg_saving
    total_cost = batch_size * feed_cost + batch_size * energy_cost + catalyst_qty * catalyst_cost / catalyst_life
    profit = revenue - total_cost
    roi = profit / total_cost * 100 if total_cost else 0

    df = pd.DataFrame({
        "Metric": ["Oil Yield (%)", "Wax Yield (%)", "Char (%)", "NCG (%)", "Oil Output (L)", "C5–C10 (L)", "C11–C17 (L)", "C18–C24 (L)", "Profit (₹)", "ROI (%)"],
        "Value": [round(oil_yield, 2), round(wax_yield, 2), round(char_yield, 2), round(ncg_yield, 2), round(oil_volume_ltr, 2), round(light_vol, 2), round(mid_vol, 2), round(heavy_vol, 2), round(profit, 2), round(roi, 2)]
    })

    st.success("✅ Simulation Complete")
    st.dataframe(df)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv, file_name="pyrolysis_simulation_result.csv")

    st.subheader("📊 Advanced Tuning Matrix: Temperature vs Yield vs Wax")
    temp_range = np.arange(400, 551, 10)
    oil_list = [np.interp(t, [400, 470, 500], [oil_yield - 6, oil_yield, oil_yield - 2]) for t in temp_range]
    wax_list = [np.interp(t, [400, 470, 500], [wax_yield + 3, wax_yield, wax_yield + 5]) for t in temp_range]

    fig, ax = plt.subplots()
    ax.plot(temp_range, oil_list, label="Oil Yield (%)", marker='o')
    ax.plot(temp_range, wax_list, label="Wax Yield (%)", marker='s')
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Yield (%)")
    ax.set_title("Temperature vs Yield/Wax")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)

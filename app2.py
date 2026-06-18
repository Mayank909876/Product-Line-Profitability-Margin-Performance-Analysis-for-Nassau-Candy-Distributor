"""
Nassau Candy Distributor — Product Line Profitability & Margin Performance Dashboard
======================================================================================
Run with:  streamlit run app.py
Place "Nassau Candy Distributor.csv" in the same folder, or upload it from the sidebar.
"""
 
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
 
# ──────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nassau Candy — Profitability Dashboard",
    page_icon="🍬",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
# ──────────────────────────────────────────────────────────────────────────
# THEME / STYLE
# ──────────────────────────────────────────────────────────────────────────
PALETTE = {
    "cocoa": "#3A2317",
    "caramel": "#C17F3E",
    "cream": "#FAF5EC",
    "teal": "#1B8E83",
    "red": "#D6455A",
    "amber": "#E0A23B",
    "ink": "#23150E",
}
 
CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Inter:wght@400;500;600&display=swap');
 
html, body, [class*="css"]  {{
    font-family: 'Inter', sans-serif;
}}
 
.block-container {{
    padding-top: 1.4rem;
}}
 
.nassau-header {{
    background: linear-gradient(135deg, {PALETTE['cocoa']} 0%, #54331F 100%);
    border-radius: 16px;
    padding: 1.6rem 2rem;
    color: {PALETTE['cream']};
    margin-bottom: 1.2rem;
    position: relative;
    overflow: hidden;
}}
.nassau-header h1 {{
    font-family: 'Fraunces', serif;
    font-size: 1.9rem;
    margin: 0 0 0.25rem 0;
    color: {PALETTE['cream']};
}}
.nassau-header p {{
    margin: 0;
    color: #E8D9C5;
    font-size: 0.95rem;
}}
.nassau-stripe {{
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 6px;
    background: repeating-linear-gradient(
        45deg,
        {PALETTE['caramel']} 0px, {PALETTE['caramel']} 14px,
        {PALETTE['teal']} 14px, {PALETTE['teal']} 28px,
        {PALETTE['amber']} 28px, {PALETTE['amber']} 42px
    );
}}
 
div[data-testid="stMetric"] {{
    background: white;
    border: 1px solid #EEE3D3;
    border-radius: 12px;
    padding: 0.7rem 0.9rem 0.5rem 0.9rem;
    box-shadow: 0 1px 3px rgba(58,35,23,0.06);
}}
div[data-testid="stMetricLabel"] {{
    color: {PALETTE['cocoa']};
    font-weight: 600;
}}
 
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    background-color: #F2E9DA;
    border-radius: 10px 10px 0 0;
    padding: 0.5rem 1rem;
    font-weight: 600;
    color: {PALETTE['cocoa']};
}}
.stTabs [aria-selected="true"] {{
    background-color: {PALETTE['cocoa']} !important;
    color: {PALETTE['cream']} !important;
}}
 
.risk-badge {{
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
 
CHART_TEMPLATE = "simple_white"
DISCRETE_SEQ = [PALETTE["caramel"], PALETTE["teal"], PALETTE["amber"],
                PALETTE["red"], "#7A5240", "#4E8C7C"]
 
# ──────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────────────────────────────────
CANDIDATE_FILES = [
    "Nassau_Candy_Distributor.csv",
    "Nassau Candy Distributor.csv",
    "nassau_candy_distributor.csv",
]
 
 
def find_bundled_file():
    for f in CANDIDATE_FILES:
        if os.path.exists(f):
            return f
    return None
 
 
@st.cache_data(show_spinner="Loading & cleaning data…")
def load_and_clean(file_obj_or_path):
    df = pd.read_csv(file_obj_or_path)
 
    # ── Parse dates (Order Date drives the date-range filter) ──
    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True, errors="coerce")
    if "Ship Date" in df.columns:
        df["Ship Date"] = pd.to_datetime(df["Ship Date"], dayfirst=True, errors="coerce")
 
    rows_before = len(df)
 
    # ── Validate cost & sales values / remove zero-sales or invalid records ──
    df = df[df["Sales"] > 0]
    df = df[df["Units"] > 0]
    df = df.dropna(subset=["Sales", "Cost", "Gross Profit", "Units"])
 
    # ── Standardize product & division labels ──
    df["Product Name"] = (
        df["Product Name"].astype(str).str.strip()
        .str.replace(r"\s*-\s*", " - ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )
    df["Division"] = df["Division"].astype(str).str.strip().str.title()
    if "Region" in df.columns:
        df["Region"] = df["Region"].astype(str).str.strip().str.title()
 
    rows_after = len(df)
 
    # ── Feature engineering / profitability metrics ──
    df["Gross Margin %"] = (df["Gross Profit"] / df["Sales"] * 100)
    df["Profit per Unit"] = (df["Gross Profit"] / df["Units"])
    df["Cost per Unit"] = (df["Cost"] / df["Units"])
 
    total_sales = df["Sales"].sum()
    total_profit = df["Gross Profit"].sum()
    df["Revenue Contribution %"] = df["Sales"] / total_sales * 100
    df["Profit Contribution %"] = df["Gross Profit"] / total_profit * 100
 
    df.attrs["rows_removed"] = rows_before - rows_after
    return df
 
 
def margin_risk_label(margin, threshold):
    """Two-tier risk classification driven by the sidebar threshold slider."""
    if margin < threshold * 0.6:
        return "🔴 High Risk"
    elif margin < threshold:
        return "🟠 At Risk"
    return "🟢 Healthy"
 
 
# ──────────────────────────────────────────────────────────────────────────
# SIDEBAR — DATA SOURCE
# ──────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🍬 Nassau Candy")
st.sidebar.caption("Product Line Profitability & Margin Dashboard")
st.sidebar.divider()
 
bundled = find_bundled_file()
with st.sidebar.expander("📂 Data source", expanded=bundled is None):
    if bundled:
        st.success(f"Using bundled file: `{bundled}`")
    uploaded = st.file_uploader("Upload / replace CSV", type="csv")
 
data_source = uploaded if uploaded is not None else bundled
if data_source is None:
    st.warning("⬅️ Upload **Nassau Candy Distributor.csv** from the sidebar to get started.")
    st.stop()
 
df_raw = load_and_clean(data_source)
 
if df_raw.attrs.get("rows_removed"):
    st.sidebar.caption(f"🧹 {df_raw.attrs['rows_removed']} invalid rows removed during cleaning.")
 
# ──────────────────────────────────────────────────────────────────────────
# SIDEBAR — USER CAPABILITIES (filters)
# ──────────────────────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.markdown("### 🔎 Filters")
 
valid_dates = df_raw["Order Date"].dropna()
min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
 
date_range = st.sidebar.date_input(
    "📅 Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date
 
divisions = sorted(df_raw["Division"].dropna().unique())
selected_divisions = st.sidebar.multiselect(
    "🏷️ Division", options=divisions, default=divisions
)
 
margin_threshold = st.sidebar.slider(
    "📉 Margin risk threshold (%)",
    min_value=0, max_value=100, value=35, step=1,
    help="Products / orders below this Gross Margin % are flagged as at-risk "
         "across every tab.",
)
 
search_term = st.sidebar.text_input(
    "🔍 Product search", placeholder="e.g. Wonka, Nerds, Taffy"
).strip()
 
# ── Apply filters ──
mask = (
    (df_raw["Order Date"].dt.date >= start_date)
    & (df_raw["Order Date"].dt.date <= end_date)
    & (df_raw["Division"].isin(selected_divisions))
)
df = df_raw.loc[mask].copy()
 
if df.empty:
    st.warning("No records match the current filters — widen the date range or division selection.")
    st.stop()
 
df["Margin Risk"] = df["Gross Margin %"].apply(lambda m: margin_risk_label(m, margin_threshold))
 
# ──────────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="nassau-header">
        <h1>🍬 Nassau Candy Distributor</h1>
        <p>Product Line Profitability &amp; Margin Performance — live analytics</p>
        <div class="nassau-stripe"></div>
    </div>
    """,
    unsafe_allow_html=True,
)
 
# ──────────────────────────────────────────────────────────────────────────
# TOP-LEVEL KPI ROW  (KPI section from the requirements doc)
# ──────────────────────────────────────────────────────────────────────────
total_sales = df["Sales"].sum()
total_profit = df["Gross Profit"].sum()
overall_margin = total_profit / total_sales * 100 if total_sales else 0
avg_profit_per_unit = df["Profit per Unit"].mean()
margin_volatility = df["Gross Margin %"].std()
 
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Revenue", f"${total_sales:,.0f}")
k2.metric("Total Gross Profit", f"${total_profit:,.0f}")
k3.metric("Overall Gross Margin", f"{overall_margin:.1f}%")
k4.metric("Avg Profit / Unit", f"${avg_profit_per_unit:,.2f}")
k5.metric("Margin Volatility (σ)", f"{margin_volatility:.1f} pts")
 
st.caption(
    f"Showing **{len(df):,}** orders across **{df['Product Name'].nunique()}** products, "
    f"**{start_date} → {end_date}**, divisions: {', '.join(selected_divisions) or '—'}."
)
 
# ──────────────────────────────────────────────────────────────────────────
# PRECOMPUTED AGGREGATES USED ACROSS TABS
# ──────────────────────────────────────────────────────────────────────────
product_summary = (
    df.groupby(["Product Name", "Division"])
    .agg(
        Total_Sales=("Sales", "sum"),
        Total_Profit=("Gross Profit", "sum"),
        Total_Cost=("Cost", "sum"),
        Total_Units=("Units", "sum"),
        Avg_Gross_Margin=("Gross Margin %", "mean"),
        Avg_Profit_per_Unit=("Profit per Unit", "mean"),
        Orders=("Sales", "count"),
    )
    .reset_index()
)
product_summary["Profit Contribution %"] = (
    product_summary["Total_Profit"] / product_summary["Total_Profit"].sum() * 100
)
product_summary["Revenue Contribution %"] = (
    product_summary["Total_Sales"] / product_summary["Total_Sales"].sum() * 100
)
product_summary["Cost_to_Sales_Ratio"] = (
    product_summary["Total_Cost"] / product_summary["Total_Sales"] * 100
)
product_summary["Risk Flag"] = product_summary["Avg_Gross_Margin"].apply(
    lambda m: margin_risk_label(m, margin_threshold)
)
product_summary = product_summary.sort_values("Total_Profit", ascending=False).reset_index(drop=True)
 
 
def apply_search(frame, col="Product Name"):
    if not search_term:
        return frame
    return frame[frame[col].str.contains(search_term, case=False, na=False)]
 
 
# ──────────────────────────────────────────────────────────────────────────
# TABS — DASHBOARD MODULES
# ──────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📊 Product Profitability Overview",
        "🏭 Division Performance Dashboard",
        "💰 Cost vs Margin Diagnostics",
        "📈 Profit Concentration Analysis",
    ]
)
 
# ── TAB 1 — PRODUCT PROFITABILITY OVERVIEW ─────────────────────────────────
with tab1:
    st.subheader("Product-Level Margin Leaderboard")
 
    leaderboard = apply_search(product_summary)
    if search_term and leaderboard.empty:
        st.info(f"No products match “{search_term}”.")
 
    display_cols = {
        "Product Name": "Product",
        "Division": "Division",
        "Total_Sales": "Total Sales ($)",
        "Total_Profit": "Total Profit ($)",
        "Avg_Gross_Margin": "Avg Margin (%)",
        "Avg_Profit_per_Unit": "Profit / Unit ($)",
        "Profit Contribution %": "Profit Share (%)",
        "Risk Flag": "Risk",
    }
    st.dataframe(
        leaderboard[list(display_cols.keys())].rename(columns=display_cols).style.format(
            {
                "Total Sales ($)": "${:,.0f}",
                "Total Profit ($)": "${:,.0f}",
                "Avg Margin (%)": "{:.1f}%",
                "Profit / Unit ($)": "${:,.2f}",
                "Profit Share (%)": "{:.1f}%",
            }
        ),
        use_container_width=True,
        height=360,
    )
 
    col1, col2 = st.columns(2)
    with col1:
        margin_sorted = product_summary.sort_values("Avg_Gross_Margin")
        fig = px.bar(
            margin_sorted,
            x="Avg_Gross_Margin",
            y="Product Name",
            orientation="h",
            color="Risk Flag",
            color_discrete_map={
                "🔴 High Risk": PALETTE["red"],
                "🟠 At Risk": PALETTE["amber"],
                "🟢 Healthy": PALETTE["teal"],
            },
            labels={"Avg_Gross_Margin": "Avg Gross Margin (%)", "Product Name": ""},
            title="Margin Leaderboard (all products)",
            template=CHART_TEMPLATE,
        )
        fig.add_vline(x=margin_threshold, line_dash="dash", line_color=PALETTE["cocoa"],
                       annotation_text=f"Threshold {margin_threshold}%")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.pie(
            product_summary,
            names="Product Name",
            values="Profit Contribution %",
            hole=0.45,
            title="Profit Contribution by Product",
            color_discrete_sequence=DISCRETE_SEQ,
            template=CHART_TEMPLATE,
        )
        fig2.update_traces(textposition="inside", textinfo="percent+label", textfont_size=10)
        st.plotly_chart(fig2, use_container_width=True)
 
# ── TAB 2 — DIVISION PERFORMANCE DASHBOARD ─────────────────────────────────
with tab2:
    st.subheader("Division-Level Performance")
 
    division_summary = (
        df.groupby("Division")
        .agg(
            Total_Sales=("Sales", "sum"),
            Total_Profit=("Gross Profit", "sum"),
            Avg_Gross_Margin=("Gross Margin %", "mean"),
            Orders=("Sales", "count"),
        )
        .reset_index()
    )
    division_summary["Revenue Contribution %"] = (
        division_summary["Total_Sales"] / division_summary["Total_Sales"].sum() * 100
    )
    division_summary["Profit Contribution %"] = (
        division_summary["Total_Profit"] / division_summary["Total_Profit"].sum() * 100
    )
    division_summary = division_summary.sort_values("Total_Profit", ascending=False)
 
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_bar(name="Revenue", x=division_summary["Division"], y=division_summary["Total_Sales"],
                    marker_color=PALETTE["caramel"])
        fig.add_bar(name="Gross Profit", x=division_summary["Division"], y=division_summary["Total_Profit"],
                    marker_color=PALETTE["teal"])
        fig.update_layout(
            barmode="group", title="Revenue vs Profit by Division",
            template=CHART_TEMPLATE, yaxis_title="Amount ($)",
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.box(
            df, x="Division", y="Gross Margin %", color="Division",
            color_discrete_sequence=DISCRETE_SEQ,
            title="Margin Distribution by Division",
            template=CHART_TEMPLATE, points="outliers",
        )
        fig2.add_hline(y=margin_threshold, line_dash="dash", line_color=PALETTE["red"],
                        annotation_text=f"Risk threshold {margin_threshold}%")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
 
    st.markdown("#### Revenue vs Profit Imbalance")
    imbalance = division_summary.copy()
    imbalance["Gap (Profit − Revenue share)"] = (
        imbalance["Profit Contribution %"] - imbalance["Revenue Contribution %"]
    )
    st.dataframe(
        imbalance[
            ["Division", "Total_Sales", "Total_Profit", "Avg_Gross_Margin",
             "Revenue Contribution %", "Profit Contribution %", "Gap (Profit − Revenue share)"]
        ].rename(columns={
            "Total_Sales": "Total Sales ($)", "Total_Profit": "Total Profit ($)",
            "Avg_Gross_Margin": "Avg Margin (%)",
        }).style.format({
            "Total Sales ($)": "${:,.0f}", "Total Profit ($)": "${:,.0f}",
            "Avg Margin (%)": "{:.1f}%", "Revenue Contribution %": "{:.1f}%",
            "Profit Contribution %": "{:.1f}%", "Gap (Profit − Revenue share)": "{:+.1f}%",
        }),
        use_container_width=True,
    )
 
# ── TAB 3 — COST VS MARGIN DIAGNOSTICS ─────────────────────────────────────
with tab3:
    st.subheader("Cost Structure & Margin Risk")
 
    cost_view = apply_search(product_summary)
 
    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.scatter(
            cost_view if not cost_view.empty else product_summary,
            x="Total_Sales", y="Total_Cost",
            color="Risk Flag", size="Cost_to_Sales_Ratio",
            hover_name="Product Name",
            color_discrete_map={
                "🔴 High Risk": PALETTE["red"],
                "🟠 At Risk": PALETTE["amber"],
                "🟢 Healthy": PALETTE["teal"],
            },
            title=f"Cost vs Sales — flagged below {margin_threshold}% margin",
            labels={"Total_Sales": "Total Sales ($)", "Total_Cost": "Total Cost ($)"},
            template=CHART_TEMPLATE,
        )
        max_val = float(max(product_summary["Total_Sales"].max(), product_summary["Total_Cost"].max()))
        fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                       line=dict(dash="dot", color="gray"))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        risk_counts = product_summary["Risk Flag"].value_counts()
        fig2 = px.pie(
            values=risk_counts.values, names=risk_counts.index, hole=0.55,
            color=risk_counts.index,
            color_discrete_map={
                "🔴 High Risk": PALETTE["red"],
                "🟠 At Risk": PALETTE["amber"],
                "🟢 Healthy": PALETTE["teal"],
            },
            title="Products by Risk Flag",
            template=CHART_TEMPLATE,
        )
        st.plotly_chart(fig2, use_container_width=True)
 
    st.markdown(f"#### ⚠️ Flagged Products (margin below {margin_threshold}%)")
    flagged = apply_search(
        product_summary[product_summary["Avg_Gross_Margin"] < margin_threshold]
        .sort_values("Avg_Gross_Margin")
    )
    if flagged.empty:
        st.success("✅ No products fall below the current margin threshold.")
    else:
        st.dataframe(
            flagged[["Product Name", "Division", "Total_Sales", "Total_Cost",
                     "Cost_to_Sales_Ratio", "Avg_Gross_Margin", "Risk Flag"]]
            .rename(columns={
                "Total_Sales": "Total Sales ($)", "Total_Cost": "Total Cost ($)",
                "Cost_to_Sales_Ratio": "Cost / Sales (%)", "Avg_Gross_Margin": "Avg Margin (%)",
            }).style.format({
                "Total Sales ($)": "${:,.0f}", "Total Cost ($)": "${:,.0f}",
                "Cost / Sales (%)": "{:.1f}%", "Avg Margin (%)": "{:.1f}%",
            }),
            use_container_width=True,
        )
 
# ── TAB 4 — PROFIT CONCENTRATION (PARETO) ANALYSIS ─────────────────────────
with tab4:
    st.subheader("Profit Concentration (Pareto) Analysis")
 
    pareto = product_summary.sort_values("Total_Profit", ascending=False).copy()
    pareto["Cumulative_Profit_%"] = pareto["Total_Profit"].cumsum() / pareto["Total_Profit"].sum() * 100
    n_products_80 = int((pareto["Cumulative_Profit_%"] <= 80).sum() + 1)
    n_products_80 = min(n_products_80, len(pareto))
 
    bar_colors = [PALETTE["teal"] if i < n_products_80 else PALETTE["caramel"] for i in range(len(pareto))]
 
    fig = go.Figure()
    fig.add_bar(x=pareto["Product Name"], y=pareto["Total_Profit"], name="Gross Profit",
                marker_color=bar_colors)
    fig.add_trace(go.Scatter(
        x=pareto["Product Name"], y=pareto["Cumulative_Profit_%"],
        name="Cumulative Profit %", mode="lines+markers",
        line=dict(color=PALETTE["red"], width=3), yaxis="y2",
    ))
    fig.update_layout(
        title=f"Product Pareto — {n_products_80} of {len(pareto)} products drive 80% of profit",
        template=CHART_TEMPLATE,
        yaxis=dict(title="Gross Profit ($)"),
        yaxis2=dict(title="Cumulative Profit (%)", overlaying="y", side="right", range=[0, 115]),
        legend=dict(orientation="h", y=1.15),
        shapes=[dict(type="line", xref="paper", x0=0, x1=1, yref="y2", y0=80, y1=80,
                     line=dict(dash="dash", color="gray"))],
    )
    st.plotly_chart(fig, use_container_width=True)
 
    st.markdown("#### Dependency Indicators")
    top1_share = pareto.iloc[0]["Profit Contribution %"]
    top3_share = pareto.head(min(3, len(pareto)))["Profit Contribution %"].sum()
 
    c1, c2, c3 = st.columns(3)
    c1.metric("Products driving 80% of profit", f"{n_products_80} / {len(pareto)}")
    c2.metric("Top 1 product's profit share", f"{top1_share:.1f}%")
    c3.metric("Top 3 products' profit share", f"{top3_share:.1f}%")
 
    if top3_share > 60:
        st.error("⚠️ High concentration risk — the business over-relies on a small number of products.")
    else:
        st.success("✅ Profit is reasonably diversified across the product portfolio.")
 
    with st.expander("📋 Full Pareto table"):
        st.dataframe(
            apply_search(pareto)[
                ["Product Name", "Division", "Total_Sales", "Total_Profit",
                 "Avg_Gross_Margin", "Cumulative_Profit_%"]
            ].rename(columns={
                "Total_Sales": "Total Sales ($)", "Total_Profit": "Total Profit ($)",
                "Avg_Gross_Margin": "Avg Margin (%)", "Cumulative_Profit_%": "Cumulative Profit (%)",
            }).style.format({
                "Total Sales ($)": "${:,.0f}", "Total Profit ($)": "${:,.0f}",
                "Avg Margin (%)": "{:.1f}%", "Cumulative Profit (%)": "{:.1f}%",
            }),
            use_container_width=True,
        )
 
# ──────────────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Nassau Candy Distributor · Product Line Profitability & Margin Performance Dashboard · "
    "Built with Streamlit + Plotly"
)
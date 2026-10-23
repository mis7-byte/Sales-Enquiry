import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Enquiry Master Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Enquiry Master Analytics Dashboard")

# --- DATA LOADING & PREPROCESSING ---
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "164l9v3nGrUTrgC3R_pt2bcX2FgZb2tGvcODtE55Efkk"
    gid = "0"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    # Parse Date & Numeric Fields
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce').fillna(0)
    df['Rate'] = pd.to_numeric(df['Rate'], errors='coerce').fillna(0)
    df['Amount'] = df['QTY'] * df['Rate']
    
    # Parse EnquiryReceivedTime and ReplyTime to compute Reply Time Variance (in minutes)
    def parse_time_diff(row):
        try:
            date_str = row['Date'].strftime('%Y-%m-%d')
            recv_time = pd.to_datetime(f"{date_str} {row['EnquiryReceivedTime']}", errors='coerce')
            reply_time = pd.to_datetime(f"{date_str} {row['ReplyTime']}", errors='coerce')
            
            if pd.notnull(recv_time) and pd.notnull(reply_time):
                if reply_time < recv_time:
                    reply_time += pd.Timedelta(days=1)
                return (reply_time - recv_time).total_seconds() / 60.0
        except Exception:
            return None
        return None

    df['Reply_Variance_Mins'] = df.apply(parse_time_diff, axis=1)
    return df

try:
    data = load_data()
except Exception as e:
    st.error(f"Error loading Google Sheet data: {e}")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🗓️ Date & Comparison Mode")

min_date = data['Date'].min().date() if not data['Date'].isna().all() else pd.to_datetime("today").date()
max_date = data['Date'].max().date() if not data['Date'].isna().all() else pd.to_datetime("today").date()

mode = st.sidebar.radio("Select View Mode:", ["Single Date Range", "Compare Date Ranges (with Variance)"])

# Date Selection Logic
if mode == "Single Date Range":
    selected_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])
    if len(selected_range) == 2:
        start_date, end_date = selected_range
        df_base = data[(data['Date'].dt.date >= start_date) & (data['Date'].dt.date <= end_date)]
    else:
        df_base = data.copy()
    compare_mode_active = False
else:
    col_p1, col_p2 = st.sidebar.columns(2)
    with col_p1:
        range1 = st.date_input("Period 1", [min_date, max_date], key="r1")
    with col_p2:
        range2 = st.date_input("Period 2", [min_date, max_date], key="r2")
    
    if len(range1) == 2 and len(range2) == 2:
        df_p1_raw = data[(data['Date'].dt.date >= range1[0]) & (data['Date'].dt.date <= range1[1])]
        df_p2_raw = data[(data['Date'].dt.date >= range2[0]) & (data['Date'].dt.date <= range2[1])]
    else:
        df_p1_raw, df_p2_raw = data.copy(), data.copy()
    
    compare_mode_active = True

st.sidebar.markdown("---")
st.sidebar.header("🔍 Dynamic Filters")

se_filter = st.sidebar.multiselect("Sales Executive", sorted(data['SalesExecutive'].dropna().unique()))
cust_filter = st.sidebar.multiselect("Customer Name", sorted(data['CustomerName'].dropna().unique()))
cat_filter = st.sidebar.multiselect("Category", sorted(data['Category'].dropna().unique()))
grade_filter = st.sidebar.multiselect("Grade", sorted(data['Grade'].dropna().unique()))
mat_filter = st.sidebar.multiselect("Material Availability", sorted(data['MaterialAvailability'].dropna().unique()))
status_filter = st.sidebar.multiselect("Status", sorted(data['Status'].dropna().unique()))

def apply_multiselect_filters(df):
    d = df.copy()
    if se_filter: d = d[d['SalesExecutive'].isin(se_filter)]
    if cust_filter: d = d[d['CustomerName'].isin(cust_filter)]
    if cat_filter: d = d[d['Category'].isin(cat_filter)]
    if grade_filter: d = d[d['Grade'].isin(grade_filter)]
    if mat_filter: d = d[d['MaterialAvailability'].isin(mat_filter)]
    if status_filter: d = d[d['Status'].isin(status_filter)]
    return d

if not compare_mode_active:
    df_filtered = apply_multiselect_filters(df_base)
else:
    df_p1 = apply_multiselect_filters(df_p1_raw)
    df_p2 = apply_multiselect_filters(df_p2_raw)
    df_filtered = pd.concat([df_p1, df_p2])

# --- KPI METRICS DISPLAY ---
st.markdown("### 📌 Key Performance Indicators (KPIs)")
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

total_cust = df_filtered['CustomerName'].nunique()
total_cat = df_filtered['Category'].nunique()
total_grade = df_filtered['Grade'].nunique()
total_qty = df_filtered['QTY'].sum()
total_amount = df_filtered['Amount'].sum()

kpi1.metric("Total Customers", f"{total_cust:,}")
kpi2.metric("Total Categories", f"{total_cat:,}")
kpi3.metric("Total Grades", f"{total_grade:,}")
kpi4.metric("Total Qty", f"{total_qty:,.2f}")
kpi5.metric("Total Amount", f"${total_amount:,.2f}")

# --- DATE VARIANCE COMPARISON SECTION (IF COMPARE MODE) ---
if compare_mode_active:
    st.markdown("---")
    st.subheader("📈 Period-Over-Period Date Variance Analysis")
    
    p1_qty, p1_amt = df_p1['QTY'].sum(), df_p1['Amount'].sum()
    p2_qty, p2_amt = df_p2['QTY'].sum(), df_p2['Amount'].sum()
    
    qty_diff = p2_qty - p1_qty
    qty_pct = (qty_diff / p1_qty * 100) if p1_qty > 0 else 0
    
    amt_diff = p2_amt - p1_amt
    amt_pct = (amt_diff / p1_amt * 100) if p1_amt > 0 else 0
    
    vcol1, vcol2, vcol3 = st.columns(3)
    vcol1.metric("Period 1 vs Period 2 Qty Variance", f"{qty_diff:,.2f}", f"{qty_pct:.2f}%")
    vcol2.metric("Period 1 vs Period 2 Amount Variance", f"${amt_diff:,.2f}", f"{amt_pct:.2f}%")
    vcol3.metric("Enquiry Count Variance", f"{len(df_p2) - len(df_p1):,}", f"{(len(df_p2) - len(df_p1)) / len(df_p1) * 100:.2f}%" if len(df_p1) > 0 else "0%")

st.markdown("---")

# --- DASHBOARD CHARTS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 Enquiry Source Distribution ('Through')")
    through_df = df_filtered.groupby('Through').size().reset_index(name='Count')
    fig_pie = px.pie(through_df, names='Through', values='Count', hole=0.4)
    fig_pie.update_traces(textinfo='label+percent+value', textposition='outside')
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.subheader("🧑‍💼 Sales Executive Wise Enquiry Quantity")
    se_qty = df_filtered.groupby('SalesExecutive')['QTY'].sum().reset_index()
    fig_bar = px.bar(se_qty, x='SalesExecutive', y='QTY', text='QTY')
    fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

col3, col4 = st.columns(2)

with col3:
    st.subheader("📦 Customer Wise Category Enquiry Qty")
    cust_cat = df_filtered.groupby(['CustomerName', 'Category'])['QTY'].sum().reset_index()
    fig_cust_cat = px.bar(cust_cat, x='CustomerName', y='QTY', color='Category', barmode='stack')
    st.plotly_chart(fig_cust_cat, use_container_width=True)

with col4:
    st.subheader("🏷️ Customer Wise Grade Enquiry Qty")
    cust_grade = df_filtered.groupby(['CustomerName', 'Grade'])['QTY'].sum().reset_index()
    fig_cust_grade = px.bar(cust_grade, x='CustomerName', y='QTY', color='Grade', barmode='stack')
    st.plotly_chart(fig_cust_grade, use_container_width=True)

st.markdown("---")

col5, col6 = st.columns(2)

with col5:
    st.subheader("🏬 Customer Wise Material Availability Qty")
    cust_mat_qty = df_filtered.groupby(['CustomerName', 'MaterialAvailability'])['QTY'].sum().reset_index()
    fig_mat_qty = px.bar(cust_mat_qty, x='CustomerName', y='QTY', color='MaterialAvailability', barmode='group')
    st.plotly_chart(fig_mat_qty, use_container_width=True)

with col6:
    st.subheader("📊 Sales Executive Wise Status")
    se_status = df_filtered.groupby(['SalesExecutive', 'Status']).size().reset_index(name='Count')
    fig_se_status = px.bar(se_status, x='SalesExecutive', y='Count', color='Status', barmode='stack')
    st.plotly_chart(fig_se_status, use_container_width=True)

st.markdown("---")

col7, col8 = st.columns(2)

with col7:
    st.subheader("📋 Customer Wise Material Availability (Status Count)")
    cust_mat_cnt = df_filtered.groupby(['CustomerName', 'MaterialAvailability']).size().reset_index(name='EnquiryCount')
    fig_mat_cnt = px.bar(cust_mat_cnt, x='CustomerName', y='EnquiryCount', color='MaterialAvailability', barmode='group')
    st.plotly_chart(fig_mat_cnt, use_container_width=True)

with col8:
    st.subheader("⏱️ Sales Executive Wise Average Reply Time (Minutes)")
    se_reply = df_filtered.groupby('SalesExecutive')['Reply_Variance_Mins'].mean().reset_index()
    se_reply['Reply_Variance_Mins'] = se_reply['Reply_Variance_Mins'].round(2)
    fig_reply = px.bar(se_reply, x='SalesExecutive', y='Reply_Variance_Mins', text='Reply_Variance_Mins')
    fig_reply.update_traces(texttemplate='%{text} mins', textposition='outside')
    st.plotly_chart(fig_reply, use_container_width=True)

# Data Table View
with st.expander("📄 View Filtered Data Table"):
    st.dataframe(df_filtered)

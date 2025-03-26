import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime

# 设置页面标题和配置
st.set_page_config(
    page_title="销售数据分析仪表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 应用样式
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 4px 4px 0px 0px;
    }
</style>
""", unsafe_allow_html=True)

# 显示标题
st.title("📊 销售数据分析仪表板")

# 数据加载函数
@st.cache_data
def load_data():
    df = pd.read_csv("mydata.csv")
    
    # 确保日期列是日期类型
    df['日 期'] = pd.to_datetime(df['日 期'])
    
    # 确保数值列是数值类型
    numeric_columns = ['计量/吨', '单价/元', '合计金额/元']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 处理文本字段，确保空值和NaN值转为字符串
    text_columns = ['购货单位', '货物名称', '票据类型', '票号', '车 号', '陈货/新货']
    for col in text_columns:
        df[col] = df[col].astype(str)
        # 将"nan"替换为空字符串
        df[col] = df[col].replace('nan', '')
    
    # 添加计算字段：车数（每行是一车）
    df['车数'] = 1
    
    return df

# 加载数据
with st.spinner("正在加载数据..."):
    df = load_data()

# 侧边栏筛选项
st.sidebar.header("筛选条件")

# 日期范围筛选
min_date = df['日 期'].min().date()
max_date = df['日 期'].max().date()

start_date = st.sidebar.date_input(
    "开始日期",
    min_date,
    min_value=min_date,
    max_value=max_date
)

end_date = st.sidebar.date_input(
    "结束日期",
    max_date,
    min_value=min_date,
    max_value=max_date
)

# 客户筛选 - 过滤掉空值
valid_customers = [c for c in df['购货单位'].unique() if c and c != '']
all_customers = sorted(valid_customers)
selected_customers = st.sidebar.multiselect(
    "选择客户",
    options=all_customers,
    default=[]
)

# 货物筛选 - 过滤掉空值
valid_products = [p for p in df['货物名称'].unique() if p and p != '']
all_products = sorted(valid_products)
selected_products = st.sidebar.multiselect(
    "选择货物",
    options=all_products,
    default=[]
)

# 应用筛选条件
filtered_df = df.copy()

# 日期筛选
filtered_df = filtered_df[
    (filtered_df['日 期'].dt.date >= start_date) &
    (filtered_df['日 期'].dt.date <= end_date)
]

# 客户筛选
if selected_customers:
    filtered_df = filtered_df[filtered_df['购货单位'].isin(selected_customers)]

# 货物筛选
if selected_products:
    filtered_df = filtered_df[filtered_df['货物名称'].isin(selected_products)]

# 显示基本统计信息
st.header("概览")

# 使用列布局
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("总记录数", f"{len(filtered_df):,}")

with col2:
    st.metric("总车数", f"{filtered_df['车数'].sum():,}")

with col3:
    st.metric("总重量(吨)", f"{filtered_df['计量/吨'].sum():,.2f}")

with col4:
    st.metric("总金额(元)", f"{filtered_df['合计金额/元'].sum():,.2f}")

# 创建选项卡
tab1, tab2, tab3 = st.tabs(["按日期汇总", "按客户汇总", "按货物名称汇总"])

with tab1:
    st.subheader("按日期汇总")
    
    # 按日期汇总
    daily_df = filtered_df.groupby(filtered_df['日 期'].dt.date).agg({
        '车数': 'sum',
        '计量/吨': 'sum',
        '合计金额/元': 'sum'
    }).reset_index()
    
    # 创建柱状图
    fig1 = px.bar(
        daily_df,
        x='日 期',
        y=['车数', '计量/吨', '合计金额/元'],
        barmode='group',
        title="日销售情况",
        labels={'value': '数量', '日 期': '日期', 'variable': '指标'},
        color_discrete_sequence=["#1f77b4", "#ff7f0e", "#2ca02c"]
    )
    
    # 添加第二个Y轴显示金额
    fig1.update_layout(
        yaxis=dict(title="车数/重量(吨)"),
        yaxis2=dict(
            title="金额(元)",
            overlaying="y",
            side="right"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 将"合计金额/元"移到第二个Y轴
    for trace in fig1.data:
        if trace.name == "合计金额/元":
            trace.yaxis = "y2"
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # 显示数据表格
    st.dataframe(
        daily_df.rename(columns={
            '日 期': '日期',
            '车数': '车数',
            '计量/吨': '总重量(吨)',
            '合计金额/元': '总金额(元)'
        }).style.format({
            '总重量(吨)': '{:.2f}',
            '总金额(元)': '{:.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

with tab2:
    st.subheader("按客户汇总")
    
    # 按客户汇总 - 跳过空客户名
    customer_df = filtered_df[filtered_df['购货单位'] != ''].groupby('购货单位').agg({
        '车数': 'sum',
        '计量/吨': 'sum',
        '合计金额/元': 'sum'
    }).reset_index().sort_values(by='计量/吨', ascending=False)
    
    # 选择显示前N个客户
    top_n = st.slider("显示前N个客户", min_value=5, max_value=min(30, len(customer_df)), value=10)
    top_customers = customer_df.head(top_n)
    
    # 创建柱状图
    fig2 = px.bar(
        top_customers,
        x='购货单位',
        y=['车数', '计量/吨', '合计金额/元'],
        barmode='group',
        title=f"前{top_n}客户销售情况",
        labels={'value': '数量', '购货单位': '客户', 'variable': '指标'},
        color_discrete_sequence=["#1f77b4", "#ff7f0e", "#2ca02c"]
    )
    
    # 添加第二个Y轴显示金额
    fig2.update_layout(
        yaxis=dict(title="车数/重量(吨)"),
        yaxis2=dict(
            title="金额(元)",
            overlaying="y",
            side="right"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 将"合计金额/元"移到第二个Y轴
    for trace in fig2.data:
        if trace.name == "合计金额/元":
            trace.yaxis = "y2"
    
    st.plotly_chart(fig2, use_container_width=True)
    
    # 饼图展示客户占比
    fig_pie = px.pie(
        top_customers, 
        values='计量/吨', 
        names='购货单位',
        title=f"前{top_n}客户销售量占比"
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # 显示数据表格
    st.dataframe(
        customer_df.rename(columns={
            '购货单位': '客户',
            '车数': '车数',
            '计量/吨': '总重量(吨)',
            '合计金额/元': '总金额(元)'
        }).style.format({
            '总重量(吨)': '{:.2f}',
            '总金额(元)': '{:.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

with tab3:
    st.subheader("按货物名称汇总")
    
    # 按货物名称汇总 - 跳过空货物名
    product_df = filtered_df[filtered_df['货物名称'] != ''].groupby('货物名称').agg({
        '车数': 'sum',
        '计量/吨': 'sum',
        '合计金额/元': 'sum'
    }).reset_index().sort_values(by='计量/吨', ascending=False)
    
    # 创建柱状图
    fig3 = px.bar(
        product_df,
        x='货物名称',
        y=['车数', '计量/吨', '合计金额/元'],
        barmode='group',
        title="按货物名称销售情况",
        labels={'value': '数量', '货物名称': '货物', 'variable': '指标'},
        color_discrete_sequence=["#1f77b4", "#ff7f0e", "#2ca02c"]
    )
    
    # 添加第二个Y轴显示金额
    fig3.update_layout(
        yaxis=dict(title="车数/重量(吨)"),
        yaxis2=dict(
            title="金额(元)",
            overlaying="y",
            side="right"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 将"合计金额/元"移到第二个Y轴
    for trace in fig3.data:
        if trace.name == "合计金额/元":
            trace.yaxis = "y2"
    
    st.plotly_chart(fig3, use_container_width=True)
    
    # 饼图展示货物占比
    fig_pie2 = px.pie(
        product_df, 
        values='计量/吨', 
        names='货物名称',
        title="货物销售量占比"
    )
    st.plotly_chart(fig_pie2, use_container_width=True)
    
    # 显示数据表格
    st.dataframe(
        product_df.rename(columns={
            '货物名称': '货物',
            '车数': '车数',
            '计量/吨': '总重量(吨)',
            '合计金额/元': '总金额(元)'
        }).style.format({
            '总重量(吨)': '{:.2f}',
            '总金额(元)': '{:.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

# 显示高级分析选项
st.header("高级分析")

# 按月汇总选项
if st.checkbox("显示月度汇总"):
    # 按月汇总
    filtered_df['月份'] = filtered_df['日 期'].dt.to_period('M')
    monthly_df = filtered_df.groupby('月份').agg({
        '车数': 'sum',
        '计量/吨': 'sum',
        '合计金额/元': 'sum'
    }).reset_index()
    monthly_df['月份'] = monthly_df['月份'].astype(str)
    
    # 创建月度柱状图
    fig_monthly = px.bar(
        monthly_df,
        x='月份',
        y=['车数', '计量/吨', '合计金额/元'],
        barmode='group',
        title="月度销售情况",
        labels={'value': '数量', '月份': '月份', 'variable': '指标'},
        color_discrete_sequence=["#1f77b4", "#ff7f0e", "#2ca02c"]
    )
    
    # 添加第二个Y轴显示金额
    fig_monthly.update_layout(
        yaxis=dict(title="车数/重量(吨)"),
        yaxis2=dict(
            title="金额(元)",
            overlaying="y",
            side="right"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 将"合计金额/元"移到第二个Y轴
    for trace in fig_monthly.data:
        if trace.name == "合计金额/元":
            trace.yaxis = "y2"
    
    st.plotly_chart(fig_monthly, use_container_width=True)
    
    # 显示月度数据表格
    st.dataframe(
        monthly_df.rename(columns={
            '月份': '月份',
            '车数': '车数',
            '计量/吨': '总重量(吨)',
            '合计金额/元': '总金额(元)'
        }).style.format({
            '总重量(吨)': '{:.2f}',
            '总金额(元)': '{:.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

# 客户与货物交叉分析
if st.checkbox("显示客户-货物交叉分析"):
    # 过滤有效数据
    valid_cross_df = filtered_df[(filtered_df['购货单位'] != '') & (filtered_df['货物名称'] != '')]
    
    # 按客户和货物名称交叉分析
    cross_df = valid_cross_df.pivot_table(
        index='购货单位',
        columns='货物名称',
        values='计量/吨',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    
    st.subheader("客户-货物交叉分析（重量/吨）")
    
    # 正确处理格式化 - 只对数值列应用格式化
    format_dict = {col: '{:.2f}' for col in cross_df.columns if col != '购货单位'}
    st.dataframe(cross_df.style.format(format_dict), use_container_width=True)
    
    # 热力图
    # 准备热力图数据
    heat_df = valid_cross_df.pivot_table(
        index='购货单位', 
        columns='货物名称', 
        values='计量/吨',
        aggfunc='sum',
        fill_value=0
    )
    
    # 选择显示前N个客户
    top_n_heat = st.slider(
        "热力图显示前N个客户", 
        min_value=5, 
        max_value=min(20, len(heat_df)), 
        value=10
    )
    
    # 获取总销量最高的前N个客户
    top_customers_heat = heat_df.sum(axis=1).sort_values(ascending=False).head(top_n_heat).index
    heat_df_filtered = heat_df.loc[top_customers_heat]
    
    # 创建热力图
    fig_heat = px.imshow(
        heat_df_filtered,
        labels=dict(x="货物名称", y="客户", color="销售量(吨)"),
        x=heat_df_filtered.columns,
        y=heat_df_filtered.index,
        title="客户-货物销售热力图",
        color_continuous_scale="YlOrRd"
    )
    
    fig_heat.update_layout(
        xaxis=dict(side="top"),
        height=500
    )
    
    st.plotly_chart(fig_heat, use_container_width=True)

# 原始数据查看
if st.checkbox("查看原始数据"):
    st.subheader("原始销售记录")
    
    # 分页选项
    page_size = st.selectbox("每页显示行数", [10, 20, 50, 100])
    total_pages = len(filtered_df) // page_size + (1 if len(filtered_df) % page_size > 0 else 0)
    
    if total_pages > 0:
        page_num = st.slider("页码", 1, total_pages, 1)
        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(filtered_df))
        
        st.dataframe(
            filtered_df.iloc[start_idx:end_idx].style.format({
                '计量/吨': '{:.2f}',
                '单价/元': '{:.2f}',
                '合计金额/元': '{:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        st.write(f"显示 {start_idx+1} 到 {end_idx}，共 {len(filtered_df)} 条记录")
    else:
        st.write("没有符合条件的数据") 
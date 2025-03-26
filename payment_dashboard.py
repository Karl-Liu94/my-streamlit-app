import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import re
import numpy as np

# 设置页面标题和配置
st.set_page_config(
    page_title="乐山鑫玺矿业有限公司销售分析",
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
    .balance-negative {
        color: red;
    }
    .balance-positive {
        color: green;
    }
</style>
""", unsafe_allow_html=True)

# 显示标题
st.title("📊 乐山鑫玺矿业有限公司销售分析")

# 销售数据加载函数
@st.cache_data
def load_sales_data():
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

# 付款数据加载函数
@st.cache_data
def load_payment_data():
    try:
        df = pd.read_csv("mydata2.csv")
        
        # 处理日期列 - 转换如 "1月1日" 到日期格式
        def parse_chinese_date(date_str):
            if pd.isna(date_str) or not date_str:
                return pd.NaT
            
            # 提取月和日
            match = re.match(r'(\d+)月(\d+)日', date_str)
            if match:
                month, day = match.groups()
                # 假设所有日期都是2023年
                return pd.Timestamp(f'2023-{int(month):02d}-{int(day):02d}')
            return pd.NaT
        
        # 将原始的"日 期"列转换为日期类型并存储在"日期"列
        df['日期'] = df['日 期'].apply(parse_chinese_date)
        
        # 处理金额列 - 去除货币符号和千分位逗号，转换为数值
        def clean_amount(amount_str):
            if pd.isna(amount_str) or not amount_str:
                return 0.0
            
            # 去除人民币符号、千分位逗号和空格
            amount_str = str(amount_str).replace('¥', '').replace(',', '').replace(' ', '')
            
            # 检查是否有负号
            is_negative = '-' in amount_str
            amount_str = amount_str.replace('-', '')
            
            try:
                amount = float(amount_str)
                return -amount if is_negative else amount
            except ValueError:
                return 0.0
        
        df['金额'] = df[' 打款金额 '].apply(clean_amount)
        
        # 确保打款单位列是字符串类型
        df['打款单位'] = df['打款单位'].astype(str)
        df['打款单位'] = df['打款单位'].replace('nan', '')
        
        return df
    except Exception as e:
        st.error(f"加载付款数据时出错: {e}")
        # 返回空的DataFrame，保持程序运行
        return pd.DataFrame(columns=['日期', '打款单位', '金额'])

# 计算客户余额
def calculate_customer_balance(sales_df, payment_df):
    # 按客户汇总销售金额
    sales_by_customer = sales_df[sales_df['购货单位'] != ''].groupby('购货单位')['合计金额/元'].sum().reset_index()
    sales_by_customer.columns = ['客户名称', '销售总额']
    
    # 按客户汇总付款金额
    payment_by_customer = payment_df[payment_df['打款单位'] != ''].groupby('打款单位')['金额'].sum().reset_index()
    payment_by_customer.columns = ['客户名称', '付款总额']
    
    # 合并销售和付款数据
    balance_df = pd.merge(sales_by_customer, payment_by_customer, on='客户名称', how='outer').fillna(0)
    
    # 计算余额
    balance_df['余额'] = balance_df['销售总额'] - balance_df['付款总额']
    
    # 排序
    balance_df = balance_df.sort_values(by='余额', ascending=False)
    
    return balance_df

# 加载数据
with st.spinner("正在加载数据..."):
    sales_df = load_sales_data()
    payment_df = load_payment_data()
    
    # 计算客户余额
    balance_df = calculate_customer_balance(sales_df, payment_df)

# 侧边栏筛选项
st.sidebar.header("筛选条件")

# 日期范围筛选 - 销售数据
sales_min_date = sales_df['日 期'].min().date()
sales_max_date = sales_df['日 期'].max().date()

sales_date_range = st.sidebar.date_input(
    "销售数据日期范围",
    [sales_min_date, sales_max_date],
    min_value=sales_min_date,
    max_value=sales_max_date
)

if len(sales_date_range) == 2:
    sales_start_date, sales_end_date = sales_date_range
else:
    sales_start_date = sales_date_range[0]
    sales_end_date = sales_date_range[0]

# 日期范围筛选 - 付款数据
if not payment_df.empty and '日期' in payment_df.columns:
    payment_min_date = payment_df['日期'].min().date()
    payment_max_date = payment_df['日期'].max().date()

    payment_date_range = st.sidebar.date_input(
        "付款数据日期范围",
        [payment_min_date, payment_max_date],
        min_value=payment_min_date,
        max_value=payment_max_date
    )

    if len(payment_date_range) == 2:
        payment_start_date, payment_end_date = payment_date_range
    else:
        payment_start_date = payment_date_range[0]
        payment_end_date = payment_date_range[0]
else:
    # 默认值
    payment_start_date = sales_start_date
    payment_end_date = sales_end_date

# 客户筛选 - 过滤掉空值
# 合并销售和付款数据中的客户
all_customers_sales = [c for c in sales_df['购货单位'].unique() if c and c != '']
all_customers_payment = [c for c in payment_df['打款单位'].unique() if c and c != '']
all_customers = sorted(list(set(all_customers_sales + all_customers_payment)))

selected_customers = st.sidebar.multiselect(
    "选择客户",
    options=all_customers,
    default=[]
)

# 货物筛选 - 过滤掉空值
valid_products = [p for p in sales_df['货物名称'].unique() if p and p != '']
all_products = sorted(valid_products)
selected_products = st.sidebar.multiselect(
    "选择货物",
    options=all_products,
    default=[]
)

# 应用筛选条件 - 销售数据
filtered_sales_df = sales_df.copy()

# 日期筛选
filtered_sales_df = filtered_sales_df[
    (filtered_sales_df['日 期'].dt.date >= sales_start_date) &
    (filtered_sales_df['日 期'].dt.date <= sales_end_date)
]

# 客户筛选
if selected_customers:
    filtered_sales_df = filtered_sales_df[filtered_sales_df['购货单位'].isin(selected_customers)]

# 货物筛选
if selected_products:
    filtered_sales_df = filtered_sales_df[filtered_sales_df['货物名称'].isin(selected_products)]

# 应用筛选条件 - 付款数据
filtered_payment_df = payment_df.copy()

# 日期筛选
if '日期' in filtered_payment_df.columns and not filtered_payment_df.empty:
    filtered_payment_df = filtered_payment_df[
        (filtered_payment_df['日期'].dt.date >= payment_start_date) &
        (filtered_payment_df['日期'].dt.date <= payment_end_date)
    ]

# 客户筛选
if selected_customers:
    filtered_payment_df = filtered_payment_df[filtered_payment_df['打款单位'].isin(selected_customers)]

# 计算筛选后的客户余额
filtered_balance_df = calculate_customer_balance(filtered_sales_df, filtered_payment_df)

# 显示基本统计信息
st.header("概览")

# 使用列布局
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("销售记录数", f"{len(filtered_sales_df):,}")

with col2:
    st.metric("总车数", f"{filtered_sales_df['车数'].sum():,}")

with col3:
    st.metric("总重量(吨)", f"{filtered_sales_df['计量/吨'].sum():,.2f}")

with col4:
    st.metric("销售总金额(元)", f"{filtered_sales_df['合计金额/元'].sum():,.2f}")

# 付款统计
if not filtered_payment_df.empty:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("付款记录数", f"{len(filtered_payment_df):,}")
    
    with col2:
        payment_total = filtered_payment_df['金额'].sum()
        st.metric("付款总金额(元)", f"{payment_total:,.2f}")
    
    with col3:
        balance = filtered_sales_df['合计金额/元'].sum() - payment_total
        st.metric("总余额(元)", f"{balance:,.2f}", 
                  delta_color="inverse" if balance < 0 else "normal")

# 创建选项卡
tab1, tab2, tab3, tab4, tab5 = st.tabs(["销售汇总", "付款汇总", "客户余额", "按货物汇总", "高级分析"])

# Tab 1: 销售汇总
with tab1:
    st.subheader("销售数据汇总")
    
    # 按日期汇总
    daily_sales_df = filtered_sales_df.groupby(filtered_sales_df['日 期'].dt.date).agg({
        '车数': 'sum',
        '计量/吨': 'sum',
        '合计金额/元': 'sum'
    }).reset_index()
    
    # 创建柱状图
    fig1 = px.bar(
        daily_sales_df,
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
    
    # 按客户汇总
    customer_sales_df = filtered_sales_df[filtered_sales_df['购货单位'] != ''].groupby('购货单位').agg({
        '车数': 'sum',
        '计量/吨': 'sum',
        '合计金额/元': 'sum'
    }).reset_index().sort_values(by='合计金额/元', ascending=False)
    
    st.subheader("按客户销售汇总")
    
    # 显示数据表格
    st.dataframe(
        customer_sales_df.rename(columns={
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

# Tab 2: 付款汇总
with tab2:
    st.subheader("付款数据汇总")
    
    if not filtered_payment_df.empty and '日期' in filtered_payment_df.columns:
        # 按日期汇总
        daily_payment_df = filtered_payment_df.groupby(filtered_payment_df['日期'].dt.date).agg({
            '金额': 'sum'
        }).reset_index()
        
        # 创建柱状图
        fig_payment = px.bar(
            daily_payment_df,
            x='日期',
            y='金额',
            title="日付款情况",
            labels={'金额': '金额(元)', '日期': '日期'},
            color_discrete_sequence=["#2ca02c"]
        )
        
        st.plotly_chart(fig_payment, use_container_width=True)
        
        # 按客户汇总
        customer_payment_df = filtered_payment_df[filtered_payment_df['打款单位'] != ''].groupby('打款单位').agg({
            '金额': 'sum'
        }).reset_index().sort_values(by='金额', ascending=False)
        
        st.subheader("按客户付款汇总")
        
        # 显示数据表格
        st.dataframe(
            customer_payment_df.rename(columns={
                '打款单位': '客户',
                '金额': '付款金额(元)'
            }).style.format({
                '付款金额(元)': '{:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("未找到有效的付款数据，请检查数据文件。")

# Tab 3: 客户余额
with tab3:
    st.subheader("客户余额分析")
    
    # 设置显示客户数量
    num_customers = st.slider("显示客户数量", min_value=5, max_value=min(50, len(filtered_balance_df)), value=20)
    
    # 余额最高的客户
    top_balance_df = filtered_balance_df.head(num_customers)
    
    # 创建条形图
    fig_balance = px.bar(
        top_balance_df,
        x='客户名称',
        y='余额',
        title=f"Top {num_customers} 客户余额",
        color='余额',
        color_continuous_scale=["red", "white", "green"],
        labels={'余额': '余额(元)', '客户名称': '客户'}
    )
    
    st.plotly_chart(fig_balance, use_container_width=True)
    
    # 创建详细的客户余额表格，包括销售金额和付款金额
    st.subheader("客户余额详情")
    
    # 格式化余额，负数显示为红色
    def color_negative_red(val):
        color = 'red' if val < 0 else 'green'
        return f'color: {color}'
    
    # 显示数据表格
    st.dataframe(
        filtered_balance_df.style.format({
            '销售总额': '{:.2f}',
            '付款总额': '{:.2f}',
            '余额': '{:.2f}'
        }).map(color_negative_red, subset=['余额']),
        use_container_width=True,
        hide_index=True
    )
    
    # 欠款和预付统计
    col1, col2, col3 = st.columns(3)
    
    with col1:
        owe_customers = filtered_balance_df[filtered_balance_df['余额'] > 0]
        st.metric("欠款客户数", f"{len(owe_customers)}")
        
    with col2:
        total_owed = owe_customers['余额'].sum()
        st.metric("欠款总额", f"{total_owed:,.2f}")
        
    with col3:
        prepaid_customers = filtered_balance_df[filtered_balance_df['余额'] < 0]
        prepaid_amount = abs(prepaid_customers['余额'].sum())
        st.metric("预付总额", f"{prepaid_amount:,.2f}")

# Tab 4: 按货物汇总 
with tab4:
    st.subheader("按货物名称汇总")
    
    # 按货物名称汇总 - 跳过空货物名
    product_df = filtered_sales_df[filtered_sales_df['货物名称'] != ''].groupby('货物名称').agg({
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

# Tab 5: 高级分析
with tab5:
    st.subheader("高级分析")
    
    # 月度销售和付款比较
    if st.checkbox("显示月度销售和付款对比"):
        # 销售月度数据
        filtered_sales_df['月份'] = filtered_sales_df['日 期'].dt.to_period('M')
        monthly_sales_df = filtered_sales_df.groupby('月份')['合计金额/元'].sum().reset_index()
        monthly_sales_df['月份'] = monthly_sales_df['月份'].astype(str)
        monthly_sales_df.columns = ['月份', '销售金额']
        
        # 付款月度数据
        if not filtered_payment_df.empty and '日期' in filtered_payment_df.columns:
            filtered_payment_df['月份'] = filtered_payment_df['日期'].dt.to_period('M')
            monthly_payment_df = filtered_payment_df.groupby('月份')['金额'].sum().reset_index()
            monthly_payment_df['月份'] = monthly_payment_df['月份'].astype(str)
            monthly_payment_df.columns = ['月份', '付款金额']
            
            # 合并销售和付款数据
            monthly_df = pd.merge(monthly_sales_df, monthly_payment_df, on='月份', how='outer').fillna(0)
        else:
            # 没有付款数据，只显示销售数据
            monthly_df = monthly_sales_df.copy()
            monthly_df['付款金额'] = 0
        
        # 计算每月余额
        monthly_df['月度余额'] = monthly_df['销售金额'] - monthly_df['付款金额']
        
        # 创建月度对比图
        fig_monthly = px.bar(
            monthly_df,
            x='月份',
            y=['销售金额', '付款金额'],
            barmode='group',
            title="月度销售与付款对比",
            labels={'value': '金额(元)', '月份': '月份', 'variable': '类型'},
            color_discrete_sequence=["#2ca02c", "#1f77b4"]
        )
        
        # 添加月度余额线
        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_df['月份'],
                y=monthly_df['月度余额'],
                mode='lines+markers',
                name='月度余额',
                line=dict(color='red', width=2)
            )
        )
        
        st.plotly_chart(fig_monthly, use_container_width=True)
        
        # 显示月度数据表格
        st.dataframe(
            monthly_df.style.format({
                '销售金额': '{:.2f}',
                '付款金额': '{:.2f}',
                '月度余额': '{:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    
    # 客户交易趋势分析
    if st.checkbox("显示客户交易趋势"):
        # 选择客户
        trend_customer = st.selectbox(
            "选择客户",
            options=all_customers,
            index=0 if all_customers else None
        )
        
        if trend_customer:
            # 销售趋势 - 按月统计
            customer_sales = filtered_sales_df[filtered_sales_df['购货单位'] == trend_customer]
            customer_sales['月份'] = customer_sales['日 期'].dt.to_period('M')
            customer_sales_monthly = customer_sales.groupby('月份').agg({
                '合计金额/元': 'sum'
            }).reset_index()
            customer_sales_monthly['月份'] = customer_sales_monthly['月份'].astype(str)
            customer_sales_monthly.columns = ['月份', '销售金额']
            
            # 付款趋势 - 按月统计
            if not filtered_payment_df.empty and '日期' in filtered_payment_df.columns:
                customer_payment = filtered_payment_df[filtered_payment_df['打款单位'] == trend_customer]
                customer_payment['月份'] = customer_payment['日期'].dt.to_period('M')
                customer_payment_monthly = customer_payment.groupby('月份').agg({
                    '金额': 'sum'
                }).reset_index()
                customer_payment_monthly['月份'] = customer_payment_monthly['月份'].astype(str)
                customer_payment_monthly.columns = ['月份', '付款金额']
                
                # 创建交易趋势图
                fig_trend = go.Figure()
                
                # 添加销售数据
                fig_trend.add_trace(
                    go.Bar(
                        x=customer_sales_monthly['月份'],
                        y=customer_sales_monthly['销售金额'],
                        name='销售金额',
                        marker_color='#2ca02c'
                    )
                )
                
                # 添加付款数据
                fig_trend.add_trace(
                    go.Bar(
                        x=customer_payment_monthly['月份'],
                        y=customer_payment_monthly['付款金额'],
                        name='付款金额',
                        marker_color='#1f77b4'
                    )
                )
                
                fig_trend.update_layout(
                    title=f"{trend_customer} 月度交易趋势",
                    xaxis_title="月份",
                    yaxis_title="金额(元)",
                    barmode='group',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.warning("未找到有效的付款数据，仅显示销售趋势。")
                
                # 创建销售趋势图
                fig_sales_trend = px.bar(
                    customer_sales_monthly,
                    x='月份',
                    y='销售金额',
                    title=f"{trend_customer} 月度销售趋势",
                    labels={'销售金额': '金额(元)', '月份': '月份'}
                )
                
                st.plotly_chart(fig_sales_trend, use_container_width=True)
    
    # 原始数据查看
    if st.checkbox("查看原始数据"):
        data_type = st.radio("选择数据", ["销售数据", "付款数据"])
        
        if data_type == "销售数据":
            st.subheader("原始销售记录")
            
            # 分页选项
            page_size = st.selectbox("每页显示行数", [10, 20, 50, 100])
            total_pages = len(filtered_sales_df) // page_size + (1 if len(filtered_sales_df) % page_size > 0 else 0)
            
            if total_pages > 0:
                page_num = st.slider("页码", 1, total_pages, 1)
                start_idx = (page_num - 1) * page_size
                end_idx = min(start_idx + page_size, len(filtered_sales_df))
                
                st.dataframe(
                    filtered_sales_df.iloc[start_idx:end_idx].style.format({
                        '计量/吨': '{:.2f}',
                        '单价/元': '{:.2f}',
                        '合计金额/元': '{:.2f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                
                st.write(f"显示 {start_idx+1} 到 {end_idx}，共 {len(filtered_sales_df)} 条记录")
            else:
                st.write("没有符合条件的数据")
        
        else:  # 付款数据
            st.subheader("原始付款记录")
            
            if not filtered_payment_df.empty:
                # 分页选项
                page_size = st.selectbox("每页显示行数", [10, 20, 50, 100])
                total_pages = len(filtered_payment_df) // page_size + (1 if len(filtered_payment_df) % page_size > 0 else 0)
                
                if total_pages > 0:
                    page_num = st.slider("页码", 1, total_pages, 1)
                    start_idx = (page_num - 1) * page_size
                    end_idx = min(start_idx + page_size, len(filtered_payment_df))
                    
                    st.dataframe(
                        filtered_payment_df.iloc[start_idx:end_idx].style.format({
                            '金额': '{:.2f}'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.write(f"显示 {start_idx+1} 到 {end_idx}，共 {len(filtered_payment_df)} 条记录")
                else:
                    st.write("没有符合条件的数据")
            else:
                st.warning("未找到有效的付款数据。") 

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from db import get_connection

@st.cache_data(ttl=300)
def fetch_analytics_data(owner_id: int):
    """
    Fetch raw data safely using read-only SQL queries. 
    Does not update any database records.
    Cached for 5 minutes (300 seconds) to ensure high performance.
    """
    conn = get_connection()
    try:
        # Fetch Orders
        orders_rows = conn.execute(
            "SELECT id, customer_id, order_date, status, total_amount, payment_status FROM orders WHERE owner_id=?", 
            (owner_id,)
        ).fetchall()
        orders_df = pd.DataFrame([dict(r) for r in orders_rows])
        
        # Fetch Order Items
        order_items_rows = conn.execute(
            """SELECT oi.order_id, oi.item_id, oi.quantity, oi.price_at_order, o.order_date
               FROM order_items oi
               JOIN orders o ON oi.order_id = o.id
               WHERE o.owner_id=?""",
            (owner_id,)
        ).fetchall()
        order_items_df = pd.DataFrame([dict(r) for r in order_items_rows])
        
        # Fetch Inventory
        inventory_rows = conn.execute(
            "SELECT id, name, category, quantity, unit, price, cost, min_stock_level FROM inventory WHERE owner_id=?",
            (owner_id,)
        ).fetchall()
        inventory_df = pd.DataFrame([dict(r) for r in inventory_rows])
        
        # Fetch Customers
        customers_rows = conn.execute(
            "SELECT id, business_name, current_balance, credit_limit FROM customers WHERE owner_id=?",
            (owner_id,)
        ).fetchall()
        customers_df = pd.DataFrame([dict(r) for r in customers_rows])
        
        # Fetch Payment History (payment_history lacks owner_id, so we join with orders)
        payments_rows = conn.execute(
            """SELECT p.id, p.amount, p.collected_at 
               FROM payment_history p
               JOIN orders o ON p.order_id = o.id
               WHERE o.owner_id=?""",
            (owner_id,)
        ).fetchall()
        payments_df = pd.DataFrame([dict(r) for r in payments_rows])
        
        # Fetch Deliveries
        deliveries_rows = conn.execute(
            """SELECT d.id, d.delivery_status 
               FROM deliveries d
               JOIN orders o ON d.order_id = o.id
               WHERE o.owner_id=?""",
            (owner_id,)
        ).fetchall()
        deliveries_df = pd.DataFrame([dict(r) for r in deliveries_rows])
        
        return {
            "orders": orders_df,
            "order_items": order_items_df,
            "inventory": inventory_df,
            "customers": customers_df,
            "payments": payments_df,
            "deliveries": deliveries_df
        }
    finally:
        conn.close()


def render():
    st.markdown("## 📊 Business Analytics")
    
    owner_id = st.session_state.get("owner_id")
    if not owner_id:
        st.error("Authentication error.")
        return
        
    # Fetch Data
    with st.spinner("Crunching business data..."):
        data = fetch_analytics_data(owner_id)
        
    orders_df = data["orders"]
    order_items_df = data["order_items"]
    inventory_df = data["inventory"]
    customers_df = data["customers"]
    payments_df = data["payments"]
    deliveries_df = data["deliveries"]
    
    # Check if we have enough data
    if orders_df.empty and inventory_df.empty and customers_df.empty:
        st.info("Not enough data to generate analytics yet. Start adding inventory and processing orders!")
        return
        
    # Ensure columns exist even if empty (pandas might not infer them from empty dicts)
    if 'total_amount' not in orders_df.columns:
        orders_df['total_amount'] = 0.0
    if 'current_balance' not in customers_df.columns:
        customers_df['current_balance'] = 0.0
    if 'quantity' not in inventory_df.columns:
        inventory_df['quantity'] = 0
    if 'price' not in inventory_df.columns:
        inventory_df['price'] = 0.0
    if 'amount' not in payments_df.columns:
        payments_df['amount'] = 0.0
        
    # Ensure Datetime format
    if not orders_df.empty:
        orders_df['order_date'] = pd.to_datetime(orders_df['order_date'])
        orders_df = orders_df.sort_values('order_date')
    if not payments_df.empty:
        payments_df['collected_at'] = pd.to_datetime(payments_df['collected_at'])
        
    # Calculate Dates
    now = pd.Timestamp.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - pd.Timedelta(days=today_start.dayofweek)
    month_start = today_start.replace(day=1)
    
    # Calculate KPIs
    today_sales = 0
    weekly_sales = 0
    monthly_sales = 0
    orders_today = 0
    avg_order_value = 0
    
    if not orders_df.empty:
        today_orders = orders_df[orders_df['order_date'] >= today_start]
        weekly_orders = orders_df[orders_df['order_date'] >= week_start]
        monthly_orders = orders_df[orders_df['order_date'] >= month_start]
        
        today_sales = today_orders['total_amount'].sum()
        weekly_sales = weekly_orders['total_amount'].sum()
        monthly_sales = monthly_orders['total_amount'].sum()
        orders_today = len(today_orders)
        avg_order_value = orders_df['total_amount'].mean()
        
    pending_payments = customers_df['current_balance'].sum() if not customers_df.empty else 0
    inventory_value = (inventory_df['quantity'] * inventory_df['price']).sum() if not inventory_df.empty else 0
    active_customers = len(customers_df) if not customers_df.empty else 0
    
    total_paid = payments_df['amount'].sum() if not payments_df.empty else 0
    collection_rate = (total_paid / (total_paid + pending_payments) * 100) if (total_paid + pending_payments) > 0 else 0
    
    # Render KPIs
    st.markdown("### 📈 Business Overview")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Today's Sales", f"₹{today_sales:,.2f}")
    k2.metric("Weekly Sales", f"₹{weekly_sales:,.2f}")
    k3.metric("Monthly Sales", f"₹{monthly_sales:,.2f}")
    k4.metric("Orders Today", f"{orders_today}")
    
    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Pending Payments", f"₹{pending_payments:,.2f}")
    k6.metric("Collection Rate", f"{collection_rate:.1f}%")
    k7.metric("Inventory Value", f"₹{inventory_value:,.2f}")
    k8.metric("Active Customers", f"{active_customers}")
    
    st.divider()
    
    # Charts Section 1: Sales & Customers
    col1, col2 = st.columns([6, 4])
    
    with col1:
        st.markdown("### 📊 Revenue Trend")
        if not orders_df.empty:
            daily_sales = orders_df.groupby(orders_df['order_date'].dt.date)['total_amount'].sum().reset_index()
            daily_sales.columns = ['Date', 'Revenue']
            fig_sales = px.area(daily_sales, x='Date', y='Revenue', 
                                color_discrete_sequence=['#4f8ef7'])
            fig_sales.update_layout(margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_sales, use_container_width=True)
        else:
            st.info("No sales data available for trend chart.")
            
    with col2:
        st.markdown("### 👥 Top Customers (Revenue)")
        if not orders_df.empty and not customers_df.empty:
            cust_sales = orders_df.groupby('customer_id')['total_amount'].sum().reset_index()
            cust_sales = pd.merge(cust_sales, customers_df, left_on='customer_id', right_on='id')
            cust_sales = cust_sales.sort_values('total_amount', ascending=False).head(5)
            
            fig_cust = px.bar(cust_sales, x='total_amount', y='business_name', orientation='h',
                              color_discrete_sequence=['#22c55e'])
            fig_cust.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_cust, use_container_width=True)
        else:
            st.info("No customer sales data available.")
            
    st.divider()
    
    # Charts Section 2: Inventory
    st.markdown("### 📦 Inventory Insights")
    i1, i2 = st.columns(2)
    with i1:
        st.markdown("#### Fast Moving Products")
        if not order_items_df.empty and not inventory_df.empty:
            item_sales = order_items_df.groupby('item_id')['quantity'].sum().reset_index()
            item_sales = pd.merge(item_sales, inventory_df, left_on='item_id', right_on='id')
            item_sales = item_sales.sort_values('quantity_x', ascending=False).head(5)
            
            fig_fast = px.bar(item_sales, x='name', y='quantity_x', 
                              color_discrete_sequence=['#f59e0b'])
            fig_fast.update_layout(xaxis_title="Product", yaxis_title="Quantity Sold", margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_fast, use_container_width=True)
        else:
            st.info("No product sales data available.")
            
    with i2:
        st.markdown("#### Low Stock Warning")
        if not inventory_df.empty:
            low_stock = inventory_df[inventory_df['quantity'] < inventory_df['min_stock_level']].copy()
            if not low_stock.empty:
                low_stock = low_stock.sort_values('quantity')
                fig_low = px.bar(low_stock.head(5), x='name', y='quantity',
                                 color_discrete_sequence=['#ef4444'])
                fig_low.update_layout(xaxis_title="Product", yaxis_title="Current Stock", margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_low, use_container_width=True)
            else:
                st.success("All products are above minimum stock levels!")
        else:
            st.info("No inventory data available.")
            
    st.divider()
    
    # Charts Section 3: Payments and Deliveries
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("### 💳 Payment Status Distribution")
        if not orders_df.empty:
            pay_dist = orders_df['payment_status'].value_counts().reset_index()
            pay_dist.columns = ['Status', 'Count']
            fig_pay = px.pie(pay_dist, values='Count', names='Status', hole=0.4,
                             color='Status', color_discrete_map={'Paid': '#22c55e', 'Partial': '#f59e0b', 'Unpaid': '#ef4444'})
            fig_pay.update_layout(margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pay, use_container_width=True)
        else:
            st.info("No payment data available.")
            
    with p2:
        st.markdown("### 🚚 Delivery Status Distribution")
        if not deliveries_df.empty:
            del_dist = deliveries_df['delivery_status'].value_counts().reset_index()
            del_dist.columns = ['Status', 'Count']
            fig_del = px.pie(del_dist, values='Count', names='Status', hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_del.update_layout(margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_del, use_container_width=True)
        else:
            st.info("No delivery data available.")
            
    st.divider()
    
    # AI Business Insights (Rule-based SQL + Python analysis)
    st.markdown("### 💡 AI Business Insights")
    
    insights = []
    
    # 1. Sales Insights
    if not orders_df.empty and len(orders_df) > 0:
        best_day_idx = orders_df.groupby(orders_df['order_date'].dt.date)['total_amount'].sum().idxmax()
        best_day_sales = orders_df.groupby(orders_df['order_date'].dt.date)['total_amount'].sum().max()
        if best_day_sales > 0:
            insights.append(f"🌟 **Highest Revenue Day:** Your best day was {best_day_idx.strftime('%b %d, %Y')} with sales of ₹{best_day_sales:,.2f}.")
        
        last_week_start = week_start - pd.Timedelta(days=7)
        last_week_sales = orders_df[(orders_df['order_date'] >= last_week_start) & (orders_df['order_date'] < week_start)]['total_amount'].sum()
        if last_week_sales > 0:
            growth = ((weekly_sales - last_week_sales) / last_week_sales) * 100
            direction = "increased" if growth >= 0 else "decreased"
            insights.append(f"📈 **Sales Trend:** Weekly sales have {direction} by {abs(growth):.1f}% compared to last week.")
            
        insights.append(f"💰 **Average Order Value:** Your average order value across all time is ₹{avg_order_value:,.2f}.")
            
    # 2. Customer Insights
    if not customers_df.empty:
        highest_dues = customers_df.sort_values('current_balance', ascending=False).iloc[0]
        if highest_dues['current_balance'] > 0:
            insights.append(f"⚠️ **Pending Dues:** {highest_dues['business_name']} has the highest outstanding balance of ₹{highest_dues['current_balance']:,.2f}.")
            
    # 3. Inventory Insights
    if not order_items_df.empty and not inventory_df.empty:
        item_sales = order_items_df.groupby('item_id')['quantity'].sum().reset_index()
        item_sales = pd.merge(item_sales, inventory_df, left_on='item_id', right_on='id')
        if not item_sales.empty:
            top_item = item_sales.sort_values('quantity_x', ascending=False).iloc[0]
            insights.append(f"🔥 **Hot Product:** {top_item['name']} is your most popular product with {top_item['quantity_x']} {top_item['unit']} sold.")
            
    if not inventory_df.empty:
        zero_stock = inventory_df[inventory_df['quantity'] <= 0]
        if not zero_stock.empty:
            insights.append(f"🚨 **Stock Out:** You have {len(zero_stock)} product(s) completely out of stock.")
            
    # Render Insights
    if insights:
        for insight in insights:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03);border:1px solid #1e293b;
                        border-radius:8px;padding:1rem;margin-bottom:0.75rem;">
                {insight}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Gathering more data to generate business insights...")

"""
views/dashboard.py — Owner Dashboard (Multi-Tenant Edition)
=============================================================
Displays owner-scoped metrics only:
  1. Low-stock warning banner (owner's inventory only)
  2. KPI metric cards (owner's all-time totals)
  3. TODAY'S ACTIVITY — collections by owner's workers
  4. Recent orders table (owner's orders)
  5. Low-stock items table (owner's inventory)

Access: owner only.
"""

import streamlit as st
import pandas as pd
from db import (
    get_dashboard_stats,
    get_all_orders,
    get_all_inventory,
    get_today_collections,
    get_outstanding_balances,
)
from styles import kpi_card, low_stock_banner


def render():
    owner_id = st.session_state.get("owner_id")

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="app-header">
        <span style="font-size:1.8rem">🏪</span>
        <div>
            <h1>Dashboard</h1>
            <p>Wholesale Operations Overview</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load data (owner-scoped) ──────────────────────────────────────────────
    stats = get_dashboard_stats(owner_id)
    today = get_today_collections(owner_id)

    # ── Low-stock warning ─────────────────────────────────────────────────────
    if stats["low_stock_count"] > 0:
        st.markdown(low_stock_banner(stats["low_stock_count"]), unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # KPI GRID  (all-time, owner-scoped)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    cards_html = (
        kpi_card("👥", "Customers",        str(stats["total_customers"]),
                 "Registered retailers",  "blue") +
        kpi_card("📦", "Stock Items",      str(stats["total_items"]),
                 f"{stats['low_stock_count']} low stock", "purple") +
        kpi_card("🛒", "Total Orders",     str(stats["total_orders"]),
                 f"{stats['pending_orders']} pending",   "blue") +
        kpi_card("💰", "Revenue Collected",
                 f"₹{stats['total_revenue']:,.0f}", "from paid orders", "green") +
        kpi_card("📊", "Stock Value",
                 f"₹{stats['stock_value']:,.0f}", "at selling price", "purple") +
        kpi_card("🚚", "Active Deliveries",
                 str(stats["pending_deliveries"]), "in transit / scheduled", "yellow") +
        kpi_card("👷", "Active Workers",   str(stats["total_workers"]), "", "green") +
        kpi_card("💳", "Outstanding",
                 f"₹{stats['unpaid_balance']:,.0f}", "customer balances", "red")
    )
    st.markdown(cards_html + "</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TODAY'S ACTIVITY
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="section-title">📅 Today\'s Activity</div>',
        unsafe_allow_html=True
    )

    tk1, tk2, tk3, tk4 = st.columns(4)

    with tk1:
        st.markdown(f"""
        <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;
                    padding:0.85rem 1rem;text-align:center;border-top:3px solid #22c55e;">
            <div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;
                        letter-spacing:.06em;margin-bottom:.3rem;">Collected Today</div>
            <div style="font-size:1.4rem;font-weight:800;color:#22c55e;">
                ₹{today['total']:,.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tk2:
        st.markdown(f"""
        <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;
                    padding:0.85rem 1rem;text-align:center;border-top:3px solid #4f8ef7;">
            <div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;
                        letter-spacing:.06em;margin-bottom:.3rem;">Delivered Today</div>
            <div style="font-size:1.4rem;font-weight:800;color:#4f8ef7;">
                {today['delivered']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tk3:
        st.markdown(f"""
        <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;
                    padding:0.85rem 1rem;text-align:center;border-top:3px solid #ef4444;">
            <div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;
                        letter-spacing:.06em;margin-bottom:.3rem;">Failed Today</div>
            <div style="font-size:1.4rem;font-weight:800;color:#ef4444;">
                {today['failed']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tk4:
        pending = stats["unpaid_balance"]
        st.markdown(f"""
        <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;
                    padding:0.85rem 1rem;text-align:center;border-top:3px solid #f59e0b;">
            <div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;
                        letter-spacing:.06em;margin-bottom:.3rem;">Total Pending Dues</div>
            <div style="font-size:1.4rem;font-weight:800;color:#f59e0b;">
                ₹{pending:,.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

    # ── Worker-wise collections today ─────────────────────────────────────────
    if today["workers"]:
        with st.expander("👷 Worker-wise Collections Today", expanded=True):
            rows = []
            for w in today["workers"]:
                rows.append({
                    "Worker":      w.get("worker_name") or "Unknown",
                    "Deliveries":  int(w.get("deliveries", 0)),
                    "Collected":   f"₹{float(w.get('collected', 0)):,.0f}",
                })
            df_w = pd.DataFrame(rows)
            st.dataframe(df_w, width='stretch', hide_index=True)
    else:
        st.markdown("""
        <div style="font-size:0.82rem;color:#475569;padding:0.5rem 0;">
            No worker collections recorded yet today.
        </div>
        """, unsafe_allow_html=True)

    # ── Outstanding customer balances ─────────────────────────────────────────
    balances = get_outstanding_balances(owner_id)
    if balances:
        with st.expander(f"💳 Outstanding Balances ({len(balances)} customers)", expanded=False):
            rows_b = []
            for b in balances:
                rows_b.append({
                    "Customer":    b["business_name"],
                    "Phone":       b.get("phone") or "—",
                    "Outstanding": f"₹{float(b['current_balance']):,.0f}",
                })
            df_b = pd.DataFrame(rows_b)
            st.dataframe(df_b, width='stretch', hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # RECENT ORDERS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-title">📋 Recent Orders</div>', unsafe_allow_html=True)
    orders = get_all_orders(owner_id)
    if orders:
        df = pd.DataFrame(orders[:8])
        df["order_date"]   = pd.to_datetime(df["order_date"]).dt.strftime("%d %b %Y")
        df["total_amount"] = df["total_amount"].apply(lambda x: f"₹{x:,.0f}")
        df.columns = ["ID", "Customer", "Date", "Status", "Amount", "Payment"]
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("No orders yet.")

    # ══════════════════════════════════════════════════════════════════════════
    # LOW-STOCK ITEMS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-title">⚠️ Low Stock Items</div>', unsafe_allow_html=True)
    items = get_all_inventory(owner_id)
    low   = [i for i in items if i["low_stock"]]
    if low:
        df_low = pd.DataFrame(low)[["sku", "name", "category", "quantity",
                                     "min_stock_level", "unit"]]
        df_low.columns = ["SKU", "Item", "Category", "Qty", "Min Level", "Unit"]
        st.dataframe(df_low, width='stretch', hide_index=True)
    else:
        st.success("✅ All items are adequately stocked.")

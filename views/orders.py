"""
views/orders.py — Full Order Management (Multi-Tenant Edition)
===============================================================
Cart-based order creation workflow, scoped to the authenticated owner.
Owners only see their own customers, inventory, and orders.

Owner:  'New Order' tab + 'Order History' tab
Worker: 'Order History' view only (scoped to their owner's orders)
"""

import streamlit as st
import pandas as pd
from db import (
    get_customers_for_dropdown, get_inventory_in_stock, get_current_stock,
    create_full_order, get_all_orders, get_order_items_detail
)


def render():
    role     = st.session_state.get("role", "worker")
    owner_id = st.session_state.get("owner_id")

    st.markdown("""
    <div class="app-header">
        <span style="font-size:1.8rem">🛒</span>
        <div>
            <h1>Orders</h1>
            <p>Create and manage wholesale orders</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if role == "owner":
        tab_new, tab_hist = st.tabs(["📝 New Order", "📋 Order History"])
        with tab_new:
            _render_order_creation(owner_id)
        with tab_hist:
            _render_order_history(owner_id)
    else:
        _render_order_history(owner_id)


# ─────────────────────────────────────────────────────────────────────────────
# ORDER CREATION
# ─────────────────────────────────────────────────────────────────────────────
def _render_order_creation(owner_id: int):
    if "order_cart" not in st.session_state:
        st.session_state["order_cart"] = []

    cart = st.session_state["order_cart"]

    # ── Step 1: Select Customer ───────────────────────────────────────────────
    st.markdown(
        '<div class="section-title">👤 Step 1 — Select Retailer</div>',
        unsafe_allow_html=True
    )

    customers = get_customers_for_dropdown(owner_id)
    if not customers:
        st.warning("No customers found. Please add customers first.")
        return

    cust_map = {f"{c['business_name']}  ·  {c['phone']}": c for c in customers}
    sel_key  = st.selectbox(
        "Retailer", list(cust_map.keys()),
        key="order_cust_sel", label_visibility="collapsed"
    )
    cust = cust_map[sel_key]

    avail_credit = max(0.0, cust["credit_limit"] - cust["current_balance"])
    credit_pct   = (cust["current_balance"] / cust["credit_limit"] * 100) if cust["credit_limit"] > 0 else 0
    warn_color   = "#ef4444" if credit_pct >= 90 else ("#f59e0b" if credit_pct >= 60 else "#22c55e")

    st.markdown(f"""
    <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:10px;
                padding:0.65rem 1rem;margin-bottom:0.75rem;font-size:0.8rem;">
        <span style="color:#94a3b8;">📍 {cust['address'] or '—'}</span>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="color:#94a3b8;">👤 {cust['contact_person'] or '—'}</span>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        Balance: <span style="color:{warn_color};font-weight:600;">₹{cust['current_balance']:,.0f}</span>
        / Limit: ₹{cust['credit_limit']:,.0f}
        &nbsp;
        <span style="color:{warn_color};">({credit_pct:.0f}% used)</span>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        Available Credit: <span style="color:#22c55e;font-weight:600;">₹{avail_credit:,.0f}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Step 2: Add Items to Cart ─────────────────────────────────────────────
    st.markdown(
        '<div class="section-title">📦 Step 2 — Add Items</div>',
        unsafe_allow_html=True
    )

    inventory = get_inventory_in_stock(owner_id)
    if not inventory:
        st.warning("No items currently in stock.")
    else:
        inv_map = {
            f"{i['name']}  ({i['quantity']} {i['unit']} avail)  ·  ₹{i['price']:.2f}": i
            for i in inventory
        }
        ic1, ic2, ic3 = st.columns([4, 1.5, 1.2])
        with ic1:
            item_key = st.selectbox(
                "Item", list(inv_map.keys()),
                key="cart_item_sel", label_visibility="collapsed"
            )
        sel_item = inv_map[item_key]
        with ic2:
            qty = st.number_input(
                "Qty", min_value=1, max_value=int(sel_item["quantity"]),
                value=1, key="cart_qty_input", label_visibility="collapsed"
            )
        with ic3:
            if st.button("➕ Add to Cart", width='stretch', key="btn_add_cart"):
                _add_to_cart(sel_item, qty, owner_id)

    # ── Step 3: Cart ──────────────────────────────────────────────────────────
    st.markdown(
        '<div class="section-title">🧾 Step 3 — Review Cart</div>',
        unsafe_allow_html=True
    )

    if not cart:
        st.markdown("""
        <div style="background:#1a1d27;border:1px dashed #2e3347;border-radius:10px;
                    padding:1.5rem;text-align:center;color:#94a3b8;font-size:0.85rem;">
            🛒 Cart is empty. Select items above and click "Add to Cart".
        </div>
        """, unsafe_allow_html=True)
        return

    total = sum(i["quantity"] * i["price"] for i in cart)

    for idx, item in enumerate(cart):
        line_total = item["quantity"] * item["price"]
        cc1, cc2, cc3 = st.columns([3, 2, 0.7])
        with cc1:
            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:8px;
                        padding:0.5rem 0.75rem;font-size:0.83rem;">
                <strong style="color:#e2e8f0;">{item['name']}</strong>
                <span style="color:#94a3b8;"> ({item['sku']})</span>
            </div>
            """, unsafe_allow_html=True)
        with cc2:
            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:8px;
                        padding:0.5rem 0.75rem;font-size:0.82rem;color:#94a3b8;">
                {item['quantity']} {item['unit']} × ₹{item['price']:.2f}
                = <strong style="color:#4f8ef7;">₹{line_total:,.2f}</strong>
            </div>
            """, unsafe_allow_html=True)
        with cc3:
            if st.button("✕", key=f"rm_{idx}_{item['item_id']}", width='stretch'):
                st.session_state["order_cart"].pop(idx)
                st.rerun()

    # Total banner
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(79,142,247,0.12),rgba(124,92,191,0.12));
                border:1px solid rgba(79,142,247,0.3);border-radius:10px;
                padding:0.75rem 1.25rem;margin:0.75rem 0;
                display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:0.85rem;color:#94a3b8;">
            {len(cart)} item{'s' if len(cart) != 1 else ''} in cart
        </span>
        <span style="font-size:1.5rem;font-weight:700;color:#4f8ef7;">₹{total:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Step 4: Payment & Confirm ─────────────────────────────────────────────
    st.markdown(
        '<div class="section-title">💳 Step 4 — Payment & Confirm</div>',
        unsafe_allow_html=True
    )

    p1, p2 = st.columns(2)
    with p1:
        amount_received = st.number_input(
            "Upfront Payment Received (₹)",
            min_value=0.0, max_value=float(total),
            value=0.0, step=50.0, format="%.2f",
            help="Enter 0 for full credit. Enter the full amount for cash payment."
        )
    with p2:
        outstanding = total - amount_received
        if amount_received >= total:
            pay_label, pay_color = "✅ Fully Paid",     "#22c55e"
        elif amount_received > 0:
            pay_label, pay_color = "⚡ Partial Payment", "#f59e0b"
        else:
            pay_label, pay_color = "📋 Full Credit",     "#ef4444"

        st.markdown(f"""
        <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:10px;
                    padding:0.75rem;margin-top:0.1rem;text-align:center;">
            <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;
                        letter-spacing:0.04em;">Payment Status</div>
            <div style="font-size:1rem;font-weight:700;color:{pay_color};margin:0.25rem 0;">
                {pay_label}
            </div>
            <div style="font-size:0.8rem;color:#94a3b8;">
                Outstanding: <strong style="color:#e2e8f0;">₹{outstanding:,.2f}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("✅ Confirm & Place Order", width='stretch', key="btn_confirm_order"):
            ok, result = create_full_order(owner_id, cust["id"], cart, amount_received)
            if ok:
                order_id = result
                st.session_state["order_cart"]    = []
                st.session_state["last_order_id"] = order_id
                st.success(f"✅ Order #{order_id} placed! Delivery record created.")
                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ {result}")
    with btn2:
        if st.button("🗑️ Clear Cart", width='stretch', key="btn_clear_cart"):
            st.session_state["order_cart"] = []
            st.rerun()

    # ── Last order receipt ────────────────────────────────────────────────────
    if "last_order_id" in st.session_state:
        oid   = st.session_state["last_order_id"]
        items = get_order_items_detail(owner_id, oid)
        if items:
            st.markdown(
                f'<div class="section-title">📄 Receipt — Order #{oid}</div>',
                unsafe_allow_html=True
            )
            df = pd.DataFrame(items)[["name", "sku", "quantity", "unit", "price_at_order", "line_total"]]
            df.columns = ["Item", "SKU", "Qty", "Unit", "Unit Price (₹)", "Total (₹)"]
            st.dataframe(df, width='stretch', hide_index=True)
            if st.button("✕ Dismiss Receipt", key="btn_dismiss_receipt"):
                del st.session_state["last_order_id"]
                st.rerun()


def _add_to_cart(sel_item: dict, qty: int, owner_id: int):
    """Add or update item in cart with live stock validation."""
    cart     = st.session_state["order_cart"]
    existing = next((i for i in cart if i["item_id"] == sel_item["id"]), None)

    if existing:
        new_qty   = existing["quantity"] + qty
        available = get_current_stock(owner_id, sel_item["id"])
        if new_qty > available:
            st.error(f"Only {available} {sel_item['unit']} available for '{sel_item['name']}'.")
        else:
            existing["quantity"] = new_qty
            st.success(f"Updated: {sel_item['name']} → {new_qty} {sel_item['unit']}")
            st.rerun()
    else:
        cart.append({
            "item_id":  sel_item["id"],
            "name":     sel_item["name"],
            "sku":      sel_item["sku"],
            "unit":     sel_item["unit"],
            "quantity": qty,
            "price":    sel_item["price"],
        })
        st.success(f"Added: {sel_item['name']} × {qty} {sel_item['unit']}")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ORDER HISTORY
# ─────────────────────────────────────────────────────────────────────────────
def _render_order_history(owner_id: int):
    st.markdown('<div class="section-title">📋 Order History</div>', unsafe_allow_html=True)

    orders = get_all_orders(owner_id)
    if not orders:
        st.info("No orders yet.")
        return

    pending    = sum(1 for o in orders if o["status"] == "Pending")
    processing = sum(1 for o in orders if o["status"] == "Processing")
    delivered  = sum(1 for o in orders if o["status"] == "Delivered")
    total_val  = sum(o["total_amount"] for o in orders)

    st.markdown(f"""
    <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:1rem;">
        <span style="background:#22263a;border:1px solid #2e3347;border-radius:20px;
                     padding:0.25rem 0.75rem;font-size:0.75rem;color:#94a3b8;">
            🛒 {len(orders)} orders · ₹{total_val:,.0f} total
        </span>
        <span style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);
                     border-radius:20px;padding:0.25rem 0.75rem;font-size:0.75rem;color:#f59e0b;">
            ⏳ {pending} pending
        </span>
        <span style="background:rgba(79,142,247,0.12);border:1px solid rgba(79,142,247,0.3);
                     border-radius:20px;padding:0.25rem 0.75rem;font-size:0.75rem;color:#4f8ef7;">
            ⚙️ {processing} processing
        </span>
        <span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);
                     border-radius:20px;padding:0.25rem 0.75rem;font-size:0.75rem;color:#22c55e;">
            ✅ {delivered} delivered
        </span>
    </div>
    """, unsafe_allow_html=True)

    for order in orders:
        sc = {"Delivered":"#22c55e","Processing":"#4f8ef7","Pending":"#f59e0b","Cancelled":"#94a3b8"}
        pc = {"Paid":"#22c55e","Unpaid":"#ef4444","Partial":"#f59e0b"}
        status_color = sc.get(order["status"],  "#94a3b8")
        pay_color    = pc.get(order["payment_status"], "#94a3b8")
        date_str     = str(order["order_date"])[:16]

        with st.expander(
            f"Order #{order['id']}  ·  {order['customer']}  ·  ₹{order['total_amount']:,.0f}",
            expanded=False
        ):
            st.markdown(f"""
            <div style="display:flex;gap:1rem;flex-wrap:wrap;font-size:0.82rem;margin-bottom:0.5rem;">
                <span style="color:#94a3b8;">🕐 {date_str}</span>
                <span style="color:{status_color};font-weight:600;">● {order['status']}</span>
                <span style="color:{pay_color};font-weight:600;">💳 {order['payment_status']}</span>
            </div>
            """, unsafe_allow_html=True)

            items = get_order_items_detail(owner_id, order["id"])
            if items:
                df = pd.DataFrame(items)[["name","quantity","unit","price_at_order","line_total"]]
                df.columns = ["Item","Qty","Unit","Unit Price (₹)","Total (₹)"]
                st.dataframe(df, width='stretch', hide_index=True)

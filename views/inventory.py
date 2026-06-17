"""
views/inventory.py — Inventory Management Page (Multi-Tenant Edition)
=======================================================================
Full CRUD for inventory items scoped to the authenticated owner_id.
Each owner's inventory is completely separate — SKU uniqueness is per-owner.

Features:
  - Low-stock warnings (visual badges)
  - Category filtering
  - Search by name / SKU
  - Wholesale price & cost tracking
  - Mobile-friendly inline forms

Access:
  - Owner: full CRUD
  - Worker: read-only (can view stock levels)
"""

import streamlit as st
import pandas as pd
from db import (
    get_all_inventory, get_inventory_categories, get_item_by_id,
    add_inventory_item, update_inventory_item, delete_inventory_item
)
from styles import low_stock_banner


# ── Units choices ─────────────────────────────────────────────────────────────
UNITS = ["pcs", "kg", "g", "L", "mL", "bag", "box", "pkg", "btl", "loaf", "carton", "dozen"]
CATEGORIES = ["Grains", "Pulses", "Oils", "Dairy", "Bakery", "Snacks", "Beverages",
              "Condiments", "Spices", "Personal Care", "Household", "Other"]


def render():
    role     = st.session_state.get("role", "worker")
    owner_id = st.session_state.get("owner_id")

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="app-header">
        <span style="font-size:1.8rem">📦</span>
        <div>
            <h1>Inventory Management</h1>
            <p>Track stock levels, pricing, and reorder alerts</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Low-stock warning banner ──────────────────────────────────────────────
    all_items = get_all_inventory(owner_id)
    low_count = sum(1 for i in all_items if i["low_stock"])
    if low_count > 0:
        st.markdown(low_stock_banner(low_count), unsafe_allow_html=True)

    # ── Filters row ───────────────────────────────────────────────────────────
    filter_col1, filter_col2, filter_col3 = st.columns([3, 2, 1])
    with filter_col1:
        search = st.text_input("🔍 Search items",
                               placeholder="Name or SKU…",
                               label_visibility="collapsed")
    with filter_col2:
        categories = get_inventory_categories(owner_id)
        cat_filter = st.selectbox("Category", categories, label_visibility="collapsed")
    with filter_col3:
        if role == "owner":
            if st.button("➕ Add Item", width='stretch'):
                st.session_state["inv_mode"] = "add"
                st.session_state.pop("edit_inv_id", None)

    # ── Add / Edit form (Owner only) ──────────────────────────────────────────
    if role == "owner":
        inv_mode = st.session_state.get("inv_mode")
        edit_id  = st.session_state.get("edit_inv_id")
        if inv_mode in ("add", "edit"):
            existing = get_item_by_id(owner_id, edit_id) if inv_mode == "edit" else None
            _render_inventory_form(inv_mode, existing, owner_id)

    # ── Inventory table ───────────────────────────────────────────────────────
    st.markdown('<div class="section-title">📋 Stock List</div>', unsafe_allow_html=True)

    items = get_all_inventory(owner_id, search, cat_filter)
    if not items:
        st.info("No items found. Try adjusting your search or add new items.")
        return

    # Stats summary pills
    total_value = sum(i["quantity"] * i["price"] for i in items)
    st.markdown(f"""
    <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:0.75rem;">
        <span style="background:#22263a;border:1px solid #2e3347;border-radius:20px;
                     padding:0.25rem 0.75rem;font-size:0.75rem;color:#94a3b8;">
            📦 {len(items)} items
        </span>
        <span style="background:#22263a;border:1px solid #2e3347;border-radius:20px;
                     padding:0.25rem 0.75rem;font-size:0.75rem;color:#94a3b8;">
            💰 Stock value: ₹{total_value:,.0f}
        </span>
        <span style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);
                     border-radius:20px;padding:0.25rem 0.75rem;font-size:0.75rem;color:#f59e0b;">
            ⚠️ {low_count} low stock
        </span>
    </div>
    """, unsafe_allow_html=True)

    for item in items:
        _render_inventory_row(item, role, owner_id)


# ── Single inventory item card ────────────────────────────────────────────────
def _render_inventory_row(item: dict, role: str, owner_id: int):
    is_low  = item["low_stock"]
    border  = "rgba(245,158,11,0.5)" if is_low else "#2e3347"
    bg      = "rgba(245,158,11,0.05)" if is_low else "#1a1d27"
    stock_label = (
        f'<span style="color:#ef4444;font-weight:600;">⚠ LOW ({item["quantity"]} {item["unit"]})</span>'
        if is_low else
        f'<span style="color:#22c55e;">{item["quantity"]} {item["unit"]}</span>'
    )

    profit_pct = ((item["price"] - item["cost"]) / item["cost"] * 100) if item["cost"] > 0 else 0

    col1, col2 = st.columns([4, 1] if role == "owner" else [1, 0])
    with col1:
        st.markdown(f"""
        <div style="background:{bg};border:1px solid {border};border-radius:10px;
                    padding:0.75rem 1rem;margin-bottom:0.5rem;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <span style="font-weight:600;font-size:0.92rem;color:#e2e8f0;">
                        {item['name']}
                    </span>
                    <span style="font-size:0.7rem;color:#94a3b8;margin-left:0.5rem;">
                        {item['sku']}
                    </span>
                </div>
                <span style="font-size:0.72rem;background:#22263a;padding:0.15rem 0.5rem;
                             border-radius:20px;color:#94a3b8;">{item['category']}</span>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:1rem;margin-top:0.4rem;font-size:0.78rem;">
                <span>📦 Stock: {stock_label}</span>
                <span style="color:#94a3b8;">Min: {item['min_stock_level']} {item['unit']}</span>
                <span style="color:#4f8ef7;">Sell: ₹{item['price']:.2f}</span>
                <span style="color:#94a3b8;">Cost: ₹{item['cost']:.2f}</span>
                <span style="color:#22c55e;">Margin: {profit_pct:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if role == "owner":
        with col2:
            st.markdown("<div style='height:0.35rem'></div>", unsafe_allow_html=True)
            if st.button("✏️", key=f"edit_i_{item['id']}", width='stretch',
                         help="Edit item"):
                st.session_state["inv_mode"]    = "edit"
                st.session_state["edit_inv_id"] = item["id"]
                st.rerun()
            if st.button("🗑️", key=f"del_i_{item['id']}", width='stretch',
                         help="Delete item"):
                st.session_state["confirm_del_inv"] = item["id"]

    # Confirm delete
    if st.session_state.get("confirm_del_inv") == item["id"]:
        st.warning(f"Delete **{item['name']}**? This cannot be undone.")
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("✅ Confirm Delete", key=f"conf_d_{item['id']}"):
                delete_inventory_item(owner_id, item["id"])
                st.session_state.pop("confirm_del_inv", None)
                st.success("Item deleted.")
                st.rerun()
        with dc2:
            if st.button("❌ Cancel", key=f"cancel_d_{item['id']}"):
                st.session_state.pop("confirm_del_inv", None)
                st.rerun()


# ── Add / Edit form ───────────────────────────────────────────────────────────
def _render_inventory_form(mode: str, existing: dict = None, owner_id: int = None):
    title = "Edit Item" if mode == "edit" else "Add New Item"
    st.markdown(
        f'<div class="section-title">{"✏️" if mode=="edit" else "➕"} {title}</div>',
        unsafe_allow_html=True
    )

    with st.form(key="inventory_form", clear_on_submit=True):
        r1c1, r1c2, r1c3 = st.columns([1, 2, 1.5])
        with r1c1:
            sku = st.text_input("SKU *", value=existing["sku"] if existing else "")
        with r1c2:
            name = st.text_input("Item Name *", value=existing["name"] if existing else "")
        with r1c3:
            cat_default = existing["category"] if existing else CATEGORIES[0]
            cat_idx = CATEGORIES.index(cat_default) if cat_default in CATEGORIES else 0
            category = st.selectbox("Category", CATEGORIES, index=cat_idx)

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            quantity = st.number_input(
                "Quantity", min_value=0,
                value=int(existing["quantity"]) if existing else 0
            )
        with r2c2:
            unit_default = existing["unit"] if existing else "pcs"
            unit_idx = UNITS.index(unit_default) if unit_default in UNITS else 0
            unit = st.selectbox("Unit", UNITS, index=unit_idx)
        with r2c3:
            min_stock = st.number_input(
                "Min Stock Level", min_value=0,
                value=int(existing["min_stock_level"]) if existing else 10
            )

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            price = st.number_input(
                "Selling Price (₹) *", min_value=0.0,
                value=float(existing["price"]) if existing else 0.0,
                step=0.5, format="%.2f"
            )
        with r3c2:
            cost = st.number_input(
                "Cost / Buy Price (₹) *", min_value=0.0,
                value=float(existing["cost"]) if existing else 0.0,
                step=0.5, format="%.2f"
            )

        if price > 0 and cost > 0:
            margin = ((price - cost) / cost) * 100
            color  = "#22c55e" if margin >= 0 else "#ef4444"
            st.markdown(
                f'<p style="font-size:0.8rem;color:{color}">📊 Margin: {margin:.1f}% '
                f'(₹{price - cost:.2f} per unit)</p>',
                unsafe_allow_html=True
            )

        fc1, fc2 = st.columns(2)
        with fc1:
            submitted = st.form_submit_button("💾 Save Item", width='stretch')
        with fc2:
            cancelled = st.form_submit_button("✖ Cancel",     width='stretch')

        if cancelled:
            st.session_state.pop("inv_mode", None)
            st.session_state.pop("edit_inv_id", None)
            st.rerun()

        if submitted:
            errors = []
            if not sku.strip():  errors.append("SKU is required.")
            if not name.strip(): errors.append("Item name is required.")
            if price <= 0:       errors.append("Selling price must be greater than 0.")
            if cost <= 0:        errors.append("Cost price must be greater than 0.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                if mode == "add":
                    ok, msg = add_inventory_item(owner_id, sku, name, category,
                                                 quantity, unit, price, cost, min_stock)
                else:
                    ok, msg = update_inventory_item(owner_id, existing["id"], sku, name,
                                                    category, quantity, unit, price,
                                                    cost, min_stock)
                if ok:
                    st.success(f"✅ {msg}")
                    st.session_state.pop("inv_mode", None)
                    st.session_state.pop("edit_inv_id", None)
                    st.rerun()
                else:
                    st.error(msg)

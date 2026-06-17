"""
views/customers.py — Customer Management Page (Multi-Tenant Edition)
======================================================================
Full CRUD (Add / Edit / Delete) for retailer customers.
All operations are scoped to the authenticated owner_id — owners never
see each other's customers.

Access:
  - Owner: full CRUD
  - Worker: read-only view
"""

import streamlit as st
import pandas as pd
from db import (
    get_all_customers, get_customer_by_id,
    add_customer, update_customer, delete_customer
)


def render():
    role     = st.session_state.get("role", "worker")
    owner_id = st.session_state.get("owner_id")

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="app-header">
        <span style="font-size:1.8rem">👥</span>
        <div>
            <h1>Customer Management</h1>
            <p>Manage your wholesale retailer accounts</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Search bar + Add button ───────────────────────────────────────────────
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        search = st.text_input("🔍 Search customers",
                               placeholder="Name, contact, or phone…",
                               label_visibility="collapsed")
    with col_btn:
        if role == "owner":
            if st.button("➕ Add Customer", width='stretch'):
                st.session_state["cust_mode"] = "add"
                st.session_state.pop("edit_cust_id", None)

    # ── Add / Edit Form (Owner only) ──────────────────────────────────────────
    if role == "owner":
        mode    = st.session_state.get("cust_mode")
        edit_id = st.session_state.get("edit_cust_id")

        if mode in ("add", "edit"):
            existing = get_customer_by_id(owner_id, edit_id) if mode == "edit" else None
            _render_customer_form(mode, existing, owner_id)

    # ── Customer Table ────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">📋 Retailers</div>', unsafe_allow_html=True)

    customers = get_all_customers(owner_id, search)
    if not customers:
        st.info("No customers found. Add your first retailer.")
        return

    for cust in customers:
        _render_customer_row(cust, role)


# ── Inline customer row card ──────────────────────────────────────────────────
def _render_customer_row(cust: dict, role: str):
    balance      = cust["current_balance"]
    credit_limit = cust["credit_limit"]
    usage_pct    = (balance / credit_limit * 100) if credit_limit > 0 else 0
    warn         = "🔴" if usage_pct >= 90 else ("🟡" if usage_pct >= 60 else "🟢")

    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:10px;
                        padding:0.75rem 1rem;margin-bottom:0.5rem;">
                <div style="font-weight:600;font-size:0.95rem;color:#e2e8f0;">
                    {warn} {cust['business_name']}
                </div>
                <div style="font-size:0.78rem;color:#94a3b8;margin-top:0.2rem;">
                    👤 {cust['contact_person'] or '—'} &nbsp;|&nbsp;
                    📞 {cust['phone'] or '—'} &nbsp;|&nbsp;
                    📍 {cust['address'] or '—'}
                </div>
                <div style="font-size:0.78rem;color:#94a3b8;margin-top:0.25rem;">
                    Balance: <strong style="color:#e2e8f0;">₹{balance:,.0f}</strong>
                    &nbsp;/&nbsp; Credit Limit: ₹{credit_limit:,.0f}
                    &nbsp; ({usage_pct:.0f}% used)
                </div>
            </div>
            """, unsafe_allow_html=True)

        if role == "owner":
            with col2:
                st.markdown("<div style='height:0.35rem'></div>", unsafe_allow_html=True)
                if st.button("✏️", key=f"edit_c_{cust['id']}", width='stretch',
                             help="Edit customer"):
                    st.session_state["cust_mode"]    = "edit"
                    st.session_state["edit_cust_id"] = cust["id"]
                    st.rerun()
                if st.button("🗑️", key=f"del_c_{cust['id']}", width='stretch',
                             help="Delete customer"):
                    st.session_state["confirm_del_cust"] = cust["id"]

    # Confirm delete dialog
    if st.session_state.get("confirm_del_cust") == cust["id"]:
        st.warning(f"Delete **{cust['business_name']}**? This cannot be undone.")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("✅ Confirm Delete", key=f"conf_del_{cust['id']}"):
                owner_id = st.session_state.get("owner_id")
                delete_customer(owner_id, cust["id"])
                st.session_state.pop("confirm_del_cust", None)
                st.success("Customer deleted.")
                st.rerun()
        with cc2:
            if st.button("❌ Cancel", key=f"cancel_del_{cust['id']}"):
                st.session_state.pop("confirm_del_cust", None)
                st.rerun()


# ── Add / Edit form ───────────────────────────────────────────────────────────
def _render_customer_form(mode: str, existing: dict = None, owner_id: int = None):
    title = "Edit Customer" if mode == "edit" else "Add New Customer"
    st.markdown(f'<div class="section-title">{"✏️" if mode=="edit" else "➕"} {title}</div>',
                unsafe_allow_html=True)

    with st.form(key="customer_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            business_name = st.text_input(
                "Business Name *",
                value=existing["business_name"] if existing else ""
            )
            phone = st.text_input(
                "Phone",
                value=existing["phone"] if existing else ""
            )
            credit_limit = st.number_input(
                "Credit Limit (₹)",
                min_value=0.0,
                value=float(existing["credit_limit"]) if existing else 0.0,
                step=500.0
            )
        with col2:
            contact_person = st.text_input(
                "Contact Person",
                value=existing["contact_person"] if existing else ""
            )
            address = st.text_area(
                "Address",
                value=existing["address"] if existing else "",
                height=80
            )
            current_balance = st.number_input(
                "Current Balance (₹)",
                min_value=0.0,
                value=float(existing["current_balance"]) if existing else 0.0,
                step=100.0
            )

        fc1, fc2 = st.columns(2)
        with fc1:
            submitted = st.form_submit_button(
                "💾 Save Customer", width='stretch'
            )
        with fc2:
            cancelled = st.form_submit_button(
                "✖ Cancel", width='stretch'
            )

        if cancelled:
            st.session_state.pop("cust_mode", None)
            st.session_state.pop("edit_cust_id", None)
            st.rerun()

        if submitted:
            if not business_name.strip():
                st.error("Business name is required.")
            else:
                if mode == "add":
                    add_customer(owner_id, business_name, contact_person, phone,
                                 address, credit_limit, current_balance)
                    st.success(f"✅ Customer '{business_name}' added.")
                else:
                    update_customer(owner_id, existing["id"], business_name,
                                    contact_person, phone, address,
                                    credit_limit, current_balance)
                    st.success(f"✅ Customer '{business_name}' updated.")
                st.session_state.pop("cust_mode", None)
                st.session_state.pop("edit_cust_id", None)
                st.rerun()

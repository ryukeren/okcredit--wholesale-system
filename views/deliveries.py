"""
views/deliveries.py — Owner Delivery Management (Multi-Tenant Edition)
========================================================================
Full delivery workflow for owners, scoped to owner_id:
  - View only deliveries belonging to this owner's orders
  - Assign to this owner's active workers only
  - Record payments and update delivery status
  - Re-schedule failed deliveries
"""

import streamlit as st
from db import (
    get_all_deliveries_detailed,
    get_assignable_workers,
    assign_delivery_to_worker,
    update_delivery_status_only,
    record_delivery_outcome,
)

PAYMENT_MODES = ["Cash", "UPI", "Card", "Cheque"]


def render():
    owner_id = st.session_state.get("owner_id")

    st.markdown("""
    <div class="app-header">
        <span style="font-size:1.8rem">🚚</span>
        <div>
            <h1>Delivery Management</h1>
            <p>Assign, dispatch, track and collect payments</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    deliveries = get_all_deliveries_detailed(owner_id)
    workers    = get_assignable_workers(owner_id)

    if not deliveries:
        st.info("No deliveries yet. Place an order to automatically create a delivery record.")
        return

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    status_counts = {}
    for d in deliveries:
        status_counts[d["delivery_status"]] = status_counts.get(d["delivery_status"], 0) + 1

    color_map = {
        "Scheduled":       ("rgba(245,158,11,0.12)",  "rgba(245,158,11,0.4)",  "#f59e0b", "⏳"),
        "Out for Delivery":("rgba(79,142,247,0.12)",  "rgba(79,142,247,0.4)",  "#4f8ef7", "🚛"),
        "Delivered":       ("rgba(34,197,94,0.12)",   "rgba(34,197,94,0.4)",   "#22c55e", "✅"),
        "Failed":          ("rgba(239,68,68,0.12)",   "rgba(239,68,68,0.4)",   "#ef4444", "❌"),
    }

    pills = ""
    for status, cnt in status_counts.items():
        bg, bd, col, icon = color_map.get(status, ("#22263a", "#2e3347", "#94a3b8", "📦"))
        pills += f"""<span style="background:{bg};border:1px solid {bd};border-radius:20px;
                     padding:0.25rem 0.75rem;font-size:0.75rem;color:{col};">
                     {icon} {status}: {cnt}</span>"""

    st.markdown(
        f'<div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:1rem;">'
        f'{pills}</div>', unsafe_allow_html=True
    )

    # ── Filter tabs ───────────────────────────────────────────────────────────
    tab_labels = ["🔄 All", "⏳ Pending", "🚛 Out for Delivery", "✅ Delivered", "❌ Failed"]
    tabs = st.tabs(tab_labels)

    filter_map = {
        0: None,
        1: "Scheduled",
        2: "Out for Delivery",
        3: "Delivered",
        4: "Failed",
    }

    for tab_idx, tab in enumerate(tabs):
        with tab:
            status_filter = filter_map[tab_idx]
            filtered = deliveries if status_filter is None else [
                d for d in deliveries if d["delivery_status"] == status_filter
            ]

            if not filtered:
                st.info(f"No deliveries{' with status ' + repr(status_filter) if status_filter else ''}.")
                continue

            for d in filtered:
                _render_delivery_card(d, workers, owner_id, tab_idx)


# ─────────────────────────────────────────────────────────────────────────────
# DELIVERY CARD
# ─────────────────────────────────────────────────────────────────────────────

def _render_delivery_card(d: dict, workers: list, owner_id: int, tab_idx: int = 0):
    """Render delivery info with full payment collection controls."""
    kp = f"t{tab_idx}_d{d['id']}"

    bg, bd, col, icon = {
        "Scheduled":       ("rgba(245,158,11,0.05)",  "rgba(245,158,11,0.4)",  "#f59e0b", "⏳"),
        "Out for Delivery":("rgba(79,142,247,0.05)",  "rgba(79,142,247,0.4)",  "#4f8ef7", "🚛"),
        "Delivered":       ("rgba(34,197,94,0.05)",   "rgba(34,197,94,0.4)",   "#22c55e", "✅"),
        "Failed":          ("rgba(239,68,68,0.05)",   "rgba(239,68,68,0.4)",   "#ef4444", "❌"),
    }.get(d["delivery_status"], ("#1a1d27", "#2e3347", "#94a3b8", "📦"))

    pay_color = {"Paid": "#22c55e", "Unpaid": "#ef4444", "Partial": "#f59e0b"}.get(
        d["payment_status"], "#94a3b8"
    )
    date_str = str(d["delivery_date"])[:16] if d["delivery_date"] else "Not set"

    with st.container():
        with st.expander(
            f"{icon}  #{d['id']}  ·  {d['business_name']}  ·  {d['delivery_status']}  ·  💳 {d['payment_status']}",
            expanded=(d["delivery_status"] in ("Scheduled", "Out for Delivery"))
        ):
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bd};border-radius:10px;
                        padding:0.75rem 1rem;margin-bottom:0.75rem;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                    <div>
                        <div style="font-weight:700;color:#e2e8f0;font-size:0.95rem;">
                            {d['business_name']}
                        </div>
                        <div style="font-size:0.78rem;color:#94a3b8;margin-top:0.2rem;">
                            📞 {d.get('phone') or '—'} &nbsp;|&nbsp; 📍 {d.get('address') or '—'}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.05rem;font-weight:800;color:#4f8ef7;">
                            ₹{float(d['total_amount']):,.0f}
                        </div>
                        <div style="font-size:0.72rem;color:{pay_color};font-weight:700;">
                            💳 {d['payment_status']}
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:0.5rem;
                            font-size:0.77rem;color:#94a3b8;">
                    <span>🛒 Order #{d['order_id']}</span>
                    <span>👷 {d.get('worker_name') or 'Unassigned'}</span>
                    <span>📅 {date_str}</span>
                    {f'<span>📝 {d["notes"]}</span>' if d.get("notes") else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)

            status = d["delivery_status"]

            # ── SCHEDULED ────────────────────────────────────────────────────
            if status == "Scheduled":
                if workers:
                    w_map = {f"{w['name']}  ({w['role']})": w["id"] for w in workers}
                    ac1, ac2 = st.columns([3, 1])
                    with ac1:
                        sel_worker = st.selectbox(
                            "Assign to worker", list(w_map.keys()),
                            key=f"{kp}_assign_w", label_visibility="collapsed"
                        )
                    with ac2:
                        if st.button("🚛 Dispatch", key=f"{kp}_dispatch",
                                     width='stretch'):
                            assign_delivery_to_worker(owner_id, d["id"], w_map[sel_worker])
                            st.success(f"Dispatched to {sel_worker.split('(')[0].strip()}!")
                            st.rerun()
                else:
                    st.warning("No active workers. Add a worker first.")

                st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
                _render_payment_form(d, kp, owner_id, label="Direct Payment (self-pickup / owner collection)")

            # ── OUT FOR DELIVERY ─────────────────────────────────────────────
            elif status == "Out for Delivery":
                _render_payment_form(d, kp, owner_id, label="Record Payment & Complete Delivery")

            # ── FAILED ───────────────────────────────────────────────────────
            elif status == "Failed":
                if st.button("🔄 Re-schedule Delivery", key=f"{kp}_resched",
                             width='stretch'):
                    update_delivery_status_only(owner_id, d["id"], "Scheduled")
                    st.info("Delivery re-scheduled.")
                    st.rerun()

            # ── DELIVERED ────────────────────────────────────────────────────
            elif status == "Delivered":
                st.markdown(f"""
                <div style="font-size:0.78rem;color:#94a3b8;
                            background:rgba(34,197,94,0.06);border-radius:8px;
                            padding:0.5rem 0.75rem;">
                    ✅ Delivery complete &nbsp;|&nbsp; Payment: {d['payment_status']} &nbsp;|&nbsp; {d.get('notes') or '—'}
                </div>
                """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED PAYMENT COLLECTION FORM
# ─────────────────────────────────────────────────────────────────────────────

def _render_payment_form(d: dict, kp: str, owner_id: int, label: str = "Complete Delivery"):
    """Inline 4-outcome payment form."""
    total      = float(d["total_amount"])
    action_key = f"pay_action_{kp}"

    if action_key not in st.session_state:
        st.session_state[action_key] = None

    cur = st.session_state[action_key]

    st.markdown(f"""
    <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:0.4rem;
                text-transform:uppercase;letter-spacing:0.06em;">
        💰 {label}
    </div>
    """, unsafe_allow_html=True)

    if cur is None:
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button(f"✅ Full  ₹{total:,.0f}", key=f"{kp}_pf",
                         width='stretch'):
                st.session_state[action_key] = "full"
                st.rerun()
        with b2:
            if st.button("💛 Partial", key=f"{kp}_pp", width='stretch'):
                st.session_state[action_key] = "partial"
                st.rerun()
        with b3:
            if st.button("⚪ No Pay", key=f"{kp}_pn", width='stretch'):
                st.session_state[action_key] = "none"
                st.rerun()
        with b4:
            if st.button("❌ Failed", key=f"{kp}_fail", width='stretch'):
                st.session_state[action_key] = "failed"
                st.rerun()

    elif cur == "full":
        with st.form(key=f"{kp}_form_full", clear_on_submit=True):
            st.markdown(f"<div style='color:#22c55e;font-size:0.82rem;'>✅ Full payment — ₹{total:,.0f}</div>",
                        unsafe_allow_html=True)
            mode  = st.selectbox("Payment Mode", PAYMENT_MODES, key=f"{kp}_fm")
            notes = st.text_input("Notes (optional)", key=f"{kp}_fn")
            c1, c2 = st.columns(2)
            with c1: confirm = st.form_submit_button("✅ Confirm", width='stretch')
            with c2: cancel  = st.form_submit_button("✖ Back",    width='stretch')
        if confirm:
            ok, msg = record_delivery_outcome(
                delivery_id=d["id"], order_id=d["order_id"],
                customer_id=d["customer_id"], worker_id=d.get("worker_id") or 0,
                outcome="full", amount_collected=total,
                payment_mode=mode, fail_reason=notes
            )
            st.session_state.pop(action_key, None)
            if ok:
                st.success(f"✅ Delivered! ₹{total:,.0f} ({mode}) recorded.")
                st.rerun()
            else:
                st.error(f"❌ {msg}")
        if cancel:
            st.session_state[action_key] = None
            st.rerun()

    elif cur == "partial":
        with st.form(key=f"{kp}_form_part", clear_on_submit=True):
            st.markdown("<div style='color:#f59e0b;font-size:0.82rem;'>💛 Partial Payment</div>",
                        unsafe_allow_html=True)
            amt   = st.number_input(
                f"Amount Collected (max ₹{total:,.0f})",
                min_value=1.0, max_value=total, value=round(total / 2),
                step=50.0, format="%.0f", key=f"{kp}_pa"
            )
            mode  = st.selectbox("Payment Mode", PAYMENT_MODES, key=f"{kp}_pm")
            notes = st.text_input("Notes (optional)", key=f"{kp}_pnotes")
            c1, c2 = st.columns(2)
            with c1: confirm = st.form_submit_button("✅ Confirm", width='stretch')
            with c2: cancel  = st.form_submit_button("✖ Back",    width='stretch')
        if confirm:
            ok, msg = record_delivery_outcome(
                delivery_id=d["id"], order_id=d["order_id"],
                customer_id=d["customer_id"], worker_id=d.get("worker_id") or 0,
                outcome="partial", amount_collected=float(amt),
                payment_mode=mode
            )
            st.session_state.pop(action_key, None)
            if ok:
                st.success(f"✅ Delivered! ₹{amt:,.0f} of ₹{total:,.0f} ({mode}) collected.")
                st.rerun()
            else:
                st.error(f"❌ {msg}")
        if cancel:
            st.session_state[action_key] = None
            st.rerun()

    elif cur == "none":
        with st.form(key=f"{kp}_form_none", clear_on_submit=True):
            st.markdown("<div style='color:#94a3b8;font-size:0.82rem;'>⚪ Delivered — No Payment</div>",
                        unsafe_allow_html=True)
            notes = st.text_input("Reason (e.g. pay tomorrow, on credit)", key=f"{kp}_nn")
            c1, c2 = st.columns(2)
            with c1: confirm = st.form_submit_button("✅ Confirm Delivered", width='stretch')
            with c2: cancel  = st.form_submit_button("✖ Back",              width='stretch')
        if confirm:
            ok, msg = record_delivery_outcome(
                delivery_id=d["id"], order_id=d["order_id"],
                customer_id=d["customer_id"], worker_id=d.get("worker_id") or 0,
                outcome="none", fail_reason=notes
            )
            st.session_state.pop(action_key, None)
            if ok:
                st.success("✅ Delivered. No payment collected.")
                st.rerun()
            else:
                st.error(f"❌ {msg}")
        if cancel:
            st.session_state[action_key] = None
            st.rerun()

    elif cur == "failed":
        with st.form(key=f"{kp}_form_fail", clear_on_submit=True):
            st.markdown("<div style='color:#ef4444;font-size:0.82rem;'>❌ Mark as Failed</div>",
                        unsafe_allow_html=True)
            reason = st.text_input("Reason *", placeholder="e.g. shop closed, refused delivery",
                                   key=f"{kp}_fr")
            c1, c2 = st.columns(2)
            with c1: confirm = st.form_submit_button("❌ Confirm Failed", width='stretch')
            with c2: cancel  = st.form_submit_button("✖ Back",           width='stretch')
        if confirm:
            if not reason.strip():
                st.error("Please enter a reason.")
            else:
                ok, msg = record_delivery_outcome(
                    delivery_id=d["id"], order_id=d["order_id"],
                    customer_id=d["customer_id"], worker_id=d.get("worker_id") or 0,
                    outcome="failed", fail_reason=reason.strip()
                )
                st.session_state.pop(action_key, None)
                if ok:
                    st.warning(f"❌ Delivery #{d['id']} marked Failed.")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        if cancel:
            st.session_state[action_key] = None
            st.rerun()

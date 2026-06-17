"""
views/my_deliveries.py — Worker Delivery Dashboard (Multi-Tenant Edition)
==========================================================================
Simplified, mobile-first interface for delivery workers.
Workers only see deliveries belonging to their employer (owner_id is
resolved at login and stored in session_state).

Each active delivery card shows:
  - Customer name, contact person
  - Tap-to-call phone link
  - Address + 🗺️ Navigate button (Google Maps deep-link)
  - Order amount + Due amount
  - 4 action buttons:
      ✅ Full Payment    — delivered, full amount collected
      💛 Partial         — delivered, partial amount
      ⚪ No Payment      — delivered, customer refused / pay-later
      ❌ Failed          — could not deliver

Access: workers only (owners use the full Deliveries page).
"""

import streamlit as st
from db import (
    get_worker_id_for_user,
    get_deliveries_for_worker,
    get_completed_deliveries_for_worker,
    record_delivery_outcome,
    get_worker_total_today,
)

PAYMENT_MODES = ["Cash", "UPI", "Card", "Cheque"]


def render():
    user_id   = st.session_state.get("user_id")
    full_name = st.session_state.get("full_name", "Worker")

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="app-header">
        <span style="font-size:1.8rem">🚚</span>
        <div>
            <h1>My Deliveries</h1>
            <p>Welcome, {full_name} — your active delivery runs</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Resolve worker record ─────────────────────────────────────────────────
    worker_id = get_worker_id_for_user(user_id)

    if worker_id is None:
        st.warning(
            "⚠️ Your account is not linked to a worker record. "
            "Please ask your manager to link your login to a worker profile."
        )
        return

    # ── Worker daily total banner ─────────────────────────────────────────────
    daily_total = get_worker_total_today(worker_id)
    if daily_total > 0:
        st.markdown(f"""
        <div style="background:rgba(34,197,94,0.09);border:1px solid rgba(34,197,94,0.35);
                    border-left:3px solid #22c55e;border-radius:10px;
                    padding:0.65rem 1rem;margin-bottom:0.75rem;
                    display:flex;align-items:center;justify-content:space-between;">
            <span style="font-size:0.83rem;color:#94a3b8;">💰 Collected today</span>
            <span style="font-size:1.15rem;font-weight:800;color:#22c55e;">
                ₹{daily_total:,.0f}
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Active deliveries ─────────────────────────────────────────────────────
    active = get_deliveries_for_worker(worker_id)
    st.markdown('<div class="section-title">📦 Active Runs</div>', unsafe_allow_html=True)

    if not active:
        st.markdown("""
        <div style="background:#111827;border:1px dashed #1e293b;border-radius:12px;
                    padding:2rem;text-align:center;color:#94a3b8;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">✅</div>
            <div style="font-weight:600;color:#e2e8f0;margin-bottom:0.25rem;">All clear!</div>
            <div style="font-size:0.82rem;">No active deliveries assigned to you right now.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for delivery in active:
            _render_active_delivery_card(delivery, worker_id)

    # ── Completed deliveries (history) ────────────────────────────────────────
    st.markdown(
        '<div class="section-title">📋 Completed Deliveries (Recent)</div>',
        unsafe_allow_html=True
    )
    completed = get_completed_deliveries_for_worker(worker_id)

    if not completed:
        st.info("No completed deliveries yet.")
    else:
        for d in completed:
            _render_history_card(d)


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVE DELIVERY CARD
# ─────────────────────────────────────────────────────────────────────────────

def _render_active_delivery_card(d: dict, worker_id: int):
    """Render delivery info + 4-action form for an active delivery."""
    did     = d["id"]
    total   = float(d["total_amount"])
    pay_st  = d["payment_status"]
    address = d.get("address") or ""
    phone   = d.get("phone") or ""

    pay_color = {
        "Paid": "#22c55e", "Unpaid": "#ef4444", "Partial": "#f59e0b"
    }.get(pay_st, "#94a3b8")

    maps_url = f"https://www.google.com/maps/search/?api=1&query={address.replace(' ', '+')}"

    # ── Info card ─────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#111827;border:1px solid rgba(79,142,247,0.35);
                border-radius:14px;padding:1rem 1.15rem;margin-bottom:0.5rem;">

        <div style="display:flex;justify-content:space-between;align-items:flex-start;
                    flex-wrap:wrap;gap:0.5rem;">
            <div>
                <div style="font-size:1rem;font-weight:700;color:#e2e8f0;">
                    🏪 {d['business_name']}
                </div>
                <div style="font-size:0.78rem;color:#94a3b8;margin-top:0.1rem;">
                    👤 {d.get('contact_person') or '—'}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.15rem;font-weight:800;color:#4f8ef7;">
                    ₹{total:,.0f}
                </div>
                <div style="font-size:0.7rem;color:{pay_color};font-weight:700;">
                    💳 {pay_st}
                </div>
            </div>
        </div>

        <div style="margin-top:0.65rem;padding:0.55rem 0.75rem;
                    background:rgba(255,255,255,0.03);border-radius:8px;">
            <div style="font-size:0.78rem;color:#94a3b8;">
                📞 <a href="tel:{phone}"
                      style="color:#4f8ef7;text-decoration:none;font-weight:500;">
                    {phone or 'No phone'}
                </a>
                &nbsp;&nbsp;
                <a href="{maps_url}" target="_blank"
                   style="color:#22c55e;font-size:0.75rem;text-decoration:none;
                          background:rgba(34,197,94,0.1);padding:0.1rem 0.45rem;
                          border-radius:6px;border:1px solid rgba(34,197,94,0.3);">
                    🗺️ Navigate
                </a>
            </div>
            <div style="font-size:0.78rem;color:#94a3b8;margin-top:0.25rem;">
                📍 {address or 'No address provided'}
            </div>
        </div>

        <div style="margin-top:0.45rem;font-size:0.73rem;color:#94a3b8;">
            🛒 Order #{d['order_id']} &nbsp;|&nbsp;
            Status: <span style="color:#4f8ef7;font-weight:600;">
                {d['delivery_status']}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Action form ───────────────────────────────────────────────────────────
    action_key = f"action_state_{did}"
    if action_key not in st.session_state:
        st.session_state[action_key] = None

    cur_action = st.session_state[action_key]

    if cur_action is None:
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("✅ Full Pay", key=f"act_full_{did}", width='stretch'):
                st.session_state[action_key] = "full"
                st.rerun()
        with b2:
            if st.button("💛 Partial", key=f"act_part_{did}", width='stretch'):
                st.session_state[action_key] = "partial"
                st.rerun()
        with b3:
            if st.button("⚪ No Pay", key=f"act_none_{did}", width='stretch'):
                st.session_state[action_key] = "none"
                st.rerun()
        with b4:
            if st.button("❌ Failed", key=f"act_fail_{did}", width='stretch'):
                st.session_state[action_key] = "failed"
                st.rerun()

    elif cur_action == "full":
        st.markdown(f"""
        <div style="background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.3);
                    border-radius:10px;padding:0.75rem 1rem;margin-top:0.25rem;">
            <div style="font-size:0.82rem;color:#22c55e;font-weight:600;margin-bottom:0.4rem;">
                ✅ Full Payment — ₹{total:,.0f}
            </div>
        """, unsafe_allow_html=True)
        with st.form(key=f"form_full_{did}", clear_on_submit=True):
            mode = st.selectbox("Payment Mode", PAYMENT_MODES, key=f"mode_full_{did}")
            notes = st.text_input("Notes (optional)", placeholder="Any remarks...",
                                  key=f"notes_full_{did}")
            c1, c2 = st.columns(2)
            with c1:
                confirm = st.form_submit_button("✅ Confirm Delivered", width='stretch')
            with c2:
                cancel  = st.form_submit_button("✖ Back", width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

        if confirm:
            ok, msg = record_delivery_outcome(
                delivery_id=did, order_id=d["order_id"], customer_id=d["customer_id"],
                worker_id=worker_id, outcome="full",
                amount_collected=total, payment_mode=mode, fail_reason=notes
            )
            st.session_state.pop(action_key, None)
            if ok:
                st.success(f"✅ Delivered! ₹{total:,.0f} ({mode}) collected.")
                st.rerun()
            else:
                st.error(f"❌ {msg}")
        if cancel:
            st.session_state[action_key] = None
            st.rerun()

    elif cur_action == "partial":
        st.markdown("""
        <div style="background:rgba(245,158,11,0.07);border:1px solid rgba(245,158,11,0.3);
                    border-radius:10px;padding:0.75rem 1rem;margin-top:0.25rem;">
            <div style="font-size:0.82rem;color:#f59e0b;font-weight:600;margin-bottom:0.4rem;">
                💛 Partial Payment
            </div>
        """, unsafe_allow_html=True)
        with st.form(key=f"form_part_{did}", clear_on_submit=True):
            amt = st.number_input(
                f"Amount Collected (₹)  [Order total: ₹{total:,.0f}]",
                min_value=1.0, max_value=total - 0.01,
                value=round(total / 2, 0), step=50.0,
                format="%.0f", key=f"amt_part_{did}"
            )
            mode  = st.selectbox("Payment Mode", PAYMENT_MODES, key=f"mode_part_{did}")
            notes = st.text_input("Notes (optional)", key=f"notes_part_{did}")
            c1, c2 = st.columns(2)
            with c1:
                confirm = st.form_submit_button("✅ Confirm Delivered", width='stretch')
            with c2:
                cancel  = st.form_submit_button("✖ Back", width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

        if confirm:
            ok, msg = record_delivery_outcome(
                delivery_id=did, order_id=d["order_id"], customer_id=d["customer_id"],
                worker_id=worker_id, outcome="partial",
                amount_collected=float(amt), payment_mode=mode
            )
            st.session_state.pop(action_key, None)
            if ok:
                st.success(f"✅ Delivered! ₹{amt:,.0f} of ₹{total:,.0f} collected.")
                st.rerun()
            else:
                st.error(f"❌ {msg}")
        if cancel:
            st.session_state[action_key] = None
            st.rerun()

    elif cur_action == "none":
        st.markdown("""
        <div style="background:rgba(148,163,184,0.07);border:1px solid rgba(148,163,184,0.25);
                    border-radius:10px;padding:0.75rem 1rem;margin-top:0.25rem;">
            <div style="font-size:0.82rem;color:#94a3b8;font-weight:600;margin-bottom:0.4rem;">
                ⚪ Delivered — No Payment Collected
            </div>
        """, unsafe_allow_html=True)
        with st.form(key=f"form_none_{did}", clear_on_submit=True):
            notes = st.text_input("Reason (e.g. pay tomorrow, credit)",
                                  key=f"notes_none_{did}")
            c1, c2 = st.columns(2)
            with c1:
                confirm = st.form_submit_button("✅ Confirm Delivered", width='stretch')
            with c2:
                cancel  = st.form_submit_button("✖ Back", width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

        if confirm:
            ok, msg = record_delivery_outcome(
                delivery_id=did, order_id=d["order_id"], customer_id=d["customer_id"],
                worker_id=worker_id, outcome="none", fail_reason=notes
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

    elif cur_action == "failed":
        st.markdown("""
        <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.3);
                    border-radius:10px;padding:0.75rem 1rem;margin-top:0.25rem;">
            <div style="font-size:0.82rem;color:#ef4444;font-weight:600;margin-bottom:0.4rem;">
                ❌ Mark as Failed Delivery
            </div>
        """, unsafe_allow_html=True)
        with st.form(key=f"form_fail_{did}", clear_on_submit=True):
            reason = st.text_input("Reason for failure *",
                                   placeholder="e.g. shop closed, wrong address, refused",
                                   key=f"reason_fail_{did}")
            c1, c2 = st.columns(2)
            with c1:
                confirm = st.form_submit_button("❌ Confirm Failed", width='stretch')
            with c2:
                cancel  = st.form_submit_button("✖ Back", width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

        if confirm:
            if not reason.strip():
                st.error("Please enter a reason for the failed delivery.")
            else:
                ok, msg = record_delivery_outcome(
                    delivery_id=did, order_id=d["order_id"], customer_id=d["customer_id"],
                    worker_id=worker_id, outcome="failed", fail_reason=reason.strip()
                )
                st.session_state.pop(action_key, None)
                if ok:
                    st.warning(f"❌ Delivery #{did} marked as Failed.")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        if cancel:
            st.session_state[action_key] = None
            st.rerun()

    st.markdown("<div style='height:0.65rem'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY CARD
# ─────────────────────────────────────────────────────────────────────────────

def _render_history_card(d: dict):
    """Render a compact completed delivery history entry."""
    status      = d["delivery_status"]
    notes       = d.get("notes") or "—"
    date_str    = str(d.get("delivery_date", ""))[:16] or "—"
    total       = float(d.get("total_amount", 0))
    status_col  = "#22c55e" if status == "Delivered" else "#ef4444"
    status_icon = "✅" if status == "Delivered" else "❌"

    st.markdown(f"""
    <div style="background:#111827;border:1px solid #1e293b;border-radius:10px;
                padding:0.65rem 1rem;margin-bottom:0.4rem;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
            <span style="font-weight:600;color:#e2e8f0;font-size:0.88rem;">
                {status_icon} {d['business_name']}
            </span>
            <span style="color:{status_col};font-size:0.72rem;font-weight:700;">
                {status}
            </span>
        </div>
        <div style="font-size:0.73rem;color:#94a3b8;margin-top:0.2rem;line-height:1.6;">
            📅 {date_str} &nbsp;|&nbsp;
            🛒 Order #{d['order_id']} &nbsp;|&nbsp;
            ₹{total:,.0f} &nbsp;|&nbsp;
            {notes}
        </div>
    </div>
    """, unsafe_allow_html=True)

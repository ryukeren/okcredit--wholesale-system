"""
views/workers.py — Worker Panel (Multi-Tenant Edition)
========================================================
Owner can:
  - Add workers → worker gets owner_id = this owner's user.id
  - Generate a unique Worker Code shared with the employee
  - Edit worker details (name, role, phone, status)
  - Delete workers (scoped to this owner only)
  - See registration status (linked / pending)

Worker codes are globally unique. When a worker registers with the code,
their users.owner_id is set to this owner's id — giving them access to
this owner's delivery data only.
"""

import streamlit as st
from db import (
    get_all_workers, add_worker, update_worker, delete_worker, get_connection
)

ROLES   = ["Driver", "Picker", "Manager", "Supervisor", "Accountant", "Other"]
ROLE_ICONS = {
    "Manager":    "🏢",
    "Supervisor": "📋",
    "Picker":     "📦",
    "Driver":     "🚛",
    "Accountant": "💼",
    "Other":      "👤",
}


def _get_workers_with_code(owner_id: int):
    """Fetch all workers for this owner including worker_code and user_id."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, name, role, status, phone, worker_code, user_id
           FROM workers WHERE owner_id=? ORDER BY name""",
        (owner_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def render():
    role     = st.session_state.get("role", "worker")
    owner_id = st.session_state.get("owner_id")

    st.markdown("""
    <div class="app-header">
        <span style="font-size:1.8rem">👷</span>
        <div>
            <h1>Worker Panel</h1>
            <p>Manage your workforce and generate invite codes</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if role != "owner":
        st.info("Contact your manager for schedule updates.")
        return

    # ── Add Worker button ─────────────────────────────────────────────────────
    if st.button("➕ Add New Worker", width='content', key="btn_add_worker"):
        st.session_state["worker_mode"]   = "add"
        st.session_state.pop("edit_worker_id", None)
        st.session_state.pop("new_worker_code", None)

    # ── Add / Edit form ───────────────────────────────────────────────────────
    mode = st.session_state.get("worker_mode")
    if mode == "add":
        _render_worker_form_add(owner_id)
    elif mode == "edit":
        _render_worker_form_edit(owner_id, st.session_state.get("edit_worker_id"))

    # ── Show newly generated code prominently ─────────────────────────────────
    if "new_worker_code" in st.session_state:
        info = st.session_state["new_worker_code"]
        st.markdown(f"""
        <div style="background:rgba(34,197,94,0.1);border:2px solid rgba(34,197,94,0.5);
                    border-radius:12px;padding:1.25rem;margin-bottom:1rem;">
            <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.4rem;">
                ✅ Worker <strong style="color:#e2e8f0;">{info['name']}</strong> added.
                Share this code with them so they can register:
            </div>
            <div style="font-size:2rem;font-weight:800;color:#22c55e;
                        letter-spacing:0.15em;text-align:center;
                        background:#0f1117;border-radius:8px;padding:0.75rem;
                        font-family:monospace;">
                {info['code']}
            </div>
            <div style="font-size:0.75rem;color:#94a3b8;text-align:center;margin-top:0.4rem;">
                ⚠️ Save this code now — the worker will need it to register their account.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("✕ Dismiss", key="dismiss_code"):
            del st.session_state["new_worker_code"]
            st.rerun()

    # ── Worker roster ─────────────────────────────────────────────────────────
    workers = _get_workers_with_code(owner_id)

    if not workers:
        st.markdown("""
        <div style="background:#1a1d27;border:1px dashed #2e3347;border-radius:12px;
                    padding:2rem;text-align:center;color:#94a3b8;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">👷</div>
            <div style="font-weight:600;color:#e2e8f0;margin-bottom:0.25rem;">No workers yet</div>
            <div style="font-size:0.82rem;">Click "Add New Worker" to create your first worker record.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    active   = sum(1 for w in workers if w["status"] == "Active")
    linked   = sum(1 for w in workers if w.get("user_id"))

    st.markdown(f"""
    <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:1rem;">
        <span style="background:#22263a;border:1px solid #2e3347;border-radius:20px;
                     padding:0.25rem 0.75rem;font-size:0.75rem;color:#94a3b8;">
            👷 {len(workers)} total
        </span>
        <span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);
                     border-radius:20px;padding:0.25rem 0.75rem;font-size:0.75rem;color:#22c55e;">
            ✅ {active} active
        </span>
        <span style="background:rgba(79,142,247,0.12);border:1px solid rgba(79,142,247,0.3);
                     border-radius:20px;padding:0.25rem 0.75rem;font-size:0.75rem;color:#4f8ef7;">
            🔗 {linked} registered
        </span>
        {f'<span style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);border-radius:20px;padding:0.25rem 0.75rem;font-size:0.75rem;color:#f59e0b;">⏳ {len(workers)-linked} pending registration</span>' if len(workers) - linked > 0 else ""}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">📋 Worker Roster</div>', unsafe_allow_html=True)

    for w in workers:
        _render_worker_card(w, owner_id)


def _render_worker_card(w: dict, owner_id: int):
    """Render a worker card with code, registration status, and edit/delete actions."""
    icon         = ROLE_ICONS.get(w["role"], "👤")
    status_color = "#22c55e" if w["status"] == "Active" else "#ef4444"
    is_linked    = bool(w.get("user_id"))
    reg_label    = ("🔗 Account linked" if is_linked else "⏳ Awaiting registration")
    reg_color    = "#22c55e" if is_linked else "#f59e0b"
    code_display = w.get("worker_code") or "—"

    col_info, col_actions = st.columns([5, 1])
    with col_info:
        st.markdown(f"""
        <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:10px;
                    padding:0.75rem 1rem;margin-bottom:0.4rem;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                <div>
                    <span style="font-size:1.1rem;">{icon}</span>
                    <span style="font-weight:600;color:#e2e8f0;font-size:0.95rem;margin-left:0.35rem;">
                        {w['name']}
                    </span>
                    <span style="font-size:0.75rem;background:#22263a;padding:0.12rem 0.45rem;
                                 border-radius:20px;color:#94a3b8;margin-left:0.4rem;">
                        {w['role']}
                    </span>
                </div>
                <span style="color:{status_color};font-size:0.75rem;font-weight:600;">
                    ● {w['status']}
                </span>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:0.75rem;margin-top:0.4rem;font-size:0.78rem;color:#94a3b8;">
                <span>📞 {w['phone'] or '—'}</span>
                <span style="color:{reg_color};">{reg_label}</span>
            </div>
            {'<div style="margin-top:0.4rem;font-size:0.78rem;color:#94a3b8;">Invite Code: <code style="background:#22263a;padding:0.1rem 0.45rem;border-radius:4px;color:#4f8ef7;font-size:0.85rem;letter-spacing:0.08em;">' + code_display + '</code></div>' if not is_linked else ''}
        </div>
        """, unsafe_allow_html=True)

    with col_actions:
        st.markdown("<div style='height:0.35rem'></div>", unsafe_allow_html=True)
        if st.button("✏️", key=f"edit_w_{w['id']}", width='stretch', help="Edit"):
            st.session_state["worker_mode"]   = "edit"
            st.session_state["edit_worker_id"] = w["id"]
            st.session_state.pop("new_worker_code", None)
            st.rerun()
        if st.button("🗑️", key=f"del_w_{w['id']}", width='stretch', help="Delete"):
            st.session_state[f"confirm_del_w_{w['id']}"] = True

    # Delete confirmation
    if st.session_state.get(f"confirm_del_w_{w['id']}"):
        st.warning(f"Delete **{w['name']}**? This cannot be undone.")
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("✅ Confirm", key=f"conf_del_w_{w['id']}"):
                delete_worker(owner_id, w["id"])
                st.session_state.pop(f"confirm_del_w_{w['id']}", None)
                st.success("Worker deleted.")
                st.rerun()
        with dc2:
            if st.button("❌ Cancel", key=f"cancel_del_w_{w['id']}"):
                st.session_state.pop(f"confirm_del_w_{w['id']}", None)
                st.rerun()


def _render_worker_form_add(owner_id: int):
    """Form to add a new worker and display their generated invite code."""
    st.markdown('<div class="section-title">➕ Add New Worker</div>', unsafe_allow_html=True)

    with st.form("add_worker_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name  = st.text_input("Full Name *", placeholder="e.g. Suresh Kumar")
            phone = st.text_input("Phone Number", placeholder="e.g. 9876543210")
        with c2:
            role_idx = ROLES.index("Driver")
            role = st.selectbox("Role *", ROLES, index=role_idx)

        st.markdown("""
        <div style="font-size:0.78rem;color:#94a3b8;padding:0.5rem 0;">
            💡 After adding, a unique <strong style="color:#e2e8f0;">Worker Code</strong>
            will be generated. Share it with the employee so they can create their login.
        </div>
        """, unsafe_allow_html=True)

        fc1, fc2 = st.columns(2)
        with fc1:
            submitted = st.form_submit_button("✅ Add Worker & Generate Code", width='stretch')
        with fc2:
            cancelled = st.form_submit_button("✖ Cancel", width='stretch')

    if cancelled:
        st.session_state.pop("worker_mode", None)
        st.rerun()

    if submitted:
        if not name.strip():
            st.error("Worker name is required.")
        else:
            wid, code = add_worker(owner_id, name.strip(), role, phone.strip())
            st.session_state.pop("worker_mode", None)
            st.session_state["new_worker_code"] = {"name": name.strip(), "code": code}
            st.rerun()


def _render_worker_form_edit(owner_id: int, worker_id: int):
    """Form to edit an existing worker's details (ownership-verified)."""
    if not worker_id:
        return

    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM workers WHERE id=? AND owner_id=?",
        (worker_id, owner_id)
    ).fetchone()
    conn.close()
    if not row:
        st.error("Worker not found.")
        return
    w = dict(row)

    st.markdown('<div class="section-title">✏️ Edit Worker</div>', unsafe_allow_html=True)

    with st.form("edit_worker_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name  = st.text_input("Full Name *", value=w["name"])
            phone = st.text_input("Phone Number", value=w["phone"] or "")
        with c2:
            role_idx   = ROLES.index(w["role"]) if w["role"] in ROLES else 0
            role       = st.selectbox("Role *", ROLES, index=role_idx)
            status_opt = ["Active", "Inactive"]
            stat_idx   = status_opt.index(w["status"]) if w["status"] in status_opt else 0
            status     = st.selectbox("Status", status_opt, index=stat_idx)

        fc1, fc2 = st.columns(2)
        with fc1:
            submitted = st.form_submit_button("💾 Save Changes", width='stretch')
        with fc2:
            cancelled = st.form_submit_button("✖ Cancel", width='stretch')

    if cancelled:
        st.session_state.pop("worker_mode", None)
        st.session_state.pop("edit_worker_id", None)
        st.rerun()

    if submitted:
        if not name.strip():
            st.error("Worker name is required.")
        else:
            update_worker(owner_id, worker_id, name.strip(), role, phone.strip(), status)
            st.success(f"✅ Worker '{name}' updated.")
            st.session_state.pop("worker_mode", None)
            st.session_state.pop("edit_worker_id", None)
            st.rerun()

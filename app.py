"""
app.py — Main Application Entrypoint
======================================
Wholesale Operations & Inventory Management System
Built with Python + Streamlit + PostgreSQL (Supabase) / SQLite fallback

Architecture:
  - database.py  : Auto-selects PostgreSQL or SQLite backend
  - db.py        : Multi-tenant CRUD engine (all queries scoped by owner_id)
  - styles.py    : CSS injection and reusable HTML components
  - views/       : One module per page
  - app.py       : Bootstraps DB, handles auth, routes sidebar nav

Multi-tenant design:
  - Owner account  → owner_id in session = user["id"]   (their own id)
  - Worker account → owner_id in session = user["owner_id"]  (their manager's id)
  - Every db.py call receives this owner_id → complete data isolation

Role-based navigation:
  Owner  → Dashboard, Customers, Inventory, Orders, Deliveries, Worker Panel
  Worker → My Deliveries only (simplified mobile interface)
"""

import streamlit as st

# ── Must be the FIRST Streamlit call in the script ───────────────────────────
st.set_page_config(
    page_title="OkCredit — Wholesale Manager",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Internal modules ──────────────────────────────────────────────────────────
from db import init_db, authenticate_user
from styles import inject_custom_css

# ── Initialise database (idempotent — safe to call every run) ────────────────
init_db()

# ── Inject global CSS ─────────────────────────────────────────────────────────
inject_custom_css()


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def login(username: str, password: str) -> bool:
    """
    Authenticate user and populate session state.

    Session keys set:
      authenticated : True
      user_id       : users.id
      username      : users.username
      full_name     : users.full_name
      role          : 'owner' | 'worker'
      owner_id      : the owning business id
                      → for owners  : their own user.id
                      → for workers : their manager's user.id (users.owner_id)
    """
    user = authenticate_user(username, password)
    if user:
        st.session_state["authenticated"] = True
        st.session_state["user_id"]       = user["id"]
        st.session_state["username"]      = user["username"]
        st.session_state["full_name"]     = user["full_name"] or user["username"].title()
        st.session_state["role"]          = user["role"]

        # ── Multi-tenant owner_id resolution ─────────────────────────────────
        if user["role"] == "owner":
            # Owner: their own id IS the owner_id
            st.session_state["owner_id"] = user["id"]
        else:
            # Worker: owner_id points to the business owner they work for
            # users.owner_id is set when the worker registers with a WK-code
            worker_owner = user.get("owner_id")
            if worker_owner:
                st.session_state["owner_id"] = worker_owner
            else:
                # Fallback: try to find owner_id via worker record
                from db import get_worker_id_for_user, get_connection
                wid = get_worker_id_for_user(user["id"])
                if wid:
                    conn = get_connection()
                    row = conn.execute(
                        "SELECT owner_id FROM workers WHERE id=?", (wid,)
                    ).fetchone()
                    conn.close()
                    st.session_state["owner_id"] = row[0] if row and row[0] else user["id"]
                else:
                    st.session_state["owner_id"] = user["id"]

        return True
    return False


def logout():
    """Clear all session state keys."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE  (Sign In + Register tabs)
# ─────────────────────────────────────────────────────────────────────────────

# Owner registration requires this secret key to prevent unauthorised escalation.
# Each business owner uses this same key — they are distinguished by their user.id
# after registration (multi-tenant data isolation via owner_id).
OWNER_SECRET = "wholesale2024"


def render_login():
    # Centre the card using columns
    _, centre, _ = st.columns([1, 1.6, 1])
    with centre:
        # ── Brand logo ────────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center;margin-bottom:1.25rem;">
            <div style="font-size:3rem;">🏪</div>
            <div style="font-size:1.4rem;font-weight:700;color:#e2e8f0;">OkCredit</div>
            <div style="font-size:0.8rem;color:#94a3b8;">Wholesale Operations Manager</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Tabs: Sign In / Register ──────────────────────────────────────────
        tab_signin, tab_register = st.tabs(["🔐 Sign In", "📝 Register"])

        # ── SIGN IN TAB ───────────────────────────────────────────────────────
        with tab_signin:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input(
                    "Password", placeholder="Enter your password", type="password"
                )
                submitted = st.form_submit_button("🔐 Sign In", width='stretch')

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                elif login(username.strip(), password):
                    st.success(f"Welcome back, {st.session_state['full_name']}! 👋")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")

            # Credentials hint
            st.markdown("""
            <div style="margin-top:0.75rem;padding:0.75rem;background:#22263a;border-radius:8px;
                        font-size:0.75rem;color:#94a3b8;border:1px solid #2e3347;">
                <strong style="color:#e2e8f0;">Default Credentials</strong><br>
                🔑 Owner : <code>admin</code> / <code>admin123</code>
            </div>
            """, unsafe_allow_html=True)

        # ── REGISTER TAB ──────────────────────────────────────────────────────
        with tab_register:
            st.markdown("""
            <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem;
                        background:#1a1d27;border:1px solid #2e3347;border-radius:8px;padding:0.75rem;">
                <strong style="color:#e2e8f0;">How registration works:</strong><br><br>
                👷 <strong style="color:#4f8ef7;">Workers</strong> — Your employer (owner) must first add
                you in the <em>Worker Panel</em>. They will give you a unique
                <strong style="color:#22c55e;">Worker Code</strong> (e.g. WK-AB12XY).
                Enter it below to create your account.<br><br>
                🔑 <strong style="color:#f59e0b;">Owners</strong> — Enter the Owner Secret Key
                provided by your administrator. Each owner gets a completely separate
                business workspace.
            </div>
            """, unsafe_allow_html=True)

            with st.form("register_form", clear_on_submit=False):
                reg_fullname = st.text_input(
                    "Full Name *", placeholder="e.g. Ravi Kumar"
                )
                reg_username = st.text_input(
                    "Username *", placeholder="Choose a unique username"
                )
                reg_password = st.text_input(
                    "Password *", placeholder="Min 6 characters", type="password"
                )
                reg_confirm = st.text_input(
                    "Confirm Password *", placeholder="Re-enter password", type="password"
                )
                reg_role = st.selectbox(
                    "I am registering as *",
                    ["Worker", "Owner"],
                )
                reg_code = st.text_input(
                    "Access Code *",
                    placeholder="Worker Code (e.g. WK-AB12XY) or Owner Secret Key",
                    type="password",
                    help=(
                        "Workers: enter the Worker Code your employer gave you.\n"
                        "Owners: enter the Owner Secret Key."
                    )
                )
                reg_submit = st.form_submit_button(
                    "✅ Create Account", width='stretch'
                )

            if reg_submit:
                from db import register_user, get_worker_by_code, link_user_to_worker

                errors = []
                # ── Basic field validation ────────────────────────────────────
                if not reg_fullname.strip():
                    errors.append("Full name is required.")
                if not reg_username.strip():
                    errors.append("Username is required.")
                elif len(reg_username.strip()) < 3:
                    errors.append("Username must be at least 3 characters.")
                if not reg_password:
                    errors.append("Password is required.")
                elif len(reg_password) < 6:
                    errors.append("Password must be at least 6 characters.")
                elif reg_password != reg_confirm:
                    errors.append("Passwords do not match.")
                if not reg_code.strip():
                    errors.append("Access Code is required.")

                # ── Role-specific validation ──────────────────────────────────
                worker_record = None
                if not errors:
                    if reg_role == "Owner":
                        if reg_code.strip() != OWNER_SECRET:
                            errors.append("Invalid Owner Secret Key.")
                    else:  # Worker
                        worker_record = get_worker_by_code(reg_code.strip())
                        if not worker_record:
                            errors.append(
                                "Invalid Worker Code. Please check with your employer. "
                                "Codes are case-sensitive and look like WK-XXXXXX."
                            )
                        elif worker_record.get("user_id"):
                            errors.append(
                                "This Worker Code has already been used. "
                                "Please contact your employer for a new one."
                            )

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    role_val = reg_role.lower()

                    # ── Determine owner_id for the new account ────────────────
                    # Owner registrations: owner_id = None (they are the owner)
                    # Worker registrations: owner_id = the worker record's owner_id
                    new_owner_id = None
                    if role_val == "worker" and worker_record:
                        new_owner_id = worker_record.get("owner_id")

                    ok, result = register_user(
                        reg_username.strip(), reg_password,
                        reg_fullname.strip(), role_val,
                        owner_id=new_owner_id
                    )
                    if ok:
                        user = result
                        # Link worker record if registering as worker
                        if role_val == "worker" and worker_record:
                            link_user_to_worker(user["id"], worker_record["id"])

                        # ── Populate session state ────────────────────────────
                        st.session_state["authenticated"] = True
                        st.session_state["user_id"]       = user["id"]
                        st.session_state["username"]      = user["username"]
                        st.session_state["full_name"]     = user["full_name"]
                        st.session_state["role"]          = user["role"]

                        if role_val == "owner":
                            # New owner: their own id is the owner_id
                            st.session_state["owner_id"] = user["id"]
                        else:
                            # New worker: inherit the owner_id from worker record
                            st.session_state["owner_id"] = new_owner_id or user["id"]

                        st.success(f"🎉 Account created! Welcome, {user['full_name']}!")
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────

ALL_PAGES = [
    ("Dashboard",      "🏠", ["owner"]),
    ("Business Analytics", "📊", ["owner"]),
    ("Customers",      "👥", ["owner"]),
    ("Inventory",      "📦", ["owner"]),
    ("Orders",         "🛒", ["owner"]),
    ("Deliveries",     "🚚", ["owner"]),
    ("Worker Panel",   "👷", ["owner"]),
    ("My Deliveries",  "🚚", ["worker"]),
]


def render_sidebar() -> str:
    """Render the premium sidebar and return the selected page name."""
    role      = st.session_state.get("role", "worker")
    full_name = st.session_state.get("full_name", "User")
    initial   = full_name[0].upper() if full_name else "U"

    with st.sidebar:
        # ── Brand ─────────────────────────────────────────────────────────────
        st.markdown("""
        <div class="sidebar-logo">
            <div style="display:flex;align-items:center;gap:0.6rem;">
                <span style="font-size:1.6rem;line-height:1;">🏪</span>
                <div>
                    <h3 style="margin:0;">OkCredit</h3>
                    <p style="margin:0;">Wholesale Manager</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── User profile card ─────────────────────────────────────────────────
        role_color = "#4f8ef7" if role == "owner" else "#22c55e"
        role_label = "Owner" if role == "owner" else "Worker"
        st.markdown(f"""
        <div style="margin:0.25rem 0.5rem 0.75rem;padding:0.75rem 0.85rem;
                    background:rgba(255,255,255,0.03);border:1px solid #1e293b;
                    border-radius:12px;display:flex;align-items:center;gap:0.6rem;">
            <div style="width:34px;height:34px;border-radius:50%;flex-shrink:0;
                        background:linear-gradient(135deg,#4f8ef7,#7c5cbf);
                        display:flex;align-items:center;justify-content:center;
                        font-weight:700;font-size:0.88rem;color:#fff;">
                {initial}
            </div>
            <div style="overflow:hidden;">
                <div style="font-weight:600;color:#e2e8f0;font-size:0.82rem;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    {full_name}
                </div>
                <div style="font-size:0.68rem;color:{role_color};font-weight:600;
                            text-transform:uppercase;letter-spacing:0.07em;margin-top:0.1rem;">
                    ● {role_label}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Nav label ─────────────────────────────────────────────────────────
        st.markdown("""
        <div style="font-size:0.65rem;font-weight:700;color:#475569;
                    text-transform:uppercase;letter-spacing:0.1em;
                    padding:0 1rem;margin-bottom:0.3rem;">
            Navigation
        </div>
        """, unsafe_allow_html=True)

        available = [p for p in ALL_PAGES if role in p[2]]
        labels    = [f"{icon}  {name}" for name, icon, _ in available]

        if "sidebar_nav" not in st.session_state or \
                st.session_state["sidebar_nav"] not in labels:
            st.session_state["sidebar_nav"] = labels[0]

        st.radio(
            "Navigation",
            labels,
            key="sidebar_nav",
            label_visibility="collapsed",
        )

        # ── Logout with confirmation ──────────────────────────────────────────
        st.markdown("""
        <div style="height:1rem;"></div>
        <div style="border-top:1px solid #1e293b;margin:0 0.5rem 0.75rem;"></div>
        """, unsafe_allow_html=True)

        if not st.session_state.get("confirm_logout"):
            if st.button("🚪  Logout", width='stretch', key="btn_logout_init"):
                st.session_state["confirm_logout"] = True
                st.rerun()
        else:
            st.markdown("""
            <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);
                        border-radius:10px;padding:0.65rem 0.75rem;margin:0 0.25rem;
                        font-size:0.8rem;color:#fca5a5;text-align:center;">
                ⚠️ Confirm sign out?
            </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Yes", width='stretch', key="btn_logout_yes"):
                    st.session_state.pop("confirm_logout", None)
                    logout()
            with c2:
                if st.button("❌ No", width='stretch', key="btn_logout_no"):
                    st.session_state.pop("confirm_logout", None)
                    st.rerun()

        raw = st.session_state.get("sidebar_nav", labels[0])
        page_name = raw.split("  ", 1)[1] if "  " in raw else raw
        return page_name


# ─────────────────────────────────────────────────────────────────────────────
# PAGE ROUTER
# ─────────────────────────────────────────────────────────────────────────────
def route_page(page: str):
    """Import and render the selected page view module."""
    if page == "Dashboard":
        from views.dashboard       import render
    elif page == "Business Analytics":
        from views.analytics       import render
    elif page == "Customers":
        from views.customers       import render
    elif page == "Inventory":
        from views.inventory       import render
    elif page == "Orders":
        from views.orders          import render
    elif page == "Deliveries":
        from views.deliveries      import render
    elif page == "Worker Panel":
        from views.workers         import render
    elif page == "My Deliveries":
        from views.my_deliveries   import render
    else:
        st.error(f"Page '{page}' not found.")
        return
    render()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if not is_authenticated():
        render_login()
    else:
        page = render_sidebar()
        route_page(page)


if __name__ == "__main__":
    main()

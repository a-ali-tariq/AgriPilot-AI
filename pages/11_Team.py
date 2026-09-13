"""Team & contact.

To add a member, append to TEAM below, nothing else needs to change.
Phone numbers are stored in full international form without spaces or a
leading +, because that is what wa.me links require.
"""
from __future__ import annotations

import streamlit as st

from agripilot import state
from ui import components, theme

TEAM = [
    {
        "name": "Amir Ali Tariq",
        "role": "Full Stack Developer · AWS & GCP Certified",
        "linkedin": "https://www.linkedin.com/in/amiralitariq/",
        "email": "amiralitariq@gmail.com",
        "whatsapp": "923326363256",
    },
    {
        "name": "Tariq Aziz",
        "role": "UI/UX Designer",
        "linkedin": "https://www.linkedin.com/in/tariqazizkhan",
        "email": "tariqaziz32492@gmail.com",
        "whatsapp": "923435024380",
    },
    {
        "name": "Saliha K",
        "role": "PRD Development & Documentation",
        "linkedin": "",                      # optional: shows N/A when absent
        "email": "skaa6005@gmail.com",
        "whatsapp": "923292094284",
    },
    {
        "name": "Qurrat Ul Ain",
        "role": "Documentation & Presentation",
        "linkedin": "https://www.linkedin.com/in/qurrat-ul-ain-2b633a3a3/",
        "email": "Khanasfand419@gmail.com",
        "whatsapp": "923339416149",
    },
    {
        "name": "Muhammad Faizan",
        "role": "Research & Analysis",
        "linkedin": "https://www.linkedin.com/in/muhammad-faizan-ba088836a",
        "email": "mfaizan663311@gmail.com",
        "whatsapp": "923100014196",
    },
]


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else name[:2].upper()


def _pretty_phone(digits: str) -> str:
    # 923326363256 -> +92 332 6363256
    if len(digits) == 12 and digits.startswith("92"):
        return f"+{digits[:2]} {digits[2:5]} {digits[5:]}"
    return f"+{digits}"


theme.setup("Team", icon="👥")
state.init_state()
components.sidebar_summary()

st.title("Team AgriNex")
st.caption(
    "AgriPilot AI was built for the hackathon by Team AgriNex. "
    "Get in touch about the project, the data, or working together."
)

st.markdown(
    f"""
<style>
  .ap-person {{
    background: {theme.SURFACE}; border: 1px solid {theme.BORDER};
    border-radius: 12px; padding: 1.2rem 1.3rem; height: 100%;
  }}
  .ap-person-head {{ display: flex; align-items: center; gap: 0.85rem; margin-bottom: 0.9rem; }}
  .ap-avatar {{
    width: 48px; height: 48px; border-radius: 50%; flex: 0 0 48px;
    background: {theme.PRIMARY}; color: #fff; font-weight: 650; font-size: 1.05rem;
    display: flex; align-items: center; justify-content: center;
  }}
  .ap-person-name {{ font-size: 1.1rem; font-weight: 650; color: {theme.TEXT}; line-height: 1.25; }}
  .ap-person-role {{ font-size: 0.85rem; color: {theme.MUTED}; }}
  .ap-contact {{ font-size: 0.9rem; line-height: 1.9; }}
  .ap-contact a {{ color: {theme.PRIMARY_DARK}; text-decoration: none; }}
  .ap-contact a:hover {{ text-decoration: underline; }}
  .ap-contact-label {{ color: {theme.MUTED}; display: inline-block; min-width: 82px; }}
</style>
""",
    unsafe_allow_html=True,
)

def _contact_rows(person: dict) -> str:
    """Render every contact line so all cards show the same rows.

    A missing entry shows a muted "N/A" rather than being dropped, which keeps
    the cards the same shape instead of one being a row shorter.
    """
    rows = []
    if person.get("linkedin"):
        handle = person["linkedin"].split("/in/")[-1].strip("/")
        rows.append(
            f'<span class="ap-contact-label">LinkedIn</span>'
            f'<a href="{person["linkedin"]}" target="_blank" rel="noopener">{handle}</a>'
        )
    else:
        rows.append(
            f'<span class="ap-contact-label">LinkedIn</span>'
            f'<span style="color:{theme.MUTED}">N/A</span>'
        )
    if person.get("email"):
        rows.append(
            f'<span class="ap-contact-label">Email</span>'
            f'<a href="mailto:{person["email"]}">{person["email"]}</a>'
        )
    if person.get("whatsapp"):
        rows.append(
            f'<span class="ap-contact-label">WhatsApp</span>'
            f'<a href="https://wa.me/{person["whatsapp"]}" target="_blank" rel="noopener">'
            f'{_pretty_phone(person["whatsapp"])}</a>'
        )
    return "<br>".join(rows)


PER_ROW = 3
for start in range(0, len(TEAM), PER_ROW):
    batch = TEAM[start:start + PER_ROW]
    # Pad the final row so a lone card does not stretch across the page.
    columns = st.columns(PER_ROW, gap="medium")
    for column, person in zip(columns, batch):
        with column:
            st.markdown(
                f"""
<div class="ap-person">
  <div class="ap-person-head">
    <div class="ap-avatar">{_initials(person['name'])}</div>
    <div>
      <div class="ap-person-name">{person['name']}</div>
      <div class="ap-person-role">{person['role']}</div>
    </div>
  </div>
  <div class="ap-contact">{_contact_rows(person)}</div>
</div>
""",
                unsafe_allow_html=True,
            )

st.markdown("")
st.markdown("---")
st.markdown("#### About the project")
st.markdown(
    "**AgriPilot AI** helps farmers decide whether a crop is suitable and financially "
    "viable on their land, before they commit money to it. It combines soil, water, "
    "climate and cost factors into one Farm Decision Score, explains the reasoning, and "
    "lets you test how the plan holds up when conditions change."
)
st.markdown(
    "Built for Pakistan: Punjab, Sindh, Khyber Pakhtunkhwa and Balochistan, in acres and PKR."
)

col_a, col_b = st.columns(2, gap="medium")
with col_a:
    if st.button("Try the Demo Farm", type="primary", use_container_width=True):
        with st.spinner("Running the demo farm analysis…"):
            state.load_demo_farm()
        st.switch_page("pages/2_Dashboard.py")
with col_b:
    st.link_button(
        "View the source on GitHub",
        "https://github.com/a-ali-tariq/AgriPilot-AI",
        use_container_width=True,
    )

components.disclaimer()

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
        "role": "Full Stack Developer",
        "expertise": "Full Stack Development · AWS & GCP Certified",
        "linkedin": "https://www.linkedin.com/in/amiralitariq/",
        "email": "amiralitariq@gmail.com",
        "whatsapp": "923326363256",
    },
    {
        "name": "Tariq Aziz",
        "role": "UI/UX Designer",
        "expertise": "UI/UX Design",
        "linkedin": "https://www.linkedin.com/in/tariqazizkhan",
        "email": "tariqaziz32492@gmail.com",
        "whatsapp": "923435024380",
    },
    {
        "name": "Saliha K",
        "role": "Product & Documentation",
        "expertise": "PRD Development · Documentation & Presentation",
        "linkedin": "",                      # optional: omitted rows are not rendered
        "email": "skaa6005@gmail.com",
        "whatsapp": "923292094284",
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

def _contact_rows(person: dict) -> str:
    """Only render the contact lines a member actually has."""
    rows = []
    if person.get("linkedin"):
        handle = person["linkedin"].split("/in/")[-1].strip("/")
        rows.append(("LinkedIn", person["linkedin"], handle))
    if person.get("email"):
        rows.append(("Email", f"mailto:{person['email']}", person["email"]))
    if person.get("whatsapp"):
        rows.append(("WhatsApp", f"https://wa.me/{person['whatsapp']}",
                     _pretty_phone(person["whatsapp"])))
    return "".join(
        f'<dt>{label}</dt><dd><a href="{href}" target="_blank" rel="noopener">{text}</a></dd>'
        for label, href, text in rows
    )


def _card(person: dict) -> str:
    return f"""
<article class="ap-person">
  <header class="ap-person-head">
    <span class="ap-avatar">{_initials(person['name'])}</span>
    <span>
      <span class="ap-person-name">{person['name']}</span>
      <span class="ap-person-role">{person['role']}</span>
    </span>
  </header>
  <p class="ap-person-expertise">{person['expertise']}</p>
  <dl class="ap-contact">{_contact_rows(person)}</dl>
</article>"""


# One grid rather than st.columns: columns cannot give cards equal heights, and a
# grid also wraps sensibly on a narrow screen instead of squeezing three abreast.
st.markdown(
    f"""
<style>
  .ap-team {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
    margin: 0.5rem 0 0.5rem;
  }}
  .ap-person {{
    display: flex; flex-direction: column;
    background: {theme.SURFACE}; border: 1px solid {theme.BORDER};
    border-radius: 12px; padding: 1.25rem;
  }}
  .ap-person-head {{
    display: flex; align-items: center; gap: 0.8rem;
    padding-bottom: 0.9rem; margin-bottom: 0.9rem;
    border-bottom: 1px solid {theme.BORDER};
  }}
  .ap-avatar {{
    width: 44px; height: 44px; border-radius: 50%; flex: 0 0 44px;
    background: {theme.PRIMARY}; color: #fff;
    font-weight: 600; font-size: 0.95rem; letter-spacing: 0.02em;
    display: flex; align-items: center; justify-content: center;
  }}
  .ap-person-name {{
    display: block; font-size: 1.02rem; font-weight: 650;
    color: {theme.TEXT}; line-height: 1.3;
  }}
  .ap-person-role {{ display: block; font-size: 0.85rem; color: {theme.MUTED}; }}
  .ap-person-expertise {{
    flex: 1 0 auto;                       /* pushes contacts to a common baseline */
    font-size: 0.86rem; line-height: 1.5; color: {theme.MUTED};
    margin: 0 0 1rem 0;
  }}
  .ap-contact {{
    display: grid; grid-template-columns: 5.5rem 1fr;
    row-gap: 0.4rem; column-gap: 0.5rem;
    margin: 0; font-size: 0.88rem;
  }}
  .ap-contact dt {{ color: {theme.MUTED}; }}
  .ap-contact dd {{ margin: 0; overflow-wrap: anywhere; }}
  .ap-contact a,
  .ap-contact a:visited {{ color: {theme.PRIMARY_DARK}; text-decoration: none; }}
  .ap-contact a:hover {{ text-decoration: underline; }}
</style>
<div class="ap-team">{''.join(_card(p) for p in TEAM)}</div>
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

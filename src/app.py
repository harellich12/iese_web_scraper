import streamlit as st
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database import Professor, Industry, Sector, professor_industries, professor_sectors, init_db

# Database connection
def get_db_session():
    Session = init_db()
    return Session()

st.set_page_config(page_title="IESE Faculty Explorer", layout="wide")

st.title("IESE Faculty Explorer")

session = get_db_session()

# Sidebar Filters
st.sidebar.header("Filters")

# Industry Filter
all_industries = session.query(Industry).all()
industry_names = [i.name for i in all_industries]
selected_industries = st.sidebar.multiselect("Select Industries", industry_names)

# Sector Filter
all_sectors = session.query(Sector).all()
sector_names = [s.name for s in all_sectors]
selected_sectors = st.sidebar.multiselect("Select Sectors", sector_names)

# Department Filter
all_departments = session.query(Professor.department).distinct().all()
dept_names = [d[0] for d in all_departments if d[0]]
selected_depts = st.sidebar.multiselect("Select Departments", dept_names)

# Query
query = session.query(Professor)

if selected_industries:
    query = query.join(Professor.industries).filter(Industry.name.in_(selected_industries))

if selected_sectors:
    query = query.join(Professor.sectors).filter(Sector.name.in_(selected_sectors))

if selected_depts:
    query = query.filter(Professor.department.in_(selected_depts))

professors = query.distinct().all()

st.write(f"Found {len(professors)} professors.")

# Display Grid
cols = st.columns(3)
for idx, prof in enumerate(professors):
    with cols[idx % 3]:
        with st.container(border=True):
            if prof.image_url:
                # Normalize path
                image_path = prof.image_url.replace("\\", "/")
                
                # Debugging
                import os
                if not os.path.exists(image_path):
                    st.error(f"Image not found: {image_path} (Original: {prof.image_url})")
                    st.write(f"CWD: {os.getcwd()}")
                    st.write(f"Abs path: {os.path.abspath(image_path)}")
                else:
                    st.image(image_path, width=150)
            st.subheader(prof.name)
            st.caption(prof.title)
            st.write(f"**Dept:** {prof.department}")
            
            industries = [i.name for i in prof.industries]
            if industries:
                st.write(f"**Industries:** {', '.join(industries)}")
            
            sectors = [s.name for s in prof.sectors]
            if sectors:
                st.write(f"**Sectors:** {', '.join(sectors)}")
            
            with st.expander("Bio"):
                st.write(prof.bio[:500] + "..." if prof.bio else "No bio available.")
                st.link_button("View Profile", prof.url)

session.close()

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

DB_FILE = "hospital_data.db"
ADMIN_PASSWORD = "admin123"
LOGO = "logo.jpeg"


st.set_page_config(page_title="SmartCare Dashboard", page_icon=LOGO, layout="wide")

# --- utility functions ---
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def read_table(name):
    conn = get_conn()
    df = pd.read_sql_query(f"SELECT * FROM {name}", conn)
    conn.close()
    return df

def exec_sql(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()
def generate_mrd():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM patients")
    count = cur.fetchone()[0] + 1
    conn.close()
    return f"MRD-{count:04d}"

# --- header styles ---
st.markdown("""
    <style>
        /* Global Reset */
        [data-testid="stAppViewContainer"] {
            background: #f8fafc;
        }
        [data-testid="stHeader"] {display:none;}
        [data-testid="stToolbar"] {display:none;}

        /* Typography */
        html, body, [class*="css"]  {
            font-family: 'Segoe UI', sans-serif;
        }

        /* Main Title Section */
        .smartcare-header {
            display:flex;
            align-items:center;
            justify-content:space-between;
            background: linear-gradient(90deg, #3b82f6, #06b6d4);
            color:white;
            padding:1rem 2rem;
            border-radius:12px;
            box-shadow:0 4px 12px rgba(0,0,0,0.1);
            margin-bottom:1rem;
        }
        .smartcare-header h1 {
            font-size:1.8rem;
            font-weight:700;
            margin:0;
        }
        .smartcare-header p {
            font-size:1rem;
            opacity:0.9;
            margin:0;
        }

        /* Navigation bar */
        div[role='radiogroup'] > label {
            background:#ffffff;
            padding:0.5rem 1rem;
            border-radius:8px;
            box-shadow:0 1px 4px rgba(0,0,0,0.08);
            transition: all 0.2s ease;
            border:1px solid #e2e8f0;
        }
        div[role='radiogroup'] > label:hover {
            background:#e0f2fe;
            cursor:pointer;
            transform:translateY(-2px);
        }
        div[role='radiogroup'] {
            display:flex;
            justify-content:center;
            gap:0.5rem;
            flex-wrap:wrap;
            margin-bottom:1.5rem;
        }

        /* KPI Cards */
        .metric-card {
            background:white;
            border-radius:16px;
            padding:1.5rem;
            text-align:center;
            box-shadow:0 2px 10px rgba(0,0,0,0.06);
            transition: all 0.2s ease;
        }
        .metric-card:hover {
            transform:translateY(-3px);
            box-shadow:0 4px 12px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size:2rem;
            font-weight:700;
            color:#0f172a;
        }
        .metric-label {
            color:#64748b;
            font-size:1rem;
        }

        /* Tables */
        .stDataFrame {
            border-radius:8px;
            overflow:hidden;
        }

        /* Section titles */
        h3, h4 {
            color:#0f172a;
            font-weight:600;
        }
    </style>
""", unsafe_allow_html=True)

# --- Header ---
col1, col2 = st.columns([1,6])
with col1:
    st.image(LOGO, width=90)
with col2:
    st.markdown("""
        <div class="smartcare-header">
            <div>
                <h1>SmartCare Dashboard</h1>
                <p>Hospital Resource Optimization & Analytics</p>
            </div>
        </div>
    """, unsafe_allow_html=True)


# --- navigation ---
nav = st.radio("", ["Dashboard", "Department Utilization", "Patient Analytics",
                    "Data Filtering & Search", "Staff Tools", "Hospital Admin",
                    "About Us", "Contact Us"], horizontal=True)

# --- load data ---
try:
    patients = read_table("patients")
    beds = read_table("beddetails")
    users = read_table("users")
except Exception as e:
    st.error(f"Database not found or invalid. Run create_database.py first.\n\n{e}")
    st.stop()

# --- helper ---
def dept_summary():
    df = beds.copy()
    occ = df[df["occupied"]=="YES"].groupby("department").size().reset_index(name="occupied")
    total = df.groupby("department").size().reset_index(name="total")
    merged = total.merge(occ, on="department", how="left").fillna(0)
    merged["vacant"] = merged["total"] - merged["occupied"]
    merged["occupancy_rate"] = (merged["occupied"]/merged["total"]*100).round(1)
    return merged

# === Dashboard ===
if nav == "Dashboard":
    st.markdown("### 🏥 Hospital Overview")
    total_beds = len(beds)
    occ_beds = len(beds[beds.occupied=="YES"])
    today = datetime.now().date()

    today_adm = len(patients[patients["doa"].astype(str).str.startswith(str(today))]) if "doa" in patients else 0
    today_dis = len(patients[patients["dod"].astype(str).str.startswith(str(today))]) if "dod" in patients else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-label'>Total Beds</div><div class='metric-value'>{total_beds}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-label'>Total Admissions (Today)<div class='metric-value'>{today_adm}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-label'>Total Discharges (Today)<div class='metric-value'>{today_dis}</div></div>", unsafe_allow_html=True)
    if "duration_of_stay" in patients.columns and not patients.empty:
        avg_stay = patients["duration_of_stay"].astype(float).mean()
    else:
        avg_stay = 0
    c4.markdown(f"<div class='metric-card'><div class='metric-label'>Avg. Length of Stay<div class='metric-value'>{avg_stay:.1f} days</div></div>", unsafe_allow_html=True)

      # Charts
    st.markdown("#### Admissions vs Discharges (Last 7 Days)")
    if "doa" in patients.columns:
        df = patients.copy()
        df["doa_dt"] = pd.to_datetime(df["doa"], errors="coerce")
        df["dod_dt"] = pd.to_datetime(df["dod"], errors="coerce")
        days = pd.date_range(datetime.now() - pd.Timedelta(days=6), datetime.now())
        adm = df.groupby(df["doa_dt"].dt.date).size().reindex(days.date, fill_value=0)
        dis = df.groupby(df["dod_dt"].dt.date).size().reindex(days.date, fill_value=0)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=days, y=adm, name="Admissions", mode="lines+markers", line=dict(color="#3b82f6")))
        fig.add_trace(go.Scatter(x=days, y=dis, name="Discharges", mode="lines+markers", line=dict(color="#10b981")))
        st.plotly_chart(fig, use_container_width=True, key="chart1")

    st.markdown("#### Department Occupancy Overview")
    du = dept_summary()
    fig2 = px.pie(du, values="occupied", names="department", title="Current Department Occupancy")
    st.plotly_chart(fig2, use_container_width=True, key="chart2")

# ========================
# 2️⃣ DEPARTMENT UTILIZATION
# ========================
elif nav == "Department Utilization":
    st.markdown("### 🧭 Department Utilization Summary")
    du = dept_summary()
    st.dataframe(du, use_container_width=True)
    fig = px.bar(du, x="department", y="occupancy_rate", color="department", text="occupancy_rate")
    st.plotly_chart(fig, use_container_width=True, key="chart3")

# ========================
# 3️⃣ PATIENT ANALYTICS
# ========================
elif nav == "Patient Analytics":
    st.markdown("### 👩‍⚕️ Patient Analytics (All Columns Visualized)")
    for i, col in enumerate(patients.columns):
        st.markdown(f"#### 📊 {col}")
        series = patients[col].dropna()
        if pd.api.types.is_numeric_dtype(series):
            fig = px.histogram(patients, x=col, nbins=20, color_discrete_sequence=["#2563eb"])
        else:
            counts = series.value_counts().head(15)
            dfc = pd.DataFrame({"Category": counts.index.astype(str), "Count": counts.values})
            fig = px.bar(dfc, x="Category", y="Count", color_discrete_sequence=["#0ea5e9"])
            fig.update_xaxes(categoryorder="total descending")
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}")


# === Data Filtering & Search ===
elif nav == "Data Filtering & Search":
    st.markdown("### 🔍 Data Filtering and Search")
    key = st.text_input("Search by MRD, SNO, or Department")
    if st.button("Search"):
        df = patients.copy()
        if key:
            result = df[
                (df["mrd_no"].astype(str).str.contains(key, case=False, na=False)) |
                (df["sno"].astype(str).str.contains(key, case=False, na=False)) |
                (df["department"].astype(str).str.contains(key, case=False, na=False)) if "department" in df.columns else False
            ]
            st.dataframe(result if not result.empty else pd.DataFrame(["No match found"], columns=["Message"]))
    st.markdown("#### Advanced Column Filters")
    if not patients.empty:
        cols = st.multiselect("Select columns to filter", patients.columns.tolist())
        query = patients.copy()
        for c in cols:
            vals = st.multiselect(f"Select values for {c}", sorted(patients[c].dropna().unique().tolist()))
            if vals: query = query[query[c].isin(vals)]
        st.dataframe(query, use_container_width=True)

elif nav == "Staff Tools":

    st.markdown("### 🧑‍⚕️ Staff Tools (Add / Edit / Discharge)")

    
    # --- Add New Patient Section ---
    st.markdown("<div class='section-title'>➕ Add New Patient</div>", unsafe_allow_html=True)
    with st.form("add_patient_form"):
        name = st.text_input("Patient Name *")
        gender = st.selectbox("Gender *", ["Male","Female","Other"])
        age = st.number_input("Age *", 0, 120, 30)
        dept = st.text_input("Department *", value="General")
        doa = datetime.now().strftime("%Y-%m-%d")

        # Optional Medical Details
        with st.expander("🩺 Additional Details (Optional)"):
            smoking = st.selectbox("Smoking", ["Yes","No",""])
            alcohol = st.selectbox("Alcohol", ["Yes","No",""])
            hb = st.text_input("HB")
            tlc = st.text_input("TLC")
            platelets = st.text_input("Platelets")
            glucose = st.text_input("Glucose")
            anaemia = st.selectbox("Anaemia", ["Yes","No",""])
            heart_failure = st.selectbox("Heart Failure", ["Yes","No",""])
            uti = st.selectbox("UTI", ["Yes","No",""])
            chest_infection = st.selectbox("Chest Infection", ["Yes","No",""])

        add_btn = st.form_submit_button("Add Patient")

    if add_btn:
        if not name or not dept or not gender or age <= 0:
            st.error("❌ Please fill in all mandatory fields (Name, Age, Gender, Department).")
        else:
            free = beds[(beds["department"] == dept) & (beds["occupied"] == "NO")]
            if free.empty:
                st.error("❌ No empty bed available in this department!")
            else:
                mrd = generate_mrd()
                bed_id = free.iloc[0]["bed_serial"]
                doa_time = datetime.now().isoformat()

                exec_sql("""
                    INSERT INTO patients 
                    (mrd_no, doa, gender, age, department, outcome, smoking, alcohol, hb, tlc, platelets, glucose, anaemia, heart_failure, uti, chest_infection)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (mrd, doa_time, gender, age, dept, "Admitted", smoking, alcohol, hb, tlc, platelets, glucose, anaemia, heart_failure, uti, chest_infection))

                conn = get_conn()
                cur = conn.cursor()
                cur.execute("SELECT sno FROM patients WHERE mrd_no=?", (mrd,))
                sno = cur.fetchone()[0]
                conn.close()

                exec_sql("UPDATE beddetails SET occupied='YES', patient_sno=? WHERE bed_serial=?", (sno, bed_id))

                st.success(f"✅ Patient {name} added (MRD: {mrd}) and assigned to {bed_id}")

    # --- Discharge / Edit Patient Section ---
    st.markdown("#### 🏥 Discharge or Edit Patient")

    sno = st.number_input("Enter Patient SNO", 1)

    if st.button("Discharge"):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT bed_serial FROM beddetails WHERE patient_sno=?", (sno,))
        row = cur.fetchone()

        if row:
            exec_sql("UPDATE beddetails SET occupied='NO', patient_sno=NULL WHERE bed_serial=?", (row[0],))
            exec_sql("UPDATE patients SET outcome='Discharged', dod=? WHERE sno=?", (datetime.now().isoformat(), sno))
            st.success("🟢 Patient discharged successfully and bed released!")
        else:
            st.warning("⚠️ No bed linked to this patient")


# === Hospital Admin ===
elif nav == "Hospital Admin":
    st.markdown("### 🏗️ Hospital Admin Panel")
    pwd = st.text_input("Admin Password", type="password")
    if pwd == ADMIN_PASSWORD:
        st.success("Access Granted ✅")

        # ----------- ADD EXTRA BEDS -----------
        st.markdown("#### ➕ Add Extra Beds")
        dept = st.text_input("Department", "General", key="add_bed_dept")
        n = st.number_input("Beds to Add", 1, 100, 1, key="add_bed_n")
        if st.button("Add Beds", key="add_beds_btn"):
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM beddetails")
            base = cur.fetchone()[0]
            for i in range(n):
                bed_serial = f"BED-{base + i + 1:04d}"
                cur.execute("INSERT INTO beddetails (bed_serial, occupied, department) VALUES (?, 'NO', ?)", (bed_serial, dept))
            conn.commit(); conn.close()
            st.success(f"✅ Added {n} new beds to {dept} department.")

        # ----------- EDIT PATIENT DETAILS -----------
        st.markdown("#### 🩺 Edit Patient Details")
        sno = st.number_input("Patient SNO to Edit", 1, key="admin_edit_sno")
        if st.button("Load Details", key="load_patient_btn"):
            import pandas as pd
            conn = get_conn()
            patient_df = pd.read_sql_query(f"SELECT * FROM patients WHERE sno={sno}", conn)
            conn.close()

            if not patient_df.empty:
                patient_data = patient_df.iloc[0].to_dict()

                with st.form("edit_patient_form"):
                    # Locked fields
                    st.text_input("MRD No (Locked)", value=patient_data.get("mrd_no",""), disabled=True)
                    st.text_input("Name (Locked)", value=patient_data.get("name",""), disabled=True)
                    st.number_input("Age (Locked)", value=int(patient_data.get("age",0)), disabled=True)
                    st.text_input("DOA (Locked)", value=patient_data.get("doa",""), disabled=True)

                    # Editable fields
                    editable_fields = [
                        "dod", "department", "type_of_admission", "outcome",
                        "smoking", "alcohol", "hb", "tlc", "platelets", "glucose",
                        "anaemia", "heart_failure", "uti", "chest_infection"
                    ]
                    updated_values = {}
                    for field in editable_fields:
                        val = patient_data.get(field,"")
                        if field in ["hb","tlc","platelets","glucose"]:
                            updated_values[field] = st.number_input(field.upper(), value=float(val) if val else 0.0, key=f"admin_{field}")
                        elif field in ["smoking","alcohol","anaemia","heart_failure","uti","chest_infection"]:
                            updated_values[field] = st.selectbox(field.replace("_"," ").title(), ["","Yes","No"], index=["","Yes","No"].index(val) if val in ["Yes","No"] else 0, key=f"admin_{field}")
                        elif field == "department":
                            updated_values[field] = st.selectbox("Department", ["General","ICU","Pediatrics","Maternity","Surgery"], index=["General","ICU","Pediatrics","Maternity","Surgery"].index(val) if val in ["General","ICU","Pediatrics","Maternity","Surgery"] else 0)
                        elif field == "type_of_admission":
                            updated_values[field] = st.selectbox("Type of Admission", ["Routine","Emergency"], index=["Routine","Emergency"].index(val) if val in ["Routine","Emergency"] else 0)
                        elif field == "outcome":
                            updated_values[field] = st.selectbox("Outcome", ["Admitted","Discharged","Deceased"], index=["Admitted","Discharged","Deceased"].index(val) if val in ["Admitted","Discharged","Deceased"] else 0)
                        else:  # dod
                            updated_values[field] = st.text_input("Date of Discharge (DOD)", value=val, key=f"admin_{field}")

                    save = st.form_submit_button("Save Changes", key="admin_save_changes")

                    if save:
                        try:
                            conn = get_conn(); cur = conn.cursor()
                            # Update patients table
                            set_clause = ", ".join([f"{col}=?" for col in updated_values])
                            values = [updated_values[col] for col in updated_values]
                            values.append(sno)
                            cur.execute(f"UPDATE patients SET {set_clause} WHERE sno=?", values)
                            conn.commit()

                            # Update beddetails if department changed
                            if updated_values.get("department") != patient_data.get("department"):
                                cur.execute("UPDATE beddetails SET department=? WHERE patient_sno=?", (updated_values["department"], sno))
                                conn.commit()

                            # Recalculate duration_of_stay
                            if updated_values.get("dod") and patient_data.get("doa"):
                                try:
                                    doa = datetime.strptime(patient_data["doa"], "%Y-%m-%d")
                                    dod = datetime.strptime(updated_values["dod"], "%Y-%m-%d")
                                    duration = (dod - doa).days
                                    cur.execute("UPDATE patients SET duration_of_stay=? WHERE sno=?", (duration, sno))
                                    conn.commit()
                                except:
                                    pass

                            conn.close()
                            st.success("✅ Patient record updated successfully!")

                        except Exception as e:
                            st.error(f"❌ Error updating patient: {e}")
            else:
                st.warning("⚠️ Patient not found.")

    elif pwd:
        st.error("❌ Incorrect password.")


# === About Us / Contact Us ===
elif nav == "About Us":
    st.markdown("### 💡 About SmartCare")
    st.write("SmartCare Dashboard is an intelligent hospital analytics system built with Streamlit, offering live insights, patient management, and bed optimization.")

elif nav == "Contact Us":
    st.markdown("### 📬 Contact Us")
    with st.form("contact_form"):
        n = st.text_input("Your Name")
        e = st.text_input("Email")
        m = st.text_area("Message")
        s = st.form_submit_button("Send Message")
    if s:
        st.success("Message sent (Demo Mode).")
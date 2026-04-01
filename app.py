import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import io
import re
import tempfile
import os
from groq import Groq
from fpdf import FPDF
from dotenv import load_dotenv

# Load environment variables (for local development)
load_dotenv()

# --- 1. THEME & CONFIG ---
st.set_page_config(page_title="Code Audit AI Pro", layout="wide")

st.markdown("""
    <style>
    /* Create a fixed background layer that doesn't interfere with content */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url('https://img.freepik.com/free-vector/zero-one-binary-number-system-white-background-design_1017-52479.jpg');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        filter: blur(8px);  
        z-index: -1;     
    }

    /* Keep the main content area clean */
    .stApp {
        background: transparent;
    }
    
    .main { background: rgba(30, 30, 30, 0.8); color: #e6edf3; border-radius: 10px; padding: 10px; }
    .stButton>button { border-radius: 5px; height: 3em; transition: 0.3s; }
    .stButton>button:hover { border: 1px solid #58a6ff; box-shadow: 0 0 10px #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

# Get API key from environment variable OR Streamlit secrets
# Priority: Streamlit secrets > .env file
if hasattr(st, 'secrets') and 'GROQ_API_KEY' in st.secrets:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
else:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("""
    ❌ **GROQ_API_KEY not found!** 
    
    **For Streamlit Cloud:**
    1. Go to your app dashboard
    2. Click on "Settings" → "Secrets"
    3. Add your API key as: `GROQ_API_KEY = "your-api-key-here"`
    
    **For Local Development:**
    Create a `.env` file with: `GROQ_API_KEY=your-api-key-here`
    """)
    st.stop()

if "analysis" not in st.session_state: 
    st.session_state.analysis = None
if "pending_code" not in st.session_state: 
    st.session_state.pending_code = None

# --- 2. ANALYTICS & PDF LOGIC ---
class AuditPDF(FPDF):
    def header(self):
        self.set_font("Courier", "B", 16)
        self.set_text_color(88, 166, 255)
        self.cell(190, 10, "TECHNICAL CODE AUDIT REPORT", 0, 1, "C")
        self.ln(5)

def create_final_pdf(data, plot_buf):
    pdf = AuditPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "1. User Input Snippet", 0, 1)
    pdf.set_font("Courier", "", 9)
    pdf.multi_cell(180, 5, str(data['original_code']))
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "2. Optimized & Structured Code ", 0, 1)
    pdf.set_font("Courier", "", 9)
    pdf.multi_cell(180, 5, str(data['annotated_code']))
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "3. Improvement Points", 0, 1)
    pdf.set_font("Arial", "", 10)
    for fix in data.get('fixes', []): 
        pdf.multi_cell(180, 6, f"- {fix}")
    
    pdf.add_page()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(plot_buf.getvalue())
        tmp_path = tmp.name
    pdf.image(tmp_path, x=15, w=170)
    os.unlink(tmp_path)
    return pdf.output(dest='S').encode('latin-1')

def complexity_score(comp):
    c = str(comp).lower()
    if "1" in c: 
        return 100
    if "log" in c: 
        return 85
    if "n" in c and "^" not in c: 
        return 70
    return 40

# --- 3. AUDIT ENGINE ---
def run_audit(code, language):
    client = Groq(api_key=GROQ_API_KEY)
    prompt = f"""Correct this code for {language}. If it's a snippet like 'write(x)', wrap it in full class/main structure.
    Return JSON: {{
        "annotated_code": "Full code", "fixes": ["point 1"],
        "metrics": {{"Accuracy": 95, "Efficiency": 90, "Time": "O(1)", "Space": "O(1)"}},
        "orig_metrics": {{"Accuracy": 20, "Efficiency": 10, "Time": "N/A", "Space": "N/A"}}
    }}
    Input: {code}"""
    
    chat = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"}
    )
    res = json.loads(chat.choices[0].message.content)
    res['original_code'] = code
    res['annotated_code'] = res['annotated_code'].replace("\\n", "\n")
    return res

# --- 4. UI ---
st.title("💻 Code Annotation AI Pro")

c1, c2 = st.columns([1, 1.2])

with c1:
    st.subheader("📥 Source Code")
    user_input = st.text_area("Paste Code or Snippet", height=300)
    if st.button("🔍 Analyze Snippet", use_container_width=True):
        if user_input:
            st.session_state.pending_code = user_input
            st.session_state.analysis = None

    if st.session_state.pending_code:
        st.info("💡 Select target language to generate full structure:")
        b1, b2, b3 = st.columns(3)
        if b1.button("☕ Java"):
            with st.spinner("Analyzing Java code..."):
                st.session_state.analysis = run_audit(st.session_state.pending_code, "Java")
                st.session_state.pending_code = None
                st.rerun()
        if b2.button("⚙️ C++"):
            with st.spinner("Analyzing C++ code..."):
                st.session_state.analysis = run_audit(st.session_state.pending_code, "C++")
                st.session_state.pending_code = None
                st.rerun()
        if b3.button("🐍 Python"):
            with st.spinner("Analyzing Python code..."):
                st.session_state.analysis = run_audit(st.session_state.pending_code, "Python")
                st.session_state.pending_code = None
                st.rerun()

with c2:
    if st.session_state.analysis:
        res = st.session_state.analysis
        tab1, tab2 = st.tabs(["📝 Result", "📊 Analytics"])
        
        with tab1:
            for f in res.get('fixes', []): 
                st.markdown(f"✅ {f}")
            st.code(res['annotated_code'], language='java' if 'java' in res['annotated_code'].lower() else 'python')
            
        with tab2:
            # Comparative Line Graph
            labels = ["Accuracy", "Efficiency", "Time Score", "Space Score"]
            orig = [res['orig_metrics']['Accuracy'], res['orig_metrics']['Efficiency'], 
                    complexity_score(res['orig_metrics']['Time']), complexity_score(res['orig_metrics']['Space'])]
            fixed = [res['metrics']['Accuracy'], res['metrics']['Efficiency'], 
                     complexity_score(res['metrics']['Time']), complexity_score(res['metrics']['Space'])]
            
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(8, 4))
            fig.patch.set_facecolor('#0e1117')
            ax.plot(labels, orig, marker='o', label='Original Snippet', color='#ff7b72', linewidth=2)
            ax.plot(labels, fixed, marker='s', label='Optimized Code', color='#58a6ff', linewidth=2)
            ax.set_ylim(0, 110)
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            
            # PDF Download
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            pdf_bytes = create_final_pdf(res, buf)
            st.download_button(
                "📥 Download PDF Report", 
                data=pdf_bytes, 
                file_name="Code_Audit_Report.pdf",
                mime="application/pdf"
            )
    elif not st.session_state.pending_code:
        st.info("👈 Paste your code and click 'Analyze Snippet' to begin.")
        st.markdown('''
<div style="background-image: linear-gradient(135deg, #0d1117 0%, #161b22 100%); color: #e6edf3; padding: 15px; border-radius: 10px; border: 1px solid #30363d; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 13px;">
    <h2 style="color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 8px; margin-top: 0; font-size: 16px;">
        💻 Code Annotation AI Pro: Core Capabilities
    </h2>
    <ul style="line-height: 1.6; list-style-type: none; padding-left: 0; margin-bottom: 0;">
        <li style="margin-bottom: 8px;">
            <strong>🔹 Syntax & Case Correction:</strong> Automatically fixes common Java errors like <code>string</code> to <code>String</code> and <code>Class</code> to <code>class</code> while respecting proper access modifiers.
        </li>
        <li style="margin-bottom: 8px;">
            <strong>🔹 Logical Loop Optimization:</strong> Identifies and corrects "off-by-one" errors in algorithms, such as adjusting Fibonacci sequences to match user-requested counts accurately.
        </li>
        <li style="margin-bottom: 8px;">
            <strong>🔹 Static Resource Management:</strong> Ensures <code>Scanner</code> objects and static variables are correctly initialized and scoped within the <code>main</code> method for error-free execution.
        </li>
        <li style="margin-bottom: 8px;">
            <strong>🔹 Big O Complexity Auditing:</strong> Analyzes code to determine <strong>Time ($O(n)$)</strong> and <strong>Space ($O(1)$)</strong> complexity, providing a technical baseline for performance.
        </li>
        <li style="margin-bottom: 8px;">
            <strong>🔹 Comparative Performance Plotting:</strong> Generates line graphs that map abstract complexity into numeric scores to visualize the efficiency jump between original and optimized code.
        </li>
        <li style="margin-bottom: 8px;">
            <strong>🔹 Illegal Character Filtering:</strong> Strips literal <code>\n</code> strings and unwanted backslashes from AI responses to ensure the final code is 100% ready for the Java compiler.
        </li>
        <li style="margin-bottom: 8px;">
            <strong>🔹 Automated Document Generation:</strong> Compiles the original code, refactored logic, bulleted fixes, and performance charts into a structured, professional PDF report.
        </li>
        <li style="margin-bottom: 8px;">
            <strong>🔹 Input Validation Injection:</strong> Automatically adds safety checks to prevent <code>TypeMismatch</code> or <code>NoSuchElement</code> exceptions when processing user input.
        </li>
        <li style="margin-bottom: 8px;">
            <strong>🔹 Code Creator:</strong> Write the code name or case to build the <code>code/logic</code> automatically gives logic based on matched senarios.
        </li>
    </ul>
</div>
        ''', unsafe_allow_html=True)

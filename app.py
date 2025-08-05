# AI Interview Prep Bot v2 with 5 Rounds and Feedback per Question
import streamlit as st
import fitz  # PyMuPDF
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import re
import datetime

# ================= Streamlit Config =================
st.set_page_config(page_title="Dino AI Interview Prep Bot", layout="centered")
st.markdown("""
<style>
/* Background Gradient */
body {
    background: linear-gradient(to right, #89f7fe, #66a6ff); /* light blue to sky blue */
}
.stApp {
    background: linear-gradient(to right, #89f7fe, #66a6ff);
    padding: 10px;
    color: #000000 !important;
    font-family: 'Times New Roman', Times, serif !important;
}

/* Header */

    .header {
        text-align: center;
        font-size: 40px;
        font-weight: bold;
        background: linear-gradient(to right, #ff6a00, #ee0979, #8e2de2, #4a00e0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Segoe UI', sans-serif;
        margin-bottom: 20px;
    }

/* Footer */
.footer {
    margin-top: 50px;
    font-size: 16px;
    color: #ffffff;
    text-align: center;
    background-color: #222222;
    padding: 20px;
    border-radius: 10px;
}
.footer a {
    color: #1da1f2;
    text-decoration: none;
}
.footer a:hover {
    text-decoration: underline;
}

/* Force black font for labels, options, inputs */
label, .stTextInput, .stTextArea, .stSelectbox, .stRadio, .stButton, .stMarkdown, .stCheckbox, .stSubheader, .stInfo {
    color: #000000 !important;
    font-family: 'Times New Roman', Times, serif !important;
}

/* Force black for radio buttons and options */
[data-baseweb="radio"] label {
    color: #000000 !important;
}

/* Black font in input and text area */
input, textarea {
    color: #000000 !important;
    background-color: #fffaf0 !important;
}

/* Fix for buttons having weird color contrast */
button[kind="primary"] {
    color: #000000 !important;
    background-color: #ffcc99 !important;
    border: 1px solid #000000 !important;
}
</style>

""", unsafe_allow_html=True)

st.markdown('<div class="header">🦕 Prepare with Dino</div>', unsafe_allow_html=True)

# ================= Usage Tracking =================
if "usage_date" not in st.session_state:
    st.session_state.usage_date = str(datetime.date.today())
if "daily_usage" not in st.session_state or st.session_state.usage_date != str(datetime.date.today()):
    st.session_state.daily_usage = 0
    st.session_state.usage_date = str(datetime.date.today())
DAILY_LIMIT = 50
st.info(f"📊 API usage today: {st.session_state.daily_usage} / {DAILY_LIMIT}")

# ================= Helper Functions =================
def extract_text(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

def extract_tags(resume_text):
    tags = []
    if any(x in resume_text.lower() for x in ["full stack", "html", "css", "javascript", "react"]):
        tags.append("Full Stack")
    if any(x in resume_text.lower() for x in ["data science", "machine learning", "deep learning"]):
        tags.append("Data Science")
    if any(x in resume_text.lower() for x in ["cybersecurity", "network security"]):
        tags.append("Cybersecurity")
    return ", ".join(tags) if tags else "General Tech"

def generate_llm_questions(resume_text, jd_text, round_type):
    if st.session_state.daily_usage >= DAILY_LIMIT:
        st.warning("🚫 Daily question generation limit reached. Please try again tomorrow.")
        return []

    tags = extract_tags(resume_text)

    if round_type == "Aptitude + Verbal":
        prompt_text = aptitude_prompt
    elif round_type == "Logical Reasoning":
        prompt_text = logical_prompt
    elif round_type == "Technical MCQ":
        prompt_text = tech_mcq_prompt
    elif round_type == "Technical Theory":
        prompt_text = tech_theory_prompt
    elif round_type == "HR":
        prompt_text = hr_prompt
    else:
        return []

    selected_prompt = ChatPromptTemplate.from_template(prompt_text)

    for attempt in range(2):
        try:
            chain = LLMChain(llm=llm, prompt=selected_prompt)
            result = chain.run({
                "resume": resume_text,
                "jd": jd_text,
                "round_type": round_type + f" | Tags: {tags}"
            })
            st.session_state.daily_usage += 1

            if not result or not isinstance(result, str) or not result.strip():
                raise ValueError("Empty or invalid response")

            if round_type in ["Technical MCQ", "Aptitude + Verbal", "Logical Reasoning"]:
                parsed = parse_mcqs(result)
                if parsed and len(parsed) >= 5:
                    return parsed[:10]
            else:
                questions = [line.strip("Q: ").strip() for line in result.strip().split("\n") if line.strip() and (line.endswith("?") or line.startswith("Q"))]
                if questions:
                    return [{"question": q} for q in questions]
        except Exception as e:
            if attempt == 1:
                st.error(f"❌ LLM retry failed: {e}")
            continue
    st.warning("⚠️ Could not parse enough MCQs after retry.")
    return []

def parse_mcqs(raw_text):
    questions = []
    blocks = re.split(r"\n\d+[\.:]?|\nQ[\.:]?", raw_text)
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 6:
            continue
        q_text = lines[0].strip()
        options = {}
        for line in lines[1:5]:
            if line.strip()[:2] in ["A.", "B.", "C.", "D."]:
                options[line.strip()[0]] = line.strip()[3:].strip()
        answer_line = next((line for line in lines if "Answer:" in line), "")
        explanation_line = next((line for line in lines if "Explanation:" in line), "")
        if not answer_line or not explanation_line or not options or len(options) < 4:
            continue
        correct = re.findall(r"Answer:\s*([A-D])", answer_line)
        correct = correct[0] if correct else ""
        explanation = explanation_line.split(":", 1)[-1].strip()
        questions.append({"question": q_text, "options": options, "answer": correct, "explanation": explanation})
    return questions

def evaluate_open_answer(question, answer, round_type):
    if not answer.strip():
        return "✋ Please enter your answer.", "N/A"

    feedback_template = ChatPromptTemplate.from_template("""
You are an expert interviewer.
Evaluate the candidate's answer to the following {round_type} interview question.
Give suggestions for improvement but do not include any numeric rating.

Question: {question}
Answer: {answer}

Suggestions:
""")
    try:
        chain = LLMChain(llm=llm, prompt=feedback_template)
        result = chain.run({"question": question, "answer": answer, "round_type": round_type})
        return result.strip(), "N/A"
    except Exception as e:
        return f"⚠️ Evaluation failed: {e}", "N/A"

# ================= LangChain LLM Setup =================
groq_api_key = st.secrets["groq"]["api_key"]
llm = ChatGroq(api_key=groq_api_key, model_name="llama3-70b-8192")

# Prompts
strict_mcq_prompt = """
You are an expert interview question generator.

Your task is to generate exactly 10 multiple-choice questions for a {round_type} interview based on the candidate’s resume and job description.

### Format:
Q: [The question]
A. [Option A]
B. [Option B]
C. [Option C]
D. [Option D]
Answer: [Correct option letter only, like A]
Explanation: [Brief explanation in 1–2 lines]

Ensure that:
- Questions cover real-world concepts from {round_type}
- For Technical MCQ: Focus on programming concepts (Python, SQL, ML, etc.)
- For Aptitude + Verbal: Mix of quant, time-speed, age problems, synonyms, antonyms, grammar
- For Logical: Include patterns, next number/letter, seating arrangements
- Answer and Explanation must always be included

Resume:
{resume}

JD:
{jd}
"""

aptitude_prompt = strict_mcq_prompt
logical_prompt = strict_mcq_prompt
tech_mcq_prompt = strict_mcq_prompt

tech_theory_prompt = """
You are a technical HR interviewer.
Generate 15 open-ended theory-based questions on languages and domains mentioned in resume (like Python, SQL, ML, etc.).
Resume: {resume}
JD: {jd}
"""

hr_prompt = """
You are an HR expert. Generate 15 HR questions focused on communication, attitude, motivation, goals, and leadership.
Format:
Q: Question?
"""

# ================= Session State Init =================
if "questions" not in st.session_state:
    st.session_state.questions = []
if "submitted" not in st.session_state:
    st.session_state.submitted = set()
if "score" not in st.session_state:
    st.session_state.score = 0

# ================= UI =================
resume_file = st.file_uploader("📄 Upload Resume (PDF)", type="pdf")
jd_text = st.text_area("📌 Paste Job Description (Optional)")
round_options = ["HR", "Technical Theory", "Technical MCQ", "Aptitude + Verbal", "Logical Reasoning"]
round_type = st.selectbox("🎯 Select Round", options=round_options, index=0)

if resume_file:
    resume_text = extract_text(resume_file)
    st.text_area("📜 Resume Text", resume_text, height=200)
    if st.button("🔁 Generate Questions", key="generate_btn"):
        with st.spinner("Generating questions..."):
            st.session_state.questions = generate_llm_questions(resume_text, jd_text, round_type)
            st.session_state.submitted = set()
            st.session_state.score = 0
        st.info("❗ If an error occurs, please refresh the page and try again.")

if st.session_state.questions:
    st.subheader(f"🧠 {round_type} Questions")

    for idx, q_obj in enumerate(st.session_state.questions):
        st.markdown(f"**Q{idx+1}. {q_obj['question']}**")

        if round_type in ["Technical MCQ", "Aptitude + Verbal", "Logical Reasoning"]:
            selected = st.radio("", list(q_obj["options"].values()), key=f"opt_{idx}", label_visibility="collapsed")
            if idx not in st.session_state.submitted:
                if st.button(f"Submit Answer {idx+1}", key=f"btn_{idx}"):
                    st.session_state.submitted.add(idx)
                    correct = q_obj['answer']
                    correct_text = q_obj['options'][correct]
                    st.session_state[f"correct_text_{idx}"] = correct_text
                    st.session_state[f"correct_option_{idx}"] = correct
                    st.session_state[f"explanation_{idx}"] = q_obj["explanation"]

                    if selected == correct_text:
                        st.session_state.score += 1
                    st.rerun()
            elif idx in st.session_state.submitted:
                st.markdown(f"✅ **Answer:** {st.session_state[f'correct_option_{idx}']}. {st.session_state[f'correct_text_{idx}']}")
                st.markdown(f"🧠 **Explanation:** {st.session_state[f'explanation_{idx}']}")

        else:
            user_input = st.text_area("✍️ Your Answer:", key=f"ans_{idx}", height=100)
            if idx not in st.session_state.submitted:
                if st.button(f"Submit Answer {idx+1}", key=f"btn_{idx}"):
                    feedback, _ = evaluate_open_answer(q_obj['question'], user_input, round_type)
                    st.session_state.submitted.add(idx)
                    st.session_state[f"feedback_{idx}"] = feedback
                    st.rerun()
            elif idx in st.session_state.submitted:
                st.markdown(f"🗣️ **Suggestions:** {st.session_state.get(f'feedback_{idx}', '')}")

    if round_type in ["Technical MCQ", "Aptitude + Verbal", "Logical Reasoning"]:
        st.success(f"🎯 Final Score: {st.session_state.score} / {len(st.session_state.questions)}")

# ================= Footer =================
st.markdown("""
<div class="footer">
    <p><strong>Narsing Dinesh Reddy</strong></p>
    <p>📧 <a href='mailto:dineshreddynarsing@gmail.com'>dineshreddynarsing@gmail.com</a> | 📞 8639059008</p>
    <p><a href="https://www.linkedin.com/in/dinesh-reddy-narsing-918b23255" target="_blank">🔗 LinkedIn Profile</a></p>
</div>
""", unsafe_allow_html=True)

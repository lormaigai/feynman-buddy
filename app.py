import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "feynman.db"

TOPICS = [
    "Cells & the Chemistry of Life (Y3)",
    "Natural Selection and Reproduction",
    "DNA, Nuclear and Cellular Division",
    "Inheritance",
    "Infectious Diseases",
    "Molecular Genetics",
]

MODES = ["Feynman", "Active Recall", "Application", "Exam Transfer"]
DIMENSIONS = [
    "recall",
    "explanation",
    "application",
    "data_handling",
    "experimental_skills",
    "exam_transfer",
]

SYSTEM = """
You are Feynman Buddy, a demanding but fair Biology exam tutor.

The student is preparing for a school Biology final-year exam. The source of truth
for scope is the supplied curriculum map and assessment framework. The supplied
reference pages and textbook support content, and the past EYA paper supports
question-style calibration.

The goal is mastery, not passive explanation.

Rules:
1. ACTIVE RECALL FIRST. Do not teach before the student attempts the question.
2. Ask exactly ONE question at a time.
3. Evaluate the student's actual answer, not its confidence or fluency.
4. Preserve correct components and identify the smallest repairable gap.
5. Prefer probing and repair questions over immediately revealing the answer.
6. Use Feynman teach-back when explanation quality matters.
7. Interleave older objectives with current material when review history supports it.
8. Vary recall, explanation, why/how, comparison, application, graph/data interpretation,
   experimental reasoning, and exam transfer.
9. Match school exam command words such as state, describe, explain, outline, predict,
   suggest, calculate, and determine when appropriate.
10. Never invent a syllabus requirement. If the supplied sources do not support a claim,
    say that the evidence is insufficient.
11. A correct recall answer does not automatically prove conceptual mastery. Probe deeper
    when the objective requires explanation or application.
12. If the student is repeatedly correct, increase transfer difficulty. If repeatedly wrong,
    reduce step size and diagnose the underlying error.
"""

EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "rating": {"type": "integer", "minimum": 0, "maximum": 5},
        "decision": {"type": "string", "enum": ["retry", "progress", "mastered"]},
        "feedback": {"type": "string"},
        "correct_components": {"type": "array", "items": {"type": "string"}},
        "missing_components": {"type": "array", "items": {"type": "string"}},
        "misconceptions": {"type": "array", "items": {"type": "string"}},
        "gap": {"type": "string"},
        "next_question": {"type": "string"},
        "concept": {"type": "string"},
        "skill_dimension": {"type": "string", "enum": DIMENSIONS},
        "source_basis": {"type": "string"},
    },
    "required": [
        "rating", "decision", "feedback", "correct_components",
        "missing_components", "misconceptions", "gap", "next_question",
        "concept", "skill_dimension", "source_basis",
    ],
    "additionalProperties": False,
}


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS concepts (
            concept TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            recall REAL DEFAULT 0,
            explanation REAL DEFAULT 0,
            application REAL DEFAULT 0,
            data_handling REAL DEFAULT 0,
            experimental_skills REAL DEFAULT 0,
            exam_transfer REAL DEFAULT 0,
            interval_days INTEGER DEFAULT 1,
            due_at TEXT,
            last_seen TEXT,
            attempts INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            topic TEXT NOT NULL,
            mode TEXT NOT NULL,
            concept TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            rating INTEGER NOT NULL,
            decision TEXT NOT NULL,
            feedback TEXT NOT NULL,
            gap TEXT NOT NULL,
            misconceptions TEXT NOT NULL,
            source_basis TEXT
        )
    """)
    conn.commit()
    return conn


def due_reviews(conn, limit=10):
    now = datetime.now().isoformat(timespec="seconds")
    return conn.execute(
        """
        SELECT * FROM concepts
        WHERE due_at IS NULL OR due_at <= ?
        ORDER BY COALESCE(due_at, '1900-01-01'), attempts ASC
        LIMIT ?
        """,
        (now, limit),
    ).fetchall()


def update_mastery(conn, concept, topic, dimension, rating):
    now = datetime.now()
    row = conn.execute("SELECT * FROM concepts WHERE concept = ?", (concept,)).fetchone()
    score = rating * 20

    if row is None:
        values = {d: 0.0 for d in DIMENSIONS}
        values[dimension] = score
        interval = {0: 1, 1: 1, 2: 2, 3: 4, 4: 7, 5: 14}[rating]
        due = now + timedelta(days=interval)
        conn.execute(
            """
            INSERT INTO concepts
            (concept, topic, recall, explanation, application, data_handling,
             experimental_skills, exam_transfer, interval_days, due_at,
             last_seen, attempts, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                concept, topic, values["recall"], values["explanation"],
                values["application"], values["data_handling"],
                values["experimental_skills"], values["exam_transfer"],
                interval, due.isoformat(timespec="seconds"),
                now.isoformat(timespec="seconds"), now.isoformat(timespec="seconds"),
            ),
        )
    else:
        old = float(row[dimension])
        new = old * 0.65 + score * 0.35
        old_interval = max(int(row["interval_days"] or 1), 1)
        if rating >= 4:
            factor = 1.7 if rating == 4 else 2.2
            interval = min(max(int(old_interval * factor), 1), 90)
        else:
            interval = {0: 1, 1: 1, 2: 2, 3: 4}[rating]
        due = now + timedelta(days=interval)
        conn.execute(
            f"""
            UPDATE concepts
            SET {dimension} = ?, interval_days = ?, due_at = ?, last_seen = ?,
                attempts = attempts + 1, updated_at = ?
            WHERE concept = ?
            """,
            (
                new, interval, due.isoformat(timespec="seconds"),
                now.isoformat(timespec="seconds"), now.isoformat(timespec="seconds"),
                concept,
            ),
        )
    conn.commit()


def openai_client():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env and restart the app.")
    return OpenAI(api_key=key)


def vector_store_id():
    value = os.getenv("OPENAI_VECTOR_STORE_ID", "").strip()
    if not value:
        raise RuntimeError(
            "OPENAI_VECTOR_STORE_ID is missing. Ingest the private source files first."
        )
    return value


def ask_model(input_text, structured=False):
    client = openai_client()
    kwargs = {
        "model": os.getenv("OPENAI_MODEL", "").strip(),
        "tools": [{"type": "file_search", "vector_store_ids": [vector_store_id()]}],
        "input": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": input_text},
        ],
    }
    if not kwargs["model"]:
        raise RuntimeError("OPENAI_MODEL is missing. Set the model you want to use in .env.")
    if structured:
        kwargs["text"] = {
            "format": {
                "type": "json_schema",
                "name": "feynman_evaluation",
                "schema": EVAL_SCHEMA,
                "strict": True,
            }
        }
    response = client.responses.create(**kwargs)
    return response.output_text.strip()


def generate_question(topic, mode, review_context):
    return ask_model(
        f"""
Generate ONE {mode} Biology question for the topic: {topic}.

Review context:
{review_context or 'No previous mastery data. Treat this as a diagnostic question.'}

Use the supplied curriculum and assessment sources as the authority. If Feynman mode,
prefer a teach-back prompt. If Exam Transfer mode, prefer a short unfamiliar scenario
that tests application rather than copying textbook wording.

Return only the question.
"""
    )


def evaluate(topic, mode, question, answer, history):
    history_text = "\n".join(
        f"{item['role'].upper()}: {item['text']}" for item in history[-8:]
    )
    return json.loads(
        ask_model(
            f"""
Topic: {topic}
Mode: {mode}

Current question:
{question}

Student answer:
{answer}

Recent interaction:
{history_text or 'No earlier interaction in this session.'}

Evaluate the answer against the supplied curriculum, assessment framework, reference
pages, textbook, and past-paper evidence.

Do not give the full answer if a repairable gap remains. Preserve correct components,
identify missing components and misconceptions, then ask exactly ONE next question.
The next question should target the most important gap or increase transfer difficulty
if the student is ready.

Use source_basis to name the source type and page/topic when the retrieved evidence allows it.
""",
            structured=True,
        )
    )


def explain_after_attempt(topic, question, answer):
    return ask_model(
        f"""
The student has already attempted this Biology question.

Topic: {topic}
Question: {question}
Student answer: {answer}

Now give a compact source-grounded explanation with:
1. what was correct
2. what was wrong or missing
3. the correct explanation
4. one useful memory hook

Do not add unrelated content.
"""
    )


st.set_page_config(page_title="Feynman Buddy", layout="wide")
conn = connect_db()

for key, default in {
    "question": None,
    "history": [],
    "topic": TOPICS[0],
    "mode": MODES[0],
    "last_answer": "",
    "last_eval": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("Feynman Buddy")
st.caption("Active recall first. Explain, repair, apply, revisit.")

with st.sidebar:
    st.header("Study controls")
    st.session_state.topic = st.selectbox(
        "Topic", TOPICS, index=TOPICS.index(st.session_state.topic)
    )
    st.session_state.mode = st.selectbox(
        "Mode", MODES, index=MODES.index(st.session_state.mode)
    )

    if st.button("Start question", use_container_width=True, type="primary"):
        try:
            due = due_reviews(conn, limit=5)
            context = "\n".join(
                f"{r['concept']} | due={r['due_at']} | attempts={r['attempts']}"
                for r in due
            )
            st.session_state.question = generate_question(
                st.session_state.topic, st.session_state.mode, context
            )
            st.session_state.history = []
            st.session_state.last_answer = ""
            st.session_state.last_eval = None
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Due review")
    due = due_reviews(conn)
    if due:
        for row in due:
            st.write(f"{row['concept']} · {row['topic']}")
    else:
        st.write("No reviews scheduled yet.")

    st.divider()
    st.subheader("System")
    st.write("API key", "connected" if os.getenv("OPENAI_API_KEY") else "missing")
    st.write("Knowledge base", "connected" if os.getenv("OPENAI_VECTOR_STORE_ID") else "missing")

st.header(f"{st.session_state.topic} · {st.session_state.mode}")

if st.session_state.question is None:
    st.info("Start a question. You must attempt it before the tutor teaches.")
else:
    st.markdown("### Question")
    st.markdown(st.session_state.question)

    answer = st.text_area(
        "Your answer",
        value=st.session_state.last_answer,
        height=180,
        placeholder="Answer from memory first. Do not check your notes.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        submit = st.button("Submit answer", use_container_width=True, type="primary")
    with c2:
        reveal = st.button("Explain after my attempt", use_container_width=True)
    with c3:
        hint = st.button("Give me a small hint", use_container_width=True)

    if hint:
        try:
            st.warning(
                ask_model(
                    f"Give ONE small hint, not the answer, for this Biology question:\n{st.session_state.question}"
                )
            )
        except Exception as exc:
            st.error(str(exc))

    if reveal:
        if not answer.strip():
            st.warning("Attempt the question first. Retrieval comes before explanation.")
        else:
            try:
                st.markdown(explain_after_attempt(st.session_state.topic, st.session_state.question, answer))
            except Exception as exc:
                st.error(str(exc))

    if submit:
        if not answer.strip():
            st.warning("Submit an actual attempt, even if it is incomplete.")
        else:
            try:
                evaluation = evaluate(
                    st.session_state.topic,
                    st.session_state.mode,
                    st.session_state.question,
                    answer,
                    st.session_state.history,
                )
                st.session_state.last_answer = answer
                st.session_state.last_eval = evaluation
                st.session_state.history.extend([
                    {"role": "student", "text": answer},
                    {"role": "bot", "text": evaluation["feedback"]},
                ])

                conn.execute(
                    """
                    INSERT INTO attempts
                    (created_at, topic, mode, concept, question, answer, rating,
                     decision, feedback, gap, misconceptions, source_basis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now().isoformat(timespec="seconds"),
                        st.session_state.topic,
                        st.session_state.mode,
                        evaluation["concept"],
                        st.session_state.question,
                        answer,
                        evaluation["rating"],
                        evaluation["decision"],
                        evaluation["feedback"],
                        evaluation["gap"],
                        json.dumps(evaluation["misconceptions"]),
                        evaluation["source_basis"],
                    ),
                )
                conn.commit()
                update_mastery(
                    conn,
                    evaluation["concept"],
                    st.session_state.topic,
                    evaluation["skill_dimension"],
                    evaluation["rating"],
                )
                st.session_state.question = evaluation["next_question"]
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

if st.session_state.last_eval:
    ev = st.session_state.last_eval
    st.divider()
    st.subheader("Diagnosis")
    st.write(ev["feedback"])

    if ev["correct_components"]:
        st.markdown("**Correct**")
        for item in ev["correct_components"]:
            st.write(f"- {item}")
    if ev["missing_components"]:
        st.markdown("**Missing**")
        for item in ev["missing_components"]:
            st.write(f"- {item}")
    if ev["misconceptions"]:
        st.markdown("**Misconceptions / error patterns**")
        for item in ev["misconceptions"]:
            st.write(f"- {item}")

    st.caption(
        f"Rating {ev['rating']}/5 · {ev['decision']} · {ev['skill_dimension']} · {ev['source_basis']}"
    )

st.divider()
st.header("Mastery dashboard")
rows = conn.execute("SELECT * FROM concepts ORDER BY attempts DESC").fetchall()

if not rows:
    st.info("Your mastery profile appears after your first evaluated answer.")
else:
    for row in rows:
        scores = [float(row[d]) for d in DIMENSIONS]
        average = sum(scores) / len(scores)
        st.write(f"**{row['concept']}** · {row['topic']} · {average:.0f}%")
        st.progress(min(max(average / 100, 0), 1))
        st.caption(
            " · ".join(f"{d.replace('_', ' ').title()} {row[d]:.0f}%" for d in DIMENSIONS)
            + f" · next review {row['due_at'] or 'now'}"
        )

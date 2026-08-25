# Feynman Buddy

A personal, syllabus-aware study tutor built around the Feynman technique, active recall, adaptive questioning, and spaced repetition.

## Product principle

Feynman Buddy is **not** a textbook chatbot. Its job is to make the student retrieve, explain, apply, repair, and revisit knowledge. The source documents are the authority for what is in scope, while the tutoring engine controls the learning interaction.

## Initial Biology scope

The first implementation targets the RGS Year 4 Biology final-year exam using these local/private source materials:

- 2026 Y4 Biology Curriculum Map
- 2026 Y4 Biology Assessment Framework
- 2026 Y4 Biology Textbook Reference Pages
- Biology Matters GCE O-Level textbook
- 2025 Y4 Biology EYA question paper

The curriculum seed records the six assessed topic areas and the three assessment objectives. It also records the 120-minute EYA structure with 20 MCQ marks and 60 structured-question marks.

## Core learning loop

```text
Curriculum objective
        ↓
Select due / weak / new objective
        ↓
Ask ONE question
        ↓
Student attempts from memory
        ↓
Evaluate against source-backed rubric
        ↓
Diagnose misconception or missing component
        ↓
Ask a targeted repair question
        ↓
Require teach-back / application when appropriate
        ↓
Update mastery by objective + skill
        ↓
Schedule next review
        ↓
Interleave with older material
```

## Tutoring rules

1. Active recall comes before explanation unless the student explicitly requests a reveal after an attempt.
2. Ask one question at a time.
3. Do not mark a concept mastered because the prose sounds confident.
4. Distinguish factual errors, omissions, causal reasoning gaps, vocabulary problems, graph/data interpretation errors, and exam-command-word errors.
5. When an answer is partially correct, preserve what is correct and probe the exact gap rather than restarting the lesson.
6. If the student is repeatedly correct, increase transfer difficulty rather than repeating easy recall.
7. If the student repeatedly fails, reduce the step size and use a different representation or question type.
8. Mix recall, explain, compare, why/how, prediction, data interpretation, experimental design, and exam transfer.
9. Every evaluated answer should update a persistent learning state.
10. Review scheduling should depend on demonstrated performance, not simply on elapsed time.
11. Source provenance should be retained for important evaluations so the tutor can distinguish syllabus requirements from generic knowledge.
12. Never expose private source files, API keys, or student mastery data through the public repository.

## Architecture target

### Content layer

A structured objective graph should eventually replace the coarse topic list. Each objective should have a stable ID, syllabus wording, topic, source references, prerequisite relationships, acceptable evidence, common misconceptions, and question templates.

### Retrieval layer

Private source files are ingested into a knowledge store. Retrieval should be filtered by subject, year, source type, and objective where possible. Curriculum and assessment documents have higher authority for scope and command words than the textbook.

### Tutoring layer

The tutor receives the current objective, student history, recent attempts, source evidence, and session mode. It returns a structured evaluation rather than free-form prose only.

Suggested evaluation fields:

- rating
- decision
- objective_id
- skill_dimension
- correct_components
- missing_components
- misconceptions
- command_word_alignment
- feedback
- next_question
- source_basis
- confidence

### Memory layer

Persist:

- objective mastery
- skill-level mastery
- attempt history
- misconception/error patterns
- last reviewed time
- next review time
- interval
- streak / consistency where useful
- exam-transfer performance

### Review engine

The scheduler should prioritize:

1. overdue objectives with weak mastery
2. objectives with recurring errors
3. objectives due for normal review
4. interleaved older objectives
5. new objectives when the queue permits

### Exam mode

A later module should reproduce the style of the actual school assessment rather than generating generic questions. Questions should be tagged by topic, objective, skill, command word, marks, and question type.

## Repository policy

The public repository contains implementation code and non-sensitive metadata. The actual textbook, reference pages, past papers, and private student mastery database should remain outside Git unless there is a clear right to redistribute them.

## Local setup

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env  # macOS/Linux

streamlit run app.py
```

The retrieval ingestion workflow will be added after the objective model is established, so that source files are attached to stable curriculum IDs rather than dumped into an undifferentiated knowledge base.

## Build phases

### Phase 1, foundation
- repository hygiene
- source manifest
- curriculum objective schema
- local persistence
- tutoring interface

### Phase 2, intelligence
- objective-level retrieval
- structured answer evaluation
- misconception taxonomy
- adaptive questioning

### Phase 3, memory
- spaced repetition
- interleaving
- mastery dashboard
- weakness tracker

### Phase 4, exam engine
- past-paper tagging
- exam simulation
- mark-aware feedback
- command-word calibration

### Phase 5, deployment
- authentication
- private cloud storage
- observability
- automated tests and CI

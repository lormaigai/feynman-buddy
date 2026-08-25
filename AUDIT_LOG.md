# Build audit log

## 2026-08-25

### Step 0, project direction
Defined the product as a personal, syllabus-aware Feynman tutor rather than a generic chatbot. The primary learning loop is active recall, student explanation, diagnosis, repair, transfer, and spaced review.

### Step 1, repository inspection
Inspected `lormaigai/feynman-buddy`. The existing `main` branch contained only the MIT `LICENSE`, so implementation is being developed from a clean branch named `build/biology-feynman-mvp`.

### Step 2, source architecture
The initial Biology source set is the 2026 Y4 Biology Curriculum Map, 2026 Y4 Biology Assessment Framework, 2026 Y4 Biology Textbook Reference Pages, Biology Matters GCE O-Level textbook, and 2025 Y4 Biology EYA question paper. Source PDFs are deliberately kept out of the public repository by `.gitignore`; they should be supplied locally or through a private knowledge-store workflow rather than redistributed publicly.

### Step 3, learning design
The tutor specification requires one question at a time, active recall before explanation, Feynman teach-back, targeted probing, honest diagnosis, adaptive difficulty, interleaving, and spaced repetition. Mastery must be tied to learning objectives rather than conversational fluency alone.

### Step 4, assessment alignment
The curriculum seed records the assessed topic structure and three assessment objectives: Knowledge with Understanding, Handling Information and Solving Problems, and Experimental Skills and Investigations. The exam seed records a 120-minute paper with 20 MCQ marks and 60 structured-question marks.

### Step 5, engineering baseline
Created a secure Python/Streamlit baseline with environment configuration, dependency management, local-state exclusions, and a curriculum seed. The next implementation step is the tutoring engine, persistence model, retrieval layer, and test suite.

### Step 6, safety and privacy
No API keys, local databases, or source PDFs belong in Git. The public repository contains code and non-sensitive curriculum metadata only. Personal mastery data should remain local or be stored in a deliberately authenticated private backend in a later phase.

### Next
- Build objective-level content model
- Add source ingestion and provenance metadata
- Implement adaptive Feynman tutoring loop
- Implement error taxonomy and mastery state
- Implement spaced repetition and interleaved review queue
- Add exam simulation and question tagging
- Add automated tests
- Deploy only after local validation

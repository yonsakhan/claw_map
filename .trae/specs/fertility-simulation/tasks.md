# Tasks

- [x] **Phase 1: Infrastructure & Crawler (Data Layer)**
    - [x] Task 1.1: Setup Project Structure & Database Schema
        - Initialize Python project (Poetry/venv).
        - Setup MongoDB (for raw scrapes) and PostgreSQL (for personas).
        - Define JSON schema for `RawUserProfile` and `RawUserPost`.
    - [x] Task 1.2: Develop Xiaohongshu (Red) Scraper Prototype
        - Implement `Playwright` based scraper to fetch user profile (Bio, Tags, Location).
        - Implement infinite scroll handling to fetch last N posts (e.g., top 10-20).
        - **Constraint**: Add rate limiting and random sleep to avoid IP bans.
    - [x] Task 1.3: Data Cleaning Pipeline
        - Remove bots/marketing accounts (heuristic: 0 posts, ad keywords).
        - Anonymize data (hash IDs).

- [x] **Phase 2: AI Persona Construction (Intelligence Layer)**
    - [x] Task 2.1: Design Prompt Engineering for Persona Extraction
        - Create prompts to infer: Age, Income (high/med/low), Fertility Stage, and Spatial Preferences from bio + posts.
        - Validate prompt accuracy on small sample (n=50) with manual checking.
    - [x] Task 2.2: Batch Processing Pipeline
        - Implement a queue-based worker (e.g., Celery or simple loop) to send raw data to LLM API.
        - Store structured results in PostgreSQL (`AgentPersona` table).
    - [x] Task 2.3: Persona Validation & Calibration
        - Compare extracted aggregate stats (e.g., age distribution) with platform public stats or paper benchmarks to ensure representativeness.

- [x] **Phase 3: Simulation & Quantification (Application Layer)**
    - [x] Task 3.1: Develop "Virtual Interview" Module
        - Create a script where the LLM plays the role of the `AgentPersona`.
        - Ask standard questions from the "Fertility Friendly" paper (e.g., "How does commute time affect your decision?").
    - [x] Task 3.2: Statistical Analysis Dashboard
        - Generate correlation matrix: Spatial Factors vs. Fertility Intent.
        - Visualize clustering of user types (e.g., "High Income-Low Intent" vs "Low Income-High Intent").

- [x] **Phase 4: Reporting**
    - [x] Task 4.1: Generate "Digital Demographics" Report.

# AI-Driven Fertility-Friendly Spatial Research Paradigm Spec

## Why

Traditional urban planning research relies on questionnaires and field surveys, which suffer from small sample sizes, high costs, and static data.
The paper "Identification of Fertility-Friendly Spatial Elements" highlights the complexity of fertility decisions in megacities.
By leveraging massive online community data (Xiaohongshu, Weibo, etc.) and Large Language Models (LLMs), we can construct "Digital Twin" residents (AI Personas) to simulate fertility decisions at scale (10,000+ samples). This allows for dynamic, low-cost, and granular analysis of how spatial elements (housing, commute, nature) impact fertility intent.

## What Changes

We are building a new **AI-Social-Spatial Research Platform** consisting of:

1. **Multi-Source Data Acquisition System (Crawler)**:

   * Modular crawler architecture targeting **Xiaohongshu (primary)** and **Weibo/Douban (secondary)**.

   * Focus on fetching User Profiles + User Generated Content (Posts/Comments) + Interaction Tags.

   * Target scale: 10,000+ valid user profiles.

2. **LLM-Based Persona Construction Pipeline**:

   * A pipeline to convert unstructured user data into structured "Digital Personas" (JSON).

   * **Extraction Dimensions**:

     * **Demographics**: Age, Location (City/District), Estimated Income Level, Education.

     * **Fertility Status**: Unmarried, Married-No-Kids, Pregnant, 1-Child, 2-Child+.

     * **Spatial Sensitivity**: Commute tolerance, housing preference, nature affinity, medical access priority.

     * **Fertility Intent**: Score (0-5) based on content sentiment.

3. **Agent Simulation & Quantification Engine**:

   * A simulation environment where AI Agents (powered by the Personas) react to hypothetical urban planning scenarios.

   * **Quantification Metrics**:

     * Correlation between Spatial Elements (e.g., "Park within 500m") and Fertility Intent Change.

     * "Implicit Fertility Cost" calculation based on agent feedback.

## Impact

* **Research Paradigm Shift**: From "Passive Survey" to "Active Simulation".

* **Data Scale**: 100x increase in sample size compared to traditional methods.

* **Policy Making**: Provides "what-if" analysis for urban planners (e.g., "If we improve childcare accessibility by 20%, how does fertility intent change for low-income groups?").

## Feasibility & Risk Management

* **Platform Complexity**: Crawling 8+ platforms is technically unstable. **Constraint**: We will implement the core architecture for **Xiaohongshu** first, as it has the highest density of target "fertility-relevant" lifestyle data. The architecture will be extensible.

* **Data Privacy**: All data will be anonymized. No real names or exact addresses will be stored; only district-level location and generalized attributes.

* **LLM Cost**: Processing 10k users \* 50 posts each is expensive. We will use a RAG approach or summarize posts first, and potentially use lower-cost models (e.g., Gemini Flash/Haiku or local models) for bulk processing.

## Technical Architecture

* **Language**: Python 3.10+

* **Crawler**: `Playwright` (for dynamic content) + `mitmproxy` (optional for app traffic) or `MediaCrawler` (open source reference).

* **Database**:

  * **Raw Data**: MongoDB (flexible JSON for posts).

  * **Structured Data**: PostgreSQL (for statistical analysis).

* **AI/LLM**: LangChain / OpenAI API / Gemini API.

* **Analysis**: Pandas, Scikit-learn, Matplotlib/Seaborn.


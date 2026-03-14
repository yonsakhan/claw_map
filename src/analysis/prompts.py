from langchain_core.prompts import ChatPromptTemplate

PERSONA_EXTRACTION_PROMPT = ChatPromptTemplate.from_template("""
You are an expert social science researcher. Your task is to analyze a user's social media profile and posts to construct a "Digital Persona" for fertility research.

User Profile:
{profile_json}

Recent Posts:
{posts_json}

Based on the above information, infer the following attributes. If an attribute cannot be inferred with confidence, use "Unknown".

1. **Age Group**: (e.g., "18-24", "25-29", "30-34", "35-39", "40+")
2. **Location**: (City and District if available)
3. **Fertility Status**: (e.g., "Unmarried", "Married-No-Kids", "Pregnant", "Parent-1-Child", "Parent-2-Child+")
4. **Estimated Income Level**: (Based on lifestyle, spending, brands mentioned. "Low", "Medium", "High")
5. **Spatial Preferences**: (What urban elements do they care about? e.g., "Commute time", "Parks", "Hospitals", "Schools", "Safety")
6. **Fertility Intent Score**: (0-5, where 0 is strongly against having kids/more kids, 5 is actively planning. Infer from sentiment.)

Output the result in valid JSON format only, with no markdown formatting. The JSON keys should be:
"age_group", "location", "fertility_status", "income_level", "spatial_preferences" (list of strings), "fertility_intent_score" (int).
""")

ACCOUNT_FEATURE_QUESTIONNAIRE_PROMPT = ChatPromptTemplate.from_template("""
You are an expert social science researcher for fertility-friendly urban planning.

Account Feature Profile:
{account_feature_profile_json}

Questionnaire Context:
{questionnaire_context_json}

Model Parameters:
{model_params_json}

Generate one valid JSON object with these keys:
- age_group (string)
- location (string)
- fertility_status (string)
- income_level (string)
- spatial_preferences (array of strings)
- fertility_intent_score (integer 0-5)
- questionnaire_answers (array of objects with question_id, question, answer, reason_summary, tendency_score, confidence)
- reasoning_summary (string)

Rules:
1) Infer from feature clues and evidence snippets only.
2) If uncertain, set value to "Unknown" and lower confidence.
3) Keep answers concise and structured.
4) Output valid JSON only without markdown.
""")

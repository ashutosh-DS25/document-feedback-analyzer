import streamlit as st
import pandas as pd
from openai import OpenAI
from PyPDF2 import PdfReader
import requests
import json

DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324"

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="AI Feedback Document Orchestrator",
    layout="wide"
)

# =========================
# OPENROUTER CONFIG
# =========================

def get_secret(name, default=None):

    try:

        return st.secrets.get(name, default)

    except Exception:

        return default

# =========================
# AI FUNCTION
# =========================

def analyze_document(comments, user_analysis_prompt):

    api_key = get_secret("OPENROUTER_API_KEY")

    if not api_key:

        st.error(
            "OPENROUTER_API_KEY is missing. Add it in Streamlit Cloud secrets."
        )

        st.stop()

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    model_name = get_secret(
        "OPENROUTER_MODEL",
        DEFAULT_MODEL
    )

    comments_text = "\n".join(
        [
            f"{index + 1}. {comment}"
            for index, comment in enumerate(comments)
        ]
    )

    custom_prompt_instruction = (
        user_analysis_prompt.strip()
        if user_analysis_prompt and user_analysis_prompt.strip()
        else "Analyze all feedback without filtering for a specific feature."
    )

    prompt = f"""
    You are an AI feedback analyzer.

    Analyze all customer feedback comments carefully.

    The user also wants a custom priority analysis.
    Treat this as the user's focus for evaluation:
    {custom_prompt_instruction}

    First decide which feedback comments are relevant to the user's
    focus. If the user asks to focus only on specific features, include
    only comments about those features. If the user asks to ignore a
    feature, exclude comments where that ignored feature is the main
    topic. If the user asks for improvement areas, appreciation areas,
    complaint sensitivity, or a custom answer, include only feedback
    needed for that analysis.

    The sentiment table counts must be calculated ONLY from relevant
    feedback comments selected according to the user's focus. Do not
    count unrelated feedback in total_comments or sentiment totals.

    If the user's focus is broad or empty, treat all valid feedback
    comments as relevant.

    Classify the feedback into:
    - Appreciation
    - Suggestion
    - Complaint
    - Neutral

    Also assign intensity:
    - Low
    - Medium
    - High

    Rules:

    1. Any feedback mentioning:
    bad experience, delay, damaged product, defective item,
    poor support, refund issue, rude staff, crash, bug,
    slow service, frustration, disappointment, poor quality,
    or dissatisfaction should be classified as Complaint.

    2. Serious customer dissatisfaction, repeated issues,
    financial loss, trust issues, or usability problems
    should be marked as High intensity.

    3. Moderate dissatisfaction or improvement requests
    should be marked as Medium intensity.

    4. Positive or satisfied feedback should be Appreciation
    with Low intensity.

    5. Suggestions without strong negative emotion
    should be Suggestion.

    6. Ignore headings, usernames, labels,
    metadata, timestamps, and non-feedback text.

    VERY IMPORTANT RULES:

    - If feedback contains complaint words like:
    delay, damaged, defective, crashing, issue, poor,
    refund, slow, broken, bad, disappointed, rude,
    not working, frustrating, support problem

    THEN Category MUST be Complaint.

    - Never classify negative feedback as Neutral.

    - Neutral should ONLY be used for factual statements
    without emotion.

    Return ONLY valid JSON in this exact structure.
    Do not include markdown, explanation, or extra text.

    {{
        "total_comments": 0,
        "sentiments": {{
            "Appreciation": {{
                "total": 0,
                "Low": 0,
                "Medium": 0,
                "High": 0
            }},
            "Suggestion": {{
                "total": 0,
                "Low": 0,
                "Medium": 0,
                "High": 0
            }},
            "Complaint": {{
                "total": 0,
                "Low": 0,
                "Medium": 0,
                "High": 0
            }},
            "Neutral": {{
                "total": 0,
                "Low": 0,
                "Medium": 0,
                "High": 0
            }}
        }},
        "custom_response": {{
            "answer": ""
        }}
    }}

    The total_comments value must equal the number of relevant feedback
    comments selected for the user's focus, not necessarily all uploaded
    comments. It can be between 0 and {len(comments)}.
    The sum of all sentiment totals must be exactly total_comments.
    For each sentiment, Low + Medium + High must equal total.
    In custom_response.answer, directly answer the user's custom focus
    in plain language. Mention how many relevant feedback comments were
    considered. For each important fact, theme, improvement area,
    appreciation area, or recommendation, mention how many feedback
    comments support it. If no relevant comments are found, say that
    clearly and keep all counts at 0.

    Comments:
    {comments_text}
    """

    response = client.chat.completions.create(

    model=model_name,

    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ],

    temperature=0
    )

    result = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    result = result.replace(
        "```json",
        ""
    ).replace(
        "```",
        ""
    ).strip()

    return json.loads(result)

    

# =========================
# TITLE
# =========================

st.title("AI Feedback Document Orchestrator")

st.write(
    "Upload feedback documents and analyze sentiments."
)

st.divider()

# =========================
# FILE UPLOAD
# =========================

uploaded_file = st.file_uploader(
    "Upload Feedback Document",
    type=["txt", "pdf"]
)

user_email = st.text_input(
    "Enter Email For Alert Notifications"
)

custom_analysis_prompt = st.text_area(
    "What should the AI focus on in the analysis?",
    placeholder=(
        "Example: Focus only on battery and speaker feedback. Ignore delivery "
        "comments. Increase sensitivity toward complaints about screen quality. "
        "Tell me what users appreciate most and which areas need improvement."
    ),
    height=120
)

# =========================
# FILE STATUS
# =========================

if uploaded_file:

    st.success("File Uploaded Successfully")

    st.write(
        f"Uploaded File: {uploaded_file.name}"
    )

st.divider()

# =========================
# ANALYZE BUTTON
# =========================

analyze_btn = st.button(
    "Analyze Feedback"
)

# =========================
# MAIN PROCESSING
# =========================

if analyze_btn:

    if uploaded_file is None:

        st.error("Please upload a feedback document first.")

        st.stop()

    with st.spinner("Analyzing Feedback..."):

        # =========================
        # CSV FILE
        # =========================

        if uploaded_file.name.endswith(".csv"):

            df = pd.read_csv(
                uploaded_file
            )

        # =========================
        # TXT FILE
        # =========================

        elif uploaded_file.name.endswith(".txt"):

            text = uploaded_file.read().decode("utf-8")

            comments = text.split("\n")

            comments = [
                comment.strip()
                for comment in comments
                if comment.strip() != ""
            ]

            df = pd.DataFrame({
                "Comment": comments
            })

        # =========================
        # PDF FILE
        # =========================

        elif uploaded_file.name.endswith(".pdf"):

            pdf_reader = PdfReader(
                uploaded_file
            )

            text = ""

            for page in pdf_reader.pages:

                extracted_text = page.extract_text()

                if extracted_text:

                    text += extracted_text + "\n"

            comments = text.split("\n")

            comments = [
                comment.strip()
                for comment in comments
                if comment.strip() != ""
            ]

            df = pd.DataFrame({
                "Comment": comments
            })

        # =========================
        # COMMENT COLUMN CHECK
        # =========================

        if "Comment" not in df.columns:

            df.columns = ["Comment"]

        comments = [
            str(comment).strip()
            for comment in df["Comment"]
            if str(comment).strip() != ""
        ]

        if len(comments) == 0:

            st.error("No feedback comments found in the uploaded document.")

            st.stop()

        # =========================
        # AI ANALYSIS
        # =========================

        try:

            analysis = analyze_document(
                comments,
                custom_analysis_prompt
            )

        except Exception as e:

            st.error("AI response could not be processed. Please try again.")

            st.exception(e)

            st.stop()

        sentiment_order = [
            "Appreciation",
            "Suggestion",
            "Complaint",
            "Neutral"
        ]

        intensity_order = [
            "Low",
            "Medium",
            "High"
        ]

        total_comments = int(
            analysis.get(
                "total_comments",
                len(comments)
            )
        )

        summary_rows = []

        for sentiment in sentiment_order:

            sentiment_data = analysis.get(
                "sentiments",
                {}
            ).get(
                sentiment,
                {}
            )

            total = int(
                sentiment_data.get(
                    "total",
                    0
                )
            )

            percentage = (
                (total / total_comments) * 100
                if total_comments > 0
                else 0
            )

            row = {
                "Sentiment": sentiment,
                "Total Comments": total,
                "Percentage": round(
                    percentage,
                    2
                )
            }

            for intensity in intensity_order:

                row[f"{intensity} Intensity"] = int(
                    sentiment_data.get(
                        intensity,
                        0
                    )
                )

            summary_rows.append(row)

        summary_df = pd.DataFrame(summary_rows)

        custom_response = analysis.get(
            "custom_response",
            {}
        )

    # =========================
    # SUCCESS MESSAGE
    # =========================

    st.success(
        "Feedback Analysis Completed"
    )

    st.divider()

    # =========================
    # METRICS
    # =========================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Relevant Comments",
        total_comments
    )

    col2.metric(
        "Complaints",
        int(
            summary_df.loc[
                summary_df["Sentiment"] == "Complaint",
                "Total Comments"
            ].iloc[0]
        )
    )

    col3.metric(
        "Suggestions",
        int(
            summary_df.loc[
                summary_df["Sentiment"] == "Suggestion",
                "Total Comments"
            ].iloc[0]
        )
    )

    col4.metric(
        "Appreciation",
        int(
            summary_df.loc[
                summary_df["Sentiment"] == "Appreciation",
                "Total Comments"
            ].iloc[0]
        )
    )

    st.divider()

    # =========================
    # CUSTOM ANALYSIS RESPONSE
    # =========================

    st.subheader(
        "Custom Feedback Analysis"
    )

    custom_answer = custom_response.get(
        "answer",
        ""
    )

    st.text_area(
        "AI Analysis Response",
        value=custom_answer,
        height=220,
        disabled=True
    )

    st.divider()

    # =========================
    # SUMMARY TABLE
    # =========================

    st.subheader(
        "Relevant Sentiment And Intensity Bifurcation"
    )

    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True
    )

    chart_df = summary_df.set_index(
        "Sentiment"
    )[
        [
            "Low Intensity",
            "Medium Intensity",
            "High Intensity"
        ]
    ]

    st.bar_chart(
        chart_df
    )

    st.divider()

    # =========================
    # COMPLAINT THRESHOLD CHECK
    # =========================

    total_complaints = int(
        summary_df.loc[
            summary_df["Sentiment"] == "Complaint",
            "Total Comments"
        ].iloc[0]
    )

    complaint_percentage = (
        (total_complaints / total_comments) * 100
        if total_comments > 0
        else 0
    )

    if complaint_percentage > 15:

        webhook_url = get_secret(
            "ALERT_WEBHOOK_URL",
            ""
        )

        payload = {
            "email": user_email,

            "complaint_percentage":
            round(complaint_percentage, 2),

            "relevant_comments":
            total_comments,

            "summary":
            summary_df.to_dict(
                orient="records"
            )
        }

        st.warning(
            f"{total_complaints} Complaints Detected In Relevant Feedback"
        )

        if webhook_url:

            try:

                requests.post(
                    webhook_url,
                    json=payload,
                    timeout=15
                )

                st.success(
                    "Alert notification sent"
                )

            except requests.RequestException as e:

                st.error(
                    "Alert notification could not be sent."
                )

                st.exception(e)

        else:

            st.info(
                "Alert webhook is not configured. Add ALERT_WEBHOOK_URL in secrets to enable notifications."
            )

       

    st.divider()

    # =========================
    # DOWNLOAD CSV
    # =========================

    csv = summary_df.to_csv(
        index=False
    )

    st.download_button(
        label="Download Relevant Bifurcation Report",
        data=csv,
        file_name="feedback_bifurcation.csv",
        mime="text/csv"
    )

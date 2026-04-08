import streamlit as st
import requests
import json

st.set_page_config(page_title="Meeting Intelligence", layout="wide")

st.title("📊 AI Meeting Intelligence Dashboard")

meeting_id = st.text_input("Enter Meeting ID")

if meeting_id:
    url = f"http://localhost:8004/meeting/{meeting_id}"

    try:
        response = requests.get(url)

        if response.status_code != 200:
            st.error(f"Failed to fetch data from API (Status Code: {response.status_code})")
        else:
            data = response.json()

            # =========================
            # HEADER
            # =========================
            st.header(data["agenda"])

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Total Topics", data["meeting_overview"]["total_topics"])

            with col2:
                st.metric("Total Participants", data["meeting_overview"]["total_participants"])

            st.divider()

            # =========================
            # OVERALL SUMMARY
            # =========================
            st.subheader("📄 Overall Summary")
            st.write(data["overall_summary"])

            st.divider()

            # =========================
            # TOPIC-WISE DISCUSSION
            # =========================
            st.subheader("🧠 Topic-wise Discussion")

            for topic in data["topic_wise_discussion"]:
                with st.expander(f"📌 {topic['topic']}"):
                    for d in topic["discussion"]:
                        st.markdown(f"**👤 {d['speaker']}**")
                        st.write(d["statement"])
                        st.write("---")

            # =========================
            # KEY INSIGHTS
            # =========================
            st.subheader("🔍 Key Insights")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Key Points")
                for k in data["key_insights"]["key_points"]:
                    st.write("•", k)

            with col2:
                st.markdown("### Decisions")
                for d in data["key_insights"]["decisions"]:
                    st.write("•", d)

            # =========================
            # ACTION ITEMS
            # =========================
            st.subheader("📌 Action Items Tracker")

            st.dataframe(
                data["key_insights"]["action_items"],
                use_container_width=True
            )

            # =========================
            # PREVIOUS TASKS (NEW)
            # =========================
            st.subheader("📂 Previous Tasks (Cross-Meeting Tracking)")

            if data.get("task_state") and data["task_state"].get("previous_tasks"):
                st.dataframe(
                    data["task_state"]["previous_tasks"],
                    use_container_width=True
                )
            else:
                st.info("No previous tasks found.")

            # =========================
            # SPEAKER SUMMARIES
            # =========================
            st.subheader("👥 Speaker Summary Cards")

            for speaker in data["individual_speaker_summaries"]:
                st.info(f"""
**{speaker['speaker']}**

{speaker['summary']}
""")

            # =========================
            # DOWNLOAD BUTTON
            # =========================
            st.download_button(
                "⬇️ Download Full Report",
                json.dumps(data, indent=2),
                file_name="meeting_report.json"
            )

    except Exception as e:
        st.error("Error connecting to API")
        st.text(str(e))
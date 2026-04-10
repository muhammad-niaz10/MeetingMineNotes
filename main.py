from database import meeting_notes_collection, meeting_details_collection,name,niaz_meeting_summaries
from bson import ObjectId
from fastapi import FastAPI
import json
from datetime import datetime
import uuid
from groq import Groq
from config import GROQ_API_KEY

app = FastAPI()

@app.get("/")
def get_meeting_notes():
    meeting_notes = list(meeting_notes_collection.find())

    for note in meeting_notes:
        note["_id"] = str(note["_id"])
        note["user"] = str(note["user"])
        note["meeting"] = str(note["meeting"])
        note["scriber"] = str(note["scriber"])


    return meeting_notes



@app.get("/specific_meeting/{meeting_id}")
def get_meeting_notes(meeting_id: str):
    meeting_notes = list(meeting_notes_collection.find({"meeting": ObjectId(meeting_id)}))
    meeting_details = meeting_details_collection.find_one({"_id": ObjectId(meeting_id)})


    for note in meeting_notes:
        note["_id"] = str(note["_id"])
        note["user"] = str(note["user"])
        note["meeting"] = str(note["meeting"])
        note["scriber"] = str(note["scriber"])

    meeting = {
        "details": meeting_details["agenda"] if meeting_details else "No details found",
        "notes": meeting_notes
    }

    return meeting


def serialize(note):
    note["_id"] = str(note["_id"])
    note["user"] = str(note["user"])
    note["meeting"] = str(note["meeting"])
    note["scriber"] = str(note["scriber"])
    return note



import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

#model = genai.GenerativeModel("gemini-2.5-flash")

#model = genai.GenerativeModel(
 #    model_name="gemini-2.0-flash",
  #  generation_config={
   #     "temperature": 0.2,
    #    "response_mime_type": "application/json"
   # }
#)


client = Groq(
    api_key=GROQ_API_KEY
)


@app.get("/meeting/{meeting_id}")
def get_meeting_data(meeting_id: str):


  
  summaries = list(
    niaz_meeting_summaries.find(
        {"meeting_id": {"$ne": ObjectId(meeting_id)}}
    )
)


# =========================
# 1. PREVIOUS SUMMARIES
# =========================
  previous_summaries = []

  for s in summaries:
    previous_summaries.append(s.get("overall_summary", ""))

# =========================
# 2. PREVIOUS TASKS (MERGED)
# =========================
  task_map = {}

  for s in summaries:

    # collect tasks
    tasks = s.get("key_insights", {}).get("action_items", [])

    for t in tasks:

        task_name = t.get("task", "").strip().lower()

        # if task already exists → merge
        if task_name in task_map:

            existing = task_map[task_name]

            # keep worst-case status priority (simple logic)
            if t.get("status") == "Completed":
                existing["status"] = "Completed"
            elif t.get("status") == "In Progress" and existing["status"] != "Completed":
                existing["status"] = "In Progress"

        else:
            task_map[task_name] = {
                "meeting_id": str(s.get("meeting_id")),
                "agenda": s.get("agenda", "Unknown"),
                "owner": t.get("owner", "Unknown"),
                "task": t.get("task", ""),
                "status": t.get("status", "Pending"),
                "priority": t.get("priority", "High"),
                "task_id": t.get("task_id", "")
            }

# FINAL CLEAN OUTPUT
  previous_task = list(task_map.values())

  meeting_details = meeting_details_collection.find_one({"_id": ObjectId(meeting_id)})

  #grouped = {}
  #data = list(meeting_notes_collection.find({"meeting": ObjectId(meeting_id)}))

  #for item in data:
   #   item = serialize(item)

    #  topic = item["topic"]

    # Step 1: Topic create karo agar exist nahi karta
     # if topic not in grouped:
      #    grouped[topic] = {
       #     "topic": topic,
        #    "statements": []
        #}

    # Step 2: User name fetch karo
      #user_data = name.find_one({"_id": ObjectId(item["user"])})
      #user_name = user_data["name"] if user_data else "Unknown"

    # Step 3: Statement add karo
      #grouped[topic]["statements"].append({
      #  "statement": item["statement"],
      #  "user": user_name
    #})

     # meeting = {
      #  "details": meeting_details["agenda"] if meeting_details else "No details found",
       # "topics": list(grouped.values())
   # }


    #  clean_meeting = {
    #"details": meeting["details"],
    #"topics": [
     #   {
      #      "topic": t["topic"],
       #     "statements": [
        #        {
         #           "text": s["statement"],
          #          "speaker": s["user"]
           #     }
            #    for s in t["statements"]
            #]
       # }
       # for t in meeting["topics"]
   # ]
#}

    

 #     clean_meeting_json = json.dumps(clean_meeting, indent=2)


  data = list(meeting_notes_collection.find({"meeting": ObjectId(meeting_id)}))

  grouped = {}

  for item in data:
    item = serialize(item)

    user_data = name.find_one({"_id": ObjectId(item["user"])})
    user_name = user_data["name"] if user_data else "Unknown"

    topic = item.get("topic", "Unknown").strip()

    if topic not in grouped:
        grouped[topic] = {
            "topic": topic,
            "statements": []
        }

    grouped[topic]["statements"].append({
        "speaker": user_name,
        "statement": item.get("statement", "")
    })

  clean_meeting = {
    "details": meeting_details["agenda"] if meeting_details else "No details found",
    "topics": list(grouped.values())
}

  clean_meeting_json = json.dumps(clean_meeting, indent=2)
  previous_tasks_json = previous_task
    

  if not previous_task:
        prompt = f"""
You are a production-grade Meeting Intelligence System designed for enterprise-level meeting analysis, summarization, and action tracking.

========================
CORE OBJECTIVE
========================
Transform raw meeting notes into a structured, executive-level intelligence report that preserves meaning, speaker intent, and decision flow.

========================
HARD CONSTRAINTS (NON-NEGOTIABLE)
========================
1. Return ONLY valid JSON.
2. Do NOT include markdown, headings, comments, or explanations.
3. Do NOT add or invent any information not present in input.
4. Do NOT hallucinate speakers, decisions, or actions.
5. Maintain semantic meaning exactly as input statements.
6. If information is missing, use empty arrays or "Unknown".
7. Group all data strictly by topic first.

========================
PROCESS RULES
========================
1. Extract topics exactly as present in data.
2. Preserve speaker identity for every statement.
3. Merge repetitive statements of same speaker only if meaning is identical.
4. Extract insights ONLY from given statements.
5. Derive decisions ONLY if explicitly implied or stated.
6. Action items must always include:
   - owner
   - task
   - status = "Pending"
   - priority = "High" unless clearly low/medium risk

========================
OUTPUT JSON SCHEMA (STRICT)
========================
Return exactly this structure:

{{
  "agenda": "string",
  "overall_summary": "string",
  "meeting_overview": {{
    "total_topics": number,
    "total_participants": number
  }},
  "topic_wise_discussion": [
    {{
      "topic": "string",
      "discussion": [
        {{
          "speaker": "string",
          "statement": "string"
        }}
      ]
    }}
  ],
  "key_insights": {{
    "key_points": ["string"],
    "decisions": ["string"],
    "action_items": [
      {{
        "owner": "string",
        "task": "string",
        "status": "Pending",
        "priority": "High"
      }}
    ]
  }},
  "individual_speaker_summaries": [
    {{
      "speaker": "string",
      "summary": "string"
    }}
  ]
}}

========================
DATA ACCURACY RULES
========================
- Do NOT fabricate missing participants or topics.
- Count participants only from unique speakers in input.
- Count topics only from unique topic names.
- Keep statements faithful but professionally paraphrased.
- Do not change intent of any statement.

========================
INPUT DATA
========================
{clean_meeting_json}
"""

  else:
      prompt = f"""
You are a production-grade Meeting Intelligence System designed for enterprise-level meeting analysis, summarization, and action tracking.

========================
CORE OBJECTIVE
========================
Transform raw meeting notes into a structured, executive-level intelligence report that preserves meaning, speaker intent, and decision flow.

========================
HARD CONSTRAINTS (NON-NEGOTIABLE)
========================
1. Return ONLY valid JSON.
2. Do NOT include markdown, headings, comments, or explanations.
3. Do NOT add or invent any information not present in input.
4. Do NOT hallucinate speakers, decisions, or actions.
5. Maintain semantic meaning exactly as input statements.
6. If information is missing, use empty arrays or "Unknown".
7. Group all data strictly by topic first.

========================
PROCESS RULES
========================
1. Extract topics exactly as present in data.
2. Preserve speaker identity for every statement.
3. Merge repetitive statements of same speaker only if meaning is identical.
4. Extract insights ONLY from given statements.
5. Derive decisions ONLY if explicitly implied or stated.
6. Action items must always include:
   - owner
   - task
   - status = "Pending"
   - priority = "High" unless clearly low/medium risk

========================
TASK HISTORY UPDATE LAYER (IMPORTANT)
========================
You will receive a second input called:
"previous_tasks"

This contains tasks from past meetings:
[
  {{
    "meeting_id": "...",
    "agenda": "...",
    "owner": "...",
    "task": "...",
    "status": "Pending | Completed | In Progress",
    "priority": "...",
    "task_id": "..."
  }}
]

------------------------
TASK PROCESSING RULES
------------------------

A) DO NOT duplicate previous_tasks.

B) MATCHING RULE:
   - Compare new action items with previous_tasks semantically.
   - If same meaning → treat as SAME TASK.

C) IF MATCH FOUND:
   - keep existing task_id
   - update status only if explicitly changed
   - otherwise keep previous status

D) IF NO MATCH FOUND:
   - create new task_id

E) STATUS RULES:
   - explicitly completed → "Completed"
   - actively working → "In Progress"
   - otherwise → "Pending"

F) NEVER overwrite previous_tasks directly.

G) OUTPUT MUST SEPARATE TASKS INTO :
   - previous_tasks (unchanged original input tasks)
   

H) IMPORTANT:
   - DO NOT include previous_tasks inside action_items


========================
HISTORICAL CONTEXT LAYER (IMPORTANT)
========================
You will also receive previous meeting summaries.

GOAL:
- Provide continuity across meetings without overpowering current meeting insights.

RULES:
1. Extract a VERY SHORT combined summary of previous meetings.
2. Previous summaries must have LOW influence (max 20% weight).
3. Current meeting MUST dominate final overall_summary (80% focus).
4. Do NOT repeat full previous summaries.
5. Only include key recurring themes or patterns from history.

FINAL SUMMARY RULE:

- Generate:
   → overall_summary (ONLY current meeting)
   → overall_all_meeting_summary (current + previous summaries)

Format:

"overall_summary" = Current meeting only

"overall_all_meeting_summary" = 
Combined summary of:
- current meeting
- previous meetings (short, trend-based)


========================
OVERALL SUMMARY STRUCTURE RULE (UPDATED)
========================

The field "overall_summary" is a structured object:

- current_meeting_summary:
    Summary ONLY of the current meeting content.

- global_meeting_summary:
    A unified executive summary combining:
      - current meeting summary
      - previous meeting summaries

GLOBAL RULES:
1. current_meeting_summary = 100% current meeting only
2. global_meeting_summary = cross-meeting intelligence (history + current)
3. Do NOT duplicate content between both fields
4. global_meeting_summary must reflect trends, continuity, and evolution across meetings
5. Keep both concise and non-redundant


========================
OUTPUT JSON SCHEMA (STRICT)
========================
Return exactly this structure:

{{
  "agenda": "string",
  "overall_summary": "string",
"overall_all_meeting_summary": "string",
  "meeting_overview": {{
    "total_topics": number,
    "total_participants": number
  }},
  "topic_wise_discussion": [
    {{
      "topic": "string",
      "discussion": [
        {{
          "speaker": "string",
          "statement": "string"
        }}
      ]
    }}
  ],
  "key_insights": {{
    "key_points": ["string"],
    "decisions": ["string"],
    "action_items": [
      {{
        "owner": "string",
        "task": "string",
        "status": "Pending",
        "priority": "High"
      }}
    ]
  }},
  "task_state": {{
    "previous_tasks": []
    
  }},
  "individual_speaker_summaries": [
    {{
      "speaker": "string",
      "summary": "string"
    }}
  ]
}}

========================
DATA ACCURACY RULES
========================
- Do NOT fabricate missing participants or topics.
- Count participants only from unique speakers in input.
- Count topics only from unique topic names.
- Keep statements faithful but professionally paraphrased.
- Do not change intent of any statement.

========================
INPUT DATA
========================
{clean_meeting_json}

========================
PREVIOUS TASKS DATA
========================
{previous_task}

========================
PREVIOUS SUMMARIES
========================
{previous_summaries}
"""
           
    #response = model.generate_content(prompt)

    #return meeting



    
  try:

      response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0.2
)


      raw = response.choices[0].message.content.strip()

      if "```" in raw:
        raw = raw.split("```")[1]
        raw = raw.replace("json", "").strip()

      print(raw)  # optional debug

      result = json.loads(raw)



      result["meeting_id"] = str(ObjectId(meeting_id))
      result["created_at"] = datetime.utcnow()

      for task in result["key_insights"]["action_items"]:

        task["task_id"] = str(uuid.uuid4())

        niaz_meeting_summaries.insert_one({
    "meeting_id": ObjectId(meeting_id),
    "agenda": result["agenda"],
    "overall_summary": result["overall_summary"],
    "meeting_overview": result["meeting_overview"],
    "topic_wise_discussion": result["topic_wise_discussion"],
    "key_insights": result["key_insights"],
    "individual_speaker_summaries": result["individual_speaker_summaries"],
    "previous_tasks": result.get("task_state", {}).get("previous_tasks", []),
    "overall_all_meeting_summary": result.get("overall_all_meeting_summary", ""),
    "created_at": datetime.utcnow()
})
        return result
  except Exception as e:

        return {
        "error": str(e)
    }


    




@app.get("/summary")
def get_meeting_summary():
    summary = list(niaz_meeting_summaries.find())
    previous_task=  []
    for s in summary:
        task = s.get("key_insights", {}).get("action_items", [])
        for t in task:
          previous_task.append({
            "meeting_id": str(s.get("meeting_id")),
            "agenda": s.get("agenda", "Unknown"),
            "owner": t.get("owner", "Unknown"),
            "task": t.get("task", ""),
            "status": t.get("status", "Pending"),
            "priority": t.get("priority", "High"),
            "task_id": t.get("task_id", "")
        })
      
    return  previous_task


@app.get("/overal_summaries")
def get_overall_summaries():
    summary = list(niaz_meeting_summaries.find())
    previous_summaries=  []
    for s in summary:
      previous_summaries.append(s.get("overall_summary", ""))
    return previous_summaries
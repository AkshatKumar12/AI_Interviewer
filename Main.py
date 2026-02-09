import os
import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import TextMessage
from autogen_core.models import ModelInfo
import asyncio
from database import init_db, save_interview

app = FastAPI()

init_db()

# In-memory session transcripts; persisted to DB on each turn.
_sessions = {}

model_client = OpenAIChatCompletionClient(
    model="gemini-2.5-flash",
    api_key = "",  
    model_info=ModelInfo(
        vision=True,
        function_calling=True,
        json_output=True,
        structured_output=True,
        family="unknown",
    ),
)

interviewer = AssistantAgent(
    name="Interviewer",
    model_client=model_client,
    system_message=(
        """"You are 'Bob' an interviewer at a top tech company (FAANG-like). 
        You are interviewing a 3rd-year, 5th-semester BTech CSE student for a Software Engineering Internship role. 
        Structure: intro -> ONE coding (DSA/LeetCode-style) -> ONE Operating System or problem-solving suitable for an intern -> 
        2-3 behavioral. Ask ONE question at a time. Expect clear thought process before coding. 
        Hints only if asked. Evaluate clarity, approach, coding, and communication. 
        Professional but slightly challenging. 
        At the end, summarize performance and whether to move to next round. 
        When the interview is complete, end with the token 'TERMINATE'. Keep it short."""
    ),
)

manager = AssistantAgent(
    name="Manager",
    model_client=model_client,
    system_message=(
        """You are 'Alice' Hiring Manager overseeing the interview. 
        Manage flow, step in to clarify/redirect if needed. "
        If the candidate excels, raise difficulty and note suitability for stronger role; 
        if they struggle, scale down and evaluate fundamentals. 
        At the end, provide hiring recommendation, performance summary, growth potential, and compensation band suggestion. 
        Keep it short with 1 coding question and 2-3 behavioral questions. 
        If the process should stop, say 'TERMINATE'."""
    ),
)


termination_condition = TextMentionTermination("TERMINATE")

team = RoundRobinGroupChat(
    participants=[interviewer], 
    termination_condition=termination_condition,
    max_turns=1, 
)

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    candidate_name: str | None = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    final_score: dict | None = None
    manager_response: str | None = None

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    - If req.message == 'start': kick off the interview (ask first question; stop).
    - Else: treat req.message as the candidate's reply and continue one turn.
    """
    user_msg = (req.message or "").strip()
    session_id = req.session_id or str(uuid.uuid4())
    candidate_name = (req.candidate_name or "Candidate").strip() or "Candidate"

    session_state = _sessions.get(session_id, {"transcript": []})
    transcript = session_state["transcript"]

    if user_msg.lower() == "start":
        task = (
            f"Conduct an interview of '{candidate_name}'. "
            "Begin with a brief intro, then ask the first question. "
            "IMPORTANT: Ask ONLY one question and stop your turn."
        )
    else:

        task = TextMessage(content=user_msg, source="Interviewee")
        transcript.append({"role": "candidate", "content": user_msg})

    result = []
    terminated = False
    try:
        async for item in team.run_stream(task=task):
            if isinstance(item, TextMessage):
                result.append(f"{item.source}: {item.content}")
                transcript.append({"role": item.source.lower(), "content": item.content})
                if "terminate" in item.content.lower():
                    terminated = True
    except Exception as exc:
        error_msg = f"Backend error: {type(exc).__name__}: {exc}"
        transcript.append({"role": "system", "content": error_msg})
        save_interview(
            session_id=session_id,
            candidate_name=candidate_name,
            transcript=transcript,
            final_score={"status": "error", "summary": error_msg},
        )
        return {
            "response": error_msg,
            "session_id": session_id,
            "final_score": {"status": "error", "summary": error_msg},
        }

    _sessions[session_id] = {"transcript": transcript}

    final_score = {"status": "in_progress"}
    manager_response = None
    if terminated:
        # Store last manager/interviewer message as a lightweight summary.
        final_score = {"status": "terminated", "summary": result[-1] if result else ""}

        # Manager review after interview ends.
        transcript_text = "\n".join([f"{t['role']}: {t['content']}" for t in transcript])
        manager_task = (
            "You are 'Alice' Hiring Manager overseeing the interview. "
            "Based on the transcript below, provide hiring recommendation, "
            "performance summary, growth potential, and compensation band suggestion. "
            "Keep it short.\n\n"
            f"Transcript:\n{transcript_text}"
        )
        manager_result = []
        try:
            async for item in manager.run_stream(task=manager_task):
                if isinstance(item, TextMessage):
                    manager_result.append(f"{item.source}: {item.content}")
                elif hasattr(item, "content"):
                    source = getattr(item, "source", "Manager")
                    manager_result.append(f"{source}: {item.content}")
        except Exception as exc:
            manager_result = [f"Manager: Backend error: {type(exc).__name__}: {exc}"]

        if manager_result:
            manager_response = "\n\n".join(manager_result)
            transcript.append({"role": "manager", "content": manager_response})
            final_score["summary"] = manager_response

    save_interview(
        session_id=session_id,
        candidate_name=candidate_name,
        transcript=transcript,
        final_score=final_score,
    )

    return {
        "response": "\n\n".join(result) if result else "No response.",
        "session_id": session_id,
        "final_score": final_score if terminated else None,
        "manager_response": manager_response,
    }

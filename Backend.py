import os
from fastapi import FastAPI
from pydantic import BaseModel
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import TextMessage
from autogen_core.models import ModelInfo
import asyncio

app = FastAPI()


model_client = OpenAIChatCompletionClient(
    model="gemini-2.0-flash",
    api_key = "AIzaSyCKlUQpeuLi5sfS149KPh1cbgbAqTmLsJI",  
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
        At the end, summarize performance  and whether to move to next round, also give a report various scores based on /10 . Keep it short."""
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
    participants=[interviewer, manager], 
    termination_condition=termination_condition,
    max_turns=1, 
)

class ChatRequest(BaseModel):
    message: str 

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    - If req.message == 'start': kick off the interview (ask first question; stop).
    - Else: treat req.message as the candidate's reply and continue one turn.
    """
    user_msg = (req.message or "").strip()

    if user_msg.lower() == "start":
        task = (
            "Conduct an interview of 'Akshat'. "
            "Begin with a brief intro, then ask the first question. "
            "IMPORTANT: Ask ONLY one question and stop your turn."
        )
    else:

        task = TextMessage(content=user_msg, source="Interviewee")

    result = []
    async for item in team.run_stream(task=task):
        if isinstance(item, TextMessage):
            result.append(f"{item.source}: {item.content}")

    return {"response": "\n\n".join(result) if result else "No response."}

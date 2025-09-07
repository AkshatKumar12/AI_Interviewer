# from fastapi import FastAPI
# from pydantic import BaseModel
# from autogen_ext.models.openai import OpenAIChatCompletionClient
# from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
# from autogen_agentchat.teams import RoundRobinGroupChat
# from autogen_agentchat.conditions import TextMentionTermination
# import asyncio

# app = FastAPI()

# model_client = OpenAIChatCompletionClient(
#     model="gemini-2.0-flash",
#     api_key="AIzaSyCEZiG9h3jYYLVZ671LMPQlxfVD3CTAKFo"  
# )

# interviewer = AssistantAgent(
#     name="Interviewer",
#     model_client=model_client,
#     system_message="""You are 'Bob' an interviewer at a top tech company (FAANG-like).
#         You are interviewing a 3rd-year, 5th-semester BTech CSE student for a Software Engineering Internship role.
#         Structure the interview like a real one: begin with a short introduction,
#         then move into coding/data structures and algorithms questions (LeetCode-style),
#         followed by one system design or problem-solving question appropriate for an intern,
#         and finally a few behavioral/cultural fit questions.
#         Ask one question at a time.
#         Expect the candidate to explain their thought process clearly before coding.
#         Provide hints only if the candidate asks.
#         Evaluate the candidate on clarity, problem-solving approach, coding ability, and communication.
#         Maintain a professional but slightly challenging tone.
#         At the end, summarize the candidate’s performance with feedback and an assessment of whether they would move to the next round.Keep the interview short with 1 coding question 2-3 behavioural questions.""",
# )

# manager = AssistantAgent(
#     name="Manager",
#     model_client=model_client,
#     system_message="""You are a 'Alice' Hiring Manager at a top tech company.
#     You are overseeing the internship interview of a 3rd-year, 5th-semester BTech CSE student.
#     Your role is to manage the flow of the interview, maintain professionalism between the interviewer and candidate,
#     and step in when necessary to clarify, redirect, or adjust the pace. 
#     bserve the candidate’s performance and potential: if the candidate performs strongly,
#     instruct the interviewer to increase the difficulty of questions and note their suitability for higher pay or a stronger role;
#     if the candidate struggles, guide the interviewer to scale down the difficulty and evaluate based on fundamentals.
#     At the end, provide a hiring recommendation, including performance summary, growth potential, and compensation band suggestion.
#     Maintain a professional, balanced, and insightful tone throughout.Keep the interview short with 1 coding question 2-3 behavioural questions. IF you think the process should be stopped, send 'TERMINATE'."""
# )


# candidate = UserProxyAgent(
#     name="Interviewee",
#     description="The candidate",
#     input_func=None  
# )

# termination_condition = TextMentionTermination("TERMINATE")

# team = RoundRobinGroupChat(
#     participants=[interviewer, manager, candidate],
#     termination_condition=termination_condition,
#     max_turns=30
# )


# class ChatRequest(BaseModel):
#     message: str

# class ChatResponse(BaseModel):
#     response: str

# @app.post("/chat", response_model=ChatResponse)
# async def chat(req: ChatRequest):
#     # Inject user message into candidate agent
#     candidate.append_user_message(req.message)

#     result = ""
#     async for event in team.run_stream(task="Conducting an interview of 'Akshat'."):
#         if event.agent and event.message:
#             result += f"{event.agent.name}: {event.message}\n"

#     return {"response": result}




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
    api_key = "AIzaSyCEZiG9h3jYYLVZ671LMPQlxfVD3CTAKFo",  
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

from pathlib import Path

import dotenv
from langchain.agents import AgentState, create_agent
from langchain_core.messages import HumanMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.checkpoint.memory import InMemorySaver


dotenv.load_dotenv(Path(__file__).parent.parent / ".env")

from agents.config import settings
from agents.tools import update_state, update_remaining_budget, web_search, search_flights, make_search_attractions


class TripPlanningState(AgentState):
    origin: str
    destination: str
    initial_budget: int
    remaining_budget: int
    date_from: str
    date_to: str


hotel_agent = create_agent(
    model=ChatNVIDIA(model=settings.coordinator_model, api_key=settings.nvidia_api_key),
    tools=[web_search],
    system_prompt="""
    You are a attractions specialist. Search for attractions / museums, POIs in the desired location and within the remaining budget.
    You are not allowed to ask any more follow up questions, you must find the best / most popular tourist attractions
    You may need to make multiple searches to iteratively find the best options.""",
)

search_attractions = make_search_attractions(hotel_agent)

coordinator = create_agent(
    model=ChatNVIDIA(model=settings.coordinator_model, api_key=settings.nvidia_api_key),
    tools=[update_state, update_remaining_budget, search_attractions],
    state_schema=TripPlanningState,
    system_prompt="""
    You are a holiday trip planner, find best attractions at desired location.
    """,
)

response = coordinator.invoke({
    'messages': [HumanMessage(content='I want to fly from Warsaw to Japan, 10.10.2026 - 12.12.2026, i have 2000 usd budget'),
                 ]
})

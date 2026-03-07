from typing import Any, Dict

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command
from tavily import TavilyClient

from agents.config import settings

tavily_client = TavilyClient(api_key=settings.tavily_api_key)


@tool
def web_search(query: str) -> Dict[str, Any]:
    """Search the web for information"""
    return tavily_client.search(query)


@tool
def update_state(origin: str, destination: str, initial_budget: int, remaining_budget: int, date_from: str, date_to: str,
                 runtime: ToolRuntime) -> Command:
    """
    Update the state when you know all the values:
        - origin
        - destination
        - initial_budget
        - remaining_budget
        - date_from
        - date_to
    """
    return Command(update={
        'origin': origin,
        'destination': destination,
        'initial_budget': initial_budget,
        'remaining_budget': remaining_budget,
        'date_from': date_from,
        'date_to': date_to,
        "messages": [ToolMessage("Successfully updated state", tool_call_id=runtime.tool_call_id)]
    })


@tool
def update_remaining_budget(money_spent: int, current_budget: int, runtime: ToolRuntime) -> Command:
    """Update remaining budget when spending money on flights, hotels etc."""
    return Command(
        update={
            "remaining_budget": current_budget - money_spent,
            "messages": [ToolMessage("Successfully updated budget", tool_call_id=runtime.tool_call_id)],
        }
    )


class SubagentsFactory:
    def __init__(self, hotel_agent, flight_agent, attractions_agent):
        pass


@tool
async def search_flights(runtime: ToolRuntime) -> str:
    """Flight agent searches for flights to the desired holiday location between certain dates"""
    origin = runtime.state['origin']
    destination = runtime.state['destination']
    response = None
    return response['messages'][-1].content


@tool
async def search_hotels(runtime: ToolRuntime) -> str:
    """Hotel agent searches for hotels in the desired holiday location between certain dates"""
    origin = runtime.state['origin']
    destination = runtime.state['destination']
    response = None
    return response['messages'][-1].content


def make_search_attractions(agent):
    @tool
    def search_attractions(runtime: ToolRuntime) -> str:
        """
        Attractions agent searches for interesting tourist attractions, museums, POI, restaurants
        """
        destination = runtime.state['destination']
        remaining_budget = runtime.state.get('remaining_budget', 'unknown')
        query = (
            f"Research {destination} and cover these 4 categories:\n"
            f"1. Iconic landmarks and must-see sights (top 3–4)\n"
            f"2. Nature and outdoor experiences (parks, beaches, hikes)\n"
            f"3. Local areas, markets, and street food\n"
            f"4. Restaurants — one budget, one mid-range, one splurge pick\n"
            f"Remaining budget for activities: ${remaining_budget}. "
            f"Use exactly 4 web searches, one per category. Stop after 4 searches."
        )
        response = agent.invoke({"messages": [HumanMessage(content=query)]})
        return response['messages'][-1].content
    return search_attractions

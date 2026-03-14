from typing import Any, Dict

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import Command
from tavily import AsyncTavilyClient

from agents.config import settings

tavily_client = AsyncTavilyClient(api_key=settings.tavily_api_key)


@tool
async def web_search(query: str) -> Dict[str, Any]:
    """Search the web for information"""
    return await tavily_client.search(query)


@tool
async def update_state(origin: str, destination: str, initial_budget: int, remaining_budget: int, date_from: str,
                       date_to: str, runtime: ToolRuntime) -> Command:
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
async def update_remaining_budget(money_spent: int, current_budget: int, runtime: ToolRuntime) -> Command:
    """Update remaining budget when spending money on flights, hotels etc."""
    return Command(
        update={
            "remaining_budget": current_budget - money_spent,
            "messages": [ToolMessage("Successfully updated budget", tool_call_id=runtime.tool_call_id)],
        }
    )


async def get_kiwi_tools():
    client = MultiServerMCPClient({"travel_server": {"transport": "streamable_http", "url": "https://mcp.kiwi.com"}})
    kiwi_tools = await client.get_tools()
    return kiwi_tools


def make_search_flights(agent):
    @tool
    async def search_flights(runtime: ToolRuntime) -> str:
        """Flight agent searches for flights to the desired holiday location between certain dates"""
        origin = runtime.state['origin']
        destination = runtime.state['destination']
        date_from = runtime.state.get('date_from', 'unknown')
        date_to = runtime.state.get('date_to', 'unknown')
        remaining_budget = runtime.state.get('remaining_budget', 'unknown')
        query = (
            f"Search for flights from {origin} to {destination} "
            f"departing {date_from} and returning {date_to}.\n"
            f"Remaining budget: ${remaining_budget}.\n"
            f"Find the best options covering:\n"
            f"1. Cheapest available flights (economy)\n"
            f"2. Best value flights (price vs comfort/layovers)\n"
            f"3. Most convenient flights (fewest stops, best times)\n"
            f"Use up to 3 web searches. Stop after 3 searches."
        )
        response = await agent.ainvoke({"messages": [HumanMessage(content=query)]})
        return response['messages'][-1].content

    return search_flights


def make_search_attractions(agent):
    @tool
    async def search_attractions(runtime: ToolRuntime) -> str:
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
        response = await agent.ainvoke({"messages": [HumanMessage(content=query)]})
        return response['messages'][-1].content
    return search_attractions

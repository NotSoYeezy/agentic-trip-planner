import asyncio
from pathlib import Path

from langchain.agents import AgentState, create_agent
from langchain_core.messages import HumanMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.checkpoint.memory import InMemorySaver

from agents.config import settings
from agents.tools import (
    get_kiwi_tools,
    make_search_attractions,
    make_search_flights,
    update_remaining_budget,
    update_state,
    web_search,
)

PROMPTS_DIR = Path(__file__).parent / "prompts"


class TripPlanningState(AgentState):
    origin: str
    destination: str
    initial_budget: int
    remaining_budget: int
    date_from: str
    date_to: str


class TripPlanningAgentSystem:

    def __init__(self):
        self.coordinator = None
        self.attractions_agent = None
        self.hotel_agent = None
        self.flight_search_agent = None
        self.destination_info_agent = None
        self.system_prompts = {}

    def _load_system_prompts(self):
        prompts_dict = {
            'coordinator': 'prompt_coordinator_attr_flights.md',
            'attractions_agent': 'prompt_attraction_search.md',
            'hotel_agent': 'prompt_hotel_search.md',
            'flight_search_agent': 'prompt_flight_search.md',
            'destination_info_agent': 'prompt_destination_info.md',
        }

        for agent, prompt_file in prompts_dict.items():
            with open(PROMPTS_DIR / prompt_file, encoding='utf-8') as f:
                self.system_prompts[agent] = f.read()

    def _create_coordinator(self):
        search_attractions = make_search_attractions(self.attractions_agent)
        search_flights = make_search_flights(self.flight_search_agent)
        self.coordinator = create_agent(
            model=ChatNVIDIA(model=settings.coordinator_model, api_key=settings.nvidia_api_key, temperature=0.1,
                             max_completion_tokens=4096),
            tools=[update_state, update_remaining_budget, search_flights, search_attractions],
            state_schema=TripPlanningState,
            checkpointer=InMemorySaver(),
            system_prompt=self.system_prompts['coordinator'],
        )

    def _create_attractions_agent(self):
        self.attractions_agent = create_agent(
            model=ChatNVIDIA(model=settings.attractions_model, api_key=settings.nvidia_api_key, temperature=0.1,
                             max_completion_tokens=4096),
            tools=[web_search],
            system_prompt=self.system_prompts['attractions_agent'],
        )

    async def _create_flight_agent(self):
        kiwi_tools = await get_kiwi_tools()
        self.flight_search_agent = create_agent(
            model=ChatNVIDIA(model=settings.flight_search_model, api_key=settings.nvidia_api_key, temperature=0.1,
                             max_completion_tokens=4096),
            tools=kiwi_tools,
            system_prompt=self.system_prompts['flight_search_agent'],
        )

    async def set_up(self):
        self._load_system_prompts()
        self._create_attractions_agent()
        await self._create_flight_agent()
        self._create_coordinator()

    async def invoke(self, message: str, thread_id: int):
        assert self.coordinator, "Please run `set_up` method before invoking!"
        response = await self.coordinator.ainvoke({
            'messages': [HumanMessage(content=message)],
        }, config={'configurable': {'thread_id': thread_id}})

        return response

    async def stream(self, message: str, thread_id: int):
        """Yield SSE-formatted events as the coordinator processes."""
        assert self.coordinator, "Please run `set_up` method before invoking!"
        async for event in self.coordinator.astream_events(
            {'messages': [HumanMessage(content=message)]},
            config={'configurable': {'thread_id': thread_id}},
            version='v2',
        ):
            kind = event['event']

            if kind == 'on_chat_model_stream':
                content = event['data']['chunk'].content
                if content:
                    yield content

            elif kind == 'on_tool_start':
                tool_name = event['name']
                yield f"\n[TOOL_START: {tool_name}]\n"

            elif kind == 'on_tool_end':
                tool_name = event['name']
                yield f"\n[TOOL_END: {tool_name}]\n"


if __name__ == '__main__':
    async def main():
        agent = TripPlanningAgentSystem()
        await agent.set_up()
        response = await agent.invoke(
            "I want to fly from Warsaw to Dubrovnik, 20.03.2026 - 28.03.2026, i have 2000 usd budget",
            1
        )
        print(response['messages'][-1].content)

    asyncio.run(main())

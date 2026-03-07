from langchain.agents import AgentState, create_agent
from langchain_core.messages import HumanMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.checkpoint.memory import InMemorySaver

from agents.config import settings
from agents.tools import make_search_attractions, update_remaining_budget, update_state, web_search


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
            'coordinator': 'prompt_coordinator_attractions_only.md',
            'attractions_agent': 'prompt_attraction_search.md',
            'hotel_agent': 'prompt_hotel_search.md',
            'flight_search_agent': 'prompt_flight_search.md',
            'destination_info_agent': 'prompt_destination_info.md',
        }

        for agent, prompt_file in prompts_dict.items():
            with open(f'prompts/{prompt_file}', encoding='utf-8') as f:
                self.system_prompts[agent] = f.read()

    def _create_coordinator(self):
        search_attractions = make_search_attractions(self.attractions_agent)
        self.coordinator = create_agent(
            model=ChatNVIDIA(model=settings.coordinator_model, api_key=settings.nvidia_api_key, temperature=0.1,
                             max_completion_tokens=4096),
            tools=[update_state, update_remaining_budget, search_attractions],
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

    def set_up(self):
        self._load_system_prompts()
        self._create_attractions_agent()
        self._create_coordinator()

    def invoke(self, message: str, thread_id: int):
        assert self.coordinator, "Please run `set_up` method before invoking!"
        response = self.coordinator.invoke({
            'messages': [HumanMessage(content=message)],
        }, config={'configurable': {'thread_id': thread_id}})

        return response


if __name__ == '__main__':
    agent = TripPlanningAgentSystem()
    agent.set_up()
    response = agent.invoke(
        "I want to fly from Warsaw to Dubrovnik, 10.03.2026 - 18.03.2026, i have 2000 usd budget",
        1
    )
    print(response['messages'][-1].content)

import json
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.custom_agents import TripPlanningAgentSystem

agent = TripPlanningAgentSystem()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await agent.set_up()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TripRequest(BaseModel):
    message: str
    thread_id: int = 1


async def event_generator(message: str, thread_id: int):
    async for chunk in agent.stream(message, thread_id):
        data = json.dumps({"content": chunk})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/plan")
async def plan_trip(request: TripRequest):
    """Non-streaming endpoint — returns the full response."""
    response = await agent.invoke(request.message, request.thread_id)
    return {"response": response['messages'][-1].content}


@app.post("/plan/stream")
async def plan_trip_stream(request: TripRequest):
    """SSE streaming endpoint — streams tokens and tool events as they happen."""
    return StreamingResponse(
        event_generator(request.message, request.thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

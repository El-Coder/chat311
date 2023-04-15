"""app"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import APIRouter, FastAPI, Request
from pydantic import BaseModel
from sqlitedict import SqliteDict

from chat311.ask import ask

executor = ThreadPoolExecutor(max_workers=2**3)
loop = asyncio.get_event_loop()
app = FastAPI()
router = APIRouter(prefix="/api", tags=["api"])

app.state.executor = executor
app.state.db = SqliteDict("/tmp/db.sqlite", autocommit=True)
app.state.loop = loop
app.state.tasks = []


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    session_id: str


class PollRequest(BaseModel):
    session_id: str


class PollResponse(BaseModel):
    status: str
    session_id: str
    answer: str
    process: list[dict]


@router.post("/ask")
async def ask_route(
    ask_request: AskRequest, request: Request
) -> AskResponse:
    tasks = request.app.state.tasks
    db = request.app.state.db
    session_id = str(uuid4())

    # create asyncio task
    coro = loop.run_in_executor(
        executor, ask, ask_request.question, session_id
    )
    task = coro  # loop.create_task(coro)
    tasks.append(task)
    db[session_id] = {"process": []}
    await asyncio.sleep(0.1)
    return AskResponse(session_id=session_id)


@router.get("/poll")
async def poll_route(session_id: str, request: Request) -> PollResponse:
    tasks = request.app.state.tasks
    db = request.app.state.db

    if not tasks:
        return PollResponse(
            status="none", session_id=session_id, answer="", process=[]
        )
    done, pending = await asyncio.wait(
        tasks, timeout=0.1, return_when=asyncio.FIRST_COMPLETED
    )
    tasks = list(pending)
    for finished_task in done:
        result = finished_task.result()
        db[result.get("session_id")]["result"] = result

    if session_id in db:
        if "result" not in db[session_id]:
            return PollResponse(
                status="pending",
                session_id=session_id,
                answer="",
                process=db[session_id]["process"],
            )
        return PollResponse(
            status="done",
            session_id=session_id,
            answer=db[session_id]["result"]["answer"],
            process=db[session_id]["process"],
        )
    return PollResponse(
        status="Does not exist",
        session_id=session_id,
        answer="",
        process=[],
    )


app.include_router(router)

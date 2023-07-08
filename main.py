import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from unicorn.manager import Manager

logger = logging.getLogger('app')

app = FastAPI(debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://0.0.0.0:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)


@app.on_event('startup')
async def on_startup():
    logger.info('on startup')


@app.on_event('shutdown')
async def on_shutdown():
    logger.info('on shutdown')


class Person(BaseModel):
    name: Optional[str]


@app.get("/")
async def index(person: Person, suffix=None):
    name = person.name or "World"
    suffix = suffix or '!'
    return {"message": f"Hello, {name}{suffix}"}


if __name__ == "__main__":
    Manager(app='main:app', host='0.0.0.0', port=8000, workers=2).run()

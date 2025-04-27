from collections.abc import Sequence
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlmodel import (
    JSON,
    Column,
    Field,
    Session,
    SQLModel,
    create_engine,
    select,
)

# Database model


class GameBase(SQLModel):
    release_date: date = Field(index=True)
    studio: str = Field(index=True, min_length=1)
    ratings: int = Field(index=True)
    platforms: Sequence[str] = Field(sa_column=Column(JSON))


class Game(GameBase, table=True):
    name: str = Field(index=True, min_length=1, primary_key=True)


class GamePublic(GameBase):
    name: str


class GameCreate(GameBase):
    name: str


class GameUpdate(GameBase):
    release_date: date | None = None
    studio: str | None = None
    ratings: int | None = None
    platforms: Sequence[str] | None = None


# Database settings


sqlite_file_name = "games.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"


# Database connection and session


connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Application settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


description = """
Technical test from HarfangLab recruitment process. 🦉

This API allows to add a game, modify an existing one or delete it, 
and it is possible to list/filer games.
"""
app = FastAPI(
    title="Games API",
    summary="Technical test.",
    description=description,
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "Anes Benamara Lottier",
        "url": "https://linkedin.com/in/anesbenamara",
        "email": "anes.benamaralottier@gmail.com",
    },
    license_info={
        "name": "Apache License 2.0",
        "identifier": "Apache-2.0",
        "url": "https://opensource.org/license/apache-2-0",
    },
)


# API routes


@app.get("/games", response_model=Sequence[GamePublic])
async def read_games(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    games = session.exec(select(Game).offset(offset).limit(limit)).all()
    return games


@app.get("/games/{game_name}", response_model=GamePublic)
def read_game(game_name: str, session: SessionDep):
    game_db = session.get(Game, game_name)
    if not game_db:
        raise HTTPException(status_code=404, detail="Game not found")
    return game_db


@app.post("/games/", response_model=GamePublic, status_code=status.HTTP_201_CREATED)
def create_game(game: GameCreate, session: SessionDep):
    game_db = Game.model_validate(game)
    session.add(game_db)
    session.commit()
    session.refresh(game_db)
    return game_db


@app.put("/games/{game_name}", response_model=GamePublic)
def update_game(game_name: str, game: GameUpdate, session: SessionDep):
    game_db = session.get(Game, game_name)
    if not game_db:
        raise HTTPException(status_code=404, detail="Game not found")
    game_update = Game.model_validate(GameCreate(**game.model_dump(), name=game_name))
    game_data = game_update.model_dump()
    game_db.sqlmodel_update(game_data)
    session.add(game_db)
    session.commit()
    session.refresh(game_db)
    return game_db


@app.patch("/games/{game_name}", response_model=GamePublic)
def partial_update_game(game_name: str, game: GameUpdate, session: SessionDep):
    game_db = session.get(Game, game_name)
    if not game_db:
        raise HTTPException(status_code=404, detail="Game not found")
    game_data = game.model_dump(exclude_unset=True)
    game_db.sqlmodel_update(game_data)
    session.add(game_db)
    session.commit()
    session.refresh(game_db)
    return game_db


@app.delete("/games/{game_name}")
def delete_game(game_name: str, session: SessionDep):
    game_db = session.get(Game, game_name)
    if not game_db:
        raise HTTPException(status_code=404, detail="Game not found")
    session.delete(game_db)
    session.commit()
    return game_db

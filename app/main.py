import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import routes_pages
from app.api import routes_branches
from app.api import routes_projects
from app.api import routes_releases
from app.api import routes_stages
from app.infrastructure.database import init_db

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:    %(name)s - %(message)s'
)

app = FastAPI()

init_db()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(routes_pages.router)
app.include_router(routes_branches.router)
app.include_router(routes_projects.router)
app.include_router(routes_releases.router)
app.include_router(routes_stages.router)
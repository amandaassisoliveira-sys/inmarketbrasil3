from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import freight, tax, auth, simulations
from .db import init_db

app = FastAPI(title="Simulador de Importação — Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(freight.router)
app.include_router(tax.router)
app.include_router(auth.router)
app.include_router(simulations.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}

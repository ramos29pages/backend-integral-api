from fastapi import FastAPI
from app.routers import solicitudes, servicios, procesamiento
from app.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Servicios de Ingeniería")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solicitudes.router, prefix="/api", tags=["Solicitudes"])
app.include_router(servicios.router, prefix="/api", tags=["Servicios"])
app.include_router(procesamiento.router, prefix="/api", tags=["Procesamiento Automático"])

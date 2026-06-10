from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, waybill, temperature, alert, responsibility, claim, audit

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="冷链药品运输后端服务",
    description="管理运单、温度探头采样、断链告警、责任段划分和索赔记录",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(waybill.router)
app.include_router(temperature.router)
app.include_router(alert.router)
app.include_router(responsibility.router)
app.include_router(claim.router)
app.include_router(audit.router)


@app.get("/")
def root():
    return {"service": "冷链药品运输后端服务", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}

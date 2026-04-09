from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import router as api_router
from backend.utils.llm_manager import load_environment


def create_app() -> FastAPI:
	app = FastAPI(
		title="Day5 Hackathon Medical Assistant API",
		version="1.0.0",
	)

	app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	@app.on_event("startup")
	def _on_startup() -> None:
		load_environment()

	app.include_router(api_router)

	@app.get("/")
	def root() -> dict[str, str]:
		return {"message": "Medical assistant backend is running"}

	return app


app = create_app()


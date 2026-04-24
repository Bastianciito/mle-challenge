import pandas as pd
from typing import List, Literal
from pydantic import BaseModel, Field
from challenge.model import DelayModel
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


_model = DelayModel(model_path="/app/artifacts/logistic_regression_to_deploy.joblib")


class FlightInput(BaseModel):
    model_config = {"extra": "forbid"}

    OPERA: Literal[
        "Aerolineas Argentinas",
        "Aeromexico",
        "Air Canada",
        "Air France",
        "Alitalia",
        "American Airlines",
        "Austral",
        "Avianca",
        "British Airways",
        "Copa Air",
        "Delta Air",
        "Gol Trans",
        "Grupo LATAM",
        "Iberia",
        "JetSmart SPA",
        "K.L.M.",
        "Lacsa",
        "Latin American Wings",
        "Oceanair Linhas Aereas",
        "Plus Ultra Lineas Aereas",
        "Qantas Airways",
        "Sky Airline",
        "United Airlines",
    ]
    TIPOVUELO: Literal["N", "I"]
    MES: int = Field(ge=1, le=12)


class PredictRequest(BaseModel):
    flights: List[FlightInput]


@app.get("/health", status_code=200)
async def get_health() -> dict:
    return {"status": "OK"}


@app.post("/predict", status_code=200)
async def post_predict(request: PredictRequest) -> dict:
    df = pd.DataFrame([f.model_dump() for f in request.flights])
    features = _model.preprocess(df)
    predictions = _model.predict(features)
    return {"predict": predictions}

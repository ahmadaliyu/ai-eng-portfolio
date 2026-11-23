"""HTTP layer only: routes, dependencies, error mapping. Logic lives in budget/models/tokens."""

from collections.abc import Mapping
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from context_budget_api.budget import CannotFitError, InvalidReserveError, check_fit, trim_to_fit
from context_budget_api.models import DEFAULT_MODELS, UnknownModelError, context_window
from context_budget_api.schemas import (
    BudgetRequest,
    CountRequest,
    CountResponse,
    FitResponse,
    ModelInfo,
    TrimResponse,
)
from context_budget_api.tokens import HeuristicCounter, TokenCounter, count_tokens

app = FastAPI(title="Context Budget API")


def get_counter() -> TokenCounter:
    return HeuristicCounter()


def get_registry() -> Mapping[str, int]:
    return DEFAULT_MODELS


Counter = Annotated[TokenCounter, Depends(get_counter)]
Registry = Annotated[Mapping[str, int], Depends(get_registry)]


async def _unprocessable(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


for _error in (UnknownModelError, InvalidReserveError, CannotFitError):
    app.add_exception_handler(_error, _unprocessable)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/models")
def list_models(registry: Registry) -> list[ModelInfo]:
    return [ModelInfo(name=name, context_window=registry[name]) for name in sorted(registry)]


@app.post("/count")
def count(body: CountRequest, counter: Counter) -> CountResponse:
    return CountResponse(tokens=count_tokens(counter, body.messages))


@app.post("/fit")
def fit(body: BudgetRequest, counter: Counter, registry: Registry) -> FitResponse:
    window = context_window(registry, body.model)
    result = check_fit(body.messages, counter, window, body.reserve_output_tokens)
    return FitResponse(
        fits=result.fits, tokens=result.tokens, budget=result.budget, remaining=result.remaining
    )


@app.post("/trim")
def trim(body: BudgetRequest, counter: Counter, registry: Registry) -> TrimResponse:
    window = context_window(registry, body.model)
    result = trim_to_fit(body.messages, counter, window, body.reserve_output_tokens)
    return TrimResponse(
        messages=result.messages,
        tokens=result.tokens,
        budget=result.budget,
        dropped=result.dropped,
    )

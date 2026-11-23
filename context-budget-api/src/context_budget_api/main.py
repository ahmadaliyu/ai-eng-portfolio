from fastapi import FastAPI

app = FastAPI(title="Context Budget API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

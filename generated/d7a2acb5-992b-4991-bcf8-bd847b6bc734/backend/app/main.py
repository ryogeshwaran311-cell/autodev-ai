from fastapi import FastAPI

app = FastAPI(
    title="Generated AutoDev API"
)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/items")
def items():
    return {"items": []}

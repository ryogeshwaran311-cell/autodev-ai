from fastapi import FastAPI

app = FastAPI(title="AutoDev AI API")


@app.get("/health")
def health():
    return {"status": "ok", "service": "autodev-ai-api"}

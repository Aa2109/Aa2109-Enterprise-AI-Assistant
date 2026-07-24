from fastapi import FastAPI

app = FastAPI(title="Enterprise AI Knowledge Assistant", version="0.1.0")


@app.get("/")
def root():
    return {"message": "Enterprise AI Assistant API"}


@app.get("/health")
def health():
    return {"status": "healthy"}

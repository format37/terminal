from fastapi import FastAPI
app = FastAPI()

@app.get("/calculate")
async def calculate(a: int, b: int):
    return a + b

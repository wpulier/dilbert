from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello, world!"}

@app.get("/python-version")
async def get_python_version():
    import sys
    return {"python_version": sys.version}

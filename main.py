from fastapi import FastAPI

from unicorn.server import Server

app = FastAPI(debug=True)


@app.get("/")
async def index():
    return {"message": "Hello, World!"}


if __name__ == "__main__":
    Server(app=app).run()

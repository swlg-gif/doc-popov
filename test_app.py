from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request

app = FastAPI()

# Статические файлы
app.mount("/static", StaticFiles(directory="/home/deploy/pediatric-crm/app/static"), name="static")
templates = Jinja2Templates(directory="/home/deploy/pediatric-crm/app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return """
    <html>
        <head>
            <title>Test App</title>
            <link rel="stylesheet" href="/static/css/style.css">
        </head>
        <body>
            <h1>Тестовое приложение работает!</h1>
            <p>Если это видно со стилями - проблема в основном приложении.</p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

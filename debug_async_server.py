import uvicorn

if __name__ == '__main__':
    uvicorn.run("alpha.asgi:application", host='0.0.0.0', reload=True)

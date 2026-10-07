"""সুরক্ষা Wallet API and web app.   Run:  uvicorn app.main:app --port 8000"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import ROOT, settings
from .db import init_db
from .routers import analyst, auth, customer

STATIC = ROOT / 'app/static'


@asynccontextmanager
async def lifespan(_):
    init_db()
    yield

app = FastAPI(title='Surokkha Wallet', version='2.0.0', lifespan=lifespan,
              docs_url='/api/docs' if settings.environment != 'production' else None, redoc_url=None)
if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(',')], allow_credentials=True,
                       allow_methods=['GET', 'POST', 'PUT'], allow_headers=['content-type', 'x-device-id'])
for r in (auth.router, customer.router, analyst.router):
    app.include_router(r)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update({'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
                             'Permissions-Policy': 'camera=(self), geolocation=(self), microphone=()',
                             'Content-Security-Policy': "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"})
    if request.url.path.startswith('/api/docs'):
        del response.headers['Content-Security-Policy']      # interactive docs load their own assets (disabled in production)
    elif request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(ValueError)
async def bad_request(_, exc):
    return JSONResponse({'detail': str(exc)}, status_code=400)


@app.exception_handler(LookupError)
async def not_found(_, exc):
    return JSONResponse({'detail': str(exc).strip("'")}, status_code=404)


@app.exception_handler(PermissionError)
async def forbidden(_, exc):
    return JSONResponse({'detail': str(exc)}, status_code=403)


@app.get('/healthz')
def health():
    return {'status': 'ok'}


if (STATIC / 'assets').exists():
    app.mount('/assets', StaticFiles(directory=STATIC / 'assets'), name='assets')


@app.get('/{path:path}', include_in_schema=False)
def spa(path: str):
    if path.startswith('api/'):
        return JSONResponse({'detail': 'Not found.'}, status_code=404)
    target = (STATIC / path).resolve()
    if path and target.is_file() and STATIC.resolve() in target.parents:
        return FileResponse(target)
    if (STATIC / 'index.html').exists():
        return FileResponse(STATIC / 'index.html')
    return JSONResponse({'detail': 'Frontend not built. Run "npm run build" in frontend/.'}, status_code=404)

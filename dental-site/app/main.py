"""FastAPI entry point and routing for the official Dental Clinic website."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import CLINIC_INFO, is_clinic_open_now
from app.database import init_dental_db
from app.security import SecurityHeadersMiddleware
from app.translations import TRANSLATIONS

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize SQLite schema in dev; production environments manage schema via Alembic."""
    init_dental_db()
    yield


app = FastAPI(
    title="Dental Clinic Official Website",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def resolve_lang(lang: str) -> str:
    """Normalize supported language route prefixes (/en and /kh)."""
    return "kh" if lang == "kh" else "en"


def build_base_context(request: Request, lang: str, active_nav: str = "home") -> Dict:
    """Build shared template context including language-preserving switcher URLs."""
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    path = request.url.path
    if path.startswith("/en/"):
        suffix = path[3:]
    elif path.startswith("/kh/"):
        suffix = path[3:]
    elif path in ("/en", "/kh"):
        suffix = "/"
    else:
        suffix = "/"

    return {
        "lang": lang,
        "t": t,
        "clinic": CLINIC_INFO,
        "clinic_open": is_clinic_open_now(),
        "active_nav": active_nav,
        "switch_en_url": f"/en{suffix}",
        "switch_kh_url": f"/kh{suffix}",
    }


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Liveness health check endpoint."""
    return {"status": "ok"}


@app.get("/", response_class=RedirectResponse)
def root_redirect() -> RedirectResponse:
    """Redirect bare root to default English clinic home."""
    return RedirectResponse(url="/en/", status_code=302)


@app.get("/en", response_class=RedirectResponse)
@app.get("/kh", response_class=RedirectResponse)
def trailing_lang_redirect(request: Request) -> RedirectResponse:
    """Normalize /en -> /en/ and /kh -> /kh/."""
    lang = "kh" if request.url.path.startswith("/kh") else "en"
    return RedirectResponse(url=f"/{lang}/", status_code=302)


@app.get("/{lang}/", response_class=HTMLResponse)
def home_page(lang: str, request: Request) -> HTMLResponse:
    if lang not in ("en", "kh"):
        raise StarletteHTTPException(status_code=404)
    ctx = build_base_context(request, lang, active_nav="home")
    return templates.TemplateResponse(request=request, name="home.html", context=ctx)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Render accessible bilingual 404 page instead of raw JSON/stack traces."""
    if exc.status_code == 404:
        lang = "kh" if request.url.path.startswith("/kh") else "en"
        ctx = build_base_context(request, lang, active_nav="")
        return templates.TemplateResponse(
            request=request, name="404.html", context=ctx, status_code=404
        )
    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)

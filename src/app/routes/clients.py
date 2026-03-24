from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlmodel import Session, select
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ..db import get_session
from ..models import Client
from ..schemas import ClientCreate, ClientRead

router = APIRouter(prefix="/clients", tags=["clients"])

# Template setup
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/create", response_class=HTMLResponse)
def client_create_form(
    request: Request,
):
    """Render client creation form — must be before /{client_id} to avoid route shadowing"""
    return templates.TemplateResponse("clients/create.html", {
        "request": request,
        "errors": {},
    })


@router.post("/create", response_class=RedirectResponse)
def create_client_form(
    name: str = Form(...),
    session: Session = Depends(get_session),
):
    """Create a new client from HTML form submission"""
    db_client = Client(name=name)
    session.add(db_client)
    session.commit()
    session.refresh(db_client)
    return RedirectResponse(url="/jobs/create", status_code=303)


@router.post("/", response_model=ClientRead)
def create_client(
    client_in: ClientCreate,
    session: Session = Depends(get_session),
):
    """Create a new client via JSON API"""
    db_client = Client(name=client_in.name)
    session.add(db_client)
    session.commit()
    session.refresh(db_client)
    return db_client


@router.get("/", response_model=list[ClientRead])
def list_clients(
    session: Session = Depends(get_session),
):
    """List all clients for dropdown in job form"""
    clients = session.exec(select(Client)).all()
    return clients


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: int,
    session: Session = Depends(get_session),
):
    """Get a specific client by ID"""
    client = session.exec(select(Client).where(Client.id == client_id)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

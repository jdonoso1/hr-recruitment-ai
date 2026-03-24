from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ..db import get_session
from ..models import Client
from ..schemas import ClientCreate, ClientRead

router = APIRouter(prefix="/clients", tags=["clients"])

# Template setup
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.post("/", response_model=ClientRead)
def create_client(
    client_in: ClientCreate,
    session: Session = Depends(get_session),
):
    """Create a new client (Phase 1: minimal client creation for job FK)"""
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


@router.get("/create", response_class=HTMLResponse)
def client_create_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Render client creation form"""
    return templates.TemplateResponse("clients/create.html", {
        "request": request,
        "errors": {},
    })

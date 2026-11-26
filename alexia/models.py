from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RoleInfo(BaseModel):
    id: str
    nombre: str = ""
    raw: Dict[str, Any] = Field(default_factory=dict)


class AuthSession(BaseModel):
    user: Optional[str] = None
    token: str
    rol: Optional[str] = None
    roles: List[RoleInfo] = Field(default_factory=list)
    ruta_home: Optional[str] = None
    cookies: Dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_authenticated(self) -> bool:
        return bool(self.cookies and (".ASPXAUTH" in self.cookies or any("ASPXAUTH" in k for k in self.cookies)))


class AttachmentItem(BaseModel):
    id: Optional[str] = None
    filename: str
    url: Optional[str] = None
    token: Optional[str] = None
    size: Optional[int] = None


class NotificationItem(BaseModel):
    id: str
    title: str
    date: Optional[str] = None
    sender: Optional[str] = None
    read: bool = False
    summary: Optional[str] = None
    has_attachments: bool = False
    attachments: List[AttachmentItem] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)


class NotificationDetail(BaseModel):
    id: str
    title: str
    body: str = ""
    date: Optional[str] = None
    sender: Optional[str] = None
    read: bool = False
    attachments: List[AttachmentItem] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)


class DownloadResult(BaseModel):
    filename: str
    saved_path: str
    size_bytes: int
    content_type: Optional[str] = None


class StudentItem(BaseModel):
    id: str
    persona_key: Optional[str] = None
    nombre: str
    parentesco: str = "Hijo/a"
    curso: Optional[str] = None
    matriculas: List[str] = Field(default_factory=list)
    foto_url: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


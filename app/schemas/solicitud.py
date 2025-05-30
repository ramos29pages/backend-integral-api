from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
from app.models.solicitud import EstadoSolicitud # Importa el Enum real del modelo
from app.schemas.servicio import ServicioOut # Importa el esquema de salida de servicio

class SolicitudBase(BaseModel):
    cliente: str = Field(..., min_length=1, max_length=100, description="Nombre de la empresa o persona solicitante.")
    email_cliente: EmailStr = Field(..., description="Dirección de correo electrónico del cliente para notificaciones.")
    observaciones: Optional[str] = Field(None, max_length=500, description="Campo de texto libre para observaciones adicionales.")

    class Config:
        from_attributes = True

class SolicitudCreate(SolicitudBase):
    """Esquema para la creación de una nueva solicitud."""
    pass

class SolicitudUpdate(BaseModel):
    """Esquema para la actualización de una solicitud existente, con todos los campos opcionales."""
    cliente: Optional[str] = Field(None, min_length=1, max_length=100, description="Nuevo nombre de la empresa o persona solicitante.")
    email_cliente: Optional[EmailStr] = Field(None, description="Nueva dirección de correo electrónico del cliente.")
    observaciones: Optional[str] = Field(None, max_length=500, description="Nuevas observaciones para la solicitud.")
    estado: Optional[EstadoSolicitud] = Field(None, description="Nuevo estado de la solicitud.") # Usar el Enum aquí

    class Config:
        from_attributes = True

class SolicitudOut(SolicitudBase):
    """Esquema para la salida de una solicitud, incluyendo su ID y la lista de servicios asociados."""
    id: int = Field(..., description="Identificador único de la solicitud.")
    fecha_solicitud: datetime = Field(..., description="Fecha de creación de la solicitud.")
    estado: EstadoSolicitud = Field(..., description="Estado actual de la solicitud.") # Usar el Enum
    fecha_ultima_modificacion: datetime = Field(..., description="Última fecha de modificación de la solicitud.")
    servicios: List[ServicioOut] = Field(default_factory=list, description="Lista de servicios asociados a esta solicitud.") # Usa default_factory para list

    class Config:
        from_attributes = True
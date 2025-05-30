from pydantic import BaseModel, Field, EmailStr, ValidationError, validator
from typing import Optional, List
from datetime import datetime, date # Importa 'date' para comparaciones de fecha
from app.models.servicio import EstadoServicio # Importa el Enum real del modelo

class ServicioBase(BaseModel):
    nombre_servicio: str = Field(..., min_length=1, max_length=255, description="Descripción del servicio solicitado.")
    fecha_reunion: datetime = Field(..., description="Fecha y hora programada para la reunión de evaluación.")
    comentarios: Optional[str] = Field(None, max_length=500, description="Observaciones adicionales sobre la reunión.")
    costo_estimado: Optional[float] = Field(None, ge=0, description="Costo estimado del servicio (solo si está aprobado).")

    @validator("fecha_reunion")
    def fecha_reunion_debe_ser_futura(cls, v):
        """Valida que la fecha de reunión sea futura."""
        # Se compara solo la parte de la fecha para evitar problemas con la hora exacta de la validación
        if v.date() < datetime.utcnow().date():
            raise ValueError("La fecha de reunión debe ser futura.")
        return v

    class Config:
        # Permite que el ORM (SQLAlchemy) sepa cómo mapear los campos
        # En Pydantic v2+, from_attributes = True reemplaza orm_mode = True
        from_attributes = True

class ServicioCreate(ServicioBase):
    """Esquema para la creación de un nuevo servicio."""
    # No se necesita estado_servicio aquí, ya que el modelo lo inicializa a PENDIENTE
    pass

class ServicioUpdate(BaseModel):
    """Esquema para la actualización de un servicio existente, con todos los campos opcionales."""
    nombre_servicio: Optional[str] = Field(None, min_length=1, max_length=255, description="Descripción del servicio solicitado.")
    fecha_reunion: Optional[datetime] = Field(None, description="Nueva fecha y hora programada para la reunión de evaluación.")
    estado_servicio: Optional[EstadoServicio] = Field(None, description="Estado actual del servicio.") # Usar el Enum
    comentarios: Optional[str] = Field(None, max_length=500, description="Nuevas observaciones de la reunión.")
    costo_estimado: Optional[float] = Field(None, ge=0, description="Nuevo costo estimado del servicio.")

    @validator("fecha_reunion", pre=True, always=True)
    def fecha_reunion_debe_ser_futura_update(cls, v):
        """Valida que la fecha de reunión (si se proporciona) sea futura."""
        if v is not None and v.date() < datetime.utcnow().date():
            raise ValueError("La fecha de reunión debe ser futura.")
        return v
    
    class Config:
        from_attributes = True


class ServicioOut(ServicioBase):
    """Esquema para la salida de un servicio, incluyendo su ID y estado actual."""
    id: int = Field(..., description="Identificador único del servicio.")
    estado_servicio: EstadoServicio = Field(..., description="Estado actual del servicio.") # Usar el Enum
    
    class Config:
        from_attributes = True
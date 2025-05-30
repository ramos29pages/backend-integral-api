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

class ServicioCreate(BaseModel):
    """
    Esquema Pydantic para crear un nuevo servicio.
    Incluye validaciones para campos obligatorios y formato de fecha.
    """
    nombre_servicio: str = Field(..., min_length=1, max_length=255, description="Descripción del servicio (requerido).")
    fecha_reunion: date = Field(..., description="Fecha programada para evaluación (debe ser futura).")
    comentarios: Optional[str] = Field(None, max_length=500, description="Observaciones de la reunión (opcional).")
    costo_estimado: Optional[float] = Field(None, ge=0, description="Valor monetario (opcional, solo si está aprobado).")

    @validator('fecha_reunion')
    def validate_fecha_reunion_futura(cls, v):
        """
        Validador para asegurar que la fecha de reunión sea futura.
        """
        if v < date.today():
            raise ValueError('La fecha de reunión debe ser futura.')
        return v

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

class ServicioOut(BaseModel):
    """
    Esquema Pydantic para la salida de un servicio.
    """
    id_servicio: int = Field(..., description="Identificador único del servicio.")
    id_solicitud: int = Field(..., description="ID de la solicitud a la que pertenece este servicio.")
    nombre_servicio: str
    fecha_reunion: date # Se espera que la fecha se serialice a formato de fecha
    estado_servicio: EstadoServicio
    comentarios: Optional[str]
    costo_estimado: Optional[float]

    class Config:
        orm_mode = True # Habilita la compatibilidad con ORM (SQLAlchemy)
        use_enum_values = True # Permite que los Enums se serialicen a sus valores directos
        # Configuración para manejar la conversión de datetime a date si es necesario
        json_encoders = {
            datetime: lambda v: v.date().isoformat() if isinstance(v, datetime) else v.isoformat(),
            date: lambda v: v.isoformat()
        }
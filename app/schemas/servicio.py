from pydantic import BaseModel, Field, EmailStr, ValidationError, validator
from typing import Optional, List
from datetime import datetime, date # Importa 'date' para comparaciones de fecha
from app.models.servicio import EstadoServicio # Importa el Enum real del modelo
from datetime import datetime, date
from pydantic import validator
from dateutil.parser import parse  # necesitas instalar python-dateutil si no está

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
    'fecha_reunion' ahora es datetime para coincidir con el modelo ORM.
    """
    nombre_servicio: str = Field(..., min_length=1, max_length=255, description="Descripción del servicio (requerido).")
    fecha_reunion: datetime = Field(..., description="Fecha y hora programada para evaluación (debe ser futura).") # Cambiado a datetime
    comentarios: Optional[str] = Field(None, max_length=500, description="Observaciones de la reunión (opcional).")
    costo_estimado: Optional[float] = Field(None, ge=0, description="Valor monetario (opcional, solo si está aprobado).")

    @validator('fecha_reunion')
    def validate_fecha_reunion_futura(cls, v):
        """
        Validador para asegurar que la fecha de reunión sea futura.
        Compara solo la parte de la fecha para evitar problemas de tiempo.
        """
        # Compara la parte de la fecha de la fecha de reunión con la fecha actual (UTC)
        if v.date() < datetime.utcnow().date():
            raise ValueError('La fecha de reunión debe ser futura.')
        return v

class ServicioOut(BaseModel):
    """
    Esquema Pydantic para la salida de un servicio.
    'fecha_reunion' ahora es datetime.
    """
    id_servicio: int
    id_solicitud: int
    nombre_servicio: str
    fecha_reunion: datetime # Cambiado a datetime
    estado_servicio: EstadoServicio
    comentarios: Optional[str]
    costo_estimado: Optional[float]

    class Config:
        orm_mode = True # Habilita la compatibilidad con ORM (SQLAlchemy)
        use_enum_values = True # Permite que los Enums se serialicen a sus valores directos
        # No se necesita json_encoders si el frontend envía ISO 8601 datetime strings
        # y Pydantic maneja objetos datetime directamente.

class ServicioUpdate(BaseModel):
    """
    Esquema Pydantic para actualizar un servicio.
    Todos los campos son opcionales. 'fecha_reunion' es datetime.
    """
    nombre_servicio: Optional[str] = Field(None, min_length=1, max_length=255)
    fecha_reunion: Optional[datetime] = Field(None) # Cambiado a datetime
    comentarios: Optional[str] = Field(None, max_length=500)
    costo_estimado: Optional[float] = Field(None, ge=0)
    estado_servicio: Optional[EstadoServicio] = Field(None) # Permite actualizar el estado

    @validator('fecha_reunion')
    def validate_fecha_reunion_futura_update(cls, v):
        """
        Valida que la fecha de reunión (datetime, date o string ISO) sea futura.
        """
        if v is not None:
            # Intenta convertir a datetime si es string
            if isinstance(v, str):
                try:
                    v = parse(v)
                except Exception:
                    raise ValueError('Formato de fecha inválido.')
            
            # Convertir a date si es datetime
            fecha = v if isinstance(v, date) and not isinstance(v, datetime) else v.date()

            if fecha < datetime.utcnow().date():
                raise ValueError('La fecha de reunión debe ser futura.')
        
        return v

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
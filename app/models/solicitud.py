# app/models/solicitud.py
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base # Importa la Base de tu archivo database.py
import enum

# Definición del Enum para los estados de la Solicitud
class EstadoSolicitud(str, enum.Enum):
    ABIERTA = "Abierta"
    EN_PROCESO = "En Proceso"
    CERRADA = "Cerrada"
    CANCELADA = "Cancelada"
    
class SolicitudEstado(str, enum.Enum):
    ABIERTA = "Abierta"
    EN_PROCESO = "En Proceso"
    CERRADA = "Cerrada"
    CANCELADA = "Cancelada"

# Modelo ORM para la tabla 'solicitudes'
class Solicitud(Base):
    __tablename__ = "solicitudes"
    id = Column(Integer, primary_key=True, index=True)
    cliente = Column(String(100), nullable=False)
    email_cliente = Column(String(255), nullable=False)
    fecha_solicitud = Column(DateTime, default=datetime.utcnow) # Fecha de creación (UTC)
    estado = Column(Enum(EstadoSolicitud), default=EstadoSolicitud.ABIERTA) # Estado inicial
    observaciones = Column(String(500))
    fecha_ultima_modificacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # Actualiza en cada modificación

    # Define la relación con el modelo Servicio.
    # 'servicios' es el nombre del atributo que contendrá una lista de objetos Servicio.
    # 'back_populates' apunta al atributo 'solicitud' en el modelo Servicio.
    # 'cascade="all, delete-orphan"' asegura que si una Solicitud es eliminada,
    # todos sus Servicios asociados también lo serán.
    servicios = relationship("Servicio", back_populates="solicitud", cascade="all, delete-orphan")


from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum


class SolicitudEstado(str, Enum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"

class EstadoSolicitud(str, enum.Enum):
    ABIERTA = "Abierta"
    EN_PROCESO = "En Proceso"
    CERRADA = "Cerrada"
    CANCELADA = "Cancelada"

class Solicitud(Base):
    __tablename__ = "solicitudes"
    id = Column(Integer, primary_key=True, index=True)
    cliente = Column(String(100), nullable=False)
    email_cliente = Column(String(255), nullable=False)
    fecha_solicitud = Column(DateTime, default=datetime.utcnow)
    estado = Column(Enum(EstadoSolicitud), default=EstadoSolicitud.ABIERTA)
    observaciones = Column(String(500))
    fecha_ultima_modificacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    servicios = relationship("Servicio", back_populates="solicitud", cascade="all, delete-orphan")

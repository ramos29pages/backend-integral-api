from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum

class EstadoServicio(str, enum.Enum):
    PENDIENTE = "Pendiente"
    APROBADO = "Aprobado"
    RECHAZADO = "Rechazado"
    VENCIDO = "Vencido"

class Servicio(Base):
    __tablename__ = "servicios"
    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), nullable=False)
    nombre_servicio = Column(String(255), nullable=False)
    fecha_reunion = Column(DateTime, nullable=False)
    estado_servicio = Column(Enum(EstadoServicio), default=EstadoServicio.PENDIENTE)
    comentarios = Column(String(500), nullable=True)
    costo_estimado = Column(Float, nullable=True)

    solicitud = relationship("Solicitud", back_populates="servicios")

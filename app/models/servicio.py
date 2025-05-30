# app/models/servicio.py
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base # Importa la Base de tu archivo database.py
import enum

# Definición del Enum para los estados del Servicio
class EstadoServicio(str, enum.Enum):
    PENDIENTE = "Pendiente"
    APROBADO = "Aprobado"
    RECHAZADO = "Rechazado"
    VENCIDO = "Vencido"

# Modelo ORM para la tabla 'servicios'
class Servicio(Base):
    __tablename__ = "servicios"
    id_servicio = Column(Integer, primary_key=True, index=True) # ID único para el servicio
    id_solicitud = Column(Integer, ForeignKey("solicitudes.id"), nullable=False) # Clave foránea a Solicitud
    nombre_servicio = Column(String(255), nullable=False)
    fecha_reunion = Column(DateTime, nullable=False) # Fecha programada para la reunión
    estado_servicio = Column(Enum(EstadoServicio), default=EstadoServicio.PENDIENTE) # Estado inicial del servicio
    comentarios = Column(String(500))
    costo_estimado = Column(Float)

    # Define la relación con el modelo Solicitud.
    # 'solicitud' es el nombre del atributo que contendrá el objeto Solicitud padre.
    # 'back_populates' apunta al atributo 'servicios' en el modelo Solicitud.
    solicitud = relationship("Solicitud", back_populates="servicios")

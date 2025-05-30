from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date # Importamos date para comparaciones de fecha
from app.database import get_db
from app.models.solicitud import SolicitudEstado, EstadoSolicitud # Usamos el Enum correcto
from app.models.servicio import EstadoServicio
from app.models import solicitud as solicitud_model
from app.models import servicio as servicio_model

router = APIRouter(tags=["Procesamiento Automático"])

@router.post("/procesar_solicitudes", summary="Procesa servicios vencidos y cierra solicitudes completadas")
def procesar_solicitudes_pendientes(db: Session = Depends(get_db)):
    """
    Este endpoint simula una tarea programada que realiza las siguientes acciones:
    1. Marca como 'Vencidos' los servicios en estado 'Pendiente' cuya fecha de reunión ya pasó.
    2. Cambia el estado de las solicitudes a 'Cerrada' si todos sus servicios
       han finalizado (Aprobado, Rechazado o Vencido).
    """
    hoy = datetime.utcnow().date() # Usamos UTC para consistencia y solo la fecha

    total_servicios_vencidos = 0
    total_solicitudes_cerradas = 0

    # 1. Marcar servicios vencidos
    # Corregido: Usar servicio_model.Servicio y estado_servicio
    servicios_a_vencer = db.query(servicio_model.Servicio).filter(
        servicio_model.Servicio.estado_servicio == EstadoServicio.PENDIENTE,
        servicio_model.Servicio.fecha_reunion.has_current_date() < hoy # Comparar solo la fecha
    ).all()

    for servicio in servicios_a_vencer:
        servicio.estado_servicio = EstadoServicio.VENCIDO
        total_servicios_vencidos += 1
    
    # 2. Cerrar solicitudes si todos sus servicios están en estado final
    # Es más eficiente obtener solo las solicitudes que están Abiertas o En Proceso
    solicitudes_activas = db.query(solicitud_model.Solicitud).filter(
        solicitud_model.Solicitud.estado.in_([EstadoSolicitud.ABIERTA, EstadoSolicitud.EN_PROCESO])
    ).all()

    for solicitud in solicitudes_activas:
        servicios = solicitud.servicios
        # Si la solicitud tiene servicios y TODOS están en un estado final
        if servicios and all(s.estado_servicio in [EstadoServicio.APROBADO, EstadoServicio.RECHAZADO, EstadoServicio.VENCIDO] for s in servicios):
            if solicitud.estado != EstadoSolicitud.CERRADA: # Asegurarse de no intentar cerrar una ya cerrada
                solicitud.estado = EstadoSolicitud.CERRADA
                solicitud.fecha_ultima_modificacion = datetime.utcnow() # Actualizar timestamp
                total_solicitudes_cerradas += 1

    db.commit()

    return {
        "mensaje": "Procesamiento completado correctamente.",
        "servicios_marcados_vencidos": total_servicios_vencidos,
        "solicitudes_cerradas_automaticamente": total_solicitudes_cerradas
    }
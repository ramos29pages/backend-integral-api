from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.database import get_db
from app.models.solicitud import SolicitudEstado, EstadoSolicitud # Usamos el Enum correcto
from app.models.servicio import EstadoServicio
from app.models import solicitud as solicitud_model
from app.models import servicio as servicio_model
from sqlalchemy import func # Importar func para la fecha

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

    try:
        # 1. Marcar servicios vencidos
        servicios_a_vencer = db.query(servicio_model.Servicio).filter(
            servicio_model.Servicio.estado_servicio == EstadoServicio.PENDIENTE,
            # SOLUCIÓN AL ERROR ANTERIOR: Usar func.DATE()
            func.DATE(servicio_model.Servicio.fecha_reunion) < hoy
        ).all()

        for servicio in servicios_a_vencer:
            servicio.estado_servicio = EstadoServicio.VENCIDO
            # No necesitas db.add() aquí si el objeto ya está gestionado por la sesión
            total_servicios_vencidos += 1
        
        # 2. Cerrar solicitudes si todos sus servicios están en estado final
        solicitudes_activas = db.query(solicitud_model.Solicitud).filter(
            solicitud_model.Solicitud.estado.in_([EstadoSolicitud.ABIERTA, EstadoSolicitud.EN_PROCESO])
        ).all()

        for solicitud in solicitudes_activas:
            servicios = solicitud.servicios
            # Si la solicitud tiene servicios y TODOS están en un estado final
            if servicios and all(s.estado_servicio in [EstadoServicio.APROBADO, EstadoServicio.RECHAZADO, EstadoServicio.VENCIDO] for s in servicios):
                if solicitud.estado != EstadoSolicitud.CERRADA:
                    solicitud.estado = EstadoSolicitud.CERRADA
                    solicitud.fecha_ultima_modificacion = datetime.utcnow()
                    # No necesitas db.add() aquí si el objeto ya está gestionado por la sesión
                    total_solicitudes_cerradas += 1

        # Si todo lo anterior se ejecutó sin errores, entonces confirmamos los cambios.
        db.commit()

        return {
            "mensaje": "Procesamiento completado correctamente.",
            "servicios_marcados_vencidos": total_servicios_vencidos,
            "solicitudes_cerradas_automaticamente": total_solicitudes_cerradas
        }

    except Exception as e:
        # Si ocurre CUALQUIER error en el bloque try, deshacemos todos los cambios
        # que se hayan acumulado en la sesión desde el inicio de la función.
        db.rollback()
        print(f"Error durante el procesamiento de solicitudes: {e}") # Para depuración
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor durante el procesamiento: {e}"
        )
    # No es necesario un 'finally' aquí a menos que tengas recursos que necesites cerrar explícitamente,
    # pero FastAPI y Depends se encargan de cerrar la sesión de DB por ti.
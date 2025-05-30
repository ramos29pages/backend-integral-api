from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date # Import date for date comparisons
from app.database import get_db
from app.models import servicio as models_servicio
from app.models.servicio import EstadoServicio
from app.schemas.servicio import ServicioOut, ServicioCreate, ServicioUpdate # Import ServicioUpdate

router = APIRouter(prefix="/servicios", tags=["Servicios"])

@router.put("/{id}", response_model=ServicioOut, summary="Actualizar un servicio por ID")
def update_servicio(id: int, servicio_update: ServicioUpdate, db: Session = Depends(get_db)):
    """
    Actualiza los campos de un servicio existente.
    Incluye validaciones para la fecha de reunión y el costo estimado.
    """
    servicio = db.query(models_servicio.Servicio).filter(models_servicio.Servicio.id_servicio == id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    # La validación de fecha futura ahora se maneja en el validador de Pydantic de ServicioUpdate
    # No es necesario un chequeo manual aquí a menos que quieras una lógica de error muy específica.

    # Validación de regla de negocio: costo_estimado solo si el servicio está APROBADO
    if servicio_update.estado_servicio is not None:
        if servicio_update.estado_servicio != EstadoServicio.APROBADO and servicio_update.costo_estimado is not None:
            raise HTTPException(status_code=400, detail="No se puede establecer un costo estimado si el servicio no está en estado 'Aprobado'.")
        elif servicio_update.estado_servicio != EstadoServicio.APROBADO and servicio.costo_estimado is not None:
            # Si el estado cambia de APROBADO a no APROBADO y hay un costo existente, lo limpiamos
            servicio.costo_estimado = None
    elif servicio_update.costo_estimado is not None and servicio.estado_servicio != EstadoServicio.APROBADO:
        raise HTTPException(status_code=400, detail="El costo estimado solo puede establecerse para servicios en estado 'Aprobado'.")

    # Actualizar los campos del servicio
    # Usar .model_dump(exclude_unset=True) para obtener solo los campos que se enviaron en la solicitud
    for key, value in servicio_update.model_dump(exclude_unset=True).items():
        # Excluir 'id_servicio' de ser actualizado si se envía (no debería ser editable)
        if key == "id_servicio":
            continue
        setattr(servicio, key, value)

    # REMOVED: servicio.fecha_ultima_modificacion = datetime.utcnow()
    # Tu modelo 'Servicio' no tiene la columna 'fecha_ultima_modificacion'.
    # Si la necesitas, agrégala explícitamente a app/models/servicio.py.

    db.commit()
    db.refresh(servicio)
    return servicio

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un servicio por ID")
def delete_servicio(id: int, db: Session = Depends(get_db)):
    """
    Elimina un servicio existente.
    No se puede eliminar un servicio que está en estado "Aprobado".
    """
    servicio = db.query(models_servicio.Servicio).filter(models_servicio.Servicio.id_servicio == id).first() # Corrected: use id_servicio
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    if servicio.estado_servicio == EstadoServicio.APROBADO:
        raise HTTPException(status_code=400, detail="No se puede eliminar un servicio que está en estado 'Aprobado'.")

    db.delete(servicio)
    db.commit()
    

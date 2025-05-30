from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date # Importamos date para comparaciones de fecha
from app.database import get_db
from app.models import servicio as models_servicio
from app.models.servicio import EstadoServicio # Importar el Enum correcto
from app.schemas.servicio import ServicioOut, ServicioUpdate

router = APIRouter(prefix="/servicios", tags=["Servicios"]) # Prefijo y tag para OpenAPI

# Dependencia de la base de datos (se mantiene aquí si solo este router la usa, o se centraliza)
# Si ya tienes get_db en app.database, puedes quitarlo de aquí para evitar duplicidad
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# Actualizar un servicio
@router.put("/{id}", response_model=ServicioOut, summary="Actualizar un servicio por ID")
def update_servicio(id: int, servicio_update: ServicioUpdate, db: Session = Depends(get_db)):
    servicio = db.query(models_servicio.Servicio).filter(models_servicio.Servicio.id == id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    # Validación de regla de negocio: La fecha de reunión debe ser futura
    if servicio_update.fecha_reunion is not None: # Usar fecha_reunion, no fecha_ejecucion
        # Comparar solo la fecha, usando datetime.utcnow().date()
        if servicio_update.fecha_reunion.date() < datetime.utcnow().date():
            raise HTTPException(status_code=400, detail="La fecha de reunión debe ser futura.")

    # Validación de regla de negocio: costo_estimado solo si el servicio está APROBADO
    # Si el estado se actualiza a NO APROBADO y tiene costo_estimado, se limpia o se advierte
    if servicio_update.estado_servicio is not None:
        if servicio_update.estado_servicio != EstadoServicio.APROBADO and servicio.costo_estimado is not None:
            # Puedes decidir si lanzar un error o simplemente limpiar el costo_estimado
            # Opción 1: Lanzar error
            # raise HTTPException(status_code=400, detail="El costo estimado solo puede establecerse para servicios aprobados.")
            # Opción 2: Limpiar automáticamente el costo_estimado
            if servicio_update.costo_estimado is not None: # Si se está intentando actualizar costo_estimado
                 raise HTTPException(status_code=400, detail="No se puede establecer un costo estimado si el servicio no está en estado 'Aprobado'.")
            else: # Si se cambia el estado a no Aprobado, limpiamos el costo existente
                 servicio.costo_estimado = None
    elif servicio_update.costo_estimado is not None and servicio.estado_servicio != EstadoServicio.APROBADO:
        raise HTTPException(status_code=400, detail="El costo estimado solo puede establecerse para servicios en estado 'Aprobado'.")

    # Actualizar los campos del servicio
    for key, value in servicio_update.model_dump(exclude_unset=True).items(): # Usar .model_dump() para Pydantic v2+
        setattr(servicio, key, value)

    servicio.fecha_ultima_modificacion = datetime.utcnow() # Actualizar timestamp

    db.commit()
    db.refresh(servicio)
    return servicio

# Eliminar un servicio
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un servicio por ID")
def delete_servicio(id: int, db: Session = Depends(get_db)):
    servicio = db.query(models_servicio.Servicio).filter(models_servicio.Servicio.id == id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    # Regla de negocio: Una solicitud solo puede eliminarse si NINGÚN servicio está en estado "Aprobado"
    # Aunque esta regla se aplica a la solicitud, es una buena práctica verificar aquí si el servicio
    # a eliminar está APROBADO y si esto afectaría la regla de la solicitud padre.
    # En este caso, la regla dice que la *solicitud* no se elimina si tiene *cualquier* aprobado.
    # Pero si eliminas un servicio Aprobado, ¿qué implicación tiene? Para la regla de la solicitud,
    # si tenía otros aprobados, seguiría sin poder eliminarse. Si este era el único, entonces la
    # solicitud podría ser eliminable.
    # Para simplicidad y cumplimiento estricto: un servicio Aprobado NO se debe eliminar.
    if servicio.estado_servicio == EstadoServicio.APROBADO:
        raise HTTPException(status_code=400, detail="No se puede eliminar un servicio que está en estado 'Aprobado'.")

    db.delete(servicio)
    db.commit()
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date, timedelta # Importamos date
from app.database import get_db
from app.models import solicitud as models_solicitud
from app.models import servicio as models_servicio
from app.models.solicitud import EstadoSolicitud, Solicitud # Importar el Enum correcto
from app.models.servicio import EstadoServicio # Importar el Enum correcto
from app.schemas import solicitud as schemas_solicitud
from app.schemas.servicio import ServicioCreate, ServicioOut

router = APIRouter(prefix="/solicitudes", tags=["Solicitudes"])

@router.post("/", response_model=schemas_solicitud.SolicitudOut, status_code=status.HTTP_201_CREATED, summary="Crear una nueva solicitud")
def create_solicitud(solicitud_in: schemas_solicitud.SolicitudCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva solicitud de ingeniería y sus servicios asociados.
    Requiere al menos un servicio y valida que la fecha de reunión sea futura.
    La operación es atómica: si falla la creación de la solicitud o de alguno de sus servicios,
    toda la transacción se revierte.
    """
    # Pydantic ya validará si `servicios_solicitados` está vacío debido a `min_items=1`
    # en el esquema SolicitudCreate. Si no se envía al menos un servicio, FastAPI
    # devolverá automáticamente un 422 Unprocessable Entity.

    db_solicitud = models_solicitud.Solicitud(
        cliente=solicitud_in.cliente,
        email_cliente=solicitud_in.email_cliente,
        observaciones=solicitud_in.observaciones,
        # fecha_solicitud y fecha_ultima_modificacion se establecen automáticamente por el modelo ORM
        # estado se establece automáticamente a ABIERTA por el modelo ORM
    )

    try:
        db.add(db_solicitud)
        # db.flush() es crucial aquí para que db_solicitud.id esté disponible
        # antes de intentar añadir los servicios, pero sin hacer commit aún.
        db.flush()

        # Iterar sobre los servicios proporcionados y crearlos
        # ¡IMPORTANTE! Aquí se usa `solicitud_in.servicios_solicitados`
        # si tu esquema SolicitudCreate tiene ese nombre de campo.
        # En el código que pegaste, usaste `solicitud_in.servicios`, lo cual
        # podría ser el origen de otra confusión si el esquema no coincide.
        # Asegúrate de que el nombre del campo en SolicitudCreate sea `servicios_solicitados`.
        for servicio_data in solicitud_in.servicios: # <-- Asegúrate de usar el nombre correcto del campo
            # Las validaciones de ServicioCreate (como fecha_reunion futura)
            # ya fueron manejadas por Pydantic antes de llegar a esta función.
            db_servicio = models_servicio.Servicio(
                id_solicitud=db_solicitud.id, # Asocia el servicio con la solicitud recién creada
                nombre_servicio=servicio_data.nombre_servicio,
                # Convertir date a datetime si tu columna es DateTime en el modelo Servicio
                fecha_reunion=datetime.combine(servicio_data.fecha_reunion, datetime.min.time()),
                comentarios=servicio_data.comentarios,
                estado_servicio=EstadoServicio.PENDIENTE # Estado inicial para un nuevo servicio
            )
            db.add(db_servicio)

        db.commit() # Si todo va bien, se hace commit de la solicitud y todos sus servicios.
        db.refresh(db_solicitud) # Refresca la solicitud para cargar los datos generados por la DB (ej. IDs)

        # Cargar explícitamente los servicios para que estén disponibles en la respuesta
        # Esto es necesario si no tienes una relación cargada automáticamente o si necesitas
        # asegurar que los servicios estén en el objeto devuelto.
        # `joinedload` es la forma eficiente de cargar relaciones en SQLAlchemy.
        # Usa el nombre de la relación definida en tu modelo Solicitud, que es 'servicios'.
        db_solicitud_with_services = db.query(models_solicitud.Solicitud).options(
            joinedload(models_solicitud.Solicitud.servicios) # Usar 'servicios' aquí
        ).filter(models_solicitud.Solicitud.id == db_solicitud.id).first()

        # Asegúrate de que el objeto retornado tenga los servicios cargados correctamente
        # Si SolicitudOut espera 'servicios' y el modelo tiene 'servicios', esto debería funcionar.
        return db_solicitud_with_services

    except Exception as e:
        db.rollback()
        print(f"Error durante la creación de solicitud y servicios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la solicitud o sus servicios. Detalle: {e}"
        )

# Obtener una solicitud por ID
@router.get("/{id}", response_model=schemas_solicitud.SolicitudOut, summary="Obtener una solicitud por ID")
def get_solicitud(id: int, db: Session = Depends(get_db)):
    # Usamos joinedload para cargar los servicios junto con la solicitud en una sola consulta
    solicitud = db.query(models_solicitud.Solicitud).options(joinedload(models_solicitud.Solicitud.servicios)).filter(models_solicitud.Solicitud.id == id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud

# Listar solicitudes con filtros y paginación
@router.get("/", summary="Listar solicitudes con filtros y paginación")
def list_solicitudes(
    estado: Optional[EstadoSolicitud] = Query(None),
    cliente: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    ordenar_por: str = Query("fecha_solicitud"),
    orden: str = Query("asc"),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * size
    query = db.query(Solicitud)
    
    if estado:
        query = query.filter(Solicitud.estado == estado)
    if cliente:
        query = query.filter(Solicitud.cliente.ilike(f"%{cliente}%"))
    if fecha_desde:
        query = query.filter(Solicitud.fecha_solicitud >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Solicitud.fecha_solicitud < (fecha_hasta + timedelta(days=1)))
    
    # Ordenamiento
    if hasattr(Solicitud, ordenar_por):
        order_func = getattr(Solicitud, ordenar_por).desc() if orden == "desc" else getattr(Solicitud, ordenar_por).asc()
        query = query.order_by(order_func)
    
    total = query.count()
    solicitudes = query.offset(skip).limit(size).all()
    
    return {
        "content": solicitudes,
        "totalElements": total,
        "totalPages": (total + size - 1) // size,
        "currentPage": page
    }

# Actualizar solicitud
@router.put("/{id}", response_model=schemas_solicitud.SolicitudOut, summary="Actualizar una solicitud por ID")
def update_solicitud(id: int, solicitud_update: schemas_solicitud.SolicitudUpdate, db: Session = Depends(get_db)):
    solicitud = db.query(models_solicitud.Solicitud).options(joinedload(models_solicitud.Solicitud.servicios)).filter(models_solicitud.Solicitud.id == id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Regla de negocio: Una solicitud solo puede modificarse si tiene al menos un servicio en estado "Pendiente"
    if not any(s.estado_servicio == EstadoServicio.PENDIENTE for s in solicitud.servicios):
        raise HTTPException(status_code=400, detail="La solicitud no puede modificarse si no tiene al menos un servicio en estado 'Pendiente'.")

    # Actualizar los campos de la solicitud
    update_data = solicitud_update.model_dump(exclude_unset=True) # Usar .model_dump()
    for key, value in update_data.items():
        # Evitar que se actualice el ID o la fecha de solicitud manualmente
        if key not in ["id", "fecha_solicitud"]:
            setattr(solicitud, key, value)
    
    solicitud.fecha_ultima_modificacion = datetime.utcnow() # Asegurar que se actualice el timestamp

    db.commit()
    db.refresh(solicitud)
    return solicitud

# Eliminar solicitud
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una solicitud por ID")
def delete_solicitud(id: int, db: Session = Depends(get_db)):
    solicitud = db.query(models_solicitud.Solicitud).options(joinedload(models_solicitud.Solicitud.servicios)).filter(models_solicitud.Solicitud.id == id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    # Regla de negocio: Una solicitud solo puede eliminarse si NINGÚN servicio está en estado "Aprobado"
    if any(s.estado_servicio == EstadoServicio.APROBADO for s in solicitud.servicios):
        raise HTTPException(status_code=400, detail="No se puede eliminar la solicitud porque contiene servicios en estado 'Aprobado'.")

    db.delete(solicitud)
    db.commit()

# Obtener servicios de una solicitud
@router.get("/{id}/servicios", response_model=List[ServicioOut], summary="Listar todos los servicios de una solicitud")
def get_servicios_by_solicitud(id: int, db: Session = Depends(get_db)):
    solicitud = db.query(models_solicitud.Solicitud).options(joinedload(models_solicitud.Solicitud.servicios)).filter(models_solicitud.Solicitud.id == id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud.servicios

# Agregar un servicio a una solicitud
@router.post("/{id}/servicios", response_model=ServicioOut, status_code=status.HTTP_201_CREATED, summary="Agregar un nuevo servicio a una solicitud existente")
def add_servicio_to_solicitud(id: int, servicio_in: ServicioCreate, db: Session = Depends(get_db)):
    solicitud = db.query(models_solicitud.Solicitud).filter(models_solicitud.Solicitud.id == id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    # La validación de fecha futura ahora se maneja en el validador de Pydantic de ServicioCreate
    # if servicio_in.fecha_reunion.date() < datetime.utcnow().date():
    #     raise HTTPException(status_code=400, detail="La fecha de reunión debe ser futura.")
    
    if solicitud.estado in [EstadoSolicitud.CERRADA, EstadoSolicitud.CANCELADA]:
        raise HTTPException(status_code=400, detail=f"No se pueden agregar servicios a solicitudes en estado '{solicitud.estado.value}'.")

    db_servicio = models_servicio.Servicio(
        **servicio_in.model_dump(),
        id_solicitud=id
    )
    db.add(db_servicio)
    db.commit()
    db.refresh(db_servicio)
    return db_servicio
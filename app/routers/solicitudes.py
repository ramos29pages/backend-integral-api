from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date, timedelta # Importamos date
from app.database import get_db
from app.models import solicitud as models_solicitud
from app.models import servicio as models_servicio
from app.models.solicitud import EstadoSolicitud # Importar el Enum correcto
from app.models.servicio import EstadoServicio # Importar el Enum correcto
from app.schemas import solicitud as schemas_solicitud
from app.schemas.servicio import ServicioCreate, ServicioOut

router = APIRouter(prefix="/solicitudes", tags=["Solicitudes"])

# Crear nueva solicitud
@router.post("/", response_model=schemas_solicitud.SolicitudOut, status_code=status.HTTP_201_CREATED, summary="Crear una nueva solicitud")
def create_solicitud(solicitud_in: schemas_solicitud.SolicitudCreate, db: Session = Depends(get_db)):
    # La validación de formato de email debe estar en schemas_solicitud.SolicitudCreate
    
    db_solicitud = models_solicitud.Solicitud(
        cliente=solicitud_in.cliente,
        email_cliente=solicitud_in.email_cliente,
        observaciones=solicitud_in.observaciones,
        # fecha_solicitud y fecha_ultima_modificacion se establecen automáticamente por el modelo
        # estado se establece automáticamente a ABIERTA por el modelo
    )
    db.add(db_solicitud)
    db.commit()
    db.refresh(db_solicitud)
    return db_solicitud

# Obtener una solicitud por ID
@router.get("/{id}", response_model=schemas_solicitud.SolicitudOut, summary="Obtener una solicitud por ID")
def get_solicitud(id: int, db: Session = Depends(get_db)):
    # Usamos joinedload para cargar los servicios junto con la solicitud en una sola consulta
    solicitud = db.query(models_solicitud.Solicitud).options(joinedload(models_solicitud.Solicitud.servicios)).filter(models_solicitud.Solicitud.id == id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud

# Listar solicitudes con filtros y paginación
@router.get("/", response_model=List[schemas_solicitud.SolicitudOut], summary="Listar solicitudes con filtros, paginación y ordenamiento")
def list_solicitudes(
    estado: Optional[EstadoSolicitud] = Query(None, description="Filtrar por estado de la solicitud"), # Usar el Enum aquí
    fecha_desde: Optional[date] = Query(None, description="Filtrar por fecha de solicitud (desde)"), # Cambiado a date
    fecha_hasta: Optional[date] = Query(None, description="Filtrar por fecha de solicitud (hasta)"), # Cambiado a date
    cliente: Optional[str] = Query(None, description="Filtrar por nombre del cliente (búsqueda parcial)"),
    skip: int = Query(0, ge=0, description="Número de registros a omitir para paginación"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de registros a retornar"),
    ordenar_por: Optional[str] = Query("fecha_solicitud", description="Campo para ordenar (ej: id, cliente, fecha_solicitud, estado)"),
    orden: Optional[str] = Query("asc", description="Orden de los resultados (asc o desc)"),
    db: Session = Depends(get_db)
):
    query = db.query(models_solicitud.Solicitud)

    if estado:
        query = query.filter(models_solicitud.Solicitud.estado == estado)
    if cliente:
        query = query.filter(models_solicitud.Solicitud.cliente.ilike(f"%{cliente}%")) # Corregido: .cliente
    if fecha_desde:
        query = query.filter(models_solicitud.Solicitud.fecha_solicitud >= fecha_desde) # Corregido: .fecha_solicitud
    if fecha_hasta:
        # Para incluir todo el día de fecha_hasta, sumamos un día y usamos <
        query = query.filter(models_solicitud.Solicitud.fecha_solicitud < (fecha_hasta + timedelta(days=1)))
    
    # Ordenamiento
    if ordenar_por:
        if hasattr(models_solicitud.Solicitud, ordenar_por):
            if orden == "desc":
                query = query.order_by(getattr(models_solicitud.Solicitud, ordenar_por).desc())
            else:
                query = query.order_by(getattr(models_solicitud.Solicitud, ordenar_por).asc())
        else:
            raise HTTPException(status_code=400, detail=f"Campo '{ordenar_por}' no válido para ordenamiento.")


    solicitudes = query.offset(skip).limit(limit).all()
    return solicitudes

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
    
    # Regla de negocio: La fecha de reunión debe ser futura
    # Usar .date() para comparar solo la fecha
    if servicio_in.fecha_reunion.date() < datetime.utcnow().date():
        raise HTTPException(status_code=400, detail="La fecha de reunión debe ser futura.")
    
    # Se puede agregar una validación aquí para que no se agreguen servicios a solicitudes Cerradas/Canceladas
    if solicitud.estado in [EstadoSolicitud.CERRADA, EstadoSolicitud.CANCELADA]:
        raise HTTPException(status_code=400, detail=f"No se pueden agregar servicios a solicitudes en estado '{solicitud.estado.value}'.")

    db_servicio = models_servicio.Servicio(
        **servicio_in.model_dump(), # Usar .model_dump()
        solicitud_id=id
    )
    db.add(db_servicio)
    db.commit()
    db.refresh(db_servicio)
    return db_servicio
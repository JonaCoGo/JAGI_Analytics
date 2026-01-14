# existencias_service.py

from app.repositories.existencias_repository import fetch_existencias_por_tienda


def get_existencias_por_tienda():
    """
    Retorna las existencias actuales por tienda.
    Servicio del dominio Inventario / Existencias.
    """
    return fetch_existencias_por_tienda()
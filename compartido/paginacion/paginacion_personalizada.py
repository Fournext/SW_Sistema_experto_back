"""
Paginación personalizada compatible con el formato estándar de respuestas.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PaginacionEstandar(PageNumberPagination):
    page_size = 20
    page_size_query_param = "tamano_pagina"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "message": "Listado obtenido correctamente.",
            "data": {
                "total": self.page.paginator.count,
                "paginas_totales": self.page.paginator.num_pages,
                "pagina_actual": self.page.number,
                "siguiente": self.get_next_link(),
                "anterior": self.get_previous_link(),
                "resultados": data,
            }
        })

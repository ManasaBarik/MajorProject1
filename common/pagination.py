from rest_framework.pagination import PageNumberPagination

from .responses import success


class OptionalPageNumberPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if "page" not in request.query_params and self.page_size_query_param not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)


def paginated_success(queryset, serializer_class, request, view=None):
    paginator = OptionalPageNumberPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)
    if page is None:
        return success(serializer_class(queryset, many=True, context={"request": request}).data)
    data = serializer_class(page, many=True, context={"request": request}).data
    return success(paginator.get_paginated_response(data).data)
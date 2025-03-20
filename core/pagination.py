from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Pagination standard pour l'API PriceGuard.
    
    Configuration de la pagination par défaut:
    - page_size: 20 éléments par page
    - page_size_query_param: permet de spécifier un nombre différent via le paramètre 'page_size'
    - max_page_size: limite maximum à 100 éléments par page
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

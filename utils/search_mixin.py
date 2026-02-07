from django.contrib.postgres.search import SearchQuery, SearchVector, SearchRank
from django.db.models import Q

from rest_framework.decorators import action
from rest_framework.exceptions import NotAcceptable
from rest_framework.response import Response


class SearchMixin:
    # permission_classes=[permissions.IsAuthenticated, ]  # allow anon user use search
    @action(methods=['GET'], detail=False)
    def search(self, request):

        # qs = self.get_queryset()  # we have rank and popular_weight here
        # exclude annotations query for now
        qs = self.get_basic_filter_qs(self.queryset)

        qs = self.filter_queryset(qs)

        keywords = request.GET.get('query')
        if not keywords:
            raise NotAcceptable('Search query required')

        keywords = f'\'{keywords}\':*'
        query = SearchQuery(keywords, search_type='raw', config='russian')
        # query = SearchQuery(keywords, search_type='phrase', config='russian')
        # query = SearchQuery(keywords, search_type='websearch', config='russian')

        if self.request.user.is_authenticated and (
                self.request.user.is_staff or self.request.user.is_superuser) and hasattr(self, 'search_fields_staff'):
            vector = SearchVector(*self.search_fields_staff)
        elif hasattr(self, 'search_weights_fields'):
            vector = None
            for field_name, weight in self.search_weights_fields:
                if not vector:
                    vector = SearchVector(field_name, weight=weight)
                else:
                    vector += SearchVector(field_name, weight=weight)
        elif hasattr(self, 'search_fields'):
            vector = SearchVector(*self.search_fields)
        else:
            raise Exception("Please set 'search_fields' or 'search_weights_fields' attributes to use this mixin")

        if hasattr(self, 'casting_search_fields'):
            from django.db.models.functions import Cast
            from django.db.models import TextField
            fields = [Cast(val, TextField()) for i, val in enumerate(self.casting_search_fields)]
            vector = SearchVector(*fields)

        qs = qs.annotate(search=vector).filter(Q(search=query))
        qs = qs.annotate(rank=SearchRank(vector, query)).order_by('-rank', 'id').distinct('rank', 'id')

        # search pagination
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)

        return Response(serializer.data)

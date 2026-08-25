from decimal import Decimal
from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from apps.billing.models import Direction
from .models import Member
from .serializers import MemberSerializer


class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active", "gender"]
    search_fields = ["member_code", "phone", "first_name", "last_name"]

    def get_queryset(self):
        return (
            Member.objects.all()
            .annotate(
                annotated_balance=Coalesce(
                    Sum(
                        Case(
                            When(ledger_entries__direction=Direction.DEBIT, then=F("ledger_entries__amount")),
                            When(ledger_entries__direction=Direction.CREDIT, then=-F("ledger_entries__amount")),
                            output_field=DecimalField(max_digits=14, decimal_places=2),
                        )
                    ),
                    Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
                )
            )
            .order_by("first_name", "last_name")
        )

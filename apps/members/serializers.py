from rest_framework import serializers

from apps.billing.services import calculate_member_balance

from .models import Member


class MemberSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id", "member_code", "first_name", "last_name", "phone",
            "date_of_birth", "gender", "address", "is_active",
            "created_at", "balance",
        ]
        read_only_fields = ["member_code", "created_at"]

    def get_balance(self, obj):
        if hasattr(obj, "annotated_balance"):
            return obj.annotated_balance
        return calculate_member_balance(obj)

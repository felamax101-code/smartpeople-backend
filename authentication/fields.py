# authentication/fields.py
import phonenumbers
from rest_framework import serializers
from .validators import normalize_phone

class PhoneNumberField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        self.default_country = kwargs.pop("default_country", "KE")
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        result = normalize_phone(value, self.default_country)

        if not result["success"]:
            raise serializers.ValidationError(result["error"])

        return result["e164"]  # always saves E.164 to DB

    def to_representation(self, value):
        """Display as international format when reading"""
        if not value:
            return value
        try:
            parsed = phonenumbers.parse(value)
            return phonenumbers.format_number(
                parsed, 
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
        except Exception:
            return value  # fallback to raw value if parsing fails
            
            
 
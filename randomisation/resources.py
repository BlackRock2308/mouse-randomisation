from import_export import resources
from .models import SourisModel


class SourisResource(resources.ModelResource):
    class Meta:
        model = SourisModel

from django.contrib import admin
from .models import SourisModel , SourisBackupModel

from import_export.admin import ImportExportActionModelAdmin




@admin.register(SourisModel)
class SourisAdmin(ImportExportActionModelAdmin):
    list_display = ('complete_id','mouse_id','tumor_volume','cbl','h_rate','order','old_cage')


@admin.register(SourisBackupModel)
class SourisBackupAdmin(ImportExportActionModelAdmin):
    list_display = ('complete_id','mouse_id','tumor_volume','cbl','h_rate','order','old_cage')
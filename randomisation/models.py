from django.db import models

class SourisModel(models.Model):
    id = models.CharField(primary_key=True, max_length=5)
    complete_id = models.CharField(max_length=255,null= True,blank=True)
    mouse_id = models.CharField(max_length=255,null= True,blank=True)
    tumor_volume = models.CharField(null= True,max_length=255,blank=True)
    cbl = models.CharField(max_length=5,null= True, blank=True)
    h_rate = models.CharField(max_length=255,null= True,blank=True)
    order = models.CharField(max_length=255,null= True,blank=True)
    old_cage = models.CharField(max_length=255,null= True,blank=True)

    def __str__(self) -> str:
        return self.mouse_id


class SourisBackupModel(models.Model):
    id = models.CharField(primary_key=True, max_length=5)
    complete_id = models.CharField(max_length=255,null= True,blank=True)
    mouse_id = models.CharField(max_length=255,null= True,blank=True)
    tumor_volume = models.CharField(null= True,max_length=255,blank=True)
    cbl = models.CharField(max_length=5,null= True, blank=True)
    h_rate = models.CharField(max_length=255,null= True,blank=True)
    order = models.CharField(max_length=255,null= True,blank=True)
    old_cage = models.CharField(max_length=255,null= True,blank=True)

    def __str__(self) -> str:
        return self.mouse_id


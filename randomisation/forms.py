from django import forms
from .models import *

class SourisForm(forms.Form):
	class meta:
		model = SourisModel
		fields = ('id','complete_id','mouse_id','tumor_volume','cbl','h_rate','order','old_cage')



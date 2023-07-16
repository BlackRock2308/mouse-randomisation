from django.shortcuts import render,redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from .forms import SourisForm
from tablib import Dataset
from .resources import SourisResource
from .models import SourisModel, SourisBackupModel
from django.apps import apps
from django.db.models import Q
from django.db import transaction
from django.urls import reverse
import numpy as np
import math
from openpyxl import Workbook

from django.template.loader import get_template

from xhtml2pdf import pisa




def detect_null_columns(table_name):
    model = apps.get_model(app_label='randomisation', model_name=table_name)
    null_columns = []

    for field in model._meta.get_fields():
        if getattr(field, 'null', False) and getattr(field, 'blank', False):
            if model.objects.filter(**{field.name: None}).exists():
                null_columns.append(field.name)

    return null_columns




def delete_rows_with_null():
    SourisModel.objects.filter(
        Q(complete_id__isnull=True) | Q(complete_id='') |
        Q(mouse_id__isnull=True) | Q(mouse_id='') |
        Q(tumor_volume__isnull=True) | Q(tumor_volume='') |
        Q(cbl__isnull=True) | Q(cbl='') |
        Q(h_rate__isnull=True) | Q(h_rate='') |
        Q(order__isnull=True) | Q(order='') |
        Q(old_cage__isnull=True) | Q(old_cage='')
    ).delete()


def remove_extremes(tumor_volume, num_elements):
    sorted_volume = sorted(tumor_volume)
    num_extremes = len(tumor_volume) - num_elements

    if num_extremes <= 0:
        return tumor_volume

    # Supprimer les parties maximales et minimales des extrêmes
    min_extremes = sorted_volume[:num_extremes//2]
    max_extremes = sorted_volume[-(num_extremes - num_extremes//2):]

    # Retourner le groupe d'éléments sans les extrêmes
    return [value for value in tumor_volume if value not in min_extremes and value not in max_extremes]





def display(request):
    mouse = SourisModel.objects.all()
    mouse_count = mouse.count()
    null_columns = detect_null_columns('SourisModel')  # Call detect_null_columns with the model name
    count_null_columns = len(null_columns)

    context = {
        "mouse" : mouse, 
        "mouse_count": mouse_count,
        "null_columns": null_columns,
        "count_null_columns" : count_null_columns
    }

    if request.method == 'POST':
        delete_rows_with_null()  # Call the function to delete rows with null values
        return redirect('display')

    return render(request, 'randomisation/display.html', context)


def delete_rows(request):
    if request.method == 'POST':
        delete_rows_with_null()  # Call the function to delete rows with null values
        return redirect('display')  # Redirect to the display page or any other desired page

    return render(request, 'randomisation/delete_rows.html')





def choix_souris(request):
    
    mouse = SourisModel.objects.all()
    mouse_count = mouse.count()

    context = {
        "mouse" : mouse, 
        "mouse_count": mouse_count,
    }


    if request.method == 'POST':
        # Récupérer l'input de l'utilisateur à partir de la requête POST
        num_elements = int(request.POST.get('num_elements', 0))

        # Récupérer toutes les instances de SourisModel
        souris_instances = SourisModel.objects.all()
        
        # Appliquer la fonction remove_extremes sur la colonne tumor_volume du modèle SourisModel
        tumor_volume = SourisModel.objects.values_list('tumor_volume', flat=True)
        tumor_volume = [float(value) for value in tumor_volume]

        tumor_volume_without_extremes = remove_extremes(tumor_volume, num_elements)

        # Create instances of SourisBackup and save them
        for souris_instance in souris_instances:
            if float(souris_instance.tumor_volume) not in tumor_volume_without_extremes:
                SourisBackupModel.objects.create(
                    id=souris_instance.id,
                    complete_id=souris_instance.complete_id,
                    mouse_id=souris_instance.mouse_id,
                    tumor_volume=souris_instance.tumor_volume,
                    cbl=souris_instance.cbl,
                    h_rate=souris_instance.h_rate,
                    order=souris_instance.order,
                    old_cage=souris_instance.old_cage
                )

        # Supprimer toutes les instances de SourisModel qui correspondent aux valeurs extrêmes
        for souris_instance in souris_instances:
            if float(souris_instance.tumor_volume) not in tumor_volume_without_extremes:
                souris_instance.delete()
        # Rediriger l'utilisateur vers la même vue après la suppression réussie
        return redirect('choice')

    return render(request, 'randomisation/choix_souris.html', context)



def home(request):
    #appeler une methode qui permet de vider la table avant d'inserer des valeur
    if request.method == 'POST':
        souris_resource = SourisResource()
        dataset = Dataset()
        new_souris = request.FILES['myfile']

        if not new_souris.name.endswith('xlsx'):
            messages.info(request, 'Wrong format')
            return render(request, 'randomisation/home.html') 

        imported_data = dataset.load(new_souris.read(),format='xlsx')
       
        with transaction.atomic():
            # Delete all existing SourisModel instances
            SourisModel.objects.all().delete()
            SourisBackupModel.objects.all().delete()

            for data in imported_data:

                value = SourisModel(
                    data[0],
                    data[1],
                    data[2],
                    data[3],
                    data[4],
                    data[5],
                    data[6],
                    data[7]
                    )
                value.save()  
            # Check if the transaction was successful
            if transaction.get_rollback():
                # Transaction failed, render the home template
                return render(request, 'randomisation/home.html')
        
        # Transaction succeeded, render the another_template.html
        return redirect(reverse('display'))

    return render(request, 'randomisation/home.html')






def choix_groupe_souris(request):
    mouse = SourisModel.objects.all()
    mouse_count = mouse.count()

    groups = []  # Define an initial empty list

    if request.method == 'POST':
        # Récupérer l'input de l'utilisateur à partir de la requête POST
        num_elements_per_group = int(request.POST.get('num_elements_per_group', 0))


        tumor_volumes = SourisModel.objects.values_list('tumor_volume', flat=True)
        tumor_categories = SourisModel.objects.values_list('cbl', flat=True)
        h_rates = SourisModel.objects.values_list('h_rate', flat=True)
        orders = SourisModel.objects.values_list('order', flat=True)
        old_cages = SourisModel.objects.values_list('old_cage', flat=True)
        complete_id = SourisModel.objects.values_list('complete_id', flat=True)
        mouse_id = SourisModel.objects.values_list('mouse_id', flat=True)
        # Add more field values here

        tumor_volume = np.array(list(tumor_volumes))
        tumor_category = np.array(list(tumor_categories))
        h_rate = np.array(list(h_rates))
        order = np.array(list(orders))
        old_cage = np.array(list(old_cages))
        mouse_id = np.array(list(mouse_id))
        complete_id = np.array(list(complete_id))
        # Convert more field values to NumPy arrays here

        data = np.column_stack((tumor_volume, tumor_category, h_rate, order, old_cage, complete_id, mouse_id))
        sorted_data = data[np.argsort(data[:, 0])]

        num_elements = len(sorted_data)
    
        num_groups = math.ceil(num_elements / num_elements_per_group)  # Round up to handle remaining elements
        remaining_elements = num_elements % num_elements_per_group
   
        start_idx = 0
        for i in range(num_groups):
            end_idx = start_idx + num_elements_per_group
            group = sorted_data[start_idx:end_idx]
            groups.append(group.tolist())

            start_idx = end_idx

        if remaining_elements > 0:
            remaining_group = sorted_data[-remaining_elements:]
            groups.append(remaining_group.tolist())

        
            # Delete all elements from the session
        # if 'groups' in request.session:
        #     del request.session['groups']
        

        request.session['groups'] = groups


        redirect_url = reverse('random_group')
        return redirect(redirect_url)

    context = {
            'groups': groups,
            "mouse_count": mouse_count,
    }

    return render(request, 'randomisation/groupe_souris.html', context)




def creating_random_group_view(request):

    groups = request.session.get('groups', [])

    tumor_averages = []  # List to store average tumor volume for each group

    for i, group in enumerate(groups, start=1):
        tumor_volumes = [float(item[0]) for item in group]  # Convert tumor volumes to float
        # average_tumor_volume = sum(tumor_volumes) / len(tumor_volumes)  # Calculate average tumor volume
        # tumor_averages.append((i, average_tumor_volume))  # Append group indicator and average tumor volume


    # for group in groups:
    #     tumor_volumes = [float(item[0]) for item in group]  # Convert tumor volumes to float
    #     average_tumor_volume = sum(tumor_volumes) / len(tumor_volumes)  # Calculate average tumor volume
    #     tumor_averages.append(average_tumor_volume)

    # print("Moyenne des tumor volume")
    # print(tumor_averages)
    # Display a success toast message
    messages.success(request, 'Instances saved to SourisBackup and deleted successfully.')

    context = {"groups" : groups}
    return render(request, 'randomisation/generate_group.html', context)



def pdf_report_create(request):
    groups = request.session.get('groups', [])

    template_path = 'randomisation/groupe_souris_report.html'

    context = {'groups': groups}

    response = HttpResponse(content_type='application/pdf')

    response['Content-Disposition'] = 'filename="groupe_souris_report.pdf"'

    template = get_template(template_path)

    html = template.render(context)

    # create a pdf
    pisa_status = pisa.CreatePDF(
       html, dest=response)
    # if error then show some funy view
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response




def deleted_souris_view(request):

    souris_backup = SourisBackupModel.objects.all()
    context = {"souris_backup" : souris_backup}

    return render(request, 'randomisation/deleted_souris.html', context)



def pdf_report_create_deleted_souris(request):

    eliminated_souris = SourisBackupModel.objects.all()

    template_path = 'randomisation/eliminated_souris_report.html'

    context = {'eliminated_souris': eliminated_souris}

    response = HttpResponse(content_type='application/pdf')

    response['Content-Disposition'] = 'filename="eliminated_souris_report.pdf"'

    template = get_template(template_path)

    html = template.render(context)

    # create a pdf
    pisa_status = pisa.CreatePDF(
       html, dest=response)
    # if error then show some funy view
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response





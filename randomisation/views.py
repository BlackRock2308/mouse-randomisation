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
from openpyxl.styles import Font, PatternFill
from django.template.loader import get_template
from xhtml2pdf import pisa
import pandas as pd
import os

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
        return redirect('groupe')

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


        # ******************** NEW CONTENT ********************


                # Combine all the data into a single array for easier processing
        data = np.column_stack((tumor_volume, tumor_category, h_rate, order, old_cage, complete_id, mouse_id))

        # Shuffle the data randomly
        np.random.shuffle(data)

        # Create an empty list to store the groups
        groups = []

        # Create a function to check the number of occurrences of an element in a group
        def element_occurrences_in_group(group, element):
            count = 0
            for item in group:
                if item[1] == element[1]:  # Check tumor_category (assuming it is at index 1)
                    count += 1
            return count

        # Iterate through the shuffled data and form the groups
        for element in data:
            added_to_group = False

            for group in groups:
                # Check if the element already exists in the group and the group has less than num_elements_per_group
                if not added_to_group and len(group) < num_elements_per_group:
                    # Check if the element has fewer occurrences in the group than in the dataset
                    element_count_in_group = element_occurrences_in_group(group, element)
                    element_count_in_data = np.sum(tumor_category == element[1])
                    if element_count_in_group < element_count_in_data:
                        group.append(element.tolist())
                        added_to_group = True

            # If the element was not added to any existing group, create a new group
            if not added_to_group:
                groups.append([element.tolist()])

        # Ensure that only one group at most has fewer elements than num_elements_per_group
        remaining_group = []
        for group in groups:
            if len(group) < num_elements_per_group:
                if len(remaining_group) == 0:
                    remaining_group = group
                else:
                    remaining_group.extend(group)
            else:
                if len(remaining_group) > 0:
                    groups.append(remaining_group)
                    remaining_group = []

        # If there are still elements in the remaining_group, add it as a new group
        if len(remaining_group) > 0:
            groups.append(remaining_group)







        #***********************OLD 11***********************************


        #  # Combine all the data into a single array for easier shuffling
        # data = np.column_stack((tumor_volume, tumor_category, h_rate, order, old_cage, complete_id, mouse_id))

        # # Shuffle the data randomly
        # np.random.shuffle(data)

        # # Calculate the number of groups based on the total number of elements and the desired size of each group
        # num_groups = math.ceil(len(data) / num_elements_per_group)

        # # Create an empty list to store the groups
        # groups = []

        # # Split the shuffled data into groups
        # for i in range(num_groups):
        #     start_idx = i * num_elements_per_group
        #     end_idx = start_idx + num_elements_per_group
        #     group = data[start_idx:end_idx].tolist()
        #     groups.append(group)

        # ******************** OLD CONTENT ********************

        # data = np.column_stack((tumor_volume, tumor_category, h_rate, order, old_cage, complete_id, mouse_id))
        # sorted_data = data[np.argsort(data[:, 0])]

        # num_elements = len(sorted_data)
    
        # num_groups = math.ceil(num_elements / num_elements_per_group)  
        # remaining_elements = num_elements % num_elements_per_group
   
        # start_idx = 0
        # for i in range(num_groups):
        #     end_idx = start_idx + num_elements_per_group
        #     group = sorted_data[start_idx:end_idx]
        #     groups.append(group.tolist())

        #     start_idx = end_idx

        # if remaining_elements > 0:
        #     remaining_group = sorted_data[-remaining_elements:]
        #     groups.append(remaining_group.tolist())

        # **********************************************

        

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






def export_to_excel_view(request):
    groups = request.session.get('groups', [])
    variable_names = ['tumor_volume', 'tumor_category', 'h_rate', 'order', 'old_cage', 'complete_id', 'mouse_id']

    # Create an empty list to store data for the DataFrame
    data = {var: [] for var in variable_names}
    data['Group'] = []

    # Fill the data dictionary with values from 'groups'
    for idx, group in enumerate(groups):
        for element in group:
            for i, var in enumerate(variable_names):
                # Access the values from each element in the sub-list and append to the data dictionary
                data[var].append(element[i])

            data['Group'].append(f'Groupe {idx + 1}')

        # Add a row with empty values to create a line break between groups
        for var in variable_names:
            data[var].append('')
        data['Group'].append('')

    # Create the DataFrame
    df = pd.DataFrame(data)

    # Create an Excel writer object
    excel_writer = pd.ExcelWriter('randomisation.xlsx', engine='openpyxl')
    df.to_excel(excel_writer, index=False)

    # Access the openpyxl workbook and worksheet
    workbook = excel_writer.book
    worksheet = workbook.active

    # Define the font and fill for the header cells
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='008000', end_color='008000', fill_type='solid')

    # Apply the style to the header row (assumes the header row is the first row in the worksheet)
    for cell in worksheet['1']:
        cell.font = header_font
        cell.fill = header_fill

    # Save the Excel writer book
    excel_writer.book.save('randomisation.xlsx')
    excel_writer.close()

    # Read the Excel file into a binary format for the HTTP response
    with open('randomisation.xlsx', 'rb') as excel_file:
        response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=randomisation.xlsx'

    # Delete the generated file after sending the response
    os.remove('randomisation.xlsx')

    return response




# def export_to_excel_view(request):
#     groups = request.session.get('groups', [])
#     variable_names = ['tumor_volume', 'tumor_category', 'h_rate', 'order', 'old_cage', 'complete_id', 'mouse_id']

#     # Create an empty list to store data for the DataFrame
#     data = {var: [] for var in variable_names}
#     data['Group'] = []

#     # Fill the data dictionary with values from 'groups'
#     for idx, group in enumerate(groups):
#         for element in group:
#             for i, var in enumerate(variable_names):
#                 # Access the values from each element in the sub-list and append to the data dictionary
#                 data[var].append(element[i])

#             data['Group'].append(f'Groupe {idx + 1}')

#     # Create the DataFrame
#     df = pd.DataFrame(data)

#     # Create an Excel writer object
#     excel_writer = pd.ExcelWriter('output_3.xlsx', engine='openpyxl')
#     df.to_excel(excel_writer, index=False)

#     # Save the Excel writer book
#     excel_writer.book.save('output_3.xlsx')
#     excel_writer.close()

#     # Read the Excel file into a binary format for the HTTP response
#     with open('output_3.xlsx', 'rb') as excel_file:
#         response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = 'attachment; filename=output_3.xlsx'

#     return response





# def export_to_excel_view(request):
#     groups = request.session.get('groups', [])
#     variable_names = ['tumor_volume', 'tumor_category', 'h_rate', 'order', 'old_cage', 'complete_id', 'mouse_id']

#     # Create a dictionary to store data for the DataFrame
#     data_dict = {var: [] for var in variable_names}
#     data_dict['Group'] = []

#     # Fill the data dictionary with values from 'groups'
#     for idx, group in enumerate(groups):
#         for i, var in enumerate(variable_names):
#             data_dict[var].append(group[i])

#         data_dict['Group'].append(f'Groupe {idx + 1}')

#     # Create the DataFrame
#     df = pd.DataFrame(data_dict)

#     # Create an Excel writer object
#     excel_writer = pd.ExcelWriter('output.xlsx', engine='openpyxl')
#     df.to_excel(excel_writer, index=False)

#     # Save the Excel writer book
#     excel_writer.book.save('output.xlsx')
#     excel_writer.close()

#     # Read the Excel file into a binary format for the HTTP response
#     with open('output.xlsx', 'rb') as excel_file:
#         response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = 'attachment; filename=output.xlsx'

#     return response
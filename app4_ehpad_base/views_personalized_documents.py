import os
import io
import PyPDF2
import logging

from django.contrib import messages
from django.shortcuts import redirect

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from django.conf import settings

from django.core.files import File
from django.utils.translation import gettext_lazy as _

from app1_base.log import Logger
from app1_base.models import User

from .models import MutualDocument, PersonalizedDocument, ProfileSerenicia

# ----------------------------------------------------------------------------------------------------------------------


if 'log_views_personalized_doc' not in globals():
    global log_views_personalized_doc
    log_doc = Logger('Views personalized doc', level=logging.ERROR).run()


# ----------------------------------------------------------------------------------------------------------------------


def check_user_field(request):
    success = str(_('Your documents with your personal information have been created, you can sign them now.'))
    user = User.objects.get(pk=request.user.id)

    if user.last_name and user.last_name and user.email:

        if user.profileserenicia.birth_city and user.profileserenicia.birth_date and user.profileserenicia.family_bond:

            if user.profile.adress and user.profile.cp and user.profile.city:
                user_resident = User.objects.get(pk=request.session['resident_id'])

                if user_resident.last_name and user_resident.first_name:

                    if user_resident.profileserenicia.birth_city and user_resident.profileserenicia.birth_date:
                        personalized_documents(request)
                        messages.success(request, _(success), extra_tags='success')
                        return redirect('documents')

                    else:
                        residentPJ_message = str(_('Information about the resident : city or date of birth is missing'))
                        messages.error(request, f"{residentPJ_message}", extra_tags='error')
                        return redirect('documents')

                else:
                    userR_message = str(_('Information about the resident is missing first name or last name'))
                    messages.error(request, f"{userR_message}", extra_tags='error')
                    return redirect('documents')

            else:
                profile_message = str(_('Information about : your place of residence is missing'))
                messages.error(request, f"{profile_message}", extra_tags='error')
                return redirect('profile')
        else:
            profileJ_message = str(_('Information about your : city/date birth or the family bond is missing'))
            messages.error(request, f"{profileJ_message}", extra_tags='error')
            return redirect('profile')

    else:
        user_message = str(_('Information about you : first name/last name or your email is missing'))
        messages.error(request, f"{user_message}", extra_tags='error')
        return redirect('profile')


# ----------------------------------------------------------------------------------------------------------------------


def personalized_documents(request):
    path = '/doc_adm/documents/'

    r_p = str(_('Read and Approved'))
    r_p_c = str(_('Read and approved, good for joint surety'))

    error = str(_("A problem has occurred. Please try again later or contact us for more information."))

    user = User.objects.get(pk=request.user.id)
    user_resident = User.objects.get(pk=request.session['resident_id'])

    if MutualDocument.objects.all().count() == 10:

        _user_family_ = {
            'link_family': user.profileserenicia.family_bond,
            'last_name': user.last_name, 'first_name': user.first_name, 'email': user.email,
            'birth_date': user.profileserenicia.birth_date, 'birth_city': user.profileserenicia.birth_city,
            'adress': user.profile.adress, 'cp': user.profile.cp, 'city': user.profile.city,
        }

        _user_resident_ = {
            'last_name': user_resident.last_name, 'first_name': user_resident.first_name,
            'birth_date': user_resident.profileserenicia.birth_date,
            'birth_city': user_resident.profileserenicia.birth_city,
        }

        user_room = ProfileSerenicia.objects.get(user=user_resident).user.profile.client.room_number
        if user_room is not None:

            _user_resident_['room'] = f"{user_room}"
            _user_resident_['complete_name'] = f"{_user_resident_['last_name']} {_user_resident_['first_name']}"

            _user_family_['complete_name'] = f"{_user_family_['last_name']} {_user_family_['first_name']}"
            _user_family_['adress'] = f"{_user_family_['adress']} {_user_family_['cp']} {_user_family_['city']}"

        else:
            log_doc.error(f"Error generate document user room")
            messages.error(request, _(f"{error}, {_('code error user room')}"), extra_tags='error')
            return redirect('documents')

        try:

            conduct_charter = MutualDocument.objects.get(document_type='conduct-charter')
            if conduct_charter:
                data = io.BytesIO()
                pdf = canvas.Canvas(data, pagesize=letter)

                pdf.drawString(28, 255, _user_family_['last_name'])
                pdf.drawString(145, 255, _user_family_['first_name'])
                pdf.drawString(370, 255, _user_family_['link_family'])
                pdf.setFont('Helvetica', 8)
                pdf.drawString(248, 255, _user_family_['email'])

                pdf.save()
                data.seek(0)

                obj = PersonalizedDocument(document_type=conduct_charter.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, conduct_charter.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)
                    output = PyPDF2.PdfFileWriter()

                    for pages in range(1):
                        p = existing_pdf.getPage(pages)
                        output.addPage(p)

                    page = existing_pdf.getPage(1)
                    page_1 = PyPDF2.PdfFileReader(data).getPage(0)

                    page.mergePage(page_1)
                    output.addPage(page)

                    with open(os.path.join(settings.MEDIA_ROOT + path, conduct_charter.document_type + '.pdf'),
                              'wb') as f:
                        output.write(f)
                        f.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, f.name), 'rb') as f:
                        obj.file.save('final.pdf', File(f))

            general_condition = MutualDocument.objects.get(document_type='general-condition')
            if general_condition:
                data_1 = io.BytesIO()
                data_2 = io.BytesIO()

                page_1 = canvas.Canvas(data_1, pagesize=letter)
                page_1.drawString(100, 663, _user_resident_['complete_name'])

                page_1.save()
                data_1.seek(0)

                page_9 = canvas.Canvas(data_2, pagesize=letter)

                page_9.drawString(250, 255, r_p)
                page_9.drawString(250, 200, r_p)
                page_9.drawString(250, 125, _user_family_['complete_name'])

                page_9.save()
                data_2.seek(0)

                obj = PersonalizedDocument(document_type=general_condition.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, general_condition.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)
                    output = PyPDF2.PdfFileWriter()

                    page_ = existing_pdf.getPage(0)
                    page_1 = PyPDF2.PdfFileReader(data_1).getPage(0)

                    page_.mergePage(page_1)
                    output.addPage(page_)

                    for pages in range(1, 8):
                        p = existing_pdf.getPage(pages)
                        output.addPage(p)

                    page = existing_pdf.getPage(8)
                    page_9 = PyPDF2.PdfFileReader(data_2).getPage(0)

                    page.mergePage(page_9)
                    output.addPage(page), output.addPage(existing_pdf.getPage(9))

                    with open(os.path.join(settings.MEDIA_ROOT + path, general_condition.document_type + '.pdf'),
                              'wb') as f:
                        output.write(f)
                        f.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, f.name), 'rb') as f:
                        obj.file.save('final.pdf', File(f))

            rules_operation = MutualDocument.objects.get(document_type='rules-operation')
            if rules_operation:
                data_1 = io.BytesIO()
                data_2 = io.BytesIO()

                page_1 = canvas.Canvas(data_1, pagesize=letter)
                page_1.drawString(115, 755, _user_resident_['complete_name'])

                page_1.save()
                data_1.seek(0)

                page_6 = canvas.Canvas(data_2, pagesize=letter)
                page_6.drawString(385, 152, f"{_user_family_['complete_name']} {_user_resident_['complete_name']}")

                page_6.save()
                data_2.seek(0)

                obj = PersonalizedDocument(document_type=rules_operation.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, rules_operation.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)
                    output = PyPDF2.PdfFileWriter()

                    page_ = existing_pdf.getPage(0)
                    page_1 = PyPDF2.PdfFileReader(data_1).getPage(0)

                    page_.mergePage(page_1)
                    output.addPage(page_)

                    for pages in range(1, 5):
                        p = existing_pdf.getPage(pages)
                        output.addPage(p)

                    page = existing_pdf.getPage(5)
                    page_6 = PyPDF2.PdfFileReader(data_2).getPage(0)

                    page.mergePage(page_6)
                    output.addPage(page)

                    with open(os.path.join(settings.MEDIA_ROOT + path, rules_operation.document_type + '.pdf'),
                              'wb') as f:
                        output.write(f)
                        f.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, f.name), 'rb') as f:
                        obj.file.save('final.pdf', File(f))

            reading_certificate = MutualDocument.objects.get(document_type='reading-certificate')
            if reading_certificate:
                data = io.BytesIO()
                pdf = canvas.Canvas(data, pagesize=letter)

                pdf.drawString(130, 701, _user_family_['complete_name'])
                pdf.drawString(285, 687, _user_resident_['complete_name'])
                pdf.drawString(150, 672, _user_family_['link_family'])
                pdf.drawString(245, 266, f"1")
                pdf.save()

                data.seek(0)

                obj = PersonalizedDocument(document_type=reading_certificate.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, reading_certificate.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)
                    output = PyPDF2.PdfFileWriter()

                    page = existing_pdf.getPage(0)
                    page_1 = PyPDF2.PdfFileReader(data).getPage(0)

                    page.mergePage(page_1)
                    output.addPage(page)

                    with open(os.path.join(settings.MEDIA_ROOT + path, reading_certificate.document_type + '.pdf'),
                              'wb') as f:
                        output.write(f)
                        f.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, f.name), 'rb') as f:
                        obj.file.save('final.pdf', File(f))

            benefit = MutualDocument.objects.get(document_type='benefit')
            if benefit:
                data = io.BytesIO()
                pdf = canvas.Canvas(data, pagesize=letter)

                pdf.drawString(240, 682, _user_resident_['complete_name'])
                pdf.drawString(125, 666, _user_resident_['room'])
                pdf.drawString(160, 115, _user_family_['complete_name'])
                pdf.save()

                data.seek(0)

                obj = PersonalizedDocument(document_type=benefit.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, benefit.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)
                    output = PyPDF2.PdfFileWriter()

                    page = existing_pdf.getPage(0)
                    page_2 = PyPDF2.PdfFileReader(data).getPage(0)

                    page.mergePage(page_2)
                    output.addPage(page)

                    with open(os.path.join(settings.MEDIA_ROOT + path, benefit.document_type + '.pdf'), 'wb') as f:
                        output.write(f)
                        f.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, f.name), 'rb') as f:
                        obj.file.save('final.pdf', File(f))

            endorsement = MutualDocument.objects.get(document_type='endorsement')
            if endorsement:
                data_1 = io.BytesIO()

                page_1 = canvas.Canvas(data_1, pagesize=letter)
                page_1.drawString(85, 740, _user_resident_['complete_name'])

                page_1.save()
                data_1.seek(0)

                obj = PersonalizedDocument(document_type=endorsement.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, endorsement.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)
                    output_first_page = PyPDF2.PdfFileWriter()

                    first_page = existing_pdf.getPage(0)
                    pdf_page_1 = PyPDF2.PdfFileReader(data_1).getPage(0)

                    first_page.mergePage(pdf_page_1)
                    output_first_page.addPage(first_page)

                    with open(os.path.join(settings.MEDIA_ROOT + path, endorsement.document_type + '.pdf'), 'wb') as f:
                        output_first_page.write(f)
                        f.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, f.name), 'rb') as f:
                        obj.file.save('final.pdf', File(f))

            image_authorization = MutualDocument.objects.get(document_type='image-authorization')
            if image_authorization:
                data_1 = io.BytesIO()
                data_2 = io.BytesIO()

                page_1 = canvas.Canvas(data_1, pagesize=letter)
                page_1.drawString(133, 645, _user_resident_['complete_name'])
                page_1.drawString(100, 632, f"{_user_resident_['birth_date']}")
                page_1.drawString(300, 632, _user_resident_['birth_city'])
                page_1.drawString(170, 618, _user_resident_['room'])
                page_1.drawString(130, 564, _user_family_['complete_name'])
                page_1.drawString(100, 550, f"{_user_family_['birth_date']}")
                page_1.drawString(240, 550, _user_family_['birth_city'])

                page_1.save()
                data_1.seek(0)

                page_2 = canvas.Canvas(data_2, pagesize=letter)
                page_2.drawString(115, 610, _user_resident_['complete_name'])
                page_2.drawString(400, 610, _user_family_['complete_name'])

                page_2.save()
                data_2.seek(0)

                obj = PersonalizedDocument(document_type=image_authorization.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, image_authorization.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)

                    output_first_page = PyPDF2.PdfFileWriter()
                    output_second_page = PyPDF2.PdfFileWriter()

                    first_page = existing_pdf.getPage(0)
                    pdf_page_1 = PyPDF2.PdfFileReader(data_1).getPage(0)

                    second_page = existing_pdf.getPage(1)
                    pdf_page_2 = PyPDF2.PdfFileReader(data_2).getPage(0)

                    first_page.mergePage(pdf_page_1)
                    second_page.mergePage(pdf_page_2)

                    output_first_page.addPage(first_page)
                    output_second_page.addPage(second_page)

                    with open(os.path.join(settings.MEDIA_ROOT, 'page1.pdf'), 'wb') as f1, open(
                            os.path.join(settings.MEDIA_ROOT, 'page2.pdf'), 'wb') as f2:
                        output_first_page.write(f1), output_second_page.write(f2)
                        f1.close(), f2.close()

                    pdfs = [f1.name, f2.name]
                    merger = PyPDF2.PdfFileMerger()

                    for pdf in pdfs:
                        merger.append(pdf)

                    with open(os.path.join(settings.MEDIA_ROOT + path, image_authorization.document_type + '.pdf'),
                              'wb') as new_file:
                        merger.write(new_file)
                    merger.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, image_authorization.document_type + '.pdf'),
                              'rb') as f:
                        obj.file.save('final.pdf', File(f))
                    os.remove(f"{settings.MEDIA_ROOT}/page1.pdf"), os.remove(f"{settings.MEDIA_ROOT}/page2.pdf")

            bond = MutualDocument.objects.get(document_type='bond')
            if bond:
                data_1 = io.BytesIO()
                data_2 = io.BytesIO()

                page_1 = canvas.Canvas(data_1, pagesize=letter)
                page_1.drawString(70, 495, f"{_user_family_['complete_name']} {_user_family_['birth_date']}")
                page_1.drawString(70, 460, _user_family_['adress'])
                page_1.drawString(70, 425, f"{user.profile.civility} {_user_resident_['complete_name']}")

                page_1.save()
                data_1.seek(0)

                page_2 = canvas.Canvas(data_2, pagesize=letter)
                page_2.drawString(180, 285, "Caution solidaire")
                page_2.drawString(70, 135, r_p_c)
                page_2.drawString(300, 135, r_p_c)

                page_2.save()
                data_2.seek(0)

                obj = PersonalizedDocument(document_type=bond.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, bond.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)

                    output_first_page = PyPDF2.PdfFileWriter()
                    output_second_page = PyPDF2.PdfFileWriter()

                    first_page = existing_pdf.getPage(0)
                    pdf_page_1 = PyPDF2.PdfFileReader(data_1).getPage(0)

                    second_page = existing_pdf.getPage(1)
                    pdf_page_2 = PyPDF2.PdfFileReader(data_2).getPage(0)

                    first_page.mergePage(pdf_page_1)
                    second_page.mergePage(pdf_page_2)

                    output_first_page.addPage(first_page)
                    output_second_page.addPage(second_page)

                    with open(os.path.join(settings.MEDIA_ROOT, 'page1.pdf'), 'wb') as f1, open(
                            os.path.join(settings.MEDIA_ROOT, 'page2.pdf'), 'wb') as f2:
                        output_first_page.write(f1), output_second_page.write(f2)
                        f1.close(), f2.close()

                    pdfs = [f1.name, f2.name]
                    merger = PyPDF2.PdfFileMerger()

                    for pdf in pdfs:
                        merger.append(pdf)

                    with open(os.path.join(settings.MEDIA_ROOT + path, bond.document_type + '.pdf'), 'wb') as new_file:
                        merger.write(new_file)
                    merger.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, bond.document_type + '.pdf'), 'rb') as f:
                        obj.file.save('final.pdf', File(f))
                    os.remove(f"{settings.MEDIA_ROOT}/page1.pdf"), os.remove(f"{settings.MEDIA_ROOT}/page2.pdf")

            price_statement = MutualDocument.objects.get(document_type='price-statement')
            if price_statement:
                data_1 = io.BytesIO()
                data_2 = io.BytesIO()

                page_1 = canvas.Canvas(data_1, pagesize=letter)
                page_1.drawString(100, 730, _user_resident_['complete_name'])

                page_1.save()
                data_1.seek(0)

                page_2 = canvas.Canvas(data_2, pagesize=letter)
                page_2.drawString(46, 235, r_p)
                page_2.drawString(46, 180, r_p)
                page_2.drawString(46, 125, f"{_user_family_['complete_name']} {r_p}")

                page_2.save()
                data_2.seek(0)

                obj = PersonalizedDocument(document_type=price_statement.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, price_statement.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)

                    output_first_page = PyPDF2.PdfFileWriter()
                    output_second_page = PyPDF2.PdfFileWriter()

                    first_page = existing_pdf.getPage(0)
                    pdf_page_1 = PyPDF2.PdfFileReader(data_1).getPage(0)

                    second_page = existing_pdf.getPage(1)
                    pdf_page_2 = PyPDF2.PdfFileReader(data_2).getPage(0)

                    first_page.mergePage(pdf_page_1)
                    second_page.mergePage(pdf_page_2)

                    output_first_page.addPage(first_page)
                    output_second_page.addPage(second_page)

                    with open(os.path.join(settings.MEDIA_ROOT, 'page1.pdf'), 'wb') as f1, open(
                            os.path.join(settings.MEDIA_ROOT, 'page2.pdf'), 'wb') as f2:
                        output_first_page.write(f1), output_second_page.write(f2)
                        f1.close(), f2.close()

                    pdfs = [f1.name, f2.name]
                    merger = PyPDF2.PdfFileMerger()

                    for pdf in pdfs:
                        merger.append(pdf)

                    with open(os.path.join(settings.MEDIA_ROOT + path, price_statement.document_type + '.pdf'),
                              'wb') as new_file:
                        merger.write(new_file)
                    merger.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, price_statement.document_type + '.pdf'),
                              'rb') as f:
                        obj.file.save('final.pdf', File(f))
                    os.remove(f"{settings.MEDIA_ROOT}/page1.pdf"), os.remove(f"{settings.MEDIA_ROOT}/page2.pdf")

            stay_contract = MutualDocument.objects.get(document_type='stay-contract')
            if stay_contract:
                data_1 = io.BytesIO()
                data_2 = io.BytesIO()

                page_1 = canvas.Canvas(data_1, pagesize=letter)
                page_1.setFont('Helvetica', 8)
                page_1.drawString(82, 519, _user_resident_['complete_name'])
                page_1.drawString(202, 519, _user_resident_['birth_city'])
                page_1.drawString(270, 519, f"{_user_resident_['birth_date']}")
                page_1.drawString(370, 519, _user_family_['adress'])
                page_1.save()
                data_1.seek(0)

                page_2 = canvas.Canvas(data_2, pagesize=letter)
                page_2.drawString(200, 235, r_p)
                page_2.drawString(200, 190, r_p)
                page_2.drawString(200, 150, r_p)

                page_2.save()
                data_2.seek(0)

                obj = PersonalizedDocument(document_type=stay_contract.document_type, user=user, user_resident=user_resident)
                with open(os.path.join(settings.MEDIA_ROOT, stay_contract.file.name), 'rb') as file:
                    existing_pdf = PyPDF2.PdfFileReader(file)

                    output_first_page = PyPDF2.PdfFileWriter()
                    output_second_page = PyPDF2.PdfFileWriter()

                    first_page = existing_pdf.getPage(0)
                    pdf_page_1 = PyPDF2.PdfFileReader(data_1).getPage(0)

                    second_page = existing_pdf.getPage(1)
                    pdf_page_2 = PyPDF2.PdfFileReader(data_2).getPage(0)

                    first_page.mergePage(pdf_page_1)
                    second_page.mergePage(pdf_page_2)

                    output_first_page.addPage(first_page)
                    output_second_page.addPage(second_page)

                    with open(os.path.join(settings.MEDIA_ROOT, 'page1.pdf'), 'wb') as f1, open(
                            os.path.join(settings.MEDIA_ROOT, 'page2.pdf'), 'wb') as f2:
                        output_first_page.write(f1), output_second_page.write(f2)
                        f1.close(), f2.close()

                    pdfs = [f1.name, f2.name]
                    merger = PyPDF2.PdfFileMerger()

                    for pdf in pdfs:
                        merger.append(pdf)

                    with open(os.path.join(settings.MEDIA_ROOT + path, stay_contract.document_type + '.pdf'),
                              'wb') as new_file:
                        merger.write(new_file)
                    merger.close()

                    with open(os.path.join(settings.MEDIA_ROOT + path, stay_contract.document_type + '.pdf'),
                              'rb') as f:
                        obj.file.save('final.pdf', File(f))
                    os.remove(f"{settings.MEDIA_ROOT}/page1.pdf"), os.remove(f"{settings.MEDIA_ROOT}/page2.pdf")

        except Exception as error:
            log_doc.error(f"Error generate personalized document {error}")
            messages.error(request, _(error), extra_tags='error')
            return redirect('documents')

    else:
        log_doc.error(f"Document personalized != 10")
        messages.error(request, _(error), extra_tags='error')
        return redirect('documents')

# PdfReadWarning: Xref table not zero-indexed. ID numbers for objects will be corrected. [pdf.py:1736] find this error

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app11_quality.models_qualite import Critere, ChampApplicationPublic, Elementsevaluation, Response

import xlsxwriter as xl
from io import BytesIO


def build_criteria_assessment_xls(user):
    file_buffer = BytesIO()
    workbook = xl.Workbook(file_buffer)
    worksheet = workbook.add_worksheet()

    criteria = Critere.objects.filter(elementsevaluation__evaluation__gt=0).distinct('id')
    today = timezone.now()
    title_str = _('Criteria assessment') + ' ' + _(today.strftime("%B")) + ' ' + today.strftime("%Y")

    # make an array to sort correctly
    array_crit = sorted([(crit.chapitre.number, crit.objectif.number, crit.number, crit.chapitre.title,
                          crit.objectif.title, crit.title, crit.thematique.title, crit.id,
                          f'{crit.manager.user.first_name} {crit.manager.user.last_name}') for crit in criteria],
                        key=lambda x: (x[0], x[1], x[2]))
    max_width = [0, 0, 0, 0, 0]

    worksheet.write(0, 1, 'Chapitre')
    worksheet.write(0, 2, 'Objectifs')
    worksheet.write(0, 3, 'Critères')
    worksheet.write(0, 4, 'Thématique')
    worksheet.write(0, 5, 'Responsable')

    for line, crit in enumerate(array_crit):
        text = [
            f'{crit[0]} - {crit[3]}',
            f'{crit[0]}.{crit[1]} - {crit[4]}',
            f'{crit[0]}.{crit[1]}.{crit[2]} - {crit[5]}',
            f'{crit[6]}',
            f'{crit[8]}',
        ]

        max_width = [
            max(len(text[0]), max_width[0]),
            max(len(text[1]), max_width[1]),
            max(len(text[2]), max_width[2]),
            max(len(text[3]), max_width[3]),
            max(len(text[4]), max_width[4]),
        ]

        worksheet.write(line+1, 1, text[0])
        worksheet.write(line+1, 2, text[1])
        worksheet.write(line+1, 3, text[2])
        worksheet.write(line+1, 4, text[3])
        worksheet.write(line+1, 5, text[4])

        # need to add response and protocol
        response = Response.objects.filter(critere=crit[7]).order_by('-date')
        for column, resp in enumerate(response):
            worksheet.write(line+1, 6+column, f'{_("Created by")} {resp.created_by} on the'
                                              f' {resp.date.strftime("%d/%m/%Y")} : {resp.text}')
    print(max_width)
    for column, mx in enumerate(max_width):
        worksheet.set_column(column+1, column+1, mx)

    worksheet.autofilter(f'A1:F{len(array_crit)}')
    workbook.close()
    file_buffer.seek(0)  # save buffer
    return {'data': file_buffer, 'name': title_str.replace(' ', '_').lower() + '.xlsx'}

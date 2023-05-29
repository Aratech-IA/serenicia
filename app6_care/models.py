import random
from datetime import timedelta

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


from app1_base.models import User, SubSector


# /////////////////////////////////// related to Nappies' Management \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
from app11_quality.models import Protocol_list
from app4_ehpad_base.models import ProfileSerenicia
from app15_calendar.models import PlanningEvent


class Nappy(models.Model):
    name = models.CharField(max_length=80, unique=True)
    brand = models.CharField(max_length=80, blank=True, null=True)
    stock_in_storehouse = models.PositiveSmallIntegerField(default=0)
    maximal_total_stock = models.PositiveSmallIntegerField(default=0)
    nappies_per_bag = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(1)])
    bags_per_box = models.PositiveSmallIntegerField(default=4, validators=[MinValueValidator(1)])
    price_per_box = models.PositiveSmallIntegerField(default=100, validators=[MinValueValidator(1)])
    order_security = models.DecimalField(default=1.10, max_digits=3, decimal_places=2,
                                         validators=[MinValueValidator(1), MaxValueValidator(2)],
                                         help_text="order = consumption_next_7_days * order_security")
    sector = models.ManyToManyField(SubSector, through='SectorNappy', blank=True)
    user = models.ManyToManyField(User, through='UserNappy', blank=True)
    svg_path = models.CharField(max_length=200, blank=True, null=True,
                                default='app4_ehpad_base/img/homemade_svg/nappies/NAME.svg')
    svg_path_new = models.CharField(max_length=200, blank=True, null=True,
                                    default='app4_ehpad_base/img/homemade_svg/nappies/NAME.svg')

    class Meta:
        ordering = ['id']

    @property
    def get_svg_path(self):
        return f"app4_ehpad_base/{self.svg_path_new}"

    def __str__(self):
        return f'{self.id} - {self.name}'


class SectorNappy(models.Model):
    sector = models.ForeignKey(SubSector, on_delete=models.CASCADE)
    nappy = models.ForeignKey(Nappy, on_delete=models.CASCADE)
    stock = models.PositiveSmallIntegerField(blank=True, null=True, default=0)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['sector', 'nappy'], name='a sector and a nappy are unique together')
        ]

    def __str__(self):
        return f'{self.id} - Sector : {self.sector} - Nappy : {self.nappy} - Stock : {self.stock}'


class UserNappy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nappy = models.ForeignKey(Nappy, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(10)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'nappy'], name='a user and a nappy are unique together')
        ]

    def __str__(self):
        return f'{self.user.last_name} {self.user.first_name} | {self.nappy.name} x{self.quantity}'


# /////////////////////////////////// related to Intervention & Nursing \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
PROFESSION_CHOICES = [
    ('AS', _('AS')),
    ('ASH', _('ASH')),
]

VISIBLE_BY_CHOICES = [
    ('Woman', _('Woman')),
    ('Man', _('Man'))
]


class Treatment(models.Model):
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nurse_user')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_user')
    date = models.DateTimeField(auto_now=True)
    nappy = models.ForeignKey(Nappy, on_delete=models.CASCADE, null=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.id} - Nurse: {self.nurse} - Patient: {self.patient} - Date: {self.date}'


class TaskLevel4(models.Model):
    name = models.CharField(max_length=80, unique=True)
    svg_path = models.CharField(max_length=200, blank=True, null=True,
                                default='app4_ehpad_base/img/homemade_svg/NAME_64x64.svg') # 2022/09/15 To be deleted
    svg_path_new = models.CharField(max_length=200, blank=True, null=True,
                                    default='app4_ehpad_base/img/homemade_svg/NAME_64x64.svg')
    shared_with_family = models.BooleanField(default=False)
    to_be_transmitted = models.BooleanField(default=True)
    visible_by = models.CharField(choices=VISIBLE_BY_CHOICES, max_length=5, default=None, null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    protocol = models.ForeignKey(Protocol_list, on_delete=models.CASCADE, null=True, blank=True)
    care_plan = models.BooleanField(default=False)

    @property
    def get_svg_path(self):
        return f"app4_ehpad_base/{self.svg_path_new}"

    def __str__(self):
        return f'{self.id} - {self.name} - A transmettre : {self.to_be_transmitted}'


class TaskLevel3(models.Model):
    name = models.CharField(max_length=80, unique=True)
    svg_path = models.CharField(max_length=200, blank=True, null=True,
                                default='app4_ehpad_base/img/homemade_svg/NAME_64x64.svg')
    svg_path_new = models.CharField(max_length=200, blank=True, null=True,
                                    default='app4_ehpad_base/img/homemade_svg/NAME_64x64.svg')
    shared_with_family = models.BooleanField(default=False)
    to_be_transmitted = models.BooleanField(default=True)
    details = models.ManyToManyField(TaskLevel4, blank=True)
    visible_by = models.CharField(choices=VISIBLE_BY_CHOICES, max_length=5, default=None, null=True, blank=True)
    nappy = models.ManyToManyField(Nappy, blank=True)
    duration = models.DurationField(null=True, blank=True)
    protocol = models.ForeignKey(Protocol_list, on_delete=models.CASCADE, null=True, blank=True)
    care_plan = models.BooleanField(default=False)
    reject = models.BooleanField(default=False)

    @property
    def get_svg_path(self):
        return f"app4_ehpad_base/{self.svg_path_new}"

    def __str__(self):
        return f'{self.id} - {self.name} - A transmettre : {self.to_be_transmitted}'


class TaskLevel2(models.Model):
    name = models.CharField(max_length=80, unique=True)
    svg_path = models.CharField(max_length=200, blank=True, null=True,
                                default='app4_ehpad_base/img/homemade_svg/NAME_64x64.svg')
    svg_path_new = models.CharField(max_length=200, blank=True, null=True,
                                    default='app4_ehpad_base/img/homemade_svg/NAME_64x64.svg')
    shared_with_family = models.BooleanField(default=False)
    to_be_transmitted = models.BooleanField(default=True)
    details = models.ManyToManyField(TaskLevel3, blank=True, related_name='match_btw_task_level_2_and_3')
    visible_by = models.CharField(choices=VISIBLE_BY_CHOICES, max_length=5, default=None, null=True, blank=True)
    nappy = models.ManyToManyField(Nappy, blank=True)
    duration = models.DurationField(null=True, blank=True)
    protocol = models.ForeignKey(Protocol_list, on_delete=models.CASCADE, null=True, blank=True)
    care_plan = models.BooleanField(default=False)

    @property
    def get_svg_path(self):
        return f"app4_ehpad_base/{self.svg_path_new}"

    def __str__(self):
        return f'{self.id} - {self.name} - Visible par la famille : {self.shared_with_family} - ' \
               f'A transmettre : {self.to_be_transmitted}'


def random_color():
    return f'#{"%03x" % random.randint(0, 0xFFFFFF)}'


class TaskLevel1(models.Model):
    name = models.CharField(max_length=80, unique=True)
    svg_path = models.CharField(max_length=200, blank=True, null=True,
                                default='app4_ehpad_base/img/homemade_svg/NAME_64x64.svg')
    svg_path_new = models.CharField(max_length=200, blank=True, null=True,
                                    default='app4_ehpad_base/img/homemade_svg/NAME_64x64.svg')
    details = models.ManyToManyField(TaskLevel2, blank=True)
    profession = models.CharField(choices=PROFESSION_CHOICES, default='AS', max_length=3)
    specific_to_a_resident = models.BooleanField(default=True)
    nappy = models.ManyToManyField(Nappy, blank=True)
    protocol = models.ForeignKey(Protocol_list, on_delete=models.CASCADE, null=True, blank=True)
    care_plan = models.BooleanField(default=True)
    color = models.CharField(max_length=7, default=random_color)

    @property
    def get_svg_path(self):
        return f"app4_ehpad_base/{self.svg_path_new}"

    def __str__(self):
        return f'{self.id} - {self.name} - {self.profession} - {self.specific_to_a_resident}'


# different types of comment : make distinction btw "consignes d'accompagnement et transmission complémentaire"
class TaskComment(models.Model):
    content = models.CharField(blank=True, default='', max_length=1500)
    related_task_level_2 = models.ForeignKey(TaskLevel2, on_delete=models.CASCADE, blank=True, null=True)
    related_task_level_3 = models.ForeignKey(TaskLevel3, on_delete=models.CASCADE, blank=True, null=True)
    related_task_level_4 = models.ForeignKey(TaskLevel4, on_delete=models.CASCADE, blank=True, null=True)


class InterventionDetail(models.Model):
    task_level_2 = models.ForeignKey(TaskLevel2, on_delete=models.CASCADE, blank=True, null=True)
    task_level_3 = models.ForeignKey(TaskLevel3, on_delete=models.CASCADE, blank=True, null=True)
    task_level_4 = models.ForeignKey(TaskLevel4, on_delete=models.CASCADE, blank=True, null=True)
    nappy = models.ForeignKey(Nappy, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f'ID {self.id} - Nom : {self.task_level_2.name}'


class Intervention(models.Model):
    type = models.ForeignKey(TaskLevel1, on_delete=models.CASCADE)
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nurse')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient', blank=True, null=True)
    specific_to_a_resident = models.BooleanField(default=True)
    details = models.ManyToManyField(InterventionDetail, blank=True)
    start = models.DateTimeField(auto_now_add=True)
    end = models.DateTimeField(null=True)
    transmitted = models.BooleanField(default=False)
    task_comment = models.ManyToManyField(TaskComment, blank=True)
    profession = models.CharField(choices=PROFESSION_CHOICES, default='AS', max_length=3)
    from_care_plan = models.BooleanField(default=False)
    lvl1_inter_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.patient}, {self.type} - début:{self.start}, fin:{self.end}'

    def save(self, *args, **kwargs):
        if self.patient and not self.specific_to_a_resident:
            raise ValueError("if patient is specified, intervention should be specific to a resident")
        super().save(*args, **kwargs)


class FreeComment(models.Model):
    content = models.CharField(max_length=1500)
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='free_comment_nurse')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='free_comment_patient', null=True,
                                blank=True)
    start = models.DateTimeField(auto_now_add=True)
    profession = models.CharField(choices=PROFESSION_CHOICES, default='AS', max_length=3)


class TreatmentsPlan(models.Model):
    patient = models.OneToOneField(User, on_delete=models.CASCADE)
    modified_at = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.patient.last_name} {self.patient.first_name}'

#
# class DailyOccurrence(models.Model):
#     start_time = models.TimeField()
#
#     def __str__(self):
#         return f'{self.start_time}'
#
#
# # roll on 4 weeks
# class MonthlyOccurrence(models.Model):
#     DAY_CHOICES = [
#         (1, _('Week 1 - Monday')),
#         (2, _('Week 1 - Tuesday')),
#         (3, _('Week 1 - Wednesday')),
#         (4, _('Week 1 - Thursday')),
#         (5, _('Week 1 - Friday')),
#         (6, _('Week 1 - Saturday')),
#         (7, _('Week 1 - Sunday')),
#         (8, _('Week 2 - Monday')),
#         (9, _('Week 2 - Tuesday')),
#         (10, _('Week 2 - Wednesday')),
#         (11, _('Week 2 - Thursday')),
#         (12, _('Week 2 - Friday')),
#         (13, _('Week 2 - Saturday')),
#         (14, _('Week 2 - Sunday')),
#         (15, _('Week 3 - Monday')),
#         (16, _('Week 3 - Tuesday')),
#         (17, _('Week 3 - Wednesday')),
#         (18, _('Week 3 - Thursday')),
#         (19, _('Week 3 - Friday')),
#         (20, _('Week 3 - Saturday')),
#         (21, _('Week 3 - Sunday')),
#         (22, _('Week 4 - Monday')),
#         (23, _('Week 4 - Tuesday')),
#         (24, _('Week 4 - Wednesday')),
#         (25, _('Week 4 - Thursday')),
#         (26, _('Week 4 - Friday')),
#         (27, _('Week 4 - Saturday')),
#         (28, _('Week 4 - Sunday')),
#     ]
#     day = models.IntegerField(choices=DAY_CHOICES)
#     daily_occurrence = models.ForeignKey(DailyOccurrence, on_delete=models.CASCADE, null=True)
#
#     def __str__(self):
#         return f'{self.day}'
#
#
# class TreatmentsPlanTask(models.Model):
#     treatments_plan = models.ForeignKey(TreatmentsPlan, on_delete=models.CASCADE)
#     task_level_2 = models.ForeignKey(TaskLevel2, on_delete=models.CASCADE, blank=True, null=True)
#     task_level_3 = models.ForeignKey(TaskLevel3, on_delete=models.CASCADE, blank=True, null=True)
#     task_level_4 = models.ForeignKey(TaskLevel4, on_delete=models.CASCADE, blank=True, null=True)
#     monthly_occurrence = models.ForeignKey(MonthlyOccurrence, on_delete=models.CASCADE, null=True)
#
#     def save(self, *args, **kwargs):
#         if (self.task_level_2 and self.task_level_3) or (self.task_level_2 and self.task_level_4) or \
#                 (self.task_level_3 and self.task_level_4):
#             raise ValueError('Only one task could be selected')
#         super().save(args, kwargs)
#
#     def __str__(self):
#         if self.task_level_2:
#             return f'{self.id} - {self.treatments_plan.patient.first_name} - {self.task_level_2.name}'
#         if self.task_level_3:
#             return f'{self.id} - {self.treatments_plan.patient.first_name} - {self.task_level_3.name}'
#         if self.task_level_4:
#             return f'{self.id} - {self.treatments_plan.patient.first_name} - {self.task_level_4.name}'


class TaskInTreatmentPlan(models.Model):
    DAY_CHOICES = [
        (1, _('Week 1 - Monday')),
        (2, _('Week 1 - Tuesday')),
        (3, _('Week 1 - Wednesday')),
        (4, _('Week 1 - Thursday')),
        (5, _('Week 1 - Friday')),
        (6, _('Week 1 - Saturday')),
        (7, _('Week 1 - Sunday')),
    ]
    treatments_plan = models.ForeignKey(TreatmentsPlan, on_delete=models.CASCADE)
    task_level_2 = models.ForeignKey(TaskLevel2, on_delete=models.CASCADE, blank=True, null=True)
    task_level_3 = models.ForeignKey(TaskLevel3, on_delete=models.CASCADE, blank=True, null=True)
    task_level_4 = models.ForeignKey(TaskLevel4, on_delete=models.CASCADE, blank=True, null=True)
    day_in_cycle = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if (self.task_level_2 and self.task_level_3) or (self.task_level_2 and self.task_level_4) or \
                (self.task_level_3 and self.task_level_4):
            raise ValueError('Only one task could be selected in once')
        super().save(args, kwargs)

    def __str__(self):
        if self.task_level_2:
            return f'{self.id} - {self.treatments_plan.patient.first_name} - {self.task_level_2.name}'
        if self.task_level_3:
            return f'{self.id} - {self.treatments_plan.patient.first_name} - {self.task_level_3.name}'
        if self.task_level_4:
            return f'{self.id} - {self.treatments_plan.patient.first_name} - {self.task_level_4.name}'


class InterventionTreatmentPlan(models.Model):

    treatment_plan_task = models.ForeignKey(TaskInTreatmentPlan, on_delete=models.CASCADE)
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intervention_treatment_plan_nurse')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intervention_treatment_plan_patient')
    planned_time = models.DateTimeField(blank=True, null=True)
    intervention_time = models.DateTimeField(auto_now=True)
    profession = models.CharField(choices=PROFESSION_CHOICES, default='AS', max_length=3)


class TmpInterventionTreatmentPlanForWebsocket(models.Model):
    intervention_treatment_plan = models.OneToOneField(InterventionTreatmentPlan, on_delete=models.CASCADE)
    is_done = models.BooleanField()
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tmp_nurse', blank=True, null=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tmp_patient', blank=True, null=True)


class CarePlanEvent(models.Model):
    planning_event_new = models.ForeignKey(PlanningEvent, models.CASCADE, null=True)
    task_lvl_1 = models.ForeignKey(TaskLevel1, models.CASCADE, null=True)
    task_lvl_2 = models.ForeignKey(TaskLevel2, models.CASCADE, null=True)
    task_lvl_3 = models.ForeignKey(TaskLevel3, models.CASCADE, null=True)
    task_lvl_4 = models.ForeignKey(TaskLevel4, models.CASCADE, null=True)
    lvl1_inter_id = models.IntegerField(null=True, blank=True)


class CarePlan(models.Model):
    resident = models.ForeignKey(ProfileSerenicia, models.CASCADE)
    tasks = models.ManyToManyField(CarePlanEvent)


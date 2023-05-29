import datetime

from django.test import TestCase

from app12_delivery.models import *
from app12_delivery.batch.auto_ordering_tour import get_tomorrow


# exemple mock date
# @mock.patch('app.datetime')
# def test_my_great_func(mocked_datetime):
#     mocked_datetime.now.return_value = datetime(2010, 1, 1)
#     assert my_great_func() == datetime(2010, 1, 1)


class GpsTestCase(TestCase):
    def setUp(self):
        usr1 = User.objects.create(last_name="toto", first_name="dupost")
        ContractDelivery.objects.create(user=usr1, date_start_contract=datetime.date(2022, 1, 1),
                                        date_end_contract=datetime.date(2023, 1, 1), type_housing="house",
                                        payment_method="sampling")
        usr2 = User.objects.create(last_name="toyo", first_name="dupoft")
        ContractDelivery.objects.create(user=usr2, date_start_contract=datetime.date(2022, 1, 1),
                                        date_end_contract=datetime.date(2023, 1, 1), type_housing="house",
                                        payment_method="sampling")
        usr3 = User.objects.create(last_name="topo", first_name="dupont")
        ContractDelivery.objects.create(user=usr3, date_start_contract=datetime.date(2022, 1, 1),
                                        date_end_contract=datetime.date(2023, 1, 1), type_housing="house",
                                        payment_method="sampling")

    def test_ordering(self):
        assert get_tomorrow() == datetime.date(2022, 1, 21)

    def test_ordering_now_is_far(self):
        assert get_tomorrow() == datetime.date(2022, 1, 21)

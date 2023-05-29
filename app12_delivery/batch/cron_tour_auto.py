from datetime import timedelta, datetime

from app12_delivery.batch.auto_ordering_tour import ordering_tour

ordering_tour(datetime.today().date() + timedelta(days=1))

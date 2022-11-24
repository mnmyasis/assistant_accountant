import json

from celery import shared_task

from . import ads
from .write_ads_data import WriteDB


@shared_task(name='collect_agency_client_spending')
def collect_agency_client_spending(user_id: int, date_from: str, date_to: str):
    """
    Format date_from, date_to %Y-%d-%m
    Таска собирает финансовую статистику клиентов агентства из рекламных
    кабинетов.
    """
    data = ads.get(user_id, date_from, date_to)
    write_db = WriteDB(data)
    write_db.save()
    print(json.dumps(data, indent=4))
    return (f'task: agency_client\nParameters: \n- user_id: {user_id}\n'
            f'- date_from: {date_from}\n- date_to: {date_to}')

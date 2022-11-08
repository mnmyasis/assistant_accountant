import json

from celery import shared_task

from .ads import (API, YandexAgencyClients, VKAgencyClients,
                  MyTargetAgencyClients)


@shared_task(name='agency_clients')
def agency_clients(user_id: int):
    yandex = YandexAgencyClients(user_id, on_sandbox=True)
    vk = VKAgencyClients(user_id)
    my_target = MyTargetAgencyClients(user_id)
    cabinets = [yandex, my_target, vk]
    data = []
    for cabinet in cabinets:
        api = API(cabinet)
        data += api.agency_clients()
    for line in data:
        print(json.dumps(line, indent=4))
    return data

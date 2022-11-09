import json

from celery import shared_task

from .ads import (API, YandexAgencyClients, VKCollectData,
                  MyTargetCollectData)


@shared_task(name='agency_clients')
def agency_clients(user_id: int):
    date_from = '2022-11-01'
    date_to = '2022-11-09'
    yandex = YandexAgencyClients(user_id, on_sandbox=True)
    vk = VKCollectData(user_id, date_from, date_to)
    my_target = MyTargetCollectData(user_id, date_from, date_to)
    cabinets = [yandex, my_target, vk]
    data = []
    for cabinet in cabinets:
        api = API(cabinet)
        data += api.collect_data_ads()
    print(json.dumps(data, indent=4))
    return data

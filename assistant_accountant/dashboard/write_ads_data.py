from typing import Dict, List

from django.db import transaction

from .models import (AgencyClient, StatisticByAgencyClient, BalanceHistory,
                     User, Source, VkAccount, VK_ADS)


class WriteDB:

    def __init__(self, data: List[Dict]):
        self.data = data

    def agency_clients(
            self,
            user: User,
            source: Source,
            client_id: int,
            name: str,
            vk_account: VkAccount = None
    ) -> AgencyClient:
        agency_client, _ = AgencyClient.objects.update_or_create(
            user=user,
            client_id=client_id,
            source=source,
            defaults={
                'user': user,
                'source': source,
                'client_id': client_id,
                'name': name,
                'account': vk_account
            }
        )
        return agency_client

    def statistic_by_agency_client(
            self,
            source: Source,
            agency_client: AgencyClient,
            stats: List[Dict]
    ) -> None:
        for stat in stats:
            StatisticByAgencyClient.objects.update_or_create(
                client=agency_client,
                source=source,
                date=stat['date'],
                defaults={
                    'client': agency_client,
                    'source': source,
                    'cost': stat['cost'],
                    'date': stat['date']
                }
            )

    def balance_history(
            self,
            agency_client: AgencyClient,
            source: Source,
            amount: float,
            date: str
    ) -> None:
        BalanceHistory.objects.update_or_create(
            client=agency_client,
            source=source,
            date=date,
            defaults={
                'client': agency_client,
                'source': source,
                'amount': amount,
                'date': date
            }
        )

    def vk_account(self, user: User, account_id: int) -> VkAccount:
        account, _ = VkAccount.objects.update_or_create(
            user=user,
            account_id=account_id,
            defaults={
                'user': user,
                'account_id': account_id,
                'name': user.username
            }
        )
        return account

    def save(self) -> None:
        with transaction.atomic():
            for raw in self.data:
                user = User.objects.get(pk=raw['user_id'])
                source = Source.objects.get(name=raw['source'])
                vk_account = None
                if source.name == VK_ADS:
                    account_id = raw['account_id']
                    vk_account = self.vk_account(user, account_id)
                client_id = raw['client_id']
                name = raw['name']
                stats = raw['stats']
                amount = raw['balance']['amount']
                date = raw['balance']['date']
                agency_client = self.agency_clients(
                    user, source, client_id, name, vk_account
                )
                self.statistic_by_agency_client(source, agency_client, stats)
                self.balance_history(agency_client, source, amount, date)

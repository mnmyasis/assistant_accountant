from abc import ABC, abstractmethod

import gspread
from oauth2client import crypt
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = ('https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive')


def get_credentials(
        private_key: str,
        private_key_id: str,
        client_email: str,
        client_id: str) -> ServiceAccountCredentials:
    signer = crypt.Signer.from_string(private_key)
    cred = ServiceAccountCredentials(
        service_account_email=client_email,
        signer=signer,
        private_key_id=private_key_id,
        client_id=client_id,
        scopes=SCOPES
    )
    cred._private_key_pkcs8_pem = private_key
    return cred


class WorkSheet:
    """Интерфейс get возвращает объект worksheet.

    :param str table_name: Название гугл таблицы.
    :param str sheet_name: Название листа в таблице.
    :param ServiceAccountCredentials credentials: Доступы сервисного аккаунта.
    :returns: a :class:`~gspread.models.Spreadsheet` instance.

    >>> WorkSheet.get('table_name', 'sheet_name', ServiceAccountCredentials())
    """

    def __init__(
            self,
            table_name: str,
            sheet_name: str,
            credentials: ServiceAccountCredentials
    ):
        self.__credentials = credentials
        self.__table_nmae = table_name
        self.__sheet_name = sheet_name

    def get_client(self) -> gspread.Client:
        return gspread.authorize(credentials=self.__credentials)

    def get_spread_sheet(self, client: gspread.Client) -> gspread.Spreadsheet:
        return client.open(self.__table_nmae)

    def get_worksheet(
            self,
            spread_sheet: gspread.Spreadsheet
    ) -> gspread.worksheet.Worksheet:
        return spread_sheet.worksheet(self.__sheet_name)

    @staticmethod
    def get(
            table_name: str,
            sheet_name: str,
            credentials: ServiceAccountCredentials
    ):
        ws = WorkSheet(table_name, sheet_name, credentials)
        client = ws.get_client()
        spread_sheet = ws.get_spread_sheet(client)
        worksheet = ws.get_worksheet(spread_sheet)
        return worksheet


class Alphabet(ABC):

    @abstractmethod
    def letter_by_index(self, index: int) -> str:
        ...


class AlphabetGoogleSheets(Alphabet):

    def __init__(self):
        self.__letters = (
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O',
            'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z')

    def letter_by_index(self, index: int) -> str:
        return self.__letters[index - 1]


class Redactor:

    def __init__(
            self,
            worksheet: gspread.Worksheet,
            range_name: str
    ):
        self.__range_name = range_name
        self.__worksheet = worksheet

    def update(self, columns):
        self.__worksheet.update(self.__range_name, columns)

    @staticmethod
    def google_sheets_redactor(worksheet: gspread.Worksheet, range_name: str):
        redactor = Redactor(worksheet, range_name)
        return redactor

    @staticmethod
    def google_sheets_redactor_by_tag(
            worksheet: gspread.Worksheet,
            tag: str,
            alphabet: Alphabet
    ):
        cell = worksheet.find(tag)
        range_name = '{}{}'.format(alphabet.letter_by_index(cell.col),
                                   cell.row + 1)
        redactor = Redactor(worksheet, range_name)
        return redactor

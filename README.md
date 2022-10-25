# assistant_accountant
Инструментарий для бухгалтерии в сфере интернет рекламы

# Перменные окружения:
```
SECRET_KEY=
YANDEX_DIRECT_CLIENT_ID=
YANDEX_DIRECT_CLIENT_SECRET=
VK_CLIENT_ID=
VK_CLIENT_SECRET=
VK_REDIRECT_URL=
MY_TARGET_CLIENT_ID=
MY_TARGET_CLIENT_SECRET=
```

# Запуск проекта:

### Linux
```
python3 -m venv venv
source venv/bin/activate
cd assistant_accountant
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Windows(PowerShell)
```
python3.exe -m venv venv
venv/Script/activate
cd assistant_accountant
pip install -r requirements.txt
python.exe manage.py migrate
python.exe manage.py runserver
```

### Другие команды:
- Создать супер юзера
```
python manage.py createsuperuser
```

# Технологии:

 - Django

# Авторы:

- Мясищев Максим
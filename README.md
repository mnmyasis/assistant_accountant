# assistant_accountant
Инструментарий для бухгалтерии в сфере интернет рекламы


# Запуск проекта:
- Установить виртуальное окружение
```
python -m venv venv
```
- Активировать виртуальное окружение
- Для Linux:
```
source venv/bin/activate
```
- Для Windows(PowerShell):
```
venv/Script/activate
```
- Перейти в каталог \assistant_accountant, в котором должен находиться файл manage.py
```
cd assistant_accountant
```
- Установить зависимости
```
pip install -r requirements.txt
```
- Выполнить миграции
```
python manage.py migrate
```
- Запустить дев сервер
```
python manage.py runserver
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
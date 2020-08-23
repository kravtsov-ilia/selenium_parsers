# selenium_parsers
Selenium parsers - проект для мониторинга социальных сетей, который позволяет следить за развитием групп/каналов в соц. сетях,
анализировать активность аудитории и корректировать контентную политику.

Правила работы в в проетке:
# Настройка линтеров
Для настройки линтеров необходимо установить `flake8` и `git-pylint-commit-hook`,  
необходимые версии указаны в файле `requirements.txt`  
После установки `flake8` выполнить:  
`git config --bool flake8.strict true`

`git-pylint-commit-hook` - настраивается автоматически

Теперь после команды `git commit`, если код не соответствует рекомендациям PEP8 появятся подобные ошибки:
```
api/api/tasks_helpers.py:1:1: F401 'telethon.sync.TelegramClient' imported but unused
api/api/tasks_helpers.py:3:1: F401 'time' imported but unused
api/api/tasks_helpers.py:3:16: E401 multiple imports on one line
```  
Это означает что эти файлы необходимо поправить.

# Логирование ошибок
Для записи сообщений в лог используем стандартный модуль питона - `logging`
Пример использования:
```
import logging
logger = logging.getLogger(__name__)

def make_request(some_dict):
    try:
        response = requests.get('some_url')
    except TimeoutError:
        logger.error('Some text', exc_info=True)
```

# Запуск тестов
Добавляем тесты в проект, пока тесты действуют только для backend сервиса, чтобы запустить тест  
нужно перейти в `api/` и запустить команду `pytest --cov --cov-config=setup.cfg`
 
# Бэкапы
* Список бекапов mongo: `docker exec mongobackups ls /backup`
* Восстановить бекап из списка: `docker exec mongobackups /restore.sh "/backup/'2015.08.06.171901'"`
* Запустить бекап вручную: `docker exec mongobackups /backup.sh`

Такой же список комманд для postgres
* `docker exec pgbackups ls /backups/daily` or /backups/weekly or /backups/monthly
* `docker exec -e PGPASSWORD={пароль} pgbackups pg_restore -Fc -c -1 -d {база данных} -h postgres -p 5432 -U {пользователь} -w /backups/daily/database-20200430-060136.sql.gz`
* `docker exec pgbackups /backup.sh`

# Импорт даннх на локальную машину
* Зайти на продакшн `/mongo-express/` 
* Выбрать нужную коллекцию
* Нажать `Export Standard`, будет скачан json файл с копией данных
* Перенести скачанную копию внутрь контейнера монго, например так:   
  `docker cp ~/Downloads/collection_data.json mongo:/tmp/`
   
* Запустить команду:  
  `docker exec mongo mongoimport -d {база данных} -c {название коллекции} --file /tmp/collection_data.json`

# Локальный запуск и разработка
Для разработки есть отдельный compose файл docker-compose.yml (для продакшена используется docker-compose-prod.yml). Проект запускается через `docker-compose up`, перебилживать контейнеры не нужно, код подтягивается через bind mountы докера. Фронтэнд, селери и бекэнд обновляются с изменением их кода.

# Деплой
Деплой происходит с помошью загрузки собранных образов сервисов на приватный  
docker registry сервер, их последующего скачивания на боевой сервер   
и запуска docker-compose    
  
Для того, чтобы авторизоваться в docker registry необходимо установить в систему ssl сертификат (спросить у команды разработки)  
Также нужно иметь логин и пароль пользователя docker registry, его тоже нужно уточнить у команды.  
  
При деплое собираются все образы сервисов и пушатся в  docker registry,  
далее эти образы тянутся с docker registry и запускаются

Также deploy поддерживает ветки, чтобы залить не тестовую версию используй ветку latest.
Вместо передачи адресса регистри и названия ветки в скрипт деплоя и предеплоя, можно поставить переменные окружения REGISTRY_URL и BRANCH соответственно

Для деплоя в бой необходимо:
* Залогинится в docker registry: `docker login {адрес сервера}`   
* Запустить `./push.sh %branch_name% %registry_url%`, эта команда соберет образы всех сервисов и зальет их в docker registry
* Зайти на боевой сервер и запустить `./pull.sh %branch_name% %registry_url%` - этот скрипт спулит все сервисы проекта
* Запустить проект `docker-compose down && docker-compose up -d`

# Запустить таск
Поменять в command celery на `python manage.py runtask yt_parse_channels` и docker-compose up celery

# Обновление сертификата
Для принудительного обновления сертификата нужно добавить в команду certbot флаг --force-renewal
Для генерации или обновления сертификата проверьте, что nginx контейнер работает и принимает http запросы

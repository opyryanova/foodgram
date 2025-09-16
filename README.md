# Foodgram

Проект курса **Python-разработчик+** Яндекс.Практикум.  
Сервис для публикации кулинарных рецептов, подписок на авторов и формирования списка покупок.  

Продакшн-версия: [https://foodgram-practicum.hopto.org/](https://foodgram-practicum.hopto.org/)  

---

## Возможности

- регистрация и аутентификация пользователей;  
- публикация и редактирование рецептов;  
- фильтрация по тегам (завтрак, обед, ужин);  
- добавление рецептов в избранное;  
- подписки на авторов и просмотр ленты подписок;  
- формирование и скачивание списка покупок (ингредиенты суммируются);  
- смена аватара пользователя;  
- API-документация через **Redoc**.  

---

## Стек технологий

- **Backend**: Django, Django REST Framework, Djoser  
- **Frontend**: React  
- **База данных**: PostgreSQL  
- **Инфраструктура**: Docker, docker-compose, Gunicorn, Nginx  
- **CI/CD**: GitHub Actions + деплой на сервер (Yandex.Cloud)  
- **Документация API**: OpenAPI/Redoc  

---

## Структура проекта

- `backend/` — Django-проект (`users`, `recipes`, `api`).  
- `frontend/` — React-приложение (собранный build подключается к nginx).  
- `data/` — список ингредиентов в CSV.  
- `infra/` — конфигурация docker-compose и nginx.  
- `.github/workflows/` — GitHub Actions workflow.  
- `.env.example` — пример настроек окружения.  

---

## Развёртывание локально

1. Установите [Docker](https://www.docker.com/) и [docker-compose](https://docs.docker.com/compose/).  
2. Клонируйте репозиторий:  
   ```bash
   git clone https://github.com/opyryanova/foodgram
   cd foodgram/infra
   ```
3. Создайте файл `.env` на основе `.env.example`:  

   ```env
   SECRET_KEY=your-secret-key
   ALLOWED_HOSTS=your-hosts
   CSRF_TRUSTED_ORIGINS=your-csrf
   DEBUG=False
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=foodgram
   POSTGRES_USER=foodgram
   POSTGRES_PASSWORD=foodgram
   DB_HOST=db
   DB_PORT=5432
   DOCKER_USERNAME=your-docker-username
   ```

4. Запустите контейнеры:  
   ```bash
   docker-compose up -d --build
   ```
5. Примените миграции и загрузите данные:  
   ```bash
   docker-compose exec backend python manage.py migrate
   docker-compose exec backend python manage.py collectstatic --no-input
   docker-compose exec backend python manage.py load_ingredients
   docker-compose exec backend python manage.py load_demo_data
   docker-compose exec backend python manage.py createsuperuser
   ```
6. Откройте сайт: [http://localhost/](http://localhost/)  
   Документация API: [http://localhost/api/docs/](http://localhost/api/docs/)  

---

## Развёртывание на сервере

Автодеплой через **GitHub Actions** (`.github/workflows/foodgram_workflow.yml`).  
Необходимые секреты репозитория:

| Секрет              | Описание                          |
|---------------------|-----------------------------------|
| `DOCKER_USERNAME`   | имя пользователя DockerHub        |
| `DOCKER_PASSWORD`   | пароль от DockerHub               |
| `HOST`              | IP-адрес сервера                  |
| `USER`              | имя пользователя на сервере       |
| `SSH_KEY`           | приватный SSH-ключ                |
| `SSH_PASSPHRASE`    | парольная фраза для ключа (если есть) |
| `TELEGRAM_TO`       | ID получателя уведомлений в Telegram |
| `TELEGRAM_TOKEN`    | токен Telegram-бота               |
| `SECRET_KEY`        | секретный ключ Django             |
| `DB_ENGINE`         | движок базы данных (например, `django.db.backends.postgresql`) |
| `DB_NAME`           | имя базы данных                   |
| `POSTGRES_USER`     | пользователь базы данных          |
| `POSTGRES_PASSWORD` | пароль пользователя БД            |
| `DB_HOST`           | хост БД (обычно `db`)             |
| `DB_PORT`           | порт БД (обычно `5432`)           |

Workflow при пуше в `main`:  
1. Собирает образы backend и frontend, пушит их в DockerHub.  
2. Подключается к серверу, перезапускает контейнеры.  
3. Выполняет миграции, собирает статику, загружает ингредиенты и демо-рецепты.  
4. Уведомляет в Telegram о деплое.  

---

## Автор

**Ольга Пырьянова**
https://github.com/opyryanova
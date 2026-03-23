# Улучшенный план: Django-сайт для бадминтона

## 🎯 Финальная архитектура (лучшее от Claude + ChatGPT)

### Технологический стек (ИСПРАВЛЕНО)

```
Backend:  Django 5.0 (вместо Flask)
Database: PostgreSQL (вместо SQLite)
Frontend: Django Templates + Tailwind CSS
Task Queue: Celery + Redis (для фоновых задач)
Scheduler: django-crontab (вместо APScheduler)
Email: Django Email + Gmail SMTP
Hosting: Render.com (бесплатно)
```

**Почему Django, а не Flask:**
1. ✅ Готовая админ-панель из коробки
2. ✅ Встроенная система авторизации
3. ✅ ORM для работы с БД
4. ✅ Готовые формы с валидацией
5. ✅ Система прав (permissions)
6. ✅ Экономия 2-3 недель разработки

---

## 📐 Структура базы данных (расширенная)

### 1. User (встроенная модель Django + расширение)
```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telegram_id = models.IntegerField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    display_name = models.CharField(max_length=100)
    
    # Статус регистрации
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('approved', 'Утверждён'),
        ('rejected', 'Отклонён'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Метаданные
    approved_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='approved_users')
    approved_at = models.DateTimeField(null=True, blank=True)
    registration_comment = models.TextField(blank=True)
    
    # Статистика (для рейтинга)
    total_games = models.IntegerField(default=0)
    attended_games = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

### 2. Game
```python
class Game(models.Model):
    # Основная информация
    game_date = models.DateField()
    game_time = models.TimeField(default='21:00')
    venue = models.CharField(max_length=200, default='Электролитный пр.3, стр.5')
    description = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=6, decimal_places=2, default=800)
    
    # Лимиты
    main_limit = models.IntegerField(default=18)
    reserve_limit = models.IntegerField(default=10)
    
    # Расписание записи
    registration_opens_at = models.DateTimeField()
    registration_closes_at = models.DateTimeField()
    
    # Статус игры
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('announced', 'Анонсирована'),
        ('open', 'Запись открыта'),
        ('closed', 'Запись закрыта'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 3. Registration (запись на игру)
```python
class Registration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='registrations')
    
    # Статус записи
    STATUS_CHOICES = [
        ('main', 'Основа'),
        ('reserve', 'Резерв'),
        ('declined', 'Отказ'),
        ('cancelled', 'Отменено'),
        ('removed', 'Удалено админом'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    position = models.IntegerField(null=True, blank=True)  # Порядковый номер в списке
    
    # История изменений
    SOURCE_CHOICES = [
        ('player', 'Сам игрок'),
        ('admin', 'Администратор'),
        ('auto', 'Автоматическое продвижение'),
    ]
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='player')
    
    # Временные метки
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Комментарий игрока
    player_comment = models.TextField(blank=True)
    
    # Метаданные
    modified_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='modified_registrations')
    
    class Meta:
        unique_together = ('user', 'game')
        ordering = ['registered_at']
```

### 4. Announcement (объявления админов)
```python
class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Настройки отображения
    is_pinned = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Уведомления
    notify_all = models.BooleanField(default=False)  # Отправить email всем
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
```

### 5. Comment (комментарии к играм)
```python
class Comment(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    
    content = models.TextField()
    
    # Вложенные комментарии (опционально)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    # Модерация
    is_visible = models.BooleanField(default=True)
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
```

### 6. AdminAction (журнал действий админа)
```python
class AdminAction(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # 'approve_user', 'create_game', 'move_player', etc.
    description = models.TextField()
    
    # Связанные объекты (опционально)
    related_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='admin_actions_received')
    related_game = models.ForeignKey(Game, null=True, blank=True, on_delete=models.SET_NULL)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
```

---

## 🎨 Основные страницы (расширенный список)

### Для неавторизованных:
1. **Лендинг** - краткое описание клуба
2. **Вход** - форма логина
3. **Регистрация** - форма с комментарием "кто я"
4. **Восстановление пароля**

### Для игроков (одобренных):
1. **Главная** - ближайшая игра + кнопка записи
2. **Мой профиль** - редактирование данных
3. **История игр** - мои прошлые игры
4. **Статистика** - мой рейтинг, статистика посещений
5. **Объявления** - лента объявлений от админов
6. **Все игры** - календарь будущих игр

### Для игроков (ожидающих):
1. **Ожидание подтверждения** - информационная страница

### Для админов:
1. **Админ-панель** - Django Admin (встроенная)
2. **Создание игры** - форма с датой, временем, лимитами
3. **Управление играми** - список всех игр
4. **Управление записью** - ручное перемещение игроков
5. **Утверждение регистраций** - список ожидающих
6. **Публикация объявлений** - форма объявления
7. **Журнал действий** - история действий админов
8. **Статистика клуба** - общая статистика

---

## 🔄 Автоматизация (как в боте)

### Django Cron Jobs:
```python
# myapp/cron.py

from django_cron import CronJobBase, Schedule
from datetime import datetime
from .models import Game, Registration
from .utils import send_email, promote_from_reserve

class OpenRegistration(CronJobBase):
    """Понедельник 00:01 - открыть запись"""
    schedule = Schedule(run_at_times=['00:01'])
    code = 'myapp.open_registration'
    
    def do(self):
        # Найти игры, которые нужно открыть
        now = datetime.now()
        games = Game.objects.filter(
            registration_opens_at__lte=now,
            status='announced'
        )
        
        for game in games:
            game.status = 'open'
            game.save()
            
            # Отправить email всем игрокам
            send_invitations(game)

class SendReminders(CronJobBase):
    """Вторник 09:45 - напомнить неответившим"""
    schedule = Schedule(run_at_times=['09:45'])
    code = 'myapp.send_reminders'
    
    def do(self):
        # Логика напоминаний
        pass

class CloseRegistration(CronJobBase):
    """Среда 17:00 - закрыть запись"""
    schedule = Schedule(run_at_times=['17:00'])
    code = 'myapp.close_registration'
    
    def do(self):
        # Логика закрытия
        pass

class PromoteFromReserve(CronJobBase):
    """Каждые 5 минут - продвижение из резерва"""
    schedule = Schedule(run_every_mins=5)
    code = 'myapp.promote_from_reserve'
    
    def do(self):
        # Найти открытые игры
        games = Game.objects.filter(status='open')
        
        for game in games:
            promote_from_reserve(game)
```

---

## 📧 Email-уведомления

```python
# myapp/notifications.py

from django.core.mail import send_mail
from django.template.loader import render_to_string

def send_registration_approved(user):
    """Регистрация одобрена"""
    subject = 'Добро пожаловать в клуб бадминтона!'
    message = render_to_string('emails/registration_approved.html', {'user': user})
    send_mail(subject, message, 'noreply@badminton.ru', [user.email])

def send_registration_open(game, user):
    """Запись открыта"""
    subject = f'Запись на игру {game.game_date} открыта!'
    message = render_to_string('emails/registration_open.html', {'game': game, 'user': user})
    send_mail(subject, message, 'noreply@badminton.ru', [user.email])

def send_promoted_to_main(registration):
    """Переведен из резерва в основу"""
    subject = 'Вы переведены в основу!'
    message = render_to_string('emails/promoted_to_main.html', {'registration': registration})
    send_mail(subject, message, 'noreply@badminton.ru', [registration.user.email])

def send_reminder(game, user):
    """Напоминание"""
    subject = 'Напоминание: ответьте на запись'
    message = render_to_string('emails/reminder.html', {'game': game, 'user': user})
    send_mail(subject, message, 'noreply@badminton.ru', [user.email])
```

---

## 🚀 План разработки (6-8 недель)

### Неделя 1-2: Основа Django
- [x] Установка Django
- [x] Настройка PostgreSQL
- [x] Модели User, Game, Registration
- [x] Django Admin настройка
- [x] Базовые шаблоны (base.html)

### Неделя 3: Авторизация
- [x] Регистрация с комментарием
- [x] Вход/выход
- [x] Восстановление пароля
- [x] Страница "ожидание подтверждения"
- [x] Админ: утверждение регистраций

### Неделя 4: Запись на игры
- [x] Главная страница с ближайшей игрой
- [x] Кнопка "Записаться/Отменить"
- [x] Автоматическое распределение (основа/резерв)
- [x] Отображение списков
- [x] Логика продвижения из резерва

### Неделя 5: Автоматизация
- [x] Django Cron Jobs
- [x] Автоматическое открытие записи
- [x] Автоматическое закрытие
- [x] Напоминания
- [x] Email-уведомления

### Неделя 6: Комментарии и объявления
- [x] Модель Comment
- [x] Форма комментария к игре
- [x] Лента комментариев
- [x] Модель Announcement
- [x] Админ: публикация объявлений
- [x] Отображение объявлений на главной

### Неделя 7: Статистика и рейтинг
- [x] Перенос analyze_participation.py
- [x] Страница статистики
- [x] Страница рейтинга
- [x] История игр пользователя
- [x] Экспорт в Google Sheets (опционально)

### Неделя 8: Полировка и деплой
- [x] Мобильная версия (Tailwind responsive)
- [x] Тестирование всех сценариев
- [x] Деплой на Render.com
- [x] Настройка домена (опционально)

---

## 💰 Стоимость (финальная)

### Бесплатный вариант:
- **Хостинг:** Render.com (750 часов/месяц)
- **База данных:** PostgreSQL на Render (бесплатно)
- **Email:** Gmail SMTP (500/день)
- **Домен:** yoursite.render.com
- **Итого:** 0₽/месяц

### Платный вариант (рекомендуется для надёжности):
- **Хостинг:** Render.com Pro ($7/месяц)
- **База данных:** включена в Pro
- **Email:** SendGrid ($15/месяц)
- **Домен:** badminton.ru (~$10/год)
- **Итого:** ~$22/месяц (~2000₽)

---

## ✅ Преимущества Django над Flask (для вашей задачи)

| Фича | Flask | Django |
|------|-------|--------|
| Админ-панель | Нужно делать с нуля | ✅ Из коробки |
| Авторизация | Flask-Login | ✅ Встроена |
| Формы | Flask-WTF | ✅ Django Forms |
| ORM | SQLAlchemy | ✅ Django ORM |
| Права доступа | Вручную | ✅ Permissions |
| Миграции БД | Flask-Migrate | ✅ Встроены |
| Email | Flask-Mail | ✅ Встроен |
| Cron jobs | APScheduler | ✅ django-crontab |

**Итог:** Django экономит 2-3 недели разработки!

---

## 🎯 Итоговая рекомендация

**Делайте так:**

1. **Неделя 1:** Запустить Google Forms (временное решение)
2. **Недели 2-9:** Разработка Django-сайта параллельно
3. **Неделя 10:** Переход на сайт, Google Forms отключить

**Технологии:**
- ✅ Django (вместо Flask)
- ✅ PostgreSQL (вместо SQLite)
- ✅ Django Templates + Tailwind
- ✅ Render.com

Готов помочь с Django? 🚀

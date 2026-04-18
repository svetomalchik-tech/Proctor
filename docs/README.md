# Документация системы прокторинга

## Документы

| Документ | Описание |
|----------|----------|
| [📘 ARCHITECTURE.md](ARCHITECTURE.md) | Архитектура системы, диаграммы компонентов и потоков данных |
| [🔌 INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) | **Полная инструкция по интеграции** с корпоративной платформой (Java + JS/React) |
| [README.md](README.md) | Базовая документация, типы нарушений и быстрый старт |

## 🔌 Инструкция по интеграции

Документ [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md) содержит:

### Для Backend разработчиков (Java/Spring Boot)
- ✅ Пошаговая настройка подключения к прокторинг сервису
- ✅ DTO классы для всех API моделей
- ✅ ProctoringClient для вызова API
- ✅ Интеграция с ExamService
- ✅ REST контроллеры для frontend
- ✅ Обработка вебхуков
- ✅ Unit и Integration тесты

### Для Frontend разработчиков (JavaScript/React/TypeScript)
- ✅ Сервис для работы с API прокторинга
- ✅ Хук `useExamSession` для управления сессией
- ✅ Компонент `TestTakerView` с интеграцией прокторинга
- ✅ Модальные окна предупреждений
- ✅ Обработка нарушений в реальном времени
- ✅ E2E тесты с Cypress

### Для DevOps инженеров
- ✅ Production checklist
- ✅ Настройка HTTPS, CORS, rate limiting
- ✅ Мониторинг и логирование
- ✅ Масштабирование и backup
- ✅ Security hardening

### Troubleshooting
- 📷 Проблемы с камерой в разных браузерах
- 🔌 Обрыв WebSocket соединений
- ⚡ Высокая нагрузка на сервер
- 🎯 Ложные срабатывания детекции

## 🚀 Быстрый старт интеграции

```bash
# 1. Склонируйте примеры кода
cp -r integration-examples/java-spring/ your-project/src/main/java/com/corporate/learning/proctoring/

# 2. Добавьте зависимости (pom.xml)
mvn dependency:add -Dartifact=org.springframework.boot:spring-boot-starter-web
mvn dependency:add -Dartifact=org.projectlombok:lombok

# 3. Настройте подключение (application.yml)
proctoring:
  base-url: http://localhost:8000/api/v1
  api-key: your-api-key

# 4. Запустите сервис прокторинга
docker-compose -f docker/docker-compose.yml up -d

# 5. Проверьте интеграцию
curl http://localhost:8000/api/v1/health
```

## 📚 Дополнительные ресурсы

- [OpenAPI спецификация](../openapi/proctoring-api.yaml) - полная документация API
- [Admin Panel](../admin-panel/README.md) - интерфейс для проверки сессий
- [Примеры кода Java](../integration-examples/java-spring/) - готовые DTO и клиенты

## 📞 Поддержка

- Email: proctoring-support@corporate.local
- Slack: #proctoring-integration
- Documentation: https://docs.corporate.local/proctoring

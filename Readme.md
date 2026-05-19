# Discord Gemini Chatbot

Discord-бот, использующий **Google Gemini API** для общения, обработки изображений, аудио, документов и озвучивания ответов в голосовых каналах.

## Возможности

- **Общение с ИИ** — отвечает на упоминания, в ЛС и в отслеживаемых каналах/тредах
- **Поддержка вложений** — изображения, аудио, PDF, документы
- **Контекст по каналам** — у каждого канала/треда своя история
- **Slash-команды** — `/forget` (сброс истории + смена персонажа), `/createthread`
- **TTS в голосовых каналах** — синтез речи через Gemini и воспроизведение в крупнейший голосовой канал сервера
- **Персистентность** — история сохраняется между перезапусками через `shelve`
- **Логирование ошибок** — подробные логи в `errors.log`

## Требования

- Python 3.9+
- [Google Gemini API key](https://ai.google.dev/)
- [Discord Bot Token](https://discord.com/developers/applications)

## Установка

```bash
git clone https://github.com/he6ot/Discord-Gemini-Chatbot-TTS.git
cd Discord-Gemini-Chatbot-TTS
pip install -r requirements.txt
```

Создайте файл `.env` в корне проекта:

```
GOOGLE_AI_KEY=your_gemini_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token
TTS_ENABLED=true
```

Запуск:

```bash
python main.py
```

## Использование

- **@упоминание бота** в любом канале — бот ответит
- **ЛС боту** — личный диалог
- **Отслеживаемые каналы** — бот отвечает на каждое сообщение (настройте `TRACKED_CHANNELS` в `settings.py`)
- **Треды** — создайте тред через `/createthread` для выделенного диалога

### Команды

| Команда | Описание |
|---|---|
| `/forget [persona]` | Очистить историю чата в текущем канале. Можно указать новую персонализацию |
| `/createthread <name>` | Создать тред для общения с ботом (бот отвечает на все сообщения в нём) |

## Настройка

Все настройки в `settings.py`:

- **`BOT_TEMPLATE`** — кастомное начальное приветствие / системный промпт
- **`SAFETY_SETTINGS`** — фильтры контента (по умолчанию выключены)
- **`TEXT_GENERATION_CONFIG`** / **`IMAGE_GENERATION_CONFIG`** — параметры генерации (temperature, top_p, top_k)
- **`TRACKED_CHANNELS`** — ID каналов, где бот отвечает на все сообщения
- **`MAX_MESSAGE_LENGTH`** — максимальная длина одного сообщения (по умолчанию 1700)
- **`TTS_*`** — настройки TTS (модель, голос, язык)

## TTS (Text-to-Speech)

При `TTS_ENABLED=true` бот зачитывает ответы вслух в голосовом канале с наибольшим количеством участников. Используется встроенная возможность Gemini по генерации аудио.

Настройки TTS:
- `TTS_VOICE_NAME` — имя голоса (по умолчанию `Kore`)
- `TTS_LANGUAGE_CODE` — код языка (`ru-RU`)
- `TTS_MODEL` — модель Gemini для TTS (`gemini-3.1-flash-tts-preview`)
- `TTS_PROMPT` — инструкция голоса
- `TTS_MAX_LENGTH` — максимальная длина текста для синтеза (10000 символов)

## Структура проекта

```
main.py              — точка входа, инициализация бота
ai_service.py        — взаимодействие с Gemini API
message_handler.py   — обработка входящих сообщений
commands.py          — slash-команды (/forget, /createthread)
attachments.py       — загрузка и обработка вложений
tts_service.py       — синтез речи и воспроизведение в голосовых каналах
storage.py           — сохранение/загрузка истории (shelve)
settings.py          — конфигурация из переменных окружения
```

## Лицензия

GNU General Public License v3.0. См. [LICENSE](LICENSE).

# Discord Gemini Chatbot TTS

Discord-бот, использующий **Google Gemini API** (SDK `google-genai`) для общения, обработки изображений, аудио, документов и озвучивания ответов в голосовых каналах. 

Основа (без TTS): https://github.com/EnArvy/Discord-Gemini-Chatbot

99% Vibecoded

## Возможности

- **Общение с ИИ** — отвечает на упоминания, в ЛС и в отслеживаемых каналах/тредах
- **Поддержка вложений** — изображения, аудио, PDF, документы
- **Контекст по каналам** — у каждого канала/треда своя история
- **Системный промпт на канал** — задаётся через `/setprompt`, передаётся как `system_instruction`
- **Slash-команды** — `/forget`, `/setprompt`, `/getprompt`, `/clearprompt`, `/createthread`
- **TTS в голосовых каналах** — синтез речи через Gemini и воспроизведение в крупнейший голосовой канал сервера
- **Персистентность** — история и промпты сохраняются между перезапусками через `shelve`
- **Логирование ошибок** — подробные логи в `errors.log`

## Требования

- Python 3.10+
- [Google Gemini API key](https://ai.google.dev/)
- [Discord Bot Token](https://discord.com/developers/applications)
- **FFmpeg** — для воспроизведения TTS в голосовых каналах

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
SYSTEM_PROMPT=You are a helpful assistant.
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
- **Приглашение бота на сервер** — при добавлении на сервер обязательно включите scope `applications.commands`, иначе слеш-команды не будут работать

### Команды

| Команда | Описание |
|---|---|
| `/forget [persona] [system_prompt]` | Очистить историю чата. Можно сменить персонажа или системный промпт |
| `/setprompt <prompt>` | Установить системный промпт для этого канала (сохраняет историю) |
| `/getprompt` | Показать текущий системный промпт канала |
| `/clearprompt` | Убрать промпт канала (вернуться к глобальному) |
| `/createthread <name>` | Создать тред для общения с ботом (бот отвечает на все сообщения в нём) |

## Системные промпты

Каждый канал/тред может иметь свой системный промпт. Промпт передаётся через нативный `system_instruction` нового SDK, а не через историю сообщений — модель следует инструкции, а не отвечает на неё.

- **Глобальный дефолт** — задаётся в `.env` через `SYSTEM_PROMPT`
- **Канальный промпт** — устанавливается через `/setprompt`, переопределяет глобальный
- **Приоритет**: промпт канала > глобальный `SYSTEM_PROMPT` > отсутствие промпта
- Промпты сохраняются в `chatdata.dat` и восстанавливаются при перезапуске

## Настройка

Все настройки в `settings.py` и `.env`:

| Переменная | Описание | По умолчанию |
|---|---|---|
| `GOOGLE_AI_KEY` | API-ключ Gemini | — |
| `DISCORD_BOT_TOKEN` | Токен Discord-бота | — |
| `SYSTEM_PROMPT` | Глобальный системный промпт | `''` |
| `TTS_ENABLED` | Включить TTS | `false` |
| `TTS_MODEL` | Модель для TTS | `gemini-3.1-flash-tts-preview` |
| `TTS_VOICE_NAME` | Имя голоса | `Kore` |
| `TTS_LANGUAGE_CODE` | Код языка | `ru-RU` |
| `TTS_PROMPT` | Инструкция голоса | `Speak in a clear, natural voice.` |

Также в `settings.py`:
- **`BOT_TEMPLATE`** — кастомное начальное приветствие в истории (не промпт)
- **`SAFETY_SETTINGS`** — фильтры контента (по умолчанию выключены)
- **`TEXT_GENERATION_CONFIG`** / **`IMAGE_GENERATION_CONFIG`** — параметры генерации (thinking, temperature, top_p, top_k)
- **`TRACKED_CHANNELS`** — ID каналов, где бот отвечает на все сообщения
- **`MAX_MESSAGE_LENGTH`** — максимальная длина одного сообщения (по умолчанию 1700)

## TTS (Text-to-Speech)

При `TTS_ENABLED=true` бот зачитывает ответы вслух в голосовом канале с наибольшим количеством участников. Используется встроенная возможность Gemini по генерации аудио (`response_modalities: ["AUDIO"]`).

Для работы TTS требуется [FFmpeg](https://ffmpeg.org/) в системе.

## Структура проекта

```
main.py              — точка входа, инициализация бота
ai_service.py        — взаимодействие с Gemini API (google-genai SDK)
message_handler.py   — обработка входящих сообщений
commands.py          — slash-команды (/forget, /setprompt, /getprompt, /createthread)
attachments.py       — загрузка и обработка вложений
tts_service.py       — синтез речи и воспроизведение в голосовых каналах
storage.py           — сохранение/загрузка истории и промптов (shelve)
settings.py          — конфигурация из переменных окружения
```

## Лицензия

GNU General Public License v3.0. См. [LICENSE](LICENSE).

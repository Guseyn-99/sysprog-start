# Ядро агента (C)

Ядро собирается в динамическую библиотеку: `sentry_core.dll` в Windows, `libsentry_core.dylib` в macOS,
`libsentry_core.so` в Linux. Первая функция появляется на паре 2.

| Файл | Что в нём |
|---|---|
| `core.h` | Структура core_info и объявление core_get_info |
| `core_info.c` | Получение PID, числа процессоров, размера страницы и имени компьютера |
| `show_info.c` | Проверка функции ядра на C |


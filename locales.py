LOCALES: dict[str, dict] = {
    "ru": {
        "choose_language":        "🌐 Выбери язык интерфейса:",
        "language_set":           "✅ Язык изменён на <b>Русский</b>",
        "welcome":                "👋 <b>LU Schedule Bot</b>\n\nГруппа: <code>{group}</code>\n\nИспользуй кнопки внизу 👇\n\n<i>Учебный проект, без гарантий — /about</i>",
        "subscribed":             "✅ Ты подписан на уведомления!\nГруппа: <code>{group}</code>",
        "already_active":         "ℹ️ Ты уже подписан.",
        "unsubscribed":           "👋 Ты отписался от уведомлений. Напиши /start чтобы подписаться снова.",
        "not_subscribed":         "ℹ️ Ты не подписан. Напиши /start.",
        "no_classes":             "📭 Пар нет",
        "cancelled_label":        "ОТМЕНЕНО",
        "cancelled_alert_title":  "⚠️ <b>Пара ОТМЕНЕНА!</b>",
        "morning_greeting":       "🌅 <b>Доброе утро!</b>",
        "reminder_title":         "⏰ <b>Напоминание!</b> Через {minutes} мин:",
        "online_label":           "Онлайн",
        "error":                  "⚠️ Не удалось загрузить расписание. Попробуй позже.",
        "help":                   "👋 <b>LU Schedule Bot</b>\n\nГруппа: <code>{group}</code>\n\nИспользуй кнопки внизу 👇\n\n<i>Учебный проект, без гарантий — /about</i>",
        "btn_today":              "📅 Сегодня",
        "btn_tomorrow":           "📅 Завтра",
        "btn_week":               "📆 Эта неделя",
        "btn_nextweek":           "📆 След. неделя",
        "btn_back":               "◀️ Назад",
        "btn_menu":               "📋 Меню",
        "break":                  "⏸ {minutes} мин",
        "no_lessons_week":        "📭 На этой неделе пар нет",
        "btn_about":               "ℹ️ О боте",
        "about": (
            "ℹ️ <b>О боте</b>\n\n"
            "Автор: <b>Sergejs Krasikovs</b>\n\n"
            "Бот сделан как учебный проект — в научно-развлекательных целях.\n\n"
            "Данные берутся с сайта lekciju-saraksts.lu.lv и могут расходиться с "
            "реальностью: расписание меняют, сайт иногда врёт, бот иногда спит. "
            "Автор <b>не даёт 100% гарантии</b> точности и не несёт ответственности "
            "за пропущенные пары.\n\n"
            "Что-то важное — перепроверяй на официальном сайте 🙂"
        ),
        "commands": {
            "start":    "Меню и подписка на уведомления",
            "me":       "Указать свои подгруппы",
            "group":    "Выбрать свою группу",
            "language": "Сменить язык интерфейса",
            "about":    "Об авторе и дисклеймер",
            "stop":     "Отписаться от уведомлений",
        },
        "btn_group":               "🎓 Моя группа",
        "group_prompt":            "🎓 <b>Выбор группы</b>\n\nСейчас: <code>{group}</code>\n\nНапиши номер программы или её название — например <code>22302</code> или <code>Datorzinātnes</code>.",
        "group_none":              "🤷 По запросу «{query}» ничего не нашлось. Попробуй короче — например только номер программы.",
        "group_set":               "✅ Группа: <code>{group}</code>",
        "hint":                    "🤔 Я понимаю только кнопки и команды. Жми /start.",
        "btn_me":                  "👤 Мои подгруппы",
        "btn_me_off":              "🔓 Показывать все пары потока",
        "me_prompt":               "👤 <b>Твои подгруппы</b>\n\nСейчас: {who}\n\nНапиши свою фамилию из списка потока — например <code>Krasikovs</code>.\n\nПосле выбора бот покажет только твоё: общие лекции плюс твои маленькие группы (4, 4a, 12, E и прочие).",
        "me_none":                 "🤷 В списках потока никого похожего на «{query}» нет. Проверь написание — фамилии там латиницей.",
        "me_off":                  "не выбраны — показываю все пары потока",
        "me_gap":                   "⚠️ <i>По распределению у тебя тут есть пара, но на сайте её нет:</i>",
        "days": {
            "Pr": "Понедельник", "Ot": "Вторник", "Tr": "Среда",
            "Ce": "Четверг",     "Pk": "Пятница",  "Se": "Суббота",
            "Sv": "Воскресенье",
        },
    },
    "en": {
        "choose_language":        "🌐 Choose interface language:",
        "language_set":           "✅ Language changed to <b>English</b>",
        "welcome":                "👋 <b>LU Schedule Bot</b>\n\nGroup: <code>{group}</code>\n\nUse the buttons below 👇\n\n<i>A study project, no guarantees — /about</i>",
        "subscribed":             "✅ You are subscribed to notifications!\nGroup: <code>{group}</code>",
        "already_active":         "ℹ️ You are already subscribed.",
        "unsubscribed":           "👋 You unsubscribed. Send /start to subscribe again.",
        "not_subscribed":         "ℹ️ You are not subscribed. Send /start.",
        "no_classes":             "📭 No classes",
        "cancelled_label":        "CANCELLED",
        "cancelled_alert_title":  "⚠️ <b>Class CANCELLED!</b>",
        "morning_greeting":       "🌅 <b>Good morning!</b>",
        "reminder_title":         "⏰ <b>Reminder!</b> In {minutes} min:",
        "online_label":           "Online",
        "error":                  "⚠️ Could not load schedule. Try again later.",
        "help":                   "👋 <b>LU Schedule Bot</b>\n\nGroup: <code>{group}</code>\n\nUse the buttons below 👇\n\n<i>A study project, no guarantees — /about</i>",
        "btn_today":              "📅 Today",
        "btn_tomorrow":           "📅 Tomorrow",
        "btn_week":               "📆 This week",
        "btn_nextweek":           "📆 Next week",
        "btn_back":               "◀️ Back",
        "btn_menu":               "📋 Menu",
        "break":                  "⏸ {minutes} min",
        "no_lessons_week":        "📭 No classes this week",
        "btn_about":               "ℹ️ About",
        "about": (
            "ℹ️ <b>About this bot</b>\n\n"
            "Author: <b>Sergejs Krasikovs</b>\n\n"
            "A study project, built for educational and recreational purposes.\n\n"
            "Data comes from lekciju-saraksts.lu.lv and may not match reality: "
            "schedules get changed, the site occasionally lies, the bot occasionally "
            "sleeps. The author gives <b>no 100% guarantee</b> of accuracy and takes "
            "no responsibility for missed classes.\n\n"
            "Double-check anything important on the official site 🙂"
        ),
        "commands": {
            "start":    "Menu and notification subscription",
            "me":       "Set your subgroups",
            "group":    "Choose your group",
            "language": "Change interface language",
            "about":    "Author and disclaimer",
            "stop":     "Unsubscribe from notifications",
        },
        "btn_group":               "🎓 My group",
        "group_prompt":            "🎓 <b>Pick a group</b>\n\nCurrently: <code>{group}</code>\n\nSend the programme number or its name — for example <code>22302</code> or <code>Datorzinātnes</code>.",
        "group_none":              "🤷 Nothing matched “{query}”. Try something shorter — the programme number alone usually works.",
        "group_set":               "✅ Group: <code>{group}</code>",
        "hint":                    "🤔 I only understand buttons and commands. Send /start.",
        "btn_me":                  "👤 My subgroups",
        "btn_me_off":              "🔓 Show the whole year",
        "me_prompt":               "👤 <b>Your subgroups</b>\n\nCurrently: {who}\n\nSend your surname as it appears in the year list — for example <code>Krasikovs</code>.\n\nAfter that the bot shows only your own: shared lectures plus your small groups (4, 4a, 12, E and the rest).",
        "me_none":                 "🤷 Nobody in the year list looks like “{query}”. Check the spelling — the names are in Latvian.",
        "me_off":                  "not set — showing every class of the year",
        "me_gap":                   "⚠️ <i>The distribution list gives you a class here that the website does not show:</i>",
        "days": {
            "Pr": "Monday",   "Ot": "Tuesday",   "Tr": "Wednesday",
            "Ce": "Thursday", "Pk": "Friday",     "Se": "Saturday",
            "Sv": "Sunday",
        },
    },
    "lv": {
        "choose_language":        "🌐 Izvēlies saskarnes valodu:",
        "language_set":           "✅ Valoda nomainīta uz <b>Latviešu</b>",
        "welcome":                "👋 <b>LU Schedule Bot</b>\n\nGrupa: <code>{group}</code>\n\nIzmanto pogas zemāk 👇\n\n<i>Mācību projekts, bez garantijām — /about</i>",
        "subscribed":             "✅ Tu esi pieteicies paziņojumiem!\nGrupa: <code>{group}</code>",
        "already_active":         "ℹ️ Tu jau esi pieteicies.",
        "unsubscribed":           "👋 Tu atteicies no paziņojumiem. Raksti /start, lai pieteiktos vēlreiz.",
        "not_subscribed":         "ℹ️ Tu neesi pieteicies. Raksti /start.",
        "no_classes":             "📭 Nav nodarbību",
        "cancelled_label":        "ATCELTS",
        "cancelled_alert_title":  "⚠️ <b>Nodarbība ATCELTS!</b>",
        "morning_greeting":       "🌅 <b>Labrīt!</b>",
        "reminder_title":         "⏰ <b>Atgādinājums!</b> Pēc {minutes} min:",
        "online_label":           "Tiešsaistē",
        "error":                  "⚠️ Neizdevās ielādēt sarakstu. Mēģini vēlāk.",
        "help":                   "👋 <b>LU Schedule Bot</b>\n\nGrupa: <code>{group}</code>\n\nIzmanto pogas zemāk 👇\n\n<i>Mācību projekts, bez garantijām — /about</i>",
        "btn_today":              "📅 Šodien",
        "btn_tomorrow":           "📅 Rīt",
        "btn_week":               "📆 Šī nedēļa",
        "btn_nextweek":           "📆 Nākamā nedēļa",
        "btn_back":               "◀️ Atpakaļ",
        "btn_menu":               "📋 Izvēlne",
        "break":                  "⏸ {minutes} min",
        "no_lessons_week":        "📭 Šonedēļ nav nodarbību",
        "btn_about":               "ℹ️ Par botu",
        "about": (
            "ℹ️ <b>Par šo botu</b>\n\n"
            "Autors: <b>Sergejs Krasikovs</b>\n\n"
            "Bots ir mācību projekts, veidots izglītojošos un izklaides nolūkos.\n\n"
            "Dati tiek ņemti no lekciju-saraksts.lu.lv un var neatbilst īstenībai: "
            "saraksts mainās, vietne reizēm melo, bots reizēm guļ. Autors "
            "<b>negarantē 100% precizitāti</b> un neuzņemas atbildību par nokavētām "
            "nodarbībām.\n\n"
            "Ko svarīgu — pārbaudi oficiālajā vietnē 🙂"
        ),
        "commands": {
            "start":    "Izvēlne un paziņojumu abonēšana",
            "me":       "Norādīt savas apakšgrupas",
            "group":    "Izvēlēties savu grupu",
            "language": "Mainīt saskarnes valodu",
            "about":    "Par autoru un atruna",
            "stop":     "Atteikties no paziņojumiem",
        },
        "btn_group":               "🎓 Mana grupa",
        "group_prompt":            "🎓 <b>Grupas izvēle</b>\n\nPašlaik: <code>{group}</code>\n\nRaksti programmas numuru vai nosaukumu — piemēram <code>22302</code> vai <code>Datorzinātnes</code>.",
        "group_none":              "🤷 Pēc “{query}” nekas netika atrasts. Mēģini īsāk — piemēram, tikai programmas numuru.",
        "group_set":               "✅ Grupa: <code>{group}</code>",
        "hint":                    "🤔 Es saprotu tikai pogas un komandas. Raksti /start.",
        "btn_me":                  "👤 Manas apakšgrupas",
        "btn_me_off":              "🔓 Rādīt visa kursa nodarbības",
        "me_prompt":               "👤 <b>Tavas apakšgrupas</b>\n\nPašlaik: {who}\n\nRaksti savu uzvārdu, kā tas ir kursa sarakstā — piemēram <code>Krasikovs</code>.\n\nPēc tam bots rādīs tikai tavu: kopīgās lekcijas un tavas mazās grupas (4, 4a, 12, E un citas).",
        "me_none":                 "🤷 Kursa sarakstā nav neviena, kas līdzinātos “{query}”. Pārbaudi rakstību.",
        "me_off":                  "nav izvēlētas — rādu visa kursa nodarbības",
        "me_gap":                   "⚠️ <i>Sadalījumā tev šeit ir nodarbība, bet vietnē tās nav:</i>",
        "days": {
            "Pr": "Pirmdiena",  "Ot": "Otrdiena",  "Tr": "Trešdiena",
            "Ce": "Ceturtdiena","Pk": "Piektdiena", "Se": "Sestdiena",
            "Sv": "Svētdiena",
        },
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    loc = LOCALES.get(lang, LOCALES["ru"])
    text = loc.get(key, LOCALES["ru"].get(key, key))
    return text.format(**kwargs) if kwargs else text

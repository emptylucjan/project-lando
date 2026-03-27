import pathlib

# Fix mrowka_data.py
p = pathlib.Path("mrowka/mrowka_data.py")
txt = p.read_text(encoding="utf-8")

# Fix broken line from PowerShell patch
txt = txt.replace(
    "import logger as logger`r`nfrom discord.ext import commands",
    "import logger as logger\nfrom discord.ext import commands",
)
# Fix reference to CHANNEL_IMPORTY_DO_SUBIEKTA (doesn't exist in our dc.py)
txt = txt.replace(
    'await dc.CHANNEL_IMPORTY_DO_SUBIEKTA(bot)',
    'await dc.channel_from_name(bot, "importy-do-subiekta")',
)
# Fix reference to USERS_DAILY_MESSAGES
txt = txt.replace(
    'dc.USERS_DAILY_MESSAGES(bot)',
    'dc.get_daily_message_users(bot)',
)
# Remove interia_pass from daily CSV (we don't have it anymore)
txt = txt.replace(
    '            "HASŁO INTERIA",\n',
    '',
)
txt = txt.replace(
    '                    order_item.mail.interia_pass\n                        if order_item.mail and order_item.mail.interia_pass\n                        else ""\n                    ),\n',
    '                    "",\n',
)
p.write_text(txt, encoding="utf-8")
print("Fixed mrowka_data.py")

# Fix mrowka_lib.py
p2 = pathlib.Path("mrowka/mrowka_lib.py")
txt2 = p2.read_text(encoding="utf-8")

txt2 = txt2.replace("import interia\r\n", "import gmail_imap\n")
txt2 = txt2.replace("import interia\n", "import gmail_imap\n")
txt2 = txt2.replace("import eans.ean\r\n", "# import eans.ean\n")
txt2 = txt2.replace("import eans.ean\n", "# import eans.ean\n")
txt2 = txt2.replace("# import interia  # zastapione przez gmail_imap`r`n", "import gmail_imap\n")
txt2 = txt2.replace("# import eans.ean  # TODO: EAN scan`r`n", "# import eans.ean\n")
# Replace interia calls with gmail_imap
txt2 = txt2.replace(
    "interia.get_info_from_interia",
    "gmail_imap.get_delivery_info_for_mail",
)
# Fix eans call
txt2 = txt2.replace(
    "await eans.ean.send_eans(bot, ticket_name)",
    "pass  # EAN scan: TODO",
)
p2.write_text(txt2, encoding="utf-8")
print("Fixed mrowka_lib.py")

# Fix mrowka_bot.py  
p3 = pathlib.Path("mrowka/mrowka_bot.py")
txt3 = p3.read_text(encoding="utf-8")
txt3 = txt3.replace("import eans.ean\r\n", "# import eans.ean\n")
txt3 = txt3.replace("import eans.ean\n", "# import eans.ean\n")
txt3 = txt3.replace(
    "import mrowka_lib\nimport logger",
    "import mrowka_lib\nimport logger as logger",
)
txt3 = txt3.replace("import interia\r\n", "")
txt3 = txt3.replace("import interia\n", "")
p3.write_text(txt3, encoding="utf-8")
print("Fixed mrowka_bot.py")
print("ALL DONE")

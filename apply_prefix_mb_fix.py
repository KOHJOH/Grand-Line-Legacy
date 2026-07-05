from pathlib import Path

path = Path("cogs/prefix.py")

if not path.exists():
    raise SystemExit("Could not find cogs/prefix.py. Run this from the repo root.")

text = path.read_text(encoding="utf-8")

old = '''        if not handler:
            await message.reply(f"Unknown command: `{PREFIX}{command}`. Use `-help`.", mention_author=False)
            return
'''

new = '''        if not handler:
            # If this is a real discord.py command/group from another cog
            # such as -mb, let that cog handle it and do NOT send
            # PrefixCog's unknown-command message.
            if self.bot.get_command(command) is not None:
                return

            await message.reply(f"Unknown command: `{PREFIX}{command}`. Use `-help`.", mention_author=False)
            return
'''

if old in text:
    text = text.replace(old, new)
else:
    old_compact = 'if not handler: await message.reply(f"Unknown command: `{PREFIX}{command}`. Use `-help`.", mention_author=False) return'
    new_compact = '''if not handler:
            if self.bot.get_command(command) is not None:
                return
            await message.reply(f"Unknown command: `{PREFIX}{command}`. Use `-help`.", mention_author=False)
            return'''
    if old_compact not in text:
        raise SystemExit("Could not find the unknown-command block. Upload cogs/prefix.py and patch manually.")
    text = text.replace(old_compact, new_compact)

path.write_text(text, encoding="utf-8")
print("Patched cogs/prefix.py successfully.")

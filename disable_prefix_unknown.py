from pathlib import Path

path = Path("cogs/prefix.py")
if not path.exists():
    raise SystemExit("Could not find cogs/prefix.py. Run this from repo root.")

text = path.read_text(encoding="utf-8")
lines = text.splitlines()
new_lines = []

for line in lines:
    # Kill PrefixCog's custom unknown-command replies.
    # discord.py should handle real commands/groups like -mb by itself.
    if "Unknown command:" in line and ("send(" in line or "reply(" in line):
        indent = line[: len(line) - len(line.lstrip())]
        new_lines.append(indent + "return")
        new_lines.append(indent + "# Disabled duplicate unknown-command reply:")
        new_lines.append(indent + "# " + line.strip())
    else:
        new_lines.append(line)

new_text = "\n".join(new_lines) + "\n"
path.write_text(new_text, encoding="utf-8")
print("Disabled duplicate Unknown command replies in cogs/prefix.py")

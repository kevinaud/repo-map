import base64
import os
import shutil
import subprocess
import sys


def copy_to_clipboard(text: str) -> bool:
  """
  Copies text to clipboard, supporting WSL, OSC 52 (VS Code), and Linux X11/Wayland.
  Returns True if successful.
  """
  data = text.encode("utf-8")

  # 1. WSL Check
  if shutil.which("clip.exe"):
    try:
      subprocess.run(["clip.exe"], input=data, check=True)
      return True
    except subprocess.CalledProcessError:
      pass

  # 2. OSC 52 (VS Code / Remote Containers)
  # Checks specific env vars usually present in these environments
  if os.environ.get("REMOTE_CONTAINERS") or os.environ.get("TERM_PROGRAM") == "vscode":
    try:
      # \033]52;c;{base64}\a
      encoded = base64.b64encode(data).decode("utf-8")
      # Write directly to stdout (tty) ensuring it's not buffered
      sys.stdout.write(f"\033]52;c;{encoded}\a")
      sys.stdout.flush()
      return True
    except Exception:
      pass

  # 3. X11 (xclip)
  if shutil.which("xclip"):
    try:
      subprocess.run(["xclip", "-selection", "clipboard"], input=data, check=True)
      return True
    except subprocess.CalledProcessError:
      pass

  # 4. Wayland (wl-copy)
  if shutil.which("wl-copy"):
    try:
      subprocess.run(["wl-copy"], input=data, check=True)
      return True
    except subprocess.CalledProcessError:
      pass

  return False

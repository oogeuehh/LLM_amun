# -*- coding: utf-8 -*-
import requests
import json
import sys
import os
import re
import codecs

if sys.version_info[0] < 3:
    reload(sys)
    if hasattr(sys, 'setdefaultencoding'):
        sys.setdefaultencoding('utf-8')

### DF: Import LLM API
API_KEY = "sk-i2GQTkZ4h1XuFaYtPmMEAziCNZNY0zfcNCTQwwhDVy7lSJdp"
BASE_URL = "https://api.chatanywhere.tech"
MODEL = "gpt-4o-mini"

# -----------------------------
# Helpers
# -----------------------------
def _normalize_command(s):
    """Trim + collapse inner spaces for stable cache keys."""
    return u" ".join((s or u"").strip().split())

_INVALID_PATTERNS = [
    r"\bbash:\s*.*command not found\b",
    r"\bcommand not found\b",
    r"\bnot recognized as an internal or external command\b",
    r"\bno such file or directory\b",
    r"\bunknown command\b",
    r"\binvalid command\b",
]
_INVALID_RE = re.compile("|".join(_INVALID_PATTERNS), re.IGNORECASE)

def _looks_like_invalid(output):
    if not output:
        return True
    return bool(_INVALID_RE.search(output))

# -----------------------------
# VALID COMMANDS
# -----------------------------
VALID_COMMANDS = set()
valid_file = os.path.join(os.path.dirname(__file__), "valid_commands.txt")
if os.path.exists(valid_file):
    with codecs.open(valid_file, "r", "utf-8") as f:
        for line in f:
            cmd = line.strip()
            if cmd:
                VALID_COMMANDS.add(cmd)
                

### DF: Clean output
def _sanitize_output(output):
    if not output:
        return ""

    output = re.sub(r"^(```+|'''+)", "", output.strip())
    output = re.sub(r"(```+|'''+)$", "", output.strip())

    output = re.sub(r"^bash:\s*", "", output)
    output = re.sub(r"^bash\n", "", output)
    
    output = re.sub(r"^plaintext:\s*", "", output)
    output = re.sub(r"^plaintext\n", "", output)

    return output.strip()
    
    
def query_llm(command):
    norm_cmd_line = _normalize_command(command)
    cmd = (norm_cmd_line.split()[0] if norm_cmd_line else u"")

    url = BASE_URL + "/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY
    }

    system_prompt = (
        "You are a shell with system information Linux can201-VirtualBox "
        "5.15.0-139-generic #149~20.04.1-Ubuntu with distribution Debian GNU/Linux 8.11 (jessie). "
        "Simulate a bash shell faithfully. Output only what a real shell would print; "
        "do not include extra explanations or quotation marks."
    )

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": norm_cmd_line}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            resp_json = response.json()
            output = resp_json["choices"][0]["message"]["content"].strip()
            output = _sanitize_output(output)

            # new commands --> valid --> add into VALID_COMMANDS
            if cmd and (cmd not in VALID_COMMANDS) and not _looks_like_invalid(output):
                VALID_COMMANDS.add(cmd)
                try:
                    with codecs.open(valid_file, "a", "utf-8") as f:
                        f.write(cmd + "\n")
                except Exception as e:
                    print("Failed to update valid_commands.txt: %s" % e)

            return output
        else:
            return "API error: {0} - {1}".format(response.status_code, response.text)
    except Exception as e:
        return "any errors occurred: " + str(e)

# -----------------------------
# LLM Context Manager with persistent cache + dynamic command collection
# -----------------------------
class LLMContextManager(object):
    def __init__(self, model, api_key, base_url, max_history=20):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_history = max_history
        self.history = [
            {"role": "system", "content": (
                "You are a bash shell running on Linux can201-VirtualBox "
                "5.15.0-139-generic #149~20.04.1-Ubuntu SMP Wed Apr 16 08:29:56 UTC 2025 x86_64 GNU/Linux. "
                "Simulate bash faithfully. Output only what a real shell would print."
            )}
        ]

        # Persistent cache
        self.cache_file = os.path.join(os.path.dirname(__file__), "llm_response_cache.json")
        self.cmd_cache = {}
        if os.path.exists(self.cache_file):
            try:
                with codecs.open(self.cache_file, "r", "utf-8") as f:
                    self.cmd_cache = json.load(f)
            except Exception as e:
                print("Failed to load cache file: %s" % e)

    def ask(self, command, stream=False):
        norm_cmd_line = _normalize_command(command)
        if not norm_cmd_line:
            return "" 

        cmd = norm_cmd_line.split()[0]

        # 1) collected command in catch
        if (cmd in VALID_COMMANDS) or (norm_cmd_line in self.cmd_cache):
            # look for catch
            if norm_cmd_line in self.cmd_cache:
                return self.cmd_cache[norm_cmd_line]
            # not in catch --> save
            return self._call_llm_and_cache(norm_cmd_line, dynamic_collect=False)

        # 2) new command --> collect according to LLM response
        return self._call_llm_and_cache(norm_cmd_line, dynamic_collect=True)

    def _call_llm_and_cache(self, norm_cmd_line, dynamic_collect=False):
        url = self.base_url + "/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key
        }
        data = {
            "model": self.model,
            "messages": self.history + [{"role": "user", "content": norm_cmd_line}],
            "stream": False
        }

        try:
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code == 200:
                output = resp.json()["choices"][0]["message"]["content"].strip()
                output = _sanitize_output(output)

                # update history
                self.history.append({"role": "user", "content": norm_cmd_line})
                self.history.append({"role": "assistant", "content": output})
                self._trim_history()

                cmd_key = norm_cmd_line.split()[0]

                if dynamic_collect:
                    # unknown command --> leagal --> save in catch & VALID_COMMANDS
                    if cmd_key and not _looks_like_invalid(output):
                        if cmd_key not in VALID_COMMANDS:
                            VALID_COMMANDS.add(cmd_key)
                            try:
                                with codecs.open(valid_file, "a", "utf-8") as f:
                                    f.write(cmd_key + "\n")
                            except Exception as e:
                                print("Failed to update valid_commands.txt: %s" % e)
                        self.cmd_cache[norm_cmd_line] = output
                        self._save_cache()
                else:
                    # known command --> invoke catch
                    self.cmd_cache[norm_cmd_line] = output
                    self._save_cache()

                return output
            else:
                return "API error: {0} - {1}".format(resp.status_code, resp.text)
        except Exception as e:
            return "any errors occurred: " + str(e)

    def _save_cache(self):
        try:
            with codecs.open(self.cache_file, "w", "utf-8") as f:
                json.dump(self.cmd_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Failed to save cache file: %s" % e)

    def _trim_history(self):
        if len(self.history) > self.max_history * 2:
            self.history = self.history[0:1] + self.history[-self.max_history*2:]

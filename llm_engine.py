# -*- coding: utf-8 -*-
import requests
import json
import sys
import os
import codecs

if sys.version_info[0] < 3:
    reload(sys)
    if hasattr(sys, 'setdefaultencoding'):
        sys.setdefaultencoding('utf-8')

### DF: Import LLM API
API_KEY = "sk-i2GQTkZ4h1XuFaYtPmMEAziCNZNY0zfcNCTQwwhDVy7lSJdp"
BASE_URL = "https://api.chatanywhere.tech"
MODEL = "gpt-4o-mini"


VALID_COMMANDS = set()
valid_file = os.path.join(os.path.dirname(__file__), "valid_commands.txt")
with codecs.open(valid_file, "r", "utf-8") as f:
    for line in f:
        cmd = line.strip() 
        if cmd:
            VALID_COMMANDS.add(cmd)


#print([repr(c) for c in VALID_COMMANDS])

def query_llm(command):

    cmd = command.strip().split()[0] 
    #print("Checking command:", repr(cmd))
    
    if cmd not in VALID_COMMANDS:
        return "invalid: command not found"

    url = BASE_URL + "/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY
    }

    system_prompt = (
        "You are a shell with system information Linux can201-VirtualBox "
        "5.15.0-139-generic #149~20.04.1-Ubuntu with distribution Debian GNU/Linux 8.11 (jessie), "
        "now that you need to simulate a bash shell, your output should look as if you executed this command, "
        "and you should not output any other text that is not part of the response of this command. "
        "You should not reply with command not found."
    )

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            resp_json = response.json()
            return resp_json["choices"][0]["message"]["content"].strip()
        else:
            return "API error: {0} - {1}".format(response.status_code, response.text)
    except Exception as e:
        return "any errors occurred: " + str(e)
        
        
### DF: LLM responses cache manager
class LLMContextManager(object):
    def __init__(self, model, api_key, base_url, max_history=20):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_history = max_history
        self.history = [
            {"role": "system", "content": (
                "You are a bash shell running on Linux can201-VirtualBox 5.15.0-139-generic #149~20.04.1-Ubuntu SMP Wed Apr 16 08:29:56 UTC 2025 x86_64 GNU/Linux. Simulate bash faithfully. Output only what a real shell would print. "
            )}
        ]
        self.cmd_cache = {}
        self.cache_cmds = set(["ls", "pwd", "whoami", "uname -a"])

    def ask(self, command, stream=False):
        # 1. check cache
        if command in self.cmd_cache:
            return self.cmd_cache[command]

        # 2. append user message
        self.history.append({"role": "user", "content": command})
        self._trim_history()

        # 3. request
        url = self.base_url + "/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key
        }
        data = {
            "model": self.model,
            "messages": self.history,
            "stream": stream
        }

        return self._call_api(url, headers, data, command)

    def _trim_history(self):
        if len(self.history) > self.max_history * 2:  # user+assistant
            self.history = self.history[0:1] + self.history[-self.max_history*2:]

    def _call_api(self, url, headers, data, command):
        try:
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code == 200:
                msg = resp.json()["choices"][0]["message"]["content"].strip()
                # add to history
                self.history.append({"role": "assistant", "content": msg})
                if command in self.cache_cmds:
                    self.cmd_cache[command] = msg
                return msg
            else:
                return "API error: {0} - {1}".format(resp.status_code, resp.text)
        except Exception as e:
            return "any errors occure: " + str(e)


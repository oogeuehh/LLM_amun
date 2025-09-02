import csv
import time
import os
from datetime import datetime

class ExperimentLogger:
    def __init__(self, filename="logs/experiment.log"):
        self.filename = filename
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "connection_id", "step",
                    "src", "dst", "Pr_Actual", "Pr_Max",
                    "payoff", "block", "commands_raw"
                ])
        self.step_counter = {}

    def log_transition(self, connection_id, src, dst, Pr_Actual, Pr_Max, payoff, block, commands_raw=None):
        if connection_id not in self.step_counter:
            self.step_counter[connection_id] = 1
        else:
            self.step_counter[connection_id] += 1

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        step = self.step_counter[connection_id]

        with open(self.filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, connection_id, step,
                src, dst, Pr_Actual, Pr_Max,
                payoff, block, commands_raw
            ])

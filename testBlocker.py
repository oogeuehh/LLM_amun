# -*- coding: utf-8 -*-
import pandas as pd
from core.blocker import Blocker
from core.input_manager import split_commands

def run_test(commands):
    print("\n===== START TEST =====")
    blocker = Blocker(
        counts_file="core/transition_counts_matrix.csv",
        probs_file="core/transition_probabilities_matrix.csv"
    )

    for cmd in commands:
        parsed = split_commands(cmd)
        print(f"\n[INPUT] raw: {cmd}")
        print(f"[INPUT] parsed: {parsed}")

        for p in parsed:
            src = blocker.matrix.last_command
            decision = blocker.check_and_update(p)

            print(f"[TRANSITION] src={src}, dst={p}, "
                f"Pr_Actual={decision['Pr_Actual']}, Pr_Max={decision['Pr_Max']}, "
                f"payoff={decision['payoff']:.3f}, block={decision['block']}")

    print("\n===== END TEST =====")
    print("\n[FINAL COUNTS MATRIX]:")
    print(blocker.matrix.counts_df)

    print("\n[FINAL PROBS MATRIX]:")
    print(blocker.matrix.probs_df)


if __name__ == "__main__":
    test_commands = [
        # "ls",
        # "pwd"
        "uname -a",
        "ifconfig"
        # "ls; pwd",
        # "uname -a && ifconfig",
        # "exit"
    ]

    run_test(test_commands)

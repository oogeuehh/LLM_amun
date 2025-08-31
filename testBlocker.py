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
            dst = p

            decision = blocker.check_and_update(p)

            Pr_Actual = None
            Pr_Max = None
            if src and src in blocker.matrix.probs_df.index and dst in blocker.matrix.probs_df.columns:
                Pr_Actual = blocker.matrix.probs_df.loc[src, dst]
                Pr_Max = blocker.matrix.find_optimal_pr(src, dst)

            print(f"[TRANSITION] src={src}, dst={dst}, "
                  f"Pr_Actual={Pr_Actual}, Pr_Max={Pr_Max}, "
                  f"payoff={decision['payoff']:.3f}, block={decision['block']}")

    print("\n===== END TEST =====")
    print("\n[FINAL COUNTS MATRIX]:")
    print(blocker.matrix.counts_df)

    print("\n[FINAL PROBS MATRIX]:")
    print(blocker.matrix.probs_df)


if __name__ == "__main__":
    test_commands = [
        "ls",
        "pwd"
        # "uname -a",
        # "ifconfig"
        # "ls; pwd",
        # "uname -a && ifconfig",
        # "exit"
    ]

    run_test(test_commands)

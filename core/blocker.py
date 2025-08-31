### DF: blocker.py
from core.matrix_manager import Matrix

class Blocker:
    def __init__(self, counts_file="transition_counts_matrix.csv", probs_file="transition_probabilities_matrix.csv"):
        self.matrix = Matrix(counts_file, probs_file)

    def check_and_update(self, current_command):
        result = {"block": False, "payoff": 0.0, "Pr_Actual": None, "Pr_Max": None}
        dst = current_command

        if self.matrix.last_command is None:
            self.matrix.last_command = dst
            return result

        src = self.matrix.last_command
        self.matrix.last_command = dst

        if src in self.matrix.probs_df.index and dst in self.matrix.probs_df.columns:
            Pr_Actual = float(self.matrix.probs_df.loc[src, dst])
            Pr_Max = float(self.matrix.find_optimal_pr(src, dst, self.matrix.probs_df))
            payoff = Pr_Actual / Pr_Max if Pr_Max > 0 else 0.0

            result.update({
                "Pr_Actual": Pr_Actual,
                "Pr_Max": Pr_Max,
                "payoff": payoff,
                "block": payoff > 0.5
            })

        # Update counts/probs
        self.matrix.update_matrix(src, dst)

        return result

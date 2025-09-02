# core/matrix_manager.py
# -*- coding: utf-8 -*-
import pandas as pd
import csv
import os

class Matrix:
    def __init__(self,
                 counts_file="core/transition_counts_matrix.csv",
                 probs_file="core/transition_probabilities_matrix.csv",
                 initial_states=None,
                 epsilon: float = 4.48e-8):
        self.counts_file = counts_file
        self.probs_file = probs_file
        self.epsilon = epsilon

        columns_order = []
        if os.path.exists(counts_file):
            try:
                with open(counts_file, "r", encoding="utf-8-sig") as f:
                    reader = csv.reader(f)
                    header = next(reader) 
                    if len(header) > 1:
                        columns_order = header[1:]
            except Exception:
                columns_order = []


        self.counts_df = self._load_counts(counts_file)

        # header order
        if list(self.counts_df.index):
            state_order = list(self.counts_df.index)
        elif columns_order:
            state_order = list(columns_order)
        else:
            state_order = []

        if initial_states:
            for s in initial_states:
                if s not in state_order:
                    state_order.append(s)
        self.state_order = state_order

        # read & calculate probs_df
        if os.path.exists(probs_file):
            self.probs_df = pd.read_csv(probs_file, index_col=0)
        else:
            self.probs_df = self.counts_to_probs_with_smoothing(self.counts_df, self.epsilon)

        if self.state_order:
            self.counts_df = self.counts_df.reindex(index=self.state_order, columns=self.state_order, fill_value=0).astype("int64")
            self.probs_df  = self.probs_df.reindex(index=self.state_order, columns=self.state_order, fill_value=0.0).astype("float64")
        else:
            # no init
            self.counts_df = self.counts_df.astype("int64") if not self.counts_df.empty else pd.DataFrame(dtype="int64")
            self.probs_df = self.probs_df.astype("float64") if not self.probs_df.empty else pd.DataFrame(dtype="float64")

        self.last_command = None

    def _load_counts(self, path):
        try:
            df = pd.read_csv(path, index_col=0)
            states = list(df.index)
            return df.reindex(index=states, columns=states, fill_value=0).astype("int64")
        except FileNotFoundError:
            return pd.DataFrame(dtype="int64")

    def save_matrix(self):
        if self.state_order:
            counts = self.counts_df.reindex(index=self.state_order, columns=self.state_order, fill_value=0)
            probs = self.probs_df.reindex(index=self.state_order, columns=self.state_order, fill_value=0.0)
        else:
            counts = self.counts_df
            probs = self.probs_df

        counts.to_csv(self.counts_file, index=True, encoding="utf-8-sig")
        probs.to_csv(self.probs_file, index=True, encoding="utf-8-sig")

    def counts_to_probs_with_smoothing(self, counts_df, epsilon=None):
        if epsilon is None:
            epsilon = self.epsilon

        if self.state_order:
            counts_df = counts_df.reindex(index=self.state_order, columns=self.state_order, fill_value=0)
        else:
            counts_df = counts_df.copy()

        if counts_df.empty:
            return pd.DataFrame(dtype="float64")

        N = counts_df.shape[1]
        if N == 0:
            return pd.DataFrame(dtype="float64")

        probs = counts_df.astype("float64").copy()

        for s in probs.index:
            row_counts = counts_df.loc[s]
            total = row_counts.sum()

            if total == 0:
                probs.loc[s] = 1.0 / N
                continue

            p = row_counts / total
            n = int((p > 0).sum())

            if n < N:
                p_sm = p.copy()
                nonzero_mask = (p > 0)
                zero_mask = ~nonzero_mask
                p_sm[nonzero_mask] = p_sm[nonzero_mask] * (1.0 - epsilon)
                if (N - n) > 0:
                    p_sm[zero_mask] = epsilon / (N - n)
                probs.loc[s] = p_sm
            else:
                probs.loc[s] = p

        if self.state_order:
            return probs.reindex(index=self.state_order, columns=self.state_order, fill_value=0.0).astype("float64")
        else:
            return probs.astype("float64")

    def update_matrix(self, src, dst):
        # new src/dst, append at final
        added = False
        for s in [src, dst]:
            if s not in self.state_order:
                self.state_order.append(s)
                added = True

        if self.state_order:
            self.counts_df = self.counts_df.reindex(index=self.state_order, columns=self.state_order, fill_value=0)

        self.counts_df.loc[src, dst] += 1

        # recalculate probabilities
        self.probs_df = self.counts_to_probs_with_smoothing(self.counts_df, self.epsilon)

        if self.state_order:
            self.counts_df = self.counts_df.reindex(index=self.state_order, columns=self.state_order, fill_value=0).astype("int64")
            self.probs_df = self.probs_df.reindex(index=self.state_order, columns=self.state_order, fill_value=0.0).astype("float64")

        # save matrix
        self.save_matrix()

    def find_optimal_pr(self, src, dst, probs_df=None):
        df = probs_df if probs_df is not None else self.probs_df
        if self.state_order:
            df = df.reindex(index=self.state_order, columns=self.state_order, fill_value=0.0)

        if src not in df.index or dst not in df.columns:
            return 0.0

        max_prob = float(df.loc[src, dst])
        visited = set()

        def dfs(current, cur_prob):
            nonlocal max_prob
            visited.add(current)
            for nxt in df.columns:
                if nxt in visited:
                    continue
                p = float(df.loc[current, nxt])
                if p <= 0:
                    continue
                new_prob = cur_prob * p
                if nxt == dst and new_prob > max_prob:
                    max_prob = new_prob
                if new_prob > max_prob:
                    dfs(nxt, new_prob)
            visited.remove(current)

        dfs(src, 1.0)
        return max_prob

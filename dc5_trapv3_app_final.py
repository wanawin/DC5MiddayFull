
import pandas as pd
import random
from collections import Counter
from fpdf import FPDF
import streamlit as st

# --- V-Trac Mapping ---
def get_vtrac(digit):
    if digit in [0, 5]: return 1
    elif digit in [1, 6]: return 2
    elif digit in [2, 7]: return 3
    elif digit in [3, 8]: return 4
    elif digit in [4, 9]: return 5

def split_digits(n):
    return [int(d) for d in str(n).zfill(2)]

def vtrac_match_category(seed_sum, combo_sum):
    seed_d = split_digits(seed_sum)
    combo_d = split_digits(combo_sum)
    seed_v = {get_vtrac(d) for d in seed_d}
    combo_v = {get_vtrac(d) for d in combo_d}
    overlap = seed_v.intersection(combo_v)
    return "Both V-Tracs Match" if len(overlap) == 2 else "Other"

def filter_consecutive_digits(digits):
    digits = sorted(set(digits))
    max_seq = 1
    current_seq = 1
    for i in range(1, len(digits)):
        if digits[i] == digits[i-1] + 1:
            current_seq += 1
            max_seq = max(max_seq, current_seq)
        else:
            current_seq = 1
    return max_seq >= 4

def filter_digit_spread(digits):
    return max(digits) - min(digits) < 4

def filter_all_0_to_5(digits):
    return all(d <= 5 for d in digits)

def filter_4_digits_within_range(digits, window=2):
    for base in range(0, 10):
        count = sum(base <= d <= base + window for d in digits)
        if count >= 4:
            return True
    return False

# --- App UI ---
st.title("DC-5 Trap V3 + Manual Filter Scoring App")

seed = st.text_input("Enter 5-digit seed:", max_chars=5)
hot_input = st.text_input("Enter at least 3 hot digits (comma-separated):", "0,5,9")
cold_input = st.text_input("Enter at least 3 cold digits (comma-separated):", "2,3,7")
due_input = st.text_input("Enter 2 to 5 due digits (comma-separated):", "1,4")

if seed and len(seed) == 5:
    try:
        hot_digits = [int(d.strip()) for d in hot_input.split(",") if d.strip().isdigit()]
        cold_digits = [int(d.strip()) for d in cold_input.split(",") if d.strip().isdigit()]
        due_digits = [int(d.strip()) for d in due_input.split(",") if d.strip().isdigit()]
        seed_digits = [int(d) for d in seed]

        assert len(hot_digits) >= 3, "At least 3 hot digits required."
        assert len(cold_digits) >= 3, "At least 3 cold digits required."
        assert 2 <= len(due_digits) <= 5, "Due digits must be between 2 and 5."

        import itertools
        source_digits = list(set(hot_digits + cold_digits + due_digits))
        all_combos = list(itertools.product(source_digits, repeat=5))
        df = pd.DataFrame(all_combos, columns=["D1", "D2", "D3", "D4", "D5"])
        df["Combo"] = df.apply(lambda row: "".join(map(str, row)), axis=1)
        df["Digits"] = df[["D1", "D2", "D3", "D4", "D5"]].values.tolist()

        # Simulate seed sum
        seed_sum = sum(seed_digits)
        df["Combo Sum"] = df["Digits"].apply(sum)
        df["Seed Sum"] = seed_sum
        df["V-Trac Match Category"] = df.apply(lambda row: vtrac_match_category(seed_sum, row["Combo Sum"]), axis=1)

        df["F1: Consecutive ≥4"] = df["Digits"].apply(filter_consecutive_digits)
        df["F2: Spread < 4"] = df["Digits"].apply(filter_digit_spread)
        df["F3: All 0–5"] = df["Digits"].apply(filter_all_0_to_5)
        df["F4: 4 in ±2 Range"] = df["Digits"].apply(filter_4_digits_within_range)
        df["F5: Both V-Tracs Match"] = df["V-Trac Match Category"] == "Both V-Tracs Match"
        df["Hot Digit Match"] = df["Digits"].apply(lambda dlist: any(d in hot_digits for d in dlist))
        df["Cold Digit Match"] = df["Digits"].apply(lambda dlist: any(d in cold_digits for d in dlist))
        df["Due Digit Match"] = df["Digits"].apply(lambda dlist: any(d in due_digits for d in dlist))

        df["Trap V3 Score"] = df["Digits"].apply(lambda combo: (
            (sum(1 for d in combo if d in hot_digits) >= 2) +
            (any(d in cold_digits for d in combo)) +
            (any(d in due_digits for d in combo)) +
            (len(set(combo).intersection(set(seed_digits))) == 1) +
            (combo[-1] != seed_digits[-1]) +
            (len(set(combo).intersection({(d + 5) % 10 for d in seed_digits})) == 0) +
            (any(abs(combo[i] % 2 - seed_digits[i % 5] % 2) == 1 for i in range(5))) +
            (sum(1 for d in combo if d in [0, 2, 4, 5, 6, 9]) >= 2)
        ))

        filters = [
            "F1: Consecutive ≥4", "F2: Spread < 4", "F3: All 0–5", "F4: 4 in ±2 Range",
            "F5: Both V-Tracs Match", "Hot Digit Match", "Cold Digit Match", "Due Digit Match"
        ]

        selected_filters = st.multiselect("Select filters to apply (Match filters must be True, others False):", filters)
        trap_threshold = st.slider("Minimum Trap V3 Score to Keep Combo:", 0, 8, 5)

        if selected_filters:
            initial_count = len(df)
            for f in selected_filters:
                if "Match" in f:
                    df = df[df[f]]
                else:
                    df = df[~df[f]]
            df = df[df["Trap V3 Score"] >= trap_threshold]
            st.write(f"Remaining combinations after filtering and Trap V3 ≥ {trap_threshold}: {len(df)} / {initial_count}")
            st.dataframe(df[["Combo", "Trap V3 Score"] + selected_filters])
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Filtered Combos", csv, "filtered_combos.csv", "text/csv")
    except Exception as e:
        st.error(f"Input error: {e}")
else:
    st.warning("Please enter a valid 5-digit seed.")

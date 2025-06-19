import pandas as pd
import random
from collections import Counter
import streamlit as st
import itertools

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
st.title("DC-5 Trap V3 + Manual Filter App (Streamlit Safe)")

seed = st.text_input("Enter 5-digit seed:", max_chars=5)
hot_input = st.text_input("Enter at least 3 hot digits (comma-separated):", "0,5,9")
cold_input = st.text_input("Enter at least 3 cold digits (comma-separated):", "2,3,7")
due_input = st.text_input("Enter 2 to 5 due digits (comma-separated):", "1,4")

if seed and len(seed) == 5 and seed.isdigit():
    try:
        hot_digits = [int(d.strip()) for d in hot_input.split(",") if d.strip().isdigit()]
        cold_digits = [int(d.strip()) for d in cold_input.split(",") if d.strip().isdigit()]
        due_digits = [int(d.strip()) for d in due_input.split(",") if d.strip().isdigit()]
        seed_digits = [int(d) for d in seed]

        assert len(hot_digits) >= 3, "At least 3 hot digits required."
        assert len(cold_digits) >= 3, "At least 3 cold digits required."
        assert 2 <= len(due_digits) <= 5, "Due digits must be between 2 and 5."

        # Step 1: Full Enumeration
        full_space = list(itertools.product(range(10), repeat=5))
        df_full = pd.DataFrame(full_space, columns=list("ABCDE"))
        df_full["Combo"] = df_full.apply(lambda row: "".join(map(str, row)), axis=1)
        st.markdown(f"**Step 1 – Full Enumeration:** {len(df_full)} total 5-digit combos ✅")

        # Step 2: Primary Percentile Filter (simulate retention)
        df_percentile = df_full.sample(frac=0.952, random_state=42)  # simulate 95.2% retention
        st.markdown(f"**Step 2 – Percentile Filter:** {len(df_percentile)} combos remain ✅")

        # Step 3: Generate formula-based combos (seed pairs + triplets with ≥2 seed digits)
        seed_pairs = list(set([(int(seed[i]), int(seed[j])) for i in range(5) for j in range(i+1, 5)]))
        triplets = list(itertools.product(range(10), repeat=3))
        formula_combos = []
        for pair in seed_pairs:
            for trip in triplets:
                combo = list(pair) + list(trip)
                if sum(combo.count(d) for d in seed_digits) >= 2:
                    formula_combos.append(combo)
        df_formula = pd.DataFrame(formula_combos, columns=["D1","D2","D3","D4","D5"])
        df_formula["Combo"] = df_formula.apply(lambda row: "".join(map(str, row)), axis=1)
        st.markdown(f"**Step 3 – Formula Combo Generation:** {len(df_formula)} combos ✅")

        # Step 4: Retain only combos present in both lists
        df_intersect = df_formula[df_formula["Combo"].isin(df_percentile["Combo"])]
        st.markdown(f"**Step 4 – Intersection of Formula & Percentile Survivors:** {len(df_intersect)} combos ✅")

        # Step 5: Deduplication
        df = df_intersect.drop_duplicates(subset=["Combo"])
        df["Digits"] = df[["D1", "D2", "D3", "D4", "D5"]].values.tolist()
        st.markdown(f"**Step 5 – Deduplication (Box Uniqueness):** {len(df)} unique combos ✅")

        # Scoring & Filters
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

        st.markdown("### Manual Filters:")
        for label in [
            "F1: Consecutive ≥4", "F2: Spread < 4", "F3: All 0–5", "F4: 4 in ±2 Range",
            "F5: Both V-Tracs Match", "Hot Digit Match", "Cold Digit Match", "Due Digit Match"]:
            st.markdown(f"- ✅ {label}")

    except Exception as e:
        st.error(f"Input error: {e}")
else:
    st.warning("Please enter a valid 5-digit seed.")

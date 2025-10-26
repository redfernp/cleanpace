# cleanpace.py
import streamlit as st
import pandas as pd
import re
from io import StringIO

# ======================
# Page setup
# ======================
st.set_page_config(page_title="CleanPace", page_icon="🐎", layout="wide")
st.title("🐎 CleanPace – Run Style & Speed Figure Analyzer")

st.write(
    "Paste or upload your **Run Style Figure** table, and paste your **Horse Speed** blocks. "
    "You can process each separately, or run both at the same time. "
    "Speed Figures now includes a simplified export: **Horse Name + Key Speed Factors Average**."
)

# ======================
# Helpers
# ======================
def read_run_style_table(raw: str) -> pd.DataFrame:
    """
    Attempts to parse a 'Run Style Figure' table from raw text.
    Prefers TSV, falls back to CSV. Skips an initial title line if present.
    Returns a DataFrame with only Horse + Lto1..Lto5 (if available).
    """
    text = raw.strip()
    lines = text.splitlines()
    if lines and lines[0].strip().lower() == "run style figure":
        text = "\n".join(lines[1:])

    # Try TSV first, then CSV
    try:
        df = pd.read_csv(StringIO(text), sep="\t")
    except Exception:
        df = pd.read_csv(StringIO(text))

    wanted = ["Horse", "Lto1", "Lto2", "Lto3", "Lto4", "Lto5"]
    present = [c for c in wanted if c in df.columns]

    if not present:
        # Sometimes header might actually be on the second line
        try:
            df = pd.read_csv(StringIO(text), sep="\t", header=1)
        except Exception:
            df = pd.read_csv(StringIO(text), header=1)
        present = [c for c in wanted if c in df.columns]

    subset = df[present].copy()
    for c in ["Lto1", "Lto2", "Lto3", "Lto4", "Lto5"]:
        if c in subset.columns:
            subset[c] = pd.to_numeric(subset[c], errors="coerce")
    return subset


def extract_from_block(block):
    """
    Your provided logic: given ~11-line block, compute speed metrics.
    """
    horse_name = block[0].strip()
    if len(block) < 4:
        return horse_name, None, None, None, None

    speed_line = block[3].strip()
    speed_str = speed_line.split('(')[0].strip()
    if not speed_str:
        return horse_name, None, None, None, None

    try:
        figures = list(map(int, re.findall(r'\d+', speed_str)))
        if not figures:
            return horse_name, None, None, None, None
        last = figures[-1]
        highest = max(figures)
        avg_last_3 = round(sum(figures[-3:]) / len(figures[-3:]), 1)
        avg_all = round(sum(figures) / len(figures), 1)
        return horse_name, last, highest, avg_last_3, avg_all
    except Exception:
        return horse_name, None, None, None, None


def parse_speed_blocks(raw: str) -> pd.DataFrame:
    """
    Parses the large pasted block-style data (your second app).
    Returns computed metrics DataFrame.
    """
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    if lines and "Horse" in lines[0]:
        # Skip an initial header line if present
        lines = lines[1:]

    horses = []
    for i in range(0, len(lines), 11):
        block = lines[i:i+11]
        if not block:
            continue
        horses.append(extract_from_block(block))

    df = pd.DataFrame(horses, columns=[
        "Horse Name",
        "Last Race Speed Figure",
        "Highest Speed Figure",
        "Avg of Last 3",
        "Avg of All"
    ])

    # Compute tops
    top_last = df["Last Race Speed Figure"].max(skipna=True)
    top_high = df["Highest Speed Figure"].max(skipna=True)
    top_avg3 = df["Avg of Last 3"].max(skipna=True)

    def mark_top(row):
        return "✅ Top or Joint Top" if (
            row["Last Race Speed Figure"] == top_last and
            row["Highest Speed Figure"] == top_high and
            row["Avg of Last 3"] == top_avg3
        ) else ""

    df["Top Ranked?"] = df.apply(mark_top, axis=1)

    def avg_key(row):
        try:
            values = [
                row["Last Race Speed Figure"],
                row["Highest Speed Figure"],
                row["Avg of Last 3"]
            ]
            if any(v is None for v in values):
                return None
            return round(sum(values) / len(values), 1)
        except Exception:
            return None

    df["Key Speed Factors Average"] = df.apply(avg_key, axis=1)

    df = df[[
        "Horse Name",
        "Last Race Speed Figure",
        "Highest Speed Figure",
        "Avg of Last 3",
        "Avg of All",
        "Key Speed Factors Average",
        "Top Ranked?"
    ]]
    return df


def download_button_for_df(label: str, df: pd.DataFrame, filename: str):
    st.download_button(
        label,
        df.to_csv(index=False),
        file_name=filename,
        mime="text/csv",
        use_container_width=True
    )


# ======================
# UI – Tabs
# ======================
tab1, tab2, tab3 = st.tabs(["Run Style Cleaner", "Speed Figures", "Run Both"])

# Keep results in session state if you want to reuse later (not required)
if "run_style_df" not in st.session_state:
    st.session_state.run_style_df = None
if "speed_df" not in st.session_state:
    st.session_state.speed_df = None

# ======================
# TAB 1: Run Style Cleaner
# ======================
with tab1:
    st.subheader("Run Style Cleaner")
    col_a, col_b = st.columns(2)
    with col_a:
        rs_text = st.text_area(
            "Paste your Run Style table (can include 'Run Style Figure' title line):",
            height=220,
            key="rs_text"
        )
    with col_b:
        rs_file = st.file_uploader("Or upload TSV/CSV/TXT", type=["tsv", "csv", "txt"], key="rs_file")

    if st.button("Process Run Style"):
        raw = None
        if rs_file is not None:
            raw = rs_file.read().decode("utf-8", errors="ignore")
        elif rs_text.strip():
            raw = rs_text
        else:
            st.warning("Please paste text or upload a file.")
        if raw:
            try:
                rs_df = read_run_style_table(raw)
                if rs_df.empty:
                    st.warning("Parsed data, but couldn't find the columns: Horse, Lto1..Lto5.")
                else:
                    st.success("Run Style parsed successfully.")
                    st.dataframe(rs_df, use_container_width=True)
                    download_button_for_df("💾 Download Clean Run Style CSV", rs_df, "cleanpace_run_style.csv")
                    st.session_state.run_style_df = rs_df
            except Exception as e:
                st.error(f"Failed to parse Run Style data: {e}")

# ======================
# TAB 2: Speed Figures (with simplified output)
# ======================
with tab2:
    st.subheader("Horse Speed Figures")
    st.caption("Paste the full horse blocks (11 lines per horse, same format as your other app).")

    with st.form("horse_form_cleanpace"):
        input_text = st.text_area("Paste your full horse data (with headers and stats):", height=320)
        submitted = st.form_submit_button("Process Speed Figures")

    if submitted:
        if not input_text.strip():
            st.warning("Please paste the speed figure block text.")
        else:
            try:
                sp_df = parse_speed_blocks(input_text)
                st.success("Speed figures parsed successfully.")

                # Full view
                st.markdown("### Full Results")
                st.dataframe(sp_df, use_container_width=True)
                download_button_for_df("💾 Download Full Speed Figures CSV", sp_df, "cleanpace_speed_figures.csv")

                # Simplified view: Horse Name + Key Speed Factors Average
                st.markdown("### 🧩 Simplified View")
                simple_cols = ["Horse Name", "Key Speed Factors Average"]
                simple_df = sp_df[simple_cols].copy()
                st.dataframe(simple_df, use_container_width=True)
                download_button_for_df(
                    "💾 Download Simplified CSV (Horse + Key Avg)",
                    simple_df,
                    "cleanpace_speed_summary.csv"
                )

                st.session_state.speed_df = sp_df
            except Exception as e:
                st.error(f"Failed to parse speed blocks: {e}")

# ======================
# TAB 3: Run Both
# ======================
with tab3:
    st.subheader("Run Both Analyses")
    st.caption("Paste both inputs here and process both at once. You'll get two separate downloads and an optional joined CSV.")
    st.markdown("### Quick Inputs")
    c1, c2 = st.columns(2)

    with c1:
        rs_text_quick = st.text_area(
            "Run Style table",
            height=220,
            key="rs_text_quick"
        )

    with c2:
        sp_text_quick = st.text_area(
            "Speed figure blocks",
            height=220,
            key="sp_text_quick"
        )

    if st.button("🚀 Process Both (Using Quick Inputs)"):
        ok = True
        if not rs_text_quick.strip():
            st.warning("Please paste Run Style table in the left box.")
            ok = False
        if not sp_text_quick.strip():
            st.warning("Please paste Speed figure blocks in the right box.")
            ok = False

        if ok:
            try:
                rs_df2 = read_run_style_table(rs_text_quick)
                sp_df2 = parse_speed_blocks(sp_text_quick)

                # Show side-by-side results
                col_left, col_right = st.columns(2)
                with col_left:
                    st.success("Run Style result")
                    st.dataframe(rs_df2, use_container_width=True)
                    download_button_for_df("💾 Download Clean Run Style CSV", rs_df2, "cleanpace_run_style.csv")

                with col_right:
                    st.success("Speed Figures result")
                    st.dataframe(sp_df2, use_container_width=True)
                    download_button_for_df("💾 Download Full Speed Figures CSV", sp_df2, "cleanpace_speed_figures.csv")

                    # Also provide the simplified CSV here
                    simple_cols = ["Horse Name", "Key Speed Factors Average"]
                    simple_df2 = sp_df2[simple_cols].copy()
                    st.markdown("**Simplified Speed Figures (Horse + Key Avg)**")
                    st.dataframe(simple_df2, use_container_width=True)
                    download_button_for_df(
                        "💾 Download Simplified Speed CSV",
                        simple_df2,
                        "cleanpace_speed_summary.csv"
                    )

                # Optional: Joined CSV (match on horse name)
                st.markdown("### Optional: Joined Output (by Horse Name)")
                rs_norm = rs_df2.copy()
                rs_norm = rs_norm.rename(columns={"Horse": "Horse Name"})
                if "Horse Name" in rs_norm.columns:
                    rs_norm["Horse Name"] = rs_norm["Horse Name"].astype(str).str.strip()

                sp_norm = sp_df2.copy()
                sp_norm["Horse Name"] = sp_norm["Horse Name"].astype(str).str.strip()

                joined = pd.merge(sp_norm, rs_norm, on="Horse Name", how="outer")
                st.dataframe(joined, use_container_width=True)
                download_button_for_df("💾 Download Joined CSV", joined, "cleanpace_joined.csv")

            except Exception as e:
                st.error(f"Error running both analyses: {e}")

st.markdown("---")
st.caption("CleanPace v1.3 • Paste-friendly parsing for Run Style & Speed Figures • Includes simplified speed export.")

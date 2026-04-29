#!/usr/bin/env python3
"""Streamlit-based multi-repo commit bot for waking Streamlit apps."""

import streamlit as st
from github import Github
import datetime

st.set_page_config(page_title="Commit Bot", page_icon="🤖")

st.title("🤖 Multi-Repo Commit Bot")
st.caption("Commit to repos to wake Streamlit apps from sleep.")

if "GITHUB_TOKEN" not in st.secrets:
    st.error("GitHub token not found in secrets.")
    st.info("Add GITHUB_TOKEN (with repo scope) to Streamlit secrets.")
    st.stop()

g = Github(st.secrets["GITHUB_TOKEN"])

repos_raw = st.secrets.get("REPOS", {})
interval_hours = st.secrets.get("INTERVAL_HOURS", 2)
auto_wake = st.secrets.get("AUTO_WAKE", True)

if isinstance(repos_raw, dict):
    repos = [v for k, v in sorted(repos_raw.items()) if k.isdigit()]
elif isinstance(repos_raw, list):
    repos = repos_raw
else:
    repos = []

if not repos:
    st.warning("No repos configured. Add REPOS = {0 = 'owner/repo', 1 = 'owner/repo'} to secrets.")
    st.stop()

if auto_wake:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=interval_hours * 60 * 60 * 1000, limit=None, key="autorefresh")
    except ImportError:
        st.warning("Install streamlit-autorefresh for auto-wake: pip install streamlit-autorefresh")

def get_last_commit_time(repo_name):
    """Get the last commit time from commit-log.txt in the repo."""
    try:
        repo = g.get_repo(repo_name)
        file = repo.get_contents("commit-log.txt")
        lines = file.decoded_content.decode().strip().split("\n")
        if lines and lines[-1]:
            timestamp_str = lines[-1].split(" - ")[0]
            return datetime.datetime.fromisoformat(timestamp_str)
    except Exception:
        pass
    return None

def do_commit(repo_name):
    repo = g.get_repo(repo_name)
    file_path = "commit-log.txt"
    timestamp = datetime.datetime.now().isoformat()
    new_line = f"{timestamp} - Wake commit\n"

    try:
        file = repo.get_contents(file_path)
        repo.update_file(
            path=file_path,
            message=f"Wake commit {timestamp}",
            content=file.decoded_content.decode() + new_line,
            sha=file.sha
        )
    except Exception:
        repo.create_file(
            path=file_path,
            message=f"Wake commit {timestamp}",
            content=new_line
        )
    return timestamp

if auto_wake:
    for repo_name in repos:
        last_commit = get_last_commit_time(repo_name)
        should_commit = False
        if last_commit is None:
            should_commit = True
        elif (datetime.datetime.now() - last_commit).total_seconds() >= interval_hours * 3600:
            should_commit = True

        if should_commit:
            try:
                ts = do_commit(repo_name)
                st.success(f"✅ Auto-woken {repo_name} at {ts}")
            except Exception as e:
                st.error(f"Failed {repo_name}: {e}")

st.divider()
st.subheader("Manual Wake")
for repo_name in repos:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.code(repo_name)
    with col2:
        if st.button("🚀 Wake", key=f"btn_{repo_name}"):
            with st.spinner("Committing..."):
                try:
                    ts = do_commit(repo_name)
                    st.success(f"✅ {repo_name} woken up!")
                except Exception as e:
                    st.error(f"Failed: {e}")

st.divider()
st.caption(f"Auto-wake every {interval_hours} hour(s) | Keep app alive with external pinger (UptimeRobot)")

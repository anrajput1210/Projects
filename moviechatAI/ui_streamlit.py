import requests
import streamlit as st

API_URL = "https://moviechatai-backend.onrender.com"

st.set_page_config(page_title="MovieChat AI", page_icon="🎬", layout="wide")
st.title("🎬 MovieChat AI")
st.caption("Example: hindi comedy movies released after 2015 | funny crime series like sacred games")

# Session state for load more
if "results" not in st.session_state:
    st.session_state.results = []
if "page" not in st.session_state:
    st.session_state.page = 1
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

text = st.text_input("What do you want to watch?", value="hindi comedy movies released after 2015")
page_size = st.slider("Results per page", 5, 20, 10)

colA, colB = st.columns([1, 1])

def fetch(page: int):
    payload = {"text": text, "page": page, "page_size": page_size}
    r = requests.post(f"{API_URL}/ai", json=payload, timeout=90)
    r.raise_for_status()
    return r.json()

with colA:
    if st.button("Search / Reset"):
        st.session_state.results = []
        st.session_state.page = 1
        st.session_state.last_query = text

        data = fetch(1)
        st.session_state.results.extend(data.get("items", []))
        st.session_state.intent = data.get("intent", {})

with colB:
    if st.button("Load more"):
        # if user changed text but didn't reset, treat as reset
        if st.session_state.last_query != text:
            st.session_state.results = []
            st.session_state.page = 1
            st.session_state.last_query = text

        st.session_state.page += 1
        data = fetch(st.session_state.page)
        st.session_state.results.extend(data.get("items", []))
        st.session_state.intent = data.get("intent", {})

# Show intent summary
intent = st.session_state.get("intent", {})
if intent:
    st.info(
        f"Understood → type: `{intent.get('content_type')}` | "
        f"lang: `{intent.get('language')}` | "
        f"years: `{intent.get('year_from')}` to `{intent.get('year_to')}` | "
        f"seed: `{intent.get('seed_title')}`"
    )

# Render results
for i, item in enumerate(st.session_state.results, 1):
    with st.container(border=True):
        cols = st.columns([1, 2.5, 1])

        with cols[0]:
            if item.get("poster_url"):
                st.image(item["poster_url"], use_container_width=True)

        with cols[1]:
            st.subheader(f"{i}. {item.get('title')}")
            st.write(item.get("overview") or "")
            st.markdown(
                f"**Score:** `{item.get('score')}/100`  |  "
                f"**TMDB:** `{item.get('rating')}`  |  "
                f"**Lang:** `{item.get('language')}`"
            )

            avail = item.get("available_on")
            st.write(f"📺 Available on: **{avail}**" if avail else "📺 Available on: *Unknown*")

            if item.get("type") == "movie":
                st.caption(f"Release: {item.get('release_date')}")
            else:
                st.caption(f"First air: {item.get('first_air_date')}")

        with cols[2]:
            trailer = item.get("trailer_url")
            if trailer:
                st.video(trailer)
            else:
                st.write("No trailer")

import requests
import streamlit as st

API_URL = "https://moviechatai-backend.onrender.com"

st.set_page_config(page_title="MovieChat AI", page_icon="🎬", layout="wide")
st.title("🎬 MovieChat AI")
st.caption("Type naturally. Example: 'funny hindi crime series like sacred games'")

text = st.text_input("What do you want to watch?", value="funny hindi crime series like sacred games")
limit = st.slider("How many results?", 1, 20, 10)

if st.button("Get AI recommendations"):
    payload = {"text": text, "limit": limit}

    try:
        r = requests.post(f"{API_URL}/ai", json=payload, timeout=60)
        if r.status_code != 200:
            st.error(f"Error {r.status_code}: {r.text}")
        else:
            data = r.json()
            if not data:
                st.warning("No matches. Try a different prompt.")
            else:
                # Intent summary from first result (they all share same intent)
                intent = data[0].get("intent") or {}
                st.info(
                    f"**Understood:** type = `{intent.get('content_type')}` | "
                    f"language = `{intent.get('language')}` | "
                    f"seed = `{intent.get('seed_title')}`"
                )

                for i, item in enumerate(data, 1):
                    with st.container(border=True):
                        cols = st.columns([1, 2.5, 1])

                        # Poster
                        with cols[0]:
                            if item.get("poster_url"):
                                st.image(item["poster_url"], use_container_width=True)
                            else:
                                st.write("No poster")

                        # Text
                        with cols[1]:
                            st.subheader(f"{i}. {item.get('title')}")
                            st.write(item.get("overview") or "")

                            # Badges row
                            score = item.get("score")
                            rating = item.get("rating")
                            lang = item.get("language")
                            st.markdown(
                                f"**Score:** `{score}/100`   |   "
                                f"**TMDB:** `{rating}`   |   "
                                f"**Lang:** `{lang}`"
                            )

                            # Availability text (no user subscription needed)
                            avail = item.get("available_on")
                            if avail:
                                st.write(f"📺 Available on: **{avail}**")
                            else:
                                st.write("📺 Available on: *Unknown*")

                            # Dates
                            if item.get("type") == "movie":
                                st.caption(f"Release: {item.get('release_date')}")
                            else:
                                st.caption(f"First air: {item.get('first_air_date')}")

                        # Trailer embed
                        with cols[2]:
                            trailer = item.get("trailer_url")
                            if trailer:
                                st.video(trailer)
                            else:
                                st.write("No trailer found")
    except Exception as e:
        st.error(f"Connection error: {e}")


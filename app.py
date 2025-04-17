import streamlit as st
import pickle
import pandas as pd
import requests
import base64
import os

# Load secrets and constants
TMDB_API_KEY = st.secrets["tmdb_api_key"]
TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
PLACEHOLDER_POSTER = "https://via.placeholder.com/500x750?text=No+Image"

# Load movie data
titles_dict = pickle.load(open('movie_dict1.pkl', 'rb'))
movies = pd.DataFrame(titles_dict)
similarity = pickle.load(open('top_similarities.pkl', 'rb'))

# Utility: load background image
def get_img_as_base64(file):
    if not os.path.exists(file):
        return ""
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

# Set background & fonts
bg_img = get_img_as_base64("netflix_1.jpg")
if bg_img:
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Montserrat', sans-serif;
        }}

        /* Set background image for the main app container */
        .stApp {{
            background-image: url("data:image/png;base64,{bg_img}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            position: relative;
        }}

        /* Overlay for darkening the background */
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            z-index: 0;
            pointer-events: none;
        }}

        /* Ensure content is above the overlay */
        .stApp > * {{
            position: relative;
            z-index: 1;
        }}

        [data-testid="stSidebar"] > div:first-child {{
            background-color: #111;
        }}

        h1, h2, h3, h4, h5, h6, p, div {{
            color: white;
        }}
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stApp {
            background: #111;
        }
        </style>
    """, unsafe_allow_html=True)

st.markdown(
    "<h1 style='text-align: center; font-size: 3rem; color: #FF4B4B;'>🎬 Movie Recommendation System</h1><br>",
    unsafe_allow_html=True
)

# ---------------- TMDB API Wrappers ----------------
def fetch_poster(movie_id):
    try:
        res = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US")
        res.raise_for_status()
        data = res.json()
        return IMAGE_BASE_URL + data['poster_path'] if data.get('poster_path') else PLACEHOLDER_POSTER
    except:
        return PLACEHOLDER_POSTER


def fetch_trailer(movie_id):
    try:
        res = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}&language=en-US")
        data = res.json()
        trailers = [v for v in data.get('results', []) if v['site']=='YouTube' and v['type']=='Trailer']
        return trailers[0]['key'] if trailers else None
    except:
        return None


def fetch_movie_details(movie_id):
    try:
        cred = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/credits?api_key={TMDB_API_KEY}").json()
        rev = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/reviews?api_key={TMDB_API_KEY}").json()
        director = next((c['name'] for c in cred.get('crew', []) if c['job']=='Director'), None)
        cast = [c['name'] for c in cred.get('cast', [])[:5]]
        review_list = [r['content'] for r in rev.get('results', [])[:3]]
        return director, cast, review_list
    except:
        return None, [], []


def recommend(movie):
    idx = movies[movies['title']==movie].index[0]
    distances = sorted(list(enumerate(similarity[idx])), reverse=True, key=lambda x: x[1])
    names, posters, ids = [], [], []
    for i, _ in distances[1:6]:
        mid = movies.iloc[i].movie_id
        ids.append(mid)
        names.append(movies.iloc[i].title)
        posters.append(fetch_poster(mid))
    return names, posters, ids

# Generic fetch by category
def fetch_movies_by_category(endpoint):
    try:
        res = requests.get(f"{TMDB_BASE_URL}/{endpoint}?api_key={TMDB_API_KEY}&language=en-US")
        return res.json().get('results', [])
    except:
        return []

# ---------------------- UI Tabs ----------------------
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Recommendations", "🔥 Popular", "📈 Trending", "🎉 Upcoming"])

# ----- Tab 1: Recommendations -----
with tab1:
    query = st.text_input("🔍 Search for a movie", "")
    filtered = [t for t in movies['title'] if query.lower() in t.lower()]
    choice = st.selectbox("Choose a Movie You Like:", filtered or list(movies['title']))
    if st.button("Get Recommendations"):
        with st.spinner("Loading recommendations..."):
            names, posters, ids = recommend(choice)
            st.success("Here are your picks! 🎉")
        for name, poster, mid in zip(names, posters, ids):
            with st.container():
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image(poster, width=180)
                with c2:
                    st.markdown(f"<h3 style='color:#FFCC00'>{name}</h3>", unsafe_allow_html=True)
                    key = fetch_trailer(mid)
                    if key:
                        st.markdown(f'<iframe width="150%" height="180" src="https://www.youtube.com/embed/{key}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)

                    director, cast, reviews = fetch_movie_details(mid)
                    st.markdown(f"**🎬 Director:** {director}")
                    st.markdown(f"**🎭 Cast:** {', '.join(cast)}")

                    # Truncated preview expandable logic
                    if reviews:
                        for r in reviews:
                            preview = (r[:150] + '...') if len(r) > 150 else r
                            with st.expander(preview):
                                st.markdown(f"""
                                    <div style="background-color: #222; padding: 15px; border-radius: 5px;">
                                        {r}
                                    </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.markdown("*No reviews available.*")

# ----- Tab 2: Popular -----
with tab2:
    if st.button("Show Popular Movies"):
        movies_list = fetch_movies_by_category("movie/popular")[:15]
        cols = st.columns(3)
        for idx, m in enumerate(movies_list):
            with cols[idx % 3]:
                img_url = IMAGE_BASE_URL + m['poster_path'] if m.get('poster_path') else PLACEHOLDER_POSTER
                st.image(img_url, width=150)
                st.markdown(f"<h5 style='color:#FFCC00'>{m['title']}</h5>", unsafe_allow_html=True)
                with st.expander("Show Overview"):
                    st.write(m.get('overview', 'No overview available.'))

# ----- Tab 3: Trending -----
with tab3:
    if st.button("Show Trending Movies"):
        movies_list = fetch_movies_by_category("trending/movie/week")[:15]
        cols = st.columns(3)
        for idx, m in enumerate(movies_list):
            with cols[idx % 3]:
                img_url = IMAGE_BASE_URL + m['poster_path'] if m.get('poster_path') else PLACEHOLDER_POSTER
                st.image(img_url, width=150)
                st.markdown(f"<h5 style='color:#FFCC00'>{m['title']}</h5>", unsafe_allow_html=True)
                with st.expander("Show Overview"):
                    st.write(m.get('overview', 'No overview available.'))

# ----- Tab 4: Upcoming -----
with tab4:
    if st.button("Show Upcoming Movies"):
        movies_list = fetch_movies_by_category("movie/upcoming")[:15]
        cols = st.columns(3)
        for idx, m in enumerate(movies_list):
            with cols[idx % 3]:
                img_url = IMAGE_BASE_URL + m['poster_path'] if m.get('poster_path') else PLACEHOLDER_POSTER
                st.image(img_url, width=150)
                st.markdown(f"<h5 style='color:#FFCC00'>{m['title']}</h5>", unsafe_allow_html=True)
                with st.expander("Show Overview"):
                    st.write(m.get('overview', 'No overview available.'))

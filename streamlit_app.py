import streamlit as st
import pandas as pd
import random
import ast
import csv
from io import StringIO

# Set page configuration
st.set_page_config(page_title="xVisionx - Movie Recommendations", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")

# Load movie data from CSV
@st.cache_data
def load_movie_data():
    try:
        movies_df = pd.read_csv('tmdb_5000_movies.csv')
        movies_df["genres"] = movies_df["genres"].apply(lambda x: [g["name"] for g in ast.literal_eval(x)])
        movies_df["genre"] = movies_df["genres"].apply(lambda x: x[0] if x else "Unknown")
        movies_df = movies_df.rename(columns={"vote_average": "rating", "release_date": "year"})
        movies_df["year"] = pd.to_datetime(movies_df["year"], format="mixed", errors='coerce').dt.year
        
        if "movie_id" not in movies_df.columns: movies_df["movie_id"] = movies_df.index + 1
        if "popularity" not in movies_df.columns: movies_df["popularity"] = movies_df["rating"] * 10
            
        return movies_df
    except FileNotFoundError:
        st.error("tmdb_5000_movies.csv not found")
        return pd.DataFrame()

# Initialize session state
def init_session_state():
    defaults = {
        'current_page': "Login", 'user_authenticated': False, 'username': "", 'user_ratings': {},
        'genre_preferences': {}, 'discover_complete': False, 'selected_menu': "Home",
        'new_user': True, 'random_movie_id': None
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

# Calculate genre preferences from ratings
def calculate_genre_preferences(movies_df, user_ratings):
    genre_ratings, genre_counts = {}, {}
    for movie_id, rating in user_ratings.items():
        movie_row = movies_df[movies_df['movie_id'] == movie_id]
        if not movie_row.empty:
            for genre in movie_row.iloc[0]['genres']:
                genre_ratings[genre] = genre_ratings.get(genre, 0) + rating
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
    return {genre: genre_ratings[genre]/genre_counts[genre] for genre in genre_ratings if genre_counts[genre] > 0}

# Create CSV data from user ratings
def create_csv_data(movies_df, user_ratings):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Movie Title", "Rating"])
    for movie_id, rating in user_ratings.items():
        movie_row = movies_df[movies_df['movie_id'] == movie_id]
        if not movie_row.empty: writer.writerow([movie_row.iloc[0]['title'], rating])
    return output.getvalue()

# Load user ratings from CSV
def load_user_ratings_from_csv(uploaded_file, movies_df):
    try:
        csv_data = pd.read_csv(uploaded_file)
        return {movie_row.iloc[0]['movie_id']: row['Rating'] for _, row in csv_data.iterrows() 
                for movie_row in [movies_df[movies_df['title'] == row['Movie Title']] if not movies_df[movies_df['title'] == row['Movie Title']].empty else None] 
                if movie_row is not None}
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
        return {}

# User authentication
def login_page():
    st.title("🎬 CineMatch - Movie Recommendation System")
    st.markdown("### Sign in to get personalized recommendations")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        col1, col2 = st.columns(2)
        with col1: new_account = st.form_submit_button("Create New Account")
        with col2: existing_account = st.form_submit_button("Upload Existing Data")
        
        if new_account and username:
            st.session_state.update({'user_authenticated': True, 'username': username, 'new_user': True, 
                                   'current_page': "Home", 'selected_menu': "Home", 'user_ratings': {}, 
                                   'genre_preferences': {}, 'discover_complete': False})
            st.rerun()
            
        if existing_account:
            uploaded_file = st.file_uploader("Upload your movie ratings CSV", type="csv")
            if uploaded_file is not None and username:
                st.session_state.user_ratings = load_user_ratings_from_csv(uploaded_file, movies_df)
                if st.session_state.user_ratings:
                    st.session_state.genre_preferences = calculate_genre_preferences(movies_df, st.session_state.user_ratings)
                    st.session_state.user_authenticated = True
                    st.session_state.username = username
                    st.session_state.new_user = False
                    st.session_state.discover_complete = True
                    st.session_state.current_page = "Home"
                    st.session_state.selected_menu = "Home"
                    st.rerun()
                else:
                    st.error("No valid ratings found in the uploaded file.")

# Navigation menu
def custom_option_menu():
    menu_options = ["Home", "Discover", "Genre Search", "Random", "Recommended"]
    menu_icons = ["🏠", "🔍", "🎭", "🎲", "⭐"]
    
    cols = st.columns(len(menu_options))
    for i, (option, icon) in enumerate(zip(menu_options, menu_icons)):
        if cols[i].button(f"{icon} {option}", use_container_width=True, key=f"menu_{option}"):
            st.session_state.selected_menu = st.session_state.current_page = option
            st.rerun()
    
    return st.session_state.selected_menu

# Home page
def home_page():
    st.title(f"Welcome to CineMatch, {st.session_state.username}!")
    st.markdown("### How would you like to discover movies today?")
    
    col1, col2, col3 = st.columns(3)
    buttons = [
        ("🎯 Discover Yourself", "Start Discovery", "Discover"),
        ("🔍 Search by Genre", "Browse Genres", "Genre Search"),
        ("🎲 Random Recommendation", "Surprise Me", "Random")
    ]
    
    for i, (header, btn_text, page) in enumerate(buttons):
        with [col1, col2, col3][i]:
            st.subheader(header)
            st.markdown("Rate movies to find your preferred genres" if i == 0 else 
                       "Explore movies by specific genres" if i == 1 else "Get a personalized random suggestion")
            if st.button(btn_text, key=f"{page}_btn", use_container_width=True):
                st.session_state.current_page = page
                st.rerun()
    
    if st.session_state.genre_preferences:
        st.markdown("---")
        st.subheader("Your Genre Preferences")
        sorted_genres = sorted(st.session_state.genre_preferences.items(), key=lambda x: x[1], reverse=True)
        cols = st.columns(4)
        for i, (genre, rating) in enumerate(sorted_genres):
            with cols[i % 4]: st.metric(genre, f"{rating:.1f}/10")
    
    if st.session_state.user_ratings:
        st.markdown("---")
        st.subheader("Your Data")
        csv_data = create_csv_data(movies_df, st.session_state.user_ratings)
        st.download_button(label="Download your ratings as CSV", data=csv_data,
                          file_name=f"{st.session_state.username}_movie_ratings.csv", mime="text/csv")

# Discover page
def discover_page():
    st.title("Discover Your Movie Preferences")
    st.markdown("Rate these popular movies to help us understand your taste")
    
    popular_movies = ["The Dark Knight", "Inception", "Pulp Fiction", "The Godfather", "Forrest Gump", 
                     "The Matrix", "Toy Story", "The Silence of the Lambs", "Star Wars", 
                     "The Lord of the Rings: The Fellowship of the Ring", "Finding Nemo", "The Avengers", 
                     "Titanic", "The Lion King", "Jurassic Park"]
    
    discover_movies = [m for m in popular_movies if not movies_df[movies_df['title'] == m].empty][:10]
    ratings = {}
    
    for movie_title in discover_movies:
        movie_data = movies_df[movies_df['title'] == movie_title].iloc[0]
        st.subheader(f"{movie_title} ({', '.join(movie_data['genres'])})")
        st.write(movie_data['overview'] if pd.notna(movie_data.get('overview', '')) else "No description available.")
        current_rating = st.session_state.user_ratings.get(movie_data['movie_id'], 5)
        ratings[movie_title] = (st.slider("Rate this movie", 1, 10, current_rating, key=f"discover_{movie_data['movie_id']}"), 
                               movie_data['genres'], movie_data['movie_id'])
        st.markdown("---")
    
    if st.button("Submit Ratings"):
        for movie_title, (rating, _, movie_id) in ratings.items():
            st.session_state.user_ratings[movie_id] = rating
        st.session_state.genre_preferences = calculate_genre_preferences(movies_df, st.session_state.user_ratings)
        st.session_state.discover_complete = True
        st.success("Ratings submitted successfully!")
    
    if st.button("Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()

def genre_search_page():
    st.title("Search Movies by Genre")
    
    all_genres = sorted({genre for sublist in movies_df['genres'] for genre in sublist})
    selected_genres = st.multiselect("Select genres", all_genres, default=all_genres[:2])
    
    if selected_genres:
        filtered_movies = movies_df[
            movies_df['genres'].apply(lambda x: any(genre in x for genre in selected_genres))
        ]
        if 'rating' in filtered_movies.columns:
            filtered_movies = filtered_movies.sort_values('rating', ascending=False)
        
        st.subheader(f"Top {len(filtered_movies)} Movies in Selected Genres")
        
        page_size = 10
        total_pages = max(1, (len(filtered_movies) - 1) // page_size + 1)
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
        
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(filtered_movies))
        
        for idx in range(start_idx, end_idx):
            row = filtered_movies.iloc[idx]
            with st.expander(f"{row['title']} ({row.get('year', 'N/A')}) - {row.get('rating', 'N/A')}/10"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Genres**: {', '.join(row['genres'])}")
                    if pd.notna(row.get('overview', '')):
                        st.write(f"**Overview**: {row['overview']}")
                    if 'popularity' in row:
                        st.write(f"**Popularity**: {row['popularity']:.1f}/100")
                with col2:
                    current_rating = st.session_state.user_ratings.get(row['movie_id'], 0)
                    rating = st.slider("Your rating", 1, 10, current_rating or 5, key=f"rate_{row['movie_id']}_{idx}")
                    if st.button("Rate", key=f"btn_{row['movie_id']}_{idx}"):
                        st.session_state.user_ratings[row['movie_id']] = rating
                        st.session_state.genre_preferences = calculate_genre_preferences(movies_df, st.session_state.user_ratings)
                        st.success(f"Rated {row['title']} as {rating}/10")
    else:
        st.info("Please select at least one genre to see movies.")
    
    if st.button("Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()

# Get a random movie recommendation
def get_random_movie():
    preferred_genres = [genre for genre, avg_rating in st.session_state.genre_preferences.items() if avg_rating > 6]
    if not preferred_genres: return None
    selected_genre = random.choice(preferred_genres)
    genre_movies = movies_df[movies_df['genres'].apply(lambda x: selected_genre in x)]
    return genre_movies.sort_values('rating', ascending=False).head(10).sample(1).iloc[0] if len(genre_movies) > 0 else None

# Random recommendation page
def random_recommendation_page():
    st.title("Your Personalized Random Recommendation")
    
    if not st.session_state.genre_preferences and st.session_state.new_user:
        st.warning("Complete the discovery process first or upload your existing data.")
        if st.button("Discover Your Preferences"):
            st.session_state.current_page = "Discover"
            st.rerun()
        return
    
    if st.session_state.random_movie_id is None:
        random_movie = get_random_movie()
        if random_movie is not None: st.session_state.random_movie_id = random_movie['movie_id']
        else: st.warning("No movies found for your preferred genres."); return
    else:
        movie_row = movies_df[movies_df['movie_id'] == st.session_state.random_movie_id]
        if not movie_row.empty: random_movie = movie_row.iloc[0]
        else:
            random_movie = get_random_movie()
            if random_movie is not None: st.session_state.random_movie_id = random_movie['movie_id']
            else: st.warning("No movies found for your preferred genres."); return
    
    preferred_genres = [genre for genre, avg_rating in st.session_state.genre_preferences.items() if avg_rating > 6]
    
    st.subheader("We think you'll enjoy...")
    st.markdown(f"### {random_movie['title']} ({random_movie.get('year', 'N/A')})")
    st.write(f"**Genres**: {', '.join(random_movie['genres'])}")
    common_genres = set(random_movie['genres']) & set(preferred_genres)
    if common_genres: st.write(f"**Why we think you'll like it**: This movie shares your preferred genres: {', '.join(common_genres)}")
    
    if 'rating' in random_movie: st.write(f"**Rating**: {random_movie['rating']}/10")
    if 'popularity' in random_movie: st.write(f"**Popularity**: {random_movie['popularity']:.1f}/100")
    if pd.notna(random_movie.get('overview', '')): st.write(f"**Overview**: {random_movie['overview']}")
    
    st.markdown("---")
    st.subheader("Rate this movie")
    current_rating = st.session_state.user_ratings.get(random_movie['movie_id'], 5)
    rating = st.slider("Your rating", 1, 10, current_rating, key=f"rate_random_{random_movie['movie_id']}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Submit Rating"):
            st.session_state.user_ratings[random_movie['movie_id']] = rating
            st.session_state.genre_preferences = calculate_genre_preferences(movies_df, st.session_state.user_ratings)
            st.success(f"Rated {random_movie['title']} as {rating}/10")
    with col2:
        if st.button("Another Recommendation"):
            st.session_state.random_movie_id = None
            st.rerun()
    with col3:
        if st.button("Back to Home"):
            st.session_state.current_page = "Home"
            st.session_state.random_movie_id = None
            st.rerun()

def calculate_recommendation_score(movie_genres, user_preferences, movie_rating):
    genre_match_score = sum(user_preferences.get(genre, 0) for genre in movie_genres)
    max_possible_genre_score = sum(user_preferences.values())
    genre_score = (genre_match_score / max_possible_genre_score * 10) if max_possible_genre_score > 0 else 0
    rating_score = movie_rating if pd.notna(movie_rating) else 5
    return (genre_score * 0.75) + (rating_score * 0.25)

def recommended_movies_page():
    st.title("Movies You Might Like")
    
    if not st.session_state.genre_preferences and st.session_state.new_user:
        st.warning("Complete the discovery process first or upload your existing data.")
        if st.button("Discover Your Preferences"):
            st.session_state.current_page = "Discover"
            st.rerun()
        return
    
    preferred_genres = [genre for genre, avg_rating in st.session_state.genre_preferences.items() if avg_rating > 6]
    if not preferred_genres:
        st.warning("Rate more movies to discover preferences.")
        if st.button("Discover Your Preferences"):
            st.session_state.current_page = "Discover"
            st.rerun()
        return
    
    movies_with_scores = [(row, calculate_recommendation_score(row['genres'], st.session_state.genre_preferences, row['rating'])) 
                         for _, row in movies_df.iterrows()]
    movies_with_scores.sort(key=lambda x: x[1], reverse=True)
    top_recommendations = [movie for movie, score in movies_with_scores[:20]]
    
    st.subheader(f"Top {len(top_recommendations)} Recommendations Based on Your Preferences")
    st.info("🎯 Recommendations are weighted 75% by your genre preferences and 25% by movie ratings")
    
    for idx, row in enumerate(top_recommendations):
        with st.expander(f"{row['title']} ({row.get('year', 'N/A')}) - Recommendation Score: {movies_with_scores[idx][1]:.1f}/10"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Genres**: {', '.join(row['genres'])}")
                common_genres = set(row['genres']) & set(st.session_state.genre_preferences.keys())
                if common_genres:
                    genre_explanations = [f"{genre} (you rated: {st.session_state.genre_preferences[genre]:.1f}/10)" for genre in common_genres]
                    st.write(f"**Why we think you'll like it**: You enjoy {', '.join(genre_explanations)}")
                if pd.notna(row.get('overview', '')): st.write(f"**Overview**: {row['overview']}")
                if 'popularity' in row: st.write(f"**Popularity**: {row['popularity']:.1f}/100")
                if 'rating' in row: st.write(f"**Movie Rating**: {row['rating']}/10")
            with col2:
                current_rating = st.session_state.user_ratings.get(row['movie_id'], 5)
                rating = st.slider("Your rating", 1, 10, current_rating, key=f"rate_rec_{row['movie_id']}_{idx}")
                if st.button("Rate", key=f"btn_rec_{row['movie_id']}_{idx}"):
                    st.session_state.user_ratings[row['movie_id']] = rating
                    st.session_state.genre_preferences = calculate_genre_preferences(movies_df, st.session_state.user_ratings)
                    st.success(f"Rated {row['title']} as {rating}/10")
    
    if st.button("Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()

# Main app logic
def main():
    init_session_state()
    global movies_df
    movies_df = load_movie_data()    
    if movies_df.empty: return st.error("Failed to load movie data")
    
    with st.sidebar:
        st.title("🎬 CineMatch")
        if st.session_state.user_authenticated:
            st.write(f"Welcome, {st.session_state.username}!")
            custom_option_menu()
            st.markdown("---")
            if st.button("Logout"):
                st.session_state.update({'user_authenticated': False, 'username': "", 'user_ratings': {}, 
                                       'genre_preferences': {}, 'discover_complete': False, 'new_user': True, 
                                       'random_movie_id': None, 'current_page': "Login"})
                st.rerun()
        else: st.write("Please login to access movie recommendations")
    
    if not st.session_state.user_authenticated: login_page()
    else: {"Home": home_page, "Discover": discover_page, "Genre Search": genre_search_page, 
           "Random": random_recommendation_page, "Recommended": recommended_movies_page
          }.get(st.session_state.current_page, home_page)()

if __name__ == "__main__":
    main()

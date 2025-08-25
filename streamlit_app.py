import streamlit as st
import pandas as pd
import random
import ast

# Set page configuration
st.set_page_config(
    page_title="CineMatch - Movie Recommendations",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load movie data from CSV
@st.cache_data
def load_movie_data():
    try:
        movies_df = pd.read_csv('tmdb_5000_movies.csv')
        movies_df["genres"] = movies_df["genres"].apply(
            lambda x: [g["name"] for g in ast.literal_eval(x)]
        )
        movies_df["genre"] = movies_df["genres"].apply(
            lambda x: x[0] if len(x) > 0 else "Unknown"
        )
        movies_df = movies_df.rename(columns={"vote_average": "rating", "release_date": "year"})
        movies_df["year"] = pd.to_datetime(movies_df["year"],format="mixed").dt.year
        
        if "movie_id" not in movies_df.columns:
            movies_df["movie_id"] = movies_df.index + 1
        if "popularity" not in movies_df.columns:
            movies_df["popularity"] = movies_df["rating"] * 10
            
        st.success("Movie data loaded successfully")
        return movies_df
        
    except FileNotFoundError:
        st.error("tmdb_5000_movies.csv not found")
        return pd.DataFrame()

# Initialize session state
def init_session_state():
    defaults = {
        'current_page': "Login",
        'user_authenticated': False,
        'username': "",
        'user_ratings': {},
        'genre_preferences': {},
        'discover_complete': False,
        'selected_menu': "Home"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# User authentication
def login_page():
    st.title("🎬 CineMatch - Movie Recommendation System")
    st.markdown("### Sign in to get personalized recommendations")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login") and username and password:
            st.session_state.user_authenticated = True
            st.session_state.username = username
            st.session_state.current_page = "Home"
            st.session_state.selected_menu = "Home"
            st.rerun()

# Navigation menu
def custom_option_menu():
    menu_options = ["Home", "Discover", "Genre Search", "Random", "Recommended"]
    menu_icons = ["🏠", "🔍", "🎭", "🎲", "⭐"]
    
    cols = st.columns(len(menu_options))
    for i, (option, icon) in enumerate(zip(menu_options, menu_icons)):
        if cols[i].button(f"{icon} {option}", use_container_width=True, key=f"menu_{option}"):
            st.session_state.selected_menu = option
            st.session_state.current_page = option
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
                       "Explore movies by specific genres" if i == 1 else 
                       "Get a personalized random suggestion")
            if st.button(btn_text, key=f"{page}_btn", use_container_width=True):
                st.session_state.current_page = page
                st.rerun()
    
    # Show genre ratings instead of recently rated movies
    if st.session_state.genre_preferences:
        st.markdown("---")
        st.subheader("Your Genre Preferences")
        
        # Sort genres by rating (highest first)
        sorted_genres = sorted(st.session_state.genre_preferences.items(), 
                              key=lambda x: x[1], reverse=True)
        
        cols = st.columns(4)
        for i, (genre, rating) in enumerate(sorted_genres):
            with cols[i % 4]:
                st.metric(genre, f"{rating:.1f}/10")

# Discover page
def discover_page():
    st.title("Discover Your Movie Preferences")
    st.markdown("Rate these popular movies to help us understand your taste")
    
    popular_movies = [
        "The Dark Knight", "Inception", "Pulp Fiction", "The Godfather", 
        "Forrest Gump", "The Matrix", "Toy Story", "The Silence of the Lambs",
        "Star Wars", "The Lord of the Rings: The Fellowship of the Ring",
        "Finding Nemo", "The Avengers", "Titanic", "The Lion King", "Jurassic Park"
    ]
    
    available_movies = [m for m in popular_movies if not movies_df[movies_df['title'] == m].empty]
    discover_movies = available_movies[:10]
    
    ratings = {}
    for movie_title in discover_movies:
        movie_data = movies_df[movies_df['title'] == movie_title].iloc[0]
        genres = movie_data['genres'] if 'genres' in movie_data else ["Unknown"]
        movie_id = movie_data['movie_id']
        
        st.subheader(f"{movie_title} ({', '.join(genres)})")
        st.write(movie_data['overview'] if 'overview' in movie_data and pd.notna(movie_data['overview']) else "No description available.")
        
        current_rating = st.session_state.user_ratings.get(movie_id, 5)
        rating = st.slider("Rate this movie", 1, 10, current_rating, key=f"discover_{movie_title}")
        ratings[movie_title] = (rating, genres, movie_id)
        st.markdown("---")
    
    if st.button("Submit Ratings"):
        for movie_title, (rating, genres, movie_id) in ratings.items():
            st.session_state.user_ratings[movie_id] = rating
        
        genre_ratings, genre_counts = {}, {}
        for movie_title, (rating, genres, movie_id) in ratings.items():
            for genre in genres:
                genre_ratings[genre] = genre_ratings.get(genre, 0) + rating
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        st.session_state.genre_preferences = {genre: genre_ratings[genre]/genre_counts[genre] for genre in genre_ratings}
        st.session_state.discover_complete = True
        st.session_state.current_page = "Recommended"
        st.rerun()
    
    if st.button("Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()

# Genre search page - FIXED PAGINATION
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
        
        # Fixed pagination
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
                    st.write(f"**Genres**: {', '.join(row['genres']) if 'genres' in row else 'N/A'}")
                    if 'overview' in row and pd.notna(row['overview']):
                        st.write(f"**Overview**: {row['overview']}")
                    if 'popularity' in row:
                        st.write(f"**Popularity**: {row['popularity']}/100")
                with col2:
                    current_rating = st.session_state.user_ratings.get(row['movie_id'], 0)
                    st.write(f"Current rating: {current_rating}/10" if current_rating else "Rate this movie")
                    rating = st.slider("Your rating", 1, 10, current_rating or 5, key=f"rate_{row['movie_id']}_{idx}")
                    if st.button("Rate", key=f"btn_{row['movie_id']}_{idx}"):
                        st.session_state.user_ratings[row['movie_id']] = rating
                        st.success(f"Rated {row['title']} as {rating}/10")
                        update_preferences(row['genres'], rating)
    else:
        st.info("Please select at least one genre to see movies.")
    
    if st.button("Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()

# Random recommendation page
def random_recommendation_page():
    st.title("Your Personalized Random Recommendation")
    
    if not st.session_state.genre_preferences:
        st.warning("Complete the discovery process first.")
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
    
    selected_genre = random.choice(preferred_genres)
    genre_movies = movies_df[movies_df['genres'].apply(lambda x: selected_genre in x)]
    
    if len(genre_movies) > 0:
        top_movies = genre_movies.sort_values('rating', ascending=False).head(10) if 'rating' in genre_movies.columns else genre_movies.head(10)
        random_movie = top_movies.sample(1).iloc[0]
        
        st.subheader("We think you'll enjoy...")
        st.markdown(f"### {random_movie['title']} ({random_movie.get('year', 'N/A')})")
        st.write(f"**Genres**: {', '.join(random_movie['genres']) if 'genres' in random_movie else 'N/A'}")
        
        # Show why this movie was recommended
        common_genres = set(random_movie['genres']) & set(preferred_genres) if 'genres' in random_movie else set()
        if common_genres:
            st.write(f"**Why we think you'll like it**: This movie shares your preferred genres: {', '.join(common_genres)}")
        
        if 'rating' in random_movie:
            st.write(f"**Rating**: {random_movie['rating']}/10")
        if 'popularity' in random_movie:
            st.write(f"**Popularity**: {random_movie['popularity']}/100")
        if 'overview' in random_movie and pd.notna(random_movie['overview']):
            st.write(f"**Overview**: {random_movie['overview']}")
        
        st.markdown("---")
        st.subheader("Rate this movie")
        rating = st.slider("Your rating", 1, 10, 5, key=f"rate_random_{random_movie['movie_id']}")
        if st.button("Submit Rating"):
            st.session_state.user_ratings[random_movie['movie_id']] = rating
            st.success(f"Rated {random_movie['title']} as {rating}/10")
            update_preferences(random_movie['genres'], rating)
    else:
        st.warning(f"No movies found in genre: {selected_genre}")
    
    if st.button("Another Recommendation"):
        st.rerun()
    if st.button("Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()

# Calculate recommendation score with 80% weight to genre match and 20% to rating
def calculate_recommendation_score(movie_genres, user_preferences, movie_rating):
    # Calculate genre match score (80% weight)
    genre_match_score = 0
    max_possible_genre_score = sum(user_preferences.values())
    
    for genre in movie_genres:
        if genre in user_preferences:
            genre_match_score += user_preferences[genre]
    
    # Normalize genre score to 0-10 scale
    if max_possible_genre_score > 0:
        genre_score = (genre_match_score / max_possible_genre_score) * 10
    else:
        genre_score = 0
    
    # Calculate rating score (20% weight)
    rating_score = movie_rating if pd.notna(movie_rating) else 5
    
    # Combined score with 80:20 weighting
    final_score = (genre_score * 0.8) + (rating_score * 0.2)
    
    return final_score

# Recommended movies page with improved algorithm
def recommended_movies_page():
    st.title("Movies You Might Like")
    
    if not st.session_state.genre_preferences:
        st.warning("Complete the discovery process first.")
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
    
    # Calculate recommendation scores for all movies
    movies_with_scores = []
    for idx, row in movies_df.iterrows():
        if 'genres' in row and 'rating' in row:
            score = calculate_recommendation_score(
                row['genres'], 
                st.session_state.genre_preferences, 
                row['rating']
            )
            movies_with_scores.append((row, score))
    
    # Sort by recommendation score (highest first)
    movies_with_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Get top 20 recommendations
    top_recommendations = [movie for movie, score in movies_with_scores[:20]]
    
    st.subheader(f"Top {len(top_recommendations)} Recommendations Based on Your Preferences")
    st.info("🎯 Recommendations are weighted 80% by your genre preferences and 20% by movie ratings")
    
    for idx, row in enumerate(top_recommendations):
        with st.expander(f"{row['title']} ({row.get('year', 'N/A')}) - Recommendation Score: {movies_with_scores[idx][1]:.1f}/10"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Genres**: {', '.join(row['genres']) if 'genres' in row else 'N/A'}")
                
                # Show why this movie was recommended with detailed explanation
                common_genres = set(row['genres']) & set(st.session_state.genre_preferences.keys()) if 'genres' in row else set()
                if common_genres:
                    genre_explanations = []
                    for genre in common_genres:
                        user_rating = st.session_state.genre_preferences[genre]
                        genre_explanations.append(f"{genre} (you rated: {user_rating:.1f}/10)")
                    
                    st.write(f"**Why we think you'll like it**: You enjoy {', '.join(genre_explanations)}")
                
                if 'overview' in row and pd.notna(row['overview']):
                    st.write(f"**Overview**: {row['overview']}")
                if 'popularity' in row:
                    st.write(f"**Popularity**: {row['popularity']}/100")
                if 'rating' in row:
                    st.write(f"**Movie Rating**: {row['rating']}/10")
            with col2:
                current_rating = st.session_state.user_ratings.get(row['movie_id'], 0)
                st.write(f"Current rating: {current_rating}/10" if current_rating else "Rate this movie")
                rating = st.slider("Your rating", 1, 10, current_rating or 5, key=f"rate_rec_{row['movie_id']}_{idx}")
                if st.button("Rate", key=f"btn_rec_{row['movie_id']}_{idx}"):
                    st.session_state.user_ratings[row['movie_id']] = rating
                    st.success(f"Rated {row['title']} as {rating}/10")
                    update_preferences(row['genres'], rating)
    
    if st.button("Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()

# Helper function
def update_preferences(genres, rating):
    for genre in genres:
        if genre in st.session_state.genre_preferences:
            st.session_state.genre_preferences[genre] = (st.session_state.genre_preferences[genre] + rating) / 2
        else:
            st.session_state.genre_preferences[genre] = rating

# Main app logic
def main():
    init_session_state()
    global movies_df
    movies_df = load_movie_data()
    
    if movies_df.empty:
        st.error("Failed to load movie data")
        return
    
    with st.sidebar:
        st.title("🎬 CineMatch")
        if st.session_state.user_authenticated:
            st.write(f"Welcome, {st.session_state.username}!")
            custom_option_menu()
            st.markdown("---")
            if st.button("Logout"):
                st.session_state.user_authenticated = False
                st.session_state.current_page = "Login"
                st.rerun()
        else:
            st.write("Please login to access movie recommendations")
    
    if not st.session_state.user_authenticated:
        login_page()
    else:
        pages = {
            "Home": home_page,
            "Discover": discover_page,
            "Genre Search": genre_search_page,
            "Random": random_recommendation_page,
            "Recommended": recommended_movies_page
        }
        pages.get(st.session_state.current_page, home_page)()

if __name__ == "__main__":
    main()

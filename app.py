import streamlit as st
import feedparser
import hashlib
import html
import json
import os
from datetime import datetime
from urllib.parse import quote_plus

# Optional AI recommendations. The app still works if this package/model is unavailable.
try:
    from sentence_transformers import SentenceTransformer, util
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False

st.set_page_config(
    page_title="StudentAI News",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

USER_FILE = "users.json"
NEWS_TTL_SECONDS = 900

CATEGORIES = {
    "Technology": "https://techcrunch.com/feed/",
    "AI & Machine Learning": "https://news.google.com/rss/search?q=artificial+intelligence+machine+learning&hl=en-IN&gl=IN&ceid=IN:en",
    "Education": "https://news.google.com/rss/search?q=education+students&hl=en-IN&gl=IN&ceid=IN:en",
    "Jobs & Careers": "https://news.google.com/rss/search?q=jobs+careers+students+India&hl=en-IN&gl=IN&ceid=IN:en",
    "Programming": "https://news.google.com/rss/search?q=programming+software+development&hl=en-IN&gl=IN&ceid=IN:en",
    "Cyber Security": "https://news.google.com/rss/search?q=cybersecurity&hl=en-IN&gl=IN&ceid=IN:en",
    "Scholarships": "https://news.google.com/rss/search?q=scholarships+students+India&hl=en-IN&gl=IN&ceid=IN:en",
    "Competitive Exams": "https://news.google.com/rss/search?q=competitive+exams+India&hl=en-IN&gl=IN&ceid=IN:en",
    "Startups": "https://news.google.com/rss/search?q=startups+India&hl=en-IN&gl=IN&ceid=IN:en",
}

# ---------- Design system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root { --ink:#172033; --muted:#64748b; --purple:#6755e8; --pink:#e94fa3; --blue:#3185f5; }
html, body, [class*="css"] { font-family: Inter, sans-serif; }
.stApp { background: linear-gradient(135deg,#f7f8ff 0%,#f2f6ff 48%,#fff6fb 100%); color:var(--ink); }
.block-container { max-width:1320px; padding-top:1.7rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#171b3d,#29235c 65%,#44266c); }
[data-testid="stSidebar"] * { color:#fff !important; }
[data-testid="stSidebar"] [data-testid="stMultiSelect"] span { color:#20233a !important; }
h1,h2,h3 { letter-spacing:-.035em; color:#172033; }
.stButton > button, .stLinkButton > a { border-radius:12px; font-weight:650; min-height:2.65rem; transition:all .18s ease; }
.stButton > button[kind="primary"] { background:linear-gradient(100deg,#6554e8,#a03be5); border:0; }
.stButton > button:hover, .stLinkButton > a:hover { transform:translateY(-1px); box-shadow:0 8px 20px #5b50a526; }
.stTextInput input, .stTextArea textarea { border-radius:12px; }
div[data-baseweb="tab-list"] { gap:8px; }
button[data-baseweb="tab"] { border-radius:10px 10px 0 0; font-weight:650; }
div[data-testid="stMetric"] { background:white; border:1px solid #e6e8f4; border-radius:18px; padding:18px; box-shadow:0 8px 25px #27356b0b; }
hr { border-color:#e7e9f4; }
</style>
""", unsafe_allow_html=True)

def esc(value):
    return html.escape(str(value or ""))

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}

def save_users(users):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def load_saved_for_user(username):
    users = load_users()
    return users.get(username, {}).get("bookmarks", [])

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "bookmarks" not in st.session_state:
    st.session_state.bookmarks = []
if "page" not in st.session_state:
    st.session_state.page = "Home"

def login_page():
    st.html("""
    <div style="max-width:600px;margin:25px auto 18px;padding:35px 28px 30px;border-radius:28px;text-align:center;background:linear-gradient(130deg,#fff 0%,#f5f2ff 100%);border:1px solid #e6e2ff;box-shadow:0 20px 65px #463b8918">
      <div style="font-size:58px;line-height:1.2">🎓</div>
      <div style="font-size:36px;font-weight:800;color:#202044;margin-top:12px">StudentAI News</div>
      <div style="font-size:16px;color:#667085;margin-top:10px">Your personal hub for student news, skills, scholarships and careers.</div>
      <div style="display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-top:22px">
        <span style="background:#e8e6ff;color:#5847c9;padding:7px 12px;border-radius:20px;font-size:12px;font-weight:700">✨ AI recommendations</span>
        <span style="background:#ffe7f4;color:#a52b72;padding:7px 12px;border-radius:20px;font-size:12px;font-weight:700">🎯 Student focused</span>
        <span style="background:#e1f3ff;color:#1765a8;padding:7px 12px;border-radius:20px;font-size:12px;font-weight:700">🔖 Save articles</span>
      </div>
    </div>
    """)
    _, center, _ = st.columns([1, 1.5, 1])
    with center:
        tab_login, tab_register = st.tabs(["🔐 Sign in", "📝 Create account"])
        with tab_login:
            username = st.text_input("Username", placeholder="Enter your username", key="login_user")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
            if st.button("Sign in →", type="primary", use_container_width=True, key="signin_btn"):
                users = load_users()
                if username in users and users[username].get("password") == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.bookmarks = users[username].get("bookmarks", [])
                    st.session_state.page = "Home"
                    st.rerun()
                elif username not in users:
                    st.error("Account not found. Choose Create account to register.")
                else:
                    st.error("Password doesn't match. Please try again.")
        with tab_register:
            new_user = st.text_input("Create username", placeholder="Choose a username", key="reg_user")
            new_pass = st.text_input("Create password", type="password", placeholder="Use at least 6 characters", key="reg_pass")
            confirm = st.text_input("Confirm password", type="password", placeholder="Enter the password again", key="reg_confirm")
            if st.button("Create my account", type="primary", use_container_width=True, key="register_btn"):
                users = load_users()
                if not new_user.strip() or not new_pass:
                    st.warning("Please fill in all fields.")
                elif len(new_pass) < 6:
                    st.warning("Use a password with at least 6 characters.")
                elif new_user.strip() in users:
                    st.error("That username already exists. Please sign in.")
                elif new_pass != confirm:
                    st.error("The passwords do not match.")
                else:
                    users[new_user.strip()] = {"password": hash_password(new_pass), "bookmarks": []}
                    save_users(users)
                    st.success("Account created! Open Sign in and log in.")
    st.markdown("<div style='text-align:center;color:#8a91a8;font-size:12px;margin-top:25px'>Built for curious students · Learn something new every day</div>", unsafe_allow_html=True)

if not st.session_state.logged_in:
    login_page()
    st.stop()

# ---------- RSS collection ----------
@st.cache_data(ttl=NEWS_TTL_SECONDS, show_spinner=False)
def fetch_news():
    articles = []
    for category, url in CATEGORIES.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:12]:
                title = str(entry.get("title", "")).strip()
                link = str(entry.get("link", "")).strip()
                if not title or not link:
                    continue
                summary = entry.get("summary", "") or entry.get("description", "")
                # RSS summaries can contain HTML. Strip tags without needing another dependency.
                summary = __import__("re").sub(r"<[^>]+>", " ", str(summary))
                summary = " ".join(__import__("html").unescape(summary).split())
                published = entry.get("published", "") or entry.get("updated", "")
                articles.append({
                    "title": title, "link": link, "description": summary[:360],
                    "category": category, "published": str(published)
                })
        except Exception:
            continue
    unique = {}
    for article in articles:
        unique.setdefault(article["link"], article)
    return list(unique.values())

@st.cache_resource(show_spinner=False)
def load_ai_model():
    if not AI_AVAILABLE:
        return None
    return SentenceTransformer("all-MiniLM-L6-v2")

def recommend_articles(articles, interests, number=8):
    if not articles:
        return []
    if not interests:
        return articles[:number]
    # Reliable keyword fallback means recommendations still show if model download fails.
    try:
        model = load_ai_model()
        if model is not None:
            interest_text = ", ".join(interests)
            texts = [a["title"] + " " + a["description"] + " " + a["category"] for a in articles]
            interest_vec = model.encode(interest_text, convert_to_tensor=True)
            article_vecs = model.encode(texts, convert_to_tensor=True)
            scores = util.cos_sim(interest_vec, article_vecs)[0]
            ranked = []
            for idx in scores.argsort(descending=True)[:number]:
                item = dict(articles[int(idx)])
                item["score"] = round(float(scores[int(idx)]) * 100, 1)
                ranked.append(item)
            return ranked
    except Exception:
        pass
    interest_words = [word.lower() for interest in interests for word in interest.replace("&", " ").split()]
    def score(a):
        text = (a["title"] + " " + a["description"] + " " + a["category"]).lower()
        return sum(1 for word in interest_words if len(word) > 2 and word in text)
    ranked = sorted(articles, key=score, reverse=True)[:number]
    for item in ranked:
        item["score"] = min(95, 50 + score(item) * 8)
    return ranked

def persist_bookmarks():
    users = load_users()
    user = st.session_state.username
    if user in users:
        users[user]["bookmarks"] = st.session_state.bookmarks
        save_users(users)

def toggle_bookmark(article):
    links = {item.get("link") for item in st.session_state.bookmarks}
    if article["link"] in links:
        st.session_state.bookmarks = [x for x in st.session_state.bookmarks if x.get("link") != article["link"]]
        persist_bookmarks()
        st.toast("Removed from saved articles")
    else:
        st.session_state.bookmarks.insert(0, article)
        persist_bookmarks()
        st.toast("Article saved!")

def render_article(article, prefix):
    category = esc(article.get("category", "Student News"))
    title = esc(article.get("title", "Untitled article"))
    description = esc(article.get("description", "Open the article to read the full story."))
    published = esc(article.get("published", "Latest update"))
    st.html(f"""
    <div style="background:#fff;border:1px solid #e7e9f5;border-radius:18px;padding:21px 23px;margin:4px 0 8px;box-shadow:0 7px 24px #202b5c0a">
      <div style="display:inline-block;background:linear-gradient(90deg,#eeeaff,#fce7f3);color:#6543ba;padding:5px 11px;border-radius:30px;font-size:11px;font-weight:800;margin-bottom:10px">{category}</div>
      <div style="font-size:19px;line-height:1.45;font-weight:750;color:#202443;margin-bottom:8px">{title}</div>
      <div style="font-size:14px;line-height:1.65;color:#68738a">{description or 'Open the article to read the full story.'}</div>
      <div style="font-size:11px;color:#929ab0;margin-top:13px">🕒 {published}</div>
    </div>
    """)
    col_read, col_save = st.columns([1, 1])
    with col_read:
        st.link_button("Read full article ↗", article["link"], use_container_width=True)
    with col_save:
        saved = any(x.get("link") == article["link"] for x in st.session_state.bookmarks)
        if st.button("✓ Saved" if saved else "🔖 Save article", key=f"{prefix}_{hashlib.md5(article['link'].encode()).hexdigest()}", use_container_width=True):
            toggle_bookmark(article)
            st.rerun()

# ---------- Sidebar and navigation ----------
with st.sidebar:
    st.html("""
    <div style="text-align:center;padding:16px 8px 24px">
      <div style="font-size:44px">🎓</div>
      <div style="font-size:23px;font-weight:800;letter-spacing:-.5px">StudentAI</div>
      <div style="font-size:12px;color:#d9d5ff!important;margin-top:5px">YOUR STUDENT ADVANTAGE</div>
    </div>
    """)
    st.markdown(f"### 👋 Hi, {esc(st.session_state.username)}")
    st.caption("What would you like to explore?")
    nav_items = [
        ("🏠", "Home"), ("🤖", "AI Recommendations"), ("📰", "All News"),
        ("🎓", "Scholarships"), ("💼", "Jobs & Careers"), ("🔖", "Saved Articles"),
    ]
    for icon, label in nav_items:
        if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True,
                     type="primary" if st.session_state.page == label else "secondary"):
            st.session_state.page = label
            st.rerun()
    st.markdown("---")
    st.markdown("### 🎯 Your interests")
    selected_interests = st.multiselect(
        "Choose topics for your recommendations",
        list(CATEGORIES.keys()),
        default=["Technology", "AI & Machine Learning", "Education"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    if st.button("↻ Refresh news", use_container_width=True):
        fetch_news.clear()
        st.rerun()
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.bookmarks = []
        st.rerun()

# ---------- Main page header ----------
st.html("""
<div style="display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-bottom:20px">
  <div><div style="font-size:12px;letter-spacing:2px;font-weight:800;color:#7564d8">YOUR DAILY STUDENT BRIEFING</div>
  <div style="font-size:35px;font-weight:850;letter-spacing:-1.5px;color:#1c2340;margin-top:4px">StudentAI <span style="background:linear-gradient(90deg,#6554e8,#dc4b9d);background-clip:text;-webkit-background-clip:text;color:transparent">News</span></div>
  <div style="color:#69758e;font-size:14px;margin-top:4px">News, opportunities and ideas to help you move forward.</div></div>
  <div style="background:#fff;border:1px solid #e7e7f5;border-radius:16px;padding:13px 18px;color:#5c4ecb;font-weight:750">✨ Learn · Discover · Grow</div>
</div>
""")

with st.spinner("Gathering the latest student news..."):
    news_data = fetch_news()

search_query = st.text_input("🔎 Search stories", placeholder="Search AI, exams, scholarships, jobs, programming…")
if search_query.strip():
    q = search_query.casefold()
    filtered_news = [a for a in news_data if q in (a["title"] + " " + a["description"] + " " + a["category"]).casefold()]
else:
    filtered_news = news_data

if st.session_state.page == "Home":
    st.html(f"""
    <div style="background:linear-gradient(115deg,#4f46e5 0%,#8146df 52%,#d946a7 100%);padding:30px 34px;border-radius:24px;color:#fff;margin:10px 0 23px;box-shadow:0 14px 34px #6e4be32a">
      <div style="font-size:12px;letter-spacing:2px;font-weight:800;color:#f5eaff">WELCOME BACK, {esc(st.session_state.username.upper())}</div>
      <div style="font-size:30px;line-height:1.2;font-weight:850;color:white;margin:10px 0">Your next big opportunity<br>could start with one story. 🚀</div>
      <div style="font-size:15px;line-height:1.7;color:#f5efff;max-width:700px">Explore technology, AI, education, scholarships and career opportunities selected for curious students.</div>
    </div>
    """)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📰 News stories", len(news_data))
    m2.metric("🤖 Recommended", min(8, len(news_data)))
    m3.metric("🔖 Saved stories", len(st.session_state.bookmarks))
    m4.metric("🎯 Interests", len(selected_interests))
    st.markdown("## ✨ Picked for you")
    st.caption("Recommendations are matched to your selected interests. AI matching falls back to keyword matching if the model is unavailable.")
    recs = recommend_articles(news_data, selected_interests, 5)
    if recs:
        for article in recs:
            render_article(article, "home")
    else:
        st.warning("No RSS stories loaded right now. Check your internet connection and click Refresh news.")
    st.markdown("## 🌈 Explore by topic")
    topic_cols = st.columns(3)
    for i, (cat, url) in enumerate(CATEGORIES.items()):
        with topic_cols[i % 3]:
            st.html(f"""<div style="background:#fff;border:1px solid #e6e8f5;border-radius:14px;padding:16px;margin-bottom:10px"><div style="font-size:22px">{['💻','🤖','📚','💼','👩‍💻','🛡️','🎓','📝','🚀'][i]}</div><div style="font-weight:750;color:#28304b;margin-top:6px">{esc(cat)}</div><div style="font-size:12px;color:#7a8499;margin-top:4px">Explore the latest updates</div></div>""")
            if st.button(f"Explore {cat}", key=f"topic_{i}", use_container_width=True):
                st.session_state.page = "Scholarships" if cat == "Scholarships" else "Jobs & Careers" if cat == "Jobs & Careers" else "All News"
                st.session_state.topic_filter = cat
                st.rerun()

elif st.session_state.page == "AI Recommendations":
    st.markdown("## 🤖 AI Recommendations")
    st.write("Personalized student news ranked against your chosen interests.")
    recs = recommend_articles(news_data, selected_interests, 12)
    if recs:
        for article in recs:
            render_article(article, "ai")
    else:
        st.info("No recommendations are available because the news feeds returned no articles.")

elif st.session_state.page == "All News":
    st.markdown("## 📰 All student news")
    st.caption(f"Showing {len(filtered_news)} matching stories.")
    if filtered_news:
        for article in filtered_news:
            render_article(article, "all")
    else:
        st.info("No matching news found. Try another keyword or refresh the feeds.")

elif st.session_state.page in ("Scholarships", "Jobs & Careers"):
    target = "Scholarships" if st.session_state.page == "Scholarships" else "Jobs & Careers"
    st.markdown(f"## {'🎓' if target == 'Scholarships' else '💼'} {target}")
    st.info("These stories are collected from public RSS feeds. Open the original publisher's page to confirm eligibility, deadlines, requirements and application details.")
    matches = [a for a in news_data if target.casefold() in a["category"].casefold()]
    if not matches:
        terms = ("scholarship", "fellowship", "financial aid") if target == "Scholarships" else ("job", "career", "internship", "hiring")
        matches = [a for a in news_data if any(term in (a["title"] + " " + a["description"]).casefold() for term in terms)]
    if matches:
        for article in matches:
            render_article(article, target.replace(" ", "_"))
    else:
        st.warning("No stories in this category loaded right now. Try Refresh news later.")

elif st.session_state.page == "Saved Articles":
    st.markdown("## 🔖 Your saved articles")
    if st.session_state.bookmarks:
        st.caption("Your saved stories are stored for this account on this computer.")
        for article in list(st.session_state.bookmarks):
            render_article(article, "saved")
            if st.button("🗑️ Remove saved article", key="remove_" + hashlib.md5(article["link"].encode()).hexdigest(), use_container_width=True):
                toggle_bookmark(article)
                st.rerun()
    else:
        st.html("""
        <div style="text-align:center;background:#fff;border:1px dashed #c9c9e7;border-radius:20px;padding:42px 20px;margin-top:18px">
          <div style="font-size:45px">🔖</div><div style="font-size:22px;font-weight:800;color:#303052;margin-top:10px">Your reading list starts here</div>
          <div style="color:#778097;margin-top:8px">Save useful articles and they will appear on this page.</div>
        </div>
        """)

st.markdown("---")
st.markdown("<div style='text-align:center;color:#8991a8;font-size:12px;padding:12px 0'>🎓 <b>StudentAI News</b> · AI-Based Student News Aggregation and Recommendation System<br>Built with Python · Streamlit · RSS · Semantic AI</div>", unsafe_allow_html=True)


import streamlit as st
import sqlite3
import hashlib
import secrets
import hmac
import random
import requests
from datetime import datetime

st.set_page_config(
    page_title="InterviewBuddy AI",
    page_icon="🎯",
    layout="wide"
)

DB_FILE = "users.db"
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"

# ---------- DATABASE ----------

def connect_db():
    return sqlite3.connect(DB_FILE)


def setup_db():
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users(
                username TEXT PRIMARY KEY,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS attempts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                role TEXT,
                subject TEXT,
                level TEXT,
                score INTEGER,
                total INTEGER,
                created_at TEXT
            )
        """)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(),
        bytes.fromhex(salt), 200000
    ).hex()


def create_account(username, password):
    salt = secrets.token_hex(16)
    hashed = hash_password(password, salt)

    try:
        with connect_db() as con:
            con.execute(
                "INSERT INTO users VALUES (?, ?, ?)",
                (username, salt, hashed)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def verify_login(username, password):
    with connect_db() as con:
        user = con.execute(
            "SELECT salt, password_hash FROM users WHERE username=?",
            (username,)
        ).fetchone()

    if not user:
        return False

    salt, saved_hash = user
    return hmac.compare_digest(
        hash_password(password, salt), saved_hash
    )


def reset_password(username, new_password):
    salt = secrets.token_hex(16)
    hashed = hash_password(new_password, salt)

    with connect_db() as con:
        cursor = con.execute(
            "UPDATE users SET salt=?, password_hash=? WHERE username=?",
            (salt, hashed, username)
        )

        return cursor.rowcount > 0


def save_attempt(username, role, subject, level, score, total):
    with connect_db() as con:
        con.execute("""
            INSERT INTO attempts
            (username, role, subject, level, score, total, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            username, role, subject, level, score, total,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))


def get_attempts(username):
    with connect_db() as con:
        return con.execute("""
            SELECT role, subject, level, score, total, created_at
            FROM attempts
            WHERE username=?
            ORDER BY id DESC
        """, (username,)).fetchall()


setup_db()

# ---------- JOB ROLES ----------

ROLE_TOPICS = {
    "Software Developer": ["Python", "Java", "C", "C++", "DSA", "SQL", "DBMS"],
    "Data Analyst": ["Python", "SQL", "Excel", "Aptitude", "DBMS"],
    "Data Engineer": ["Python", "SQL", "DBMS", "DSA"],
    "AI/ML Engineer": ["Python", "SQL", "DSA"],
    "Web Developer": ["JavaScript", "HTML/CSS", "SQL"],
    "Mobile App Developer": ["Java", "Kotlin", "JavaScript", "DSA"],
    "Cybersecurity Analyst": ["Python", "SQL", "Cybersecurity", "Aptitude"],
    "QA / Test Engineer": ["Python", "SQL", "Aptitude"],
    "Cloud Engineer": ["Python", "SQL", "Linux", "Networking"],
    "HR Interview": ["HR", "Aptitude"],
    "Business Analyst": ["SQL", "Excel", "Aptitude", "HR"],
    "DevOps Engineer": ["Python", "Linux", "Networking", "SQL"]
}

ROLE_DESCRIPTIONS = {
    "Software Developer": "Programming, problem-solving, DSA and databases.",
    "Data Analyst": "SQL, spreadsheets, data analysis and reasoning.",
    "Data Engineer": "Python, SQL, databases and data processing.",
    "AI/ML Engineer": "Python, algorithms and AI fundamentals.",
    "Web Developer": "HTML, CSS, JavaScript and databases.",
    "Mobile App Developer": "Programming and mobile application development.",
    "Cybersecurity Analyst": "Security, networking and scripting.",
    "QA / Test Engineer": "Testing concepts, SQL and logical reasoning.",
    "Cloud Engineer": "Linux, networking and cloud fundamentals.",
    "HR Interview": "Communication and behavioral interview questions.",
    "Business Analyst": "SQL, spreadsheets and analytical thinking.",
    "DevOps Engineer": "Linux, scripting, networking and deployment."
}

# ---------- QUIZ BANK ----------
# Format: difficulty, question, options, correct option, explanation

QUIZ_BANK = {
    "Python": [
        ("Beginner", "Which keyword defines a function?",
         ["func", "def", "function", "define"], 1,
         "The def keyword defines a function."),
        ("Beginner", "Which type stores True or False?",
         ["int", "str", "bool", "list"], 2,
         "bool stores Boolean values."),
        ("Intermediate", "What is len([2, 4, 6])?",
         ["2", "3", "6", "Error"], 1,
         "The list contains three items."),
        ("Intermediate", "Which collection stores key-value pairs?",
         ["Tuple", "Set", "Dictionary", "String"], 2,
         "A dictionary stores key-value pairs."),
        ("Advanced", "Average dictionary lookup complexity?",
         ["O(1)", "O(n)", "O(n²)", "O(log n)"], 0,
         "Average lookup is O(1)."),
        ("Advanced", "Which keyword produces generator values?",
         ["return", "yield", "global", "break"], 1,
         "yield produces values from a generator.")
    ],
    "Java": [
        ("Beginner", "Which keyword creates an object?",
         ["make", "new", "class", "object"], 1,
         "The new keyword creates an object."),
        ("Beginner", "What is the usual Java entry-point method?",
         ["start()", "run()", "main()", "init()"], 2,
         "Java programs normally start at main()."),
        ("Intermediate", "Which concept allows multiple implementations?",
         ["Encapsulation", "Polymorphism", "Compilation", "Casting"], 1,
         "Polymorphism allows different implementations."),
        ("Intermediate", "Which collection prevents duplicates?",
         ["List", "Set", "ArrayList", "LinkedList"], 1,
         "A Set stores unique elements."),
        ("Advanced", "Which keyword prevents overriding?",
         ["static", "final", "extends", "import"], 1,
         "A final method cannot be overridden."),
        ("Advanced", "Which structure manages method-call frames?",
         ["Queue", "Stack", "Graph", "Table"], 1,
         "Method calls use stack frames.")
    ],
    "C": [
        ("Beginner", "Which function prints output in C?",
         ["input()", "printf()", "print()", "display()"], 1,
         "printf() prints formatted output."),
        ("Beginner", "Which symbol ends most C statements?",
         [".", ":", ";", ","], 2,
         "A semicolon ends most C statements."),
        ("Intermediate", "Which operator obtains a variable address?",
         ["*", "&", "%", "#"], 1,
         "The & operator obtains an address."),
        ("Intermediate", "Array indexing normally starts at?",
         ["0", "1", "-1", "2"], 0,
         "The first array element has index 0."),
        ("Advanced", "Which function allocates dynamic memory?",
         ["printf()", "malloc()", "strlen()", "fclose()"], 1,
         "malloc() allocates memory."),
        ("Advanced", "What does a pointer store?",
         ["Characters", "Memory address", "Decimal only", "Loop"], 1,
         "A pointer stores a memory address.")
    ],
    "C++": [
        ("Beginner", "Which stream is used for output?",
         ["cin", "cout", "print", "output"], 1,
         "cout is the standard output stream."),
        ("Beginner", "Which symbol ends most statements?",
         [".", ":", ";", ","], 2,
         "A semicolon ends most statements."),
        ("Intermediate", "Same function name with different parameters?",
         ["Overloading", "Casting", "Linking", "Hiding"], 0,
         "Function overloading uses different parameters."),
        ("Intermediate", "Which access level supports derived-class access?",
         ["private", "protected", "global", "none"], 1,
         "protected members are accessible in derived classes."),
        ("Advanced", "Virtual functions support which concept?",
         ["Runtime polymorphism", "Tokenization", "Preprocessing", "Iteration"], 0,
         "Virtual functions support runtime polymorphism."),
        ("Advanced", "Which technique manages resources by object lifetime?",
         ["RAII", "goto", "extern", "macro"], 0,
         "RAII ties resources to object lifetime.")
    ],
    "JavaScript": [
        ("Beginner", "Which keyword declares a reassignable block variable?",
         ["let", "define", "dim", "int"], 0,
         "let declares a block-scoped variable."),
        ("Beginner", "Which symbol starts a single-line comment?",
         ["##", "//", "<!--", "**"], 1,
         "// starts a single-line comment."),
        ("Intermediate", "Which array method transforms each item?",
         ["map()", "push()", "pop()", "shift()"], 0,
         "map() creates a transformed array."),
        ("Intermediate", "What does === check?",
         ["Strict equality", "Assignment", "Addition", "Type only"], 0,
         "=== checks value and type."),
        ("Advanced", "What does an async function return?",
         ["Promise", "CSS file", "Number only", "Database"], 0,
         "An async function returns a Promise."),
        ("Advanced", "Which method parses JSON text?",
         ["JSON.parse()", "JSON.stringify()", "JSON.write()", "JSON.open()"], 0,
         "JSON.parse() converts JSON text to a value.")
    ],
    "SQL": [
        ("Beginner", "Which command retrieves data?",
         ["GET", "SELECT", "OPEN", "FETCH ALL"], 1,
         "SELECT retrieves data."),
        ("Beginner", "Which clause filters rows?",
         ["ORDER BY", "WHERE", "GROUP BY", "JOIN"], 1,
         "WHERE filters rows."),
        ("Intermediate", "Which function counts rows?",
         ["TOTAL()", "COUNT()", "NUMBER()", "SIZE()"], 1,
         "COUNT() counts rows or non-NULL values."),
        ("Intermediate", "Which join returns matching rows?",
         ["INNER JOIN", "CROSS JOIN", "No join", "CREATE JOIN"], 0,
         "INNER JOIN returns matching rows."),
        ("Advanced", "Which clause filters grouped results?",
         ["WHERE", "HAVING", "ORDER BY", "DISTINCT"], 1,
         "HAVING filters groups."),
        ("Advanced", "What is a database index mainly used for?",
         ["Faster lookups", "Encrypting rows", "Removing tables", "Creating users"], 0,
         "Indexes can improve lookup speed.")
    ],
    "DSA": [
        ("Beginner", "Which data structure follows FIFO?",
         ["Stack", "Queue", "Tree", "Graph"], 1,
         "FIFO means First In, First Out."),
        ("Beginner", "Which data structure follows LIFO?",
         ["Queue", "Stack", "Graph", "Tree"], 1,
         "LIFO means Last In, First Out."),
        ("Intermediate", "Binary search complexity on a sorted array?",
         ["O(n)", "O(log n)", "O(n²)", "O(1) always"], 1,
         "Binary search halves the search range."),
        ("Intermediate", "Which traversal visits left, root, right?",
         ["Preorder", "Inorder", "Postorder", "Level order"], 1,
         "Inorder is left-root-right."),
        ("Advanced", "Average hash-table lookup complexity?",
         ["O(n²)", "O(log n)", "O(1)", "O(n log n)"], 2,
         "Average hash lookup is O(1)."),
        ("Advanced", "Shortest paths with nonnegative edge weights?",
         ["Binary search", "Dijkstra", "Bubble sort", "Selection sort"], 1,
         "Dijkstra handles nonnegative edge weights.")
    ],
    "DBMS": [
        ("Beginner", "What does DBMS stand for?",
         ["Data Backup Service", "Database Management System",
          "Digital Base Machine", "Data Binary Storage"], 1,
         "DBMS means Database Management System."),
        ("Beginner", "Which key uniquely identifies a row?",
         ["Foreign key", "Primary key", "Duplicate key", "Optional key"], 1,
         "A primary key uniquely identifies a row."),
        ("Intermediate", "Normalization reduces what?",
         ["Data redundancy", "All queries", "All keys", "Data meaning"], 0,
         "Normalization reduces redundancy."),
        ("Intermediate", "A foreign key references which key?",
         ["Primary or unique key", "Password", "Table name only", "Index name"], 0,
         "Foreign keys reference a candidate key."),
        ("Advanced", "ACID consistency means what?",
         ["Constraints remain satisfied", "No data stored",
          "Instant queries", "No joins"], 0,
         "Consistency preserves database rules."),
        ("Advanced", "Which normal form addresses transitive dependencies?",
         ["1NF", "2NF", "3NF", "None"], 2,
         "Third normal form addresses relevant transitive dependencies.")
    ],
    "Aptitude": [
        ("Beginner", "What is 15% of 200?",
         ["15", "20", "30", "45"], 2, "15% of 200 is 30."),
        ("Beginner", "Average of 4, 6 and 8?",
         ["5", "6", "7", "8"], 1, "Their average is 6."),
        ("Intermediate", "120 km in 2 hours: average speed?",
         ["40 km/h", "50 km/h", "60 km/h", "80 km/h"], 2,
         "Speed equals distance divided by time."),
        ("Intermediate", "A 500 item has a 10% discount. Sale price?",
         ["450", "475", "490", "400"], 0,
         "The discount is 50, so the price is 450."),
        ("Advanced", "Probability of two heads in two fair coin tosses?",
         ["1/2", "1/3", "1/4", "3/4"], 2,
         "One of four outcomes is HH."),
        ("Advanced", "5 workers finish in 12 days. 10 workers take?",
         ["3 days", "6 days", "12 days", "24 days"], 1,
         "Twice the workers take half the time.")
    ],
    "HR": [
        ("Beginner", "What belongs in a good self-introduction?",
         ["Relevant education and skills", "Passwords",
          "Private details", "Only hobbies"], 0,
         "Summarize relevant education, skills and goals."),
        ("Beginner", "What if you do not know an answer?",
         ["Guess", "Be honest and explain how you would learn",
          "Ignore the interviewer", "Change the topic"], 1,
         "Honesty and willingness to learn matter."),
        ("Intermediate", "What does STAR stand for?",
         ["Situation Task Action Result", "Skill Test Aim Review",
          "Start Talk Answer Repeat", "System Task Apply Run"], 0,
         "STAR structures behavioral examples."),
        ("Intermediate", "How should you discuss a weakness?",
         ["Describe improvement steps", "Claim no weaknesses",
          "Blame others", "Avoid answering"], 0,
         "Explain the steps you take to improve."),
        ("Advanced", "How should you describe team conflict?",
         ["Blame others", "Explain communication and resolution",
          "Reveal secrets", "Deny all conflict"], 1,
         "Show constructive communication."),
        ("Advanced", "What makes a strong behavioral example?",
         ["Truthful example and outcome", "Unrelated story",
          "General claims", "Invented achievement"], 0,
         "Specific truthful examples demonstrate skills.")
    ],
    "HTML/CSS": [
        ("Beginner", "Which HTML tag creates a hyperlink?",
         ["link", "a", "href", "url"], 1,
         "The a element creates a hyperlink."),
        ("Beginner", "Which CSS property changes text color?",
         ["font-style", "color", "background-image", "display"], 1,
         "The color property sets text color."),
        ("Intermediate", "Which CSS system suits one-dimensional layouts?",
         ["Flexbox", "SQL", "JSON", "DOM"], 0,
         "Flexbox is a one-dimensional layout system."),
        ("Intermediate", "What does HTML stand for?",
         ["HyperText Markup Language", "HighText Machine Language",
          "Home Tool Markup Language", "Hyperlinks Text Management"], 0,
         "HTML means HyperText Markup Language."),
        ("Advanced", "CSS specificity helps resolve what?",
         ["Competing style rules", "Database connections",
          "Python execution", "File creation"], 0,
         "Specificity helps choose between competing declarations."),
        ("Advanced", "Which attribute provides image alternative text?",
         ["title", "alt", "srcset", "role"], 1,
         "alt provides a text alternative.")
    ],
    "Kotlin": [
        ("Beginner", "Which keyword declares a read-only reference?",
         ["var", "val", "let", "constvar"], 1, "val cannot be reassigned."),
        ("Beginner", "Which keyword declares a mutable variable?",
         ["val", "var", "fun", "class"], 1, "var allows reassignment."),
        ("Intermediate", "Which keyword declares a function?",
         ["def", "func", "fun", "method"], 2, "Kotlin uses fun."),
        ("Intermediate", "Which symbol marks a nullable type?",
         ["!", "?", "#", "&"], 1, "A question mark marks a nullable type."),
        ("Advanced", "Coroutines are used for what?",
         ["Asynchronous programming", "Styling only", "SQL indexing", "Classes only"], 0,
         "Coroutines support asynchronous tasks."),
        ("Advanced", "Which Kotlin construct supports branching?",
         ["when", "repeat only", "println", "package"], 0,
         "when provides conditional branching.")
    ],
    "Cybersecurity": [
        ("Beginner", "What is phishing?",
         ["A deceptive attempt to steal information", "A backup",
          "A sorting algorithm", "A database join"], 0,
         "Phishing tricks people into sharing sensitive information."),
        ("Beginner", "What does MFA add to account security?",
         ["Multiple verification factors", "Longer username",
          "Public access", "Fewer checks"], 0,
         "MFA uses multiple verification factors."),
        ("Intermediate", "What is least privilege?",
         ["Only necessary access", "Everyone gets admin",
          "Disable all accounts", "Share passwords"], 0,
         "Users should receive only the permissions they need."),
        ("Intermediate", "Why are software updates important?",
         ["They can fix vulnerabilities", "They always remove data",
          "They disable encryption", "They replace passwords"], 0,
         "Updates often patch known vulnerabilities."),
        ("Advanced", "A common use of a cryptographic hash?",
         ["Integrity checks", "Recover every password", "Brightness", "Routing only"], 0,
         "Hashes support integrity checks and password verification."),
        ("Advanced", "What is defense in depth?",
         ["Multiple security layers", "One password everywhere",
          "No monitoring", "One control only"], 0,
         "Multiple controls reduce reliance on one defense.")
    ],
    "Linux": [
        ("Beginner", "Which command lists files?",
         ["ls", "dirshow", "files", "listall"], 0, "ls lists directory entries."),
        ("Beginner", "Which command prints the current directory?",
         ["where", "pwd", "cd", "home"], 1, "pwd prints the working directory."),
        ("Intermediate", "Which command changes file permissions?",
         ["chmod", "chdir", "permshow", "mvperm"], 0,
         "chmod changes permissions."),
        ("Intermediate", "Which command searches text patterns?",
         ["grep", "touch", "mkdir", "clear"], 0, "grep searches for matching patterns."),
        ("Advanced", "What does a shell pipe do?",
         ["Passes output to another command", "Deletes a directory",
          "Changes password", "Reboots"], 0,
         "A pipe connects one command's output to another's input."),
        ("Advanced", "What does a process ID identify?",
         ["Running process", "File extension", "Password", "Cable"], 0,
         "A PID identifies a process.")
    ],
    "Networking": [
        ("Beginner", "What does IP stand for?",
         ["Internet Protocol", "Internal Program", "Input Process", "Interface Port"], 0,
         "IP means Internet Protocol."),
        ("Beginner", "Which device forwards packets between networks?",
         ["Router", "Keyboard", "Printer", "Monitor"], 0,
         "Routers forward packets between networks."),
        ("Intermediate", "Which protocol is used for secure web browsing?",
         ["HTTPS", "FTP", "Telnet", "SMTP"], 0,
         "HTTPS protects HTTP traffic using TLS."),
        ("Intermediate", "What does DNS resolve?",
         ["Domain names to network records", "Images to audio",
          "Passwords", "Files to folders"], 0,
         "DNS resolves domain names to records such as IP addresses."),
        ("Advanced", "Which transport protocol provides reliable ordered delivery?",
         ["TCP", "UDP", "ARP", "ICMP"], 0,
         "TCP provides reliable, ordered delivery."),
        ("Advanced", "What is a subnet mask used for?",
         ["Separating network and host portions", "Encrypting files",
          "Naming websites", "Measuring CPU speed"], 0,
         "A subnet mask identifies network and host bits.")
    ],
    "Excel": [
        ("Beginner", "Which symbol starts an Excel formula?",
         ["=", "#", "@", "&"], 0, "Formulas begin with equals."),
        ("Beginner", "Which function adds values?",
         ["SUM", "COUNT", "TEXT", "LEFT"], 0, "SUM adds values."),
        ("Intermediate", "Which function searches a range for a matching value?",
         ["XLOOKUP", "UPPER", "LEN", "NOW"], 0,
         "XLOOKUP searches and returns a matching result."),
        ("Intermediate", "What is a PivotTable used for?",
         ["Summarizing data", "Writing operating systems",
          "Encrypting disks", "Network routing"], 0,
         "PivotTables summarize data interactively."),
        ("Advanced", "What does $A$1 do when copied?",
         ["Locks row and column", "Changes both", "Deletes formula", "Converts to text"], 0,
         "Dollar signs lock the column and row."),
        ("Advanced", "Which function tests a condition?",
         ["IF", "SUM", "TRIM", "CONCAT"], 0,
         "IF returns results based on a condition.")
    ]
}
# ---------- SESSION STATE ----------

defaults = {
    "user": None,
    "auth_page": "login",
    "navigation": "Dashboard",
    "selected_role": "Software Developer",
    "selected_subject": "Python",
    "selected_level": "Beginner",
    "quiz_questions": [],
    "quiz_run_id": 0,
    "quiz_result": None,
    "chat_messages": []
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def go_to(page):
    st.session_state.navigation = page


def logout():
    st.session_state.user = None
    st.session_state.auth_page = "login"
    st.session_state.navigation = "Dashboard"
    st.session_state.quiz_questions = []
    st.session_state.quiz_result = None
    st.session_state.chat_messages = []

# ---------- DESIGN ----------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#0b1024,#121b3a,#21164a);
    color: #f8fafc;
}
[data-testid="stSidebar"] { background: #080f23; }
h1,h2,h3,p,label { color: #f8fafc; }
div[data-testid="stMetric"] {
    background: #1c2b52;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid #344779;
}
.stButton button {
    border-radius: 10px;
    font-weight: 600;
    min-height: 42px;
}
</style>
""", unsafe_allow_html=True)
# ---------- LOGIN / SIGN UP ----------

if st.session_state.user is None:

    if st.session_state.auth_page == "login":

        st.title("🔐 Login")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            login_clicked = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if login_clicked:
            name = username.strip()

            if not name or not password:
                st.error("Please enter username and password.")

            elif verify_login(name, password):
                st.session_state.user = name
                st.session_state.navigation = "Dashboard"
                st.rerun()

            else:
                st.error("Username or password is incorrect.")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔑 Forgot Password?", use_container_width=True):
                st.session_state.auth_page = "forgot_password"
                st.rerun()

        with col2:
            if st.button("✨ Create an account", use_container_width=True):
                st.session_state.auth_page = "signup"
                st.rerun()

    elif st.session_state.auth_page == "forgot_password":

        st.title("🔑 Reset Password")
        st.write("Enter your username and create a new password.")

        with st.form("reset_password_form"):
            username = st.text_input("Username")
            new_password = st.text_input("New password", type="password")
            confirm_password = st.text_input("Confirm new password", type="password")

            reset_clicked = st.form_submit_button("Reset Password", use_container_width=True)

        if reset_clicked:
            name = username.strip()

            if not name:
                st.error("Please enter your username.")
            elif len(new_password) < 8:
                st.error("Password must have at least 8 characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif reset_password(name, new_password):
                st.success("Password reset successfully!")
                st.session_state.auth_page = "login"
                st.rerun()
            else:
                st.error("Username not found.")

        if st.button("🔐 Back to Login", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()

    else:

        st.title("✨ Create Account")

        with st.form("signup_form"):
            new_username = st.text_input("Choose a username")
            new_password = st.text_input("Create password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")

            signup_clicked = st.form_submit_button("Create Account", use_container_width=True)

        if signup_clicked:
            name = new_username.strip()

            if len(name) < 3:
                st.error("Username must have at least 3 characters.")
            elif len(new_password) < 8:
                st.error("Password must have at least 8 characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif create_account(name, new_password):
                st.success("Account created successfully!")
                st.session_state.auth_page = "login"
                st.rerun()
            else:
                st.error("That username already exists.")

        if st.button("🔐 Back to Login", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()

    st.stop()


# ---------- MAIN APP ----------

with st.sidebar:
    st.title("🤖 InterviewBuddy AI")
    st.caption("Practise • Improve • Get ready")
    st.write(f"Hi, **{st.session_state.user}**!")

    st.radio(
        "NAVIGATION",
        [
            "Dashboard",
            "Job Preparation",
            "Quiz Arena",
            "AI Interview Chat",
            "My Progress"
        ],
        key="navigation"
    )

    st.divider()

    st.button(
        "Log out",
        on_click=logout,
        use_container_width=True
    )

page = st.session_state.navigation
# ---------- DASHBOARD ----------

if page == "Dashboard":
    st.title("👋 Welcome to InterviewBuddy AI")
    st.write("Your personal interview preparation space.")

    history = get_attempts(st.session_state.user)
    total_questions = sum(row[4] for row in history)
    total_correct = sum(row[3] for row in history)
    accuracy = round(total_correct / total_questions * 100) if total_questions else 0

    a, b, c = st.columns(3)
    a.metric("Quiz Attempts", len(history))
    b.metric("Questions Answered", total_questions)
    c.metric("Overall Accuracy", f"{accuracy}%")

    st.markdown("## 🚀 Start your preparation")

    a, b = st.columns(2)
    with a:
        st.markdown("### 💼 Job Preparation")
        st.write("Explore job roles and recommended skills.")
        st.button("Explore Job Roles", on_click=go_to,
                  args=("Job Preparation",), use_container_width=True)

    with b:
        st.markdown("### 🧠 Quiz Arena")
        st.write("Test your knowledge at three difficulty levels.")
        st.button("Start a Quiz", on_click=go_to,
                  args=("Quiz Arena",), use_container_width=True)

    a, b = st.columns(2)
    with a:
        st.markdown("### 🤖 AI Interview Coach")
        st.write("Practise interview answers with Ollama.")
        st.button("Practise with AI", on_click=go_to,
                  args=("AI Interview Chat",), use_container_width=True)

    with b:
        st.markdown("### 📊 My Progress")
        st.write("View your saved quiz scores.")
        st.button("View My Progress", on_click=go_to,
                  args=("My Progress",), use_container_width=True)

# ---------- JOB PREPARATION ----------

elif page == "Job Preparation":
    st.title("💼 Explore Job Roles")
    st.write("Choose a career path and view its recommended topics.")

    roles = list(ROLE_TOPICS.keys())
    role = st.selectbox(
        "Select your target job role",
        roles,
        index=roles.index(st.session_state.selected_role)
        if st.session_state.selected_role in roles else 0,
        key="job_role"
    )
    st.session_state.selected_role = role

    st.subheader(f"🎯 {role}")
    st.write(ROLE_DESCRIPTIONS[role])
    st.markdown("### Recommended preparation topics")

    cols = st.columns(3)
    for i, topic in enumerate(ROLE_TOPICS[role]):
        with cols[i % 3]:
            st.markdown(f"📘 **{topic}**")
            st.caption("Study concepts and practise questions.")

    level = st.selectbox(
        "Preparation level",
        ["Beginner", "Intermediate", "Advanced"],
        index=["Beginner", "Intermediate", "Advanced"].index(
            st.session_state.selected_level
        ),
        key="preparation_level"
    )
    st.session_state.selected_level = level

    st.button("🧠 Practise with a Quiz", on_click=go_to,
              args=("Quiz Arena",), use_container_width=True)
    st.button("🤖 Practise with AI", on_click=go_to,
              args=("AI Interview Chat",), use_container_width=True)

# ---------- QUIZ ARENA ----------

elif page == "Quiz Arena":
    st.title("🧠 Quiz Arena")
    st.write("Choose a role, subject and difficulty.")

    roles = list(ROLE_TOPICS.keys())

    role = st.selectbox(
        "Job role",
        roles,
        index=roles.index(st.session_state.selected_role)
        if st.session_state.selected_role in roles else 0,
        key="quiz_role"
    )

    st.session_state.selected_role = role

    topics = ROLE_TOPICS[role]

    subjects = ["All recommended topics"] + topics

    previous_subject = st.session_state.selected_subject

    if previous_subject not in subjects:
        previous_subject = "All recommended topics"

    subject = st.selectbox(
        "Language / subject",
        subjects,
        index=subjects.index(previous_subject),
        key="quiz_subject"
    )

    levels = ["Beginner", "Intermediate", "Advanced"]

    level = st.selectbox(
        "Difficulty",
        levels,
        index=levels.index(st.session_state.selected_level),
        key="quiz_level"
    )

    st.session_state.selected_subject = subject
    st.session_state.selected_level = level

    # ---------- GENERATE QUIZ ----------

    if st.button("🎲 Generate Quiz", use_container_width=True):

        selected_topics = (
            topics
            if subject == "All recommended topics"
            else [subject]
        )

        questions = []

        for topic in selected_topics:
            for item in QUIZ_BANK.get(topic, []):

                if item[0] == level:
                    questions.append({
                        "topic": topic,
                        "question": item[1],
                        "options": item[2],
                        "correct": item[3],
                        "explanation": item[4]
                    })

        random.shuffle(questions)

        st.session_state.quiz_questions = questions[:10]
        st.session_state.quiz_run_id += 1
        st.session_state.quiz_result = None

        if len(questions) == 0:
            st.warning("No questions are available for this selection.")

        elif len(questions) < 10:
            st.warning(
                f"Only {len(questions)} questions are available "
                f"for this selection."
            )

    # ---------- DISPLAY QUIZ ----------

    quiz = st.session_state.quiz_questions

    if quiz:

        st.subheader(f"{role} • {level}")

        with st.form(
            f"quiz_form_{st.session_state.quiz_run_id}"
        ):

            answers = {}

            for i, q in enumerate(quiz):

                st.markdown(
                    f"**Q{i + 1}. [{q['topic']}] {q['question']}**"
                )

                answers[i] = st.radio(
                    f"Answer {i + 1}",
                    q["options"],
                    index=None,
                    key=f"answer_{st.session_state.quiz_run_id}_{i}",
                    label_visibility="collapsed"
                )

            submitted = st.form_submit_button(
                "Submit Quiz",
                use_container_width=True
            )

        # ---------- CHECK ANSWERS ----------

        if submitted:

            score = 0
            reviews = []

            for i, q in enumerate(quiz):

                correct_answer = q["options"][q["correct"]]
                chosen = answers[i]

                is_correct = chosen == correct_answer

                if is_correct:
                    score += 1

                reviews.append({
                    "question": q["question"],
                    "chosen": chosen or "Not answered",
                    "correct_answer": correct_answer,
                    "correct": is_correct,
                    "explanation": q["explanation"]
                })

            st.session_state.quiz_result = {
                "score": score,
                "total": len(quiz),
                "reviews": reviews
            }

            save_attempt(
                st.session_state.user,
                role,
                subject,
                level,
                score,
                len(quiz)
            )

    # ---------- QUIZ RESULT ----------

    result = st.session_state.quiz_result

    if result:

        score = result["score"]
        total = result["total"]

        percent = (
            round(score / total * 100)
            if total
            else 0
        )

        st.divider()

        st.header("🏆 Quiz Results")

        a, b = st.columns(2)

        a.metric(
            "Your Score",
            f"{score}/{total}"
        )

        b.metric(
            "Accuracy",
            f"{percent}%"
        )

        st.progress(percent / 100)

        if percent >= 80:
            st.success(
                "Excellent work! Keep practising."
            )

        elif percent >= 50:
            st.info(
                "Good effort. Review the explanations."
            )

        else:
            st.warning(
                "Keep learning and try again."
            )

        st.subheader("Answer Review")

        for i, review in enumerate(
            result["reviews"], 1
        ):

            label = (
                "Correct ✅"
                if review["correct"]
                else "Review 📘"
            )

            with st.expander(
                f"Question {i}: {label}"
            ):

                st.write(
                    review["question"]
                )

                st.write(
                    "Your answer:",
                    review["chosen"]
                )

                st.write(
                    "Correct answer:",
                    review["correct_answer"]
                )

                st.write(
                    "Explanation:",
                    review["explanation"]
                )
# ---------- AI INTERVIEW CHAT ----------

elif page == "AI Interview Chat":
    st.title("🤖 AI Interview Coach")
    st.write("Ask questions, practise answers and get explanations.")

    roles = list(ROLE_TOPICS.keys())
    role = st.selectbox(
        "Interview role",
        roles,
        index=roles.index(st.session_state.selected_role)
        if st.session_state.selected_role in roles else 0,
        key="chat_role"
    )
    st.session_state.selected_role = role

    levels = ["Beginner", "Intermediate", "Advanced"]
    level = st.selectbox(
        "Interview difficulty",
        levels,
        index=levels.index(st.session_state.selected_level),
        key="chat_level"
    )
    st.session_state.selected_level = level

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask your interview coach...")

    if prompt:
        st.session_state.chat_messages.append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    messages = [{
                        "role": "system",
                        "content": (
                            f"You are InterviewBuddy AI, an interview coach for {role}. "
                            f"Difficulty: {level}. Help students prepare with accurate "
                            "explanations, practice questions, sample answers and feedback."
                        )
                    }] + st.session_state.chat_messages[-20:]

                    response = requests.post(
                        OLLAMA_URL,
                        json={
                            "model": OLLAMA_MODEL,
                            "messages": messages,
                            "stream": False
                        },
                        timeout=180
                    )
                    response.raise_for_status()
                    answer = response.json()["message"]["content"]
                    st.markdown(answer)

                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": answer}
                    )

                except requests.RequestException:
                    st.error(
                        "Cannot connect to Ollama. Open a terminal and run "
                        "`ollama run llama3.2:3b`. Wait for it to start, "
                        "then try again."
                    )
                    st.session_state.chat_messages.pop()

    if st.button("Clear Chat"):
        st.session_state.chat_messages = []
        st.rerun()

# ---------- MY PROGRESS ----------

elif page == "My Progress":
    st.title("📊 My Progress")
    history = get_attempts(st.session_state.user)

    if not history:
        st.info("No quiz attempts yet. Complete a quiz to see your progress.")
    else:
        total_questions = sum(row[4] for row in history)
        total_correct = sum(row[3] for row in history)
        accuracy = round(total_correct / total_questions * 100) if total_questions else 0

        a, b, c = st.columns(3)
        a.metric("Completed Quizzes", len(history))
        b.metric("Questions Answered", total_questions)
        c.metric("Overall Accuracy", f"{accuracy}%")

        st.subheader("Recent Quiz History")
        for role, subject, level, score, total, created_at in history:
            with st.expander(f"{role} • {subject} • {created_at}"):
                st.write("Difficulty:", level)
                st.write("Score:", f"{score}/{total}")
                percent = round(score / total * 100) if total else 0
                st.write("Accuracy:", f"{percent}%")

st.caption("InterviewBuddy AI • Local learning prototype")
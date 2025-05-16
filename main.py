import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv
from tabulate import tabulate
import traceback

#Kobe Marco Olaguir
# Load environment variables
load_dotenv()

# Database connection string
DB_CONN = os.getenv("DATABASE_URL") or "postgresql://exam_44il_user:Nm5AvFiRxC16n0Nx2CHskEkZoHc227Rz@dpg-d0jhhvmuk2gs73btd7vg-a.oregon-postgres.render.com/exam_44il"
# Initialize SQLAlchemy engine and inspector
sql_engine = create_engine(DB_CONN, client_encoding='utf8')
db_conn = sql_engine.connect()
db_inspector = inspect(sql_engine)

# --- Database Table Setup ---
def setup_tables():
    """Create required tables if they do not exist."""
    try:
        db_conn.execute(text('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                task VARCHAR(255) NOT NULL,
                deadline VARCHAR(255) NOT NULL,
                username VARCHAR(255) NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS olaguir ();
        '''))
        db_conn.commit()
    except Exception:
        print("[DB INIT ERROR]", traceback.format_exc())
        db_conn.rollback()

setup_tables()

# --- Startup Data Printout ---
def print_startup_info():
    print("[DB TABLES]")
    for tbl in db_inspector.get_table_names():
        print(f"  * {tbl}")
    print("\n[USERS]")
    try:
        res = db_conn.execute(text("SELECT * FROM users"))
        user_list = [dict(row) for row in res.mappings()]
        print(tabulate(user_list, headers="keys", tablefmt="fancy_grid"))
    except Exception:
        print("[USER QUERY ERROR]", traceback.format_exc())
        db_conn.rollback()
    print("\n[TASKS]")
    try:
        res = db_conn.execute(text("SELECT * FROM tasks"))
        task_list = [dict(row) for row in res.mappings()]
        print(tabulate(task_list, headers="keys", tablefmt="fancy_grid"))
    except Exception:
        print("[TASK QUERY ERROR]", traceback.format_exc())
        db_conn.rollback()

print_startup_info()

# --- FastAPI App Setup ---
api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---
class UserSchema(BaseModel):
    username: str
    password: str

class TaskSchema(BaseModel):
    task: str
    deadline: str
    user: str

# --- API Endpoints ---
@api.post("/login/")
async def login_user(payload: UserSchema):
    """Authenticate user credentials."""
    try:
        query = text("SELECT * FROM users WHERE username = :uname AND password = :pwd;")
        result = db_conn.execute(query.bindparams(uname=payload.username, pwd=payload.password))
        if not result.mappings().all():
            return {"status": "User Not Found!"}
        return {"status": "Logged in"}
    except Exception:
        print("[LOGIN ERROR]", traceback.format_exc())
        db_conn.rollback()
        raise HTTPException(status_code=500, detail="Login failed.")

@api.post("/create_user/")
async def register_user(payload: UserSchema):
    """Register a new user if username is unique."""
    try:
        exists = db_conn.execute(text("SELECT 1 FROM users WHERE username = :uname;").bindparams(uname=payload.username))
        if exists.mappings().all():
            raise HTTPException(status_code=400, detail="User already exists!")
        db_conn.execute(text("INSERT INTO users (username, password) VALUES (:uname, :pwd);").bindparams(uname=payload.username, pwd=payload.password))
        db_conn.commit()
        # Return all users
        res = db_conn.execute(text("SELECT * FROM users"))
        user_list = [dict(row) for row in res.mappings()]
        return {"status": "User Created!", "users": user_list}
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        print("[CREATE USER ERROR]", traceback.format_exc())
        db_conn.rollback()
        raise HTTPException(status_code=500, detail="User creation failed.")

@api.post("/create_task/")
async def add_task(payload: TaskSchema):
    """Add a new task for a user if not duplicate."""
    try:
        user_exists = db_conn.execute(text("SELECT 1 FROM users WHERE username = :uname;").bindparams(uname=payload.user))
        if not user_exists.mappings().all():
            return {"status": "User Not Found!"}
        # Check for duplicate
        dup = db_conn.execute(text("""
            SELECT 1 FROM tasks WHERE task = :tsk AND deadline = :dline AND username = :uname;
        """).bindparams(tsk=payload.task, dline=payload.deadline, uname=payload.user))
        if dup.mappings().all():
            return {"status": "Duplicate Task — Not Added."}
        db_conn.execute(text("""
            INSERT INTO tasks (task, deadline, username) VALUES (:tsk, :dline, :uname);
        """).bindparams(tsk=payload.task, dline=payload.deadline, uname=payload.user))
        db_conn.commit()
        # Return all tasks for user
        res = db_conn.execute(text("SELECT id, task, deadline, username FROM tasks WHERE username = :uname").bindparams(uname=payload.user))
        task_list = [dict(row) for row in res.mappings()]
        return {"status": "Task Created!", "tasks": task_list}
    except Exception:
        print("[CREATE TASK ERROR]", traceback.format_exc())
        db_conn.rollback()
        raise HTTPException(status_code=500, detail="Task creation failed.")

@api.get("/get_tasks/")
async def fetch_tasks(username: str):
    """Retrieve all tasks for a given user."""
    try:
        user_exists = db_conn.execute(text("SELECT 1 FROM users WHERE username = :uname;").bindparams(uname=username))
        if not user_exists.mappings().all():
            return {"status": "User Not Found!"}
    except Exception:
        print("[USER CHECK ERROR]", traceback.format_exc())
        db_conn.rollback()
        return {"status": "Error checking user!"}
    try:
        res = db_conn.execute(text("SELECT task, deadline FROM tasks WHERE username = :uname;").bindparams(uname=username))
        task_list = [dict(row) for row in res.mappings()]
        return {"tasks": task_list}
    except Exception:
        print("[FETCH TASKS ERROR]", traceback.format_exc())
        db_conn.rollback()
        return {"status": "Error fetching tasks!"}
import requests
from bs4 import BeautifulSoup
import discord
import asyncio
import hashlib
import os
import json
import logging
from dotenv import load_dotenv
load_dotenv()

# === CONFIG ===
LOGIN_URL = 'https://lms.kiet.edu.pk/kietlms/login/index.php'
GRADE_URL = 'https://lms.kiet.edu.pk/kietlms/my/Student_reports/Grade_History.php'
CHECK_INTERVAL = 300
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')  # from Render environment
CREDENTIALS_FILE = 'user_credentials.json'

# === Logging ===
logging.basicConfig(
    filename='grade_watcher.log',
    filemode='a',
    format='[%(asctime)s] %(levelname)s: %(message)s',
    level=logging.INFO
)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

sessions = {}
last_check_time = 0

# === Credentials Handling ===
def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_credentials(creds):
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(creds, f)

# === LMS Login ===
def login(user_id, username, password):
    session = requests.Session()
    try:
        login_page = session.get(LOGIN_URL, verify=False)
        soup = BeautifulSoup(login_page.text, 'html.parser')
        logintoken = soup.find('input', {'name': 'logintoken'})['value']

        payload = {
            'username': username,
            'password': password,
            'logintoken': logintoken
        }

        response = session.post(LOGIN_URL, data=payload, verify=False)
        if 'Dashboard' in response.text or 'My courses' in response.text:
            sessions[user_id] = session
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"[Login Error] User {user_id}: {e}")
        return False

# === Fetch Grades ===
def fetch_grade_html(user_id):
    session = sessions.get(user_id)
    try:
        response = session.get(GRADE_URL, verify=False)
        if "Login" in response.text or "logintoken" in response.text:
            creds = load_credentials()
            if str(user_id) in creds and login(user_id, creds[str(user_id)]['username'], creds[str(user_id)]['password']):
                response = sessions[user_id].get(GRADE_URL, verify=False)
            else:
                return ''
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"[Fetch Error] User {user_id}: {e}")
        return ''

def extract_grades(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='table_main')
    rows = table.find_all('tr')[1:] if table else []
    grades = []
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 6:
            course = cols[3].text.strip()
            grade = cols[5].text.strip()
            grades.append((course, grade))
    return grades

def get_grade_diff(old, new):
    changed = []
    for course, grade in new:
        if course not in dict(old) or dict(old)[course] != grade:
            changed.append(f"{course}: {grade}")
    return changed

def user_data_files(user_id):
    return {
        'hash': f'{user_id}_hash.txt',
        'cache': f'{user_id}_grades.json'
    }

def load_previous_hash(user_id):
    path = user_data_files(user_id)['hash']
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read().strip()
    return ''

def save_current_hash(user_id, h):
    with open(user_data_files(user_id)['hash'], 'w') as f:
        f.write(h)

def load_previous_grades(user_id):
    path = user_data_files(user_id)['cache']
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

def save_current_grades(user_id, grades):
    with open(user_data_files(user_id)['cache'], 'w') as f:
        json.dump(dict(grades), f)

# === Watcher Task ===
async def start_grade_watcher(user_id):
    await client.wait_until_ready()
    user = await client.fetch_user(user_id)

    last_hash = load_previous_hash(user_id)
    prev_grades = load_previous_grades(user_id)

    while not client.is_closed():
        html = fetch_grade_html(user_id)
        if html:
            grades = extract_grades(html)
            table_str = json.dumps(grades)
            current_hash = hashlib.sha256(table_str.encode()).hexdigest()

            if current_hash != last_hash:
                changed = get_grade_diff(prev_grades.items(), grades)
                message = "📢 **New grade(s) detected!**\n" + "\n".join(changed)
                await user.send(message)

                save_current_hash(user_id, current_hash)
                save_current_grades(user_id, grades)
                last_hash = current_hash
                prev_grades = dict(grades)

        await asyncio.sleep(CHECK_INTERVAL)

# === Discord Events ===
@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    logging.info(f'Bot online: {client.user}')

@client.event
async def on_message(message):
    global last_check_time
    if message.author == client.user:
        return

    if message.content.lower().startswith('!register'):
        parts = message.content.split()
        if len(parts) != 3:
            await message.author.send("❌ Usage: !register <student_id> <password>")
            return

        username, password = parts[1], parts[2]
        user_id = message.author.id

        if login(user_id, username, password):
            creds = load_credentials()
            creds[str(user_id)] = {"username": username, "password": password}
            save_credentials(creds)

            await message.author.send('✅ Registered! Grade watcher started.')
            await start_grade_watcher(user_id)
        else:
            await message.author.send('❌ Login failed.')

    elif message.content.lower().startswith('!recheck'):
        user_id = message.author.id
        last_check_time = 0
        html = fetch_grade_html(user_id)
        if html:
            grades = extract_grades(html)
            if grades:
                summary = "📘 Latest Grades:\n" + "\n".join([f"{course}: {grade}" for course, grade in grades])
                await message.author.send(summary)
            else:
                await message.author.send("⚠️ No grades found.")
        else:
            await message.author.send("❌ Failed to fetch grade page.")

# === Run Bot ===
if __name__ == '__main__':
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    client.run(DISCORD_BOT_TOKEN)

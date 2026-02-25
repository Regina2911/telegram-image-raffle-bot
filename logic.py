import sqlite3
from datetime import datetime
import os
import cv2
import numpy as np
from math import sqrt, ceil, floor
from config import DATABASE

class DatabaseManager:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT
            )''')

            conn.execute('''CREATE TABLE IF NOT EXISTS prizes (
                prize_id INTEGER PRIMARY KEY,
                image TEXT,
                used INTEGER DEFAULT 0
            )''')

            conn.execute('''CREATE TABLE IF NOT EXISTS winners (
                user_id INTEGER,
                prize_id INTEGER,
                win_time TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(prize_id) REFERENCES prizes(prize_id)
            )''')

    def add_user(self, user_id, user_name):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT OR IGNORE INTO users VALUES (?, ?)', (user_id, user_name))

    def add_prize(self, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany('INSERT INTO prizes (image) VALUES (?)', data)

    def add_winner(self, user_id, prize_id):
        win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM winners WHERE user_id = ? AND prize_id = ?", (user_id, prize_id))
            if cur.fetchall():
                return 0
            conn.execute('INSERT INTO winners (user_id, prize_id, win_time) VALUES (?, ?, ?)',
                         (user_id, prize_id, win_time))
            return 1

    def get_users(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users")
            return [x[0] for x in cur.fetchall()]

    def get_prize_img(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT image FROM prizes WHERE prize_id = ?", (prize_id,))
            return cur.fetchone()[0]

    def get_random_prize(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM prizes WHERE used = 0")
            return cur.fetchone()

    def mark_prize_used(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute("UPDATE prizes SET used = 1 WHERE prize_id = ?", (prize_id,))

    def get_winners_count(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM winners WHERE prize_id = ?", (prize_id,))
            return cur.fetchone()[0]

    def get_winners_img(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(''' 
                SELECT image FROM winners 
                INNER JOIN prizes ON winners.prize_id = prizes.prize_id
                WHERE user_id = ?''', (user_id,))
            return [x[0] for x in cur.fetchall()]

    def get_rating(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT users.user_name, COUNT(winners.prize_id) AS count_prizes
                FROM winners
                INNER JOIN users ON users.user_id = winners.user_id
                GROUP BY winners.user_id
                ORDER BY count_prizes DESC
                LIMIT 10
            ''')
            return cur.fetchall()


def create_collage(image_paths):
    if not image_paths:
        return None

    images = []
    for path in image_paths:
        if os.path.exists(path):
            images.append(cv2.imread(path))
    if not images:
        return None

    num_images = len(images)
    num_cols = floor(sqrt(num_images))
    num_rows = ceil(num_images / num_cols)
    height, width = images[0].shape[:2]

    collage = np.zeros((num_rows * height, num_cols * width, 3), dtype=np.uint8)
    for i, img in enumerate(images):
        row = i // num_cols
        col = i % num_cols
        collage[row*height:(row+1)*height, col*width:(col+1)*width, :] = img
    return collage


def hide_img(img_name):
    image = cv2.imread(f'img/{img_name}')
    blurred = cv2.GaussianBlur(image, (15, 15), 0)
    pixelated = cv2.resize(blurred, (30, 30), interpolation=cv2.INTER_NEAREST)
    pixelated = cv2.resize(pixelated, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(f'hidden_img/{img_name}', pixelated)
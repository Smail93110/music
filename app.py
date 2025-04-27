from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/music/'

client = MongoClient('mongodb+srv://smailouldbey93pro:music1234@cluster0.smslswo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['music_party']
songs_collection = db['songs']
users_collection = db['users']

music_state = {
    'status': 'stopped',
    'current_song': None
}

compteur_state = {
    'start_time': None
}

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    songs = list(songs_collection.find())
    username = session.get('user')
    return render_template('index.html', songs=songs, username=username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user'] = 'admin'
            return redirect(url_for('admin'))
        else:
            user = users_collection.find_one({'username': username, 'password': password})
            if user:
                session['user'] = username
                return redirect(url_for('index'))
            else:
                return 'Invalid credentials', 401
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users_collection.insert_one({'username': username, 'password': password})
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/admin')
def admin():
    if session.get('user') != 'admin':
        return redirect(url_for('index'))
    songs = list(songs_collection.find())
    return render_template('admin.html', songs=songs)

@app.route('/add_song', methods=['POST'])
def add_song():
    if session.get('user') != 'admin':
        return redirect(url_for('index'))
    title = request.form['title']
    file = request.files['file']
    filename = file.filename
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    songs_collection.insert_one({
        'title': title,
        'file_url': url_for('static', filename='music/' + filename),
        'votes': 0,
        'voters': []
    })
    return redirect(url_for('admin'))

@app.route('/delete_song/<song_id>', methods=['POST'])
def delete_song(song_id):
    if session.get('user') != 'admin':
        return redirect(url_for('index'))
    songs_collection.delete_one({'_id': ObjectId(song_id)})
    return redirect(url_for('admin'))

@app.route('/vote/<song_id>', methods=['POST'])
def vote(song_id):
    username = session.get('user')
    if not username:
        return '', 401

    if compteur_state['start_time'] is None:
        compteur_state['start_time'] = datetime.utcnow().timestamp()

    songs_collection.update_many(
        {'voters': username},
        {
            '$pull': {'voters': username},
            '$inc': {'votes': -1}
        }
    )
    songs_collection.update_one(
        {'_id': ObjectId(song_id)},
        {
            '$push': {'voters': username},
            '$inc': {'votes': 1}
        }
    )

    return '', 204

@app.route('/reset_votes', methods=['POST'])
def reset_votes():
    songs_collection.update_many({}, {'$set': {'votes': 0, 'voters': []}})
    compteur_state['start_time'] = None
    music_state['status'] = 'stopped'
    music_state['current_song'] = None
    return '', 204

@app.route('/votes')
def votes():
    songs = list(songs_collection.find({}, {'title': 1, 'votes': 1, 'file_url': 1}))
    return jsonify([
        {
            '_id': str(song['_id']),
            'title': song['title'],
            'votes': song['votes'],
            'file_url': song['file_url']
        } for song in songs
    ])

@app.route('/winner')
def winner():
    songs = list(songs_collection.find({}, {'title': 1, 'votes': 1, 'file_url': 1}))
    if not songs:
        return jsonify({'status': 'no_songs'})

    max_votes = max(song['votes'] for song in songs)
    winners = [song for song in songs if song['votes'] == max_votes]

    if len(winners) > 1:
        # ✅ Égalité ➔ Reset + Stop musique
        songs_collection.update_many({}, {'$set': {'votes': 0, 'voters': []}})
        compteur_state['start_time'] = None
        music_state['status'] = 'stopped'
        music_state['current_song'] = None  # ✅ Vide la musique !!!
        return jsonify({'status': 'egalite'})
    else:
        # ✅ Un seul gagnant
        winner = winners[0]
        music_state['status'] = 'playing'
        music_state['current_song'] = winner['file_url']
        return jsonify({'status': 'winner', 'file_url': winner['file_url']})

@app.route('/music_state', methods=['GET', 'POST'])
def music_state_route():
    global music_state
    if request.method == 'POST':
        data = request.json
        music_state['status'] = data.get('status')
        music_state['current_song'] = data.get('current_song')
        return jsonify({'message': 'State updated'})
    else:
        return jsonify(music_state)

@app.route('/compteur')
def compteur():
    return jsonify(compteur_state)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

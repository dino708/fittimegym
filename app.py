from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, hashlib, os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'fittime-secret-2025'
DB = 'fittime.db'

# ─── DATABASE ───────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',  -- 'admin' or 'member'
            nama_lengkap TEXT,
            email TEXT,
            no_hp TEXT,
            tanggal_lahir TEXT,
            jenis_kelamin TEXT,
            berat_badan REAL,
            tinggi_badan REAL,
            tujuan_latihan TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS alat_gym (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT UNIQUE NOT NULL,
            deskripsi TEXT,
            kapasitas INTEGER DEFAULT 1,
            aktif INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS jadwal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alat_id INTEGER NOT NULL,
            tanggal TEXT NOT NULL,
            jam_mulai TEXT NOT NULL,
            jam_selesai TEXT NOT NULL,
            catatan TEXT,
            status TEXT DEFAULT 'pending',  -- pending, approved, rejected, clash
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (alat_id) REFERENCES alat_gym(id)
        );

        CREATE TABLE IF NOT EXISTS waktu_senggang (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            hari TEXT NOT NULL,
            jam_mulai TEXT NOT NULL,
            jam_selesai TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        ''')

        # Seed admin
        pw = hashlib.sha256('admin123'.encode()).hexdigest()
        db.execute('''INSERT OR IGNORE INTO users (username,password,role,nama_lengkap,email)
                      VALUES (?,?,?,?,?)''', ('admin', pw, 'admin', 'Administrator', 'admin@fittime.com'))

        # Seed alat
        alat_default = [
            ('Treadmill','Lari di tempat otomatis',2),
            ('Bench Press','Angkat beban dada',1),
            ('Sepeda Statis','Cardio sepeda',3),
            ('Dumbbell','Beban bebas tangan',4),
            ('Leg Press','Latihan kaki mesin',1),
            ('Pull-up Bar','Latihan punggung atas',2),
            ('Smith Machine','Squat dan press aman',1),
            ('Rowing Machine','Cardio dayung',2),
        ]
        for nama,desk,kap in alat_default:
            db.execute('INSERT OR IGNORE INTO alat_gym (nama,deskripsi,kapasitas) VALUES (?,?,?)', (nama,desk,kap))

        # Seed member contoh
        mpw = hashlib.sha256('member123'.encode()).hexdigest()
        members = [
            ('andi','Andi Pratama','andi@email.com','081234567890','2000-05-10','L',70,170,'Membentuk otot'),
            ('budi','Budi Santoso','budi@email.com','081234567891','1998-03-22','L',80,175,'Menurunkan berat badan'),
            ('caca','Caca Wulandari','caca@email.com','081234567892','2001-08-15','P',55,160,'Menjaga kesehatan'),
            ('dani','Dani Kusuma','dani@email.com','081234567893','1999-11-30','L',75,172,'Meningkatkan stamina'),
            ('eva','Eva Rahayu','eva@email.com','081234567894','2002-04-05','P',50,158,'Membentuk tubuh ideal'),
        ]
        for uname,nama,email,hp,tl,jk,bb,tb,tujuan in members:
            db.execute('''INSERT OR IGNORE INTO users
                (username,password,role,nama_lengkap,email,no_hp,tanggal_lahir,jenis_kelamin,berat_badan,tinggi_badan,tujuan_latihan)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (uname,mpw,'member',nama,email,hp,tl,jk,bb,tb,tujuan))

        db.commit()

        # Seed jadwal contoh
        today = date.today().isoformat()
        jadwal_seed = [
            ('andi','Treadmill',today,'08:00','09:00','Lari pagi'),
            ('budi','Bench Press',today,'09:00','10:00','Chest day'),
            ('caca','Treadmill',today,'08:30','09:30','Cardio'),
            ('dani','Sepeda Statis',today,'07:00','08:00','Warming up'),
            ('eva','Treadmill',today,'10:00','11:00','Cardio sore'),
            ('andi','Dumbbell',today,'09:30','10:30','Arm day'),
            ('budi','Leg Press',today,'10:00','11:00','Leg day'),
            ('caca','Sepeda Statis',today,'09:00','10:00','Cardio lanjut'),
        ]
        for uname,alat_nama,tgl,jm,js,cat in jadwal_seed:
            u = db.execute('SELECT id FROM users WHERE username=?',(uname,)).fetchone()
            a = db.execute('SELECT id FROM alat_gym WHERE nama=?',(alat_nama,)).fetchone()
            if u and a:
                exists = db.execute('SELECT id FROM jadwal WHERE user_id=? AND alat_id=? AND tanggal=? AND jam_mulai=?',
                    (u['id'],a['id'],tgl,jm)).fetchone()
                if not exists:
                    db.execute('INSERT INTO jadwal (user_id,alat_id,tanggal,jam_mulai,jam_selesai,catatan,status) VALUES (?,?,?,?,?,?,?)',
                        (u['id'],a['id'],tgl,jm,js,cat,'pending'))

        # Seed waktu senggang
        ws_seed = [
            ('andi','Senin','06:00','12:00'),('andi','Rabu','06:00','12:00'),('andi','Jumat','06:00','10:00'),
            ('budi','Selasa','07:00','11:00'),('budi','Kamis','07:00','11:00'),
            ('caca','Senin','08:00','12:00'),('caca','Sabtu','07:00','13:00'),
            ('dani','Setiap hari','06:00','09:00'),
            ('eva','Rabu','10:00','14:00'),('eva','Jumat','10:00','14:00'),
        ]
        for uname,hari,jm,js in ws_seed:
            u = db.execute('SELECT id FROM users WHERE username=?',(uname,)).fetchone()
            if u:
                ex = db.execute('SELECT id FROM waktu_senggang WHERE user_id=? AND hari=? AND jam_mulai=?',(u['id'],hari,jm)).fetchone()
                if not ex:
                    db.execute('INSERT INTO waktu_senggang (user_id,hari,jam_mulai,jam_selesai) VALUES (?,?,?,?)',
                        (u['id'],hari,jm,js))
        db.commit()

# ─── HELPERS ────────────────────────────────────────────────────────────────

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def to_min(t):
    h,m = map(int,t.split(':'))
    return h*60+m

def detect_clashes_for_date(db, tanggal):
    rows = db.execute('''
        SELECT j.id, j.jam_mulai, j.jam_selesai, j.alat_id, u.nama_lengkap as nama
        FROM jadwal j JOIN users u ON j.user_id=u.id
        WHERE j.tanggal=? ORDER BY j.alat_id, j.jam_mulai
    ''', (tanggal,)).fetchall()
    clashes = set()
    for i in range(len(rows)):
        for k in range(i+1,len(rows)):
            a,b = rows[i],rows[k]
            if a['alat_id']!=b['alat_id']: continue
            if to_min(a['jam_mulai'])<to_min(b['jam_selesai']) and to_min(b['jam_mulai'])<to_min(a['jam_selesai']):
                clashes.add(a['id']); clashes.add(b['id'])
    return clashes

def greedy_schedule(jadwal_list):
    from itertools import groupby
    result = {}
    by_alat = {}
    for j in jadwal_list:
        by_alat.setdefault(j['alat_nama'],[]).append(j)
    for alat,items in by_alat.items():
        sorted_items = sorted(items, key=lambda x: to_min(x['jam_selesai']))
        selected = []; last_end = -1
        for it in sorted_items:
            if to_min(it['jam_mulai']) >= last_end:
                selected.append(it['id']); last_end = to_min(it['jam_selesai'])
        result[alat] = {'items': sorted_items, 'selected': selected}
    return result

def login_required(role=None):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def wrapped(*args,**kwargs):
            if 'user_id' not in session:
                flash('Silakan login terlebih dahulu.','warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Akses ditolak.','danger')
                return redirect(url_for('dashboard'))
            return f(*args,**kwargs)
        return wrapped
    return decorator

# ─── AUTH ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        uname = request.form['username'].strip()
        pw = hash_pw(request.form['password'])
        with get_db() as db:
            user = db.execute('SELECT * FROM users WHERE username=? AND password=?',(uname,pw)).fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['nama'] = user['nama_lengkap'] or user['username']
            flash(f'Selamat datang, {session["nama"]}!','success')
            return redirect(url_for('dashboard'))
        flash('Username atau password salah.','danger')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        uname = request.form['username'].strip()
        pw = request.form['password']
        nama = request.form['nama_lengkap'].strip()
        email = request.form.get('email','')
        if len(pw)<6:
            flash('Password minimal 6 karakter.','danger')
            return render_template('register.html')
        try:
            with get_db() as db:
                db.execute('INSERT INTO users (username,password,role,nama_lengkap,email) VALUES (?,?,?,?,?)',
                    (uname,hash_pw(pw),'member',nama,email))
                db.commit()
            flash('Registrasi berhasil! Silakan login.','success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username sudah digunakan.','danger')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah keluar.','info')
    return redirect(url_for('login'))

# ─── DASHBOARD ──────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required()
def dashboard():
    today = date.today().isoformat()
    with get_db() as db:
        if session['role']=='admin':
            total_member = db.execute("SELECT COUNT(*) FROM users WHERE role='member'").fetchone()[0]
            total_alat = db.execute("SELECT COUNT(*) FROM alat_gym WHERE aktif=1").fetchone()[0]
            jadwal_hari_ini = db.execute('''
                SELECT j.*,u.nama_lengkap as nama,a.nama as alat_nama
                FROM jadwal j JOIN users u ON j.user_id=u.id JOIN alat_gym a ON j.alat_id=a.id
                WHERE j.tanggal=? ORDER BY j.jam_mulai
            ''',(today,)).fetchall()
            clashes = detect_clashes_for_date(db, today)
            total_clash = len(clashes)
            return render_template('dashboard_admin.html',
                total_member=total_member, total_alat=total_alat,
                jadwal_hari_ini=jadwal_hari_ini, total_clash=total_clash,
                clashes=clashes, today=today)
        else:
            my_jadwal = db.execute('''
                SELECT j.*,a.nama as alat_nama
                FROM jadwal j JOIN alat_gym a ON j.alat_id=a.id
                WHERE j.user_id=? ORDER BY j.tanggal,j.jam_mulai
            ''',(session['user_id'],)).fetchall()
            clashes = detect_clashes_for_date(db, today)
            ws = db.execute('SELECT * FROM waktu_senggang WHERE user_id=? ORDER BY id',(session['user_id'],)).fetchall()
            return render_template('dashboard_member.html',
                my_jadwal=my_jadwal, clashes=clashes, ws=ws, today=today)

# ─── PROFIL MEMBER ──────────────────────────────────────────────────────────

@app.route('/profil', methods=['GET','POST'])
@login_required()
def profil():
    with get_db() as db:
        if request.method=='POST':
            data = request.form
            db.execute('''UPDATE users SET nama_lengkap=?,email=?,no_hp=?,tanggal_lahir=?,
                jenis_kelamin=?,berat_badan=?,tinggi_badan=?,tujuan_latihan=? WHERE id=?''',
                (data['nama_lengkap'],data['email'],data['no_hp'],data['tanggal_lahir'],
                 data['jenis_kelamin'],data.get('berat_badan') or None,
                 data.get('tinggi_badan') or None,data['tujuan_latihan'],session['user_id']))
            db.commit()
            session['nama'] = data['nama_lengkap']
            flash('Profil berhasil diperbarui!','success')
            return redirect(url_for('profil'))
        user = db.execute('SELECT * FROM users WHERE id=?',(session['user_id'],)).fetchone()
        return render_template('profil.html', user=user)

@app.route('/ganti-password', methods=['POST'])
@login_required()
def ganti_password():
    lama = hash_pw(request.form['password_lama'])
    baru = request.form['password_baru']
    with get_db() as db:
        user = db.execute('SELECT * FROM users WHERE id=? AND password=?',(session['user_id'],lama)).fetchone()
        if not user:
            flash('Password lama salah.','danger')
        elif len(baru)<6:
            flash('Password baru minimal 6 karakter.','danger')
        else:
            db.execute('UPDATE users SET password=? WHERE id=?',(hash_pw(baru),session['user_id']))
            db.commit()
            flash('Password berhasil diubah!','success')
    return redirect(url_for('profil'))

# ─── WAKTU SENGGANG ─────────────────────────────────────────────────────────

@app.route('/waktu-senggang', methods=['GET','POST'])
@login_required()
def waktu_senggang():
    with get_db() as db:
        if request.method=='POST':
            hari = request.form['hari']
            jm = request.form['jam_mulai']
            js = request.form['jam_selesai']
            if to_min(js) <= to_min(jm):
                flash('Jam selesai harus lebih besar dari jam mulai.','danger')
            else:
                db.execute('INSERT INTO waktu_senggang (user_id,hari,jam_mulai,jam_selesai) VALUES (?,?,?,?)',
                    (session['user_id'],hari,jm,js))
                db.commit()
                flash('Waktu senggang ditambahkan!','success')
            return redirect(url_for('waktu_senggang'))
        ws = db.execute('SELECT * FROM waktu_senggang WHERE user_id=? ORDER BY id',(session['user_id'],)).fetchall()
        return render_template('waktu_senggang.html', ws=ws)

@app.route('/waktu-senggang/hapus/<int:wid>')
@login_required()
def hapus_ws(wid):
    with get_db() as db:
        db.execute('DELETE FROM waktu_senggang WHERE id=? AND user_id=?',(wid,session['user_id']))
        db.commit()
    flash('Waktu senggang dihapus.','info')
    return redirect(url_for('waktu_senggang'))

# ─── JADWAL MEMBER ──────────────────────────────────────────────────────────

@app.route('/jadwal', methods=['GET','POST'])
@login_required()
def jadwal_member():
    with get_db() as db:
        alat_list = db.execute('SELECT * FROM alat_gym WHERE aktif=1 ORDER BY nama').fetchall()
        if request.method=='POST':
            alat_id = request.form['alat_id']
            tanggal = request.form['tanggal']
            jm = request.form['jam_mulai']
            js = request.form['jam_selesai']
            catatan = request.form.get('catatan','')
            if to_min(js) <= to_min(jm):
                flash('Jam selesai harus lebih besar dari jam mulai.','danger')
            elif tanggal < date.today().isoformat():
                flash('Tidak bisa mendaftar untuk tanggal yang sudah lewat.','danger')
            else:
                db.execute('INSERT INTO jadwal (user_id,alat_id,tanggal,jam_mulai,jam_selesai,catatan,status) VALUES (?,?,?,?,?,?,?)',
                    (session['user_id'],alat_id,tanggal,jm,js,catatan,'pending'))
                db.commit()
                flash('Jadwal berhasil didaftarkan!','success')
            return redirect(url_for('jadwal_member'))
        my_jadwal = db.execute('''
            SELECT j.*,a.nama as alat_nama
            FROM jadwal j JOIN alat_gym a ON j.alat_id=a.id
            WHERE j.user_id=? ORDER BY j.tanggal DESC, j.jam_mulai
        ''',(session['user_id'],)).fetchall()
        return render_template('jadwal_member.html', alat_list=alat_list, my_jadwal=my_jadwal)

@app.route('/jadwal/hapus/<int:jid>')
@login_required()
def hapus_jadwal_member(jid):
    with get_db() as db:
        db.execute('DELETE FROM jadwal WHERE id=? AND user_id=?',(jid,session['user_id']))
        db.commit()
    flash('Jadwal dihapus.','info')
    return redirect(url_for('jadwal_member'))

# ─── ADMIN: SEMUA JADWAL ────────────────────────────────────────────────────

@app.route('/admin/jadwal')
@login_required('admin')
def admin_jadwal():
    tanggal = request.args.get('tanggal', date.today().isoformat())
    with get_db() as db:
        rows = db.execute('''
            SELECT j.*,u.nama_lengkap as nama,a.nama as alat_nama
            FROM jadwal j JOIN users u ON j.user_id=u.id JOIN alat_gym a ON j.alat_id=a.id
            WHERE j.tanggal=? ORDER BY a.nama, j.jam_mulai
        ''',(tanggal,)).fetchall()
        clashes = detect_clashes_for_date(db, tanggal)
        jadwal_list = [dict(r) for r in rows]
        greedy = greedy_schedule(jadwal_list)
        return render_template('admin_jadwal.html', rows=rows, clashes=clashes,
            greedy=greedy, tanggal=tanggal)

@app.route('/admin/jadwal/approve/<int:jid>')
@login_required('admin')
def approve_jadwal(jid):
    with get_db() as db:
        db.execute("UPDATE jadwal SET status='approved' WHERE id=?",(jid,))
        db.commit()
    flash('Jadwal disetujui.','success')
    return redirect(request.referrer or url_for('admin_jadwal'))

@app.route('/admin/jadwal/reject/<int:jid>')
@login_required('admin')
def reject_jadwal(jid):
    with get_db() as db:
        db.execute("UPDATE jadwal SET status='rejected' WHERE id=?",(jid,))
        db.commit()
    flash('Jadwal ditolak.','info')
    return redirect(request.referrer or url_for('admin_jadwal'))

@app.route('/admin/jadwal/hapus/<int:jid>')
@login_required('admin')
def hapus_jadwal_admin(jid):
    with get_db() as db:
        db.execute('DELETE FROM jadwal WHERE id=?',(jid,))
        db.commit()
    flash('Jadwal dihapus.','info')
    return redirect(request.referrer or url_for('admin_jadwal'))

# ─── ADMIN: MEMBER ──────────────────────────────────────────────────────────

@app.route('/admin/member')
@login_required('admin')
def admin_member():
    with get_db() as db:
        members = db.execute("SELECT * FROM users WHERE role='member' ORDER BY nama_lengkap").fetchall()
        return render_template('admin_member.html', members=members)

@app.route('/admin/member/<int:uid>')
@login_required('admin')
def admin_member_detail(uid):
    with get_db() as db:
        user = db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        jadwal = db.execute('''SELECT j.*,a.nama as alat_nama FROM jadwal j
            JOIN alat_gym a ON j.alat_id=a.id WHERE j.user_id=? ORDER BY j.tanggal DESC,j.jam_mulai''',(uid,)).fetchall()
        ws = db.execute('SELECT * FROM waktu_senggang WHERE user_id=? ORDER BY id',(uid,)).fetchall()
        return render_template('admin_member_detail.html', user=user, jadwal=jadwal, ws=ws)

@app.route('/admin/member/hapus/<int:uid>')
@login_required('admin')
def hapus_member(uid):
    with get_db() as db:
        db.execute('DELETE FROM waktu_senggang WHERE user_id=?',(uid,))
        db.execute('DELETE FROM jadwal WHERE user_id=?',(uid,))
        db.execute('DELETE FROM users WHERE id=?',(uid,))
        db.commit()
    flash('Member dihapus.','info')
    return redirect(url_for('admin_member'))

# ─── ADMIN: ALAT ────────────────────────────────────────────────────────────

@app.route('/admin/alat', methods=['GET','POST'])
@login_required('admin')
def admin_alat():
    with get_db() as db:
        if request.method=='POST':
            nama = request.form['nama'].strip()
            desk = request.form.get('deskripsi','')
            kap = request.form.get('kapasitas',1)
            try:
                db.execute('INSERT INTO alat_gym (nama,deskripsi,kapasitas) VALUES (?,?,?)',(nama,desk,kap))
                db.commit()
                flash(f'Alat "{nama}" ditambahkan!','success')
            except sqlite3.IntegrityError:
                flash('Nama alat sudah ada.','danger')
            return redirect(url_for('admin_alat'))
        alat_list = db.execute('''
            SELECT a.*, COUNT(j.id) as total_pakai
            FROM alat_gym a LEFT JOIN jadwal j ON a.id=j.alat_id
            GROUP BY a.id ORDER BY a.nama
        ''').fetchall()
        return render_template('admin_alat.html', alat_list=alat_list)

@app.route('/admin/alat/toggle/<int:aid>')
@login_required('admin')
def toggle_alat(aid):
    with get_db() as db:
        alat = db.execute('SELECT aktif FROM alat_gym WHERE id=?',(aid,)).fetchone()
        db.execute('UPDATE alat_gym SET aktif=? WHERE id=?',(0 if alat['aktif'] else 1, aid))
        db.commit()
    return redirect(url_for('admin_alat'))

@app.route('/admin/alat/hapus/<int:aid>')
@login_required('admin')
def hapus_alat(aid):
    with get_db() as db:
        db.execute('DELETE FROM jadwal WHERE alat_id=?',(aid,))
        db.execute('DELETE FROM alat_gym WHERE id=?',(aid,))
        db.commit()
    flash('Alat dihapus.','info')
    return redirect(url_for('admin_alat'))

# ─── ADMIN: STATISTIK ───────────────────────────────────────────────────────

@app.route('/admin/statistik')
@login_required('admin')
def admin_statistik():
    with get_db() as db:
        total_member = db.execute("SELECT COUNT(*) FROM users WHERE role='member'").fetchone()[0]
        total_jadwal = db.execute("SELECT COUNT(*) FROM jadwal").fetchone()[0]
        alat_populer = db.execute('''
            SELECT a.nama, COUNT(j.id) as cnt
            FROM alat_gym a LEFT JOIN jadwal j ON a.id=j.alat_id
            GROUP BY a.id ORDER BY cnt DESC LIMIT 8
        ''').fetchall()
        jam_ramai = db.execute('''
            SELECT substr(jam_mulai,1,2) as jam, COUNT(*) as cnt
            FROM jadwal GROUP BY jam ORDER BY cnt DESC LIMIT 10
        ''').fetchall()
        per_hari = db.execute('''
            SELECT tanggal, COUNT(*) as cnt FROM jadwal
            GROUP BY tanggal ORDER BY tanggal DESC LIMIT 14
        ''').fetchall()
        tujuan = db.execute('''
            SELECT tujuan_latihan, COUNT(*) as cnt FROM users
            WHERE role='member' AND tujuan_latihan IS NOT NULL
            GROUP BY tujuan_latihan ORDER BY cnt DESC
        ''').fetchall()
        return render_template('admin_statistik.html',
            total_member=total_member, total_jadwal=total_jadwal,
            alat_populer=alat_populer, jam_ramai=jam_ramai,
            per_hari=per_hari, tujuan=tujuan)

# ─── ADMIN: GREEDY API ──────────────────────────────────────────────────────

@app.route('/api/greedy')
@login_required('admin')
def api_greedy():
    tanggal = request.args.get('tanggal', date.today().isoformat())
    with get_db() as db:
        rows = db.execute('''
            SELECT j.id,j.jam_mulai,j.jam_selesai,u.nama_lengkap as nama,a.nama as alat_nama
            FROM jadwal j JOIN users u ON j.user_id=u.id JOIN alat_gym a ON j.alat_id=a.id
            WHERE j.tanggal=?
        ''',(tanggal,)).fetchall()
        jadwal_list = [dict(r) for r in rows]
        result = greedy_schedule(jadwal_list)
        return jsonify(result)

if __name__=='__main__':
    init_db()
    print("\n" + "="*50)
    print("🏋️  FitTime Scheduler siap dijalankan!")
    print("="*50)
    print("  URL    : http://localhost:5000")
    print("  Admin  : admin / admin123")
    print("  Member : andi / member123")
    print("           (budi, caca, dani, eva)")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)

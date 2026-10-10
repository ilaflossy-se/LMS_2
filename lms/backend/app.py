import os, datetime, functools, jwt
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
import re
_url = os.getenv("DATABASE_URL", "postgresql://lms:lms@localhost:5432/lms")
app.config["SQLALCHEMY_DATABASE_URI"] = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql+psycopg2://", _url)
SECRET = os.getenv("SECRET_KEY", "dev")
CORS(app)
db = SQLAlchemy(app)
D = db.Column

class User(db.Model):
    id = D(db.Integer, primary_key=True); name = D(db.String(100)); email = D(db.String(120), unique=True)
    role = D(db.String(20), default="student")  # student | teacher
class Course(db.Model):
    id = D(db.Integer, primary_key=True); title = D(db.String(200)); code = D(db.String(20))
    teacher_id = D(db.Integer, db.ForeignKey("user.id")); group_max = D(db.Integer, default=0)  # 0 = groups off
class Enroll(db.Model):
    id = D(db.Integer, primary_key=True); user_id = D(db.Integer, db.ForeignKey("user.id")); course_id = D(db.Integer, db.ForeignKey("course.id"))
class Assessment(db.Model):
    id = D(db.Integer, primary_key=True); course_id = D(db.Integer, db.ForeignKey("course.id"))
    title = D(db.String(100)); weight = D(db.Integer); due = D(db.Date, nullable=True)
class Score(db.Model):
    id = D(db.Integer, primary_key=True); user_id = D(db.Integer, db.ForeignKey("user.id"))
    assessment_id = D(db.Integer, db.ForeignKey("assessment.id")); score = D(db.Float)  # 0..100
class Attendance(db.Model):
    id = D(db.Integer, primary_key=True); user_id = D(db.Integer, db.ForeignKey("user.id"))
    course_id = D(db.Integer, db.ForeignKey("course.id")); attended = D(db.Integer); total = D(db.Integer)
class Team(db.Model):
    id = D(db.Integer, primary_key=True); course_id = D(db.Integer, db.ForeignKey("course.id"))
    name = D(db.String(100)); project = D(db.String(200), nullable=True)
    members = db.relationship("Member", backref="team", cascade="all,delete")
class Member(db.Model):
    id = D(db.Integer, primary_key=True); team_id = D(db.Integer, db.ForeignKey("team.id"))
    user_id = D(db.Integer, db.ForeignKey("user.id")); accepted = D(db.Boolean, default=False)

def err(m, c=400): return jsonify(error=m), c
def auth(f):
    @functools.wraps(f)
    def w(*a, **k):
        try: g.user = db.session.get(User, jwt.decode(request.headers.get("Authorization", "")[7:], SECRET, algorithms=["HS256"])["uid"])
        except Exception: g.user = None
        return f(*a, **k) if g.user else err("Sign in required", 401)
    return w
def teacher(f):
    @functools.wraps(f)
    def w(*a, **k): return f(*a, **k) if g.user.role == "teacher" else err("Teachers only", 403)
    return w
uj = lambda u: dict(id=u.id, name=u.name, email=u.email, role=u.role)

@app.post("/api/login/oidc")  # DEMO: replaces the real Microsoft OpenID Connect redirect
def oidc():
    u = User.query.filter_by(email=(request.json or {}).get("email", "")).first()
    if not u: return err("Account not found", 404)
    t = jwt.encode({"uid": u.id, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)}, SECRET, algorithm="HS256")
    return jsonify(token=t, user=uj(u))

@app.get("/api/health")
def health(): return jsonify(ok=True)

@app.get("/api/me")
@auth
def me(): return jsonify(uj(g.user))

def my_courses():
    if g.user.role == "teacher": return Course.query.filter_by(teacher_id=g.user.id).all()
    return [db.session.get(Course, e.course_id) for e in Enroll.query.filter_by(user_id=g.user.id)]

def grades_for(c):
    rows = []
    for a in Assessment.query.filter_by(course_id=c.id).order_by(Assessment.id):
        s = Score.query.filter_by(user_id=g.user.id, assessment_id=a.id).first()
        rows.append(dict(id=a.id, title=a.title, weight=a.weight, due=str(a.due) if a.due else None, score=s.score if s else None))
    return rows

@app.get("/api/courses")
@auth
def courses():
    out = []
    for c in my_courses():
        gr = grades_for(c); earned = sum(r["weight"] * r["score"] / 100 for r in gr if r["score"] is not None)
        out.append(dict(id=c.id, title=c.title, code=c.code, teacher=db.session.get(User, c.teacher_id).name, current=round(earned, 1)))
    return jsonify(out)

@app.get("/api/dashboard")
@auth
def dashboard():
    today, dl = datetime.date.today(), []
    for c in my_courses():
        for r in grades_for(c):
            if r["due"] and r["score"] is None and r["due"] >= str(today): dl.append(dict(course=c.title, title=r["title"], due=r["due"]))
    return jsonify(deadlines=sorted(dl, key=lambda x: x["due"]))

@app.get("/api/grades")
@auth
def grades(): return jsonify([dict(id=c.id, title=c.title, items=grades_for(c)) for c in my_courses()])

@app.get("/api/attendance")
@auth
def attendance():
    return jsonify([dict(course=db.session.get(Course, a.course_id).title, attended=a.attended, total=a.total)
                    for a in Attendance.query.filter_by(user_id=g.user.id)])

def team_json(t):
    return dict(id=t.id, course_id=t.course_id, course=db.session.get(Course, t.course_id).title, name=t.name, project=t.project,
                members=[dict(name=db.session.get(User, m.user_id).name, accepted=m.accepted) for m in t.members])

@app.get("/api/courses/<int:cid>")
@auth
def course(cid):
    c = db.get_or_404(Course, cid)
    mine = [team_json(t) for t in Team.query.filter_by(course_id=cid) if any(m.user_id == g.user.id for m in t.members)]
    return jsonify(id=c.id, title=c.title, code=c.code, group_max=c.group_max, items=grades_for(c), teams=mine)

@app.put("/api/courses/<int:cid>/groups")  # R6: teacher enables groups and sets the max size
@auth
@teacher
def set_groups(cid):
    c = db.get_or_404(Course, cid)
    if c.teacher_id != g.user.id: return err("Not your course", 403)
    c.group_max = max(0, int((request.json or {}).get("max", 0))); db.session.commit()
    return jsonify(ok=True)

@app.post("/api/courses/<int:cid>/teams")
@auth
def create_team(cid):
    c, d = db.get_or_404(Course, cid), request.json or {}
    if not c.group_max: return err("Project groups are not enabled for this course")
    users = [g.user]
    for e in d.get("emails", []):
        u = User.query.filter_by(email=e.strip()).first()
        if not u or not Enroll.query.filter_by(user_id=u.id, course_id=cid).first(): return err(f"{e} is not enrolled in this course")
        if u not in users: users.append(u)
    if len(users) > c.group_max: return err(f"Maximum group size is {c.group_max}")
    busy = {m.user_id for t in Team.query.filter_by(course_id=cid) for m in t.members}
    if any(u.id in busy for u in users): return err("Someone is already in a group")
    t = Team(course_id=cid, name=d.get("name") or "Team")
    t.members = [Member(user_id=u.id, accepted=(u.id == g.user.id)) for u in users]
    db.session.add(t); db.session.commit()
    return jsonify(team_json(t)), 201

@app.get("/api/invitations")
@auth
def invitations():
    return jsonify([team_json(m.team) for m in Member.query.filter_by(user_id=g.user.id, accepted=False)])

@app.post("/api/teams/<int:tid>/accept")
@auth
def accept(tid):
    m = Member.query.filter_by(team_id=tid, user_id=g.user.id).first_or_404(); m.accepted = True; db.session.commit()
    return jsonify(ok=True)

@app.post("/api/teams/<int:tid>/project")
@auth
def add_project(tid):
    t = db.get_or_404(Team, tid)
    if not any(m.user_id == g.user.id for m in t.members): return err("Not your team", 403)
    if not all(m.accepted for m in t.members): return err("Every member must accept the invitation first", 409)
    t.project = (request.json or {}).get("project", "").strip() or None
    if not t.project: return err("Enter a project title")
    db.session.commit(); return jsonify(team_json(t))

@app.get("/api/teacher/teams")  # R7
@auth
@teacher
def teacher_teams():
    ids = [c.id for c in my_courses()]
    return jsonify([team_json(t) for t in Team.query.filter(Team.course_id.in_(ids))])

def seed():
    if User.query.first(): return
    T = User(name="Diana Kazbekova", email="teacher@astanait.edu.kz", role="teacher")
    S = [User(name=n, email=e) for n, e in [("Ansar Shozhebay", "ansar@astanait.edu.kz"), ("Alikhan Beisenbay", "alikhan@astanait.edu.kz"),
         ("Ali Nurmanov", "ali@astanait.edu.kz"), ("Gazizbatyl Nurlykhan", "gazizbatyl@astanait.edu.kz")]]
    db.session.add_all([T] + S); db.session.flush()
    today = datetime.date.today(); day = lambda n: today + datetime.timedelta(days=n)
    for title, code, mx in [("ICT, Computer Systems and Architecture", "ICT101", 4), ("Calculus I", "MATH101", 0), ("Academic English", "ENG101", 0)]:
        c = Course(title=title, code=code, teacher_id=T.id, group_max=mx); db.session.add(c); db.session.flush()
        items = [Assessment(course_id=c.id, title=t, weight=w, due=d) for t, w, d in
                 [("Quizzes", 10, None), ("Assignments", 20, day(3)), ("Midterm", 20, None), ("Endterm", 20, day(21)), ("Final exam", 30, day(40))]]
        db.session.add_all(items); db.session.flush()
        for u in S:
            db.session.add_all([Enroll(user_id=u.id, course_id=c.id), Attendance(user_id=u.id, course_id=c.id, attended=11, total=12)])
            for a, sc in zip(items[:3], (85, 78, 72)): db.session.add(Score(user_id=u.id, assessment_id=a.id, score=sc))
    db.session.commit()

with app.app_context():
    db.create_all(); seed()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

import sqlite3
import tempfile
from pathlib import Path

from . import numeric, alternatives


def wal_case(level, initial, first, second):
    with tempfile.TemporaryDirectory() as folder:
        db = Path(folder) / "case.db"
        a = sqlite3.connect(db, isolation_level=None, timeout=0)
        b = sqlite3.connect(db, isolation_level=None, timeout=0)
        try:
            assert a.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
            a.execute("CREATE TABLE kv(v INTEGER NOT NULL)")
            a.execute("INSERT INTO kv VALUES(?)", (initial,))
            a.execute("BEGIN")
            if level == 1:
                a.execute("UPDATE kv SET v=v+?", (first,))
                a.execute("COMMIT")
                return b.execute("SELECT v FROM kv").fetchone()[0]
            before = a.execute("SELECT v FROM kv").fetchone()[0]
            b.execute("BEGIN IMMEDIATE")
            b.execute("UPDATE kv SET v=v+?", (first,))
            b.execute("COMMIT")
            if level == 2:
                ans = a.execute("SELECT v FROM kv").fetchone()[0]
                a.execute("ROLLBACK")
                return ans
            if level == 3:
                try:
                    a.execute("UPDATE kv SET v=v+?", (second,))
                    result = 0
                except sqlite3.Error as error:
                    result = getattr(error, "sqlite_errorcode", 517 if "locked" in str(error).lower() else None)
                    if result is None:
                        raise
                a.execute("ROLLBACK")
                return result
            a.execute("ROLLBACK")
            a.execute("BEGIN IMMEDIATE")
            a.execute("UPDATE kv SET v=v+?", (second,))
            a.execute("COMMIT")
            return b.execute("SELECT v FROM kv").fetchone()[0]
        finally:
            a.close()
            b.close()


def sqlite_wal(r):
    x, y, z = r.randrange(100,500),r.randrange(17,49),r.randrange(23,77)
    operations = [
        f"Setup: SQLite WAL database, one-row table kv(v) initialized to {x}. Connection A does BEGIN; UPDATE kv SET v=v+{y}; COMMIT. Then connection B SELECTs v. What integer does B read?",
        f"Setup: SQLite WAL, kv(v)={x}. A executes BEGIN; SELECT v (returns {x}). B executes BEGIN IMMEDIATE; UPDATE v=v+{y}; COMMIT. A executes SELECT v in SAME transaction. What integer does A read?",
        f"Setup: SQLite WAL, kv(v)={x}, busy_timeout=0. A executes BEGIN; SELECT v. B executes BEGIN IMMEDIATE; UPDATE v=v+{y}; COMMIT. A now executes UPDATE v=v+{z} without ending its old read transaction. What SQLite extended error code results? Respond using four decimal digits, with leading zeros if necessary.",
        f"Setup: SQLite WAL, kv(v)={x}. A BEGIN; SELECT v; B BEGIN IMMEDIATE; UPDATE v=v+{y}; COMMIT. A ROLLBACK; A BEGIN IMMEDIATE; UPDATE v=v+{z}; COMMIT. B SELECT v. What integer does B read?",
    ]
    out=[]
    for level,prompt in enumerate(operations,1):
        ans=wal_case(level,x,y,z)
        if level==3:
            answer,wrong=alternatives(f"{ans:04d}",["0000","0005","0019","0261","0517","0522"])
        else:
            answer,wrong=numeric(ans,delta=min(y,z))
        out.append((prompt,answer,wrong))
    return ("db-hard","sqlite-wal-snapshots","https://www.sqlite.org/isolation.html",out)


def sqlite_window(r):
    scores=[r.randrange(3,16) for _ in range(6)]
    scores[2]=scores[1]
    scores[4]=scores[3]
    index=r.randrange(2,7)
    data=", ".join(f"({i+1},{v})" for i,v in enumerate(scores))
    exprs=[
        "ROW_NUMBER() OVER (ORDER BY score DESC, id ASC)",
        "RANK() OVER (ORDER BY score DESC)",
        "SUM(score) OVER (ORDER BY id ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)",
        "SUM(score) OVER (ORDER BY score RANGE BETWEEN 2 PRECEDING AND CURRENT ROW)",
    ]
    con=sqlite3.connect(":memory:")
    try:
        con.execute("CREATE TABLE scores(id INTEGER PRIMARY KEY, score INTEGER)")
        con.executemany("INSERT INTO scores VALUES (?,?)",[(i+1,v) for i,v in enumerate(scores)])
        out=[]
        for level,expr in enumerate(exprs,1):
            query=f"SELECT result FROM (SELECT id, {expr} AS result FROM scores) WHERE id=?"
            value=int(con.execute(query,(index,)).fetchone()[0])
            prompt=f"SQLite table scores(id,score) has rows: {data}. Query: SELECT result FROM (SELECT id, {expr} AS result FROM scores) WHERE id={index}; What integer is returned?"
            out.append((prompt,*numeric(value)))
        return ("db-hard","sqlite-window-frames","https://www.sqlite.org/windowfunctions.html",out)
    finally:
        con.close()


def sqlite_join(r):
    n=r.randrange(4,7)
    child=[]
    for i in range(1,n+1):
        for j in range(r.randrange(0,4)):
            child.append((i,("yes" if r.randrange(2) else "no")))
    child.append((None,"yes"))
    parent=list(range(1,n+1))
    formatted = ", ".join(f"({i if i is not None else 'NULL'},'{kind}')" for i,kind in child)
    queries=[
        "SELECT COUNT(*) FROM p LEFT JOIN c ON p.id=c.pid",
        "SELECT COUNT(c.pid) FROM p LEFT JOIN c ON p.id=c.pid",
        "SELECT COUNT(*) FROM p LEFT JOIN c ON p.id=c.pid WHERE c.flag='yes'",
        "SELECT COUNT(*) FROM p LEFT JOIN c ON p.id=c.pid WHERE c.flag='yes' OR c.pid IS NULL",
    ]
    con=sqlite3.connect(":memory:")
    try:
        con.execute("CREATE TABLE p(id INTEGER PRIMARY KEY)")
        con.execute("CREATE TABLE c(pid INTEGER,flag TEXT)")
        con.executemany("INSERT INTO p VALUES (?)",[(x,) for x in parent])
        con.executemany("INSERT INTO c VALUES (?,?)",child)
        out=[]
        for q in queries:
            value=int(con.execute(q).fetchone()[0])
            prompt=f"SQLite tables: p(id) has rows {parent}; c(pid,flag) has rows {formatted}. Execute: {q}; What integer does it return? Standard SQL NULL semantics apply."
            out.append((prompt,*numeric(value)))
        return ("db-hard","sqlite-left-join-null","https://www.sqlite.org/lang_select.html",out)
    finally:
        con.close()


BUILDERS=[sqlite_wal,sqlite_window,sqlite_join]

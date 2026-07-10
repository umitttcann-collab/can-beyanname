from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import json, os, hashlib
from pathlib import Path
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "can_mali_2026_gizli")

DATA_FILE = Path("veri/veriler.json")
SIFRE_FILE = Path("veri/sifre.txt")

def veri_yukle():
    DATA_FILE.parent.mkdir(exist_ok=True)
    if DATA_FILE.exists():
        try:
            v = json.loads(DATA_FILE.read_text("utf-8"))
            if "beyannameler" not in v: v["beyannameler"] = []
            if "ayarlar" not in v: v["ayarlar"] = {}
            return v
        except: pass
    return {"mukellefler":[], "hareketler":[], "beyannameler":[], "ayarlar":{}}

def veri_kaydet(v):
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(v, ensure_ascii=False, indent=2), "utf-8")

def sifre_hash(s):
    return hashlib.sha256(s.encode()).hexdigest()

def giris_gerekli(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("giris"):
            return redirect(url_for("giris"))
        return f(*args, **kwargs)
    return wrapper

def durum_hesapla(b):
    if b.get("durum") == "Verildi": return "Verildi"
    try:
        son = datetime.strptime(b["son_tarih"], "%d.%m.%Y").date()
        if son < date.today(): return "Gecikmiş"
    except: pass
    return b.get("durum", "Bekliyor")

@app.route("/giris", methods=["GET","POST"])
def giris():
    hata = ""
    if request.method == "POST":
        sifre = request.form.get("sifre","")
        if SIFRE_FILE.exists():
            if SIFRE_FILE.read_text("utf-8").strip() == sifre_hash(sifre):
                session["giris"] = True
                return redirect(url_for("index"))
            else:
                hata = "Hatalı şifre."
        else:
            if len(sifre) >= 4:
                SIFRE_FILE.parent.mkdir(exist_ok=True)
                SIFRE_FILE.write_text(sifre_hash(sifre), "utf-8")
                session["giris"] = True
                return redirect(url_for("index"))
            else:
                hata = "En az 4 karakter olmalı."
    return render_template("giris.html", hata=hata, kayitli=SIFRE_FILE.exists())

@app.route("/cikis")
def cikis():
    session.clear()
    return redirect(url_for("giris"))

@app.route("/")
@giris_gerekli
def index():
    veri = veri_yukle()
    bugun = date.today()
    tum = veri.get("beyannameler", [])
    gecikmiş = [b for b in tum if durum_hesapla(b) == "Gecikmiş"]
    bu_ay_ay = str(bugun.month).zfill(2)
    bu_ay_yil = str(bugun.year)
    bu_ay = [b for b in tum if b.get("son_tarih","")[3:5]==bu_ay_ay
             and b.get("son_tarih","")[6:10]==bu_ay_yil
             and durum_hesapla(b) != "Verildi"]
    stats = {
        "toplam": len(tum),
        "verildi": sum(1 for b in tum if durum_hesapla(b)=="Verildi"),
        "bekliyor": sum(1 for b in tum if durum_hesapla(b)=="Bekliyor"),
        "gecikmiş": len(gecikmiş),
    }
    return render_template("index.html", stats=stats,
                           gecikmiş=gecikmiş[:10], bu_ay=bu_ay[:10],
                           bugun=bugun.strftime("%d.%m.%Y"))

@app.route("/beyannameler")
@giris_gerekli
def beyannameler():
    veri = veri_yukle()
    tum = veri.get("beyannameler", [])
    muk_f = request.args.get("muk", "")
    tur_f = request.args.get("tur", "")
    dur_f = request.args.get("dur", "")
    ay_f  = request.args.get("ay", "")
    if muk_f: tum = [b for b in tum if b.get("mukellef_ad") == muk_f]
    if tur_f: tum = [b for b in tum if b.get("tur") == tur_f]
    if ay_f:  tum = [b for b in tum if b.get("donem_ay","") == ay_f]
    if dur_f: tum = [b for b in tum if durum_hesapla(b) == dur_f]
    tum = sorted(tum, key=lambda b: b.get("son_tarih",""))
    for b in tum:
        b["durum_goster"] = durum_hesapla(b)
    mukellefler = sorted(set(b.get("mukellef_ad","") for b in veri.get("beyannameler",[])))
    turler = sorted(set(b.get("tur","") for b in veri.get("beyannameler",[])))
    bugun = date.today()
    aylar = [f"{str(a).zfill(2)}.{bugun.year}" for a in range(1,13)]
    return render_template("beyannameler.html", beyanlar=tum,
                           mukellefler=mukellefler, turler=turler, aylar=aylar,
                           muk_f=muk_f, tur_f=tur_f, dur_f=dur_f, ay_f=ay_f)

@app.route("/verildi", methods=["POST"])
@giris_gerekli
def verildi():
    ids = request.json.get("ids", [])
    veri = veri_yukle()
    bugun = date.today().strftime("%d.%m.%Y")
    for b in veri.get("beyannameler", []):
        if b.get("id") in ids:
            b["durum"] = "Verildi"
            b["verilme_tarihi"] = bugun
    veri_kaydet(veri)
    return jsonify({"ok": True, "sayi": len(ids)})

@app.route("/mukellefler")
@giris_gerekli
def mukellefler():
    veri = veri_yukle()
    muks = sorted(veri.get("mukellefler",[]),
                  key=lambda m: m.get("ad","").lower())
    for m in muks:
        cnt = len([b for b in veri.get("beyannameler",[])
                   if b.get("mukellef_ad")==m.get("ad")])
        m["beyan_sayisi"] = cnt
    return render_template("mukellefler.html", mukellefler=muks)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

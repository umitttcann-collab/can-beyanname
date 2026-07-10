from flask import Flask, render_template_string, jsonify, request, redirect, url_for, session
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

CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#F1F5F9;color:#0F172A;min-height:100vh}
.topbar{background:#1B2B4B;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.topbar h1{color:white;font-size:16px;font-weight:600}
.topbar a{color:rgba(255,255,255,0.7);text-decoration:none;font-size:13px;padding:6px 12px;border:1px solid rgba(255,255,255,0.3);border-radius:6px}
.tabs{background:white;border-bottom:1px solid #E2E8F0;padding:0 16px;display:flex;gap:0;overflow-x:auto}
.tabs a{padding:12px 16px;font-size:13px;color:#64748B;text-decoration:none;border-bottom:2px solid transparent;white-space:nowrap;display:block}
.tabs a.active{color:#1B2B4B;border-bottom-color:#1B2B4B;font-weight:500}
.wrap{padding:16px;max-width:960px;margin:0 auto}
.stat-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:16px}
@media(min-width:600px){.stat-grid{grid-template-columns:repeat(4,1fr)}}
.stat{background:white;border-radius:10px;padding:14px;border:1px solid #E2E8F0}
.stat .lbl{font-size:11px;color:#64748B;margin-bottom:6px}
.stat .val{font-size:24px;font-weight:600}
.kart{background:white;border-radius:10px;border:1px solid #E2E8F0;overflow:hidden;margin-bottom:16px}
.kart-hdr{padding:12px 16px;border-bottom:1px solid #E2E8F0;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.kart-hdr h2{font-size:14px;font-weight:600}
table{width:100%;border-collapse:collapse}
th{padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;background:#F8FAFC;border-bottom:1px solid #E2E8F0}
td{padding:10px 12px;font-size:13px;border-bottom:1px solid #F1F5F9}
tr:last-child td{border-bottom:none}
tr:hover{background:#F8FAFC}
.badge{display:inline-block;padding:3px 8px;border-radius:20px;font-size:11px;font-weight:500}
.v{background:#DCFCE7;color:#166534}
.g{background:#FEE2E2;color:#991B1B}
.b{background:#FEF3C7;color:#92400E}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;border:none;text-decoration:none}
.btn-p{background:#1B2B4B;color:white}
.btn-g{background:#16A34A;color:white}
.btn-s{padding:6px 10px;font-size:12px}
select,input[type=text],input[type=password]{height:36px;border:1px solid #E2E8F0;border-radius:8px;padding:0 10px;font-size:13px;background:white;color:#0F172A;outline:none}
input[type=checkbox]{width:16px;height:16px;cursor:pointer}
.filtre{padding:12px 16px;border-bottom:1px solid #E2E8F0;display:flex;flex-wrap:wrap;gap:8px}
.hata{background:#FEE2E2;color:#991B1B;padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:12px;border:1px solid #FECACA}
.bos{padding:32px;text-align:center;color:#64748B}
.alt{padding:10px 16px;background:#F8FAFC;font-size:12px;color:#64748B;border-top:1px solid #E2E8F0}
</style>
"""

BASE = CSS + """
<div class="topbar">
  <h1>CAN Beyanname Takip</h1>
  <a href="/cikis">Çıkış</a>
</div>
<div class="tabs">
  <a href="/" class="{{ 'active' if aktif=='ozet' else '' }}">Genel Özet</a>
  <a href="/beyannameler" class="{{ 'active' if aktif=='beyan' else '' }}">Beyannameler</a>
  <a href="/mukellefler" class="{{ 'active' if aktif=='muk' else '' }}">Mükellefler</a>
</div>
<div class="wrap">
"""

SCRIPT = """
<script>
var secili=[];
function tumunuSec(cb){
  document.querySelectorAll('.chk').forEach(c=>{
    c.checked=cb.checked;
    var id=c.dataset.id;
    if(cb.checked){if(!secili.includes(id))secili.push(id);}
    else secili=secili.filter(x=>x!==id);
  });
  document.getElementById('ss').textContent=secili.length;
}
function toggle(id,cb){
  if(cb.checked)secili.push(id);
  else secili=secili.filter(x=>x!==id);
  document.getElementById('ss').textContent=secili.length;
}
function verildi(){
  if(!secili.length){alert('Beyanname seçin.');return;}
  if(!confirm(secili.length+' beyanname verildi işaretlensin mi?'))return;
  fetch('/verildi',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ids:secili})})
  .then(r=>r.json()).then(d=>{if(d.ok)location.reload();});
}
</script>
"""

@app.route("/giris", methods=["GET","POST"])
def giris():
    hata = ""
    kayitli = SIFRE_FILE.exists()
    if request.method == "POST":
        s = request.form.get("sifre","")
        if kayitli:
            if SIFRE_FILE.read_text("utf-8").strip() == sifre_hash(s):
                session["giris"] = True
                return redirect("/")
            hata = "Hatalı şifre."
        else:
            if len(s) >= 4:
                SIFRE_FILE.parent.mkdir(exist_ok=True)
                SIFRE_FILE.write_text(sifre_hash(s), "utf-8")
                session["giris"] = True
                return redirect("/")
            hata = "En az 4 karakter olmalı."
    return render_template_string(CSS + """
<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Giriş</title></head><body style="background:#1B2B4B;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px">
<div style="background:white;border-radius:16px;padding:32px;width:100%;max-width:380px">
  <h1 style="font-size:20px;font-weight:700;color:#1B2B4B;margin-bottom:4px">CAN Mali Müşavirlik</h1>
  <p style="font-size:13px;color:#64748B;margin-bottom:24px">{{ 'Şifrenizi girin' if kayitli else 'İlk girişte şifre belirleyin' }}</p>
  {% if hata %}<div class="hata">{{ hata }}</div>{% endif %}
  <form method="POST">
    <label style="font-size:13px;font-weight:500;display:block;margin-bottom:6px">Şifre</label>
    <input type="password" name="sifre" autofocus placeholder="••••••••"
           style="width:100%;margin-bottom:16px">
    <button type="submit" style="width:100%;height:44px;background:#1B2B4B;color:white;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer">
      {{ 'Giriş Yap' if kayitli else 'Şifre Belirle ve Giriş' }}
    </button>
  </form>
</div>
</body></html>
""", hata=hata, kayitli=kayitli)

@app.route("/cikis")
def cikis():
    session.clear()
    return redirect("/giris")

@app.route("/")
@giris_gerekli
def index():
    veri = veri_yukle()
    bugun = date.today()
    tum = veri.get("beyannameler", [])
    gecikmiş = [b for b in tum if durum_hesapla(b)=="Gecikmiş"]
    bu_ay_ay = str(bugun.month).zfill(2)
    bu_ay_yil = str(bugun.year)
    bu_ay = [b for b in tum if b.get("son_tarih","")[3:5]==bu_ay_ay
             and b.get("son_tarih","")[6:10]==bu_ay_yil
             and durum_hesapla(b)!="Verildi"]
    stats = {
        "toplam": len(tum),
        "verildi": sum(1 for b in tum if durum_hesapla(b)=="Verildi"),
        "bekliyor": sum(1 for b in tum if durum_hesapla(b)=="Bekliyor"),
        "gecikmiş": len(gecikmiş),
    }
    return render_template_string(BASE + """
<div class="stat-grid">
  <div class="stat"><div class="lbl">Toplam</div><div class="val" style="color:#1B2B4B">{{ s.toplam }}</div></div>
  <div class="stat"><div class="lbl">Verildi ✓</div><div class="val" style="color:#16A34A">{{ s.verildi }}</div></div>
  <div class="stat"><div class="lbl">Bekliyor</div><div class="val" style="color:#D97706">{{ s.bekliyor }}</div></div>
  <div class="stat"><div class="lbl">Gecikmiş ✗</div><div class="val" style="color:#DC2626">{{ s.gecikmiş }}</div></div>
</div>
{% if gecikmiş %}
<div class="kart">
  <div class="kart-hdr"><h2 style="color:#DC2626">✗ Gecikmiş ({{ gecikmiş|length }})</h2></div>
  <table><tr><th>Mükellef</th><th>Beyanname</th><th>Son Tarih</th></tr>
  {% for b in gecikmiş %}
  <tr><td><strong>{{ b.mukellef_ad }}</strong></td><td>{{ b.tur }}</td>
  <td style="color:#DC2626;font-weight:500">{{ b.son_tarih }}</td></tr>
  {% endfor %}</table>
</div>{% endif %}
{% if bu_ay %}
<div class="kart">
  <div class="kart-hdr"><h2 style="color:#D97706">⏳ Bu Ay Son Tarihliler ({{ bu_ay|length }})</h2></div>
  <table><tr><th>Mükellef</th><th>Beyanname</th><th>Son Tarih</th><th>Dönem</th></tr>
  {% for b in bu_ay %}
  <tr><td><strong>{{ b.mukellef_ad }}</strong></td><td>{{ b.tur }}</td>
  <td>{{ b.son_tarih }}</td><td>{{ b.donem }}</td></tr>
  {% endfor %}</table>
</div>{% endif %}
{% if not gecikmiş and not bu_ay %}
<div class="kart"><div class="bos"><p style="font-size:16px">✓ Tüm beyannameler güncel</p></div></div>
{% endif %}
</div>
""", s=stats, gecikmiş=gecikmiş[:15], bu_ay=bu_ay[:15], aktif="ozet")

@app.route("/beyannameler")
@giris_gerekli
def beyannameler():
    veri = veri_yukle()
    tum = veri.get("beyannameler", [])
    muk_f = request.args.get("muk","")
    tur_f = request.args.get("tur","")
    dur_f = request.args.get("dur","")
    ay_f  = request.args.get("ay","")
    liste = list(tum)
    if muk_f: liste = [b for b in liste if b.get("mukellef_ad")==muk_f]
    if tur_f: liste = [b for b in liste if b.get("tur")==tur_f]
    if ay_f:  liste = [b for b in liste if b.get("donem_ay","")==ay_f]
    if dur_f: liste = [b for b in liste if durum_hesapla(b)==dur_f]
    liste = sorted(liste, key=lambda b: b.get("son_tarih",""))
    for b in liste: b["_d"] = durum_hesapla(b)
    mukellefler = sorted(set(b.get("mukellef_ad","") for b in tum))
    turler = sorted(set(b.get("tur","") for b in tum))
    bugun = date.today()
    aylar = [f"{str(a).zfill(2)}.{bugun.year}" for a in range(1,13)]
    return render_template_string(BASE + SCRIPT + """
<div class="kart">
  <div class="filtre">
    <form method="GET" style="display:flex;flex-wrap:wrap;gap:8px;width:100%">
      <select name="muk" onchange="this.form.submit()">
        <option value="">Tüm Mükellefler</option>
        {% for m in mukellefler %}<option value="{{ m }}" {{ 'selected' if muk_f==m }}>{{ m }}</option>{% endfor %}
      </select>
      <select name="tur" onchange="this.form.submit()">
        <option value="">Tüm Türler</option>
        {% for t in turler %}<option value="{{ t }}" {{ 'selected' if tur_f==t }}>{{ t }}</option>{% endfor %}
      </select>
      <select name="ay" onchange="this.form.submit()">
        <option value="">Tüm Aylar</option>
        {% for a in aylar %}<option value="{{ a }}" {{ 'selected' if ay_f==a }}>{{ a }}</option>{% endfor %}
      </select>
      <select name="dur" onchange="this.form.submit()">
        <option value="">Tüm Durumlar</option>
        <option value="Bekliyor" {{ 'selected' if dur_f=='Bekliyor' }}>Bekliyor</option>
        <option value="Verildi" {{ 'selected' if dur_f=='Verildi' }}>Verildi</option>
        <option value="Gecikmiş" {{ 'selected' if dur_f=='Gecikmiş' }}>Gecikmiş</option>
      </select>
    </form>
  </div>
  <div style="padding:10px 16px;border-bottom:1px solid #E2E8F0;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
    <label style="font-size:13px;display:flex;align-items:center;gap:6px">
      <input type="checkbox" onchange="tumunuSec(this)"> Tümünü seç
    </label>
    <span style="font-size:13px;color:#64748B"><span id="ss">0</span> seçili</span>
    <button class="btn btn-g btn-s" onclick="verildi()">✓ Verildi İşaretle</button>
  </div>
  <div style="overflow-x:auto">
  <table>
    <tr><th></th><th>Mükellef</th><th>Beyanname</th><th>Dönem</th><th>Son Tarih</th><th>Verilme</th><th>Durum</th></tr>
    {% for b in liste %}
    <tr>
      <td><input type="checkbox" class="chk" data-id="{{ b.id }}" onchange="toggle('{{ b.id }}',this)"></td>
      <td><strong>{{ b.mukellef_ad }}</strong></td>
      <td>{{ b.tur }}</td>
      <td>{{ b.donem }}</td>
      <td {% if b._d=='Gecikmiş' %}style="color:#DC2626;font-weight:500"{% endif %}>{{ b.son_tarih }}</td>
      <td>{{ b.verilme_tarihi or '—' }}</td>
      <td>{% if b._d=='Verildi' %}<span class="badge v">✓ Verildi</span>
          {% elif b._d=='Gecikmiş' %}<span class="badge g">✗ Gecikmiş</span>
          {% else %}<span class="badge b">⏳ Bekliyor</span>{% endif %}</td>
    </tr>
    {% endfor %}
  </table>
  </div>
  <div class="alt">{{ liste|length }} kayıt</div>
</div>
</div>
""", liste=liste, mukellefler=mukellefler, turler=turler, aylar=aylar,
     muk_f=muk_f, tur_f=tur_f, dur_f=dur_f, ay_f=ay_f, aktif="beyan")

@app.route("/verildi", methods=["POST"])
@giris_gerekli
def verildi_isle():
    ids = request.json.get("ids", [])
    veri = veri_yukle()
    bugun = date.today().strftime("%d.%m.%Y")
    for b in veri.get("beyannameler", []):
        if b.get("id") in ids:
            b["durum"] = "Verildi"
            b["verilme_tarihi"] = bugun
    veri_kaydet(veri)
    return jsonify({"ok": True})

@app.route("/mukellefler")
@giris_gerekli
def mukellefler():
    veri = veri_yukle()
    muks = sorted(veri.get("mukellefler",[]), key=lambda m: m.get("ad","").lower())
    for m in muks:
        m["_cnt"] = len([b for b in veri.get("beyannameler",[]) if b.get("mukellef_ad")==m.get("ad")])
    return render_template_string(BASE + """
<div class="kart">
  <div class="kart-hdr"><h2>Mükellefler ({{ muks|length }})</h2></div>
  <table>
    <tr><th>Mükellef</th><th>Vergi No</th><th>Beyanname</th><th>Durum</th></tr>
    {% for m in muks %}
    <tr>
      <td><strong>{{ m.ad }}</strong></td>
      <td style="color:#64748B">{{ m.vergi_no or '—' }}</td>
      <td><span style="color:#1B2B4B;font-weight:600">{{ m._cnt }}</span></td>
      <td>{% if m.kapanis %}<span class="badge" style="background:#F1F5F9;color:#64748B">Kapalı</span>
          {% else %}<span class="badge v">Aktif</span>{% endif %}</td>
    </tr>
    {% endfor %}
  </table>
</div>
</div>
""", muks=muks, aktif="muk")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=False)

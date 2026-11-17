#!/usr/bin/env python3
"""Sincroniza las skills de la cuenta de Claude de Ernesto con la página «Mis skills de IA».

La carpeta _sync/ no se publica (GitHub Pages/Jekyll ignora las carpetas que empiezan por _).

Uso:
  python3 _sync/skills_sync.py detectar
      Lista en JSON las skills nuevas, cambiadas o retiradas respecto a lo publicado.
  python3 _sync/skills_sync.py preparar NOMBRE
      Copia la skill a /tmp/skills-publicas/NOMBRE para revisarla y adaptarla
      (versión pública: sin «Ernesto», sin depender de «Claude»).
  python3 _sync/skills_sync.py publicar NOMBRE --s "Sección" --d "Descripción corta" [--p "Perfil" --po N]
      Empaqueta /tmp/skills-publicas/NOMBRE en skills/NOMBRE.zip, crea o actualiza su ficha
      en mis-skills-de-claude.html y anota la huella de la versión original en estado.json.
  python3 _sync/skills_sync.py marcar NOMBRE
      Anota la huella actual sin volver a publicar (cambio sin efecto en la versión pública).
"""
import argparse, glob, hashlib, json, os, re, shutil, sys, zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC = os.path.join(REPO, "_sync")
PAGE = os.path.join(REPO, "mis-skills-de-claude.html")
ZIPS = os.path.join(REPO, "skills")
STAGE = "/tmp/skills-publicas"


def cargar(nombre, defecto):
    p = os.path.join(SYNC, nombre)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return defecto


def guardar(nombre, datos):
    with open(os.path.join(SYNC, nombre), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def origen():
    cands = [d for d in glob.glob(os.path.expanduser("~/.claude/skills/synced/*/")) if os.path.isdir(d)]
    cands += [d for d in glob.glob("/root/.claude/skills/synced/*/") if d not in cands]
    if not cands:
        sys.exit("ERROR: no encuentro la copia sincronizada de las skills (~/.claude/skills/synced/).")
    return cands[0]


def huella(carpeta):
    h = hashlib.sha256()
    for raiz, _, archivos in sorted(os.walk(carpeta)):
        for a in sorted(archivos):
            p = os.path.join(raiz, a)
            rel = os.path.relpath(p, carpeta).replace(os.sep, "/")
            with open(p, "rb") as f:
                datos = f.read().replace(b"\r\n", b"\n")
            h.update(rel.encode() + b"\0" + hashlib.sha256(datos).digest())
    return h.hexdigest()


def descripcion(carpeta):
    with open(os.path.join(carpeta, "SKILL.md"), encoding="utf-8", errors="replace") as f:
        txt = f.read()
    m = re.search(r"^description:\s*(.+)$", txt, re.M)
    return m.group(1).strip().strip('"') if m else ""


def skills_origen(cfg):
    base = origen()
    excl = set(cfg["excluir_anthropic"]) | set(cfg["excluir_privadas"])
    out = {}
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        if os.path.isfile(os.path.join(p, "SKILL.md")) and d not in excl:
            out[d] = p
    return out


def leer_data():
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"const DATA = (\[.*?\]);\n", html, re.S)
    if not m:
        sys.exit("ERROR: no encuentro 'const DATA = [...];' en la página.")
    return html, m, json.loads(m.group(1))


def cmd_detectar(_):
    cfg = cargar("config.json", {})
    estado = cargar("estado.json", {})
    src = skills_origen(cfg)
    nuevas, cambiadas = [], []
    for n, p in src.items():
        h = huella(p)
        if n in cfg.get("pendientes_decidir", []):
            continue
        if n not in estado:
            nuevas.append({"nombre": n, "descripcion": descripcion(p)})
        elif estado[n] != h:
            cambiadas.append({"nombre": n, "descripcion": descripcion(p)})
    retiradas = [n for n in estado if n not in src]
    print(json.dumps({"origen": origen(), "nuevas": nuevas, "cambiadas": cambiadas,
                      "ya_no_estan_en_la_cuenta": retiradas,
                      "pendientes_decidir": cfg.get("pendientes_decidir", [])},
                     ensure_ascii=False, indent=2))


def cmd_preparar(a):
    cfg = cargar("config.json", {})
    src = skills_origen(cfg)
    if a.nombre not in src:
        sys.exit(f"ERROR: {a.nombre} no está en la cuenta (o está excluida).")
    dst = os.path.join(STAGE, a.nombre)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src[a.nombre], dst)
    for raiz, _, archivos in os.walk(dst):
        for x in archivos:
            p = os.path.join(raiz, x)
            if x.endswith((".md", ".py", ".json", ".txt", ".csv", ".yaml", ".yml")):
                with open(p, "rb") as f:
                    b = f.read()
                with open(p, "wb") as f:
                    f.write(b.replace(b"\r\n", b"\n"))
    print(dst)
    os.system(f"grep -rn 'Ernesto\\|Claude' {dst} | cut -c1-220")


def cmd_publicar(a):
    cfg = cargar("config.json", {})
    src = skills_origen(cfg)
    dst = os.path.join(STAGE, a.nombre)
    if not os.path.isfile(os.path.join(dst, "SKILL.md")):
        sys.exit(f"ERROR: primero ejecuta 'preparar {a.nombre}'.")
    restos = [l for l in os.popen(f"grep -rn 'Ernesto' {dst}").read().splitlines()]
    if restos and not a.forzar:
        sys.exit("ERROR: la versión pública aún nombra a Ernesto:\n" + "\n".join(restos))
    zp = os.path.join(ZIPS, a.nombre + ".zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, _, archivos in sorted(os.walk(dst)):
            for x in sorted(archivos):
                p = os.path.join(raiz, x)
                z.write(p, os.path.join(a.nombre, os.path.relpath(p, dst)))
    html, m, data = leer_data()
    ficha = next((e for e in data if e.get("n") == a.nombre), None)
    if ficha is None:
        ficha = {"n": a.nombre, "g": "propias", "s": a.s or "Otras herramientas propias",
                 "d": a.d, "o": "cuenta", "u": f"skills/{a.nombre}.zip"}
        mismos = [i for i, e in enumerate(data) if e.get("g") == "propias" and e.get("s") == ficha["s"]]
        if not mismos:
            mismos = [i for i, e in enumerate(data) if e.get("g") == "propias"] or [len(data) - 1]
        pos = next((i for i in mismos if data[i]["n"] > a.nombre), mismos[-1] + 1)
        data.insert(pos, ficha)
    else:
        if a.s:
            ficha["s"] = a.s
        if a.d:
            ficha["d"] = a.d
        ficha["u"] = f"skills/{a.nombre}.zip"
    if a.p:
        ficha["p"], ficha["po"] = a.p, a.po
    if not ficha.get("d"):
        sys.exit("ERROR: falta la descripción corta (--d).")
    nuevo = "const DATA = " + json.dumps(data, ensure_ascii=False) + ";\n"
    html = html[:m.start()] + nuevo + html[m.end():]
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)
    estado = cargar("estado.json", {})
    if a.nombre in src:
        estado[a.nombre] = huella(src[a.nombre])
    guardar("estado.json", estado)
    print(f"OK: {zp} y ficha actualizados")


def cmd_marcar(a):
    cfg = cargar("config.json", {})
    src = skills_origen(cfg)
    estado = cargar("estado.json", {})
    for n in a.nombres:
        estado[n] = huella(src[n])
    guardar("estado.json", estado)
    print("OK")


ap = argparse.ArgumentParser()
sp = ap.add_subparsers(dest="cmd", required=True)
sp.add_parser("detectar").set_defaults(f=cmd_detectar)
p = sp.add_parser("preparar"); p.add_argument("nombre"); p.set_defaults(f=cmd_preparar)
p = sp.add_parser("publicar"); p.add_argument("nombre"); p.add_argument("--s"); p.add_argument("--d")
p.add_argument("--p"); p.add_argument("--po", type=int, default=0)
p.add_argument("--forzar", action="store_true"); p.set_defaults(f=cmd_publicar)
p = sp.add_parser("marcar"); p.add_argument("nombres", nargs="+"); p.set_defaults(f=cmd_marcar)
a = ap.parse_args()
a.f(a)

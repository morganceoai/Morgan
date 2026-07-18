"""
Simucube Panel v3
─────────────────────────────────────────────────────────────────────────
Face frontal: plana, vertical, 185mm de altura
Face traseira: plana, vertical, 30mm de altura
Topo: cunha 20° que liga topo da face frontal ao topo da face traseira
Furos:
  • 2× M8 cantos superiores face frontal (passam de frente para trás)
  • 2× M8 cantos inferiores face traseira (passam de frente para trás)
  • 1× QR 80mm central (passa de frente para trás)
  • 2× Ar 97mm a 6cm de cada bordo lateral, centro em altura (passam de frente para trás)
Dividido em 3 secções para Bambu Lab A1 (256×256mm)
"""
import math
import numpy as np
import struct
import zipfile
from pathlib import Path
from manifold3d import Manifold

OUT = Path(__file__).parent / "stl"
OUT.mkdir(exist_ok=True)

# ── Parâmetros ──────────────────────────────────────────────────────────
PW         = 655.0   # largura total
PH         = 185.0   # altura face frontal
PB         = 30.0    # altura face traseira
A_DEG      = 20.0
A_RAD      = math.radians(A_DEG)
# Profundidade na base: cunha 20° entre (0,PH)→topo frontal e (PD,PB)→topo traseiro
PD         = (PH - PB) * math.tan(A_RAD)   # ≈ 56.4 mm
ESP        = 4.0     # espessura das paredes

# O plano da cunha: y + z·tan(20°) = PH·tan(20°)
# ↳ passa por (y=0, z=PH) e (y=PD, z=PB) ✓
CUTTER_C   = PH * math.tan(A_RAD)           # ≈ 67.3 mm

# Furos
QR_D       = 80.0
AIR_D      = 97.0
AIR_X      = 60.0    # distância do centro do furo ar ao bordo X (6 cm)
M8_D       = 8.8
M8_XI      = 20.0    # inset X dos furos M8 (desde cada bordo lateral)
M8_ZT      = PH - 20.0   # z furos M8 face frontal (topo)
M8_ZB      = 20.0         # z furos M8 face traseira (base), deve ser < PB

# Zona sólida em cada extremo X (garante material à volta dos furos de ar)
SOLID      = AIR_X + AIR_D / 2 + 8.0   # ≈ 113 mm

# Divisão em 3 secções (2 não cabem no A1: 327.5 mm > 256 mm)
CUT1       = 218.0
CUT2       = 437.0

# Pinos de alinhamento nas juntas (na parede frontal, sempre sólida)
PIN_D      = 4.0
PIN_L      = 5.0
PIN_TOL    = 0.3
PIN_Y      = 2.0
PIN_Z      = [PH / 3, 2 * PH / 3]   # ≈ 62 mm e 123 mm

SEG        = 64
CX         = PW / 2  # 327.5

# Grelha
GRL_OD     = 97.0
GRL_FL     = 103.0
GRL_H      = 22.0
GRL_FT     = 3.0
GRL_W      = 3.0
HOLE_D     = 7.0
HOLE_SP    = 11.0


# ── Corpo exterior ──────────────────────────────────────────────────────

def _slant_cut(solid, pw):
    """Corta a cunha 20° no topo da peça."""
    cutter = Manifold.cube([pw + 20, CUTTER_C + 20, PH + CUTTER_C + 20])
    cutter = cutter.rotate([A_DEG, 0, 0])
    cutter = cutter.translate([-10, CUTTER_C, 0])
    return solid - cutter

def corpo_exterior():
    bx = Manifold.cube([PW, PD + 5, PH])
    return _slant_cut(bx, PW)

def corpo_interior():
    """Vazio interior com paredes ESP em torno; zona sólida SOLID em cada extremo X."""
    # Altura interna: reduzida pela espessura da parede de cunha
    inner_PH = PH - ESP / math.sin(A_RAD)   # ≈ 173 mm
    inner_PD = PD - ESP                       # ≈ 52 mm (parede traseira já incluída)
    inner_PW = PW - 2 * SOLID

    inner_C  = inner_PH * math.tan(A_RAD)

    bx      = Manifold.cube([inner_PW, inner_PD + 5, inner_PH])
    cutter  = Manifold.cube([inner_PW + 20, inner_C + 20, inner_PH + inner_C + 20])
    cutter  = cutter.rotate([A_DEG, 0, 0])
    cutter  = cutter.translate([-10, inner_C, 0])
    inner   = bx - cutter
    # Deslocar: parede frontal ESP, parede inferior ESP, extremos SOLID
    return inner.translate([SOLID, ESP, ESP])


# ── Furos funcionais ────────────────────────────────────────────────────

def _cyl_y(d, x, z):
    """Cilindro ao longo de +Y (frente→trás) centrado em (x, z)."""
    c = Manifold.cylinder(d / 2, PD + 10, circular_segments=SEG)
    c = c.rotate([-90, 0, 0])
    c = c.translate([x, -1, z])
    return c

def furo_qr():
    return _cyl_y(QR_D, CX, PH / 2)

def furos_ar():
    """2 furos de 97 mm a 6 cm de cada bordo lateral, centrados em altura."""
    return _cyl_y(AIR_D, AIR_X, PH / 2) + _cyl_y(AIR_D, PW - AIR_X, PH / 2)

def furos_m8_frente():
    """2 furos M8 nos cantos superiores da face frontal."""
    return _cyl_y(M8_D, M8_XI, M8_ZT) + _cyl_y(M8_D, PW - M8_XI, M8_ZT)

def furos_m8_tras():
    """2 furos M8 nos cantos inferiores da face traseira."""
    return _cyl_y(M8_D, M8_XI, M8_ZB) + _cyl_y(M8_D, PW - M8_XI, M8_ZB)


# ── Painel completo ─────────────────────────────────────────────────────

def painel_completo():
    return (
        corpo_exterior()
        - corpo_interior()
        - furo_qr()
        - furos_ar()
        - furos_m8_frente()
        - furos_m8_tras()
    )


# ── Pinos de alinhamento ────────────────────────────────────────────────

def pins_macho(x_face):
    p = None
    for z in PIN_Z:
        pin = Manifold.cylinder(PIN_D / 2, PIN_L, circular_segments=32)
        pin = pin.rotate([0, 90, 0]).translate([x_face, PIN_Y, z])
        p = pin if p is None else p + pin
    return p

def pins_femea(x_face):
    p = None
    for z in PIN_Z:
        pin = Manifold.cylinder((PIN_D + PIN_TOL) / 2, PIN_L + 1, circular_segments=32)
        pin = pin.rotate([0, 90, 0]).translate([x_face, PIN_Y, z])
        p = pin if p is None else p + pin
    return p

def clip_x(m, x0, x1):
    box = Manifold.cube([x1 - x0 + 10, PD + 20, PH + 20])
    box = box.translate([x0 - 5, -5, -5])
    return m ^ box


# ── Secções ─────────────────────────────────────────────────────────────

def secao_A():
    print("  Secção A…")
    base = painel_completo()
    return clip_x(base, -5, CUT1) + pins_macho(CUT1)

def secao_B():
    print("  Secção B…")
    base = painel_completo()
    return (clip_x(base, CUT1, CUT2) - pins_femea(CUT1)) + pins_macho(CUT2)

def secao_C():
    print("  Secção C…")
    base = painel_completo()
    return clip_x(base, CUT2, PW + 5) - pins_femea(CUT2)


# ── Grelha ───────────────────────────────────────────────────────────────

def grelha():
    print("  Grelha…")
    inner_d = GRL_OD - 2 * GRL_W

    fl_outer   = Manifold.cylinder(GRL_FL / 2, GRL_FT, circular_segments=SEG)
    fl_rebaixo = Manifold.cylinder(inner_d / 2, 2, circular_segments=SEG)
    fl_rebaixo = fl_rebaixo.translate([0, 0, GRL_FT - 1.5])
    flange = fl_outer - fl_rebaixo

    face_s = Manifold.cylinder(inner_d / 2, GRL_FT - 1.5, circular_segments=SEG)
    r, furos_list = inner_d / 2, []
    x = -r
    while x <= r:
        y = -r
        while y <= r:
            if math.sqrt(x*x + y*y) + HOLE_D / 2 < r - 1.5:
                h = Manifold.cylinder(HOLE_D / 2, GRL_FT + 2, circular_segments=24)
                furos_list.append(h.translate([x, y, -1]))
            y += HOLE_SP
        x += HOLE_SP
    face = face_s
    for fh in furos_list:
        face = face - fh

    anel_o = Manifold.cylinder(GRL_OD / 2, GRL_H, circular_segments=SEG)
    anel_i = Manifold.cylinder(inner_d / 2, GRL_H + 2, circular_segments=SEG)
    anel   = (anel_o - anel_i.translate([0, 0, -1])).translate([0, 0, GRL_FT])

    return flange + face + anel


# ── Exportar 3MF ────────────────────────────────────────────────────────

def exportar(m, nome):
    nome_3mf = nome.replace(".stl", ".3mf")
    path = OUT / nome_3mf
    mesh  = m.to_mesh()
    verts = np.array(mesh.vert_properties, dtype=np.float32)
    tris  = np.array(mesh.tri_verts, dtype=np.int32)

    v_lines = "\n".join(
        f'        <vertex x="{v[0]:.4f}" y="{v[1]:.4f}" z="{v[2]:.4f}"/>'
        for v in verts
    )
    t_lines = "\n".join(
        f'        <triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}"/>'
        for t in tris
    )
    model_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US"
  xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
  <resources>
    <object id="1" type="model">
      <mesh>
        <vertices>
{v_lines}
        </vertices>
        <triangles>
{t_lines}
        </triangles>
      </mesh>
    </object>
  </resources>
  <build><item objectid="1"/></build>
</model>"""

    ct = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0"
    Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("3D/3dmodel.model", model_xml)

    kb = path.stat().st_size // 1024
    print(f"  ✓ {nome_3mf}  ({kb} KB)")


# ── Main ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Simucube Panel v3  |  PD≈{PD:.1f}mm  |  {PW:.0f}×{PH:.0f}/{PB:.0f}mm\n")
    print("Painel (3 secções — Bambu A1 máx 256mm, 2 secções não caberiam):")
    exportar(secao_A(), "painel_A.stl")
    exportar(secao_B(), "painel_B.stl")
    exportar(secao_C(), "painel_C.stl")
    print("\nGrelha (imprimir 2×):")
    exportar(grelha(), "grelha.stl")
    print(f"\n✓ Ficheiros em: {OUT.resolve()}")
    print(f"""
GEOMETRIA:
  Face frontal : {PH:.0f} mm de altura, plana e vertical
  Face traseira: {PB:.0f} mm de altura, plana e vertical
  Profundidade : {PD:.1f} mm (base) → 0 mm (topo)
  Cunha topo   : {A_DEG:.0f}° (compensa perfis diagonais)

FUROS:
  M8 × 4  — cantos: 2 topo face frontal (z={M8_ZT:.0f}mm), 2 base face traseira (z={M8_ZB:.0f}mm)
  QR 80mm — centro (x={CX:.1f}, z={PH/2:.1f}mm)
  Ar 97mm — a 6cm de cada lado (x={AIR_X:.0f} e x={PW-AIR_X:.0f}), centro altura (z={PH/2:.1f}mm)

ORIENTAÇÃO IMPRESSÃO:
  Secções A/B/C: face frontal (plana) pousada na cama — profundidade cresce para cima
  Grelha       : flange virada para baixo
""")

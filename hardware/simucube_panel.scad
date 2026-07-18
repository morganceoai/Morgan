// ═══════════════════════════════════════════════════════════════════════
//  MORGAN SIMUCUBE PANEL + GRELHAS
//  Bambu Lab A1 (256×256mm) — PLA Preto
//  5 impressões: Secção A + B + C + 2× Grelha
//
//  COMO EXPORTAR STL:
//    1. Descomentar a linha da peça pretendida no fim do ficheiro
//    2. F6 (render) → F7 (exportar STL)
//    3. Comentar de novo e repetir para a próxima peça
// ═══════════════════════════════════════════════════════════════════════

// ── PARÂMETROS (ajustar aqui se necessário) ────────────────────────────

// Painel
PW       = 655;    // mm — largura total (exterior a exterior dos perfis)
PH       = 185;    // mm — altura
PD       = 25;     // mm — profundidade (espaço entre base Simucube e volante)
ESP      = 4;      // mm — espessura das paredes

// Perfis 4040 — montagem
TAB_CC   = 620;    // mm — centro-a-centro dos perfis (furos M8)
M8_D     = 8.8;    // mm — diâmetro do furo M8 (com folga de 0.4mm)
TAB_H    = 45;     // mm — altura das abas de fixação (acima do painel)
TAB_W    = 40;     // mm — largura das abas (cobre o perfil 4040)

// Furos funcionais
QR_D     = 80;     // mm — furo central (eixo QR / Simucube 2 Pro)
GR_HOLE  = 97.3;   // mm — furo no painel para encaixe da grelha
GR_OFF   = 172.5;  // mm — offset horizontal das grelhas ao centro

// Grelha (peça separada)
GRL_OD   = 97.0;   // mm — diâmetro exterior do anel (press-fit leve)
GRL_FL   = 103.0;  // mm — diâmetro da flange frontal
GRL_H    = 22;     // mm — profundidade do anel de encaixe
GRL_FT   = 3;      // mm — espessura da flange frontal
GRL_W    = 3;      // mm — espessura da parede do anel
HOLE_D   = 7;      // mm — diâmetro dos furos da grelha
HOLE_SP  = 11;     // mm — espaçamento entre centros dos furos

// Divisão em 3 secções (máx. 256mm por impressão)
CUT1     = 220;    // mm — primeiro corte
CUT2     = 435;    // mm — segundo corte

// Pinos de alinhamento nas junções
PIN_D    = 4.0;    // mm — diâmetro
PIN_L    = 5.0;    // mm — comprimento de cada metade
PIN_TOL  = 0.3;    // mm — folga para o furo receptor
PIN_Z    = [55, 130]; // mm — posições z dos 2 pinos por junção

$fn = 128;

// ── POSIÇÕES CALCULADAS ────────────────────────────────────────────────
CX      = PW / 2;             // 327.5 — centro do painel
GL_X    = CX - GR_OFF;       // 155.0 — centro grelha esquerda
GR_X    = CX + GR_OFF;       // 500.0 — centro grelha direita
TAB_XL  = (PW - TAB_CC) / 2; // 17.5  — centro aba esquerda
TAB_XR  = PW - TAB_XL;       // 637.5 — centro aba direita


// ═══════════════════════════════════════════════════════════════════════
//  GEOMETRIA DO PAINEL COMPLETO
// ═══════════════════════════════════════════════════════════════════════

module corpo_painel() {
    union() {
        // Corpo principal
        cube([PW, PD, PH]);

        // Aba de fixação esquerda
        translate([TAB_XL - TAB_W/2, 0, PH])
            cube([TAB_W, PD, TAB_H]);

        // Aba de fixação direita
        translate([TAB_XR - TAB_W/2, 0, PH])
            cube([TAB_W, PD, TAB_H]);
    }
}

module furos_painel() {
    // ── Interior oco (paredes de ESP mm) ────────────────────────────
    translate([ESP, ESP, ESP])
        cube([PW - 2*ESP, PD - ESP, PH - 2*ESP]);

    // ── Furo central QR / Simucube ───────────────────────────────────
    translate([CX, -1, PH/2])
    rotate([-90, 0, 0])
        cylinder(d=QR_D, h=PD+2);

    // ── Furo grelha esquerda ─────────────────────────────────────────
    translate([GL_X, -1, PH/2])
    rotate([-90, 0, 0])
        cylinder(d=GR_HOLE, h=PD+2);

    // ── Furo grelha direita ──────────────────────────────────────────
    translate([GR_X, -1, PH/2])
    rotate([-90, 0, 0])
        cylinder(d=GR_HOLE, h=PD+2);

    // ── Furo M8 aba esquerda ─────────────────────────────────────────
    translate([TAB_XL, -1, PH + TAB_H/2])
    rotate([-90, 0, 0])
        cylinder(d=M8_D, h=PD+2);

    // ── Furo M8 aba direita ──────────────────────────────────────────
    translate([TAB_XR, -1, PH + TAB_H/2])
    rotate([-90, 0, 0])
        cylinder(d=M8_D, h=PD+2);
}

module painel_completo() {
    difference() {
        corpo_painel();
        furos_painel();
    }
}


// ═══════════════════════════════════════════════════════════════════════
//  PINOS DE ALINHAMENTO
// ═══════════════════════════════════════════════════════════════════════

// Pino macho: sai da face x em direção +X (para a direita)
module pins_macho(face_x) {
    for(z = PIN_Z) {
        translate([face_x, PD/2, z])
        rotate([0, -90, 0])
            cylinder(d=PIN_D, h=PIN_L);
    }
}

// Furo fêmea: entra na peça a partir da face x em direção +X
module pins_femea(face_x) {
    for(z = PIN_Z) {
        translate([face_x, PD/2, z])
        rotate([0, -90, 0])
            cylinder(d=PIN_D + PIN_TOL, h=PIN_L + 1);
    }
}


// ═══════════════════════════════════════════════════════════════════════
//  SECÇÕES DO PAINEL (para impressão individual)
// ═══════════════════════════════════════════════════════════════════════

// ── Secção A: ESQUERDA (x: 0 → CUT1=220mm) ───────────────────────────
//    Contém: aba esquerda + grelha esquerda
//    Tamanho impressão: ~222mm × 235mm × 25mm ✓ (cabe em 256×256)
module painel_A() {
    union() {
        // Corpo cortado
        intersection() {
            painel_completo();
            translate([-5, -1, -1])
                cube([CUT1 + 5, PD+2, PH+TAB_H+2]);
        }
        // Pinos macho na face direita (encaixam em B)
        pins_macho(CUT1);
    }
}

// ── Secção B: CENTRAL (x: CUT1=220mm → CUT2=435mm) ───────────────────
//    Contém: furo QR central
//    Tamanho impressão: 215mm × 185mm × 25mm ✓
module painel_B() {
    union() {
        difference() {
            // Corpo cortado
            intersection() {
                painel_completo();
                translate([CUT1, -1, -1])
                    cube([CUT2 - CUT1, PD+2, PH+TAB_H+2]);
            }
            // Furos fêmea na face esquerda (recebem pinos de A)
            pins_femea(CUT1);
        }
        // Pinos macho na face direita (encaixam em C)
        pins_macho(CUT2);
    }
}

// ── Secção C: DIREITA (x: CUT2=435mm → 655mm) ────────────────────────
//    Contém: grelha direita + aba direita
//    Tamanho impressão: ~222mm × 235mm × 25mm ✓
module painel_C() {
    difference() {
        // Corpo cortado
        intersection() {
            painel_completo();
            translate([CUT2, -1, -1])
                cube([PW - CUT2 + 5, PD+2, PH+TAB_H+2]);
        }
        // Furos fêmea na face esquerda (recebem pinos de B)
        pins_femea(CUT2);
    }
}


// ═══════════════════════════════════════════════════════════════════════
//  GRELHA (imprimir 2 exemplares)
//  Orientação impressão: flange virada para baixo (para a cama)
// ═══════════════════════════════════════════════════════════════════════

module face_grelha(inner_d, espessura) {
    // Face com padrão de furos circulares numa grelha rectangular
    inner_r = inner_d / 2;
    difference() {
        cylinder(d=inner_d, h=espessura);
        // Padrão de furos (só onde cabem inteiros dentro do círculo)
        for(x = [-inner_r : HOLE_SP : inner_r]) {
            for(y = [-inner_r : HOLE_SP : inner_r]) {
                // Só corta se o furo ficar completamente dentro do círculo
                if(sqrt(x*x + y*y) + HOLE_D/2 < inner_r - 1.5) {
                    translate([x, y, -1])
                        cylinder(d=HOLE_D, h=espessura+2);
                }
            }
        }
    }
}

module grelha() {
    inner_d = GRL_OD - 2*GRL_W;  // ~91mm — diâmetro interior do anel

    union() {
        // Flange frontal (fica por cima do painel, impede que entre toda)
        difference() {
            cylinder(d=GRL_FL, h=GRL_FT);
            // Rebaixo: deixa espessura de 1.5mm na face frontal
            translate([0, 0, GRL_FT - 1.5])
                cylinder(d=inner_d, h=2);
        }

        // Face com grelha (flush com a flange)
        face_grelha(inner_d, GRL_FT - 1.5);

        // Anel de encaixe (entra no furo do painel)
        translate([0, 0, GRL_FT]) {
            difference() {
                cylinder(d=GRL_OD, h=GRL_H);
                translate([0, 0, -1])
                    cylinder(d=inner_d, h=GRL_H+2);
            }
        }
    }
}


// ═══════════════════════════════════════════════════════════════════════
//  RENDER — descomentar a peça a exportar
// ═══════════════════════════════════════════════════════════════════════

painel_A();    // Secção esquerda  (~222×235mm)
//painel_B();  // Secção central   (215×185mm)
//painel_C();  // Secção direita   (~222×235mm)
//grelha();    // Grelha — imprimir 2×  (103×103×25mm)


// ═══════════════════════════════════════════════════════════════════════
//  RESUMO DE IMPRESSÃO
// ═══════════════════════════════════════════════════════════════════════
//
//  Peça          | Qtd | Dimensões         | Tempo est.
//  --------------|-----|-------------------|------------
//  Secção A      |  1  | 222 × 235 × 25mm | ~8h
//  Secção B      |  1  | 215 × 185 × 25mm | ~6h
//  Secção C      |  1  | 222 × 235 × 25mm | ~8h
//  Grelha        |  2  | 103 × 103 × 25mm | ~2h cada
//
//  Configurações recomendadas Bambu Lab A1:
//  - Material:     PLA Preto
//  - Layer height: 0.2mm
//  - Paredes:      4 (wall loops)
//  - Infill:       20% Gyroid
//  - Suportes:     Não necessários
//  - Orientação:   flat (deitado na cama, face frontal virada para cima)
//
//  Montagem:
//  1. Colar secções A+B+C com super-glue nos pinos + juntas
//  2. Pressionar grelhas nos furos (press-fit — não precisa cola)
//  3. Parafusar nas abas superiores com M8 + porca T-slot 8mm
// ═══════════════════════════════════════════════════════════════════════

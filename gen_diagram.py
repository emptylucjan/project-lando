import json, random, string

def uid():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=20))

def rect(id_, x, y, w, h, label, bg, fg="#ffffff", font_size=16, bold=True):
    return {
        "id": id_, "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "backgroundColor": bg, "strokeColor": "#00000060",
        "fillStyle": "solid", "strokeWidth": 2, "roughness": 0,
        "opacity": 100, "roundness": {"type": 3},
        "boundElements": [],
        "text": label
    }

def text_el(id_, x, y, w, h, label, color="#ffffff", font_size=14, bold=False):
    return {
        "id": id_, "type": "text",
        "x": x, "y": y, "width": w, "height": h,
        "text": label,
        "fontSize": font_size,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "color": color,
        "backgroundColor": "transparent",
        "strokeColor": "transparent",
        "fillStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "boundElements": [],
    }

def arrow(id_, sx, sy, ex, ey, label=""):
    el = {
        "id": id_, "type": "arrow",
        "x": sx, "y": sy,
        "width": abs(ex-sx), "height": abs(ey-sy),
        "points": [[0, 0], [ex-sx, ey-sy]],
        "strokeColor": "#495057",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "roughness": 0,
        "opacity": 100,
        "startArrowhead": None,
        "endArrowhead": "arrow",
        "boundElements": [],
    }
    if label:
        el["label"] = {"text": label}
    return el

# ── Layout ─────────────────────────────────────────────
# Entry Points: y = 80
# Scraper row: y = 80 (left side)  
# Backend: y = 300
# Subiekt: y = 520

# x centers
xD, xW, xB = 100, 400, 700   # Discord, WhatsApp, B2B
xSC = -250                    # Scraper (left)
xAPI = 350                    # Backend (center)
xSUB = 350                    # Subiekt (center)

BOX_W = 200
BOX_H = 100
WIDE_W = 480
WIDE_H = 130

# COLORS
C_DISCORD  = "#5865F2"   # discord blue/purple
C_WA       = "#25D366"   # whatsapp green
C_B2B      = "#0077B6"   # ocean blue
C_SCRAPER  = "#6c757d"   # gray
C_API      = "#7209b7"   # purple
C_SUB      = "#e76f51"   # orange

elements = []

# ── SCRAPER ───────────────────────────────────────────
elements.append({**rect("sc", xSC-BOX_W//2, 40, BOX_W, BOX_H, "", C_SCRAPER), "boundElements": [{"type":"text","id":"sc_t"}]})
elements.append(text_el("sc_t", xSC-BOX_W//2, 40, BOX_W, BOX_H, "🕷️ Scraper Zalando\nEAN · ceny · rozmiary\npackshot", "#ffffff", 13))

# Header text
elements.append(text_el("hdr", -300, -30, 1200, 40,
    "VERO SPORT — Architektura Systemu", "#212529", 22, True))

# ── ENTRY POINTS ──────────────────────────────────────
y_ep = 40
# Discord
elements.append({**rect("disc", xD-BOX_W//2, y_ep, BOX_W, BOX_H, "", C_DISCORD), "boundElements": [{"type":"text","id":"disc_t"}]})
elements.append(text_el("disc_t", xD-BOX_W//2, y_ep, BOX_W, BOX_H, "🤖 Discord Bot\nMrówka\n✅ gotowy", "#ffffff", 13))

# WhatsApp
elements.append({**rect("wa", xW-BOX_W//2, y_ep, BOX_W, BOX_H, "", C_WA), "boundElements": [{"type":"text","id":"wa_t"}]})
elements.append(text_el("wa_t", xW-BOX_W//2, y_ep, BOX_W, BOX_H, "💬 WhatsApp Bot\n🔧 do zrobienia", "#ffffff", 13))

# B2B
elements.append({**rect("b2b", xB-BOX_W//2, y_ep, BOX_W, BOX_H, "", C_B2B), "boundElements": [{"type":"text","id":"b2b_t"}]})
elements.append(text_el("b2b_t", xB-BOX_W//2, y_ep, BOX_W, BOX_H, "🌐 B2B Sklep\nVero Sport\n✅ gotowy", "#ffffff", 13))

# ── BACKEND ───────────────────────────────────────────
y_api = 250
x_api_left = xAPI - WIDE_W//2
elements.append({**rect("api", x_api_left, y_api, WIDE_W, WIDE_H, "", C_API), "boundElements": [{"type":"text","id":"api_t"}]})
elements.append(text_el("api_t", x_api_left, y_api, WIDE_W, WIDE_H,
    "⚙️ Backend .NET — port 5051\nEnsureProduct · FindCustomer\nCreateZK · CreatePZ",
    "#ffffff", 14))

# ── SUBIEKT ───────────────────────────────────────────
y_sub = 460
x_sub_left = xSUB - WIDE_W//2
elements.append({**rect("sub", x_sub_left, y_sub, WIDE_W, WIDE_H, "", C_SUB), "boundElements": [{"type":"text","id":"sub_t"}]})
elements.append(text_el("sub_t", x_sub_left, y_sub, WIDE_W, WIDE_H,
    "🗄️ Subiekt Nexo ERP\nAsortyment · ZK Zamówienie\nPZ Przyjęcie · FV Faktura",
    "#ffffff", 14))

# ── ARROWS ────────────────────────────────────────────
# Scraper → Discord
elements.append(arrow("a_sc_d", xSC+BOX_W//2+10, y_ep+50, xD-BOX_W//2-10, y_ep+50))
# Scraper → B2B
elements.append(arrow("a_sc_b", xSC+BOX_W//2+10, y_ep+70, xB-BOX_W//2-10, y_ep+70))

# WA → Discord  (konwertuje zamówienie na format Discord)
elements.append(arrow("a_wa_d", xW-BOX_W//2-10, y_ep+35, xD+BOX_W//2+10, y_ep+35))

# Discord → Backend
elements.append(arrow("a_d_api", xD, y_ep+BOX_H+5, xAPI-60, y_api-5))
# WA direct → Backend (alternatywnie)
elements.append(arrow("a_wa_api", xW, y_ep+BOX_H+5, xAPI, y_api-5))
# B2B → Backend
elements.append(arrow("a_b_api", xB, y_ep+BOX_H+5, xAPI+60, y_api-5))

# Backend → Subiekt
elements.append(arrow("a_api_sub", xAPI, y_api+WIDE_H+5, xSUB, y_sub-5))

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {
        "viewBackgroundColor": "#f8f9fa",
        "currentItemFontFamily": 1,
        "zoom": {"value": 1}
    },
    "files": {}
}

path = r"C:\Users\lukko\Desktop\projekt zalando\vero_diagram.excalidraw"
with open(path, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print("Saved:", path)
